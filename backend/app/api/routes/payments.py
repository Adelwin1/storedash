from __future__ import annotations

from datetime import datetime
import hashlib
import hmac
import json
from typing import Any
from decimal import Decimal
from uuid import uuid4

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Request,
    status,
)
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.auth import current_user_id
from app.core.config import settings
from app.core.db import get_db
from app.models import (
    Driver,
    Order,
    OrderStatus,
    PaymentEvent,
    PaymentStatus,
    PaymentTransaction,
    Payout,
    PayoutProfile,
    PayoutRecipientType,
    PayoutStatus,
    Role,
    Supplier,
    User,
)
from app.services.sms_payment_relay import (
    message_fingerprint,
    normalize_phone_from_text,
    parse_money_sms,
)

from app.services.hubtel import (
    HubtelError,
    hubtel,
    normalize_ghana_phone,
    normalize_momo_channel,
)


router = APIRouter(
    prefix="/payments",
    tags=["payments"],
)


class CustomerPaymentRequest(BaseModel):
    customer_phone: str = Field(
        min_length=10,
        max_length=30,
    )
    network: str = Field(
        min_length=2,
        max_length=40,
    )


def require_payment_operator(
    request: Request,
    db: Session,
) -> User:
    user_id = current_user_id(request)

    user = db.get(
        User,
        user_id,
    )

    if (
        user is None
        or not user.is_active
        or user.role not in {
            Role.ADMIN,
            Role.MANAGER,
            Role.OPERATIONS,
        }
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Payment operations access required.",
        )

    return user


def require_finance_manager(
    request: Request,
    db: Session,
) -> User:
    user_id = current_user_id(request)

    user = db.get(
        User,
        user_id,
    )

    if (
        user is None
        or not user.is_active
        or user.role not in {
            Role.ADMIN,
            Role.MANAGER,
        }
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                "Manager or admin financial "
                "access required."
            ),
        )

    return user


@router.get(
    "/dashboard",
)
def payment_dashboard(
    request: Request,
    db: Session = Depends(get_db),
):
    actor = require_payment_operator(
        request,
        db,
    )

    can_control_money = (
        actor.role
        in {
            Role.ADMIN,
            Role.MANAGER,
        }
    )

    def value(item):
        return (
            item.value
            if hasattr(item, "value")
            else str(item)
        )

    def timestamp(item):
        return (
            item.isoformat()
            if item is not None
            else None
        )

    def mask_phone(phone):
        if not phone:
            return None

        phone = str(phone)

        if len(phone) <= 4:
            return phone

        return (
            "•" * max(
                len(phone) - 4,
                4,
            )
            + phone[-4:]
        )

    transactions = list(
        db.scalars(
            select(
                PaymentTransaction
            )
            .order_by(
                PaymentTransaction.id.desc()
            )
            .limit(50)
        ).all()
    )

    payouts = list(
        db.scalars(
            select(
                Payout
            )
            .order_by(
                Payout.id.desc()
            )
            .limit(50)
        ).all()
    )

    incoming_pending = (
        db.scalar(
            select(
                func.count()
            )
            .select_from(
                PaymentTransaction
            )
            .where(
                PaymentTransaction.status.in_(
                    {
                        PaymentStatus.INITIATED,
                        PaymentStatus.PENDING,
                    }
                )
            )
        )
        or 0
    )

    incoming_succeeded = (
        db.scalar(
            select(
                func.count()
            )
            .select_from(
                PaymentTransaction
            )
            .where(
                PaymentTransaction.status
                == PaymentStatus.SUCCEEDED
            )
        )
        or 0
    )

    payout_attention = (
        db.scalar(
            select(
                func.count()
            )
            .select_from(
                Payout
            )
            .where(
                Payout.status.in_(
                    {
                        PayoutStatus.PENDING_APPROVAL,
                        PayoutStatus.APPROVED,
                        PayoutStatus.PROCESSING,
                    }
                )
            )
        )
        or 0
    )

    payment_failures = (
        db.scalar(
            select(
                func.count()
            )
            .select_from(
                PaymentTransaction
            )
            .where(
                PaymentTransaction.status
                == PaymentStatus.FAILED
            )
        )
        or 0
    )

    payout_failures = (
        db.scalar(
            select(
                func.count()
            )
            .select_from(
                Payout
            )
            .where(
                Payout.status
                == PayoutStatus.FAILED
            )
        )
        or 0
    )

    incoming = []

    for transaction in transactions:
        order = db.get(
            Order,
            transaction.order_id,
        )

        incoming.append({
            "id":
                transaction.id,

            "order_id":
                transaction.order_id,

            "order_number":
                (
                    order.order_number
                    if order
                    else None
                ),

            "amount":
                str(
                    transaction.amount
                ),

            "currency":
                transaction.currency,

            "payer_phone":
                transaction.payer_phone,

            "payment_method":
                transaction.payment_method,

            "status":
                value(
                    transaction.status
                ),

            "provider_status":
                transaction.provider_status,

            "client_reference":
                transaction.client_reference,

            "failure_reason":
                transaction.failure_reason,

            "created_at":
                timestamp(
                    transaction.created_at
                ),

            "confirmed_at":
                timestamp(
                    transaction.confirmed_at
                ),
        })

    outgoing = []

    for payout in payouts:
        profile = db.get(
            PayoutProfile,
            payout.payout_profile_id,
        )

        payment_phone = (
            profile.payment_phone
            if profile
            else None
        )

        outgoing.append({
            "id":
                payout.id,

            "recipient_type":
                value(
                    payout.recipient_type
                ),

            "supplier_id":
                payout.supplier_id,

            "driver_id":
                payout.driver_id,

            "order_id":
                payout.order_id,

            "delivery_batch_id":
                payout.delivery_batch_id,

            "amount":
                str(
                    payout.amount
                ),

            "currency":
                payout.currency,

            "reason":
                payout.reason,

            "status":
                value(
                    payout.status
                ),

            "recipient_name":
                (
                    profile.payment_name
                    if profile
                    else None
                ),

            "recipient_phone":
                (
                    payment_phone
                    if can_control_money
                    else mask_phone(
                        payment_phone
                    )
                ),

            "can_control":
                can_control_money,

            "failure_reason":
                payout.failure_reason,

            "created_at":
                timestamp(
                    payout.created_at
                ),

            "completed_at":
                timestamp(
                    payout.completed_at
                ),
        })

    return {
        "role":
            actor.role.value,

        "can_control_money":
            can_control_money,

        "summary": {
            "incoming_pending":
                incoming_pending,

            "incoming_succeeded":
                incoming_succeeded,

            "payout_attention":
                payout_attention,

            "exceptions":
                (
                    payment_failures
                    + payout_failures
                ),
        },

        "incoming":
            incoming,

        "outgoing":
            outgoing,
    }


