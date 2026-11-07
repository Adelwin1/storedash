import json

from datetime import datetime
from decimal import Decimal

from zoneinfo import ZoneInfo

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Request,
)

from pydantic import (
    BaseModel,
    Field,
)

from sqlalchemy import select

from sqlalchemy.orm import (
    Session,
    selectinload,
)

from app.core.config import settings
from app.core.db import get_db

from app.services.pricing import (
    calculate_pricing,
    calculate_route,
)

from app.models import (
    Business,
    AuditEvent,
    Order,
    OrderItem,
    OrderStatus,
    Supplier,
)

from app.schemas.order import (
    OrderRead,
)


from app.services.supplier_payouts import (
    SupplierPayoutSetupError,
    prepare_supplier_payouts_for_order,
)

router = APIRouter(
    prefix="/orders",
    tags=["order-workflow"],
)


PREFINAL_STATUSES = {
    OrderStatus.DRAFT,
    OrderStatus.SOURCING,
    OrderStatus.QUOTE_READY,
    OrderStatus.AWAITING_BUYER_APPROVAL,
}


def ghana_now() -> datetime:
    return datetime.now(
        ZoneInfo(
            settings.operating_timezone
        )
    ).replace(
        tzinfo=None
    )


def load_order(
    db: Session,
    order_id: int,
):
    return db.scalars(
        select(Order)
        .options(
            selectinload(
                Order.items
            )
        )
        .where(
            Order.id == order_id
        )
    ).first()


def ensure_editable(
    order: Order,
):
    if (
        order.status
        not in PREFINAL_STATUSES
    ):
        raise HTTPException(
            status_code=409,
            detail=(
                "This order has already "
                "been finalized and is locked."
            ),
        )


def audit(
    db: Session,
    order: Order,
    action: str,
    before: dict | None = None,
    after: dict | None = None,
    actor_id: int | None = None,
):
    db.add(
        AuditEvent(
            actor_id=(
                actor_id
                if actor_id is not None
                else order.operator_id
            ),
            action=action,
            entity_type="order",
            entity_id=order.id,
            before_json=(
                json.dumps(
                    before
                )
                if before
                else None
            ),
            after_json=(
                json.dumps(
                    after
                )
                if after
                else None
            ),
        )
    )


class ItemSourcingUpdate(BaseModel):
    supplier_id: int | None = None

    availability_status: str

    confirmed_quantity: (
        float | None
    ) = Field(
        default=None,
        ge=0,
    )

    confirmed_price: (
        Decimal | None
    ) = Field(
        default=None,
        ge=0,
    )

    substitution_notes: (
        str | None
    ) = None


class QuoteCreate(BaseModel):
    delivery_fee: Decimal = Field(
        default=Decimal("0"),
        ge=0,
    )

    service_fee: Decimal = Field(
        default=Decimal("0"),
        ge=0,
    )


def validate_sourcing(
    order: Order,
):
    errors = []


    for item in order.items:
        state = (
            item.availability_status
            or "unverified"
        )


        if state not in {
            "available",
            "partial",
            "unavailable",
        }:
            errors.append(
                f"{item.name}: availability not confirmed"
            )

            continue


        if state in {
            "available",
            "partial",
        }:
            if not item.supplier_id:
                errors.append(
                    f"{item.name}: supplier missing"
                )


            if (
                item.confirmed_quantity
                is None
                or
                item.confirmed_quantity
                <= 0
            ):
                errors.append(
                    f"{item.name}: confirmed quantity missing"
                )


            if (
                item.confirmed_price
                is None
            ):
                errors.append(
                    f"{item.name}: price missing"
                )


    if errors:
        raise HTTPException(
            status_code=409,
            detail={
                "message":
                    "Sourcing is incomplete.",

                "items":
                    errors,
            },
        )


def validate_logistics(
    order: Order,
):
    missing = [
        item.name
        for item in order.items
        if (
            item.availability_status
            in {
                "available",
                "partial",
            }
            and
            (
                item.total_load_units is None
                or item.total_weight_kg is None
                or item.total_volume_l is None
                or item.total_handling_score is None
                or item.total_fragility_score is None
            )
        )
    ]


    if missing:
        raise HTTPException(
            status_code=409,
            detail={
                "message":
                    "Logistics classification is incomplete.",

                "items":
                    missing,
            },
        )


