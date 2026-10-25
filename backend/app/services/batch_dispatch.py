from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (
    BatchDriverOffer,
    BatchOrder,
    BatchStop,
    DeliveryBatch,
    Driver,
    Order,
    OrderStatus,
)

from app.services.batch_db_adapter import (
    build_order_routing_input,
    get_driver_routing_context,
)

from app.services.batch_planner import (
    plan_batch_route,
)


ACTIVE_BATCH_STATUSES = {
    "proposed",
    "offered",
    "assigned",
    "in_progress",
}


def money(
    value: float | Decimal,
) -> Decimal:
    return Decimal(
        str(value)
    ).quantize(
        Decimal("0.01")
    )


def ensure_orders_not_in_active_batch(
    db: Session,
    order_ids: list[int],
):
    existing = db.execute(
        select(
            BatchOrder.order_id,
            DeliveryBatch.id,
            DeliveryBatch.status,
        )
        .join(
            DeliveryBatch,
            DeliveryBatch.id
            ==
            BatchOrder.batch_id,
        )
        .where(
            BatchOrder.order_id.in_(
                order_ids
            ),

            DeliveryBatch.status.in_(
                ACTIVE_BATCH_STATUSES
            ),
        )
    ).all()

    if existing:
        details = ", ".join(
            (
                f"order {row.order_id} "
                f"in batch {row.id}"
            )
            for row in existing
        )

        raise ValueError(
            "Order already belongs to an active batch: "
            + details
        )


from app.services.batch_route_pricing import default_driver_offer_ceiling, price_batch_plan

def create_proposed_batch(
    db: Session,
    *,
    driver_id: int,
    order_ids: list[int],
    driver_vehicle_id: int | None = None,
    duration_multiplier: float = 1.0,
    max_total_route_minutes: float | None = None,
) -> DeliveryBatch:

    if not order_ids:
        raise ValueError(
            "At least one order is required."
        )

    order_ids = list(
        dict.fromkeys(
            int(value)
            for value
            in order_ids
        )
    )

    context = (
        get_driver_routing_context(
            db,

            driver_id=
                driver_id,

            driver_vehicle_id=
                driver_vehicle_id,
        )
    )

    orders = list(
        db.scalars(
            select(Order)
            .where(
                Order.id.in_(
                    order_ids
                )
            )
        ).all()
    )

    found = {
        order.id
        for order in orders
    }

    missing = [
        order_id
        for order_id in order_ids
        if order_id not in found
    ]

    if missing:
        raise ValueError(
            "Orders not found: "
            + ", ".join(
                str(value)
                for value in missing
            )
        )

    ensure_orders_not_in_active_batch(
        db,
        order_ids,
    )

    by_id = {
        order.id:
            order
        for order in orders
    }

    inputs = []

    for order_id in order_ids:

        order = by_id[
            order_id
        ]

        if (
            order.status
            !=
            OrderStatus.READY_FOR_DISPATCH
        ):
            raise ValueError(
                f"Order {order.id} is not READY_FOR_DISPATCH."
            )

        if order.assigned_driver_id is not None:
            raise ValueError(
                f"Order {order.id} already has a driver."
            )

        built = (
            build_order_routing_input(
                db,
                order,
            )
        )

        inputs.append(
            built.input
        )

    plan = plan_batch_route(
        orders=
            inputs,

        capacity=
            context.capacity,

        duration_multiplier=
            duration_multiplier,

        max_total_route_minutes=
            max_total_route_minutes,
    )

    if not plan.feasible:
        raise ValueError(
            "Batch route is not feasible: "
            + str(
                plan.rejection_reason
            )
        )

    pricing = (
        price_batch_plan(
            context=
                context,

            plan=
                plan,

            orders=
                orders,
        )
    )

    batch = DeliveryBatch(
        status=
            "proposed",

        driver_id=
            context.driver.id,

        driver_vehicle_id=
            context.vehicle.id,

        single_trip_required=
            True,

        capacity_feasible=
            True,

        order_count=
            plan.order_count,

        pickup_count=
            plan.pickup_count,

        delivery_count=
            plan.delivery_count,

        planned_distance_km=
            plan.total_distance_km,

        planned_minutes=
            plan.total_route_minutes,

        peak_weight_kg=
            plan.peak_weight_kg,

        peak_volume_l=
            plan.peak_volume_l,

        customer_delivery_revenue=
            money(
                plan.customer_delivery_revenue
            ),

        predicted_driver_payout=
            money(
                pricing.predicted_driver_payout
            ),

        predicted_contribution=
            money(
                pricing.predicted_contribution
            ),

        predicted_margin_rate=
            pricing.predicted_margin_rate,

        notes=
            (
                "route_economics="
                + pricing.economics_version
                + "; pricing_policy="
                + pricing.policy_version
            ),

        planner_version=
            plan.planner_version,

        road_provider=
            plan.road_provider,

        traffic_aware=
            plan.traffic_aware,

        recommended_at=
            datetime.utcnow(),
    )

    db.add(
        batch
    )

    db.flush()


    delivery_sequence = {}

    delivery_counter = 0

    for stop in plan.stops:
        if (
            stop.stop_type
            ==
            "delivery"
            and
            stop.order_id
            is not None
        ):
            delivery_counter += 1

            delivery_sequence[
                stop.order_id
            ] = (
                delivery_counter
            )


    for order_input in inputs:

        total_weight = sum(
            float(
                pickup.weight_kg
            )
            for pickup
            in order_input.pickups
        )

        total_volume = sum(
            float(
                pickup.volume_l
            )
            for pickup
            in order_input.pickups
        )

        db.add(
            BatchOrder(
                batch_id=
                    batch.id,

                order_id=
                    order_input.order_id,

                order_weight_kg=
                    round(
                        total_weight,
                        3,
                    ),

                order_volume_l=
                    round(
                        total_volume,
                        3,
                    ),

                customer_delivery_fee=
                    money(
                        order_input.delivery_fee
                    ),

                delivery_sequence=
                    delivery_sequence.get(
                        order_input.order_id
                    ),

                status=
                    "proposed",
            )
        )


    for stop in plan.stops:

        business_id = None

        if (
            stop.stop_type
            ==
            "delivery"
            and
            stop.order_id
            is not None
        ):
            order = by_id.get(
                stop.order_id
            )

            if order is not None:
                business_id = (
                    order.business_id
                )

        db.add(
            BatchStop(
                batch_id=
                    batch.id,

                sequence=
                    stop.sequence,

                stop_type=
                    stop.stop_type,

                order_id=
                    stop.order_id,

                supplier_id=
                    stop.supplier_id,

                business_id=
                    business_id,

                latitude=
                    stop.latitude,

                longitude=
                    stop.longitude,

                location_label=
                    stop.location_label,

                weight_delta_kg=
                    stop.weight_delta_kg,

                volume_delta_l=
                    stop.volume_delta_l,

                load_weight_after_kg=
                    stop.load_weight_after_kg,

                load_volume_after_l=
                    stop.load_volume_after_l,

                planned_leg_distance_km=
                    stop.travel_from_previous_km,

                planned_leg_minutes=
                    stop.travel_from_previous_minutes,

                planned_arrival_offset_minutes=
                    stop.arrival_minutes,

                planned_service_minutes=
                    stop.service_minutes,

                status=
                    "pending",
            )
        )

    db.commit()

    db.refresh(
        batch
    )

    return batch


