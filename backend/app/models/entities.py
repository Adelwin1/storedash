from __future__ import annotations

from datetime import date, datetime
from enum import Enum

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Enum as SAEnum,
    Float,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)

from sqlalchemy.orm import (
    Mapped,
    mapped_column,
    relationship,
)

from app.core.db import Base


class Role(str, Enum):
    ADMIN = "admin"
    MANAGER = "manager"
    OPERATIONS = "operations"

    SUPPLIER_FIELD = "supplier_field"
    CUSTOMER_FIELD = "customer_field"

    ACQUISITION = "acquisition"


class OrderStatus(str, Enum):
    DRAFT = "draft"

    ACTIVE = "active"

    SOURCING = "sourcing"

    PARTIALLY_FULFILLED = (
        "partially_fulfilled"
    )

    QUOTE_READY = "quote_ready"

    AWAITING_BUYER_APPROVAL = (
        "awaiting_buyer_approval"
    )

    AWAITING_PAYMENT = "awaiting_payment"

    PAYMENT_CONFIRMED = (
        "payment_confirmed"
    )

    PREPARING = "preparing"

    READY_FOR_DISPATCH = (
        "ready_for_dispatch"
    )

    DRIVER_ASSIGNED = (
        "driver_assigned"
    )

    PICKUP_IN_PROGRESS = (
        "pickup_in_progress"
    )

    OUT_FOR_DELIVERY = (
        "out_for_delivery"
    )

    DELIVERED = "delivered"

    COMPLETED = "completed"
    CANCELLED = "cancelled"
    FAILED = "failed"


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )


class User(
    Base,
    TimestampMixin,
):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
    )

    name: Mapped[str] = mapped_column(
        String(120)
    )

    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        index=True,
    )

    phone: Mapped[str | None] = mapped_column(
        String(30),
        nullable=True,
    )

    role: Mapped[Role] = mapped_column(
        SAEnum(Role),
        default=Role.OPERATIONS,
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
    )


class OperatingDay(
    Base,
    TimestampMixin,
):
    __tablename__ = "operating_days"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
    )

    business_date: Mapped[date] = mapped_column(
        Date,
        unique=True,
        index=True,
    )

    opened_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
    )

    closed_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True,
    )

    is_closed: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        index=True,
    )

    closed_by_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id"),
        nullable=True,
    )

    notes: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    orders: Mapped[list["Order"]] = relationship(
        back_populates="operating_day"
    )


class Business(
    Base,
    TimestampMixin,
):
    __tablename__ = "businesses"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
    )

    owner_name: Mapped[str] = mapped_column(
        String(120)
    )

    business_name: Mapped[str] = mapped_column(
        String(160),
        index=True,
    )

    phone: Mapped[str] = mapped_column(
        String(30),
        unique=True,
        index=True,
    )

    alternate_phone: Mapped[str | None] = mapped_column(
        String(30),
        nullable=True,
    )

    business_type: Mapped[str | None] = mapped_column(
        String(80),
        nullable=True,
    )

    address: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    landmark: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    latitude: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    longitude: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    delivery_instructions: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    created_by_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id"),
        nullable=True,
    )

    suppliers: Mapped[
        list["BusinessSupplier"]
    ] = relationship(
        back_populates="business",
        cascade="all, delete-orphan",
    )

    orders: Mapped[list["Order"]] = relationship(
        back_populates="business"
    )

    @property
    def customer_number(self) -> str:
        return f"{max(self.id - 1, 0):03d}"


class Supplier(
    Base,
    TimestampMixin,
):
    __tablename__ = "suppliers"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
    )

    name: Mapped[str] = mapped_column(
        String(160),
        index=True,
    )

    category: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    phone: Mapped[str] = mapped_column(
        String(30),
        unique=True,
        index=True,
    )

    contact_person: Mapped[str | None] = mapped_column(
        String(120),
        nullable=True,
    )

    location: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    landmark: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    latitude: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    longitude: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    pickup_notes: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    willing_to_fulfill: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
    )

    created_by_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id"),
        nullable=True,
    )

    @property
    def supplier_number(self) -> str:
        return f"{max(self.id - 1, 0):03d}"


class BusinessSupplier(
    Base,
    TimestampMixin,
):
    __tablename__ = "business_suppliers"

    __table_args__ = (
        UniqueConstraint(
            "business_id",
            "supplier_id",
            name="uq_business_supplier",
        ),
    )

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
    )

    business_id: Mapped[int] = mapped_column(
        ForeignKey(
            "businesses.id",
            ondelete="CASCADE",
        )
    )

    supplier_id: Mapped[int] = mapped_column(
        ForeignKey(
            "suppliers.id",
            ondelete="CASCADE",
        )
    )

    is_usual: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
    )

    notes: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    business: Mapped[Business] = relationship(
        back_populates="suppliers"
    )

    supplier: Mapped[Supplier] = relationship()


class Driver(
    Base,
    TimestampMixin,
):
    __tablename__ = "drivers"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
    )

    name: Mapped[str] = mapped_column(
        String(120)
    )

    phone: Mapped[str] = mapped_column(
        String(30),
        unique=True,
        index=True,
    )

    vehicle_type: Mapped[str] = mapped_column(
        String(80),
        default="tricycle",
    )

    current_area: Mapped[str | None] = mapped_column(
        String(120),
        nullable=True,
    )

    latitude: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    longitude: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    is_available: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
    )

    completion_rate: Mapped[float] = mapped_column(
        Float,
        default=1.0,
    )


    vehicle_registration: Mapped[str | None] = mapped_column(
        String(40),
        nullable=True,
    )

    payment_phone: Mapped[str | None] = mapped_column(
        String(30),
        nullable=True,
    )

    payment_name: Mapped[str | None] = mapped_column(
        String(120),
        nullable=True,
    )

    notes: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
    )


