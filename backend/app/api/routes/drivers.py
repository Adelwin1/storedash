from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
)

from pydantic import (
    BaseModel,
    Field,
)

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.db import get_db

from app.models import Driver

from app.models.entities import (
    DriverVehicle,
    VehicleSpec,
)

from app.schemas.driver import (
    DriverCreate,
    DriverRead,
    DriverUpdate,
)


class DriverRoutingProfileRequest(
    BaseModel
):

    manufacturer: str = Field(
        min_length=1,
        max_length=120,
    )

    model: str = Field(
        min_length=1,
        max_length=160,
    )

    variant: str | None = Field(
        default=None,
        max_length=160,
    )

    max_payload_kg: float = Field(
        gt=0,
    )

    cargo_volume_l: float = Field(
        gt=0,
    )

    reference_km_per_liter: float | None = Field(
        default=None,
        gt=0,
    )

    fuel_type: str | None = Field(
        default=None,
        max_length=40,
    )

    registration: str | None = Field(
        default=None,
        max_length=80,
    )

    safe_capacity_ratio: float = Field(
        default=0.90,
        gt=0,
        le=1.0,
    )

    current_latitude: float = Field(
        ge=-90,
        le=90,
    )

    current_longitude: float = Field(
        ge=-180,
        le=180,
    )

    current_area: str | None = Field(
        default=None,
        max_length=160,
    )


class DriverOnboardRequest(
    BaseModel
):

    driver: DriverCreate

    routing: DriverRoutingProfileRequest


router = APIRouter(
    prefix="/drivers",
    tags=["drivers"],
)


@router.post(
    "",
    status_code=status.HTTP_409_CONFLICT,
)
def create_driver(
    payload: DriverCreate,
    db: Session = Depends(get_db),
):
    raise HTTPException(
        status_code=409,
        detail=(
            "Bare driver creation is disabled. "
            "Use /api/drivers/onboard so every new "
            "driver receives a complete routing profile."
        ),
    )


def legacy_create_driver_disabled(
    payload: DriverCreate,
    db: Session = Depends(get_db),
):
    driver = Driver(
        **payload.model_dump()
    )

    db.add(driver)

    try:
        db.commit()

    except IntegrityError:
        db.rollback()

        raise HTTPException(
            status_code=409,
            detail=(
                "A driver with this phone number "
                "already exists."
            ),
        )

    db.refresh(driver)

    return driver


@router.get(
    "",
    response_model=list[DriverRead],
)
def list_drivers(
    available_only: bool = False,
    active_only: bool = True,
    db: Session = Depends(get_db),
):
    stmt = (
        select(Driver)
        .order_by(
            Driver.is_available.desc(),
            Driver.name,
        )
    )

    if available_only:
        stmt = stmt.where(
            Driver.is_available.is_(True)
        )

    if active_only:
        stmt = stmt.where(
            Driver.is_active.is_(True)
        )

    return db.scalars(
        stmt
    ).all()


@router.get(
    "/routing-status",
)
def driver_routing_status(
    db: Session = Depends(get_db),
):
    drivers = db.scalars(
        select(Driver)
        .order_by(
            Driver.is_available.desc(),
            Driver.name,
        )
    ).all()


    vehicles = db.scalars(
        select(DriverVehicle)
        .where(
            DriverVehicle.is_active.is_(True)
        )
        .order_by(
            DriverVehicle.id.desc()
        )
    ).all()


    vehicle_by_driver = {}

    for vehicle in vehicles:
        if (
            vehicle.driver_id
            not in vehicle_by_driver
        ):
            vehicle_by_driver[
                vehicle.driver_id
            ] = vehicle


    results = []

    for driver in drivers:
        vehicle = vehicle_by_driver.get(
            driver.id
        )

        profile_complete = (
            vehicle is not None
            and vehicle.vehicle_spec_id
                is not None
        )

        if not driver.is_active:
            reason = "Driver inactive."

        elif not profile_complete:
            reason = (
                "Routing profile incomplete. "
                "Vehicle capacity/specification "
                "has not been configured."
            )

        elif not driver.is_available:
            reason = (
                "Driver is currently busy."
            )

        else:
            reason = None


        results.append({
            "driver_id":
                driver.id,

            "driver_name":
                driver.name,

            "is_active":
                driver.is_active,

            "is_available":
                driver.is_available,

            "routing_profile_complete":
                profile_complete,

            "driver_vehicle_id":
                (
                    vehicle.id
                    if vehicle
                    else None
                ),

            "vehicle_spec_id":
                (
                    vehicle.vehicle_spec_id
                    if vehicle
                    else None
                ),

            "registration":
                (
                    vehicle.registration
                    if vehicle
                    else driver.vehicle_registration
                ),

            "reason":
                reason,
        })


    return results