def create_batch_driver_offer(
    db: Session,
    *,
    batch_id: int,
    opening_offer: float | None = None,
    operator_id: int | None = None,
    maximum_authorized_payout: float | None = None,
    notes: str | None = None,
) -> BatchDriverOffer:

    batch = db.get(
        DeliveryBatch,
        batch_id,
    )

    if batch is None:
        raise ValueError(
            "Batch not found."
        )

    if batch.status not in {
        "proposed",
        "offered",
    }:
        raise ValueError(
            "Batch is not available for a driver offer."
        )

    if batch.driver_id is None:
        raise ValueError(
            "Batch has no proposed driver."
        )

    driver = db.get(
        Driver,
        batch.driver_id,
    )

    if driver is None:
        raise ValueError(
            "Driver not found."
        )

    if not driver.is_active:
        raise ValueError(
            "Driver is inactive."
        )

    if not driver.is_available:
        raise ValueError(
            "Driver is unavailable."
        )

    if batch.predicted_driver_payout is None:
        raise ValueError(
            "Batch has no system-predicted driver payout."
        )

    recommended = money(
        batch.predicted_driver_payout
    )

    if recommended <= 0:
        raise ValueError(
            "Recommended route payout must be positive."
        )

    if opening_offer is None:
        opening = recommended
    else:
        opening = money(
            opening_offer
        )

    if opening <= 0:
        raise ValueError(
            "Opening offer must be positive."
        )

    if maximum_authorized_payout is None:

        maximum = money(
            default_driver_offer_ceiling(
                float(
                    recommended
                )
            )
        )

        if opening > maximum:
            maximum = opening

    else:

        maximum = money(
            maximum_authorized_payout
        )

        if maximum <= 0:
            raise ValueError(
                "Maximum payout must be positive."
            )

        if opening > maximum:
            raise ValueError(
                "Opening offer exceeds authorized maximum."
            )

    offer = BatchDriverOffer(
        batch_id=
            batch.id,

        driver_id=
            driver.id,

        operator_id=
            operator_id,

        recommended_payout=
            recommended,

        opening_offer=
            opening,

        maximum_authorized_payout=
            maximum,

        outcome=
            "pending",

        notes=
            notes,
    )

    db.add(
        offer
    )

    batch.status = (
        "offered"
    )

    db.commit()

    db.refresh(
        offer
    )

    return offer