@router.put(
    "/{order_id}/items/{item_id}/sourcing",
    response_model=OrderRead,
)
def save_item_sourcing(
    order_id: int,
    item_id: int,
    payload: ItemSourcingUpdate,
    db: Session = Depends(
        get_db
    ),
):
    order = load_order(
        db,
        order_id,
    )


    if not order:
        raise HTTPException(
            status_code=404,
            detail="Order not found.",
        )


    ensure_editable(
        order
    )


    item = next(
        (
            item
            for item in order.items
            if item.id == item_id
        ),
        None,
    )


    if not item:
        raise HTTPException(
            status_code=404,
            detail="Order item not found.",
        )


    allowed_states = {
        "unverified",
        "available",
        "partial",
        "unavailable",
    }


    if (
        payload.availability_status
        not in allowed_states
    ):
        raise HTTPException(
            status_code=400,
            detail=(
                "Invalid availability status."
            ),
        )


    if payload.supplier_id:
        supplier = db.get(
            Supplier,
            payload.supplier_id,
        )

        if not supplier:
            raise HTTPException(
                status_code=404,
                detail="Supplier not found.",
            )


    before = {
        "supplier_id":
            item.supplier_id,

        "availability_status":
            item.availability_status,

        "confirmed_quantity":
            item.confirmed_quantity,

        "confirmed_price":
            str(
                item.confirmed_price
            )
            if item.confirmed_price
            is not None
            else None,
    }


    item.supplier_id = (
        payload.supplier_id
    )

    item.availability_status = (
        payload.availability_status
    )

    item.confirmed_quantity = (
        payload.confirmed_quantity
    )

    # ==================================================
    # PHYSICAL QUANTITY SYNCHRONIZATION
    #
    # Sourcing can change confirmed quantity after
    # logistics has already been classified.
    #
    # Therefore every quantity change must recompute
    # ALL quantity-dependent logistics totals.
    # ==================================================

    logistics_quantity = float(
        item.confirmed_quantity
        if item.confirmed_quantity is not None
        else item.requested_quantity
    )

    logistics_quantity = max(
        logistics_quantity,
        0.0,
    )


    if item.load_units_each is not None:
        item.total_load_units = round(
            float(item.load_units_each)
            * logistics_quantity,
            2,
        )


    if item.weight_kg_each is not None:
        item.total_weight_kg = round(
            float(item.weight_kg_each)
            * logistics_quantity,
            3,
        )


    if item.volume_l_each is not None:
        item.total_volume_l = round(
            float(item.volume_l_each)
            * logistics_quantity,
            3,
        )


    if item.handling_score_each is not None:
        item.total_handling_score = round(
            float(item.handling_score_each)
            * logistics_quantity,
            3,
        )


    if item.fragility_score_each is not None:
        item.total_fragility_score = round(
            float(item.fragility_score_each)
            * logistics_quantity,
            3,
        )


    item.confirmed_price = (
        payload.confirmed_price
    )

    item.substitution_notes = (
        payload.substitution_notes
    )


    # Keep logistics load synchronized with
    # the quantity that will actually be delivered.
    if payload.availability_status == "unavailable":
        item.total_load_units = 0

    elif item.load_units_each is not None:
        quantity_for_load = (
            payload.confirmed_quantity
            if payload.confirmed_quantity is not None
            else item.requested_quantity
        )

        item.total_load_units = round(
            float(item.load_units_each)
            * float(quantity_for_load or 0),
            2,
        )


    order.status = (
        OrderStatus.SOURCING
    )


    order.quote_generated_at = (
        None
    )

    order.customer_approved_at = (
        None
    )

    order.goods_total = 0
    order.delivery_fee = 0
    order.service_fee = 0
    order.final_total = 0


    audit(
        db,
        order,
        "item_sourcing_updated",
        before=before,
        after={
            "item_id":
                item.id,

            "supplier_id":
                item.supplier_id,

            "availability_status":
                item.availability_status,

            "confirmed_quantity":
                item.confirmed_quantity,

            "confirmed_price":
                str(
                    item.confirmed_price
                )
                if item.confirmed_price
                is not None
                else None,
        },
    )


    db.commit()


    return load_order(
        db,
        order.id,
    )