class Order(
    Base,
    TimestampMixin,
):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
    )

    operating_day_id: Mapped[
        int | None
    ] = mapped_column(
        ForeignKey("operating_days.id"),
        nullable=True,
        index=True,
    )

    daily_number: Mapped[
        int | None
    ] = mapped_column(
        Integer,
        nullable=True,
        index=True,
    )

    business_id: Mapped[int] = mapped_column(
        ForeignKey("businesses.id"),
        index=True,
    )

    operator_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id"),
        nullable=True,
    )

    status: Mapped[OrderStatus] = mapped_column(
        SAEnum(OrderStatus),
        default=OrderStatus.DRAFT,
        index=True,
    )

    notes: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    goods_total: Mapped[float] = mapped_column(
        Numeric(12, 2),
        default=0,
    )

    delivery_fee: Mapped[float] = mapped_column(
        Numeric(12, 2),
        default=0,
    )

    service_fee: Mapped[float] = mapped_column(
        Numeric(12, 2),
        default=0,
    )

    final_total: Mapped[float] = mapped_column(
        Numeric(12, 2),
        default=0,
    )

    payment_amount: Mapped[float | None] = mapped_column(
        Numeric(12, 2),
        nullable=True,
    )

    payment_method: Mapped[str | None] = mapped_column(
        String(40),
        nullable=True,
    )

    payment_reference: Mapped[str | None] = mapped_column(
        String(120),
        nullable=True,
    )

    payment_notes: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    payment_confirmed_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True,
    )

    preparation_started_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True,
    )

    ready_for_dispatch_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True,
    )

    tax_total: Mapped[float] = mapped_column(
        Numeric(12, 2),
        default=0,
    )

    route_distance_km: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    route_duration_minutes: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    supplier_stop_count: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    total_load_units: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    total_weight_kg: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    total_volume_l: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    total_handling_score: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    total_fragility_score: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    driver_floor: Mapped[float | None] = mapped_column(
        Numeric(12, 2),
        nullable=True,
    )

    driver_target: Mapped[float | None] = mapped_column(
        Numeric(12, 2),
        nullable=True,
    )

    driver_ceiling: Mapped[float | None] = mapped_column(
        Numeric(12, 2),
        nullable=True,
    )


    assigned_driver_id: Mapped[int | None] = mapped_column(
        ForeignKey("drivers.id"),
        nullable=True,
        index=True,
    )

    driver_payout: Mapped[float | None] = mapped_column(
        Numeric(12, 2),
        nullable=True,
    )

    driver_assigned_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True,
    )

    estimated_driver_market_cost: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    estimated_customer_willingness: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    driver_acceptance_probability: Mapped[float | None] = mapped_column(Float, nullable=True)
    customer_acceptance_probability: Mapped[float | None] = mapped_column(Float, nullable=True)
    delivery_margin: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    optimizer_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    pricing_version: Mapped[str | None] = mapped_column(
        String(40),
        nullable=True,
    )

    quote_generated_at: Mapped[
        datetime | None
    ] = mapped_column(
        DateTime,
        nullable=True,
    )

    customer_approved_at: Mapped[
        datetime | None
    ] = mapped_column(
        DateTime,
        nullable=True,
    )

    finalized_at: Mapped[
        datetime | None
    ] = mapped_column(
        DateTime,
        nullable=True,
    )

    completed_at: Mapped[
        datetime | None
    ] = mapped_column(
        DateTime,
        nullable=True,
    )

    business: Mapped[Business] = relationship(
        back_populates="orders"
    )

    operating_day: Mapped[
        OperatingDay | None
    ] = relationship(
        back_populates="orders"
    )

    items: Mapped[
        list["OrderItem"]
    ] = relationship(
        back_populates="order",
        cascade="all, delete-orphan",
    )

    @property
    def order_number(self) -> str:
        return f"SD-{self.id:06d}"


class OrderItem(
    Base,
    TimestampMixin,
):
    __tablename__ = "order_items"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
    )

    order_id: Mapped[int] = mapped_column(
        ForeignKey(
            "orders.id",
            ondelete="CASCADE",
        ),
        index=True,
    )

    name: Mapped[str] = mapped_column(
        String(160)
    )

    brand: Mapped[str | None] = mapped_column(
        String(120),
        nullable=True,
    )

    size: Mapped[str | None] = mapped_column(
        String(80),
        nullable=True,
    )

    requested_quantity: Mapped[float] = mapped_column(
        Float
    )

    unit: Mapped[str] = mapped_column(
        String(40),
        default="unit",
    )

    confirmed_quantity: Mapped[
        float | None
    ] = mapped_column(
        Float,
        nullable=True,
    )

    confirmed_price: Mapped[
        float | None
    ] = mapped_column(
        Numeric(12, 2),
        nullable=True,
    )

    supplier_id: Mapped[
        int | None
    ] = mapped_column(
        ForeignKey("suppliers.id"),
        nullable=True,
    )

    availability_status: Mapped[str] = mapped_column(
        String(40),
        default="unverified",
    )

    logistics_category_id: Mapped[int | None] = mapped_column(
        ForeignKey("logistics_categories.id"),
        nullable=True,
        index=True,
    )

    logistics_type_id: Mapped[int | None] = mapped_column(
        ForeignKey("logistics_types.id"),
        nullable=True,
        index=True,
    )

    logistics_size_class: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
    )

    load_units_each: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    total_load_units: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    logistics_package_type: Mapped[str | None] = mapped_column(
        String(80),
        nullable=True,
    )

    weight_kg_each: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    volume_l_each: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    handling_score_each: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    fragility_score_each: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    total_weight_kg: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    total_volume_l: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    total_handling_score: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    total_fragility_score: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    physical_profile_version: Mapped[str | None] = mapped_column(
        String(60),
        nullable=True,
    )

    substitution_notes: Mapped[
        str | None
    ] = mapped_column(
        Text,
        nullable=True,
    )

    order: Mapped[Order] = relationship(
        back_populates="items"
    )

    supplier: Mapped[
        Supplier | None
    ] = relationship()



    logistics_variant_key: Mapped[str | None] = mapped_column(
        String(120),
        nullable=True,
    )

    logistics_size_detail: Mapped[str | None] = mapped_column(
        String(120),
        nullable=True,
    )

    physical_material_class: Mapped[str | None] = mapped_column(
        String(80),
        nullable=True,
    )

    physical_estimation_source: Mapped[str | None] = mapped_column(
        String(80),
        nullable=True,
    )

    physical_confidence: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )


class SupplierCall(
    Base,
    TimestampMixin,
):
    __tablename__ = "supplier_calls"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
    )

    order_id: Mapped[int] = mapped_column(
        ForeignKey("orders.id"),
        index=True,
    )

    supplier_id: Mapped[int] = mapped_column(
        ForeignKey("suppliers.id"),
        index=True,
    )

    operator_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id"),
        nullable=True,
    )

    answered: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
    )

    preparation_minutes: Mapped[
        int | None
    ] = mapped_column(
        Integer,
        nullable=True,
    )

    notes: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )


class DriverOffer(
    Base,
    TimestampMixin,
):
    __tablename__ = "driver_offers"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
    )

    order_id: Mapped[int] = mapped_column(
        ForeignKey("orders.id"),
        index=True,
    )

    driver_id: Mapped[int] = mapped_column(
        ForeignKey("drivers.id"),
        index=True,
    )

    operator_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id"),
        nullable=True,
    )

    route_value: Mapped[float] = mapped_column(
        Numeric(12, 2)
    )

    opening_offer: Mapped[float] = mapped_column(
        Numeric(12, 2)
    )

    counter_offer: Mapped[
        float | None
    ] = mapped_column(
        Numeric(12, 2),
        nullable=True,
    )

    final_payout: Mapped[
        float | None
    ] = mapped_column(
        Numeric(12, 2),
        nullable=True,
    )

    hard_ceiling: Mapped[float] = mapped_column(
        Numeric(12, 2)
    )


    driver_quote: Mapped[float | None] = mapped_column(
        Numeric(12, 2),
        nullable=True,
    )

    auto_accept_limit: Mapped[float | None] = mapped_column(
        Numeric(12, 2),
        nullable=True,
    )

    normal_negotiation_max: Mapped[float | None] = mapped_column(
        Numeric(12, 2),
        nullable=True,
    )

    current_authorized_offer: Mapped[float | None] = mapped_column(
        Numeric(12, 2),
        nullable=True,
    )

    counter_round: Mapped[int] = mapped_column(
        Integer,
        default=0,
    )

    company_delivery_share: Mapped[float | None] = mapped_column(
        Numeric(12, 2),
        nullable=True,
    )

    released_driver_reserve: Mapped[float | None] = mapped_column(
        Numeric(12, 2),
        nullable=True,
    )

    locked_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True,
    )

    outcome: Mapped[str] = mapped_column(
        String(40),
        default="pending",
    )


