from __future__ import annotations

import json

from datetime import datetime
from decimal import Decimal
from typing import Literal
from zoneinfo import ZoneInfo

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

from sqlalchemy.orm import (
    Session,
    selectinload,
)

from app.core.config import settings
from app.core.db import get_db

from app.models import (
    AuditEvent,
    Business,
    CarrierBid,
    DeliveryPricingSnapshot,
    Order,
    OrderStatus,
    PricingModelVersion,
    Supplier,
)

from app.services.delivery_market import (
    CarrierBidInput,
    reconcile_delivery_quote,
    summarize_carrier_market,
)

from app.services.pricing import (
    TAX_RATE,
    calculate_route,
    calculate_service_fee,
    round_money,
)

from app.services.upfront_delivery import (
    DEFAULT_COEFFICIENTS,
    estimate_upfront_delivery,
)


router = APIRouter(
    prefix="/orders",
    tags=["delivery-market"],
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
        select(
            Order
        )
        .options(
            selectinload(
                Order.items
            )
        )
        .where(
            Order.id
            == order_id
        )
    ).first()


def active_model(
    db: Session,
):

    model = db.scalars(
        select(
            PricingModelVersion
        )
        .where(
            PricingModelVersion.status
            == "active"
        )
        .order_by(
            PricingModelVersion.id.desc()
        )
    ).first()


    if not model:

        return (
            None,
            "storedash-market-v1-public-bootstrap",
            DEFAULT_COEFFICIENTS,
        )


    try:

        coefficients = json.loads(
            model.coefficients_json
            or "{}"
        )

    except Exception:

        coefficients = {}


    merged = dict(
        DEFAULT_COEFFICIENTS
    )

    merged.update(
        coefficients
    )


    merged[
        "capacity_multipliers"
    ] = (
        DEFAULT_COEFFICIENTS[
            "capacity_multipliers"
        ]
        | coefficients.get(
            "capacity_multipliers",
            {},
        )
    )


    merged[
        "distance_band_multipliers"
    ] = (
        DEFAULT_COEFFICIENTS[
            "distance_band_multipliers"
        ]
        | coefficients.get(
            "distance_band_multipliers",
            {},
        )
    )


    return (
        model,
        model.version_name,
        merged,
    )


def latest_snapshot(
    db: Session,
    order_id: int,
):

    return db.scalars(
        select(
            DeliveryPricingSnapshot
        )
        .where(
            DeliveryPricingSnapshot.order_id
            == order_id
        )
        .order_by(
            DeliveryPricingSnapshot.id.desc()
        )
    ).first()


def bids_for_snapshot(
    db: Session,
    snapshot_id: int,
):

    return list(
        db.scalars(
            select(
                CarrierBid
            )
            .where(
                CarrierBid.pricing_snapshot_id
                == snapshot_id
            )
            .order_by(
                CarrierBid.amount.asc(),
                CarrierBid.id.asc(),
            )
        ).all()
    )


def serialize_bid(
    bid: CarrierBid,
) -> dict:

    return {
        "id":
            bid.id,

        "provider":
            bid.provider,

        "external_bid_id":
            bid.external_bid_id,

        "amount":
            float(
                bid.amount
            ),

        "pickup_eta_minutes":
            bid.pickup_eta_minutes,

        "provider_rating":
            bid.provider_rating,

        "vehicle_type":
            bid.vehicle_type,

        "vehicle_capacity_kg":
            bid.vehicle_capacity_kg,

        "qualified":
            bid.qualified,

        "capacity_ok":
            bid.capacity_ok,

        "rejection_reason":
            bid.rejection_reason,

        "selected":
            bid.selected,

        "created_at":
            bid.created_at,
    }