@router.post(
    "/{order_id}/quote",
    response_model=OrderRead,
)
def generate_quote(
    order_id: int,
    db: Session = Depends(get_db),
):
    order = load_order(
        db,
        order_id,
    )

    if not order:
        raise HTTPException(
            status_code=404,
            detail="Order not found.",
        )

    ensure_editable(order)

    validate_sourcing(order)
    validate_logistics(order)


    # ==================================================
    # GOODS
    # ==================================================

    goods_total = Decimal("0")

    deliverable_items = [
        item
        for item in order.items
        if item.availability_status
        in {
            "available",
            "partial",
        }
    ]


    for item in deliverable_items:
        quantity = Decimal(
            str(
                item.confirmed_quantity
                or 0
            )
        )

        price = Decimal(
            str(
                item.confirmed_price
                or 0
            )
        )

        goods_total += (
            quantity * price
        )


    # ==================================================
    # CUSTOMER LOCATION
    # ==================================================

    business = db.get(
        Business,
        order.business_id,
    )

    if not business:
        raise HTTPException(
            status_code=404,
            detail="Customer not found.",
        )


    if (
        business.latitude is None
        or business.longitude is None
    ):
        raise HTTPException(
            status_code=409,
            detail=(
                "Customer delivery location "
                "has not been confirmed yet."
            ),
        )


    # ==================================================
    # SUPPLIERS
    # ==================================================

    supplier_ids = []

    for item in deliverable_items:
        if (
            item.supplier_id
            and item.supplier_id
            not in supplier_ids
        ):
            supplier_ids.append(
                item.supplier_id
            )


    if not supplier_ids:
        raise HTTPException(
            status_code=409,
            detail=(
                "No suppliers are assigned "
                "to this order."
            ),
        )


    suppliers = []

    for supplier_id in supplier_ids:
        supplier = db.get(
            Supplier,
            supplier_id,
        )

        if not supplier:
            raise HTTPException(
                status_code=409,
                detail=(
                    f"Supplier {supplier_id} "
                    "could not be found."
                ),
            )


        if (
            supplier.latitude is None
            or supplier.longitude is None
        ):
            raise HTTPException(
                status_code=409,
                detail=(
                    f"Supplier '{supplier.name}' "
                    "does not have a confirmed "
                    "pickup location."
                ),
            )


        suppliers.append(
            supplier
        )


    # ==================================================
    # LOAD
    # ==================================================

    total_load_units = sum(
        float(
            item.total_load_units
            or 0
        )
        for item in deliverable_items
    )


    # ==================================================
    # ROAD ROUTE
    # ==================================================

    try:
        route = calculate_route(
            supplier_coordinates=[
                (
                    float(
                        supplier.latitude
                    ),
                    float(
                        supplier.longitude
                    ),
                )
                for supplier in suppliers
            ],

            customer_coordinate=(
                float(
                    business.latitude
                ),
                float(
                    business.longitude
                ),
            ),
        )

    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=(
                "Could not calculate the "
                "delivery route: "
                f"{exc}"
            ),
        ) from exc


    total_weight_kg = sum(
        float(item.total_weight_kg or 0)
        for item in deliverable_items
    )

    total_volume_l = sum(
        float(item.total_volume_l or 0)
        for item in deliverable_items
    )

    total_handling_score = sum(
        float(item.total_handling_score or 0)
        for item in deliverable_items
    )

    total_fragility_score = sum(
        float(item.total_fragility_score or 0)
        for item in deliverable_items
    )


    # ==================================================
    # AUTOMATIC PRICING
    # ==================================================

    pricing = calculate_pricing(
        goods_total=float(
            goods_total
        ),

        distance_km=(
            route["distance_km"]
        ),

        duration_minutes=(
            route["duration_minutes"]
        ),

        supplier_count=len(
            suppliers
        ),

        total_load_units=(
            total_load_units
        ),

        total_weight_kg=(
            total_weight_kg
        ),

        total_volume_l=(
            total_volume_l
        ),

        total_handling_score=(
            total_handling_score
        ),

        total_fragility_score=(
            total_fragility_score
        ),

        item_count=len(
            deliverable_items
        ),
    )


    # ==================================================
    # SNAPSHOT PRICE
    # ==================================================

    order.goods_total = (
        goods_total
    )

    order.delivery_fee = Decimal(
        str(
            pricing["delivery_fee"]
        )
    )

    order.service_fee = Decimal(
        str(
            pricing["service_fee"]
        )
    )

    order.tax_total = Decimal(
        str(
            pricing["tax_total"]
        )
    )

    order.final_total = Decimal(
        str(
            pricing["final_total"]
        )
    )


    order.route_distance_km = (
        route["distance_km"]
    )

    order.route_duration_minutes = (
        route["duration_minutes"]
    )

    order.supplier_stop_count = (
        len(suppliers)
    )

    order.total_load_units = (
        total_load_units
    )


    order.total_weight_kg = (
        total_weight_kg
    )

    order.total_volume_l = (
        total_volume_l
    )

    order.total_handling_score = (
        total_handling_score
    )

    order.total_fragility_score = (
        total_fragility_score
    )


    order.driver_floor = Decimal(
        str(
            pricing["driver_floor"]
        )
    )

    order.driver_target = Decimal(
        str(
            pricing["driver_target"]
        )
    )

    order.driver_ceiling = Decimal(
        str(
            pricing["driver_ceiling"]
        )
    )


    order.estimated_driver_market_cost = Decimal(
        str(
            pricing[
                "estimated_driver_market_cost"
            ]
        )
    )

    order.estimated_customer_willingness = Decimal(
        str(
            pricing[
                "estimated_customer_willingness"
            ]
        )
    )

    order.driver_acceptance_probability = (
        pricing[
            "driver_acceptance_probability"
        ]
    )

    order.customer_acceptance_probability = (
        pricing[
            "customer_acceptance_probability"
        ]
    )

    order.delivery_margin = Decimal(
        str(
            pricing[
                "delivery_margin"
            ]
        )
    )

    order.optimizer_score = (
        pricing[
            "optimizer_score"
        ]
    )

    order.pricing_version = (
        pricing["pricing_version"]
    )


    order.quote_generated_at = (
        ghana_now()
    )

    order.customer_approved_at = (
        None
    )

    order.status = (
        OrderStatus.AWAITING_BUYER_APPROVAL
    )


    audit(
        db,
        order,
        "final_price_generated",
        after={
            "goods_total":
                str(order.goods_total),

            "delivery_fee":
                str(order.delivery_fee),

            "service_fee":
                str(order.service_fee),

            "tax_total":
                str(order.tax_total),

            "final_total":
                str(order.final_total),

            "distance_km":
                order.route_distance_km,

            "duration_minutes":
                order.route_duration_minutes,

            "supplier_stops":
                order.supplier_stop_count,

            "load_units":
                order.total_load_units,

            "driver_floor":
                str(order.driver_floor),

            "driver_target":
                str(order.driver_target),

            "driver_ceiling":
                str(order.driver_ceiling),

            "pricing_version":
                order.pricing_version,
        },
    )


    db.commit()


    return load_order(
        db,
        order.id,
    )


