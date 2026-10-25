import json

from datetime import datetime

from decimal import Decimal

from zoneinfo import ZoneInfo

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
)

from sqlalchemy import (
    func,
    select,
)

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.db import get_db

from app.models import (
    AuditEvent,
    OperatingDay,
    Order,
    OrderStatus,
)

from app.schemas.operating_day import (
    OperatingDayRead,
    OperatingDaySummary,
)


router = APIRouter(
    prefix="/operating-days",
    tags=["operating-days"],
)


def ghana_now() -> datetime:
    return datetime.now(
        ZoneInfo(
            settings.operating_timezone
        )
    ).replace(
        tzinfo=None
    )


def get_current_day(
    db: Session,
):
    return db.scalars(
        select(
            OperatingDay
        ).where(
            OperatingDay.business_date
            == ghana_now().date()
        )
    ).first()


def build_summary(
    db: Session,
    day: OperatingDay,
):
    orders = db.scalars(
        select(
            Order
        ).where(
            Order.operating_day_id
            == day.id
        )
    ).all()


    def total_for(field):
        return sum(
            (
                Decimal(
                    str(
                        getattr(
                            order,
                            field,
                        )
                        or 0
                    )
                )
                for order
                in orders
            ),
            Decimal("0"),
        )


    return OperatingDaySummary(
        id=day.id,

        business_date=(
            day.business_date
        ),

        opened_at=(
            day.opened_at
        ),

        closed_at=(
            day.closed_at
        ),

        is_closed=(
            day.is_closed
        ),

        closed_by_id=(
            day.closed_by_id
        ),

        notes=day.notes,

        total_orders=len(
            orders
        ),

        draft_orders=sum(
            order.status in {
                OrderStatus.DRAFT,
                OrderStatus.SOURCING,
                OrderStatus.QUOTE_READY,
                OrderStatus.AWAITING_BUYER_APPROVAL,
            }
            for order
            in orders
        ),

        active_orders=sum(
            order.status
            not in {
                OrderStatus.DRAFT,
                OrderStatus.SOURCING,
                OrderStatus.QUOTE_READY,
                OrderStatus.AWAITING_BUYER_APPROVAL,
                OrderStatus.COMPLETED,
                OrderStatus.CANCELLED,
                OrderStatus.FAILED,
            }
            for order
            in orders
        ),

        completed_orders=sum(
            order.status
            == OrderStatus.COMPLETED
            for order
            in orders
        ),

        cancelled_orders=sum(
            order.status
            == OrderStatus.CANCELLED
            for order
            in orders
        ),

        failed_orders=sum(
            order.status
            == OrderStatus.FAILED
            for order
            in orders
        ),

        goods_total=total_for(
            "goods_total"
        ),

        delivery_fee_total=total_for(
            "delivery_fee"
        ),

        service_fee_total=total_for(
            "service_fee"
        ),

        final_total=total_for(
            "final_total"
        ),
    )


@router.get(
    "",
    response_model=list[
        OperatingDayRead
    ],
)
def list_operating_days(
    db: Session = Depends(
        get_db
    ),
):
    return db.scalars(
        select(
            OperatingDay
        ).order_by(
            OperatingDay.business_date.desc()
        )
    ).all()


@router.get(
    "/current",
    response_model=(
        OperatingDaySummary
        | None
    ),
)
def current_operating_day(
    db: Session = Depends(
        get_db
    ),
):
    day = get_current_day(
        db
    )


    if not day:
        return None


    return build_summary(
        db,
        day,
    )


@router.get(
    "/{day_id}",
    response_model=OperatingDaySummary,
)
def operating_day_details(
    day_id: int,
    db: Session = Depends(
        get_db
    ),
):
    day = db.get(
        OperatingDay,
        day_id,
    )


    if not day:
        raise HTTPException(
            status_code=404,
            detail=(
                "Operating day "
                "not found."
            ),
        )


    return build_summary(
        db,
        day,
    )


@router.post(
    "/current/close",
    response_model=OperatingDaySummary,
)
def close_current_day(
    closed_by_id: int | None = None,
    db: Session = Depends(
        get_db
    ),
):
    day = get_current_day(
        db
    )


    if not day:
        raise HTTPException(
            status_code=404,
            detail=(
                "No operating day "
                "exists for today."
            ),
        )


    if day.is_closed:
        return build_summary(
            db,
            day,
        )


    unresolved = db.scalars(
        select(
            Order
        ).where(
            Order.operating_day_id
            == day.id,

            Order.status.notin_(
                [
                    OrderStatus.COMPLETED,
                    OrderStatus.CANCELLED,
                    OrderStatus.FAILED,
                ]
            ),
        )
    ).all()


    if unresolved:
        numbers = [
            order.daily_number
            for order
            in unresolved
        ]

        raise HTTPException(
            status_code=409,
            detail=(
                "Cannot close the day. "
                f"{len(unresolved)} order(s) "
                "are still unresolved: "
                f"{numbers}"
            ),
        )


    day.is_closed = True

    day.closed_at = (
        ghana_now()
    )

    day.closed_by_id = (
        closed_by_id
    )


    db.add(
        AuditEvent(
            actor_id=(
                closed_by_id
            ),

            action=(
                "operating_day_closed"
            ),

            entity_type=(
                "operating_day"
            ),

            entity_id=day.id,

            after_json=json.dumps(
                {
                    "business_date":
                        str(
                            day.business_date
                        ),

                    "is_closed":
                        True,
                }
            ),
        )
    )


    db.commit()


    db.refresh(
        day
    )


    return build_summary(
        db,
        day,
    )