class DriverNegotiationEvent(
    Base,
):
    __tablename__ = "driver_negotiation_events"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
    )

    driver_offer_id: Mapped[int] = mapped_column(
        ForeignKey(
            "driver_offers.id",
            ondelete="CASCADE",
        ),
        index=True,
    )

    order_id: Mapped[int] = mapped_column(
        ForeignKey("orders.id"),
        index=True,
    )

    driver_id: Mapped[int] = mapped_column(
        ForeignKey("drivers.id"),
        index=True,
    )

    operator_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id"),
        nullable=True,
    )

    event_type: Mapped[str] = mapped_column(
        String(60),
        index=True,
    )

    amount: Mapped[float | None] = mapped_column(
        Numeric(12, 2),
        nullable=True,
    )

    details: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        index=True,
    )


class DeliveryEvent(
    Base,
    TimestampMixin,
):
    __tablename__ = "delivery_events"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
    )

    order_id: Mapped[int] = mapped_column(
        ForeignKey("orders.id"),
        index=True,
    )

    event_type: Mapped[str] = mapped_column(
        String(80)
    )

    details: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    created_by_id: Mapped[
        int | None
    ] = mapped_column(
        ForeignKey("users.id"),
        nullable=True,
    )


class AuditEvent(Base):
    __tablename__ = "audit_events"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
    )

    actor_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id"),
        nullable=True,
    )

    action: Mapped[str] = mapped_column(
        String(120),
        index=True,
    )

    entity_type: Mapped[str] = mapped_column(
        String(80)
    )

    entity_id: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    before_json: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    after_json: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        index=True,
    )


class LogisticsCategory(
    Base,
    TimestampMixin,
):
    __tablename__ = "logistics_categories"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
    )

    code: Mapped[str] = mapped_column(
        String(80),
        unique=True,
        index=True,
    )

    name: Mapped[str] = mapped_column(
        String(120),
        unique=True,
        index=True,
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    fallback_small_units: Mapped[float] = mapped_column(
        Float,
        default=1.0,
    )

    fallback_medium_units: Mapped[float] = mapped_column(
        Float,
        default=4.0,
    )

    fallback_large_units: Mapped[float] = mapped_column(
        Float,
        default=8.0,
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
    )


class LogisticsType(
    Base,
    TimestampMixin,
):
    __tablename__ = "logistics_types"

    __table_args__ = (
        UniqueConstraint(
            "category_id",
            "name",
            name="uq_logistics_category_type",
        ),
    )

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
    )

    category_id: Mapped[int] = mapped_column(
        ForeignKey(
            "logistics_categories.id",
            ondelete="CASCADE",
        ),
        index=True,
    )

    name: Mapped[str] = mapped_column(
        String(160),
        index=True,
    )

    package_type: Mapped[str] = mapped_column(
        String(80),
        index=True,
    )

    load_units: Mapped[float] = mapped_column(
        Float,
    )

    weight_kg_each: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    volume_l_each: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    handling_score_each: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    fragility_score_each: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    aliases: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
    )


class ProductKnowledge(
    Base,
    TimestampMixin,
):
    __tablename__ = "product_knowledge"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
    )

    normalized_name: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        index=True,
    )

    display_name: Mapped[str] = mapped_column(
        String(255),
    )

    category_id: Mapped[int] = mapped_column(
        ForeignKey(
            "logistics_categories.id",
            ondelete="CASCADE",
        ),
        index=True,
    )

    logistics_type_id: Mapped[int | None] = mapped_column(
        ForeignKey(
            "logistics_types.id",
            ondelete="SET NULL",
        ),
        nullable=True,
        index=True,
    )

    size_class: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
    )

    source: Mapped[str] = mapped_column(
        String(40),
        default="operator",
    )

    times_seen: Mapped[int] = mapped_column(
        Integer,
        default=1,
    )

    confidence: Mapped[float] = mapped_column(
        Float,
        default=0.5,
    )

    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
    )

    notes: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )


# ============================================================
# STOREDASH DELIVERY MARKET INTELLIGENCE
# ============================================================


class PricingModelVersion(
    Base,
    TimestampMixin,
):
    __tablename__ = "pricing_model_versions"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
    )

    version_name: Mapped[str] = mapped_column(
        String(160),
        unique=True,
        index=True,
    )

    status: Mapped[str] = mapped_column(
        String(40),
        default="candidate",
        index=True,
    )

    source: Mapped[str] = mapped_column(
        String(160),
        default="storedash",
    )

    coefficients_json: Mapped[str] = mapped_column(
        Text,
        default="{}",
    )

    metrics_json: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    training_window_start: Mapped[
        datetime | None
    ] = mapped_column(
        DateTime,
        nullable=True,
    )

    training_window_end: Mapped[
        datetime | None
    ] = mapped_column(
        DateTime,
        nullable=True,
    )

    training_sample_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
    )

    validation_sample_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
    )

    activated_at: Mapped[
        datetime | None
    ] = mapped_column(
        DateTime,
        nullable=True,
    )


