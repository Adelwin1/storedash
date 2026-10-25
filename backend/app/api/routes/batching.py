from __future__ import annotations

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
)

from pydantic import (
    BaseModel,
    Field,
)

from sqlalchemy.orm import Session

from app.core.db import get_db

from app.services.batch_db_adapter import (
    load_dispatchable_orders,
)

from app.services.batch_recommender import (
    recommend_batch_for_driver,
)


from app.services.batch_preview import (
    preview_selected_batch,
)


router = APIRouter(
    prefix="/batching",
    tags=["batching"],
)


class BatchPreviewRequest(BaseModel):

    driver_id: int

    driver_vehicle_id: int | None = None

    order_ids: list[int] = Field(
        min_length=1,
        max_length=12,
    )

    duration_multiplier: float = Field(
        default=1.0,
        ge=0.5,
        le=3.0,
    )

    max_total_route_minutes: float | None = Field(
            default=None,
            ge=15,
            le=720,
        )


class BatchRecommendationRequest(BaseModel):
    driver_id: int

    driver_vehicle_id: int | None = None

    max_orders: int = Field(
        default=8,
        ge=1,
        le=12,
    )

    candidate_limit: int = Field(
        default=12,
        ge=1,
        le=20,
    )

    # Leave at 1.0 while using non-live OSRM.
    # Later this can be replaced by traffic-aware routing
    # and/or StoreDash's learned travel-time calibration.
    duration_multiplier: float = Field(
        default=1.0,
        ge=0.5,
        le=3.0,
    )

    max_total_route_minutes: float | None = Field(
        default=None,
        ge=15,
        le=720,
    )


@router.get(
    "/pool"
)
def dispatch_pool(
    db: Session = Depends(
        get_db
    ),
):
    orders = (
        load_dispatchable_orders(
            db
        )
    )

    return {
        "count":
            len(orders),

        "order_ids":
            [
                order.id
                for order in orders
            ],

        "status":
            "ready_for_dispatch",
    }


@router.post(
    "/preview"
)
def preview_batch(
    payload: BatchPreviewRequest,

    db: Session = Depends(
        get_db
    ),
):

    try:

        return (
            preview_selected_batch(
                db,

                driver_id=
                    payload.driver_id,

                driver_vehicle_id=
                    payload.driver_vehicle_id,

                order_ids=
                    payload.order_ids,

                duration_multiplier=
                    payload.duration_multiplier,

                max_total_route_minutes=
                    payload.max_total_route_minutes,
            )
        )


    except ValueError as exc:

        raise HTTPException(
            status_code=409,
            detail=str(exc),
        ) from exc


@router.post(
    "/recommend"
)
def recommend_batch(
    payload: BatchRecommendationRequest,
    db: Session = Depends(
        get_db
    ),
):
    try:
        return (
            recommend_batch_for_driver(
                db,

                driver_id=
                    payload.driver_id,

                driver_vehicle_id=
                    payload.driver_vehicle_id,

                max_orders=
                    payload.max_orders,

                candidate_limit=
                    payload.candidate_limit,

                duration_multiplier=
                    payload.duration_multiplier,

                max_total_route_minutes=
                    payload.max_total_route_minutes,
            )
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=409,
            detail=str(exc),
        ) from exc


# ============================================================
# BATCH MATERIALIZATION + DRIVER ASSIGNMENT
# ============================================================

from app.services.batch_dispatch import (
    accept_batch_driver_offer,
    create_batch_driver_offer,
    create_proposed_batch,
    decline_batch_driver_offer,
)


class MaterializeBatchRequest(BaseModel):
    driver_id: int

    driver_vehicle_id: int | None = None

    order_ids: list[int] = Field(
        min_length=1,
    )

    duration_multiplier: float = Field(
        default=1.0,
        ge=0.5,
        le=3.0,
    )

    max_total_route_minutes: float | None = Field(
        default=None,
        ge=15,
        le=720,
    )


class BatchDriverOfferRequest(BaseModel):
    opening_offer: float | None = Field(
        default=None,
        gt=0,
    )

    maximum_authorized_payout: float | None = Field(
        default=None,
        gt=0,
    )

    operator_id: int | None = None

    notes: str | None = None


class BatchDriverAcceptRequest(BaseModel):
    final_payout: float | None = Field(
        default=None,
        gt=0,
    )