@router.post(
    "/{order_id}/customer-approve",
    response_model=OrderRead,
)
def customer_approve(
    order_id: int,
    db: Session = Depends(
        get_db
    ),
):
    order = load_order(
        db,
        order_id,
    )


    if not order:
        raise HTTPException(
            status_code=404,
            detail="Order not found.",
        )


    if (
        order.status
        !=
        OrderStatus.AWAITING_BUYER_APPROVAL
    ):
        raise HTTPException(
            status_code=409,
            detail=(
                "Generate the quote before "
                "recording customer approval."
            ),
        )


    validate_sourcing(
        order
    )


    if (
        order.quote_generated_at
        is None
    ):
        raise HTTPException(
            status_code=409,
            detail=(
                "This order does not have "
                "a valid quote."
            ),
        )


    now = ghana_now()

    order.customer_approved_at = now

    order.finalized_at = now

    # Approval is NOT payment.
    order.status = (
        OrderStatus.AWAITING_PAYMENT
    )


    audit(
        db,
        order,
        "customer_quote_approved",
        after={
            "approved":
                True,

            "final_total":
                str(
                    order.final_total
                ),
        },
    )


    db.commit()


    return load_order(
        db,
        order.id,
    )


from pydantic import BaseModel


class CustomerResponseDecision(BaseModel):
    decision: str


