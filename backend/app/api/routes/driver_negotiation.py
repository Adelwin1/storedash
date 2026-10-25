from datetime import datetime
from decimal import (
    Decimal,
    ROUND_HALF_UP,
)

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
)

from pydantic import (
    BaseModel,
    Field,
)

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.db import get_db

from app.models import (
    Driver,
    DriverOffer,
    Order,
    OrderStatus,
)

from app.models.entities import (
    DriverNegotiationEvent,
)


router = APIRouter(
    prefix="/orders",
    tags=["driver-negotiation"],
)


# ============================================================
# MONEY HELPERS
# ============================================================

def money(
    value,
) -> Decimal:
    return Decimal(
        str(value)
    ).quantize(
        Decimal("0.01"),
        rounding=ROUND_HALF_UP,
    )


def half_cedi(
    value,
) -> Decimal:
    value = Decimal(
        str(value)
    )

    return (
        value * Decimal("2")
    ).quantize(
        Decimal("1"),
        rounding=ROUND_HALF_UP,
    ) / Decimal("2")


# ============================================================
# REQUEST SCHEMAS
# ============================================================

class StartNegotiationRequest(BaseModel):
    driver_id: int
    operator_id: int | None = None


class DriverQuoteRequest(BaseModel):
    amount: Decimal = Field(
        gt=0
    )

    operator_id: int | None = None


class NegotiationActionRequest(BaseModel):
    operator_id: int | None = None


# ============================================================
# INTERNAL HELPERS
# ============================================================

def event(
    db: Session,
    *,
    offer: DriverOffer,
    event_type: str,
    amount=None,
    operator_id=None,
    details=None,
):
    db.add(
        DriverNegotiationEvent(
            driver_offer_id=offer.id,
            order_id=offer.order_id,
            driver_id=offer.driver_id,
            operator_id=operator_id,
            event_type=event_type,
            amount=(
                money(amount)
                if amount is not None
                else None
            ),
            details=details,
        )
    )


def get_offer(
    db: Session,
    offer_id: int,
):
    offer = db.get(
        DriverOffer,
        offer_id,
    )

    if not offer:
        raise HTTPException(
            status_code=404,
            detail=(
                "Driver negotiation not found."
            ),
        )

    return offer


def public_state(
    db: Session,
    offer: DriverOffer,
):
    driver = db.get(
        Driver,
        offer.driver_id,
    )

    history = db.scalars(
        select(
            DriverNegotiationEvent
        )
        .where(
            DriverNegotiationEvent.driver_offer_id
            == offer.id
        )
        .order_by(
            DriverNegotiationEvent.created_at,
            DriverNegotiationEvent.id,
        )
    ).all()


    if offer.outcome == "pending":
        instruction = (
            "Ask the driver what price they "
            "would take for this delivery."
        )

    elif offer.outcome == "quote_authorized":
        instruction = (
            "The driver's quoted price is authorized. "
            "Confirm the agreement."
        )

    elif offer.outcome == "countered":
        instruction = (
            "Tell the driver the authorized offer shown. "
            "If they refuse, ask for their new price."
        )

    elif offer.outcome == "accepted":
        instruction = (
            "Driver assigned and payout locked."
        )

    elif offer.outcome == "unavailable":
        instruction = (
            "Driver unavailable. Choose another driver."
        )

    elif offer.outcome == "holding":
        instruction = (
            "Tell the driver the authorized amount is "
            "StoreDash's final offer. If they decline, "
            "they may call back and accept it while the "
            "order is still unassigned."
        )

    elif offer.outcome == "expired":
        instruction = (
            "This driver opportunity has expired because "
            "the order was assigned elsewhere."
        )

    else:
        instruction = "Negotiation updated."


    return {
        "id":
            offer.id,

        "order_id":
            offer.order_id,

        "driver": {
            "id":
                driver.id,

            "name":
                driver.name,

            "phone":
                driver.phone,

            "vehicle_type":
                driver.vehicle_type,

            "current_area":
                driver.current_area,
        },

        # IMPORTANT:
        # Internal target, automatic threshold and
        # 75% ceiling are intentionally NOT returned.

        "driver_quote":
            (
                float(
                    offer.driver_quote
                )
                if offer.driver_quote
                is not None
                else None
            ),

        "authorized_offer":
            (
                float(
                    offer.current_authorized_offer
                )
                if offer.current_authorized_offer
                is not None
                else None
            ),

        "final_payout":
            (
                float(
                    offer.final_payout
                )
                if offer.final_payout
                is not None
                else None
            ),

        "counter_round":
            offer.counter_round,

        "outcome":
            offer.outcome,

        "instruction":
            instruction,

        "history": [
            {
                "event_type":
                    row.event_type,

                "amount":
                    (
                        float(
                            row.amount
                        )
                        if row.amount
                        is not None
                        else None
                    ),

                "details":
                    row.details,

                "created_at":
                    row.created_at,
            }
            for row in history
        ],
    }


