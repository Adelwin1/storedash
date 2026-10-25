from datetime import datetime

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
)

from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.db import get_db

from app.models import (
    LogisticsCategory,
    LogisticsType,
    ProductKnowledge,
)


router = APIRouter(
    prefix="/logistics",
    tags=["logistics"],
)


def normalize(value: str) -> str:
    return " ".join(
        value.strip().casefold().split()
    )


class CategoryRead(BaseModel):
    id: int
    code: str
    name: str

    fallback_small_units: float
    fallback_medium_units: float
    fallback_large_units: float


class LogisticsTypeRead(BaseModel):
    id: int
    category_id: int

    name: str
    package_type: str
    load_units: float


class ResolveResult(BaseModel):
    product_name: str

    category_id: int
    category_code: str
    category_name: str

    logistics_type_id: int | None
    logistics_type_name: str | None

    package_type: str | None

    size_class: str

    load_units_each: float

    resolution_source: str

    learned_product: bool


class LearnProductRequest(BaseModel):
    product_name: str

    category_id: int

    logistics_type_id: int | None = None

    size_class: str = "medium"


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


@router.get(
    "/categories",
    response_model=list[CategoryRead],
)
def categories(
    db: Session = Depends(get_db),
):
    return db.scalars(
        select(
            LogisticsCategory
        )
        .where(
            LogisticsCategory.is_active
            == True
        )
        .order_by(
            LogisticsCategory.name
        )
    ).all()


@router.get(
    "/types",
    response_model=list[LogisticsTypeRead],
)
def logistics_types(
    category_id: int = Query(...),
    db: Session = Depends(get_db),
):
    return db.scalars(
        select(
            LogisticsType
        )
        .where(
            LogisticsType.category_id
            == category_id,

            LogisticsType.is_active
            == True,
        )
        .order_by(
            LogisticsType.name
        )
    ).all()


