from datetime import datetime

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
)

from pydantic import BaseModel

from sqlalchemy import (
    func,
    select,
)

from sqlalchemy.orm import Session

from app.core.db import get_db

from app.services.driver_payouts import trigger_driver_payout

from app.models.entities import (
    Business,
    DeliveryEvent,
    Driver,
    Order,
    OrderStatus,
)


router = APIRouter(
    prefix="/driver-operations",
    tags=["driver-operations"],
)


ACTIVE_DELIVERY_STATUSES = {
    OrderStatus.DRIVER_ASSIGNED,
    OrderStatus.PICKUP_IN_PROGRESS,
    OrderStatus.OUT_FOR_DELIVERY,
    OrderStatus.DELIVERED,
}


def current_operating_day_id(
    db: Session,
):
    """
    MVP:
    use the most recent operating_day_id
    that has orders.

    This matches the current daily-number workflow.
    """

    return db.scalar(
        select(
            func.max(
                Order.operating_day_id
            )
        )
        .where(
            Order.operating_day_id
            .is_not(None)
        )
    )


def order_summary(
    db: Session,
    order: Order,
):
    customer = db.get(
        Business,
        order.business_id,
    )

    driver = (
        db.get(
            Driver,
            order.assigned_driver_id,
        )
        if order.assigned_driver_id
        else None
    )


    return {
        "id":
            order.id,

        "order_number":
            order.order_number,

        "daily_number":
            order.daily_number,

        "operating_day_id":
            order.operating_day_id,

        "status":
            order.status.value,

        "delivery_fee":
            float(
                order.delivery_fee
                or 0
            ),

        "driver_payout":
            (
                float(
                    order.driver_payout
                )
                if order.driver_payout
                is not None
                else None
            ),

        "route_distance_km":
            order.route_distance_km,

        "route_duration_minutes":
            order.route_duration_minutes,

        "total_load_units":
            order.total_load_units,

        "total_weight_kg":
            order.total_weight_kg,

        "total_volume_l":
            order.total_volume_l,

        "customer": {
            "id":
                customer.id
                if customer
                else None,

            "name":
                (
                    customer.business_name
                    or customer.owner_name
                )
                if customer
                else None,

            "owner_name":
                customer.owner_name
                if customer
                else None,

            "phone":
                customer.phone
                if customer
                else None,

            "alternate_phone":
                customer.alternate_phone
                if customer
                else None,

            "address":
                customer.address
                if customer
                else None,

            "landmark":
                customer.landmark
                if customer
                else None,

            "delivery_instructions":
                customer.delivery_instructions
                if customer
                else None,
        },

        "driver": (
            {
                "id":
                    driver.id,

                "name":
                    driver.name,

                "phone":
                    driver.phone,

                "vehicle_type":
                    driver.vehicle_type,

                "vehicle_registration":
                    driver.vehicle_registration,

                "current_area":
                    driver.current_area,
            }
            if driver
            else None
        ),
    }


# ============================================================
# FIND ORDER BY STOREDASH DATABASE ID
# ============================================================

@router.get(
    "/order/{order_id}",
)
def find_order_by_id(
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
            detail=(
                f"Order ID {order_id} "
                "was not found."
            ),
        )


    return order_summary(
        db,
        order,
    )


# ============================================================
# FIND TODAY'S ORDER BY DAILY NUMBER
# ============================================================

from app.models import DeliveryBatch

from app.services.batch_delivery_execution import (
    batch_execution_summary,
    get_active_batch_for_order,
    sync_batch_order_action,
    update_batch_stop,
)


@router.get(
    "/today/order/{daily_number}",
)
def find_today_order(
    daily_number: int,
    db: Session = Depends(get_db),
):
    day_id = current_operating_day_id(
        db
    )

    if day_id is None:
        raise HTTPException(
            status_code=404,
            detail=(
                "No current operating day "
                "with orders was found."
            ),
        )


    order = db.scalars(
        select(Order)
        .where(
            Order.operating_day_id
            == day_id,

            Order.daily_number
            == daily_number,
        )
    ).first()


    if not order:
        raise HTTPException(
            status_code=404,
            detail=(
                f"Order #{daily_number} "
                "was not found for today."
            ),
        )


    return order_summary(
        db,
        order,
    )


# ============================================================
# ACTIVE DELIVERIES
# ============================================================

