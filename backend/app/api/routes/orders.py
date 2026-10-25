import json

from datetime import datetime

from zoneinfo import ZoneInfo

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    status,
)

from sqlalchemy import (
    func,
    select,
)

from sqlalchemy.orm import (
    Session,
    selectinload,
)

from app.core.config import settings
from app.core.db import get_db

from app.models import (
    AuditEvent,
    Business,
    OperatingDay,
    Order,
    OrderItem,
    OrderStatus,
)

from app.schemas.order import (
    OrderCreate,
    OrderDraftUpdate,
    OrderRead,
)


router = APIRouter(
    prefix="/orders",
    tags=["orders"],
)


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
    statement = (
        select(Order)
        .options(
            selectinload(
                Order.items
            )
        )
        .where(
            Order.id == order_id
        )
    )

    return db.scalars(
        statement
    ).first()


def get_or_create_operating_day(
    db: Session,
) -> OperatingDay:
    now = ghana_now()

    today = now.date()

    operating_day = db.scalars(
        select(
            OperatingDay
        ).where(
            OperatingDay.business_date
            == today
        )
    ).first()

    if operating_day:
        if operating_day.is_closed:
            raise HTTPException(
                status_code=409,
                detail=(
                    "Today's StoreDash operating day "
                    "has already been closed."
                ),
            )

        return operating_day


    operating_day = OperatingDay(
        business_date=today,
        opened_at=now,
        is_closed=False,
    )

    db.add(
        operating_day
    )

    db.flush()

    return operating_day


def next_daily_number(
    db: Session,
    operating_day_id: int,
) -> int:
    highest = db.scalar(
        select(
            func.max(
                Order.daily_number
            )
        ).where(
            Order.operating_day_id
            == operating_day_id
        )
    )

    return int(
        highest or 0
    ) + 1


def audit(
    db: Session,
    *,
    action: str,
    entity_type: str,
    entity_id: int | None,
    actor_id: int | None = None,
    before: dict | None = None,
    after: dict | None = None,
):
    event = AuditEvent(
        actor_id=actor_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        before_json=(
            json.dumps(before)
            if before
            else None
        ),
        after_json=(
            json.dumps(after)
            if after
            else None
        ),
    )

    db.add(event)


@router.post(
    "",
    response_model=OrderRead,
    status_code=status.HTTP_201_CREATED,
)
def create_order(
    payload: OrderCreate,
    db: Session = Depends(get_db),
):
    now = ghana_now()


    if (
        settings.enforce_operating_hours
        and now.hour
        >= settings.operating_cutoff_hour
    ):
        raise HTTPException(
            status_code=409,
            detail=(
                "StoreDash is closed for new orders "
                "for today. New orders resume on "
                "the next operating day."
            ),
        )


    business = db.get(
        Business,
        payload.business_id,
    )


    if not business:
        raise HTTPException(
            status_code=404,
            detail="Customer not found",
        )


    operating_day = (
        get_or_create_operating_day(
            db
        )
    )


    daily_number = (
        next_daily_number(
            db,
            operating_day.id,
        )
    )


    order = Order(
        operating_day_id=(
            operating_day.id
        ),

        daily_number=(
            daily_number
        ),

        business_id=(
            payload.business_id
        ),

        operator_id=(
            payload.operator_id
        ),

        notes=payload.notes,

        status=OrderStatus.DRAFT,
    )


    order.items = [
        OrderItem(
            **item.model_dump()
        )
        for item
        in payload.items
    ]


    db.add(order)

    db.flush()


    audit(
        db,
        action="order_created",
        entity_type="order",
        entity_id=order.id,
        actor_id=payload.operator_id,
        after={
            "daily_number":
                daily_number,

            "business_id":
                payload.business_id,

            "status":
                "draft",
        },
    )


    db.commit()


    return load_order(
        db,
        order.id,
    )