@router.get(
    "/resolve",
    response_model=ResolveResult,
)
def resolve_product(
    product_name: str,

    category_id: int | None = None,

    logistics_type_id: int | None = None,

    size_class: str = "medium",

    db: Session = Depends(get_db),
):
    size_class = (
        size_class.strip().lower()
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


    normalized = normalize(
        product_name
    )


    learned = db.scalars(
        select(
            ProductKnowledge
        ).where(
            ProductKnowledge.normalized_name
            == normalized
        )
    ).first()


    if learned:
        category = db.get(
            LogisticsCategory,
            learned.category_id,
        )


        if not category:
            raise HTTPException(
                status_code=500,
                detail=(
                    "Stored product has an invalid "
                    "logistics category."
                ),
            )


        logistics_type = (
            db.get(
                LogisticsType,
                learned.logistics_type_id,
            )
            if learned.logistics_type_id
            else None
        )


        learned.times_seen += 1

        learned.last_seen_at = (
            datetime.utcnow()
        )

        db.commit()


        chosen_size = (
            learned.size_class
            or size_class
        )


        if logistics_type:
            return ResolveResult(
                product_name=product_name,

                category_id=category.id,

                category_code=category.code,

                category_name=category.name,

                logistics_type_id=(
                    logistics_type.id
                ),

                logistics_type_name=(
                    logistics_type.name
                ),

                package_type=(
                    logistics_type.package_type
                ),

                size_class=chosen_size,

                load_units_each=float(
                    logistics_type.load_units
                ),

                resolution_source=(
                    "learned_exact_type"
                ),

                learned_product=True,
            )


        return ResolveResult(
            product_name=product_name,

            category_id=category.id,

            category_code=category.code,

            category_name=category.name,

            logistics_type_id=None,

            logistics_type_name=None,

            package_type=None,

            size_class=chosen_size,

            load_units_each=(
                fallback_units(
                    category,
                    chosen_size,
                )
            ),

            resolution_source=(
                "learned_category_fallback"
            ),

            learned_product=True,
        )


    if logistics_type_id:
        logistics_type = db.get(
            LogisticsType,
            logistics_type_id,
        )


        if not logistics_type:
            raise HTTPException(
                status_code=404,
                detail=(
                    "Logistics type not found."
                ),
            )


        category = db.get(
            LogisticsCategory,
            logistics_type.category_id,
        )


        if not category:
            raise HTTPException(
                status_code=500,
                detail=(
                    "Logistics type has no "
                    "valid category."
                ),
            )


        return ResolveResult(
            product_name=product_name,

            category_id=category.id,

            category_code=category.code,

            category_name=category.name,

            logistics_type_id=(
                logistics_type.id
            ),

            logistics_type_name=(
                logistics_type.name
            ),

            package_type=(
                logistics_type.package_type
            ),

            size_class=size_class,

            load_units_each=float(
                logistics_type.load_units
            ),

            resolution_source=(
                "selected_exact_type"
            ),

            learned_product=False,
        )


    if category_id:
        category = db.get(
            LogisticsCategory,
            category_id,
        )


        if not category:
            raise HTTPException(
                status_code=404,
                detail=(
                    "Logistics category not found."
                ),
            )


        return ResolveResult(
            product_name=product_name,

            category_id=category.id,

            category_code=category.code,

            category_name=category.name,

            logistics_type_id=None,

            logistics_type_name=None,

            package_type=None,

            size_class=size_class,

            load_units_each=(
                fallback_units(
                    category,
                    size_class,
                )
            ),

            resolution_source=(
                "category_fallback"
            ),

            learned_product=False,
        )


    general = db.scalars(
        select(
            LogisticsCategory
        ).where(
            LogisticsCategory.code
            == "general_goods"
        )
    ).first()


    if not general:
        raise HTTPException(
            status_code=500,
            detail=(
                "General logistics category "
                "has not been configured."
            ),
        )


    return ResolveResult(
        product_name=product_name,

        category_id=general.id,

        category_code=general.code,

        category_name=general.name,

        logistics_type_id=None,

        logistics_type_name=None,

        package_type=None,

        size_class="medium",

        load_units_each=float(
            general.fallback_medium_units
        ),

        resolution_source=(
            "general_medium_fallback"
        ),

        learned_product=False,
    )


@router.post(
    "/learn-product",
    response_model=ResolveResult,
)
def learn_product(
    payload: LearnProductRequest,

    db: Session = Depends(get_db),
):
    size_class = (
        payload.size_class.strip().lower()
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
            detail=(
                "Logistics category not found."
            ),
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
                detail=(
                    "Logistics type not found."
                ),
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


    normalized = normalize(
        payload.product_name
    )


    knowledge = db.scalars(
        select(
            ProductKnowledge
        ).where(
            ProductKnowledge.normalized_name
            == normalized
        )
    ).first()


    if not knowledge:
        knowledge = ProductKnowledge(
            normalized_name=normalized,

            display_name=(
                payload.product_name.strip()
            ),

            category_id=category.id,

            logistics_type_id=(
                logistics_type.id
                if logistics_type
                else None
            ),

            size_class=size_class,

            source="operator",

            times_seen=1,

            confidence=0.6,
        )

        db.add(
            knowledge
        )

    else:
        knowledge.category_id = (
            category.id
        )

        knowledge.logistics_type_id = (
            logistics_type.id
            if logistics_type
            else None
        )

        knowledge.size_class = (
            size_class
        )

        knowledge.times_seen += 1

        knowledge.confidence = min(
            1.0,
            knowledge.confidence
            + 0.05,
        )

        knowledge.last_seen_at = (
            datetime.utcnow()
        )


    db.commit()


    if logistics_type:
        units = float(
            logistics_type.load_units
        )

        source = (
            "learned_exact_type"
        )

        package_type = (
            logistics_type.package_type
        )

        type_name = (
            logistics_type.name
        )

        type_id = (
            logistics_type.id
        )

    else:
        units = fallback_units(
            category,
            size_class,
        )

        source = (
            "learned_category_fallback"
        )

        package_type = None
        type_name = None
        type_id = None


    return ResolveResult(
        product_name=(
            payload.product_name
        ),

        category_id=category.id,

        category_code=category.code,

        category_name=category.name,

        logistics_type_id=type_id,

        logistics_type_name=type_name,

        package_type=package_type,

        size_class=size_class,

        load_units_each=units,

        resolution_source=source,

        learned_product=True,
    )


# ============================================================
# DEEP LOGISTICS VARIANTS
# ============================================================

from app.services.logistics_variants import (
    get_variants,
)

from app.services.cargo_estimator import (
    estimate_cargo_profile,
)


class LogisticsVariantRead(BaseModel):
    key: str
    label: str

    physical_size_text: str
    size_class: str


class CargoEstimateRequest(BaseModel):
    product_name: str

    category_id: int
    logistics_type_id: int

    size_class: str = "medium"

    physical_size_text: str | None = None


class CargoEstimateRead(BaseModel):
    profile_version: str

    category_code: str
    material_class: str

    package_type: str
    size_class: str

    weight_kg_each: float
    volume_l_each: float

    handling_score_each: float
    fragility_score_each: float

    load_units_each: float

    confidence: float

    estimation_source: str

    explicit_mass_found: bool
    explicit_volume_found: bool
    multipack_found: bool


@router.get(
    "/variants",
    response_model=list[
        LogisticsVariantRead
    ],
)
def logistics_variants(
    category_id: int = Query(...),

    logistics_type_id: int = Query(...),

    db: Session = Depends(get_db),
):
    category = db.get(
        LogisticsCategory,
        category_id,
    )

    if not category:
        raise HTTPException(
            status_code=404,
            detail=(
                "Logistics category not found."
            ),
        )


    logistics_type = db.get(
        LogisticsType,
        logistics_type_id,
    )

    if not logistics_type:
        raise HTTPException(
            status_code=404,
            detail=(
                "Logistics type not found."
            ),
        )


    if (
        logistics_type.category_id
        != category.id
    ):
        raise HTTPException(
            status_code=409,
            detail=(
                "Logistics type does not "
                "belong to category."
            ),
        )


    return get_variants(
        category.code,
        logistics_type.package_type,
    )


@router.post(
    "/estimate",
    response_model=CargoEstimateRead,
)
def estimate_logistics(
    payload: CargoEstimateRequest,

    db: Session = Depends(get_db),
):
    category = db.get(
        LogisticsCategory,
        payload.category_id,
    )

    if not category:
        raise HTTPException(
            status_code=404,
            detail=(
                "Logistics category not found."
            ),
        )


    logistics_type = db.get(
        LogisticsType,
        payload.logistics_type_id,
    )

    if not logistics_type:
        raise HTTPException(
            status_code=404,
            detail=(
                "Logistics type not found."
            ),
        )


    if (
        logistics_type.category_id
        != category.id
    ):
        raise HTTPException(
            status_code=409,
            detail=(
                "Selected package does not "
                "belong to category."
            ),
        )


    return estimate_cargo_profile(
        product_name=
            payload.product_name,

        category_code=
            category.code,

        package_type=
            logistics_type.package_type,

        type_name=
            logistics_type.name,

        size_class=
            payload.size_class,

        size_text=
            payload.physical_size_text,
    )