@router.get(
    "/active",
)
def active_deliveries(
    db: Session = Depends(get_db),
):
    day_id = current_operating_day_id(
        db
    )

    if day_id is None:
        return []


    orders = db.scalars(
        select(Order)
        .where(
            Order.operating_day_id
            == day_id,

            Order.status.in_(
                ACTIVE_DELIVERY_STATUSES
            ),
        )
        .order_by(
            Order.daily_number
        )
    ).all()


    return [
        order_summary(
            db,
            order,
        )
        for order in orders
    ]


# ============================================================
# DELIVERY PROBLEMS
# ============================================================

@router.get(
    "/problems",
)
def problem_deliveries(
    db: Session = Depends(get_db),
):
    orders = db.scalars(
        select(Order)
        .where(
            Order.status
            == OrderStatus.FAILED
        )
        .order_by(
            Order.updated_at.desc()
        )
    ).all()


    return [
        order_summary(
            db,
            order,
        )
        for order in orders
    ]


# ============================================================
# COMPLETED TODAY
# ============================================================

@router.get(
    "/completed",
)
def completed_deliveries(
    db: Session = Depends(get_db),
):
    day_id = current_operating_day_id(
        db
    )

    if day_id is None:
        return []


    orders = db.scalars(
        select(Order)
        .where(
            Order.operating_day_id
            == day_id,

            Order.status
            == OrderStatus.COMPLETED,
        )
        .order_by(
            Order.daily_number
        )
    ).all()


    return [
        order_summary(
            db,
            order,
        )
        for order in orders
    ]


# ============================================================
# DELIVERY STATUS
# ============================================================

class DeliveryStatusRequest(
    BaseModel
):
    action: str

    operator_id: int | None = None

    notes: str | None = None


