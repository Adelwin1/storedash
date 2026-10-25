from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (
    BatchOrder,
    BatchStop,
    DeliveryBatch,
    Driver,
    Order,
    OrderStatus,
)


ACTIVE_BATCH_STATUSES = {
    "assigned",
    "in_progress",
}


def get_active_batch_for_order(
    db: Session,
    order_id: int,
) -> DeliveryBatch | None:

    return db.scalars(
        select(DeliveryBatch)
        .join(
            BatchOrder,
            BatchOrder.batch_id
            ==
            DeliveryBatch.id,
        )
        .where(
            BatchOrder.order_id
            ==
            order_id,

            DeliveryBatch.status.in_(
                ACTIVE_BATCH_STATUSES
            ),
        )
        .order_by(
            DeliveryBatch.id.desc()
        )
    ).first()


def _batch_links(
    db: Session,
    batch_id: int,
) -> list[BatchOrder]:

    return list(
        db.scalars(
            select(BatchOrder)
            .where(
                BatchOrder.batch_id
                ==
                batch_id
            )
            .order_by(
                BatchOrder.id.asc()
            )
        ).all()
    )


def _batch_stops(
    db: Session,
    batch_id: int,
) -> list[BatchStop]:

    return list(
        db.scalars(
            select(BatchStop)
            .where(
                BatchStop.batch_id
                ==
                batch_id
            )
            .order_by(
                BatchStop.sequence.asc()
            )
        ).all()
    )


def _mark_batch_started(
    batch: DeliveryBatch,
    now: datetime,
):

    if batch.status == "assigned":
        batch.status = "in_progress"

    if batch.started_at is None:
        batch.started_at = now


def finalize_batch_if_complete(
    db: Session,
    batch: DeliveryBatch,
) -> bool:

    links = _batch_links(
        db,
        batch.id,
    )

    stops = _batch_stops(
        db,
        batch.id,
    )

    if not links:
        return False


    orders = []

    for link in links:

        order = db.get(
            Order,
            link.order_id,
        )

        if order is None:
            return False

        orders.append(
            order
        )


    all_orders_complete = all(
        order.status
        ==
        OrderStatus.COMPLETED
        for order in orders
    )

    all_stops_complete = all(
        stop.status
        ==
        "completed"
        for stop in stops
    )


    if not (
        all_orders_complete
        and
        all_stops_complete
    ):

        if batch.driver_id:

            driver = db.get(
                Driver,
                batch.driver_id,
            )

            if driver:
                driver.is_available = False

        return False


    now = datetime.utcnow()

    batch.status = "completed"

    if batch.completed_at is None:
        batch.completed_at = now


    for link in links:
        link.status = "completed"


    if batch.actual_driver_payout is None:

        batch.actual_driver_payout = (
            batch.accepted_driver_payout
        )


    if (
        batch.actual_driver_payout
        is not None
    ):

        batch.actual_contribution = (
            batch.customer_delivery_revenue
            -
            batch.actual_driver_payout
        )

        revenue = float(
            batch.customer_delivery_revenue
            or 0
        )

        if revenue > 0:

            batch.actual_margin_rate = (
                float(
                    batch.actual_contribution
                )
                /
                revenue
            )


    if batch.driver_id:

        driver = db.get(
            Driver,
            batch.driver_id,
        )

        if driver:
            driver.is_available = True


    return True


def sync_batch_order_action(
    db: Session,
    *,
    order: Order,
    action: str,
) -> DeliveryBatch | None:

    batch = get_active_batch_for_order(
        db,
        order.id,
    )

    if batch is None:
        return None


    now = datetime.utcnow()

    _mark_batch_started(
        batch,
        now,
    )


    link = db.scalars(
        select(BatchOrder)
        .where(
            BatchOrder.batch_id
            ==
            batch.id,

            BatchOrder.order_id
            ==
            order.id,
        )
    ).first()


    if link:

        status_map = {
            "start_pickup":
                "pickup_in_progress",

            "out_for_delivery":
                "out_for_delivery",

            "delivered":
                "delivered",

            "complete":
                "completed",
        }

        if action in status_map:

            link.status = (
                status_map[
                    action
                ]
            )


    # --------------------------------------------------------
    # Once every order has left the pickup phase, every
    # planned pickup must already have occurred.
    #
    # This keeps the existing order API compatible while the
    # explicit BatchStop API gives us more precise stop data.
    # --------------------------------------------------------

    if action == "out_for_delivery":

        links = _batch_links(
            db,
            batch.id,
        )

        all_collected = True

        collected_statuses = {
            OrderStatus.OUT_FOR_DELIVERY,
            OrderStatus.DELIVERED,
            OrderStatus.COMPLETED,
        }

        for candidate in links:

            candidate_order = db.get(
                Order,
                candidate.order_id,
            )

            if (
                candidate_order is None
                or
                candidate_order.status
                not in collected_statuses
            ):
                all_collected = False
                break


        if all_collected:

            for stop in _batch_stops(
                db,
                batch.id,
            ):

                if (
                    stop.stop_type
                    ==
                    "pickup"
                    and
                    stop.status
                    !=
                    "completed"
                ):

                    stop.status = "completed"

                    if stop.actual_arrival_at is None:
                        stop.actual_arrival_at = now


    # Delivery at the customer is a real completed
    # delivery stop for this particular order.

    if action == "delivered":

        stop = db.scalars(
            select(BatchStop)
            .where(
                BatchStop.batch_id
                ==
                batch.id,

                BatchStop.stop_type
                ==
                "delivery",

                BatchStop.order_id
                ==
                order.id,
            )
        ).first()

        if stop:

            stop.status = "completed"

            if stop.actual_arrival_at is None:
                stop.actual_arrival_at = now


    if action == "complete":

        finalize_batch_if_complete(
            db,
            batch,
        )


    if batch.driver_id:

        driver = db.get(
            Driver,
            batch.driver_id,
        )

        if (
            driver
            and
            batch.status
            !=
            "completed"
        ):
            driver.is_available = False


    return batch


