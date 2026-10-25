from datetime import (
    date,
    datetime,
)

from decimal import Decimal

from app.schemas.common import ORMModel


class OperatingDayRead(ORMModel):
    id: int

    business_date: date

    opened_at: datetime

    closed_at: datetime | None

    is_closed: bool

    closed_by_id: int | None

    notes: str | None


class OperatingDaySummary(
    OperatingDayRead
):
    total_orders: int

    draft_orders: int

    active_orders: int

    completed_orders: int

    cancelled_orders: int

    failed_orders: int

    goods_total: Decimal

    delivery_fee_total: Decimal

    service_fee_total: Decimal

    final_total: Decimal
