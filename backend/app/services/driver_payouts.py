from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import uuid4
import logging

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import (
    DeliveryBatch,
    Payout,
    PayoutProfile,
    PayoutRecipientType,
    PayoutStatus,
)
from app.services.hubtel import HubtelError, hubtel


logger = logging.getLogger(__name__)


def trigger_driver_payout(
    db: Session,
    *,
    batch_id: int,
) -> Payout | None:
    batch = db.get(
        DeliveryBatch,
        batch_id,
    )

    if (
        batch is None
        or batch.status != "completed"
        or batch.driver_id is None
    ):
        return None

    amount = Decimal(
        str(batch.actual_driver_payout or 0)
    ).quantize(
        Decimal("0.01")
    )

    if amount <= 0:
        logger.warning(
            "Batch %s completed without valid driver payout.",
            batch.id,
        )
        return None

    # Never pay the same physical route twice.
    existing = db.scalars(
        select(Payout).where(
            Payout.delivery_batch_id == batch.id,
            Payout.driver_id == batch.driver_id,
            Payout.recipient_type
            == PayoutRecipientType.DRIVER,
            Payout.reason == "driver_route",
            Payout.status != PayoutStatus.CANCELLED,
        )
    ).first()

    if existing is not None:
        return existing

    profile = db.scalars(
        select(PayoutProfile)
        .where(
            PayoutProfile.driver_id == batch.driver_id,
            PayoutProfile.recipient_type
            == PayoutRecipientType.DRIVER,
            PayoutProfile.is_active.is_(True),
            PayoutProfile.is_verified.is_(True),
            PayoutProfile.is_locked.is_(True),
        )
        .order_by(
            PayoutProfile.version.desc()
        )
    ).first()

    if profile is None:
        logger.error(
            "Driver %s has no verified locked payout profile.",
            batch.driver_id,
        )
        return None

    # Deterministic per batch + driver.
    # The UNIQUE client_reference is an additional
    # database-level guard against duplicate payouts.
    client_reference = (
        f"sdd-{batch.id}-{batch.driver_id}"
    )

    now = datetime.utcnow()

    payout = Payout(
        payout_profile_id=profile.id,
        recipient_type=PayoutRecipientType.DRIVER,
        supplier_id=None,
        driver_id=batch.driver_id,
        order_id=None,
        delivery_batch_id=batch.id,
        amount=amount,
        currency="GHS",
        reason="driver_route",
        client_reference=client_reference,
        status=PayoutStatus.PROCESSING,
        approved_by_id=None,
        approved_at=now,
        initiated_at=now,
    )

    db.add(payout)

    try:
        # Commit BEFORE contacting Hubtel.
        # Even if the provider times out, this payout now
        # exists and cannot be recreated with the same reference.
        db.commit()
        db.refresh(payout)
    except IntegrityError:
        db.rollback()

        return db.scalars(
            select(Payout).where(
                Payout.client_reference
                == client_reference
            )
        ).first()

    callback_url = (
        settings.hubtel_callback_base_url.rstrip("/")
        + "/api/payments/hubtel/payouts/callback"
    )

    try:
        result = hubtel.send_money(
            recipient_name=profile.payment_name,
            recipient_phone=profile.payment_phone,
            channel=profile.network or "",
            amount=amount,
            description=(
                f"StoreDash driver payout batch #{batch.id}"
            ),
            client_reference=client_reference,
            callback_url=callback_url,
        )

    except HubtelError as exc:
        # Delivery remains completed.
        # Never retry blindly because Hubtel may have
        # actually received the transfer request.
        payout.status = PayoutStatus.PROCESSING
        payout.failure_reason = (
            "Provider result unresolved: "
            + str(exc)
        )

        db.commit()

        logger.warning(
            "Driver payout %s unresolved: %s",
            payout.id,
            exc,
        )

        return payout

    response_code = str(
        result.get("ResponseCode", "")
    ).strip()

    data = result.get("Data") or {}

    if not isinstance(data, dict):
        data = {}

    provider_transaction_id = str(
        data.get("TransactionId")
        or data.get("TransactionID")
        or ""
    ).strip()

    if provider_transaction_id:
        payout.provider_transaction_id = (
            provider_transaction_id
        )

    if response_code == "0001":
        payout.status = PayoutStatus.PROCESSING
        payout.failure_reason = None

    elif response_code == "2001":
        payout.status = PayoutStatus.FAILED
        payout.failure_reason = str(
            data.get("Description")
            or result.get("Message")
            or "Driver payout rejected."
        )

    else:
        payout.status = PayoutStatus.PROCESSING
        payout.failure_reason = (
            "Unexpected provider response; "
            "reconciliation required."
        )

    db.commit()
    db.refresh(payout)

    return payout
