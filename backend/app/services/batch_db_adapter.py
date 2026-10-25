from __future__ import annotations

from dataclasses import dataclass
from statistics import median

from sqlalchemy import select
from sqlalchemy.orm import (
    Session,
    selectinload,
)

from app.models import (
    BatchStop,
    Business,
    Driver,
    DriverVehicle,
    Order,
    OrderStatus,
    Supplier,
    VehicleSpec,
)

from app.services.batch_planner import (
    BatchOrderInput,
    PickupInput,
)

from app.services.vehicle_capacity import (
    EffectiveVehicleCapacity,
    calculate_effective_capacity,
)


# ============================================================
# IMPORTANT
#
# These are bootstrap SERVICE-TIME priors only.
#
# They are NOT delivery prices.
# They are NOT driver pay.
#
# StoreDash replaces them with observed medians as real
# batch-stop data accumulates.
# ============================================================

BOOTSTRAP_PICKUP_SERVICE_MINUTES = 5.0
BOOTSTRAP_DELIVERY_SERVICE_MINUTES = 3.0

SERVICE_HISTORY_LIMIT = 50


@dataclass(frozen=True)
class DriverRoutingContext:
    driver: Driver

    vehicle: DriverVehicle
    spec: VehicleSpec

    latitude: float
    longitude: float

    capacity: EffectiveVehicleCapacity


@dataclass(frozen=True)
class OrderRoutingBuild:
    order: Order
    input: BatchOrderInput


def _historical_service_minutes(
    db: Session,
    *,
    stop_type: str,
    supplier_id: int | None = None,
) -> float | None:

    statement = (
        select(
            BatchStop.actual_service_minutes
        )
        .where(
            BatchStop.stop_type == stop_type,
            BatchStop.actual_service_minutes.is_not(
                None
            ),
        )
    )

    if supplier_id is not None:
        statement = statement.where(
            BatchStop.supplier_id
            == supplier_id
        )

    values = list(
        db.scalars(
            statement
            .order_by(
                BatchStop.id.desc()
            )
            .limit(
                SERVICE_HISTORY_LIMIT
            )
        ).all()
    )

    cleaned = [
        float(value)
        for value in values
        if value is not None
        and float(value) >= 0
    ]

    if not cleaned:
        return None

    return float(
        median(
            cleaned
        )
    )


def pickup_service_minutes(
    db: Session,
    supplier_id: int,
) -> float:
    """
    Prefer this supplier's observed StoreDash loading/wait time.

    Until history exists, use an explicitly identified bootstrap
    prior rather than pretending we know the real number.
    """

    observed = (
        _historical_service_minutes(
            db,
            stop_type="pickup",
            supplier_id=supplier_id,
        )
    )

    if observed is not None:
        return observed

    return (
        BOOTSTRAP_PICKUP_SERVICE_MINUTES
    )


def delivery_service_minutes(
    db: Session,
) -> float:

    observed = (
        _historical_service_minutes(
            db,
            stop_type="delivery",
        )
    )

    if observed is not None:
        return observed

    return (
        BOOTSTRAP_DELIVERY_SERVICE_MINUTES
    )


def load_dispatchable_orders(
    db: Session,
) -> list[Order]:
    """
    Only READY_FOR_DISPATCH orders enter automatic routing.

    We intentionally do NOT route:
    - draft
    - sourcing
    - awaiting approval
    - merely accepted but unpaid
    - cancelled
    - completed

    Payment/readiness state must advance correctly first.
    """

    return list(
        db.scalars(
            select(Order)
            .options(
                selectinload(
                    Order.items
                )
            )
            .where(
                Order.status
                ==
                OrderStatus.READY_FOR_DISPATCH,

                Order.assigned_driver_id.is_(
                    None
                ),
            )
            .order_by(
                Order.created_at.asc(),
                Order.id.asc(),
            )
        ).all()
    )


