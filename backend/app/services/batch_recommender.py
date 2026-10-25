from __future__ import annotations

from math import (
    asin,
    cos,
    radians,
    sin,
    sqrt,
)

from sqlalchemy.orm import Session

from app.services.batch_db_adapter import (
    build_order_routing_input,
    get_driver_routing_context,
    load_dispatchable_orders,
)

from app.services.batch_planner import (
    BatchOrderInput,
    BatchPlan,
    plan_batch_route,
)


RECOMMENDER_VERSION = (
    "storedash-batch-recommender-v1"
)


def haversine_km(
    lat1: float,
    lon1: float,
    lat2: float,
    lon2: float,
) -> float:

    radius_km = 6371.0088

    phi1 = radians(
        lat1
    )

    phi2 = radians(
        lat2
    )

    delta_phi = radians(
        lat2 - lat1
    )

    delta_lambda = radians(
        lon2 - lon1
    )

    value = (
        sin(
            delta_phi / 2
        )
        ** 2

        +
        cos(phi1)
        *
        cos(phi2)
        *
        sin(
            delta_lambda / 2
        )
        ** 2
    )

    return (
        2
        *
        radius_km
        *
        asin(
            sqrt(
                value
            )
        )
    )


def _plan(
    *,
    inputs: list[
        BatchOrderInput
    ],

    driver_latitude: float,
    driver_longitude: float,

    capacity,

    duration_multiplier: float,

    max_total_route_minutes:
        float | None,
) -> BatchPlan:

    return plan_batch_route(
        orders=
            inputs,

        driver_latitude=
            driver_latitude,

        driver_longitude=
            driver_longitude,

        capacity=
            capacity,

        duration_multiplier=
            duration_multiplier,

        max_total_route_minutes=
            max_total_route_minutes,
    )