# ============================================================
# START
# ============================================================

@router.post(
    "/{order_id}/driver-negotiation/start",
)
def start_negotiation(
    order_id: int,
    payload: StartNegotiationRequest,
    db: Session = Depends(get_db),
):
    order = db.get(
        Order,
        order_id,
    )

    if not order:
        raise HTTPException(
            status_code=404,
            detail="Order not found.",
        )


    # ========================================================
    # LEGACY PATH DISABLED
    #
    # StoreDash delivery dispatch is now route/batch based.
    #
    # Even a one-order delivery must use the batching system so
    # physical capacity, route sequencing and route-level rider
    # economics are evaluated consistently.
    # ========================================================

    raise HTTPException(
        status_code=409,
        detail=(
            "Legacy per-order driver negotiation is disabled. "
            "Use StoreDash batch dispatch."
        ),
    )

    allowed = {
        OrderStatus.READY_FOR_DISPATCH,
    }

    if order.status not in allowed:
        raise HTTPException(
            status_code=409,
            detail=(
                "This order is not ready "
                "for driver assignment."
            ),
        )


    if order.assigned_driver_id:
        raise HTTPException(
            status_code=409,
            detail=(
                "A driver has already been "
                "assigned to this order."
            ),
        )


    driver = db.get(
        Driver,
        payload.driver_id,
    )

    if not driver:
        raise HTTPException(
            status_code=404,
            detail="Driver not found.",
        )

    if not driver.is_active:
        raise HTTPException(
            status_code=409,
            detail="Driver is inactive.",
        )

    if not driver.is_available:
        raise HTTPException(
            status_code=409,
            detail=(
                "Driver is currently unavailable."
            ),
        )


    route_value = money(
        order.delivery_fee
    )

    if route_value <= 0:
        raise HTTPException(
            status_code=409,
            detail=(
                "Order has no delivery fee."
            ),
        )


    # ========================================================
    # SECRET INTERNAL ECONOMICS
    #
    # 75% is the absolute payout ceiling.
    #
    # The normal negotiation limit stays BELOW the ceiling
    # so operators/drivers cannot routinely discover it.
    # ========================================================

    hard_ceiling = money(
        route_value
        * Decimal("0.75")
    )


    predicted = (
        order.driver_target
        or
        order.estimated_driver_market_cost
        or
        (
            hard_ceiling
            * Decimal("0.75")
        )
    )


    internal_target = min(
        money(predicted),
        money(
            hard_ceiling
            * Decimal("0.84")
        ),
    )


    internal_target = max(
        Decimal("1.00"),
        internal_target,
    )


    auto_accept_limit = min(
        money(
            hard_ceiling
            * Decimal("0.90")
        ),

        money(
            internal_target
            + (
                (
                    hard_ceiling
                    - internal_target
                )
                * Decimal("0.30")
            )
        ),
    )


    normal_max = money(
        hard_ceiling
        * Decimal("0.96")
    )


    offer = DriverOffer(
        order_id=order.id,

        driver_id=driver.id,

        operator_id=
            payload.operator_id,

        route_value=
            route_value,

        # Existing column reused as the SECRET
        # internal fair target. Never returned.
        opening_offer=
            internal_target,

        hard_ceiling=
            hard_ceiling,

        auto_accept_limit=
            auto_accept_limit,

        normal_negotiation_max=
            normal_max,

        counter_round=0,

        outcome="pending",
    )

    db.add(offer)
    db.flush()


    event(
        db,
        offer=offer,
        event_type="negotiation_started",
        operator_id=
            payload.operator_id,
        details=(
            "Driver called. Ask driver "
            "to state their price first."
        ),
    )


    db.commit()

    return public_state(
        db,
        offer,
    )


# ============================================================
# DRIVER STATES A PRICE
# ============================================================