def build_order_routing_input(
    db: Session,
    order: Order,
) -> OrderRoutingBuild:
    """
    Converts a real StoreDash Order into the route planner's
    physical pickup/delivery representation.

    No weight or volume is invented here.
    """

    business = db.get(
        Business,
        order.business_id,
    )

    if business is None:
        raise ValueError(
            f"Order {order.id}: customer missing."
        )

    if (
        business.latitude is None
        or
        business.longitude is None
    ):
        raise ValueError(
            f"Order {order.id}: customer location not confirmed."
        )

    deliverable_items = [
        item
        for item in order.items
        if (
            (
                item.availability_status
                or ""
            ).strip().lower()
            in {
                "available",
                "partial",
            }
        )
    ]

    if not deliverable_items:
        raise ValueError(
            f"Order {order.id}: no deliverable items."
        )

    supplier_ids = {
        item.supplier_id
        for item in deliverable_items
        if item.supplier_id is not None
    }

    suppliers = {
        supplier.id: supplier
        for supplier in db.scalars(
            select(Supplier)
            .where(
                Supplier.id.in_(
                    supplier_ids
                )
            )
        ).all()
    }

    grouped: dict[
        int,
        dict,
    ] = {}

    for item in deliverable_items:

        quantity = (
            item.confirmed_quantity
        )

        if (
            quantity is None
            or
            float(quantity) <= 0
        ):
            raise ValueError(
                f"Order {order.id}, item {item.id}: "
                "confirmed quantity missing."
            )

        if item.supplier_id is None:
            raise ValueError(
                f"Order {order.id}, item {item.id}: "
                "supplier missing."
            )

        supplier = suppliers.get(
            item.supplier_id
        )

        if supplier is None:
            raise ValueError(
                f"Order {order.id}, item {item.id}: "
                "supplier record missing."
            )

        if (
            supplier.latitude is None
            or
            supplier.longitude is None
        ):
            raise ValueError(
                f"Order {order.id}, supplier "
                f"{supplier.id}: pickup location "
                "not confirmed."
            )

        if item.total_weight_kg is None:
            raise ValueError(
                f"Order {order.id}, item {item.id}: "
                "physical weight missing."
            )

        if item.total_volume_l is None:
            raise ValueError(
                f"Order {order.id}, item {item.id}: "
                "physical volume missing."
            )

        weight = float(
            item.total_weight_kg
        )

        volume = float(
            item.total_volume_l
        )

        if weight < 0 or volume < 0:
            raise ValueError(
                f"Order {order.id}, item {item.id}: "
                "invalid physical profile."
            )

        current = grouped.setdefault(
            supplier.id,
            {
                "supplier":
                    supplier,

                "weight":
                    0.0,

                "volume":
                    0.0,
            },
        )

        current[
            "weight"
        ] += weight

        current[
            "volume"
        ] += volume

    pickups = []

    for supplier_id, data in grouped.items():

        supplier = data[
            "supplier"
        ]

        pickups.append(
            PickupInput(
                supplier_id=
                    supplier_id,

                latitude=
                    float(
                        supplier.latitude
                    ),

                longitude=
                    float(
                        supplier.longitude
                    ),

                weight_kg=
                    round(
                        data[
                            "weight"
                        ],
                        3,
                    ),

                volume_l=
                    round(
                        data[
                            "volume"
                        ],
                        3,
                    ),

                service_minutes=
                    pickup_service_minutes(
                        db,
                        supplier_id,
                    ),

                location_label=
                    supplier.name,
            )
        )

    if not pickups:
        raise ValueError(
            f"Order {order.id}: no valid pickups."
        )

    result = BatchOrderInput(
        order_id=
            order.id,

        customer_latitude=
            float(
                business.latitude
            ),

        customer_longitude=
            float(
                business.longitude
            ),

        delivery_fee=
            float(
                order.delivery_fee
                or 0
            ),

        pickups=
            tuple(
                pickups
            ),

        delivery_service_minutes=
            delivery_service_minutes(
                db
            ),

        customer_label=
            business.business_name,
    )

    return OrderRoutingBuild(
        order=
            order,

        input=
            result,
    )


def get_driver_routing_context(
    db: Session,
    *,
    driver_id: int,
    driver_vehicle_id: int | None = None,
) -> DriverRoutingContext:

    driver = db.get(
        Driver,
        driver_id,
    )

    if driver is None:
        raise ValueError(
            "Driver not found."
        )

    if driver.is_active is False:
        raise ValueError(
            "Driver is inactive."
        )

    if not driver.is_available:
        raise ValueError(
            "Driver is not currently available."
        )

    vehicle_query = (
        select(
            DriverVehicle
        )
        .where(
            DriverVehicle.driver_id
            ==
            driver.id,

            DriverVehicle.is_active
            ==
            True,
        )
    )

    if driver_vehicle_id is not None:
        vehicle_query = (
            vehicle_query
            .where(
                DriverVehicle.id
                ==
                driver_vehicle_id
            )
        )

    vehicle = db.scalars(
        vehicle_query
        .order_by(
            DriverVehicle.id.asc()
        )
    ).first()

    if vehicle is None:
        raise ValueError(
            "Driver has no active StoreDash vehicle profile."
        )

    spec = db.get(
        VehicleSpec,
        vehicle.vehicle_spec_id,
    )

    if spec is None:
        raise ValueError(
            "Vehicle specification is missing."
        )

    latitude = (
        vehicle.current_latitude
        if vehicle.current_latitude
        is not None
        else driver.latitude
    )

    longitude = (
        vehicle.current_longitude
        if vehicle.current_longitude
        is not None
        else driver.longitude
    )

    if (
        latitude is None
        or
        longitude is None
    ):
        raise ValueError(
            "Driver current location is missing."
        )

    capacity = (
        calculate_effective_capacity(
            spec_payload_kg=
                float(
                    spec.max_payload_kg
                ),

            spec_cargo_volume_l=
                float(
                    spec.cargo_volume_l
                ),

            spec_seat_cargo_volume_l=
                float(
                    spec.seat_cargo_volume_l
                    or 0
                ),

            seat_area_available_for_cargo=
                bool(
                    vehicle
                    .seat_area_available_for_cargo
                ),

            payload_override_kg=
                (
                    float(
                        vehicle
                        .payload_override_kg
                    )
                    if vehicle
                    .payload_override_kg
                    is not None
                    else None
                ),

            cargo_volume_override_l=
                (
                    float(
                        vehicle
                        .cargo_volume_override_l
                    )
                    if vehicle
                    .cargo_volume_override_l
                    is not None
                    else None
                ),

            seat_volume_override_l=
                (
                    float(
                        vehicle
                        .seat_cargo_volume_override_l
                    )
                    if vehicle
                    .seat_cargo_volume_override_l
                    is not None
                    else None
                ),

            safe_capacity_ratio=
                float(
                    vehicle.safe_capacity_ratio
                ),
        )
    )

    return DriverRoutingContext(
        driver=
            driver,

        vehicle=
            vehicle,

        spec=
            spec,

        latitude=
            float(
                latitude
            ),

        longitude=
            float(
                longitude
            ),

        capacity=
            capacity,
    )