class DeliveryPricingSnapshot(
    Base,
    TimestampMixin,
):
    __tablename__ = "delivery_pricing_snapshots"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
    )

    order_id: Mapped[int] = mapped_column(
        ForeignKey(
            "orders.id",
            ondelete="CASCADE",
        ),
        index=True,
    )

    model_version_id: Mapped[
        int | None
    ] = mapped_column(
        ForeignKey(
            "pricing_model_versions.id"
        ),
        nullable=True,
        index=True,
    )

    model_version_name: Mapped[str] = mapped_column(
        String(160),
        index=True,
    )

    status: Mapped[str] = mapped_column(
        String(80),
        default="awaiting_carrier_bids",
        index=True,
    )

    provider: Mapped[str] = mapped_column(
        String(80),
        default="cargomov",
        index=True,
    )

    goods_total: Mapped[float] = mapped_column(
        Numeric(14, 2),
        default=0,
    )

    service_fee: Mapped[float] = mapped_column(
        Numeric(14, 2),
        default=0,
    )

    route_distance_km: Mapped[
        float | None
    ] = mapped_column(
        Float,
        nullable=True,
    )

    route_duration_minutes: Mapped[
        float | None
    ] = mapped_column(
        Float,
        nullable=True,
    )

    supplier_stop_count: Mapped[int] = mapped_column(
        Integer,
        default=1,
    )

    item_count: Mapped[int] = mapped_column(
        Integer,
        default=1,
    )

    total_load_units: Mapped[float] = mapped_column(
        Float,
        default=0,
    )

    total_weight_kg: Mapped[float] = mapped_column(
        Float,
        default=0,
    )

    total_volume_l: Mapped[float] = mapped_column(
        Float,
        default=0,
    )

    total_handling_score: Mapped[float] = mapped_column(
        Float,
        default=0,
    )

    total_fragility_score: Mapped[float] = mapped_column(
        Float,
        default=0,
    )

    chargeable_weight_kg: Mapped[float] = mapped_column(
        Float,
        default=0,
    )

    capacity_class: Mapped[str] = mapped_column(
        String(80),
        index=True,
    )

    distance_band: Mapped[str] = mapped_column(
        String(80),
        index=True,
    )

    day_of_week: Mapped[int] = mapped_column(
        Integer,
        default=0,
    )

    hour_of_day: Mapped[int] = mapped_column(
        Integer,
        default=0,
    )

    feature_json: Mapped[str] = mapped_column(
        Text,
        default="{}",
    )

    model_predicted_carrier_cost: Mapped[
        float
    ] = mapped_column(
        Numeric(14, 2),
        default=0,
    )

    model_customer_price: Mapped[float] = mapped_column(
        Numeric(14, 2),
        default=0,
    )

    live_market_min: Mapped[
        float | None
    ] = mapped_column(
        Numeric(14, 2),
        nullable=True,
    )

    live_market_median: Mapped[
        float | None
    ] = mapped_column(
        Numeric(14, 2),
        nullable=True,
    )

    live_market_recommended: Mapped[
        float | None
    ] = mapped_column(
        Numeric(14, 2),
        nullable=True,
    )

    selected_carrier_bid_id: Mapped[
        int | None
    ] = mapped_column(
        Integer,
        nullable=True,
    )

    selected_carrier_cost: Mapped[
        float | None
    ] = mapped_column(
        Numeric(14, 2),
        nullable=True,
    )

    customer_delivery_fee: Mapped[
        float | None
    ] = mapped_column(
        Numeric(14, 2),
        nullable=True,
    )

    storedash_delivery_profit: Mapped[
        float | None
    ] = mapped_column(
        Numeric(14, 2),
        nullable=True,
    )

    storedash_margin_rate: Mapped[
        float | None
    ] = mapped_column(
        Float,
        nullable=True,
    )

    pricing_mode: Mapped[
        str | None
    ] = mapped_column(
        String(100),
        nullable=True,
        index=True,
    )

    customer_decision: Mapped[str] = mapped_column(
        String(40),
        default="pending",
        index=True,
    )

    customer_decision_at: Mapped[
        datetime | None
    ] = mapped_column(
        DateTime,
        nullable=True,
    )

    actual_carrier_cost: Mapped[
        float | None
    ] = mapped_column(
        Numeric(14, 2),
        nullable=True,
    )

    actual_delivery_minutes: Mapped[
        float | None
    ] = mapped_column(
        Float,
        nullable=True,
    )

    outcome_notes: Mapped[
        str | None
    ] = mapped_column(
        Text,
        nullable=True,
    )

    finalized_at: Mapped[
        datetime | None
    ] = mapped_column(
        DateTime,
        nullable=True,
    )


class CarrierBid(
    Base,
    TimestampMixin,
):
    __tablename__ = "carrier_bids"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
    )

    order_id: Mapped[int] = mapped_column(
        ForeignKey(
            "orders.id",
            ondelete="CASCADE",
        ),
        index=True,
    )

    pricing_snapshot_id: Mapped[int] = mapped_column(
        ForeignKey(
            "delivery_pricing_snapshots.id",
            ondelete="CASCADE",
        ),
        index=True,
    )

    provider: Mapped[str] = mapped_column(
        String(80),
        default="cargomov",
        index=True,
    )

    external_bid_id: Mapped[
        str | None
    ] = mapped_column(
        String(160),
        nullable=True,
        index=True,
    )

    amount: Mapped[float] = mapped_column(
        Numeric(14, 2),
    )

    pickup_eta_minutes: Mapped[
        float | None
    ] = mapped_column(
        Float,
        nullable=True,
    )

    provider_rating: Mapped[
        float | None
    ] = mapped_column(
        Float,
        nullable=True,
    )

    vehicle_type: Mapped[
        str | None
    ] = mapped_column(
        String(120),
        nullable=True,
    )

    vehicle_capacity_kg: Mapped[
        float | None
    ] = mapped_column(
        Float,
        nullable=True,
    )

    qualified: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        index=True,
    )

    capacity_ok: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        index=True,
    )

    rejection_reason: Mapped[
        str | None
    ] = mapped_column(
        Text,
        nullable=True,
    )

    selected: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        index=True,
    )

    raw_payload_json: Mapped[
        str | None
    ] = mapped_column(
        Text,
        nullable=True,
    )


class PricingCalibrationRun(
    Base,
    TimestampMixin,
):
    __tablename__ = "pricing_calibration_runs"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
    )

    window_start: Mapped[datetime] = mapped_column(
        DateTime,
        index=True,
    )

    window_end: Mapped[datetime] = mapped_column(
        DateTime,
        index=True,
    )

    active_model_version_id: Mapped[
        int | None
    ] = mapped_column(
        ForeignKey(
            "pricing_model_versions.id"
        ),
        nullable=True,
    )

    candidate_model_version_id: Mapped[
        int | None
    ] = mapped_column(
        ForeignKey(
            "pricing_model_versions.id"
        ),
        nullable=True,
    )

    sample_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
    )

    validation_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
    )

    active_mae: Mapped[
        float | None
    ] = mapped_column(
        Float,
        nullable=True,
    )

    candidate_mae: Mapped[
        float | None
    ] = mapped_column(
        Float,
        nullable=True,
    )

    active_mape: Mapped[
        float | None
    ] = mapped_column(
        Float,
        nullable=True,
    )

    candidate_mape: Mapped[
        float | None
    ] = mapped_column(
        Float,
        nullable=True,
    )

    candidate_bias: Mapped[
        float | None
    ] = mapped_column(
        Float,
        nullable=True,
    )

    underpricing_rate: Mapped[
        float | None
    ] = mapped_column(
        Float,
        nullable=True,
    )

    overpricing_rate: Mapped[
        float | None
    ] = mapped_column(
        Float,
        nullable=True,
    )

    customer_acceptance_rate: Mapped[
        float | None
    ] = mapped_column(
        Float,
        nullable=True,
    )

    promoted: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
    )

    notes: Mapped[
        str | None
    ] = mapped_column(
        Text,
        nullable=True,
    )

    completed_at: Mapped[
        datetime | None
    ] = mapped_column(
        DateTime,
        nullable=True,
    )


# ============================================================
# STOREDASH MULTI-ORDER ROUTE SYSTEM
# ============================================================