@router.post(
    "/onboard",
    status_code=status.HTTP_201_CREATED,
)
def onboard_driver(
    payload: DriverOnboardRequest,

    db: Session = Depends(
        get_db
    ),
):
    """
    Creates the Driver + routing vehicle profile
    as one onboarding operation.

    A new rider is not considered successfully
    created by this endpoint unless the routing
    profile is also created successfully.
    """

    driver = Driver(
        **payload.driver.model_dump()
    )

    db.add(
        driver
    )


    try:

        # Allocate driver.id but DO NOT commit yet.
        db.flush()


        routing = (
            configure_driver_routing_profile(
                driver.id,
                payload.routing,
                db,
            )
        )


    except IntegrityError as exc:

        db.rollback()

        raise HTTPException(
            status_code=409,
            detail=(
                "Could not onboard driver. "
                "The phone number may already exist."
            ),
        ) from exc


    except HTTPException:

        # If routing setup failed before its commit,
        # remove the newly flushed driver too.
        db.rollback()

        raise


    except Exception:

        db.rollback()

        raise


    db.refresh(
        driver
    )


    return {
        "driver_id":
            driver.id,

        "driver_name":
            driver.name,

        "phone":
            driver.phone,

        "routing_profile_complete":
            True,

        "driver_vehicle_id":
            routing[
                "driver_vehicle_id"
            ],

        "vehicle_spec_id":
            routing[
                "vehicle_spec_id"
            ],

        "registration":
            routing[
                "registration"
            ],

        "message":
            (
                "Driver onboarded and "
                "ready for StoreDash routing."
            ),
    }