def update_batch_stop(
    db: Session,
    *,
    batch_id: int,
    stop_id: int,
    action: str,
    actual_service_minutes: float | None = None,
) -> BatchStop:

    batch = db.get(
        DeliveryBatch,
        batch_id,
    )

    if batch is None:
        raise ValueError(
            "Batch not found."
        )

    if batch.status not in {
        "assigned",
        "in_progress",
    }:
        raise ValueError(
            "Batch is not currently executing."
        )


    stop = db.get(
        BatchStop,
        stop_id,
    )

    if (
        stop is None
        or
        stop.batch_id
        !=
        batch.id
    ):
        raise ValueError(
            "Batch stop not found."
        )


    action = (
        action
        .strip()
        .lower()
    )

    if action not in {
        "arrive",
        "complete",
    }:
        raise ValueError(
            "Stop action must be arrive or complete."
        )


    if (
        actual_service_minutes
        is not None
        and
        actual_service_minutes
        <
        0
    ):
        raise ValueError(
            "Actual service minutes cannot be negative."
        )


    previous_incomplete = db.scalars(
        select(BatchStop)
        .where(
            BatchStop.batch_id
            ==
            batch.id,

            BatchStop.sequence
            <
            stop.sequence,

            BatchStop.status
            !=
            "completed",
        )
        .order_by(
            BatchStop.sequence.asc()
        )
    ).first()

    if previous_incomplete:

        raise ValueError(
            "Previous batch stop "
            f"{previous_incomplete.sequence} "
            "must be completed first."
        )


    now = datetime.utcnow()

    _mark_batch_started(
        batch,
        now,
    )


    if action == "arrive":

        if stop.status == "completed":
            return stop

        stop.status = "arrived"

        if stop.actual_arrival_at is None:
            stop.actual_arrival_at = now


    elif action == "complete":

        if stop.status == "completed":
            return stop

        if stop.actual_arrival_at is None:
            stop.actual_arrival_at = now

        stop.status = "completed"

        if actual_service_minutes is not None:
            stop.actual_service_minutes = (
                actual_service_minutes
            )


        if (
            stop.stop_type
            ==
            "delivery"
            and
            stop.order_id
            is not None
        ):

            order = db.get(
                Order,
                stop.order_id,
            )

            if order is None:
                raise ValueError(
                    "Delivery stop order was not found."
                )

            if (
                order.status
                ==
                OrderStatus.OUT_FOR_DELIVERY
            ):

                order.status = (
                    OrderStatus.DELIVERED
                )

            elif order.status not in {
                OrderStatus.DELIVERED,
                OrderStatus.COMPLETED,
            }:

                raise ValueError(
                    "Order must be OUT_FOR_DELIVERY "
                    "before its delivery stop can complete."
                )


            link = db.scalars(
                select(BatchOrder)
                .where(
                    BatchOrder.batch_id
                    ==
                    batch.id,

                    BatchOrder.order_id
                    ==
                    order.id,
                )
            ).first()

            if (
                link
                and
                link.status
                !=
                "completed"
            ):
                link.status = "delivered"


    if batch.driver_id:

        driver = db.get(
            Driver,
            batch.driver_id,
        )

        if driver:
            driver.is_available = False


    finalize_batch_if_complete(
        db,
        batch,
    )

    return stop


def batch_execution_summary(
    db: Session,
    batch: DeliveryBatch,
):

    driver = (
        db.get(
            Driver,
            batch.driver_id,
        )
        if batch.driver_id
        else None
    )

    return {
        "batch_id":
            batch.id,

        "status":
            batch.status,

        "driver_id":
            batch.driver_id,

        "driver_available":
            (
                driver.is_available
                if driver
                else None
            ),

        "started_at":
            batch.started_at,

        "completed_at":
            batch.completed_at,

        "orders": [
            {
                "order_id":
                    link.order_id,

                "status":
                    link.status,
            }
            for link
            in _batch_links(
                db,
                batch.id,
            )
        ],

        "stops": [
            {
                "id":
                    stop.id,

                "sequence":
                    stop.sequence,

                "stop_type":
                    stop.stop_type,

                "order_id":
                    stop.order_id,

                "supplier_id":
                    stop.supplier_id,

                "status":
                    stop.status,

                "actual_arrival_at":
                    stop.actual_arrival_at,

                "actual_service_minutes":
                    stop.actual_service_minutes,
            }
            for stop
            in _batch_stops(
                db,
                batch.id,
            )
        ],
    }
