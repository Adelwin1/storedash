from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
)

from pydantic import BaseModel

from sqlalchemy import select

from sqlalchemy.orm import (
    Session,
    selectinload,
)

from app.core.db import get_db

from app.models import (
    LogisticsCategory,
    LogisticsType,
    Order,
    OrderStatus,
)

from app.schemas.order import OrderRead

from app.services.cargo_estimator import estimate_cargo_profile

from app.services.physical_logistics import estimate_physical_profile


router = APIRouter(
    prefix="/orders",
    tags=["order-logistics"],
)


EDITABLE_STATUSES = {
    OrderStatus.DRAFT,
    OrderStatus.SOURCING,
    OrderStatus.QUOTE_READY,
    OrderStatus.AWAITING_BUYER_APPROVAL,
}


class ItemLogisticsUpdate(BaseModel):
    category_id: int

    logistics_type_id: int | None = None

    size_class: str = "medium"

    variant_key: str | None = None

    physical_size_text: str | None = None


def load_order(
    db: Session,
    order_id: int,
):
    return db.scalars(
        select(Order)
        .options(
            selectinload(Order.items)
        )
        .where(
            Order.id == order_id
        )
    ).first()


def fallback_units(
    category: LogisticsCategory,
    size_class: str,
) -> float:
    if size_class == "small":
        return float(
            category.fallback_small_units
        )

    if size_class == "large":
        return float(
            category.fallback_large_units
        )

    return float(
        category.fallback_medium_units
    )