@router.post(
    "/{driver_id}/routing-profile",
)
def configure_driver_routing_profile(
    driver_id: int,

    payload: DriverRoutingProfileRequest,

    db: Session = Depends(
        get_db
    ),
):

    driver = db.get(
        Driver,
        driver_id,
    )

    if not driver:
        raise HTTPException(
            status_code=404,
            detail="Driver not found.",
        )


    manufacturer = (
        payload.manufacturer
        .strip()
    )

    model = (
        payload.model
        .strip()
    )

    variant = (
        payload.variant.strip()
        if payload.variant
        and payload.variant.strip()
        else None
    )


    # --------------------------------------------------------
    # SHARED VEHICLE SPEC CATALOG
    #
    # Reuse the same exact make/model/variant instead of
    # creating a duplicate spec for every rider.
    # --------------------------------------------------------

    spec_stmt = (
        select(
            VehicleSpec
        )
        .where(
            VehicleSpec.is_active.is_(
                True
            ),
            VehicleSpec.manufacturer
            == manufacturer,
            VehicleSpec.model
            == model,
        )
    )


    if variant is None:

        spec_stmt = (
            spec_stmt.where(
                VehicleSpec.variant.is_(
                    None
                )
            )
        )

    else:

        spec_stmt = (
            spec_stmt.where(
                VehicleSpec.variant
                == variant
            )
        )


    spec = db.scalar(
        spec_stmt
        .order_by(
            VehicleSpec.id.desc()
        )
    )


    if spec is not None:

        payload_match = (
            abs(
                float(
                    spec.max_payload_kg
                )
                -
                float(
                    payload.max_payload_kg
                )
            )
            <= 0.001
        )

        volume_match = (
            abs(
                float(
                    spec.cargo_volume_l
                )
                -
                float(
                    payload.cargo_volume_l
                )
            )
            <= 0.001
        )


        if (
            not payload_match
            or not volume_match
        ):

            raise HTTPException(
                status_code=409,
                detail=(
                    "A vehicle specification already "
                    "exists for this make/model/variant "
                    "with different payload or cargo "
                    "volume. Confirm the exact variant "
                    "instead of overwriting the shared "
                    "vehicle specification."
                ),
            )


        if (
            spec.reference_km_per_liter
            is None
            and
            payload.reference_km_per_liter
            is not None
        ):

            spec.reference_km_per_liter = (
                payload
                .reference_km_per_liter
            )


        if (
            not spec.fuel_type
            and payload.fuel_type
        ):

            spec.fuel_type = (
                payload.fuel_type
                .strip()
            )


    else:

        spec = VehicleSpec(
            manufacturer=
                manufacturer,

            model=
                model,

            variant=
                variant,

            max_payload_kg=
                float(
                    payload.max_payload_kg
                ),

            cargo_volume_l=
                float(
                    payload.cargo_volume_l
                ),

            seat_cargo_volume_l=
                0.0,

            reference_km_per_liter=
                payload
                .reference_km_per_liter,

            fuel_type=
                (
                    payload.fuel_type.strip()
                    if payload.fuel_type
                    else None
                ),

            source_name=
                (
                    "StoreDash operator-entered "
                    "driver onboarding"
                ),

            source_url=
                None,

            is_active=
                True,
        )

        db.add(
            spec
        )

        db.flush()


    # --------------------------------------------------------
    # ONE ACTIVE ROUTING VEHICLE PER DRIVER
    # --------------------------------------------------------

    active_vehicles = list(
        db.scalars(
            select(
                DriverVehicle
            )
            .where(
                DriverVehicle.driver_id
                == driver.id,

                DriverVehicle.is_active
                .is_(
                    True
                ),
            )
            .order_by(
                DriverVehicle.id.desc()
            )
        ).all()
    )


    vehicle = (
        active_vehicles[0]
        if active_vehicles
        else None
    )


    for existing in (
        active_vehicles[1:]
    ):

        existing.is_active = (
            False
        )


    registration = (
        payload.registration.strip()
        if payload.registration
        and payload.registration.strip()
        else driver.vehicle_registration
    )


    area = (
        payload.current_area.strip()
        if payload.current_area
        and payload.current_area.strip()
        else driver.current_area
    )


    if vehicle is None:

        vehicle = DriverVehicle(
            driver_id=
                driver.id,

            vehicle_spec_id=
                spec.id,

            registration=
                registration,

            is_active=
                True,

            seat_area_available_for_cargo=
                False,

            safe_capacity_ratio=
                float(
                    payload.safe_capacity_ratio
                ),

            current_latitude=
                float(
                    payload.current_latitude
                ),

            current_longitude=
                float(
                    payload.current_longitude
                ),

            current_area=
                area,

            notes=
                (
                    "Configured through StoreDash "
                    "driver onboarding."
                ),
        )

        db.add(
            vehicle
        )

    else:

        vehicle.vehicle_spec_id = (
            spec.id
        )

        vehicle.registration = (
            registration
        )

        vehicle.is_active = (
            True
        )

        vehicle.seat_area_available_for_cargo = (
            False
        )

        vehicle.safe_capacity_ratio = (
            float(
                payload.safe_capacity_ratio
            )
        )

        vehicle.current_latitude = (
            float(
                payload.current_latitude
            )
        )

        vehicle.current_longitude = (
            float(
                payload.current_longitude
            )
        )

        vehicle.current_area = (
            area
        )


    # Keep the lightweight driver record consistent too.
    driver.vehicle_registration = (
        registration
    )

    driver.current_area = (
        area
    )


    # Driver already has these fields in the current model.
    driver.latitude = (
        float(
            payload.current_latitude
        )
    )

    driver.longitude = (
        float(
            payload.current_longitude
        )
    )


    try:

        db.commit()

    except Exception:

        db.rollback()

        raise


    db.refresh(
        spec
    )

    db.refresh(
        vehicle
    )


    return {
        "driver_id":
            driver.id,

        "driver_name":
            driver.name,

        "routing_profile_complete":
            True,

        "driver_vehicle_id":
            vehicle.id,

        "vehicle_spec_id":
            spec.id,

        "vehicle":
            {
                "manufacturer":
                    spec.manufacturer,

                "model":
                    spec.model,

                "variant":
                    spec.variant,

                "max_payload_kg":
                    spec.max_payload_kg,

                "cargo_volume_l":
                    spec.cargo_volume_l,

                "reference_km_per_liter":
                    spec.reference_km_per_liter,
            },

        "registration":
            vehicle.registration,

        "safe_capacity_ratio":
            vehicle.safe_capacity_ratio,

        "current_latitude":
            vehicle.current_latitude,

        "current_longitude":
            vehicle.current_longitude,

        "current_area":
            vehicle.current_area,
    }


