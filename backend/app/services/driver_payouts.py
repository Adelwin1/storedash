from __future__ import annotations

from decimal import Decimal
import logging

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

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

    client_reference = (
        f"SD-DRIVER-BATCH-{batch.id:06d}-D{batch.driver_id}"
    )

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
        status=PayoutStatus.PENDING_APPROVAL,
        approved_by_id=None,
        approved_at=None,
        initiated_at=None,
    )

    db.add(payout)

    try:
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

    return payout