def serialize_snapshot(
    snapshot: DeliveryPricingSnapshot,
) -> dict:

    return {
        "id":
            snapshot.id,

        "order_id":
            snapshot.order_id,

        "status":
            snapshot.status,

        "provider":
            snapshot.provider,

        "model_version":
            snapshot.model_version_name,

        "goods_total":
            float(
                snapshot.goods_total
            ),

        "service_fee":
            float(
                snapshot.service_fee
            ),

        "route_distance_km":
            snapshot.route_distance_km,

        "route_duration_minutes":
            snapshot.route_duration_minutes,

        "supplier_stop_count":
            snapshot.supplier_stop_count,

        "item_count":
            snapshot.item_count,

        "total_load_units":
            snapshot.total_load_units,

        "total_weight_kg":
            snapshot.total_weight_kg,

        "total_volume_l":
            snapshot.total_volume_l,

        "total_handling_score":
            snapshot.total_handling_score,

        "total_fragility_score":
            snapshot.total_fragility_score,

        "chargeable_weight_kg":
            snapshot.chargeable_weight_kg,

        "capacity_class":
            snapshot.capacity_class,

        "distance_band":
            snapshot.distance_band,

        "model_predicted_carrier_cost":
            float(
                snapshot.model_predicted_carrier_cost
            ),

        "model_customer_price":
            float(
                snapshot.model_customer_price
            ),

        "live_market_min":
            float(
                snapshot.live_market_min
            )
            if snapshot.live_market_min
            is not None
            else None,

        "live_market_median":
            float(
                snapshot.live_market_median
            )
            if snapshot.live_market_median
            is not None
            else None,

        "live_market_recommended":
            float(
                snapshot.live_market_recommended
            )
            if snapshot.live_market_recommended
            is not None
            else None,

        "selected_carrier_bid_id":
            snapshot.selected_carrier_bid_id,

        "selected_carrier_cost":
            float(
                snapshot.selected_carrier_cost
            )
            if snapshot.selected_carrier_cost
            is not None
            else None,

        "customer_delivery_fee":
            float(
                snapshot.customer_delivery_fee
            )
            if snapshot.customer_delivery_fee
            is not None
            else None,

        "storedash_delivery_profit":
            float(
                snapshot.storedash_delivery_profit
            )
            if snapshot.storedash_delivery_profit
            is not None
            else None,

        "storedash_margin_rate":
            snapshot.storedash_margin_rate,

        "pricing_mode":
            snapshot.pricing_mode,

        "customer_decision":
            snapshot.customer_decision,

        "customer_decision_at":
            snapshot.customer_decision_at,

        "actual_carrier_cost":
            float(
                snapshot.actual_carrier_cost
            )
            if snapshot.actual_carrier_cost
            is not None
            else None,

        "actual_delivery_minutes":
            snapshot.actual_delivery_minutes,

        "created_at":
            snapshot.created_at,

        "finalized_at":
            snapshot.finalized_at,
    }


def audit(
    db: Session,
    order: Order,
    action: str,
    after: dict,
):

    db.add(
        AuditEvent(
            actor_id=
                order.operator_id,

            action=
                action,

            entity_type=
                "order",

            entity_id=
                order.id,

            after_json=
                json.dumps(
                    after,
                    default=str,
                ),
        )
    )


def validate_order_for_market(
    order: Order,
):

    if (
        order.status
        not in PREFINAL_STATUSES
    ):

        raise HTTPException(
            status_code=409,
            detail=(
                "This order can no longer "
                "be repriced."
            ),
        )


    errors = []


    for item in order.items:

        if (
            item.availability_status
            not in {
                "available",
                "partial",
                "unavailable",
            }
        ):

            errors.append(
                f"{item.name}: sourcing incomplete"
            )

            continue


        if (
            item.availability_status
            in {
                "available",
                "partial",
            }
        ):

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


            if item.confirmed_price is None:

                errors.append(
                    f"{item.name}: confirmed price missing"
                )


            if (
                item.total_load_units
                is None
                or
                item.total_weight_kg
                is None
                or
                item.total_volume_l
                is None
                or
                item.total_handling_score
                is None
                or
                item.total_fragility_score
                is None
            ):

                errors.append(
                    f"{item.name}: logistics profile incomplete"
                )


    if errors:

        raise HTTPException(
            status_code=409,
            detail={
                "message":
                    "Order is not ready "
                    "for the delivery market.",

                "items":
                    errors,
            },
        )