class VehicleProfile(
    Base,
    TimestampMixin,
):
    __tablename__ = "vehicle_profiles"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
    )

    driver_id: Mapped[int] = mapped_column(
        ForeignKey(
            "drivers.id",
            ondelete="CASCADE",
        ),
        index=True,
    )

    vehicle_type: Mapped[str] = mapped_column(
        String(80),
        default="cargo_tricycle",
        index=True,
    )

    registration: Mapped[
        str | None
    ] = mapped_column(
        String(80),
        nullable=True,
        index=True,
    )

    is_primary: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        index=True,
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        index=True,
    )

    verified_payload_kg: Mapped[
        float | None
    ] = mapped_column(
        Float,
        nullable=True,
    )

    cargo_length_m: Mapped[
        float | None
    ] = mapped_column(
        Float,
        nullable=True,
    )

    cargo_width_m: Mapped[
        float | None
    ] = mapped_column(
        Float,
        nullable=True,
    )

    cargo_height_m: Mapped[
        float | None
    ] = mapped_column(
        Float,
        nullable=True,
    )

    verified_volume_l: Mapped[
        float | None
    ] = mapped_column(
        Float,
        nullable=True,
    )

    safe_capacity_ratio: Mapped[float] = mapped_column(
        Float,
        default=0.80,
    )

    fuel_type: Mapped[
        str | None
    ] = mapped_column(
        String(40),
        nullable=True,
    )

    observed_km_per_liter: Mapped[
        float | None
    ] = mapped_column(
        Float,
        nullable=True,
    )

    current_latitude: Mapped[
        float | None
    ] = mapped_column(
        Float,
        nullable=True,
    )

    current_longitude: Mapped[
        float | None
    ] = mapped_column(
        Float,
        nullable=True,
    )

    current_area: Mapped[
        str | None
    ] = mapped_column(
        String(160),
        nullable=True,
    )

    capacity_verified_at: Mapped[
        datetime | None
    ] = mapped_column(
        DateTime,
        nullable=True,
    )

    notes: Mapped[
        str | None
    ] = mapped_column(
        Text,
        nullable=True,
    )


class DeliveryRoute(
    Base,
    TimestampMixin,
):
    __tablename__ = "delivery_routes"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
    )

    status: Mapped[str] = mapped_column(
        String(60),
        default="draft",
        index=True,
    )

    fulfillment_mode: Mapped[str] = mapped_column(
        String(60),
        default="storedash_driver",
        index=True,
    )

    driver_id: Mapped[
        int | None
    ] = mapped_column(
        ForeignKey(
            "drivers.id"
        ),
        nullable=True,
        index=True,
    )

    vehicle_profile_id: Mapped[
        int | None
    ] = mapped_column(
        ForeignKey(
            "vehicle_profiles.id"
        ),
        nullable=True,
        index=True,
    )

    route_engine_version: Mapped[
        str | None
    ] = mapped_column(
        String(160),
        nullable=True,
        index=True,
    )

    order_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
    )

    pickup_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
    )

    delivery_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
    )

    planned_deadhead_km: Mapped[float] = mapped_column(
        Float,
        default=0,
    )

    planned_service_km: Mapped[float] = mapped_column(
        Float,
        default=0,
    )

    planned_reposition_km: Mapped[float] = mapped_column(
        Float,
        default=0,
    )

    planned_distance_km: Mapped[float] = mapped_column(
        Float,
        default=0,
    )

    planned_driving_minutes: Mapped[float] = mapped_column(
        Float,
        default=0,
    )

    planned_active_minutes: Mapped[float] = mapped_column(
        Float,
        default=0,
    )

    actual_distance_km: Mapped[
        float | None
    ] = mapped_column(
        Float,
        nullable=True,
    )

    actual_active_minutes: Mapped[
        float | None
    ] = mapped_column(
        Float,
        nullable=True,
    )

    peak_weight_kg: Mapped[float] = mapped_column(
        Float,
        default=0,
    )

    peak_volume_l: Mapped[float] = mapped_column(
        Float,
        default=0,
    )

    customer_delivery_revenue: Mapped[float] = mapped_column(
        Numeric(14, 2),
        default=0,
    )

    predicted_driver_payout: Mapped[
        float | None
    ] = mapped_column(
        Numeric(14, 2),
        nullable=True,
    )

    accepted_driver_payout: Mapped[
        float | None
    ] = mapped_column(
        Numeric(14, 2),
        nullable=True,
    )

    actual_driver_payout: Mapped[
        float | None
    ] = mapped_column(
        Numeric(14, 2),
        nullable=True,
    )

    predicted_contribution: Mapped[
        float | None
    ] = mapped_column(
        Numeric(14, 2),
        nullable=True,
    )

    actual_contribution: Mapped[
        float | None
    ] = mapped_column(
        Numeric(14, 2),
        nullable=True,
    )

    predicted_margin_rate: Mapped[
        float | None
    ] = mapped_column(
        Float,
        nullable=True,
    )

    actual_margin_rate: Mapped[
        float | None
    ] = mapped_column(
        Float,
        nullable=True,
    )

    planned_start_at: Mapped[
        datetime | None
    ] = mapped_column(
        DateTime,
        nullable=True,
    )

    accepted_at: Mapped[
        datetime | None
    ] = mapped_column(
        DateTime,
        nullable=True,
    )

    started_at: Mapped[
        datetime | None
    ] = mapped_column(
        DateTime,
        nullable=True,
    )

    completed_at: Mapped[
        datetime | None
    ] = mapped_column(
        DateTime,
        nullable=True,
    )

    notes: Mapped[
        str | None
    ] = mapped_column(
        Text,
        nullable=True,
    )


class RouteOrder(
    Base,
    TimestampMixin,
):
    __tablename__ = "route_orders"

    __table_args__ = (
        UniqueConstraint(
            "route_id",
            "order_id",
            name="uq_route_order",
        ),
    )

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
    )

    route_id: Mapped[int] = mapped_column(
        ForeignKey(
            "delivery_routes.id",
            ondelete="CASCADE",
        ),
        index=True,
    )

    order_id: Mapped[int] = mapped_column(
        ForeignKey(
            "orders.id",
            ondelete="CASCADE",
        ),
        index=True,
    )

    customer_delivery_fee: Mapped[float] = mapped_column(
        Numeric(14, 2),
        default=0,
    )

    order_weight_kg: Mapped[float] = mapped_column(
        Float,
        default=0,
    )

    order_volume_l: Mapped[float] = mapped_column(
        Float,
        default=0,
    )

    allocated_driver_cost: Mapped[
        float | None
    ] = mapped_column(
        Numeric(14, 2),
        nullable=True,
    )

    allocated_contribution: Mapped[
        float | None
    ] = mapped_column(
        Numeric(14, 2),
        nullable=True,
    )

    delivery_sequence: Mapped[
        int | None
    ] = mapped_column(
        Integer,
        nullable=True,
    )

    status: Mapped[str] = mapped_column(
        String(60),
        default="planned",
        index=True,
    )