@router.get(
    "",
    response_model=list[
        OrderRead
    ],
)
def list_orders(
    business_id: int | None = Query(
        default=None
    ),

    supplier_id: int | None = Query(
        default=None
    ),

    operating_day_id: int | None = Query(
        default=None
    ),

    order_status: str | None = Query(
        default=None,
        alias="status",
    ),

    db: Session = Depends(
        get_db
    ),
):
    statement = (
        select(Order)
        .options(
            selectinload(
                Order.items
            )
        )
        .order_by(
            Order.created_at.desc()
        )
    )


    if business_id is not None:
        statement = statement.where(
            Order.business_id
            == business_id
        )


    if operating_day_id is not None:
        statement = statement.where(
            Order.operating_day_id
            == operating_day_id
        )


    if order_status is not None:
        try:
            parsed_status = OrderStatus(
                order_status
            )

        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=(
                    "Invalid order status."
                ),
            )

        statement = statement.where(
            Order.status
            == parsed_status
        )


    if supplier_id is not None:
        statement = (
            statement
            .join(OrderItem)
            .where(
                OrderItem.supplier_id
                == supplier_id
            )
            .distinct()
        )


    return db.scalars(
        statement
    ).unique().all()


@router.get(
    "/{order_id}",
    response_model=OrderRead,
)
def get_order(
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
            detail="Order not found",
        )


    return order


@router.put(
    "/{order_id}/draft",
    response_model=OrderRead,
)
def update_draft(
    order_id: int,
    payload: OrderDraftUpdate,
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
            detail="Order not found",
        )


    if order.status not in {
        OrderStatus.DRAFT,
        OrderStatus.SOURCING,
        OrderStatus.QUOTE_READY,
        OrderStatus.AWAITING_BUYER_APPROVAL,
    }:
        raise HTTPException(
            status_code=409,
            detail=(
                "Finalized orders are locked "
                "and cannot be edited."
            ),
        )


    before = {
        "notes":
            order.notes,

        "items": [
            {
                "name":
                    item.name,

                "quantity":
                    item.requested_quantity,

                "unit":
                    item.unit,
            }
            for item
            in order.items
        ],
    }


    order.notes = (
        payload.notes
    )

    # Changing the order invalidates
    # all previous sourcing and quote approval.
    order.status = OrderStatus.DRAFT

    order.quote_generated_at = None
    order.customer_approved_at = None

    order.goods_total = 0
    order.delivery_fee = 0
    order.service_fee = 0
    order.final_total = 0


    order.items.clear()


    for item in payload.items:
        order.items.append(
            OrderItem(
                **item.model_dump()
            )
        )


    db.flush()


    audit(
        db,
        action="draft_updated",
        entity_type="order",
        entity_id=order.id,
        actor_id=order.operator_id,
        before=before,
        after={
            "notes":
                payload.notes,

            "items": [
                {
                    "name":
                        item.name,

                    "quantity":
                        item.requested_quantity,

                    "unit":
                        item.unit,
                }
                for item
                in payload.items
            ],
        },
    )


    db.commit()


    return load_order(
        db,
        order.id,
    )


@router.post(
    "/{order_id}/finalize",
    response_model=OrderRead,
)
def finalize_order(
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
            detail="Order not found",
        )


    if (
        order.status
        !=
        OrderStatus.AWAITING_BUYER_APPROVAL
    ):
        raise HTTPException(
            status_code=409,
            detail=(
                "Order must be sourced and quoted "
                "before it can be finalized."
            ),
        )


    if (
        order.quote_generated_at
        is None
    ):
        raise HTTPException(
            status_code=409,
            detail=(
                "Generate a customer quote first."
            ),
        )


    if (
        order.customer_approved_at
        is None
    ):
        raise HTTPException(
            status_code=409,
            detail=(
                "Customer approval must be recorded "
                "before finalizing."
            ),
        )


    order.status = (
        OrderStatus.ACTIVE
    )

    order.finalized_at = (
        ghana_now()
    )


    audit(
        db,
        action="order_finalized",
        entity_type="order",
        entity_id=order.id,
        actor_id=order.operator_id,
        before={
            "status":
                "awaiting_buyer_approval"
        },
        after={
            "status":
                "active",

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


@router.post(
    "/{order_id}/complete",
    response_model=OrderRead,
)
def complete_order(
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
            detail="Order not found",
        )


    if (
        order.status
        != OrderStatus.ACTIVE
    ):
        raise HTTPException(
            status_code=409,
            detail=(
                "Only active orders "
                "can be completed."
            ),
        )


    order.status = (
        OrderStatus.COMPLETED
    )

    order.completed_at = (
        ghana_now()
    )


    audit(
        db,
        action="order_completed",
        entity_type="order",
        entity_id=order.id,
        actor_id=order.operator_id,
        before={
            "status":
                "active"
        },
        after={
            "status":
                "completed"
        },
    )


    db.commit()


    return load_order(
        db,
        order.id,
    )