class CarrierBidCreate(
    BaseModel
):

    provider: str = Field(
        default="cargomov",
        min_length=1,
        max_length=80,
    )

    external_bid_id: (
        str | None
    ) = None

    amount: Decimal = Field(
        gt=0,
    )

    pickup_eta_minutes: (
        float | None
    ) = Field(
        default=None,
        ge=0,
    )

    provider_rating: (
        float | None
    ) = Field(
        default=None,
        ge=0,
        le=5,
    )

    vehicle_type: (
        str | None
    ) = None

    vehicle_capacity_kg: (
        float | None
    ) = Field(
        default=None,
        ge=0,
    )

    qualified: bool = True

    capacity_ok: bool = True

    rejection_reason: (
        str | None
    ) = None

    raw_payload: (
        dict | None
    ) = None


class FinalizeMarketQuote(
    BaseModel
):

    bid_id: int


class CustomerDecision(
    BaseModel
):

    decision: Literal[
        "accepted",
        "declined",
    ]


class DeliveryOutcome(
    BaseModel
):

    actual_carrier_cost: (
        Decimal | None
    ) = Field(
        default=None,
        ge=0,
    )

    actual_delivery_minutes: (
        float | None
    ) = Field(
        default=None,
        ge=0,
    )

    notes: (
        str | None
    ) = None