def decline_batch_driver_offer(
    db: Session,
    *,
    batch_id: int,
    offer_id: int,
    notes: str | None = None,
) -> BatchDriverOffer:

    batch = db.get(
        DeliveryBatch,
        batch_id,
    )

    if batch is None:
        raise ValueError(
            "Batch not found."
        )

    offer = db.get(
        BatchDriverOffer,
        offer_id,
    )

    if (
        offer is None
        or offer.batch_id != batch.id
    ):
        raise ValueError(
            "Batch offer not found."
        )

    if offer.outcome != "pending":
        raise ValueError(
            "Offer is no longer pending."
        )

    now = datetime.utcnow()

    offer.outcome = "declined"
    offer.responded_at = now

    if notes:
        offer.notes = notes

    # No order was assigned yet.
    # Release this proposed route so the same orders
    # can be offered to another rider.
    batch.status = "declined"

    links = list(
        db.scalars(
            select(BatchOrder)
            .where(
                BatchOrder.batch_id
                ==
                batch.id
            )
        ).all()
    )

    for link in links:
        link.status = "released"

    db.commit()

    db.refresh(
        offer
    )

    return offer



def accept_batch_driver_offer(
    db: Session,
    *,
    batch_id: int,
    offer_id: int,
    final_payout: float | None = None,
) -> DeliveryBatch:

    batch = db.get(
        DeliveryBatch,
        batch_id,
    )

    if batch is None:
        raise ValueError(
            "Batch not found."
        )

    offer = db.get(
        BatchDriverOffer,
        offer_id,
    )

    if (
        offer is None
        or
        offer.batch_id != batch.id
    ):
        raise ValueError(
            "Batch offer not found."
        )

    if offer.outcome != "pending":
        raise ValueError(
            "Offer is no longer pending."
        )

    driver = db.get(
        Driver,
        offer.driver_id,
    )

    if driver is None:
        raise ValueError(
            "Driver not found."
        )

    if not driver.is_active:
        raise ValueError(
            "Driver is inactive."
        )

    if not driver.is_available:
        raise ValueError(
            "Driver is no longer available."
        )

    payout = money(
        final_payout
        if final_payout is not None
        else offer.opening_offer
    )

    if payout <= 0:
        raise ValueError(
            "Final payout must be positive."
        )

    if (
        offer.maximum_authorized_payout
        is not None
        and
        payout
        >
        money(
            offer.maximum_authorized_payout
        )
    ):
        raise ValueError(
            "Final payout exceeds authorized maximum."
        )

    batch_orders = list(
        db.scalars(
            select(BatchOrder)
            .where(
                BatchOrder.batch_id
                ==
                batch.id
            )
            .order_by(
                BatchOrder.id.asc()
            )
        ).all()
    )

    if not batch_orders:
        raise ValueError(
            "Batch contains no orders."
        )

    orders = []

    for link in batch_orders:

        order = db.get(
            Order,
            link.order_id,
        )

        if order is None:
            raise ValueError(
                f"Order {link.order_id} disappeared."
            )

        if (
            order.status
            !=
            OrderStatus.READY_FOR_DISPATCH
        ):
            raise ValueError(
                f"Order {order.id} is no longer ready for dispatch."
            )

        if order.assigned_driver_id is not None:
            raise ValueError(
                f"Order {order.id} already has a driver."
            )

        orders.append(
            order
        )

    now = datetime.utcnow()

    # ========================================================
    # ATOMIC ASSIGNMENT
    #
    # One accepted route assigns every order in that route.
    # ========================================================

    for order in orders:

        order.assigned_driver_id = (
            driver.id
        )

        # Driver payout belongs to the BATCH, not each order.
        # Leave the legacy per-order driver_payout field empty.
        order.driver_payout = None

        order.driver_assigned_at = (
            now
        )

        order.status = (
            OrderStatus.DRIVER_ASSIGNED
        )

    for link in batch_orders:
        link.status = (
            "assigned"
        )

    batch.status = (
        "assigned"
    )

    batch.driver_id = (
        driver.id
    )

    batch.accepted_driver_payout = (
        payout
    )

    batch.predicted_contribution = (
        money(
            batch.customer_delivery_revenue
        )
        -
        payout
    )

    revenue = float(
        batch.customer_delivery_revenue
        or 0
    )

    if revenue > 0:
        batch.predicted_margin_rate = (
            float(
                batch.predicted_contribution
            )
            /
            revenue
        )

    offer.final_payout = (
        payout
    )

    offer.outcome = (
        "accepted"
    )

    offer.responded_at = (
        now
    )

    offer.locked_at = (
        now
    )

    other_offers = list(
        db.scalars(
            select(
                BatchDriverOffer
            )
            .where(
                BatchDriverOffer.batch_id
                ==
                batch.id,

                BatchDriverOffer.id
                !=
                offer.id,

                BatchDriverOffer.outcome
                ==
                "pending",
            )
        ).all()
    )

    for other in other_offers:
        other.outcome = (
            "expired"
        )

        other.responded_at = (
            now
        )

    driver.is_available = (
        False
    )

    db.commit()

    db.refresh(
        batch
    )

    return batch