@router.get(
    "/{driver_id}",
    response_model=DriverRead,
)
def get_driver(
    driver_id: int,
    db: Session = Depends(get_db),
):
    driver = db.get(
        Driver,
        driver_id,
    )

    if not driver:
        raise HTTPException(
            status_code=404,
            detail="Driver not found.",
        )

    return driver


@router.patch(
    "/{driver_id}",
    response_model=DriverRead,
)
def update_driver(
    driver_id: int,
    payload: DriverUpdate,
    db: Session = Depends(get_db),
):
    driver = db.get(
        Driver,
        driver_id,
    )

    if not driver:
        raise HTTPException(
            status_code=404,
            detail="Driver not found.",
        )

    for key, value in (
        payload
        .model_dump(
            exclude_unset=True
        )
        .items()
    ):
        setattr(
            driver,
            key,
            value,
        )

    try:
        db.commit()

    except IntegrityError:
        db.rollback()

        raise HTTPException(
            status_code=409,
            detail=(
                "A driver with this phone number "
                "already exists."
            ),
        )

    db.refresh(driver)

    return driver


# ============================================================
# DRIVER COMPLETED ROUTE HISTORY
# ============================================================

@router.get("/{driver_id}/delivery-history")
def driver_delivery_history(
    driver_id: int,
    db: Session = Depends(get_db),
):
    from app.models.entities import (
        BatchDriverOffer,
        BatchOrder,
        BatchStop,
        Business,
        DeliveryBatch,
        OperatingDay,
        Order,
    )

    driver = db.get(
        Driver,
        driver_id,
    )

    if driver is None:
        raise HTTPException(
            status_code=404,
            detail="Driver not found",
        )

    batches = list(
        db.scalars(
            select(DeliveryBatch)
            .where(
                DeliveryBatch.driver_id
                == driver_id
            )
            .order_by(
                DeliveryBatch.id.desc()
            )
        ).all()
    )

    routes = []

    for batch in batches:

        if batch.completed_at is None:
            continue

        links = list(
            db.scalars(
                select(BatchOrder)
                .where(
                    BatchOrder.batch_id
                    == batch.id
                )
            ).all()
        )

        orders = []

        business_date = (
            batch.completed_at
            .date()
            .isoformat()
        )

        for link in links:

            order = db.get(
                Order,
                link.order_id,
            )

            customer_name = None

            if order is not None:

                business = db.get(
                    Business,
                    order.business_id,
                )

                if business is not None:
                    customer_name = (
                        getattr(
                            business,
                            "name",
                            None,
                        )
                        or
                        getattr(
                            business,
                            "business_name",
                            None,
                        )
                        or
                        getattr(
                            business,
                            "shop_name",
                            None,
                        )
                        or
                        getattr(
                            business,
                            "display_name",
                            None,
                        )
                        or
                        f"Customer {order.business_id}"
                    )

                if (
                    order.operating_day_id
                    is not None
                ):
                    day = db.get(
                        OperatingDay,
                        order.operating_day_id,
                    )

                    if day is not None:
                        business_date = str(
                            day.business_date
                        )

            orders.append({
                "order_id":
                    link.order_id,

                "daily_number":
                    (
                        order.daily_number
                        if order is not None
                        else None
                    ),

                "customer_name":
                    customer_name,

                "status":
                    (
                        getattr(
                            order.status,
                            "value",
                            str(order.status),
                        )
                        if order is not None
                        else link.status
                    ),

                "weight_kg":
                    float(
                        link.order_weight_kg
                        or 0
                    ),

                "volume_l":
                    float(
                        link.order_volume_l
                        or 0
                    ),

                "delivery_fee":
                    float(
                        link.customer_delivery_fee
                        or 0
                    ),

                "delivery_sequence":
                    link.delivery_sequence,
            })

        stops = list(
            db.scalars(
                select(BatchStop)
                .where(
                    BatchStop.batch_id
                    == batch.id
                )
                .order_by(
                    BatchStop.sequence.asc()
                )
            ).all()
        )

        offer = db.scalar(
            select(BatchDriverOffer)
            .where(
                BatchDriverOffer.batch_id
                == batch.id,
                BatchDriverOffer.driver_id
                == driver_id,
                BatchDriverOffer.outcome
                == "accepted",
            )
            .order_by(
                BatchDriverOffer.id.desc()
            )
        )

        final_payout = (
            batch.actual_driver_payout
            or
            batch.accepted_driver_payout
            or
            (
                offer.final_payout
                if offer is not None
                else None
            )
            or
            batch.predicted_driver_payout
        )

        contribution = (
            batch.actual_contribution
        )

        if (
            contribution is None
            and final_payout is not None
        ):
            contribution = (
                float(
                    batch.customer_delivery_revenue
                    or 0
                )
                -
                float(final_payout)
            )

        routes.append({
            "batch_id":
                batch.id,

            "business_date":
                business_date,

            "completed_at":
                batch.completed_at.isoformat(),

            "status":
                batch.status,

            "order_count":
                batch.order_count,

            "pickup_count":
                batch.pickup_count,

            "delivery_count":
                batch.delivery_count,

            "distance_km":
                float(
                    batch.actual_distance_km
                    if
                    batch.actual_distance_km
                    is not None
                    else
                    batch.planned_distance_km
                ),

            "road_minutes":
                float(
                    batch.actual_minutes
                    if
                    batch.actual_minutes
                    is not None
                    else
                    batch.planned_minutes
                ),

            "peak_weight_kg":
                float(
                    batch.peak_weight_kg
                    or 0
                ),

            "peak_volume_l":
                float(
                    batch.peak_volume_l
                    or 0
                ),

            "delivery_revenue":
                float(
                    batch.customer_delivery_revenue
                    or 0
                ),

            "driver_payout":
                (
                    float(final_payout)
                    if final_payout
                    is not None
                    else None
                ),

            "contribution":
                (
                    float(contribution)
                    if contribution
                    is not None
                    else None
                ),

            "orders":
                orders,

            "stops": [
                {
                    "sequence":
                        stop.sequence,

                    "stop_type":
                        stop.stop_type,

                    "location_label":
                        stop.location_label,

                    "weight_delta_kg":
                        float(
                            stop.weight_delta_kg
                            or 0
                        ),

                    "volume_delta_l":
                        float(
                            stop.volume_delta_l
                            or 0
                        ),

                    "load_weight_after_kg":
                        float(
                            stop.load_weight_after_kg
                            or 0
                        ),

                    "load_volume_after_l":
                        float(
                            stop.load_volume_after_l
                            or 0
                        ),

                    "leg_distance_km":
                        float(
                            stop.planned_leg_distance_km
                            or 0
                        ),

                    "leg_minutes":
                        float(
                            stop.planned_leg_minutes
                            or 0
                        ),

                    "status":
                        stop.status,
                }
                for stop in stops
            ],
        })

    routes.sort(
        key=lambda route: (
            route["business_date"],
            route["batch_id"],
        ),
        reverse=True,
    )

    return {
        "driver": {
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

            "is_available":
                driver.is_available,
        },

        "routes":
            routes,
    }