@router.post(
    "/{order_id}/delivery-market/prepare"
)
def prepare_delivery_market(
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


    validate_order_for_market(
        order
    )


    deliverable = [
        item
        for item in order.items
        if item.availability_status
        in {
            "available",
            "partial",
        }
    ]


    goods_total = sum(
        Decimal(
            str(
                item.confirmed_quantity
                or 0
            )
        )
        *
        Decimal(
            str(
                item.confirmed_price
                or 0
            )
        )
        for item in deliverable
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
                "Customer delivery location "
                "is incomplete."
            ),
        )


    supplier_ids = list(
        dict.fromkeys(
            item.supplier_id
            for item in deliverable
            if item.supplier_id
        )
    )


    suppliers = []


    for supplier_id in supplier_ids:

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
                    f"Supplier {supplier_id} "
                    "does not have a usable "
                    "pickup location."
                ),
            )


        suppliers.append(
            supplier
        )


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
                for supplier
                in suppliers
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
                "Could not calculate "
                f"delivery route: {exc}"
            ),
        ) from exc


    total_load_units = sum(
        float(
            item.total_load_units
            or 0
        )
        for item in deliverable
    )


    total_weight_kg = sum(
        float(
            item.total_weight_kg
            or 0
        )
        for item in deliverable
    )


    total_volume_l = sum(
        float(
            item.total_volume_l
            or 0
        )
        for item in deliverable
    )


    total_handling_score = sum(
        float(
            item.total_handling_score
            or 0
        )
        for item in deliverable
    )


    total_fragility_score = sum(
        float(
            item.total_fragility_score
            or 0
        )
        for item in deliverable
    )


    model, model_name, coefficients = (
        active_model(
            db
        )
    )


    estimate = estimate_upfront_delivery(
        distance_km=
            route[
                "distance_km"
            ],

        duration_minutes=
            route[
                "duration_minutes"
            ],

        supplier_count=
            len(
                suppliers
            ),

        total_load_units=
            total_load_units,

        total_weight_kg=
            total_weight_kg,

        total_volume_l=
            total_volume_l,

        total_handling_score=
            total_handling_score,

        total_fragility_score=
            total_fragility_score,

        coefficients=
            coefficients,
    )


    service_fee = calculate_service_fee(
        goods_total=
            float(
                goods_total
            ),

        supplier_count=
            len(
                suppliers
            ),

        item_count=
            len(
                deliverable
            ),
    )


    now = ghana_now()


    # Preserve history instead of overwriting old predictions.

    old_snapshot = latest_snapshot(
        db,
        order.id,
    )


    if (
        old_snapshot
        and
        old_snapshot.status
        in {
            "awaiting_carrier_bids",
            "customer_quote_ready",
        }
    ):

        old_snapshot.status = (
            "superseded"
        )


    item_features = []


    for item in deliverable:

        item_features.append(
            {
                "item_id":
                    item.id,

                "name":
                    item.name,

                "quantity":
                    float(
                        item.confirmed_quantity
                        or 0
                    ),

                "category_id":
                    getattr(
                        item,
                        "logistics_category_id",
                        None,
                    ),

                "logistics_type_id":
                    getattr(
                        item,
                        "logistics_type_id",
                        None,
                    ),

                "package_type":
                    getattr(
                        item,
                        "logistics_package_type",
                        None,
                    ),

                "variant":
                    getattr(
                        item,
                        "logistics_variant_key",
                        None,
                    ),

                "size_detail":
                    getattr(
                        item,
                        "logistics_size_detail",
                        None,
                    ),

                "weight_kg":
                    float(
                        item.total_weight_kg
                        or 0
                    ),

                "volume_l":
                    float(
                        item.total_volume_l
                        or 0
                    ),

                "handling":
                    float(
                        item.total_handling_score
                        or 0
                    ),

                "fragility":
                    float(
                        item.total_fragility_score
                        or 0
                    ),
            }
        )


    feature_payload = {
        "engine":
            estimate.engine_version,

        "items":
            item_features,

        "supplier_ids":
            supplier_ids,

        "supplier_coordinates": [
            {
                "id":
                    supplier.id,

                "latitude":
                    float(
                        supplier.latitude
                    ),

                "longitude":
                    float(
                        supplier.longitude
                    ),
            }
            for supplier
            in suppliers
        ],

        "customer_coordinate": {
            "latitude":
                float(
                    business.latitude
                ),

            "longitude":
                float(
                    business.longitude
                ),
        },

        "time": {
            "day_of_week":
                now.weekday(),

            "hour_of_day":
                now.hour,
        },

        "model_components":
            estimate.to_dict(),
    }


    snapshot = DeliveryPricingSnapshot(
        order_id=
            order.id,

        model_version_id=
            model.id
            if model
            else None,

        model_version_name=
            model_name,

        status=
            "awaiting_carrier_bids",

        provider=
            "cargomov",

        goods_total=
            goods_total,

        service_fee=
            service_fee,

        route_distance_km=
            route[
                "distance_km"
            ],

        route_duration_minutes=
            route[
                "duration_minutes"
            ],

        supplier_stop_count=
            len(
                suppliers
            ),

        item_count=
            len(
                deliverable
            ),

        total_load_units=
            total_load_units,

        total_weight_kg=
            total_weight_kg,

        total_volume_l=
            total_volume_l,

        total_handling_score=
            total_handling_score,

        total_fragility_score=
            total_fragility_score,

        chargeable_weight_kg=
            estimate.chargeable_weight_kg,

        capacity_class=
            estimate.capacity_class,

        distance_band=
            estimate.distance_band,

        day_of_week=
            now.weekday(),

        hour_of_day=
            now.hour,

        feature_json=
            json.dumps(
                feature_payload,
                default=str,
            ),

        model_predicted_carrier_cost=
            estimate.predicted_carrier_cost,

        model_customer_price=
            estimate.predicted_customer_price,
    )


    db.add(
        snapshot
    )


    # The customer DOES NOT have a final quote yet.

    order.goods_total = (
        goods_total
    )

    order.service_fee = (
        service_fee
    )

    order.delivery_fee = 0
    order.tax_total = 0
    order.final_total = 0

    order.route_distance_km = (
        route[
            "distance_km"
        ]
    )

    order.route_duration_minutes = (
        route[
            "duration_minutes"
        ]
    )

    order.supplier_stop_count = (
        len(
            suppliers
        )
    )

    order.total_load_units = (
        total_load_units
    )

    if hasattr(
        order,
        "total_weight_kg",
    ):
        order.total_weight_kg = (
            total_weight_kg
        )


    if hasattr(
        order,
        "total_volume_l",
    ):
        order.total_volume_l = (
            total_volume_l
        )


    if hasattr(
        order,
        "total_handling_score",
    ):
        order.total_handling_score = (
            total_handling_score
        )


    if hasattr(
        order,
        "total_fragility_score",
    ):
        order.total_fragility_score = (
            total_fragility_score
        )


    order.estimated_driver_market_cost = (
        estimate.predicted_carrier_cost
    )

    order.pricing_version = (
        model_name
    )

    order.quote_generated_at = None

    order.customer_approved_at = None

    order.status = (
        OrderStatus.SOURCING
    )


    for field in (
        "driver_floor",
        "driver_target",
        "driver_ceiling",
    ):

        if hasattr(
            order,
            field,
        ):

            setattr(
                order,
                field,
                None,
            )


    audit(
        db,
        order,
        "delivery_market_prepared",
        {
            "model_version":
                model_name,

            "predicted_carrier_cost":
                estimate.predicted_carrier_cost,

            "predicted_customer_price":
                estimate.predicted_customer_price,

            "capacity_class":
                estimate.capacity_class,

            "distance_km":
                route[
                    "distance_km"
                ],

            "duration_minutes":
                route[
                    "duration_minutes"
                ],
        },
    )


    db.commit()
    db.refresh(
        snapshot
    )


    return {
        "message":
            "Delivery market prepared. "
            "Customer price is NOT final yet.",

        "snapshot":
            serialize_snapshot(
                snapshot
            ),

        "model":
            estimate.to_dict(),
    }