class RouteStop(
    Base,
    TimestampMixin,
):
    __tablename__ = "route_stops"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
    )

    route_id: Mapped[int] = mapped_column(
        ForeignKey(
            "delivery_routes.id",
            ondelete="CASCADE",
        ),
        index=True,
    )

    sequence: Mapped[int] = mapped_column(
        Integer,
        index=True,
    )

    stop_type: Mapped[str] = mapped_column(
        String(40),
        index=True,
    )

    order_id: Mapped[
        int | None
    ] = mapped_column(
        ForeignKey(
            "orders.id"
        ),
        nullable=True,
        index=True,
    )

    supplier_id: Mapped[
        int | None
    ] = mapped_column(
        ForeignKey(
            "suppliers.id"
        ),
        nullable=True,
        index=True,
    )

    business_id: Mapped[
        int | None
    ] = mapped_column(
        ForeignKey(
            "businesses.id"
        ),
        nullable=True,
        index=True,
    )

    latitude: Mapped[float] = mapped_column(
        Float,
    )

    longitude: Mapped[float] = mapped_column(
        Float,
    )

    location_label: Mapped[
        str | None
    ] = mapped_column(
        String(255),
        nullable=True,
    )

    planned_arrival_at: Mapped[
        datetime | None
    ] = mapped_column(
        DateTime,
        nullable=True,
    )

    actual_arrival_at: Mapped[
        datetime | None
    ] = mapped_column(
        DateTime,
        nullable=True,
    )

    planned_service_minutes: Mapped[float] = mapped_column(
        Float,
        default=0,
    )

    actual_service_minutes: Mapped[
        float | None
    ] = mapped_column(
        Float,
        nullable=True,
    )

    weight_delta_kg: Mapped[float] = mapped_column(
        Float,
        default=0,
    )

    volume_delta_l: Mapped[float] = mapped_column(
        Float,
        default=0,
    )

    load_weight_after_kg: Mapped[float] = mapped_column(
        Float,
        default=0,
    )

    load_volume_after_l: Mapped[float] = mapped_column(
        Float,
        default=0,
    )

    status: Mapped[str] = mapped_column(
        String(40),
        default="pending",
        index=True,
    )

    notes: Mapped[
        str | None
    ] = mapped_column(
        Text,
        nullable=True,
    )


class RoutePricingSnapshot(
    Base,
    TimestampMixin,
):
    __tablename__ = "route_pricing_snapshots"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
    )

    route_id: Mapped[int] = mapped_column(
        ForeignKey(
            "delivery_routes.id",
            ondelete="CASCADE",
        ),
        index=True,
    )

    engine_version: Mapped[str] = mapped_column(
        String(160),
        index=True,
    )

    vehicle_type: Mapped[str] = mapped_column(
        String(80),
    )

    verified_payload_kg: Mapped[float] = mapped_column(
        Float,
    )

    verified_volume_l: Mapped[float] = mapped_column(
        Float,
    )

    safe_capacity_ratio: Mapped[float] = mapped_column(
        Float,
    )

    fuel_price_per_liter: Mapped[float] = mapped_column(
        Float,
    )

    observed_km_per_liter: Mapped[float] = mapped_column(
        Float,
    )

    maintenance_cost_per_km: Mapped[float] = mapped_column(
        Float,
    )

    rider_time_value_per_hour: Mapped[float] = mapped_column(
        Float,
    )

    deadhead_km: Mapped[float] = mapped_column(
        Float,
        default=0,
    )

    service_route_km: Mapped[float] = mapped_column(
        Float,
        default=0,
    )

    reposition_km: Mapped[float] = mapped_column(
        Float,
        default=0,
    )

    driving_minutes: Mapped[float] = mapped_column(
        Float,
        default=0,
    )

    pickup_wait_minutes: Mapped[float] = mapped_column(
        Float,
        default=0,
    )

    loading_minutes: Mapped[float] = mapped_column(
        Float,
        default=0,
    )

    delivery_service_minutes: Mapped[float] = mapped_column(
        Float,
        default=0,
    )

    peak_weight_kg: Mapped[float] = mapped_column(
        Float,
        default=0,
    )

    peak_volume_l: Mapped[float] = mapped_column(
        Float,
        default=0,
    )

    weight_utilization: Mapped[float] = mapped_column(
        Float,
        default=0,
    )

    volume_utilization: Mapped[float] = mapped_column(
        Float,
        default=0,
    )

    fuel_cost: Mapped[float] = mapped_column(
        Numeric(14, 2),
        default=0,
    )

    maintenance_cost: Mapped[float] = mapped_column(
        Numeric(14, 2),
        default=0,
    )

    rider_time_cost: Mapped[float] = mapped_column(
        Numeric(14, 2),
        default=0,
    )

    pickup_work_cost: Mapped[float] = mapped_column(
        Numeric(14, 2),
        default=0,
    )

    delivery_work_cost: Mapped[float] = mapped_column(
        Numeric(14, 2),
        default=0,
    )

    load_work_cost: Mapped[float] = mapped_column(
        Numeric(14, 2),
        default=0,
    )

    complexity_cost: Mapped[float] = mapped_column(
        Numeric(14, 2),
        default=0,
    )

    modeled_route_cost: Mapped[float] = mapped_column(
        Numeric(14, 2),
        default=0,
    )

    recommended_driver_payout: Mapped[float] = mapped_column(
        Numeric(14, 2),
        default=0,
    )

    customer_delivery_revenue: Mapped[float] = mapped_column(
        Numeric(14, 2),
        default=0,
    )

    predicted_contribution: Mapped[float] = mapped_column(
        Numeric(14, 2),
        default=0,
    )

    predicted_margin_rate: Mapped[float] = mapped_column(
        Float,
        default=0,
    )

    live_market_multiplier: Mapped[float] = mapped_column(
        Float,
        default=1,
    )

    weather_risk_multiplier: Mapped[float] = mapped_column(
        Float,
        default=1,
    )

    time_of_day_multiplier: Mapped[float] = mapped_column(
        Float,
        default=1,
    )

    feature_json: Mapped[str] = mapped_column(
        Text,
        default="{}",
    )


class DriverRouteOffer(
    Base,
    TimestampMixin,
):
    __tablename__ = "driver_route_offers"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
    )

    route_id: Mapped[int] = mapped_column(
        ForeignKey(
            "delivery_routes.id",
            ondelete="CASCADE",
        ),
        index=True,
    )

    driver_id: Mapped[int] = mapped_column(
        ForeignKey(
            "drivers.id"
        ),
        index=True,
    )

    operator_id: Mapped[
        int | None
    ] = mapped_column(
        ForeignKey(
            "users.id"
        ),
        nullable=True,
    )

    recommended_payout: Mapped[float] = mapped_column(
        Numeric(14, 2),
    )

    opening_offer: Mapped[float] = mapped_column(
        Numeric(14, 2),
    )

    counter_offer: Mapped[
        float | None
    ] = mapped_column(
        Numeric(14, 2),
        nullable=True,
    )

    final_payout: Mapped[
        float | None
    ] = mapped_column(
        Numeric(14, 2),
        nullable=True,
    )

    minimum_offer: Mapped[
        float | None
    ] = mapped_column(
        Numeric(14, 2),
        nullable=True,
    )

    maximum_offer: Mapped[
        float | None
    ] = mapped_column(
        Numeric(14, 2),
        nullable=True,
    )

    outcome: Mapped[str] = mapped_column(
        String(40),
        default="pending",
        index=True,
    )

    rejection_reason: Mapped[
        str | None
    ] = mapped_column(
        Text,
        nullable=True,
    )

    responded_at: Mapped[
        datetime | None
    ] = mapped_column(
        DateTime,
        nullable=True,
    )