@router.post(
    "/materialize"
)
def materialize_batch(
    payload: MaterializeBatchRequest,
    db: Session = Depends(
        get_db
    ),
):
    try:
        batch = (
            create_proposed_batch(
                db,

                driver_id=
                    payload.driver_id,

                driver_vehicle_id=
                    payload.driver_vehicle_id,

                order_ids=
                    payload.order_ids,

                duration_multiplier=
                    payload.duration_multiplier,

                max_total_route_minutes=
                    payload.max_total_route_minutes,
            )
        )

        return {
            "batch_id":
                batch.id,

            "status":
                batch.status,

            "driver_id":
                batch.driver_id,

            "driver_vehicle_id":
                batch.driver_vehicle_id,

            "order_count":
                batch.order_count,

            "pickup_count":
                batch.pickup_count,

            "delivery_count":
                batch.delivery_count,

            "planned_distance_km":
                batch.planned_distance_km,

            "planned_minutes":
                batch.planned_minutes,

            "peak_weight_kg":
                batch.peak_weight_kg,

            "peak_volume_l":
                batch.peak_volume_l,

            "customer_delivery_revenue":
                float(
                    batch.customer_delivery_revenue
                ),

            "predicted_driver_payout":
                (
                    float(
                        batch.predicted_driver_payout
                    )
                    if batch.predicted_driver_payout
                    is not None
                    else None
                ),

            "predicted_contribution":
                (
                    float(
                        batch.predicted_contribution
                    )
                    if batch.predicted_contribution
                    is not None
                    else None
                ),

            "predicted_margin_rate":
                batch.predicted_margin_rate,
        }

    except ValueError as exc:
        raise HTTPException(
            status_code=409,
            detail=str(exc),
        ) from exc


@router.post(
    "/{batch_id}/driver-offers"
)
def create_driver_offer(
    batch_id: int,

    payload: BatchDriverOfferRequest,

    db: Session = Depends(
        get_db
    ),
):
    try:
        offer = (
            create_batch_driver_offer(
                db,

                batch_id=
                    batch_id,

                opening_offer=
                    payload.opening_offer,

                maximum_authorized_payout=
                    payload.maximum_authorized_payout,

                operator_id=
                    payload.operator_id,

                notes=
                    payload.notes,
            )
        )

        return {
            "offer_id":
                offer.id,

            "batch_id":
                offer.batch_id,

            "driver_id":
                offer.driver_id,

            "opening_offer":
                float(
                    offer.opening_offer
                ),

            "recommended_payout":
                (
                    float(
                        offer.recommended_payout
                    )
                    if offer.recommended_payout
                    is not None
                    else None
                ),

            "maximum_authorized_payout":
                (
                    float(
                        offer.maximum_authorized_payout
                    )
                    if offer.maximum_authorized_payout
                    is not None
                    else None
                ),

            "outcome":
                offer.outcome,
        }

    except ValueError as exc:
        raise HTTPException(
            status_code=409,
            detail=str(exc),
        ) from exc



@router.post(
    "/{batch_id}/driver-offers/{offer_id}/decline"
)
def decline_driver_offer(
    batch_id: int,
    offer_id: int,
    db: Session = Depends(
        get_db
    ),
):
    try:
        offer = decline_batch_driver_offer(
            db,
            batch_id=batch_id,
            offer_id=offer_id,
            notes="Driver declined route.",
        )

        return {
            "offer_id":
                offer.id,

            "batch_id":
                offer.batch_id,

            "driver_id":
                offer.driver_id,

            "outcome":
                offer.outcome,
        }

    except ValueError as exc:
        raise HTTPException(
            status_code=409,
            detail=str(exc),
        ) from exc


@router.post(
    "/{batch_id}/driver-offers/{offer_id}/accept"
)
def accept_driver_offer(
    batch_id: int,
    offer_id: int,

    payload: BatchDriverAcceptRequest,

    db: Session = Depends(
        get_db
    ),
):
    try:
        batch = (
            accept_batch_driver_offer(
                db,

                batch_id=
                    batch_id,

                offer_id=
                    offer_id,

                final_payout=
                    payload.final_payout,
            )
        )

        return {
            "batch_id":
                batch.id,

            "status":
                batch.status,

            "driver_id":
                batch.driver_id,

            "accepted_driver_payout":
                float(
                    batch.accepted_driver_payout
                ),

            "customer_delivery_revenue":
                float(
                    batch.customer_delivery_revenue
                ),

            "predicted_contribution":
                float(
                    batch.predicted_contribution
                ),

            "predicted_margin_rate":
                float(
                    batch.predicted_margin_rate
                ),
        }

    except ValueError as exc:
        raise HTTPException(
            status_code=409,
            detail=str(exc),
        ) from exc