@router.post(
    "/{order_id}/driver-negotiation/{offer_id}/quote",
)
def driver_quote(
    order_id: int,
    offer_id: int,
    payload: DriverQuoteRequest,
    db: Session = Depends(get_db),
):
    offer = get_offer(
        db,
        offer_id,
    )


    if offer.order_id != order_id:
        raise HTTPException(
            status_code=404,
            detail=(
                "Negotiation does not belong "
                "to this order."
            ),
        )


    if offer.outcome in {
        "accepted",
        "unavailable",
        "holding",
        "expired",
    }:
        raise HTTPException(
            status_code=409,
            detail=(
                "This negotiation is closed."
            ),
        )


    quote = money(
        payload.amount
    )


    offer.driver_quote = (
        quote
    )


    event(
        db,
        offer=offer,
        event_type="driver_quote",
        amount=quote,
        operator_id=
            payload.operator_id,
    )


    target = money(
        offer.opening_offer
    )

    auto_limit = money(
        offer.auto_accept_limit
    )

    normal_max = money(
        offer.normal_negotiation_max
    )

    current = (
        money(
            offer.current_authorized_offer
        )
        if offer.current_authorized_offer
        is not None
        else None
    )


    # Driver is now asking at or below what
    # StoreDash already authorized.
    if (
        current is not None
        and quote <= current
    ):
        offer.current_authorized_offer = (
            quote
        )

        offer.outcome = (
            "quote_authorized"
        )

        event(
            db,
            offer=offer,
            event_type="quote_authorized",
            amount=quote,
            operator_id=
                payload.operator_id,
            details=(
                "Driver quote is within the "
                "current authorized amount."
            ),
        )

        db.commit()

        return public_state(
            db,
            offer,
        )


    # First quote is economically good.
    if (
        offer.counter_round == 0
        and quote <= auto_limit
    ):
        offer.current_authorized_offer = (
            quote
        )

        offer.outcome = (
            "quote_authorized"
        )

        event(
            db,
            offer=offer,
            event_type="quote_authorized",
            amount=quote,
            operator_id=
                payload.operator_id,
            details=(
                "Driver's stated price was "
                "accepted by StoreDash."
            ),
        )

        db.commit()

        return public_state(
            db,
            offer,
        )


    # After two controlled concessions,
    # StoreDash only closes if the driver's
    # new quote has entered the normal range.
    if offer.counter_round >= 2:
        if quote <= normal_max:
            offer.current_authorized_offer = (
                quote
            )

            offer.outcome = (
                "quote_authorized"
            )

            event(
                db,
                offer=offer,
                event_type="quote_authorized",
                amount=quote,
                operator_id=
                    payload.operator_id,
                details=(
                    "Driver's final stated price "
                    "entered the authorized range."
                ),
            )

        else:
            # Do NOT discard the last authorized amount.
            # This becomes the driver's final StoreDash
            # offer while they remain on hold.
            if offer.current_authorized_offer is None:
                offer.current_authorized_offer = (
                    normal_max
                )

            offer.outcome = (
                "holding"
            )

            event(
                db,
                offer=offer,
                event_type="driver_placed_on_hold",
                amount=offer.current_authorized_offer,
                operator_id=
                    payload.operator_id,
                details=(
                    "Driver declined the final authorized "
                    "offer. Driver may call back and accept "
                    "while the order remains unassigned."
                ),
            )

        db.commit()

        return public_state(
            db,
            offer,
        )


    # ========================================================
    # CONTROLLED COUNTER
    # ========================================================

    anchor = min(
        quote,
        normal_max,
    )


    if offer.counter_round == 0:

        suggested = (
            target
            + (
                anchor
                - target
            )
            * Decimal("0.45")
        )

    else:

        base = (
            current
            if current is not None
            else target
        )

        suggested = (
            base
            + (
                anchor
                - base
            )
            * Decimal("0.55")
        )


    suggested = half_cedi(
        min(
            suggested,
            normal_max,
        )
    )


    # If rounding means StoreDash has effectively
    # reached the driver's quote, just authorize it.
    if suggested >= quote:
        offer.current_authorized_offer = (
            quote
        )

        offer.outcome = (
            "quote_authorized"
        )

        event(
            db,
            offer=offer,
            event_type="quote_authorized",
            amount=quote,
            operator_id=
                payload.operator_id,
        )

    else:
        offer.current_authorized_offer = (
            suggested
        )

        offer.counter_offer = (
            suggested
        )

        offer.counter_round += 1

        offer.outcome = (
            "countered"
        )

        event(
            db,
            offer=offer,
            event_type="system_counter",
            amount=suggested,
            operator_id=
                payload.operator_id,
            details=(
                "Authorized StoreDash counteroffer."
            ),
        )


    db.commit()

    return public_state(
        db,
        offer,
    )


# ============================================================
# DRIVER ACCEPTS AUTHORIZED AMOUNT
# ============================================================