@router.post(
    "/{order_id}/customer-response",
    response_model=OrderRead,
)
def customer_response(
    order_id: int,
    payload: CustomerResponseDecision,
    db: Session = Depends(get_db),
):
    order = load_order(
        db,
        order_id,
    )

    if not order:
        raise HTTPException(
            status_code=404,
            detail="Order not found.",
        )

    if (
        order.status
        != OrderStatus.AWAITING_BUYER_APPROVAL
    ):
        raise HTTPException(
            status_code=409,
            detail=(
                "This order is not currently "
                "waiting for a customer decision."
            ),
        )

    if not order.quote_generated_at:
        raise HTTPException(
            status_code=409,
            detail=(
                "Generate the final price first."
            ),
        )

    decision = (
        payload.decision
        .strip()
        .lower()
    )

    if decision == "approved":
        now = ghana_now()

        order.customer_approved_at = now

        # Customer approved the quote.
        #
        # Approval is NOT payment and does not authorize
        # dispatch or driver commitment.
        order.finalized_at = now

        order.status = (
            OrderStatus.AWAITING_PAYMENT
        )

        audit(
            db,
            order,
            "customer_approved_final_price",
            after={
                "status":
                    order.status.value,

                "final_total":
                    str(
                        order.final_total
                    ),
            },
        )

    elif decision == "wait":
        order.customer_approved_at = (
            None
        )

        # Deliberately remains here.
        order.status = (
            OrderStatus.AWAITING_BUYER_APPROVAL
        )

        audit(
            db,
            order,
            "customer_requested_wait",
            after={
                "status":
                    order.status.value,
            },
        )

    elif decision == "declined":
        order.customer_approved_at = (
            None
        )

        order.status = (
            OrderStatus.CANCELLED
        )

        audit(
            db,
            order,
            "customer_declined_final_price",
            after={
                "status":
                    order.status.value,

                "final_total":
                    str(
                        order.final_total
                    ),
            },
        )

    else:
        raise HTTPException(
            status_code=400,
            detail=(
                "decision must be "
                "approved, wait, or declined."
            ),
        )

    db.commit()

    return load_order(
        db,
        order.id,
    )



# ============================================================
# PAYMENT + PREPARATION + DISPATCH READINESS
# ============================================================


class PaymentConfirmationRequest(BaseModel):
    amount: Decimal = Field(
        gt=0,
    )

    method: str = Field(
        min_length=1,
        max_length=40,
    )

    reference: str | None = Field(
        default=None,
        max_length=120,
    )

    notes: str | None = None

    operator_id: int | None = None


class WorkflowActionRequest(BaseModel):
    operator_id: int | None = None
    notes: str | None = None


class AdminPaymentOverrideRequest(BaseModel):
    reference: str | None = Field(
        default=None,
        max_length=120,
    )

    notes: str | None = None