@router.post(
    "/{order_id}/delivery-market/bids"
)
def add_carrier_bid(
    order_id: int,
    payload: CarrierBidCreate,
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


    snapshot = latest_snapshot(
        db,
        order_id,
    )


    if (
        not snapshot
        or
        snapshot.status
        != "awaiting_carrier_bids"
    ):

        raise HTTPException(
            status_code=409,
            detail=(
                "Prepare the delivery market "
                "before recording bids."
            ),
        )


    bid = CarrierBid(
        order_id=
            order.id,

        pricing_snapshot_id=
            snapshot.id,

        provider=
            payload.provider
            .strip()
            .lower(),

        external_bid_id=
            payload.external_bid_id,

        amount=
            payload.amount,

        pickup_eta_minutes=
            payload.pickup_eta_minutes,

        provider_rating=
            payload.provider_rating,

        vehicle_type=
            payload.vehicle_type,

        vehicle_capacity_kg=
            payload.vehicle_capacity_kg,

        qualified=
            payload.qualified,

        capacity_ok=
            payload.capacity_ok,

        rejection_reason=
            payload.rejection_reason,

        raw_payload_json=
            json.dumps(
                payload.raw_payload,
                default=str,
            )
            if payload.raw_payload
            is not None
            else None,
    )


    db.add(
        bid
    )


    audit(
        db,
        order,
        "carrier_bid_recorded",
        {
            "provider":
                bid.provider,

            "amount":
                str(
                    bid.amount
                ),

            "qualified":
                bid.qualified,

            "capacity_ok":
                bid.capacity_ok,

            "pickup_eta_minutes":
                bid.pickup_eta_minutes,
        },
    )


    db.commit()
    db.refresh(
        bid
    )


    return serialize_bid(
        bid
    )


@router.get(
    "/{order_id}/delivery-market"
)
def get_delivery_market(
    order_id: int,
    db: Session = Depends(
        get_db
    ),
):

    snapshot = latest_snapshot(
        db,
        order_id,
    )


    if not snapshot:

        raise HTTPException(
            status_code=404,
            detail=(
                "No delivery-market "
                "snapshot exists."
            ),
        )


    bids = bids_for_snapshot(
        db,
        snapshot.id,
    )


    qualified_inputs = [
        CarrierBidInput(
            amount=
                float(
                    bid.amount
                ),

            qualified=
                bid.qualified,

            provider=
                bid.provider,

            external_bid_id=
                bid.external_bid_id,

            pickup_eta_minutes=
                bid.pickup_eta_minutes,

            rating=
                bid.provider_rating,

            capacity_ok=
                bid.capacity_ok,
        )
        for bid
        in bids
    ]


    market_summary = None


    try:

        if qualified_inputs:

            market_summary = (
                summarize_carrier_market(
                    qualified_inputs
                ).to_dict()
            )

    except ValueError:

        market_summary = None


    return {
        "snapshot":
            serialize_snapshot(
                snapshot
            ),

        "bids": [
            serialize_bid(
                bid
            )
            for bid
            in bids
        ],

        "market_summary":
            market_summary,
    }


@router.post(
    "/{order_id}/delivery-market/finalize"
)
def finalize_delivery_market(
    order_id: int,
    payload: FinalizeMarketQuote,
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


    snapshot = latest_snapshot(
        db,
        order_id,
    )


    if (
        not snapshot
        or
        snapshot.status
        != "awaiting_carrier_bids"
    ):

        raise HTTPException(
            status_code=409,
            detail=(
                "There is no open "
                "delivery market to finalize."
            ),
        )


    selected_bid = db.get(
        CarrierBid,
        payload.bid_id,
    )


    if (
        not selected_bid
        or
        selected_bid.order_id
        != order.id
        or
        selected_bid.pricing_snapshot_id
        != snapshot.id
    ):

        raise HTTPException(
            status_code=404,
            detail=(
                "Carrier bid does not "
                "belong to this quote."
            ),
        )


    if (
        not selected_bid.qualified
        or
        not selected_bid.capacity_ok
    ):

        raise HTTPException(
            status_code=409,
            detail=(
                "Selected carrier bid "
                "is not qualified."
            ),
        )


    bids = bids_for_snapshot(
        db,
        snapshot.id,
    )


    summary = summarize_carrier_market(
        [
            CarrierBidInput(
                amount=
                    float(
                        bid.amount
                    ),

                qualified=
                    bid.qualified,

                provider=
                    bid.provider,

                external_bid_id=
                    bid.external_bid_id,

                pickup_eta_minutes=
                    bid.pickup_eta_minutes,

                rating=
                    bid.provider_rating,

                capacity_ok=
                    bid.capacity_ok,
            )
            for bid
            in bids
        ]
    )


    decision = reconcile_delivery_quote(
        storedash_model_price=
            float(
                snapshot.model_customer_price
            ),

        carrier_cost=
            float(
                selected_bid.amount
            ),
    )


    for bid in bids:

        bid.selected = (
            bid.id
            == selected_bid.id
        )


    snapshot.live_market_min = (
        summary.minimum_bid
    )

    snapshot.live_market_median = (
        summary.median_bid
    )

    snapshot.live_market_recommended = (
        summary.recommended_bid
    )

    snapshot.selected_carrier_bid_id = (
        selected_bid.id
    )

    snapshot.selected_carrier_cost = (
        decision.carrier_cost
    )

    snapshot.customer_delivery_fee = (
        decision.customer_delivery_fee
    )

    snapshot.storedash_delivery_profit = (
        decision.storedash_delivery_profit
    )

    snapshot.storedash_margin_rate = (
        decision.storedash_margin_rate
    )

    snapshot.pricing_mode = (
        decision.pricing_mode
    )

    snapshot.status = (
        "customer_quote_ready"
    )

    snapshot.finalized_at = (
        ghana_now()
    )


    service_fee = float(
        snapshot.service_fee
        or 0
    )


    goods_total = float(
        snapshot.goods_total
        or 0
    )


    subtotal_before_tax = (
        goods_total
        + decision.customer_delivery_fee
        + service_fee
    )


    tax_total = round_money(
        subtotal_before_tax
        * TAX_RATE
    )


    final_total = round_money(
        subtotal_before_tax
        + tax_total
    )


    order.goods_total = (
        snapshot.goods_total
    )

    order.delivery_fee = (
        decision.customer_delivery_fee
    )

    order.service_fee = (
        snapshot.service_fee
    )

    order.tax_total = (
        tax_total
    )

    order.final_total = (
        final_total
    )

    order.delivery_margin = (
        decision.storedash_delivery_profit
    )

    order.estimated_driver_market_cost = (
        snapshot.model_predicted_carrier_cost
    )

    order.pricing_version = (
        snapshot.model_version_name
        + "|"
        + decision.policy_version
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
        "delivery_market_finalized",
        {
            "selected_bid_id":
                selected_bid.id,

            "carrier_cost":
                decision.carrier_cost,

            "model_customer_price":
                decision.storedash_model_price,

            "customer_delivery_fee":
                decision.customer_delivery_fee,

            "storedash_margin":
                decision.storedash_margin_rate,

            "pricing_mode":
                decision.pricing_mode,

            "market_min":
                summary.minimum_bid,

            "market_median":
                summary.median_bid,
        },
    )


    db.commit()


    return {
        "message":
            "Final customer price generated.",

        "snapshot":
            serialize_snapshot(
                snapshot
            ),

        "order": {
            "id":
                order.id,

            "goods_total":
                float(
                    order.goods_total
                ),

            "delivery_fee":
                float(
                    order.delivery_fee
                ),

            "service_fee":
                float(
                    order.service_fee
                ),

            "tax_total":
                float(
                    order.tax_total
                ),

            "final_total":
                float(
                    order.final_total
                ),

            "status":
                order.status.value,
        },
    }


@router.post(
    "/{order_id}/delivery-market/customer-decision"
)
def record_customer_decision(
    order_id: int,
    payload: CustomerDecision,
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


    snapshot = latest_snapshot(
        db,
        order_id,
    )


    if (
        not snapshot
        or
        snapshot.status
        != "customer_quote_ready"
    ):

        raise HTTPException(
            status_code=409,
            detail=(
                "There is no final "
                "customer quote awaiting decision."
            ),
        )


    now = ghana_now()


    snapshot.customer_decision = (
        payload.decision
    )

    snapshot.customer_decision_at = (
        now
    )


    if (
        payload.decision
        == "accepted"
    ):

        snapshot.status = (
            "customer_accepted"
        )

        order.customer_approved_at = (
            now
        )

        order.status = (
            OrderStatus.QUOTE_READY
        )


    else:

        snapshot.status = (
            "customer_declined"
        )

        order.customer_approved_at = (
            None
        )

        # No haggling / negotiation.
        # The declined quote becomes a permanent data point.
        order.status = (
            OrderStatus.CANCELLED
        )


    audit(
        db,
        order,
        "customer_delivery_quote_decision",
        {
            "decision":
                payload.decision,

            "delivery_fee":
                float(
                    order.delivery_fee
                ),

            "final_total":
                float(
                    order.final_total
                ),
        },
    )


    db.commit()


    return {
        "decision":
            payload.decision,

        "order_status":
            order.status.value,

        "snapshot":
            serialize_snapshot(
                snapshot
            ),
    }


@router.post(
    "/{order_id}/delivery-market/outcome"
)
def record_delivery_outcome(
    order_id: int,
    payload: DeliveryOutcome,
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


    snapshot = latest_snapshot(
        db,
        order_id,
    )


    if not snapshot:

        raise HTTPException(
            status_code=404,
            detail=(
                "Delivery pricing snapshot "
                "not found."
            ),
        )


    if (
        payload.actual_carrier_cost
        is not None
    ):

        snapshot.actual_carrier_cost = (
            payload.actual_carrier_cost
        )


    if (
        payload.actual_delivery_minutes
        is not None
    ):

        snapshot.actual_delivery_minutes = (
            payload.actual_delivery_minutes
        )


    if payload.notes is not None:

        snapshot.outcome_notes = (
            payload.notes
        )


    audit(
        db,
        order,
        "delivery_market_outcome_recorded",
        {
            "actual_carrier_cost":
                str(
                    payload.actual_carrier_cost
                )
                if payload.actual_carrier_cost
                is not None
                else None,

            "actual_delivery_minutes":
                payload.actual_delivery_minutes,
        },
    )


    db.commit()


    return serialize_snapshot(
        snapshot
    )
