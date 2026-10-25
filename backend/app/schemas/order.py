from datetime import datetime
from decimal import Decimal

from pydantic import (
    BaseModel,
    Field,
)

from app.models import OrderStatus
from app.schemas.common import ORMModel


class OrderItemCreate(BaseModel):
    name: str

    brand: str | None = None
    size: str | None = None

    requested_quantity: float = Field(
        gt=0
    )

    unit: str = "unit"


class OrderCreate(BaseModel):
    business_id: int

    operator_id: int | None = None

    notes: str | None = None

    items: list[
        OrderItemCreate
    ] = Field(
        min_length=1
    )


class OrderDraftUpdate(BaseModel):
    notes: str | None = None

    items: list[
        OrderItemCreate
    ] = Field(
        min_length=1
    )


class OrderItemRead(ORMModel):
    id: int

    name: str

    brand: str | None
    size: str | None

    requested_quantity: float

    unit: str

    confirmed_quantity: float | None

    confirmed_price: Decimal | None

    supplier_id: int | None

    availability_status: str

    logistics_category_id: int | None = None
    logistics_type_id: int | None = None
    logistics_size_class: str | None = None

    load_units_each: float | None = None
    total_load_units: float | None = None

    logistics_package_type: str | None = None

    weight_kg_each: float | None = None
    volume_l_each: float | None = None

    handling_score_each: float | None = None
    fragility_score_each: float | None = None

    total_weight_kg: float | None = None
    total_volume_l: float | None = None

    total_handling_score: float | None = None
    total_fragility_score: float | None = None

    physical_profile_version: str | None = None



    logistics_variant_key: str | None = None
    logistics_size_detail: str | None = None

    physical_material_class: str | None = None
    physical_estimation_source: str | None = None
    physical_confidence: float | None = None


class OrderRead(ORMModel):
    id: int

    order_number: str

    operating_day_id: int | None

    daily_number: int | None

    business_id: int

    operator_id: int | None

    status: OrderStatus

    notes: str | None

    goods_total: Decimal

    delivery_fee: Decimal

    service_fee: Decimal

    final_total: Decimal

    tax_total: Decimal = Decimal("0")

    route_distance_km: float | None = None
    route_duration_minutes: float | None = None

    supplier_stop_count: int | None = None
    total_load_units: float | None = None

    total_weight_kg: float | None = None
    total_volume_l: float | None = None
    total_handling_score: float | None = None
    total_fragility_score: float | None = None

    driver_floor: Decimal | None = None
    driver_target: Decimal | None = None
    driver_ceiling: Decimal | None = None

    estimated_driver_market_cost: Decimal | None = None
    estimated_customer_willingness: Decimal | None = None
    driver_acceptance_probability: float | None = None
    customer_acceptance_probability: float | None = None
    delivery_margin: Decimal | None = None
    optimizer_score: float | None = None
    pricing_version: str | None = None

    created_at: datetime

    quote_generated_at: datetime | None = None

    customer_approved_at: datetime | None = None

    finalized_at: datetime | None = None

    completed_at: datetime | None = None

    items: list[OrderItemRead]