@router.put(
    "/{order_id}/items/{item_id}/logistics",
    response_model=OrderRead,
)
def update_item_logistics(
    order_id: int,
    item_id: int,
    payload: ItemLogisticsUpdate,
    db: Session = Depends(get_db),
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

    if order.status not in EDITABLE_STATUSES:
        raise HTTPException(
            status_code=409,
            detail="Finalized orders are locked.",
        )

    item = next(
        (
            current
            for current in order.items
            if current.id == item_id
        ),
        None,
    )

    if not item:
        raise HTTPException(
            status_code=404,
            detail="Order item not found.",
        )

    # Capture the persisted classification before applying
    # this request. Autosave can legitimately resend identical
    # values, and an identical save must NOT invalidate a quote.
    logistics_before = (
        item.logistics_category_id,
        item.logistics_type_id,
        (
            item.logistics_size_class
            or ""
        ).strip().lower(),
        item.logistics_variant_key
        or None,
        item.logistics_size_detail
        or None,
    )


    size_class = (
        payload.size_class
        .strip()
        .lower()
    )

    if size_class not in {
        "small",
        "medium",
        "large",
    }:
        raise HTTPException(
            status_code=400,
            detail=(
                "size_class must be "
                "small, medium or large."
            ),
        )

    category = db.get(
        LogisticsCategory,
        payload.category_id,
    )

    if not category:
        raise HTTPException(
            status_code=404,
            detail="Logistics category not found.",
        )

    logistics_type = None

    if payload.logistics_type_id:
        logistics_type = db.get(
            LogisticsType,
            payload.logistics_type_id,
        )

        if not logistics_type:
            raise HTTPException(
                status_code=404,
                detail="Logistics type not found.",
            )

        if (
            logistics_type.category_id
            != category.id
        ):
            raise HTTPException(
                status_code=409,
                detail=(
                    "Selected logistics type "
                    "does not belong to category."
                ),
            )

    if logistics_type:
        units_each = float(
            logistics_type.load_units
        )
    else:
        units_each = fallback_units(
            category,
            size_class,
        )

    quantity = float(
        item.confirmed_quantity
        or item.requested_quantity
        or 0
    )


    package_type = (
        logistics_type.package_type
        if logistics_type
        else (
            item.unit
            if item.unit != "unit"
            else None
        )
    )

    profile = estimate_physical_profile(
        category_code=category.code,
        package_type=package_type,
        size_class=size_class,
        load_units=units_each,

        weight_kg_each=(
            float(logistics_type.weight_kg_each)
            if (
                logistics_type
                and logistics_type.weight_kg_each
                is not None
            )
            else None
        ),

        volume_l_each=(
            float(logistics_type.volume_l_each)
            if (
                logistics_type
                and logistics_type.volume_l_each
                is not None
            )
            else None
        ),

        handling_score_each=(
            float(logistics_type.handling_score_each)
            if (
                logistics_type
                and logistics_type.handling_score_each
                is not None
            )
            else None
        ),

        fragility_score_each=(
            float(logistics_type.fragility_score_each)
            if (
                logistics_type
                and logistics_type.fragility_score_each
                is not None
            )
            else None
        ),
    )

    item.logistics_category_id = (
        category.id
    )

    item.logistics_type_id = (
        logistics_type.id
        if logistics_type
        else None
    )

    item.logistics_size_class = (
        size_class
    )

    item.load_units_each = (
        units_each
    )

    item.total_load_units = (
        round(
            units_each * quantity,
            2,
        )
    )


    item.logistics_package_type = (
        package_type
    )

    item.weight_kg_each = (
        profile["weight_kg_each"]
    )

    item.volume_l_each = (
        profile["volume_l_each"]
    )

    item.handling_score_each = (
        profile["handling_score_each"]
    )

    item.fragility_score_each = (
        profile["fragility_score_each"]
    )

    item.total_weight_kg = round(
        profile["weight_kg_each"]
        * quantity,
        3,
    )

    item.total_volume_l = round(
        profile["volume_l_each"]
        * quantity,
        3,
    )

    item.total_handling_score = round(
        profile["handling_score_each"]
        * quantity,
        3,
    )

    item.total_fragility_score = round(
        profile["fragility_score_each"]
        * quantity,
        3,
    )

    item.physical_profile_version = (
        profile["version"]
    )

    # ========================================================
    # DEEP CARGO ESTIMATOR V2
    #
    # Old logistics_type.load_units values remain useful
    # as legacy catalog data, but the ORDER ITEM now gets
    # a continuous physical estimate from:
    #
    # category + material + package + size +
    # explicit kg/g/L/ml + multipack information.
    # ========================================================

    cargo = estimate_cargo_profile(
        product_name=
            item.name,

        brand=
            item.brand,

        size_text=(
            payload.physical_size_text
            or item.size
        ),

        category_code=
            category.code,

        package_type=(
            logistics_type.package_type
            if logistics_type
            else None
        ),

        type_name=(
            logistics_type.name
            if logistics_type
            else None
        ),

        size_class=
            size_class,
    )


    item.logistics_package_type = (
        cargo[
            "package_type"
        ]
    )


    item.weight_kg_each = (
        cargo[
            "weight_kg_each"
        ]
    )

    item.volume_l_each = (
        cargo[
            "volume_l_each"
        ]
    )

    item.handling_score_each = (
        cargo[
            "handling_score_each"
        ]
    )

    item.fragility_score_each = (
        cargo[
            "fragility_score_each"
        ]
    )


    # Dynamic load score replaces crude per-package
    # constants at the item level.
    item.load_units_each = (
        cargo[
            "load_units_each"
        ]
    )


    item.total_load_units = round(
        item.load_units_each
        * quantity,
        2,
    )


    item.total_weight_kg = round(
        item.weight_kg_each
        * quantity,
        3,
    )

    item.total_volume_l = round(
        item.volume_l_each
        * quantity,
        3,
    )

    item.total_handling_score = round(
        item.handling_score_each
        * quantity,
        3,
    )

    item.total_fragility_score = round(
        item.fragility_score_each
        * quantity,
        3,
    )


    item.physical_profile_version = (
        cargo[
            "profile_version"
        ]
    )


    item.logistics_variant_key = (
        payload.variant_key
    )

    item.logistics_size_detail = (
        payload.physical_size_text
    )

    item.physical_material_class = (
        cargo[
            "material_class"
        ]
    )

    item.physical_estimation_source = (
        cargo[
            "estimation_source"
        ]
    )

    item.physical_confidence = (
        cargo[
            "confidence"
        ]
    )


    # ========================================================
    # AUTOSAVE QUOTE INVALIDATION
    #
    # Autosave may resend the exact same classification after a
    # render/refresh. That must not destroy a valid quote.
    #
    # Only a material operator change invalidates pricing.
    # ========================================================

    logistics_after = (
        item.logistics_category_id,
        item.logistics_type_id,
        (
            item.logistics_size_class
            or ""
        ).strip().lower(),
        item.logistics_variant_key
        or None,
        item.logistics_size_detail
        or None,
    )


    if (
        logistics_after
        !=
        logistics_before
    ):

        order.quote_generated_at = None
        order.customer_approved_at = None

        order.goods_total = 0
        order.delivery_fee = 0
        order.service_fee = 0
        order.tax_total = 0
        order.final_total = 0

        order.driver_floor = None
        order.driver_target = None
        order.driver_ceiling = None

        order.estimated_driver_market_cost = None
        order.estimated_customer_willingness = None

        order.driver_acceptance_probability = None
        order.customer_acceptance_probability = None

        order.delivery_margin = None
        order.optimizer_score = None
        order.pricing_version = None

        if (
            getattr(
                order.status,
                "value",
                order.status,
            )
            ==
            "awaiting_buyer_approval"
        ):
            order.status = (
                type(order.status).SOURCING
            )


    db.commit()

    return load_order(
        db,
        order.id,
    )


@router.get(
    "/{order_id}/load-summary",
)
def load_summary(
    order_id: int,
    db: Session = Depends(get_db),
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

    deliverable_items = [
        item
        for item in order.items
        if item.availability_status
        in {
            "available",
            "partial",
        }
    ]


    total = sum(
        float(
            item.total_load_units
            or 0
        )
        for item in deliverable_items
    )


    unclassified = [
        item.name
        for item in deliverable_items
        if item.total_load_units is None
    ]

    if total <= 5:
        load_class = "light"

    elif total <= 15:
        load_class = "small"

    elif total <= 30:
        load_class = "medium"

    elif total <= 60:
        load_class = "large"

    else:
        load_class = "heavy"

    return {
        "order_id": order.id,
        "total_load_units": round(
            total,
            2,
        ),
        "load_class": load_class,
        "unclassified_items": (
            unclassified
        ),
        "classification_complete": (
            len(unclassified) == 0
        ),
    }