def recommend_batch_for_driver(
    db: Session,
    *,
    driver_id: int,

    driver_vehicle_id:
        int | None = None,

    max_orders: int = 8,

    candidate_limit: int = 12,

    duration_multiplier:
        float = 1.0,

    max_total_route_minutes:
        float | None = None,
) -> dict:
    """
    Real StoreDash automatic batching recommendation.

    This version optimizes PHYSICAL + ROUTING efficiency.

    It does not yet finalize driver payout.
    Route economics gets layered on after the route is physically
    valid and operationally sensible.
    """

    max_orders = max(
        1,
        min(
            int(max_orders),
            12,
        ),
    )

    candidate_limit = max(
        max_orders,
        min(
            int(candidate_limit),
            20,
        ),
    )

    driver = (
        get_driver_routing_context(
            db,

            driver_id=
                driver_id,

            driver_vehicle_id=
                driver_vehicle_id,
        )
    )

    raw_orders = (
        load_dispatchable_orders(
            db
        )
    )

    valid = []
    blocked = []

    for order in raw_orders:

        try:
            built = (
                build_order_routing_input(
                    db,
                    order,
                )
            )

            distance = (
                haversine_km(
                    driver.latitude,
                    driver.longitude,

                    built.input
                    .customer_latitude,

                    built.input
                    .customer_longitude,
                )
            )

            valid.append(
                (
                    order,
                    built.input,
                    distance,
                )
            )

        except ValueError as exc:
            blocked.append(
                {
                    "order_id":
                        order.id,

                    "reason":
                        str(exc),
                }
            )

    # Pre-filter by geographical proximity before making
    # expensive road-matrix calls.
    valid.sort(
        key=lambda row: (
            row[2],
            row[0].created_at,
            row[0].id,
        )
    )

    valid = valid[
        :candidate_limit
    ]

    if not valid:
        return {
            "version":
                RECOMMENDER_VERSION,

            "driver_id":
                driver.driver.id,

            "driver_vehicle_id":
                driver.vehicle.id,

            "vehicle":
                {
                    "manufacturer":
                        driver.spec.manufacturer,

                    "model":
                        driver.spec.model,

                    "variant":
                        driver.spec.variant,
                },

            "capacity":
                driver.capacity.to_dict(),

            "chosen_order_ids":
                [],

            "plan":
                None,

            "blocked":
                blocked,

            "message":
                "No dispatchable orders are currently available.",
        }

    # --------------------------------------------------------
    # SEED
    #
    # Among nearby candidates, prefer the oldest paid/ready
    # order that physically works.
    # --------------------------------------------------------

    by_age = sorted(
        valid,
        key=lambda row: (
            row[0].created_at,
            row[0].id,
        ),
    )

    chosen = []
    current_plan = None

    seed_row = None

    for row in by_age:

        order, order_input, _ = row

        try:
            plan = _plan(
                inputs=[
                    order_input
                ],

                driver_latitude=
                    driver.latitude,

                driver_longitude=
                    driver.longitude,

                capacity=
                    driver.capacity,

                duration_multiplier=
                    duration_multiplier,

                max_total_route_minutes=
                    max_total_route_minutes,
            )

        except Exception as exc:
            blocked.append(
                {
                    "order_id":
                        order.id,

                    "reason":
                        (
                            "Route service failed: "
                            f"{exc}"
                        ),
                }
            )

            continue

        if plan.feasible:
            seed_row = row
            chosen = [
                order_input
            ]
            current_plan = plan
            break

        blocked.append(
            {
                "order_id":
                    order.id,

                "reason":
                    plan.rejection_reason
                    or
                    "Order does not fit this driver.",
            }
        )

    if (
        seed_row is None
        or
        current_plan is None
    ):
        return {
            "version":
                RECOMMENDER_VERSION,

            "driver_id":
                driver.driver.id,

            "driver_vehicle_id":
                driver.vehicle.id,

            "capacity":
                driver.capacity.to_dict(),

            "chosen_order_ids":
                [],

            "plan":
                None,

            "blocked":
                blocked,

            "message":
                (
                    "None of the candidate orders "
                    "can be assigned to this driver."
                ),
        }

    chosen_ids = {
        item.order_id
        for item in chosen
    }

    # --------------------------------------------------------
    # EXPANSION
    #
    # Keep adding the order with the best extra-delivery-fee
    # per extra route minute, subject to ALL physical and
    # pickup-before-delivery constraints.
    #
    # This is routing efficiency, NOT final profit optimization.
    # --------------------------------------------------------

    while (
        len(chosen)
        <
        max_orders
    ):

        possibilities = []

        for order, order_input, _ in valid:

            if (
                order_input.order_id
                in chosen_ids
            ):
                continue

            trial_inputs = (
                chosen
                +
                [
                    order_input
                ]
            )

            try:
                trial = _plan(
                    inputs=
                        trial_inputs,

                    driver_latitude=
                        driver.latitude,

                    driver_longitude=
                        driver.longitude,

                    capacity=
                        driver.capacity,

                    duration_multiplier=
                        duration_multiplier,

                    max_total_route_minutes=
                        max_total_route_minutes,
                )

            except Exception as exc:
                blocked.append(
                    {
                        "order_id":
                            order.id,

                        "reason":
                            (
                                "Route service failed: "
                                f"{exc}"
                            ),
                    }
                )
                continue

            if not trial.feasible:
                blocked.append(
                    {
                        "order_id":
                            order.id,

                        "reason":
                            trial.rejection_reason
                            or
                            "Batch became infeasible.",
                    }
                )
                continue

            extra_minutes = max(
                trial.total_route_minutes
                -
                current_plan
                .total_route_minutes,

                0.0,
            )

            extra_distance = max(
                trial.total_distance_km
                -
                current_plan
                .total_distance_km,

                0.0,
            )

            added_revenue = float(
                order_input.delivery_fee
            )

            efficiency_score = (
                added_revenue
                /
                (
                    1.0
                    +
                    extra_minutes
                )
            )

            possibilities.append(
                (
                    efficiency_score,

                    -extra_minutes,

                    -extra_distance,

                    order,
                    order_input,
                    trial,
                )
            )

        if not possibilities:
            break

        possibilities.sort(
            key=lambda row: (
                row[0],
                row[1],
                row[2],
            ),
            reverse=True,
        )

        (
            _score,
            _minutes,
            _distance,
            _order,
            best_input,
            best_plan,
        ) = possibilities[0]

        chosen.append(
            best_input
        )

        chosen_ids.add(
            best_input.order_id
        )

        current_plan = (
            best_plan
        )

    return {
        "version":
            RECOMMENDER_VERSION,

        "driver_id":
            driver.driver.id,

        "driver_name":
            driver.driver.name,

        "driver_vehicle_id":
            driver.vehicle.id,

        "vehicle":
            {
                "manufacturer":
                    driver.spec.manufacturer,

                "model":
                    driver.spec.model,

                "variant":
                    driver.spec.variant,

                "registration":
                    driver.vehicle.registration,
            },

        "capacity":
            driver.capacity.to_dict(),

        "dispatch_pool_count":
            len(raw_orders),

        "candidate_count":
            len(valid),

        "chosen_order_ids":
            [
                item.order_id
                for item in chosen
            ],

        "plan":
            current_plan.to_dict(),

        "blocked":
            blocked,
    }