@router.post(
    "/{order_id}/driver-negotiation/{offer_id}/accept",
)
def accept_driver(
    order_id: int,
    offer_id: int,
    payload: NegotiationActionRequest,
    db: Session = Depends(get_db),
):
    offer = get_offer(
        db,
        offer_id,
    )


    if offer.order_id != order_id:
        raise HTTPException(
            status_code=404,
            detail="Negotiation mismatch.",
        )


    if offer.outcome not in {
        "quote_authorized",
        "countered",
        "holding",
    }:
        raise HTTPException(
            status_code=409,
            detail=(
                "There is no authorized "
                "driver amount to accept."
            ),
        )


    payout = money(
        offer.current_authorized_offer
    )

    ceiling = money(
        offer.hard_ceiling
    )


    if payout > ceiling:
        raise HTTPException(
            status_code=409,
            detail=(
                "Driver payout violates "
                "the StoreDash payout policy."
            ),
        )


    order = db.get(
        Order,
        order_id,
    )

    if order.assigned_driver_id:
        raise HTTPException(
            status_code=409,
            detail=(
                "This order has already been assigned "
                "to another driver."
            ),
        )

    driver = db.get(
        Driver,
        offer.driver_id,
    )


    offer.final_payout = (
        payout
    )

    offer.company_delivery_share = money(
        money(
            offer.route_value
        )
        - payout
    )

    offer.released_driver_reserve = money(
        ceiling
        - payout
    )

    offer.outcome = (
        "accepted"
    )

    offer.locked_at = (
        datetime.utcnow()
    )


    order.assigned_driver_id = (
        driver.id
    )

    order.driver_payout = (
        payout
    )

    order.driver_assigned_at = (
        datetime.utcnow()
    )

    order.status = (
        OrderStatus.DRIVER_ASSIGNED
    )


    driver.is_available = False


    # Once one driver accepts, every other open/held
    # negotiation for this order becomes invalid.
    other_offers = db.scalars(
        select(DriverOffer)
        .where(
            DriverOffer.order_id == order.id,
            DriverOffer.id != offer.id,
            DriverOffer.outcome.in_(
                [
                    "pending",
                    "quote_authorized",
                    "countered",
                    "holding",
                ]
            ),
        )
    ).all()

    for other in other_offers:
        other.outcome = "expired"

        event(
            db,
            offer=other,
            event_type="negotiation_expired",
            operator_id=payload.operator_id,
            details=(
                "Order was assigned to another driver."
            ),
        )


    event(
        db,
        offer=offer,
        event_type="driver_assigned",
        amount=payout,
        operator_id=
            payload.operator_id,
        details=(
            "Driver payout locked."
        ),
    )


    db.commit()

    return public_state(
        db,
        offer,
    )


# ============================================================
# DRIVER UNAVAILABLE
# ============================================================

@router.post(
    "/{order_id}/driver-negotiation/{offer_id}/unavailable",
)
def driver_unavailable(
    order_id: int,
    offer_id: int,
    payload: NegotiationActionRequest,
    db: Session = Depends(get_db),
):
    offer = get_offer(
        db,
        offer_id,
    )


    if offer.order_id != order_id:
        raise HTTPException(
            status_code=404,
            detail="Negotiation mismatch.",
        )


    offer.outcome = (
        "unavailable"
    )


    event(
        db,
        offer=offer,
        event_type="driver_unavailable",
        operator_id=
            payload.operator_id,
    )


    db.commit()

    return public_state(
        db,
        offer,
    )


# ============================================================
# CURRENT / LATEST NEGOTIATION
# ============================================================

@router.get(
    "/{order_id}/driver-negotiation",
)
def latest_negotiation(
    order_id: int,
    db: Session = Depends(get_db),
):
    offer = db.scalars(
        select(
            DriverOffer
        )
        .where(
            DriverOffer.order_id
            == order_id
        )
        .order_by(
            DriverOffer.id.desc()
        )
    ).first()


    if not offer:
        return {
            "order_id":
                order_id,

            "negotiation":
                None,
        }


    return {
        "order_id":
            order_id,

        "negotiation":
            public_state(
                db,
                offer,
            ),
    }


# ============================================================
# DRIVERS CURRENTLY HOLDING FOR AN ORDER
# ============================================================

@router.get(
    "/{order_id}/driver-negotiation/holding",
)
def holding_negotiations(
    order_id: int,
    db: Session = Depends(get_db),
):
    order = db.get(
        Order,
        order_id,
    )

    if not order:
        raise HTTPException(
            status_code=404,
            detail="Order not found.",
        )

    offers = db.scalars(
        select(DriverOffer)
        .where(
            DriverOffer.order_id == order_id,
            DriverOffer.outcome == "holding",
        )
        .order_by(
            DriverOffer.id.desc()
        )
    ).all()

    return [
        public_state(
            db,
            offer,
        )
        for offer in offers
    ]