@router.post(
    "/orders/{order_id}/request",
    status_code=status.HTTP_202_ACCEPTED,
)
def request_customer_payment(
    order_id: int,
    payload: CustomerPaymentRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    actor = require_payment_operator(
        request,
        db,
    )

    order = db.get(
        Order,
        order_id,
    )

    if order is None:
        raise HTTPException(
            status_code=404,
            detail="Order not found.",
        )

    if order.status != OrderStatus.AWAITING_PAYMENT:
        raise HTTPException(
            status_code=409,
            detail=(
                "Order must be awaiting payment "
                "before a MoMo request can be created."
            ),
        )

    if order.customer_approved_at is None:
        raise HTTPException(
            status_code=409,
            detail="Customer approval has not been recorded.",
        )

    amount = Decimal(
        str(order.final_total or 0)
    ).quantize(
        Decimal("0.01")
    )

    if amount <= 0:
        raise HTTPException(
            status_code=409,
            detail="Order has no valid payable total.",
        )

    existing = db.scalars(
        select(PaymentTransaction)
        .where(
            PaymentTransaction.order_id == order.id,
            PaymentTransaction.status.in_(
                [
                    PaymentStatus.INITIATED,
                    PaymentStatus.PENDING,
                    PaymentStatus.SUCCEEDED,
                ]
            ),
        )
        .order_by(
            PaymentTransaction.id.desc()
        )
    ).first()

    if existing is not None:
        raise HTTPException(
            status_code=409,
            detail={
                "message":
                    "This order already has an active payment.",
                "payment_transaction_id":
                    existing.id,
                "client_reference":
                    existing.client_reference,
                "status":
                    existing.status.value,
            },
        )

    try:
        phone = normalize_ghana_phone(
            payload.customer_phone
        )
        channel = normalize_momo_channel(
            payload.network
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

    client_reference = (
        f"sd-{order.id}-{uuid4().hex[:20]}"
    )

    transaction = PaymentTransaction(
        order_id=order.id,
        provider="hubtel",
        client_reference=client_reference,
        amount=amount,
        currency="GHS",
        payment_method="momo",
        payer_phone=phone,
        status=PaymentStatus.INITIATED,
        provider_status="created",
        initiated_at=datetime.utcnow(),
    )

    db.add(transaction)
    db.commit()
    db.refresh(transaction)

    callback_url = (
        settings.hubtel_callback_base_url.rstrip("/")
        + "/api/payments/hubtel/collections/callback"
    )

    try:
        result = hubtel.receive_money(
            customer_phone=phone,
            channel=channel,
            amount=amount,
            description=f"StoreDash order #{order.id}",
            client_reference=client_reference,
            callback_url=callback_url,
        )
    except HubtelError as exc:
        # The provider result may be unknown after a timeout.
        # Never create a second charge blindly.
        transaction.status = PaymentStatus.PENDING
        transaction.provider_status = "request_unknown"
        transaction.failure_reason = str(exc)

        db.commit()

        raise HTTPException(
            status_code=502,
            detail={
                "message":
                    "Payment provider result is unresolved. "
                    "Do not retry this payment yet.",
                "client_reference":
                    client_reference,
            },
        ) from exc

    response_code = str(
        result.get("ResponseCode", "")
    )

    data = result.get("Data") or {}

    if isinstance(data, dict):
        provider_transaction_id = (
            data.get("TransactionId")
            or data.get("TransactionID")
        )
    else:
        provider_transaction_id = None

    if provider_transaction_id:
        transaction.provider_transaction_id = str(
            provider_transaction_id
        )

    transaction.provider_status = (
        response_code or "unknown"
    )

    if response_code == "0001":
        transaction.status = PaymentStatus.PENDING

    elif response_code == "2001":
        transaction.status = PaymentStatus.FAILED
        transaction.failure_reason = str(
            result.get("Message")
            or "Hubtel rejected the payment request."
        )

    else:
        # Unknown does NOT mean failed and definitely
        # does not mean paid. Reconciliation handles it.
        transaction.status = PaymentStatus.PENDING
        transaction.failure_reason = (
            "Unexpected initiation response; "
            "status reconciliation required."
        )

    db.commit()
    db.refresh(transaction)

    if transaction.status == PaymentStatus.FAILED:
        raise HTTPException(
            status_code=502,
            detail={
                "message":
                    transaction.failure_reason,
                "client_reference":
                    transaction.client_reference,
            },
        )

    return {
        "payment_transaction_id":
            transaction.id,
        "order_id":
            order.id,
        "amount":
            str(amount),
        "currency":
            "GHS",
        "status":
            transaction.status.value,
        "client_reference":
            transaction.client_reference,
        "payer_phone":
            transaction.payer_phone,
        "network":
            channel,
        "initiated_by":
            actor.id,
    }



@router.post(
    "/hubtel/collections/callback",
)
def hubtel_collection_callback(
    payload: dict[str, Any],
    db: Session = Depends(get_db),
):
    """
    Hubtel collection callbacks are provider-to-provider.
    No StoreDash employee authentication is used here.

    Security comes from matching the callback to a payment
    StoreDash already created: client reference, amount and
    provider transaction identity must agree.
    """

    response_code = str(
        payload.get("ResponseCode", "")
    ).strip()

    data = payload.get("Data") or {}

    if not isinstance(data, dict):
        data = {}

    client_reference = str(
        data.get("ClientReference", "")
    ).strip()

    provider_transaction_id = str(
        data.get("TransactionId", "")
        or data.get("TransactionID", "")
    ).strip()

    # Hubtel does not provide a separate callback/event ID.
    # Build a deterministic one so repeated callbacks are harmless.
    if provider_transaction_id:
        provider_event_id = (
            "collection:"
            + provider_transaction_id
            + ":"
            + (response_code or "unknown")
        )
    else:
        canonical = json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
            default=str,
        )

        provider_event_id = (
            "collection:"
            + hashlib.sha256(
                canonical.encode("utf-8")
            ).hexdigest()
        )

    existing_event = db.scalars(
        select(PaymentEvent).where(
            PaymentEvent.provider_event_id
            == provider_event_id
        )
    ).first()

    if existing_event is not None:
        return {
            "received": True,
            "duplicate": True,
            "provider_event_id":
                provider_event_id,
        }

    transaction = None

    if client_reference:
        transaction = db.scalars(
            select(PaymentTransaction).where(
                PaymentTransaction.client_reference
                == client_reference
            )
        ).first()

    event = PaymentEvent(
        provider="hubtel",
        provider_event_id=provider_event_id,
        event_type="collection_callback",
        payment_transaction_id=(
            transaction.id
            if transaction is not None
            else None
        ),
        raw_payload=json.dumps(
            payload,
            sort_keys=True,
            default=str,
        ),
        is_processed=False,
    )

    db.add(event)

    now = datetime.utcnow()

    if transaction is None:
        event.processing_error = (
            "Unknown or missing ClientReference."
        )
        db.commit()

        # Acknowledge receipt so the provider does not
        # repeatedly retry an event we cannot match.
        return {
            "received": True,
            "processed": False,
        }

    # If StoreDash already successfully processed the payment,
    # this new callback cannot fulfil the order a second time.
    if transaction.status == PaymentStatus.SUCCEEDED:
        event.is_processed = True
        event.processed_at = now
        db.commit()

        return {
            "received": True,
            "processed": True,
            "already_confirmed": True,
        }

    if (
        transaction.provider_transaction_id
        and provider_transaction_id
        and transaction.provider_transaction_id
        != provider_transaction_id
    ):
        event.processing_error = (
            "Provider transaction ID mismatch."
        )
        db.commit()

        return {
            "received": True,
            "processed": False,
        }

    if response_code == "0000":
        try:
            received = Decimal(
                str(data.get("Amount"))
            ).quantize(
                Decimal("0.01")
            )
        except Exception:
            event.processing_error = (
                "Successful callback has invalid amount."
            )
            db.commit()

            return {
                "received": True,
                "processed": False,
            }

        expected = Decimal(
            str(transaction.amount)
        ).quantize(
            Decimal("0.01")
        )

        if received != expected:
            event.processing_error = (
                "Callback amount does not match "
                "the StoreDash payment transaction."
            )
            db.commit()

            return {
                "received": True,
                "processed": False,
            }

        order = db.get(
            Order,
            transaction.order_id,
        )

        if order is None:
            event.processing_error = (
                "Payment transaction order not found."
            )
            db.commit()

            return {
                "received": True,
                "processed": False,
            }

        transaction.status = (
            PaymentStatus.SUCCEEDED
        )
        transaction.provider_status = (
            response_code
        )
        transaction.failure_reason = None
        transaction.confirmed_at = now

        if provider_transaction_id:
            transaction.provider_transaction_id = (
                provider_transaction_id
            )

        order.payment_amount = received
        order.payment_method = "momo"
        order.payment_reference = (
            provider_transaction_id
            or client_reference
        )
        order.payment_notes = (
            "Confirmed automatically by "
            "Hubtel collection callback."
        )
        order.payment_confirmed_at = now

        if order.status == OrderStatus.AWAITING_PAYMENT:
            order.status = (
                OrderStatus.PAYMENT_CONFIRMED
            )
        elif order.status in {
            OrderStatus.CANCELLED,
            OrderStatus.FAILED,
        }:
            # Money really arrived, so the transaction is
            # successful, but a cancelled/failed order must
            # not silently restart fulfilment.
            event.processing_error = (
                "Payment received for a cancelled "
                "or failed order. Reconciliation required."
            )

        event.is_processed = True
        event.processed_at = now

        db.commit()

        return {
            "received": True,
            "processed": True,
            "payment_confirmed": True,
            "order_id": order.id,
        }

    if response_code == "2001":
        transaction.status = (
            PaymentStatus.FAILED
        )
        transaction.provider_status = (
            response_code
        )
        transaction.failure_reason = str(
            data.get("Description")
            or payload.get("Message")
            or "Payment failed."
        )

        if provider_transaction_id:
            transaction.provider_transaction_id = (
                provider_transaction_id
            )

        event.is_processed = True
        event.processed_at = now

        db.commit()

        return {
            "received": True,
            "processed": True,
            "payment_confirmed": False,
        }

    # Anything we don't recognize remains unresolved.
    # Never interpret an unknown result as success.
    transaction.status = PaymentStatus.PENDING
    transaction.provider_status = (
        response_code or "unknown"
    )

    event.is_processed = True
    event.processed_at = now
    event.processing_error = (
        "Unresolved Hubtel result; "
        "status reconciliation required."
    )

    db.commit()

    return {
        "received": True,
        "processed": True,
        "payment_confirmed": False,
        "reconciliation_required": True,
    }


@router.post(
    "/transactions/{transaction_id}/reconcile",
)
def reconcile_customer_payment(
    transaction_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    require_payment_operator(
        request,
        db,
    )

    transaction = db.get(
        PaymentTransaction,
        transaction_id,
    )

    if transaction is None:
        raise HTTPException(
            status_code=404,
            detail="Payment transaction not found.",
        )

    if transaction.status == PaymentStatus.SUCCEEDED:
        return {
            "payment_transaction_id": transaction.id,
            "status": "succeeded",
            "already_final": True,
        }

    try:
        result = hubtel.check_collection_status(
            client_reference=
                transaction.client_reference,
        )
    except HubtelError as exc:
        raise HTTPException(
            status_code=502,
            detail=str(exc),
        ) from exc

    data = (
        result.get("data")
        or result.get("Data")
        or {}
    )

    if not isinstance(data, dict):
        raise HTTPException(
            status_code=502,
            detail="Unexpected Hubtel status response.",
        )

    provider_status = str(
        data.get("status")
        or data.get("Status")
        or ""
    ).strip()

    returned_reference = str(
        data.get("clientReference")
        or data.get("ClientReference")
        or ""
    ).strip()

    if (
        returned_reference
        and returned_reference
        != transaction.client_reference
    ):
        raise HTTPException(
            status_code=409,
            detail="Hubtel client reference mismatch.",
        )

    provider_transaction_id = str(
        data.get("transactionId")
        or data.get("TransactionId")
        or data.get("transactionID")
        or ""
    ).strip()

    now = datetime.utcnow()

    event_key = (
        "reconcile:"
        + transaction.client_reference
        + ":"
        + provider_status.lower()
        + ":"
        + provider_transaction_id
    )

    event = db.scalars(
        select(PaymentEvent).where(
            PaymentEvent.provider_event_id
            == event_key
        )
    ).first()

    if event is None:
        event = PaymentEvent(
            provider="hubtel",
            provider_event_id=event_key,
            event_type="collection_reconciliation",
            payment_transaction_id=transaction.id,
            raw_payload=json.dumps(
                result,
                sort_keys=True,
                default=str,
            ),
            is_processed=False,
        )
        db.add(event)

    normalized_status = provider_status.lower()

    if normalized_status == "paid":
        raw_amount = (
            data.get("amount")
            if "amount" in data
            else data.get("Amount")
        )

        if raw_amount is None:
            event.processing_error = (
                "Paid status returned without amount."
            )
            db.commit()

            raise HTTPException(
                status_code=409,
                detail=(
                    "Hubtel reports Paid but returned no "
                    "amount. Manual reconciliation required."
                ),
            )

        received = Decimal(
            str(raw_amount)
        ).quantize(
            Decimal("0.01")
        )

        expected = Decimal(
            str(transaction.amount)
        ).quantize(
            Decimal("0.01")
        )

        if received != expected:
            event.processing_error = (
                "Reconciled payment amount mismatch."
            )
            db.commit()

            raise HTTPException(
                status_code=409,
                detail={
                    "message":
                        "Hubtel payment amount mismatch.",
                    "expected":
                        str(expected),
                    "received":
                        str(received),
                },
            )

        order = db.get(
            Order,
            transaction.order_id,
        )

        if order is None:
            raise HTTPException(
                status_code=409,
                detail="Payment order no longer exists.",
            )

        transaction.status = PaymentStatus.SUCCEEDED
        transaction.provider_status = provider_status
        transaction.failure_reason = None
        transaction.confirmed_at = now

        if provider_transaction_id:
            transaction.provider_transaction_id = (
                provider_transaction_id
            )

        order.payment_amount = received
        order.payment_method = "momo"
        order.payment_reference = (
            provider_transaction_id
            or transaction.client_reference
        )
        order.payment_notes = (
            "Confirmed automatically by "
            "Hubtel status reconciliation."
        )
        order.payment_confirmed_at = now

        if order.status == OrderStatus.AWAITING_PAYMENT:
            order.status = (
                OrderStatus.PAYMENT_CONFIRMED
            )

        event.is_processed = True
        event.processed_at = now

        db.commit()

        return {
            "payment_transaction_id":
                transaction.id,
            "order_id":
                order.id,
            "status":
                "succeeded",
            "payment_confirmed":
                True,
        }

    if normalized_status in {
        "failed",
        "cancelled",
        "canceled",
        "declined",
    }:
        transaction.status = PaymentStatus.FAILED
        transaction.provider_status = provider_status
        transaction.failure_reason = (
            "Payment resolved as "
            + provider_status
            + "."
        )

        event.is_processed = True
        event.processed_at = now

        db.commit()

        return {
            "payment_transaction_id":
                transaction.id,
            "status":
                "failed",
            "payment_confirmed":
                False,
        }

    transaction.status = PaymentStatus.PENDING
    transaction.provider_status = (
        provider_status or "unknown"
    )

    event.is_processed = True
    event.processed_at = now

    db.commit()

    return {
        "payment_transaction_id":
            transaction.id,
        "status":
            "pending",
        "provider_status":
            provider_status or "unknown",
        "payment_confirmed":
            False,
    }


class PayoutProfileCreateRequest(BaseModel):
    recipient_type: PayoutRecipientType
    supplier_id: int | None = None
    driver_id: int | None = None
    payment_phone: str = Field(
        min_length=10,
        max_length=30,
    )
    payment_name: str = Field(
        min_length=2,
        max_length=160,
    )
    network: str = Field(
        min_length=2,
        max_length=40,
    )
    notes: str | None = None


def require_payout_profile_manager(
    request: Request,
    db: Session,
) -> User:
    user_id = current_user_id(request)

    user = db.get(
        User,
        user_id,
    )

    if (
        user is None
        or not user.is_active
        or user.role != Role.ADMIN
    ):
        raise HTTPException(
            status_code=403,
            detail=(
                "Administrator access required "
                "for payout profiles."
            ),
        )

    return user


@router.get(
    "/payout-setup",
)
def payout_setup(
    request: Request,
    db: Session = Depends(get_db),
):
    require_payout_profile_manager(
        request,
        db,
    )

    suppliers = list(
        db.scalars(
            select(Supplier)
            .order_by(
                Supplier.name.asc()
            )
        ).all()
    )

    drivers = list(
        db.scalars(
            select(Driver)
            .where(
                Driver.is_active.is_(True)
            )
            .order_by(
                Driver.name.asc()
            )
        ).all()
    )

    profiles = list(
        db.scalars(
            select(PayoutProfile)
            .order_by(
                PayoutProfile.id.desc()
            )
        ).all()
    )

    return {
        "suppliers": [
            {
                "id": item.id,
                "name": item.name,
                "phone": item.phone,
            }
            for item in suppliers
        ],

        "drivers": [
            {
                "id": item.id,
                "name": item.name,
                "phone": item.phone,
                "payment_phone":
                    item.payment_phone,
                "payment_name":
                    item.payment_name,
            }
            for item in drivers
        ],

        "profiles": [
            {
                "id":
                    profile.id,

                "recipient_type":
                    profile.recipient_type.value,

                "supplier_id":
                    profile.supplier_id,

                "driver_id":
                    profile.driver_id,

                "payment_name":
                    profile.payment_name,

                "payment_phone":
                    profile.payment_phone,

                "network":
                    profile.network,

                "is_verified":
                    profile.is_verified,

                "is_locked":
                    profile.is_locked,

                "is_active":
                    profile.is_active,

                "version":
                    profile.version,
            }
            for profile in profiles
        ],
    }


@router.post(
    "/payout-profiles",
    status_code=status.HTTP_201_CREATED,
)
def create_payout_profile(
    payload: PayoutProfileCreateRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    actor = require_payout_profile_manager(
        request,
        db,
    )

    supplier_id = payload.supplier_id
    driver_id = payload.driver_id

    if payload.recipient_type == PayoutRecipientType.SUPPLIER:
        if supplier_id is None or driver_id is not None:
            raise HTTPException(
                status_code=400,
                detail=(
                    "Supplier payout profile must have "
                    "supplier_id only."
                ),
            )

        supplier = db.get(
            Supplier,
            supplier_id,
        )

        if supplier is None:
            raise HTTPException(
                status_code=404,
                detail="Supplier not found.",
            )

    elif payload.recipient_type == PayoutRecipientType.DRIVER:
        if driver_id is None or supplier_id is not None:
            raise HTTPException(
                status_code=400,
                detail=(
                    "Driver payout profile must have "
                    "driver_id only."
                ),
            )

        driver = db.get(
            Driver,
            driver_id,
        )

        if driver is None:
            raise HTTPException(
                status_code=404,
                detail="Driver not found.",
            )

    existing_query = select(PayoutProfile).where(
        PayoutProfile.is_active.is_(True),
    )

    if supplier_id is not None:
        existing_query = existing_query.where(
            PayoutProfile.supplier_id == supplier_id
        )

    if driver_id is not None:
        existing_query = existing_query.where(
            PayoutProfile.driver_id == driver_id
        )

    existing = db.scalars(
        existing_query
    ).first()

    if existing is not None:
        raise HTTPException(
            status_code=409,
            detail={
                "message":
                    "Recipient already has an active payout profile.",
                "payout_profile_id":
                    existing.id,
            },
        )

    try:
        phone = normalize_ghana_phone(
            payload.payment_phone
        )
        network = normalize_momo_channel(
            payload.network
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

    profile = PayoutProfile(
        recipient_type=payload.recipient_type,
        supplier_id=supplier_id,
        driver_id=driver_id,
        provider="hubtel",
        destination_type="momo",
        payment_phone=phone,
        payment_name=payload.payment_name.strip(),
        network=network,
        is_verified=False,
        is_locked=False,
        is_active=True,
        version=1,
        notes=payload.notes,
    )

    db.add(profile)
    db.commit()
    db.refresh(profile)

    return {
        "payout_profile_id":
            profile.id,
        "recipient_type":
            profile.recipient_type.value,
        "supplier_id":
            profile.supplier_id,
        "driver_id":
            profile.driver_id,
        "payment_phone":
            profile.payment_phone,
        "payment_name":
            profile.payment_name,
        "network":
            profile.network,
        "is_verified":
            profile.is_verified,
        "is_locked":
            profile.is_locked,
        "created_by":
            actor.id,
    }


@router.post(
    "/payout-profiles/{profile_id}/manual-verify-and-lock",
)
def manual_verify_and_lock_payout_profile(
    profile_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    actor = require_payout_profile_manager(
        request,
        db,
    )

    profile = db.get(
        PayoutProfile,
        profile_id,
    )

    if profile is None:
        raise HTTPException(
            status_code=404,
            detail="Payout profile not found.",
        )

    if not profile.is_active:
        raise HTTPException(
            status_code=409,
            detail="Payout profile is inactive.",
        )

    if (
        profile.is_verified
        and profile.is_locked
    ):
        return {
            "id": profile.id,
            "verified": True,
            "locked": True,
            "already_locked": True,
        }

    now = datetime.utcnow()

    profile.is_verified = True
    profile.verified_at = now
    profile.verified_by_id = actor.id

    profile.is_locked = True
    profile.locked_at = now
    profile.locked_by_id = actor.id

    existing_notes = (
        profile.notes.strip()
        if profile.notes
        else ""
    )

    manual_note = (
        "Manually verified and locked by "
        "StoreDash admin for temporary launch."
    )

    profile.notes = (
        f"{existing_notes}\n{manual_note}".strip()
    )

    db.commit()
    db.refresh(profile)

    return {
        "id":
            profile.id,

        "recipient_type":
            profile.recipient_type.value,

        "supplier_id":
            profile.supplier_id,

        "driver_id":
            profile.driver_id,

        "payment_name":
            profile.payment_name,

        "payment_phone":
            profile.payment_phone,

        "network":
            profile.network,

        "verified":
            profile.is_verified,

        "locked":
            profile.is_locked,

        "verified_by_id":
            profile.verified_by_id,

        "locked_by_id":
            profile.locked_by_id,

        "manual_launch_verification":
            True,
    }


@router.post(
    "/payout-profiles/{profile_id}/verify-and-lock",
)
def verify_and_lock_payout_profile(
    profile_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    actor = require_payout_profile_manager(
        request,
        db,
    )

    profile = db.get(
        PayoutProfile,
        profile_id,
    )

    if profile is None:
        raise HTTPException(
            status_code=404,
            detail="Payout profile not found.",
        )

    if not profile.is_active:
        raise HTTPException(
            status_code=409,
            detail="Payout profile is inactive.",
        )

    if profile.is_locked:
        return {
            "payout_profile_id":
                profile.id,
            "is_verified":
                profile.is_verified,
            "is_locked":
                True,
            "payment_name":
                profile.payment_name,
            "payment_phone":
                profile.payment_phone,
        }

    try:
        result = hubtel.verify_mobile_wallet(
            phone=profile.payment_phone,
            channel=profile.network or "",
        )
    except HubtelError as exc:
        raise HTTPException(
            status_code=502,
            detail=str(exc),
        ) from exc

    response_code = str(
        result.get("responseCode")
        or result.get("ResponseCode")
        or ""
    )

    data = (
        result.get("data")
        or result.get("Data")
        or {}
    )

    if not isinstance(data, dict):
        raise HTTPException(
            status_code=502,
            detail="Unexpected wallet verification response.",
        )

    is_registered = bool(
        data.get("isRegistered")
    )

    wallet_status = str(
        data.get("status")
        or ""
    ).lower()

    registered_name = str(
        data.get("name")
        or ""
    ).strip()

    if response_code != "0000":
        raise HTTPException(
            status_code=409,
            detail=(
                "Hubtel could not verify this wallet."
            ),
        )

    if not is_registered:
        raise HTTPException(
            status_code=409,
            detail=(
                "This number is not registered "
                "for Mobile Money."
            ),
        )

    if wallet_status and wallet_status != "active":
        raise HTTPException(
            status_code=409,
            detail=(
                "The Mobile Money wallet is not active."
            ),
        )

    if not registered_name:
        raise HTTPException(
            status_code=409,
            detail=(
                "Wallet verification returned no "
                "registered account name."
            ),
        )

    now = datetime.utcnow()

    # Hubtel becomes the authoritative wallet name.
    profile.payment_name = registered_name
    profile.is_verified = True
    profile.verified_at = now
    profile.verified_by_id = actor.id

    # Lock means normal staff workflows have no path
    # for changing destination information.
    profile.is_locked = True
    profile.locked_at = now
    profile.locked_by_id = actor.id

    db.commit()
    db.refresh(profile)

    return {
        "payout_profile_id":
            profile.id,
        "recipient_type":
            profile.recipient_type.value,
        "payment_phone":
            profile.payment_phone,
        "payment_name":
            profile.payment_name,
        "network":
            profile.network,
        "is_verified":
            profile.is_verified,
        "is_locked":
            profile.is_locked,
    }


@router.post(
    "/orders/{order_id}/supplier-payouts/prepare",
)
def prepare_supplier_payouts(
    order_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    require_payment_operator(
        request,
        db,
    )

    order = db.get(
        Order,
        order_id,
    )

    if order is None:
        raise HTTPException(
            status_code=404,
            detail="Order not found.",
        )

    if order.payment_confirmed_at is None:
        raise HTTPException(
            status_code=409,
            detail=(
                "Customer payment must be confirmed "
                "before supplier payouts are created."
            ),
        )

    if order.status in {
        OrderStatus.CANCELLED,
        OrderStatus.FAILED,
    }:
        raise HTTPException(
            status_code=409,
            detail=(
                "Supplier payouts cannot be prepared "
                "for a cancelled or failed order."
            ),
        )

    totals: dict[int, Decimal] = {}

    for item in order.items:
        if item.availability_status not in {
            "available",
            "partial",
        }:
            continue

        if item.supplier_id is None:
            raise HTTPException(
                status_code=409,
                detail=(
                    f"{item.name}: supplier missing."
                ),
            )

        if (
            item.confirmed_quantity is None
            or item.confirmed_price is None
        ):
            raise HTTPException(
                status_code=409,
                detail=(
                    f"{item.name}: confirmed quantity "
                    "or supplier price missing."
                ),
            )

        quantity = Decimal(
            str(item.confirmed_quantity)
        )

        price = Decimal(
            str(item.confirmed_price)
        )

        line_total = (
            quantity * price
        ).quantize(
            Decimal("0.01")
        )

        if line_total <= 0:
            raise HTTPException(
                status_code=409,
                detail=(
                    f"{item.name}: invalid supplier total."
                ),
            )

        totals[item.supplier_id] = (
            totals.get(
                item.supplier_id,
                Decimal("0.00"),
            )
            + line_total
        )

    if not totals:
        raise HTTPException(
            status_code=409,
            detail=(
                "Order has no supplier goods "
                "eligible for payout."
            ),
        )

    created = []
    existing = []

    for supplier_id, amount in totals.items():
        supplier = db.get(
            Supplier,
            supplier_id,
        )

        if supplier is None:
            raise HTTPException(
                status_code=409,
                detail=(
                    f"Supplier {supplier_id} "
                    "no longer exists."
                ),
            )

        profile = db.scalars(
            select(PayoutProfile)
            .where(
                PayoutProfile.supplier_id
                == supplier_id,
                PayoutProfile.recipient_type
                == PayoutRecipientType.SUPPLIER,
                PayoutProfile.is_active.is_(True),
            )
            .order_by(
                PayoutProfile.version.desc()
            )
        ).first()

        if profile is None:
            raise HTTPException(
                status_code=409,
                detail=(
                    f"{supplier.name} has no active "
                    "payout profile."
                ),
            )

        if (
            not profile.is_verified
            or not profile.is_locked
        ):
            raise HTTPException(
                status_code=409,
                detail=(
                    f"{supplier.name} payout profile "
                    "is not verified and locked."
                ),
            )

        prior = db.scalars(
            select(Payout).where(
                Payout.order_id == order.id,
                Payout.supplier_id == supplier_id,
                Payout.recipient_type
                == PayoutRecipientType.SUPPLIER,
                Payout.reason == "supplier_goods",
                Payout.status
                != PayoutStatus.CANCELLED,
            )
        ).first()

        if prior is not None:
            existing.append({
                "payout_id":
                    prior.id,
                "supplier_id":
                    supplier_id,
                "supplier_name":
                    supplier.name,
                "amount":
                    str(prior.amount),
                "status":
                    prior.status.value,
            })
            continue

        client_reference = (
            f"sds-{order.id}-{supplier_id}-"
            f"{uuid4().hex[:12]}"
        )

        payout = Payout(
            payout_profile_id=profile.id,
            recipient_type=
                PayoutRecipientType.SUPPLIER,
            supplier_id=supplier_id,
            driver_id=None,
            order_id=order.id,
            delivery_batch_id=None,
            amount=amount.quantize(
                Decimal("0.01")
            ),
            currency="GHS",
            reason="supplier_goods",
            client_reference=client_reference,
            status=
                PayoutStatus.PENDING_APPROVAL,
        )

        db.add(payout)
        db.flush()

        created.append({
            "payout_id":
                payout.id,
            "supplier_id":
                supplier.id,
            "supplier_name":
                supplier.name,
            "amount":
                str(payout.amount),
            "status":
                payout.status.value,
            "destination":
                "****"
                + profile.payment_phone[-4:],
        })

    db.commit()

    return {
        "order_id":
            order.id,
        "created":
            created,
        "existing":
            existing,
    }


@router.post(
    "/payouts/{payout_id}/approve",
)
def approve_supplier_payout(
    payout_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    actor = require_finance_manager(
        request,
        db,
    )

    payout = db.get(
        Payout,
        payout_id,
    )

    if payout is None:
        raise HTTPException(
            status_code=404,
            detail="Payout not found.",
        )

    if (
        payout.recipient_type
        != PayoutRecipientType.SUPPLIER
    ):
        raise HTTPException(
            status_code=409,
            detail=(
                "This endpoint only approves "
                "supplier payouts."
            ),
        )

    if (
        payout.status
        != PayoutStatus.PENDING_APPROVAL
    ):
        raise HTTPException(
            status_code=409,
            detail={
                "message":
                    "Payout is not awaiting approval.",
                "status":
                    payout.status.value,
            },
        )

    profile = db.get(
        PayoutProfile,
        payout.payout_profile_id,
    )

    if profile is None:
        raise HTTPException(
            status_code=409,
            detail="Payout profile no longer exists.",
        )

    if (
        not profile.is_active
        or not profile.is_verified
        or not profile.is_locked
    ):
        raise HTTPException(
            status_code=409,
            detail=(
                "Payout destination is not an active, "
                "verified and locked profile."
            ),
        )

    if (
        profile.recipient_type
        != PayoutRecipientType.SUPPLIER
        or profile.supplier_id
        != payout.supplier_id
    ):
        raise HTTPException(
            status_code=409,
            detail=(
                "Payout destination does not match "
                "the supplier."
            ),
        )

    amount = Decimal(
        str(payout.amount)
    ).quantize(
        Decimal("0.01")
    )

    if amount <= 0:
        raise HTTPException(
            status_code=409,
            detail="Invalid payout amount.",
        )

    now = datetime.utcnow()

    # Lock the approval BEFORE contacting the provider.
    # This prevents a double-click or concurrent request
    # from sending the same payout twice.
    payout.approved_by_id = actor.id
    payout.approved_at = now
    payout.initiated_at = now
    payout.status = PayoutStatus.PROCESSING

    db.commit()

    callback_url = (
        settings.hubtel_callback_base_url.rstrip("/")
        + "/api/payments/hubtel/payouts/callback"
    )

    try:
        result = hubtel.send_money(
            recipient_name=
                profile.payment_name,
            recipient_phone=
                profile.payment_phone,
            channel=
                profile.network or "",
            amount=
                amount,
            description=(
                f"StoreDash supplier payout "
                f"#{payout.id}"
            ),
            client_reference=
                payout.client_reference,
            callback_url=
                callback_url,
        )
    except HubtelError as exc:
        # Outcome could be unknown after timeout.
        # Keep PROCESSING so nobody can approve/send
        # this payout again blindly.
        payout.failure_reason = (
            "Provider result unresolved: "
            + str(exc)
        )
        db.commit()

        raise HTTPException(
            status_code=502,
            detail={
                "message":
                    "Payout result is unresolved. "
                    "Do not resend this payout.",
                "payout_id":
                    payout.id,
                "client_reference":
                    payout.client_reference,
            },
        ) from exc

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
        payout.status = (
            PayoutStatus.PROCESSING
        )
        payout.failure_reason = None

    elif response_code == "2001":
        payout.status = (
            PayoutStatus.FAILED
        )
        payout.failure_reason = str(
            data.get("Description")
            or result.get("Message")
            or "Provider rejected payout."
        )

    else:
        # Unknown result is never treated as success.
        payout.status = (
            PayoutStatus.PROCESSING
        )
        payout.failure_reason = (
            "Unexpected provider response; "
            "reconciliation required."
        )

    db.commit()
    db.refresh(payout)

    return {
        "payout_id":
            payout.id,
        "supplier_id":
            payout.supplier_id,
        "amount":
            str(payout.amount),
        "status":
            payout.status.value,
        "client_reference":
            payout.client_reference,
        "destination":
            "****"
            + profile.payment_phone[-4:],
    }


class ExternalPayoutRecordRequest(BaseModel):
    transaction_reference: str = Field(
        min_length=1,
        max_length=100,
    )


@router.post(
    "/payouts/{payout_id}/record-external",
)
def record_external_payout(
    payout_id: int,
    payload: ExternalPayoutRecordRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    actor = require_finance_manager(
        request,
        db,
    )

    payout = db.get(
        Payout,
        payout_id,
    )

    if payout is None:
        raise HTTPException(
            status_code=404,
            detail="Payout not found.",
        )

    if (
        payout.status
        == PayoutStatus.SUCCEEDED
    ):
        return {
            "id": payout.id,
            "status": payout.status.value,
            "already_recorded": True,
        }

    if (
        payout.status
        == PayoutStatus.CANCELLED
    ):
        raise HTTPException(
            status_code=409,
            detail=(
                "Cancelled payout cannot "
                "be recorded as paid."
            ),
        )

    profile = db.get(
        PayoutProfile,
        payout.payout_profile_id,
    )

    if (
        profile is None
        or not profile.is_active
        or not profile.is_verified
        or not profile.is_locked
    ):
        raise HTTPException(
            status_code=409,
            detail=(
                "Payout recipient does not have "
                "an active verified locked profile."
            ),
        )

    reference = (
        payload.transaction_reference
        .strip()
    )

    manual_reference = (
        f"manual:{reference}"
    )

    duplicate = db.scalars(
        select(Payout)
        .where(
            Payout.provider_transaction_id
            == manual_reference,

            Payout.id
            != payout.id,
        )
    ).first()

    if duplicate is not None:
        raise HTTPException(
            status_code=409,
            detail=(
                "That external transaction "
                "reference has already been used."
            ),
        )

    now = datetime.utcnow()

    payout.provider_transaction_id = (
        manual_reference
    )

    payout.approved_by_id = (
        actor.id
    )

    if payout.approved_at is None:
        payout.approved_at = now

    if payout.initiated_at is None:
        payout.initiated_at = now

    payout.completed_at = now
    payout.status = PayoutStatus.SUCCEEDED
    payout.failure_reason = None

    db.commit()
    db.refresh(payout)

    return {
        "id": payout.id,

        "status":
            payout.status.value,

        "transaction_reference":
            reference,

        "completed_at":
            payout.completed_at.isoformat()
            if payout.completed_at
            else None,
    }


@router.post(
    "/hubtel/payouts/callback",
)
def hubtel_payout_callback(
    payload: dict[str, Any],
    db: Session = Depends(get_db),
):
    response_code = str(
        payload.get("ResponseCode", "")
    ).strip()

    data = payload.get("Data") or {}

    if not isinstance(data, dict):
        data = {}

    client_reference = str(
        data.get("ClientReference", "")
    ).strip()

    provider_transaction_id = str(
        data.get("TransactionId", "")
        or data.get("TransactionID", "")
    ).strip()

    if provider_transaction_id:
        provider_event_id = (
            "payout:"
            + provider_transaction_id
            + ":"
            + (response_code or "unknown")
        )
    else:
        canonical = json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
            default=str,
        )

        provider_event_id = (
            "payout:"
            + hashlib.sha256(
                canonical.encode("utf-8")
            ).hexdigest()
        )

    existing_event = db.scalars(
        select(PaymentEvent).where(
            PaymentEvent.provider_event_id
            == provider_event_id
        )
    ).first()

    if existing_event is not None:
        return {
            "received": True,
            "duplicate": True,
        }

    payout = None

    if client_reference:
        payout = db.scalars(
            select(Payout).where(
                Payout.client_reference
                == client_reference
            )
        ).first()

    event = PaymentEvent(
        provider="hubtel",
        provider_event_id=provider_event_id,
        event_type="payout_callback",
        payout_id=(
            payout.id
            if payout is not None
            else None
        ),
        raw_payload=json.dumps(
            payload,
            sort_keys=True,
            default=str,
        ),
        is_processed=False,
    )

    db.add(event)

    now = datetime.utcnow()

    if payout is None:
        event.processing_error = (
            "Unknown or missing payout ClientReference."
        )
        db.commit()

        return {
            "received": True,
            "processed": False,
        }

    if payout.status == PayoutStatus.SUCCEEDED:
        event.is_processed = True
        event.processed_at = now
        db.commit()

        return {
            "received": True,
            "processed": True,
            "already_completed": True,
        }

    if (
        payout.provider_transaction_id
        and provider_transaction_id
        and payout.provider_transaction_id
        != provider_transaction_id
    ):
        event.processing_error = (
            "Provider transaction ID mismatch."
        )
        db.commit()

        return {
            "received": True,
            "processed": False,
        }

    if response_code == "0000":
        raw_amount = data.get("Amount")

        if raw_amount is None:
            event.processing_error = (
                "Successful payout callback "
                "has no amount."
            )
            db.commit()

            return {
                "received": True,
                "processed": False,
            }

        received = Decimal(
            str(raw_amount)
        ).quantize(
            Decimal("0.01")
        )

        expected = Decimal(
            str(payout.amount)
        ).quantize(
            Decimal("0.01")
        )

        if received != expected:
            event.processing_error = (
                "Payout callback amount mismatch."
            )
            db.commit()

            return {
                "received": True,
                "processed": False,
            }

        payout.status = PayoutStatus.SUCCEEDED
        payout.completed_at = now
        payout.failure_reason = None

        if provider_transaction_id:
            payout.provider_transaction_id = (
                provider_transaction_id
            )

        event.is_processed = True
        event.processed_at = now

        db.commit()

        return {
            "received": True,
            "processed": True,
            "payout_completed": True,
            "payout_id": payout.id,
        }

    if response_code == "2001":
        payout.status = PayoutStatus.FAILED

        payout.failure_reason = str(
            data.get("Description")
            or payload.get("Message")
            or "Payout failed."
        )

        if provider_transaction_id:
            payout.provider_transaction_id = (
                provider_transaction_id
            )

        event.is_processed = True
        event.processed_at = now

        db.commit()

        return {
            "received": True,
            "processed": True,
            "payout_completed": False,
        }

    # Unknown result stays unresolved.
    payout.status = PayoutStatus.PROCESSING

    event.is_processed = True
    event.processed_at = now
    event.processing_error = (
        "Unresolved payout result."
    )

    db.commit()

    return {
        "received": True,
        "processed": True,
        "payout_completed": False,
        "reconciliation_required": True,
    }


# ============================================================
# TEMPORARY STOREDASH PAYMENT-PHONE SMS RELAY
# ============================================================


class ExpectedSmsPaymentRequest(BaseModel):
    customer_phone: str = Field(
        min_length=10,
        max_length=30,
    )

    network: str = Field(
        default="momo",
        min_length=2,
        max_length=40,
    )


class SmsRelayEventRequest(BaseModel):
    sender: str = Field(
        min_length=1,
        max_length=100,
    )

    body: str = Field(
        min_length=1,
    )

    received_at: str = Field(
        min_length=1,
        max_length=80,
    )

    device_id: str | None = Field(
        default=None,
        max_length=100,
    )


@router.post(
    "/orders/{order_id}/expect-sms-payment",
    status_code=status.HTTP_201_CREATED,
)
def expect_sms_payment(
    order_id: int,
    payload: ExpectedSmsPaymentRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    require_payment_operator(
        request,
        db,
    )

    order = db.get(
        Order,
        order_id,
    )

    if order is None:
        raise HTTPException(
            status_code=404,
            detail="Order not found.",
        )

    if (
        order.status
        != OrderStatus.AWAITING_PAYMENT
    ):
        raise HTTPException(
            status_code=409,
            detail=(
                "Order is not awaiting payment."
            ),
        )

    if order.customer_approved_at is None:
        raise HTTPException(
            status_code=409,
            detail=(
                "Customer approval has not "
                "been recorded."
            ),
        )

    amount = Decimal(
        str(
            order.final_total
            or 0
        )
    ).quantize(
        Decimal("0.01")
    )

    if amount <= 0:
        raise HTTPException(
            status_code=409,
            detail=(
                "Order has no valid payable total."
            ),
        )

    phone = normalize_ghana_phone(
        payload.customer_phone
    )

    existing = db.scalars(
        select(
            PaymentTransaction
        )
        .where(
            PaymentTransaction.order_id
            == order.id,

            PaymentTransaction.status.in_(
                {
                    PaymentStatus.INITIATED,
                    PaymentStatus.PENDING,
                    PaymentStatus.SUCCEEDED,
                }
            ),
        )
        .order_by(
            PaymentTransaction.id.desc()
        )
    ).first()

    if existing is not None:
        return {
            "transaction_id":
                existing.id,

            "status":
                existing.status.value,

            "amount":
                str(existing.amount),

            "payer_phone":
                existing.payer_phone,

            "already_exists":
                True,
        }

    transaction = PaymentTransaction(
        order_id=
            order.id,

        provider=
            "sms_relay",

        client_reference=
            (
                f"sms-{order.id}-"
                f"{uuid4().hex[:16]}"
            ),

        amount=
            amount,

        currency=
            "GHS",

        payment_method=
            payload.network
            .strip()
            .lower(),

        payer_phone=
            phone,

        status=
            PaymentStatus.PENDING,

        provider_status=
            "awaiting_sms",

        initiated_at=
            datetime.utcnow(),
    )

    db.add(transaction)
    db.commit()
    db.refresh(transaction)

    return {
        "transaction_id":
            transaction.id,

        "status":
            transaction.status.value,

        "amount":
            str(transaction.amount),

        "payer_phone":
            transaction.payer_phone,

        "already_exists":
            False,
    }


@router.post(
    "/sms-relay/events",
    status_code=status.HTTP_202_ACCEPTED,
)
def receive_sms_relay_event(
    payload: SmsRelayEventRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    if not settings.sms_relay_enabled:
        raise HTTPException(
            status_code=503,
            detail=(
                "StoreDash SMS relay is disabled."
            ),
        )

    expected_key = (
        settings.sms_relay_key
        .strip()
    )

    supplied_key = (
        request.headers.get(
            "X-StoreDash-Relay-Key",
            "",
        )
        .strip()
    )

    if (
        not expected_key
        or not supplied_key
        or not hmac.compare_digest(
            expected_key,
            supplied_key,
        )
    ):
        raise HTTPException(
            status_code=401,
            detail="Invalid SMS relay credentials.",
        )

    allowed = {
        item.strip().lower()
        for item in (
            settings
            .sms_relay_allowed_senders
            .split(",")
        )
        if item.strip()
    }

    sender = (
        payload.sender
        .strip()
        .lower()
    )

    if not allowed:
        raise HTTPException(
            status_code=503,
            detail=(
                "SMS relay sender allowlist "
                "has not been configured."
            ),
        )

    if sender not in allowed:
        return {
            "accepted": False,
            "ignored": True,
            "reason":
                "Sender is not an approved "
                "payment-message sender.",
        }

    fingerprint = message_fingerprint(
        sender=payload.sender,
        body=payload.body,
        received_at=payload.received_at,
    )

    duplicate_event = db.scalars(
        select(
            PaymentEvent
        )
        .where(
            PaymentEvent.provider_event_id
            == fingerprint
        )
    ).first()

    if duplicate_event is not None:
        return {
            "accepted": True,
            "duplicate": True,
        }

    parsed = parse_money_sms(
        payload.body
    )

    event = PaymentEvent(
        provider=
            "sms_relay",

        provider_event_id=
            fingerprint,

        event_type=
            (
                f"sms_{parsed.direction}"
                if parsed
                else "sms_ignored"
            ),

        raw_payload=
            json.dumps(
                payload.model_dump(),
                sort_keys=True,
            ),

        is_processed=
            False,
    )

    db.add(event)
    db.flush()

    if parsed is None:
        event.processing_error = (
            "Message did not match a supported "
            "money-transfer format."
        )

        db.commit()

        return {
            "accepted": True,
            "matched": False,
            "reason":
                event.processing_error,
        }

    if (
        parsed.transaction_reference
        is None
    ):
        event.processing_error = (
            "Payment SMS has no transaction reference."
        )

        db.commit()

        return {
            "accepted": True,
            "matched": False,
            "reason":
                event.processing_error,
        }

    now = datetime.utcnow()

    # --------------------------------------------------------
    # INCOMING CUSTOMER PAYMENT
    # --------------------------------------------------------

    if parsed.direction == "incoming":
        if parsed.phone is None:
            event.processing_error = (
                "Incoming payment has no usable "
                "payer phone number."
            )

            db.commit()

            return {
                "accepted": True,
                "matched": False,
                "reason":
                    event.processing_error,
            }

        candidates = list(
            db.scalars(
                select(
                    PaymentTransaction
                )
                .where(
                    PaymentTransaction.provider
                    == "sms_relay",

                    PaymentTransaction.payer_phone
                    == parsed.phone,

                    PaymentTransaction.amount
                    == parsed.amount,

                    PaymentTransaction.status.in_(
                        {
                            PaymentStatus.INITIATED,
                            PaymentStatus.PENDING,
                        }
                    ),
                )
                .order_by(
                    PaymentTransaction.id.desc()
                )
            ).all()
        )

        if len(candidates) != 1:
            event.processing_error = (
                "Incoming payment could not be "
                "matched uniquely to one order."
            )

            db.commit()

            return {
                "accepted": True,
                "matched": False,
                "candidate_count":
                    len(candidates),
                "reason":
                    event.processing_error,
            }

        transaction = candidates[0]

        provider_transaction_id = (
            "sms:"
            + parsed.transaction_reference
        )

        reused = db.scalars(
            select(
                PaymentTransaction
            )
            .where(
                PaymentTransaction.provider_transaction_id
                == provider_transaction_id,

                PaymentTransaction.id
                != transaction.id,
            )
        ).first()

        if reused is not None:
            event.processing_error = (
                "SMS transaction reference has "
                "already been used."
            )

            db.commit()

            return {
                "accepted": True,
                "matched": False,
                "reason":
                    event.processing_error,
            }

        order = db.get(
            Order,
            transaction.order_id,
        )

        if (
            order is None
            or order.status
            != OrderStatus.AWAITING_PAYMENT
        ):
            event.processing_error = (
                "Matched order is no longer "
                "awaiting payment."
            )

            db.commit()

            return {
                "accepted": True,
                "matched": False,
                "reason":
                    event.processing_error,
            }

        transaction.status = (
            PaymentStatus.SUCCEEDED
        )

        transaction.provider_status = (
            "sms_confirmed"
        )

        transaction.provider_transaction_id = (
            provider_transaction_id
        )

        transaction.confirmed_at = now

        transaction.failure_reason = None

        order.payment_amount = (
            transaction.amount
        )

        order.payment_method = (
            "sms_relay"
        )

        order.payment_reference = (
            parsed.transaction_reference
        )

        order.payment_notes = (
            "Automatically matched from "
            "the StoreDash payment phone."
        )

        order.payment_confirmed_at = now

        order.status = (
            OrderStatus.PAYMENT_CONFIRMED
        )

        event.payment_transaction_id = (
            transaction.id
        )

        event.is_processed = True
        event.processed_at = now
        event.processing_error = None

        db.commit()

        return {
            "accepted": True,
            "matched": True,
            "direction": "incoming",
            "order_id":
                order.id,
            "payment_transaction_id":
                transaction.id,
            "status":
                order.status.value,
        }

    # --------------------------------------------------------
    # OUTGOING SUPPLIER / DRIVER PAYMENT
    # --------------------------------------------------------

    if parsed.phone is None:
        event.processing_error = (
            "Outgoing payment has no usable "
            "recipient phone number."
        )

        db.commit()

        return {
            "accepted": True,
            "matched": False,
            "reason":
                event.processing_error,
        }

    possible_payouts = list(
        db.scalars(
            select(
                Payout
            )
            .where(
                Payout.amount
                == parsed.amount,

                Payout.status.in_(
                    {
                        PayoutStatus.PENDING_APPROVAL,
                        PayoutStatus.APPROVED,
                        PayoutStatus.PROCESSING,
                        PayoutStatus.FAILED,
                    }
                ),
            )
            .order_by(
                Payout.id.desc()
            )
        ).all()
    )

    matches = []

    for payout in possible_payouts:
        profile = db.get(
            PayoutProfile,
            payout.payout_profile_id,
        )

        if (
            profile is None
            or not profile.is_active
            or not profile.is_verified
            or not profile.is_locked
        ):
            continue

        profile_phone = (
            normalize_phone_from_text(
                profile.payment_phone
            )
        )

        if profile_phone == parsed.phone:
            matches.append(
                payout
            )

    if len(matches) != 1:
        event.processing_error = (
            "Outgoing payment could not be "
            "matched uniquely to one payout."
        )

        db.commit()

        return {
            "accepted": True,
            "matched": False,
            "candidate_count":
                len(matches),
            "reason":
                event.processing_error,
        }

    payout = matches[0]

    provider_transaction_id = (
        "sms:"
        + parsed.transaction_reference
    )

    reused = db.scalars(
        select(
            Payout
        )
        .where(
            Payout.provider_transaction_id
            == provider_transaction_id,

            Payout.id
            != payout.id,
        )
    ).first()

    if reused is not None:
        event.processing_error = (
            "SMS transaction reference has "
            "already been used."
        )

        db.commit()

        return {
            "accepted": True,
            "matched": False,
            "reason":
                event.processing_error,
        }

    payout.provider_transaction_id = (
        provider_transaction_id
    )

    if payout.approved_at is None:
        payout.approved_at = now

    if payout.initiated_at is None:
        payout.initiated_at = now

    payout.completed_at = now

    payout.status = (
        PayoutStatus.SUCCEEDED
    )

    payout.failure_reason = None

    event.payout_id = payout.id
    event.is_processed = True
    event.processed_at = now
    event.processing_error = None

    db.commit()

    return {
        "accepted": True,
        "matched": True,
        "direction": "outgoing",
        "payout_id":
            payout.id,
        "status":
            payout.status.value,
    }


# ============================================================
# SMS PAYMENT EXCEPTION REVIEW
# ============================================================


class ResolveSmsPaymentRequest(BaseModel):
    order_id: int = Field(
        gt=0,
    )


@router.get(
    "/sms-relay/verification",
)
def sms_relay_verification_queue(
    request: Request,
    db: Session = Depends(get_db),
):
    require_payment_operator(
        request,
        db,
    )

    events = list(
        db.scalars(
            select(PaymentEvent)
            .where(
                PaymentEvent.provider
                == "sms_relay",

                PaymentEvent.is_processed
                .is_(False),

                PaymentEvent.processing_error
                .is_not(None),
            )
            .order_by(
                PaymentEvent.id.desc()
            )
            .limit(50)
        ).all()
    )

    results = []

    for event in events:
        try:
            raw = json.loads(
                event.raw_payload
                or "{}"
            )
        except Exception:
            raw = {}

        parsed = parse_money_sms(
            str(
                raw.get(
                    "body",
                    "",
                )
            )
        )

        results.append(
            {
                "id":
                    event.id,

                "event_type":
                    event.event_type,

                "sender":
                    raw.get("sender"),

                "body":
                    raw.get("body"),

                "received_at":
                    raw.get(
                        "received_at"
                    ),

                "device_id":
                    raw.get(
                        "device_id"
                    ),

                "direction":
                    (
                        parsed.direction
                        if parsed
                        else None
                    ),

                "amount":
                    (
                        str(
                            parsed.amount
                        )
                        if parsed
                        else None
                    ),

                "phone":
                    (
                        parsed.phone
                        if parsed
                        else None
                    ),

                "transaction_reference":
                    (
                        parsed.transaction_reference
                        if parsed
                        else None
                    ),

                "reason":
                    event.processing_error,

                "can_resolve":
                    (
                        request.state.user_role
                        in {
                            Role.ADMIN.value,
                            Role.MANAGER.value,
                        }
                    ),
            }
        )

    return {
        "count":
            len(results),

        "events":
            results,
    }


@router.post(
    "/sms-relay/events/{event_id}/resolve-incoming",
)
def resolve_sms_incoming_payment(
    event_id: int,
    payload: ResolveSmsPaymentRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    actor = require_finance_manager(
        request,
        db,
    )

    event = db.get(
        PaymentEvent,
        event_id,
    )

    if event is None:
        raise HTTPException(
            status_code=404,
            detail="Payment event not found.",
        )

    if event.provider != "sms_relay":
        raise HTTPException(
            status_code=409,
            detail=(
                "Only SMS relay events can "
                "be resolved here."
            ),
        )

    if event.is_processed:
        raise HTTPException(
            status_code=409,
            detail=(
                "Payment event has already "
                "been processed."
            ),
        )

    try:
        raw = json.loads(
            event.raw_payload
            or "{}"
        )
    except Exception:
        raise HTTPException(
            status_code=409,
            detail=(
                "Payment event payload "
                "is invalid."
            ),
        )

    parsed = parse_money_sms(
        str(
            raw.get(
                "body",
                "",
            )
        )
    )

    if (
        parsed is None
        or parsed.direction
        != "incoming"
    ):
        raise HTTPException(
            status_code=409,
            detail=(
                "Event is not a valid "
                "incoming payment."
            ),
        )

    if (
        parsed.transaction_reference
        is None
    ):
        raise HTTPException(
            status_code=409,
            detail=(
                "Payment has no usable "
                "transaction reference."
            ),
        )

    order = db.get(
        Order,
        payload.order_id,
    )

    if order is None:
        raise HTTPException(
            status_code=404,
            detail="Order not found.",
        )

    if (
        order.status
        != OrderStatus.AWAITING_PAYMENT
    ):
        raise HTTPException(
            status_code=409,
            detail=(
                "Order is not awaiting payment."
            ),
        )

    expected_amount = Decimal(
        str(
            order.final_total
            or 0
        )
    ).quantize(
        Decimal("0.01")
    )

    if (
        parsed.amount
        != expected_amount
    ):
        raise HTTPException(
            status_code=409,
            detail=(
                "SMS amount does not match "
                "the order total."
            ),
        )

    provider_transaction_id = (
        "sms:"
        + parsed.transaction_reference
    )

    reused_payment = db.scalars(
        select(
            PaymentTransaction
        )
        .where(
            PaymentTransaction.provider_transaction_id
            == provider_transaction_id
        )
    ).first()

    if reused_payment is not None:
        raise HTTPException(
            status_code=409,
            detail=(
                "That SMS transaction reference "
                "has already been used."
            ),
        )

    transaction = db.scalars(
        select(
            PaymentTransaction
        )
        .where(
            PaymentTransaction.order_id
            == order.id,

            PaymentTransaction.provider
            == "sms_relay",

            PaymentTransaction.status.in_(
                {
                    PaymentStatus.INITIATED,
                    PaymentStatus.PENDING,
                }
            ),
        )
        .order_by(
            PaymentTransaction.id.desc()
        )
    ).first()

    if transaction is None:
        raise HTTPException(
            status_code=409,
            detail=(
                "This order has no pending "
                "SMS payment watch."
            ),
        )

    now = datetime.utcnow()

    transaction.status = (
        PaymentStatus.SUCCEEDED
    )

    transaction.provider_status = (
        "sms_manually_verified"
    )

    transaction.provider_transaction_id = (
        provider_transaction_id
    )

    transaction.confirmed_at = now

    if parsed.phone:
        transaction.payer_phone = (
            parsed.phone
        )

    transaction.failure_reason = None

    order.payment_amount = (
        transaction.amount
    )

    order.payment_method = (
        "sms_relay_manual_review"
    )

    order.payment_reference = (
        parsed.transaction_reference
    )

    order.payment_notes = (
        "SMS payment manually matched "
        f"by finance user #{actor.id}."
    )

    order.payment_confirmed_at = now

    order.status = (
        OrderStatus.PAYMENT_CONFIRMED
    )

    event.payment_transaction_id = (
        transaction.id
    )

    event.is_processed = True
    event.processed_at = now
    event.processing_error = None

    db.commit()

    return {
        "event_id":
            event.id,

        "order_id":
            order.id,

        "payment_transaction_id":
            transaction.id,

        "status":
            order.status.value,

        "amount":
            str(transaction.amount),

        "transaction_reference":
            parsed.transaction_reference,
    }