# ============================================================
# STOREDASH VEHICLE CAPACITY + MULTI-ORDER BATCHING
# ============================================================


class VehicleSpec(
    Base,
    TimestampMixin,
):
    """
    Shared specification for a real vehicle make/model.

    Vehicle specification is NOT a customer-pricing input.

    It exists primarily for:
    - capacity checks
    - route feasibility
    - rider operating economics
    """

    __tablename__ = "vehicle_specs"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
    )

    manufacturer: Mapped[str] = mapped_column(
        String(120),
        index=True,
    )

    model: Mapped[str] = mapped_column(
        String(160),
        index=True,
    )

    variant: Mapped[
        str | None
    ] = mapped_column(
        String(160),
        nullable=True,
    )

    # Manufacturer / verified physical maximum.
    max_payload_kg: Mapped[float] = mapped_column(
        Float,
    )

    # Normal dedicated cargo compartment.
    cargo_volume_l: Mapped[float] = mapped_column(
        Float,
    )

    # Optional additional safe cargo area.
    #
    # Example:
    # an unoccupied/folded rear-seat area in a car.
    seat_cargo_volume_l: Mapped[float] = mapped_column(
        Float,
        default=0,
    )

    reference_km_per_liter: Mapped[
        float | None
    ] = mapped_column(
        Float,
        nullable=True,
    )

    fuel_type: Mapped[
        str | None
    ] = mapped_column(
        String(40),
        nullable=True,
    )

    source_name: Mapped[
        str | None
    ] = mapped_column(
        String(255),
        nullable=True,
    )

    source_url: Mapped[
        str | None
    ] = mapped_column(
        Text,
        nullable=True,
    )

    verified_at: Mapped[
        datetime | None
    ] = mapped_column(
        DateTime,
        nullable=True,
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        index=True,
    )


class DriverVehicle(
    Base,
    TimestampMixin,
):
    """
    One actual vehicle belonging to / used by a StoreDash rider.

    Most values come automatically from VehicleSpec.

    Overrides exist only when the actual vehicle differs.
    """

    __tablename__ = "driver_vehicles"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
    )

    driver_id: Mapped[int] = mapped_column(
        ForeignKey(
            "drivers.id",
            ondelete="CASCADE",
        ),
        index=True,
    )

    vehicle_spec_id: Mapped[int] = mapped_column(
        ForeignKey(
            "vehicle_specs.id"
        ),
        index=True,
    )

    registration: Mapped[
        str | None
    ] = mapped_column(
        String(80),
        nullable=True,
        index=True,
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        index=True,
    )

    # If true, StoreDash may use the extra seat-area volume
    # configured on VehicleSpec.
    #
    # Only safe/unoccupied cargo space should be enabled.
    seat_area_available_for_cargo: Mapped[
        bool
    ] = mapped_column(
        Boolean,
        default=False,
    )

    # Until real operating history gives us confidence,
    # we can plan slightly below the absolute physical max.
    safe_capacity_ratio: Mapped[float] = mapped_column(
        Float,
        default=0.90,
    )

    payload_override_kg: Mapped[
        float | None
    ] = mapped_column(
        Float,
        nullable=True,
    )

    cargo_volume_override_l: Mapped[
        float | None
    ] = mapped_column(
        Float,
        nullable=True,
    )

    seat_cargo_volume_override_l: Mapped[
        float | None
    ] = mapped_column(
        Float,
        nullable=True,
    )

    # StoreDash learns this from real deliveries.
    observed_km_per_liter: Mapped[
        float | None
    ] = mapped_column(
        Float,
        nullable=True,
    )

    current_latitude: Mapped[
        float | None
    ] = mapped_column(
        Float,
        nullable=True,
    )

    current_longitude: Mapped[
        float | None
    ] = mapped_column(
        Float,
        nullable=True,
    )

    current_area: Mapped[
        str | None
    ] = mapped_column(
        String(160),
        nullable=True,
    )

    notes: Mapped[
        str | None
    ] = mapped_column(
        Text,
        nullable=True,
    )


class DeliveryBatch(
    Base,
    TimestampMixin,
):
    """
    One physical trip containing one or more customer orders.

    StoreDash does NOT split a batch into multiple trips.

    If capacity is exceeded, another order is not admitted.
    """

    __tablename__ = "delivery_batches"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
    )

    status: Mapped[str] = mapped_column(
        String(60),
        default="building",
        index=True,
    )

    driver_id: Mapped[
        int | None
    ] = mapped_column(
        ForeignKey(
            "drivers.id"
        ),
        nullable=True,
        index=True,
    )

    driver_vehicle_id: Mapped[
        int | None
    ] = mapped_column(
        ForeignKey(
            "driver_vehicles.id"
        ),
        nullable=True,
        index=True,
    )

    # Locked policy.
    single_trip_required: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
    )

    capacity_feasible: Mapped[
        bool | None
    ] = mapped_column(
        Boolean,
        nullable=True,
    )

    order_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
    )

    pickup_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
    )

    delivery_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
    )

    planned_distance_km: Mapped[float] = mapped_column(
        Float,
        default=0,
    )

    planned_minutes: Mapped[float] = mapped_column(
        Float,
        default=0,
    )

    actual_distance_km: Mapped[
        float | None
    ] = mapped_column(
        Float,
        nullable=True,
    )

    actual_minutes: Mapped[
        float | None
    ] = mapped_column(
        Float,
        nullable=True,
    )

    peak_weight_kg: Mapped[float] = mapped_column(
        Float,
        default=0,
    )

    peak_volume_l: Mapped[float] = mapped_column(
        Float,
        default=0,
    )

    customer_delivery_revenue: Mapped[float] = mapped_column(
        Numeric(14, 2),
        default=0,
    )

    predicted_driver_payout: Mapped[
        float | None
    ] = mapped_column(
        Numeric(14, 2),
        nullable=True,
    )

    accepted_driver_payout: Mapped[
        float | None
    ] = mapped_column(
        Numeric(14, 2),
        nullable=True,
    )

    actual_driver_payout: Mapped[
        float | None
    ] = mapped_column(
        Numeric(14, 2),
        nullable=True,
    )

    predicted_contribution: Mapped[
        float | None
    ] = mapped_column(
        Numeric(14, 2),
        nullable=True,
    )

    actual_contribution: Mapped[
        float | None
    ] = mapped_column(
        Numeric(14, 2),
        nullable=True,
    )

    predicted_margin_rate: Mapped[
        float | None
    ] = mapped_column(
        Float,
        nullable=True,
    )

    actual_margin_rate: Mapped[
        float | None
    ] = mapped_column(
        Float,
        nullable=True,
    )

    started_at: Mapped[
        datetime | None
    ] = mapped_column(
        DateTime,
        nullable=True,
    )

    completed_at: Mapped[
        datetime | None
    ] = mapped_column(
        DateTime,
        nullable=True,
    )

    planner_version: Mapped[str | None] = mapped_column(
        String(160),
        nullable=True,
    )

    road_provider: Mapped[str | None] = mapped_column(
        String(80),
        nullable=True,
    )

    traffic_aware: Mapped[bool | None] = mapped_column(
        Boolean,
        nullable=True,
    )

    recommended_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True,
    )

    notes: Mapped[
        str | None
    ] = mapped_column(
        Text,
        nullable=True,
    )