# ============================================================
# DRIVER COMPLETED ROUTE HISTORY
# ============================================================

@router.get("/{driver_id}/delivery-history")
def driver_delivery_history(
    driver_id: int,
    db: Session = Depends(get_db),
):
    from app.models.entities import (
        BatchDriverOffer,
        BatchOrder,
        BatchStop,
        Business,
        DeliveryBatch,
        OperatingDay,
        Order,
    )

    driver = db.get(
        Driver,
        driver_id,
    )

    if driver is None:
        raise HTTPException(
            status_code=404,
            detail="Driver not found",
        )

    batches = list(
        db.scalars(
            select(DeliveryBatch)
            .where(
                DeliveryBatch.driver_id
                == driver_id
            )
            .order_by(
                DeliveryBatch.id.desc()
            )
        ).all()
    )

    routes = []

    for batch in batches:

        if batch.completed_at is None:
            continue

        links = list(
            db.scalars(
                select(BatchOrder)
                .where(
                    BatchOrder.batch_id
                    == batch.id
                )
            ).all()
        )

        orders = []

        business_date = (
            batch.completed_at
            .date()
            .isoformat()
        )

        for link in links:

            order = db.get(
                Order,
                link.order_id,
            )

            customer_name = None

            if order is not None:

                business = db.get(
                    Business,
                    order.business_id,
                )

                if business is not None:
                    customer_name = (
                        business.name
                    )

                if (
                    order.operating_day_id
                    is not None
                ):
                    day = db.get(
                        OperatingDay,
                        order.operating_day_id,
                    )

                    if day is not None:
                        business_date = str(
                            day.business_date
                        )

            orders.append({
                "order_id":
                    link.order_id,

                "daily_number":
                    (
                        order.daily_number
                        if order is not None
                        else None
                    ),

                "customer_name":
                    customer_name,

                "status":
                    (
                        getattr(
                            order.status,
                            "value",
                            str(order.status),
                        )
                        if order is not None
                        else link.status
                    ),

                "weight_kg":
                    float(
                        link.order_weight_kg
                        or 0
                    ),

                "volume_l":
                    float(
                        link.order_volume_l
                        or 0
                    ),

                "delivery_fee":
                    float(
                        link.customer_delivery_fee
                        or 0
                    ),

                "delivery_sequence":
                    link.delivery_sequence,
            })

        stops = list(
            db.scalars(
                select(BatchStop)
                .where(
                    BatchStop.batch_id
                    == batch.id
                )
                .order_by(
                    BatchStop.sequence.asc()
                )
            ).all()
        )

        offer = db.scalar(
            select(BatchDriverOffer)
            .where(
                BatchDriverOffer.batch_id
                == batch.id,
                BatchDriverOffer.driver_id
                == driver_id,
                BatchDriverOffer.outcome
                == "accepted",
            )
            .order_by(
                BatchDriverOffer.id.desc()
            )
        )

        final_payout = (
            batch.actual_driver_payout
            or
            batch.accepted_driver_payout
            or
            (
                offer.final_payout
                if offer is not None
                else None
            )
            or
            batch.predicted_driver_payout
        )

        contribution = (
            batch.actual_contribution
        )

        if (
            contribution is None
            and final_payout is not None
        ):
            contribution = (
                float(
                    batch.customer_delivery_revenue
                    or 0
                )
                -
                float(final_payout)
            )

        routes.append({
            "batch_id":
                batch.id,

            "business_date":
                business_date,

            "completed_at":
                batch.completed_at.isoformat(),

            "status":
                batch.status,

            "order_count":
                batch.order_count,

            "pickup_count":
                batch.pickup_count,

            "delivery_count":
                batch.delivery_count,

            "distance_km":
                float(
                    batch.actual_distance_km
                    if
                    batch.actual_distance_km
                    is not None
                    else
                    batch.planned_distance_km
                ),

            "road_minutes":
                float(
                    batch.actual_minutes
                    if
                    batch.actual_minutes
                    is not None
                    else
                    batch.planned_minutes
                ),

            "peak_weight_kg":
                float(
                    batch.peak_weight_kg
                    or 0
                ),

            "peak_volume_l":
                float(
                    batch.peak_volume_l
                    or 0
                ),

            "delivery_revenue":
                float(
                    batch.customer_delivery_revenue
                    or 0
                ),

            "driver_payout":
                (
                    float(final_payout)
                    if final_payout
                    is not None
                    else None
                ),

            "contribution":
                (
                    float(contribution)
                    if contribution
                    is not None
                    else None
                ),

            "orders":
                orders,

            "stops": [
                {
                    "sequence":
                        stop.sequence,

                    "stop_type":
                        stop.stop_type,

                    "location_label":
                        stop.location_label,

                    "weight_delta_kg":
                        float(
                            stop.weight_delta_kg
                            or 0
                        ),

                    "volume_delta_l":
                        float(
                            stop.volume_delta_l
                            or 0
                        ),

                    "load_weight_after_kg":
                        float(
                            stop.load_weight_after_kg
                            or 0
                        ),

                    "load_volume_after_l":
                        float(
                            stop.load_volume_after_l
                            or 0
                        ),

                    "leg_distance_km":
                        float(
                            stop.planned_leg_distance_km
                            or 0
                        ),

                    "leg_minutes":
                        float(
                            stop.planned_leg_minutes
                            or 0
                        ),

                    "status":
                        stop.status,
                }
                for stop in stops
            ],
        })

    routes.sort(
        key=lambda route: (
            route["business_date"],
            route["batch_id"],
        ),
        reverse=True,
    )

    return {
        "driver": {
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

            "is_available":
                driver.is_available,
        },

        "routes":
            routes,
    }