@router.post(
    "/orders/{order_id}/status",
)
def update_delivery_status(
    order_id: int,

    payload:
        DeliveryStatusRequest,

    db: Session = Depends(
        get_db
    ),
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


    action = (
        payload.action
        .strip()
        .lower()
    )


    # --------------------------------------------------------
    # DRIVER ARRIVES / STARTS PICKUP
    # --------------------------------------------------------

    if action == "start_pickup":

        if (
            order.status
            != OrderStatus.DRIVER_ASSIGNED
        ):
            raise HTTPException(
                status_code=409,
                detail=(
                    "Order must have an assigned "
                    "driver before pickup starts."
                ),
            )

        order.status = (
            OrderStatus.PICKUP_IN_PROGRESS
        )


    # --------------------------------------------------------
    # DRIVER HAS GOODS AND LEAVES
    # --------------------------------------------------------

    elif action == "out_for_delivery":

        if order.status not in {
            OrderStatus.DRIVER_ASSIGNED,
            OrderStatus.PICKUP_IN_PROGRESS,
        }:
            raise HTTPException(
                status_code=409,
                detail=(
                    "Order is not ready to go "
                    "out for delivery."
                ),
            )

        order.status = (
            OrderStatus.OUT_FOR_DELIVERY
        )


    # --------------------------------------------------------
    # DRIVER HANDED GOODS TO CUSTOMER
    # --------------------------------------------------------

    elif action == "delivered":

        if (
            order.status
            != OrderStatus.OUT_FOR_DELIVERY
        ):
            raise HTTPException(
                status_code=409,
                detail=(
                    "Order must be out for "
                    "delivery first."
                ),
            )

        order.status = (
            OrderStatus.DELIVERED
        )


    # --------------------------------------------------------
    # OPERATOR CLOSES DELIVERY
    # --------------------------------------------------------

    elif action == "deliver_and_complete":

        if (
            order.status
            != OrderStatus.OUT_FOR_DELIVERY
        ):
            raise HTTPException(
                status_code=409,
                detail=(
                    "Order must be out for delivery "
                    "before it can be completed."
                ),
            )


        # First record the delivery stage so the batch
        # delivery stop is completed correctly.
        order.status = (
            OrderStatus.DELIVERED
        )


        sync_batch_order_action(
            db,
            order=
                order,
            action=
                "delivered",
        )


        # Then immediately close the customer order.
        order.status = (
            OrderStatus.COMPLETED
        )


        order.completed_at = (
            datetime.utcnow()
        )


        active_batch = (
            get_active_batch_for_order(
                db,
                order.id,
            )
        )


        # Legacy / non-batch route:
        # completing this order releases the driver.
        if (
            active_batch is None
            and
            order.assigned_driver_id
        ):
            driver = db.get(
                Driver,
                order.assigned_driver_id,
            )

            if driver:
                driver.is_available = True


        # The normal sync call below must run the
        # final COMPLETE action. For a batch, this is
        # what releases the driver ONLY when every
        # linked order has finished.
        action = "complete"


    elif action == "problem":

        if (
            order.status
            not in (
                OrderStatus.DRIVER_ASSIGNED,
                OrderStatus.PICKUP_IN_PROGRESS,
                OrderStatus.OUT_FOR_DELIVERY,
            )
        ):
            raise HTTPException(
                status_code=409,
                detail=(
                    "Only an active delivery can "
                    "be marked as a problem."
                ),
            )


        if (
            not payload.notes
            or not payload.notes.strip()
        ):
            raise HTTPException(
                status_code=400,
                detail=(
                    "A reason is required for "
                    "a delivery problem."
                ),
            )


        order.status = (
            OrderStatus.FAILED
        )


        # IMPORTANT:
        # Do not release the rider here.
        # The delivery has not been resolved.


    elif action == "retry_delivery":

        if (
            order.status
            != OrderStatus.FAILED
        ):
            raise HTTPException(
                status_code=409,
                detail=(
                    "Only a problem delivery "
                    "can be retried."
                ),
            )


        if (
            not order.assigned_driver_id
        ):
            raise HTTPException(
                status_code=409,
                detail=(
                    "The order has no assigned driver."
                ),
            )


        order.status = (
            OrderStatus.OUT_FOR_DELIVERY
        )


        driver = db.get(
            Driver,
            order.assigned_driver_id,
        )

        if driver:
            driver.is_available = False


        action = "out_for_delivery"


    elif action == "complete":

        if (
            order.status
            != OrderStatus.DELIVERED
        ):
            raise HTTPException(
                status_code=409,
                detail=(
                    "Order must be marked "
                    "delivered first."
                ),
            )

        order.status = (
            OrderStatus.COMPLETED
        )

        order.completed_at = (
            datetime.utcnow()
        )


        active_batch = (
            get_active_batch_for_order(
                db,
                order.id,
            )
        )

        # Legacy/non-batched delivery:
        # preserve the old single-order behavior.
        if (
            active_batch is None
            and
            order.assigned_driver_id
        ):

            driver = db.get(
                Driver,
                order.assigned_driver_id,
            )

            if driver:
                driver.is_available = True


    else:
        raise HTTPException(
            status_code=400,
            detail=(
                "Unknown delivery action."
            ),
        )


    # A problem pauses this order without pretending
    # a pickup/drop stage was completed.
    completed_batch_id = None

    if action != "problem":
        synced_batch = sync_batch_order_action(
            db,
            order=
                order,
            action=
                action,
        )

        if (
            synced_batch is not None
            and synced_batch.status == "completed"
        ):
            completed_batch_id = (
                synced_batch.id
            )


    db.add(
        DeliveryEvent(
            order_id=
                order.id,

            event_type=
                action,

            details=
                payload.notes,

            created_by_id=
                payload.operator_id,
        )
    )


    # Commit the successful delivery FIRST.
    db.commit()

    # Money movement is deliberately separated from
    # delivery completion. A Hubtel outage must never
    # undo a completed customer delivery.
    if completed_batch_id is not None:
        trigger_driver_payout(
            db,
            batch_id=
                completed_batch_id,
        )


    return order_summary(
        db,
        order,
    )



class BatchStopStatusRequest(BaseModel):

    action: str

    actual_service_minutes: float | None = None

    operator_id: int | None = None

    notes: str | None = None


@router.post(
    "/batches/{batch_id}/stops/{stop_id}/status"
)
def update_batch_stop_status(
    batch_id: int,
    stop_id: int,
    payload: BatchStopStatusRequest,
    db: Session = Depends(
        get_db
    ),
):

    try:

        stop = update_batch_stop(
            db,

            batch_id=
                batch_id,

            stop_id=
                stop_id,

            action=
                payload.action,

            actual_service_minutes=
                payload.actual_service_minutes,
        )

        batch = db.get(
            DeliveryBatch,
            batch_id,
        )

        if batch is None:
            raise ValueError(
                "Batch disappeared."
            )


        db.commit()

        db.refresh(
            stop
        )

        db.refresh(
            batch
        )


        return (
            batch_execution_summary(
                db,
                batch,
            )
        )


    except ValueError as exc:

        db.rollback()

        raise HTTPException(
            status_code=409,
            detail=str(
                exc
            ),
        ) from exc