class BatchOrder(
    Base,
    TimestampMixin,
):
    __tablename__ = "batch_orders"

    __table_args__ = (
        UniqueConstraint(
            "batch_id",
            "order_id",
            name="uq_batch_order",
        ),
    )

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
    )

    batch_id: Mapped[int] = mapped_column(
        ForeignKey(
            "delivery_batches.id",
            ondelete="CASCADE",
        ),
        index=True,
    )

    order_id: Mapped[int] = mapped_column(
        ForeignKey(
            "orders.id",
            ondelete="CASCADE",
        ),
        index=True,
    )

    order_weight_kg: Mapped[float] = mapped_column(
        Float,
        default=0,
    )

    order_volume_l: Mapped[float] = mapped_column(
        Float,
        default=0,
    )

    customer_delivery_fee: Mapped[float] = mapped_column(
        Numeric(14, 2),
        default=0,
    )

    delivery_sequence: Mapped[
        int | None
    ] = mapped_column(
        Integer,
        nullable=True,
    )

    status: Mapped[str] = mapped_column(
        String(50),
        default="planned",
        index=True,
    )


class BatchStop(
    Base,
    TimestampMixin,
):
    """
    Exact physical load after every pickup/drop.

    This is what prevents hidden overloads.
    """

    __tablename__ = "batch_stops"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
    )

    batch_id: Mapped[int] = mapped_column(
        ForeignKey(
            "delivery_batches.id",
            ondelete="CASCADE",
        ),
        index=True,
    )

    sequence: Mapped[int] = mapped_column(
        Integer,
        index=True,
    )

    stop_type: Mapped[str] = mapped_column(
        String(30),
        index=True,
    )

    order_id: Mapped[
        int | None
    ] = mapped_column(
        ForeignKey(
            "orders.id"
        ),
        nullable=True,
        index=True,
    )

    supplier_id: Mapped[
        int | None
    ] = mapped_column(
        ForeignKey(
            "suppliers.id"
        ),
        nullable=True,
        index=True,
    )

    business_id: Mapped[
        int | None
    ] = mapped_column(
        ForeignKey(
            "businesses.id"
        ),
        nullable=True,
        index=True,
    )

    latitude: Mapped[float] = mapped_column(
        Float,
    )

    longitude: Mapped[float] = mapped_column(
        Float,
    )

    location_label: Mapped[
        str | None
    ] = mapped_column(
        String(255),
        nullable=True,
    )

    # Pickup = positive.
    # Delivery = negative.
    weight_delta_kg: Mapped[float] = mapped_column(
        Float,
        default=0,
    )

    volume_delta_l: Mapped[float] = mapped_column(
        Float,
        default=0,
    )

    load_weight_after_kg: Mapped[float] = mapped_column(
        Float,
        default=0,
    )

    load_volume_after_l: Mapped[float] = mapped_column(
        Float,
        default=0,
    )

    planned_leg_distance_km: Mapped[float] = mapped_column(
        Float,
        default=0,
    )

    planned_leg_minutes: Mapped[float] = mapped_column(
        Float,
        default=0,
    )

    planned_arrival_offset_minutes: Mapped[float] = mapped_column(
        Float,
        default=0,
    )

    planned_arrival_at: Mapped[
        datetime | None
    ] = mapped_column(
        DateTime,
        nullable=True,
    )

    actual_arrival_at: Mapped[
        datetime | None
    ] = mapped_column(
        DateTime,
        nullable=True,
    )

    planned_service_minutes: Mapped[float] = mapped_column(
        Float,
        default=0,
    )

    actual_service_minutes: Mapped[
        float | None
    ] = mapped_column(
        Float,
        nullable=True,
    )

    status: Mapped[str] = mapped_column(
        String(40),
        default="pending",
        index=True,
    )


class BatchDriverOffer(
    Base,
    TimestampMixin,
):
    """
    One driver offer for an entire multi-order StoreDash batch.

    This deliberately does NOT use the old per-order 75/25 rule.
    """

    __tablename__ = "batch_driver_offers"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
    )

    batch_id: Mapped[int] = mapped_column(
        ForeignKey(
            "delivery_batches.id",
            ondelete="CASCADE",
        ),
        index=True,
    )

    driver_id: Mapped[int] = mapped_column(
        ForeignKey(
            "drivers.id"
        ),
        index=True,
    )

    operator_id: Mapped[int | None] = mapped_column(
        ForeignKey(
            "users.id"
        ),
        nullable=True,
    )

    recommended_payout: Mapped[float | None] = mapped_column(
        Numeric(14, 2),
        nullable=True,
    )

    opening_offer: Mapped[float] = mapped_column(
        Numeric(14, 2),
    )

    driver_counter: Mapped[float | None] = mapped_column(
        Numeric(14, 2),
        nullable=True,
    )

    maximum_authorized_payout: Mapped[float | None] = mapped_column(
        Numeric(14, 2),
        nullable=True,
    )

    final_payout: Mapped[float | None] = mapped_column(
        Numeric(14, 2),
        nullable=True,
    )

    outcome: Mapped[str] = mapped_column(
        String(40),
        default="pending",
        index=True,
    )

    notes: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    responded_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True,
    )

    locked_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True,
    )



# ============================================================
# STOREDASH EMPLOYEE AUTH
# ============================================================

class ApprovedEmployee(
    Base,
    TimestampMixin,
):
    __tablename__ = "approved_employees"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
    )

    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        index=True,
    )

    name: Mapped[str | None] = mapped_column(
        String(120),
        nullable=True,
    )

    role: Mapped[Role] = mapped_column(
        SAEnum(Role),
        default=Role.OPERATIONS,
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
    )

    claimed_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id"),
        nullable=True,
        unique=True,
    )

    claimed_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True,
    )


class UserCredential(
    Base,
    TimestampMixin,
):
    __tablename__ = "user_credentials"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
    )

    user_id: Mapped[int] = mapped_column(
        ForeignKey(
            "users.id",
            ondelete="CASCADE",
        ),
        unique=True,
        index=True,
    )

    password_salt: Mapped[str] = mapped_column(
        String(128),
    )

    password_hash: Mapped[str] = mapped_column(
        String(128),
    )

    password_iterations: Mapped[int] = mapped_column(
        Integer,
        default=310000,
    )


class AuthSession(
    Base,
):
    __tablename__ = "auth_sessions"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
    )

    user_id: Mapped[int] = mapped_column(
        ForeignKey(
            "users.id",
            ondelete="CASCADE",
        ),
        index=True,
    )

    token_hash: Mapped[str] = mapped_column(
        String(64),
        unique=True,
        index=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
    )

    expires_at: Mapped[datetime] = mapped_column(
        DateTime,
        index=True,
    )

    revoked_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True,
    )