@router.post(
    "/{order_id}/admin-override-payment",
    response_model=OrderRead,
)
def admin_override_payment(
    order_id: int,
    payload: AdminPaymentOverrideRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    # Temporary testing/launch escape hatch.
    # Only a real authenticated StoreDash admin can use it.
    if getattr(
        request.state,
        "user_role",
        None,
    ) != "admin":
        raise HTTPException(
            status_code=403,
            detail="Admin access required.",
        )

    actor_id = getattr(
        request.state,
        "user_id",
        None,
    )

    order = load_order(
        db,
        order_id,
    )

    if not order:
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
                "Admin payment override is only "
                "available while awaiting payment."
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

    expected = Decimal(
        str(
            order.final_total
            or 0
        )
    ).quantize(
        Decimal("0.01")
    )

    if expected <= 0:
        raise HTTPException(
            status_code=409,
            detail=(
                "Order has no valid payable total."
            ),
        )

    now = ghana_now()

    before_status = (
        order.status.value
    )

    # Amount is always taken from StoreDash.
    # Admin cannot type or modify it.
    order.payment_amount = expected

    order.payment_method = (
        "admin_override"
    )

    order.payment_reference = (
        payload.reference.strip()
        if payload.reference
        else (
            f"ADMIN-OVERRIDE-"
            f"{order.id}-"
            f"{now.strftime('%Y%m%d%H%M%S')}"
        )
    )

    order.payment_notes = (
        payload.notes
        or (
            "Temporary admin payment override "
            "used while payment relay is unavailable."
        )
    )

    order.payment_confirmed_at = now

    order.status = (
        OrderStatus.PAYMENT_CONFIRMED
    )

    audit(
        db,
        order,
        "admin_payment_override",
        before={
            "status":
                before_status,
        },
        after={
            "status":
                order.status.value,

            "amount":
                str(expected),

            "method":
                "admin_override",

            "reference":
                order.payment_reference,
        },
        actor_id=
            actor_id,
    )

    db.commit()

    return load_order(
        db,
        order.id,
    )


@router.post(
    "/{order_id}/confirm-payment",
    response_model=OrderRead,
)
def confirm_payment(
    order_id: int,
    payload: PaymentConfirmationRequest,
    db: Session = Depends(get_db),
):
    # Payment confirmation is provider-controlled.
    # StoreDash employees must never be able to mark an order paid manually.
    raise HTTPException(
        status_code=410,
        detail=(
            "Manual payment confirmation is disabled. "
            "Payment must be confirmed by the payment provider."
        ),
    )

    order = load_order(
        db,
        order_id,
    )

    if not order:
        raise HTTPException(
            status_code=404,
            detail="Order not found.",
        )

    if order.status not in {
        OrderStatus.AWAITING_PAYMENT,

        # Backward compatibility for old development orders
        # created before AWAITING_PAYMENT existed.
        OrderStatus.ACTIVE,
    }:
        raise HTTPException(
            status_code=409,
            detail=(
                "Order must have an approved customer "
                "quote before payment can be confirmed."
            ),
        )

    if order.customer_approved_at is None:
        raise HTTPException(
            status_code=409,
            detail=(
                "Customer approval has not been recorded."
            ),
        )

    expected = Decimal(
        str(
            order.final_total
            or 0
        )
    ).quantize(
        Decimal("0.01")
    )

    received = Decimal(
        str(
            payload.amount
        )
    ).quantize(
        Decimal("0.01")
    )

    if expected <= 0:
        raise HTTPException(
            status_code=409,
            detail=(
                "Order has no valid payable total."
            ),
        )

    if received != expected:
        raise HTTPException(
            status_code=409,
            detail={
                "message":
                    "Payment amount does not match the approved order total.",

                "expected":
                    str(expected),

                "received":
                    str(received),
            },
        )

    method = (
        payload.method
        .strip()
        .lower()
    )

    if not method:
        raise HTTPException(
            status_code=400,
            detail="Payment method is required.",
        )

    now = ghana_now()

    before_status = (
        order.status.value
    )

    order.payment_amount = (
        received
    )

    order.payment_method = (
        method
    )

    order.payment_reference = (
        payload.reference.strip()
        if payload.reference
        else None
    )

    order.payment_notes = (
        payload.notes
    )

    order.payment_confirmed_at = (
        now
    )

    order.status = (
        OrderStatus.PAYMENT_CONFIRMED
    )

    audit(
        db,
        order,
        "payment_confirmed",
        before={
            "status":
                before_status,
        },
        after={
            "status":
                order.status.value,

            "amount":
                str(received),

            "method":
                method,

            "reference":
                order.payment_reference,
        },
        actor_id=
            payload.operator_id,
    )

    db.commit()

    return load_order(
        db,
        order.id,
    )


@router.post(
    "/{order_id}/begin-preparation",
    response_model=OrderRead,
)
def begin_preparation(
    order_id: int,
    payload: WorkflowActionRequest,
    db: Session = Depends(get_db),
):
    order = load_order(
        db,
        order_id,
    )

    if not order:
        raise HTTPException(
            status_code=404,
            detail="Order not found.",
        )

    if (
        order.status
        !=
        OrderStatus.PAYMENT_CONFIRMED
    ):
        raise HTTPException(
            status_code=409,
            detail=(
                "Payment must be confirmed before "
                "supplier preparation begins."
            ),
        )

    if order.payment_confirmed_at is None:
        raise HTTPException(
            status_code=409,
            detail=(
                "Payment confirmation timestamp is missing."
            ),
        )

    now = ghana_now()

    order.preparation_started_at = (
        now
    )

    order.status = (
        OrderStatus.PREPARING
    )

    if payload.notes:
        order.notes = (
            (
                order.notes + "\n"
            )
            if order.notes
            else ""
        ) + payload.notes

    audit(
        db,
        order,
        "supplier_preparation_started",
        after={
            "status":
                order.status.value,
        },
        actor_id=
            payload.operator_id,
    )

    db.commit()

    return load_order(
        db,
        order.id,
    )


@router.post(
    "/{order_id}/ready-for-dispatch",
    response_model=OrderRead,
)
def mark_ready_for_dispatch(
    order_id: int,
    payload: WorkflowActionRequest,
    db: Session = Depends(get_db),
):
    order = load_order(
        db,
        order_id,
    )

    if not order:
        raise HTTPException(
            status_code=404,
            detail="Order not found.",
        )

    if (
        order.status
        !=
        OrderStatus.PREPARING
    ):
        raise HTTPException(
            status_code=409,
            detail=(
                "Order must be in PREPARING before "
                "it can enter the dispatch pool."
            ),
        )

    if order.payment_confirmed_at is None:
        raise HTTPException(
            status_code=409,
            detail=(
                "Payment has not been confirmed."
            ),
        )

    # Recheck all launch-critical physical information before
    # allowing this order into automatic routing.
    validate_sourcing(
        order
    )

    validate_logistics(
        order
    )

    business = db.get(
        Business,
        order.business_id,
    )

    if (
        not business
        or
        business.latitude is None
        or
        business.longitude is None
    ):
        raise HTTPException(
            status_code=409,
            detail=(
                "Customer delivery location is missing."
            ),
        )

    supplier_ids = {
        item.supplier_id
        for item in order.items
        if item.availability_status
        in {
            "available",
            "partial",
        }
    }

    for supplier_id in supplier_ids:

        if supplier_id is None:
            raise HTTPException(
                status_code=409,
                detail=(
                    "A deliverable item has no supplier."
                ),
            )

        supplier = db.get(
            Supplier,
            supplier_id,
        )

        if (
            not supplier
            or
            supplier.latitude is None
            or
            supplier.longitude is None
        ):
            raise HTTPException(
                status_code=409,
                detail=(
                    f"Supplier {supplier_id} does not "
                    "have a confirmed pickup location."
                ),
            )

    try:
        prepare_supplier_payouts_for_order(
            db,
            order.id,
        )
    except SupplierPayoutSetupError as exc:
        raise HTTPException(
            status_code=409,
            detail=str(exc),
        ) from exc

    now = ghana_now()

    order.ready_for_dispatch_at = (
        now
    )

    order.status = (
        OrderStatus.READY_FOR_DISPATCH
    )

    if payload.notes:
        order.notes = (
            (
                order.notes + "\n"
            )
            if order.notes
            else ""
        ) + payload.notes

    audit(
        db,
        order,
        "order_ready_for_dispatch",
        after={
            "status":
                order.status.value,

            "supplier_count":
                len(
                    supplier_ids
                ),
        },
        actor_id=
            payload.operator_id,
    )

    db.commit()

    return load_order(
        db,
        order.id,
    )


@router.get(
    "/{order_id}/readiness",
)
def get_order_readiness(
    order_id: int,
    db: Session = Depends(get_db),
):
    order = load_order(
        db,
        order_id,
    )

    if not order:
        raise HTTPException(
            status_code=404,
            detail="Order not found.",
        )


    # ==================================================
    # CUSTOMER
    # ==================================================

    business = db.get(
        Business,
        order.business_id,
    )

    customer_location_ok = bool(
        business
        and business.latitude is not None
        and business.longitude is not None
    )


    # ==================================================
    # ITEMS / SOURCING / LOGISTICS
    # ==================================================

    sourcing_issues = []

    logistics_issues = []

    deliverable_items = []


    for item in order.items:
        status = (
            item.availability_status
            or "unverified"
        )

        if status == "unverified":
            sourcing_issues.append(
                f"{item.name}: availability not confirmed"
            )

            continue


        if status in {
            "available",
            "partial",
        }:
            deliverable_items.append(
                item
            )


            if not item.supplier_id:
                sourcing_issues.append(
                    f"{item.name}: supplier missing"
                )


            if (
                item.confirmed_quantity
                is None
                or float(
                    item.confirmed_quantity
                ) <= 0
            ):
                sourcing_issues.append(
                    f"{item.name}: confirmed quantity missing"
                )


            if (
                item.confirmed_price
                is None
            ):
                sourcing_issues.append(
                    f"{item.name}: supplier price missing"
                )


            if (
                item.total_load_units
                is None
                or float(
                    item.total_load_units
                ) <= 0
            ):
                logistics_issues.append(
                    f"{item.name}: logistics/load missing"
                )


    if not deliverable_items:
        sourcing_issues.append(
            "No deliverable items are available."
        )


    sourcing_ok = (
        len(sourcing_issues) == 0
    )

    logistics_ok = (
        len(logistics_issues) == 0
    )


    # ==================================================
    # SUPPLIER LOCATIONS
    # ==================================================

    supplier_ids = []

    for item in deliverable_items:
        if (
            item.supplier_id
            and item.supplier_id
            not in supplier_ids
        ):
            supplier_ids.append(
                item.supplier_id
            )


    missing_suppliers = []

    for supplier_id in supplier_ids:
        supplier = db.get(
            Supplier,
            supplier_id,
        )

        if not supplier:
            missing_suppliers.append(
                {
                    "id":
                        supplier_id,

                    "name":
                        f"Supplier {supplier_id}",

                    "location":
                        None,

                    "reason":
                        "Supplier record missing",
                }
            )

            continue


        if (
            supplier.latitude is None
            or supplier.longitude is None
        ):
            missing_suppliers.append(
                {
                    "id":
                        supplier.id,

                    "name":
                        supplier.name,

                    "location":
                        supplier.location,

                    "reason":
                        "Pickup location not confirmed",
                }
            )


    supplier_locations_ok = (
        len(missing_suppliers) == 0
    )


    # ==================================================
    # STATUS
    # ==================================================

    pricing_status_ok = (
        order.status
        in {
            OrderStatus.DRAFT,
            OrderStatus.SOURCING,
            OrderStatus.PARTIALLY_FULFILLED,
            OrderStatus.QUOTE_READY,
            OrderStatus.AWAITING_BUYER_APPROVAL,
        }
    )


    # ==================================================
    # DATA READINESS
    # ==================================================

    ready = all(
        [
            sourcing_ok,
            logistics_ok,
            customer_location_ok,
            supplier_locations_ok,
        ]
    )


    can_generate_price = (
        ready
        and pricing_status_ok
        and order.status
        != OrderStatus.AWAITING_BUYER_APPROVAL
    )


    if (
        order.status
        == OrderStatus.AWAITING_BUYER_APPROVAL
    ):
        stage = "awaiting_customer"

    elif order.status == OrderStatus.ACTIVE:
        stage = "active"

    elif order.status == OrderStatus.CANCELLED:
        stage = "cancelled"

    elif order.status == OrderStatus.COMPLETED:
        stage = "completed"

    elif ready:
        stage = "ready_for_pricing"

    else:
        stage = "setup_required"


    checks = [
        {
            "key":
                "sourcing",

            "label":
                "Sourcing",

            "ok":
                sourcing_ok,

            "detail":
                (
                    "All item sourcing is complete."
                    if sourcing_ok
                    else "; ".join(
                        sourcing_issues
                    )
                ),
        },

        {
            "key":
                "logistics",

            "label":
                "Logistics",

            "ok":
                logistics_ok,

            "detail":
                (
                    "Load information is complete."
                    if logistics_ok
                    else "; ".join(
                        logistics_issues
                    )
                ),
        },

        {
            "key":
                "customer_location",

            "label":
                "Customer location",

            "ok":
                customer_location_ok,

            "detail":
                (
                    "Delivery location confirmed."
                    if customer_location_ok
                    else
                    "Customer delivery location must be confirmed."
                ),
        },

        {
            "key":
                "supplier_locations",

            "label":
                "Supplier locations",

            "ok":
                supplier_locations_ok,

            "detail":
                (
                    "All pickup locations confirmed."
                    if supplier_locations_ok
                    else
                    f"{len(missing_suppliers)} supplier location(s) missing."
                ),
        },

        {
            "key":
                "status",

            "label":
                "Order stage",

            "ok":
                True,

            "detail":
                (
                    "Ready for final pricing."
                    if can_generate_price
                    else (
                        "Final price generated; waiting for customer."
                        if order.status
                        == OrderStatus.AWAITING_BUYER_APPROVAL
                        else (
                            "Order is already in progress."
                            if order.status
                            == OrderStatus.ACTIVE
                            else
                            f"Current stage: {stage.replace('_', ' ')}."
                        )
                    )
                ),
        },
    ]


    return {
        "order_id":
            order.id,

        "ready":
            ready,

        "can_generate_price":
            can_generate_price,

        "stage":
            stage,

        "checks":
            checks,

        "customer": {
            "id":
                business.id
                if business
                else order.business_id,

            "name":
                business.business_name
                if business
                else None,

            "address":
                business.address
                if business
                else None,

            "location_confirmed":
                customer_location_ok,
        },

        "missing_suppliers":
            missing_suppliers,

        "deliverable_item_count":
            len(
                deliverable_items
            ),

        "issue_count":
            sum(
                1
                for check in checks
                if not check["ok"]
            ),
    }
