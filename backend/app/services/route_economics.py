from __future__ import annotations

from dataclasses import (
    asdict,
    dataclass,
)

from math import ceil


ROUTE_ENGINE_VERSION = (
    "storedash-route-economics-v1"
)


# ============================================================
# IMPORTANT ARCHITECTURE
#
# Customer delivery revenue and driver payout are deliberately
# separate.
#
# Driver payout is based on THE WHOLE ROUTE:
#
# - vehicle operating cost
# - route distance
# - deadhead
# - route time
# - pickup waiting
# - delivery service time
# - number of pickups
# - number of drops
# - peak weight
# - peak volume
# - handling
# - fragility
# - access difficulty
# - urgency
# - traffic / live market pressure
#
# We do NOT calculate:
#
#     driver = 75% * each customer's delivery fee
#
# That would destroy the economic benefit of batching.
# ============================================================


def round_up_money(
    value: float,
    increment: float = 0.50,
) -> float:

    value = max(
        float(value),
        0.0,
    )

    increment = max(
        float(increment),
        0.01,
    )

    return round(
        ceil(
            value
            / increment
            - 1e-12
        )
        * increment,
        2,
    )


def clamp(
    value: float,
    minimum: float,
    maximum: float,
) -> float:

    return max(
        minimum,
        min(
            maximum,
            float(value),
        ),
    )


@dataclass(
    frozen=True
)
class VehicleEconomics:
    """
    Real vehicle-specific operating profile.

    Do NOT guess these permanently.

    They should eventually come from:
    - verified vehicle specs
    - rider onboarding
    - observed fuel use
    - actual route history
    """

    vehicle_type: str

    verified_payload_kg: float

    verified_volume_l: float

    # StoreDash intentionally plans below the manufacturer's
    # or operator's claimed maximum capacity.
    safe_capacity_ratio: float

    fuel_price_per_liter: float

    observed_km_per_liter: float

    maintenance_cost_per_km: float

    # What the rider's time should be worth before route
    # complexity adjustments.
    rider_time_value_per_hour: float

    # Stop workload is separate from pure driving time.
    pickup_service_pay: float

    delivery_service_pay: float

    # Additional pay when the vehicle is carrying close to a
    # full safe load.
    full_load_work_pay: float

    # Minimum amount worth dispatching this vehicle for.
    minimum_route_payout: float

    # Gives the rider earnings above modeled vehicle/labor cost.
    driver_earnings_margin: float = 0.20


@dataclass(
    frozen=True
)
class RouteWorkload:
    """
    Facts about ONE planned multi-order route.
    """

    order_count: int

    pickup_count: int

    delivery_count: int

    # Distance after dispatch.
    #
    # deadhead:
    # rider -> first pickup
    #
    # service route:
    # pickups / deliveries
    #
    # reposition:
    # optional expected movement after last drop
    deadhead_km: float

    service_route_km: float

    reposition_km: float

    # Route engine / map ETA excluding explicit waiting below.
    driving_minutes: float

    pickup_wait_minutes: float

    loading_minutes: float

    delivery_service_minutes: float

    # Maximum simultaneous cargo carried at any point in route.
    peak_weight_kg: float

    peak_volume_l: float

    # Normalized operational burden.
    #
    # These should eventually be generated from the existing
    # StoreDash physical-profile data.
    handling_score: float

    fragility_score: float

    # 0.0 -> 1.0
    access_difficulty: float

    # 0.0 -> 1.0
    urgency_score: float

    # Live marketplace/environment inputs.
    #
    # 1.0 means normal.
    #
    # Examples:
    # traffic / rider scarcity / heavy rain / unusual period.
    live_market_multiplier: float = 1.0

    weather_risk_multiplier: float = 1.0

    time_of_day_multiplier: float = 1.0


@dataclass(
    frozen=True
)
class RouteEconomics:
    engine_version: str

    vehicle_type: str

    order_count: int

    feasible: bool

    infeasibility_reasons: tuple[str, ...]

    operational_payload_kg: float

    operational_volume_l: float

    weight_utilization: float

    volume_utilization: float

    limiting_utilization: float

    total_route_km: float

    total_active_minutes: float

    fuel_liters: float

    fuel_cost: float

    maintenance_cost: float

    rider_time_cost: float

    pickup_work_cost: float

    delivery_work_cost: float

    load_work_cost: float

    complexity_cost: float

    modeled_route_cost: float

    driver_base_payout: float

    driver_final_payout: float

    payout_per_order_equivalent: float

    def to_dict(
        self
    ) -> dict:

        return asdict(
            self
        )


def calculate_route_economics(
    *,
    vehicle: VehicleEconomics,
    route: RouteWorkload,
) -> RouteEconomics:

    # ========================================================
    # VALIDATION
    # ========================================================

    if (
        vehicle.verified_payload_kg
        <= 0
    ):
        raise ValueError(
            "Vehicle payload capacity must be positive."
        )

    if (
        vehicle.verified_volume_l
        <= 0
    ):
        raise ValueError(
            "Vehicle volume capacity must be positive."
        )

    if (
        vehicle.observed_km_per_liter
        <= 0
    ):
        raise ValueError(
            "Vehicle km-per-liter must be positive."
        )

    if (
        vehicle.fuel_price_per_liter
        < 0
        or
        vehicle.maintenance_cost_per_km
        < 0
    ):
        raise ValueError(
            "Vehicle costs cannot be negative."
        )

    if route.order_count <= 0:
        raise ValueError(
            "Route must contain at least one order."
        )


    safe_ratio = clamp(
        vehicle.safe_capacity_ratio,
        0.40,
        1.0,
    )


    operational_payload = (
        vehicle.verified_payload_kg
        * safe_ratio
    )


    operational_volume = (
        vehicle.verified_volume_l
        * safe_ratio
    )


    peak_weight = max(
        float(
            route.peak_weight_kg
        ),
        0.0,
    )


    peak_volume = max(
        float(
            route.peak_volume_l
        ),
        0.0,
    )


    weight_utilization = (
        peak_weight
        / operational_payload
    )


    volume_utilization = (
        peak_volume
        / operational_volume
    )


    limiting_utilization = max(
        weight_utilization,
        volume_utilization,
    )


    infeasibility = []


    if weight_utilization > 1.0:
        infeasibility.append(
            "weight_capacity_exceeded"
        )


    if volume_utilization > 1.0:
        infeasibility.append(
            "volume_capacity_exceeded"
        )


    feasible = (
        len(
            infeasibility
        )
        == 0
    )


    # ========================================================
    # DISTANCE
    # ========================================================

    deadhead_km = max(
        float(
            route.deadhead_km
        ),
        0.0,
    )


    service_km = max(
        float(
            route.service_route_km
        ),
        0.0,
    )


    reposition_km = max(
        float(
            route.reposition_km
        ),
        0.0,
    )


    total_route_km = (
        deadhead_km
        + service_km
        + reposition_km
    )


    # ========================================================
    # TIME
    #
    # Driving is only part of rider workload.
    #
    # Waiting/loading/stopping must be paid too.
    # ========================================================

    driving_minutes = max(
        float(
            route.driving_minutes
        ),
        0.0,
    )


    pickup_wait_minutes = max(
        float(
            route.pickup_wait_minutes
        ),
        0.0,
    )


    loading_minutes = max(
        float(
            route.loading_minutes
        ),
        0.0,
    )


    delivery_service_minutes = max(
        float(
            route.delivery_service_minutes
        ),
        0.0,
    )


    total_active_minutes = (
        driving_minutes
        + pickup_wait_minutes
        + loading_minutes
        + delivery_service_minutes
    )


    # ========================================================
    # VEHICLE COST
    # ========================================================

    fuel_liters = (
        total_route_km
        /
        vehicle.observed_km_per_liter
    )


    fuel_cost = (
        fuel_liters
        * vehicle.fuel_price_per_liter
    )


    maintenance_cost = (
        total_route_km
        * vehicle.maintenance_cost_per_km
    )


    # ========================================================
    # RIDER TIME
    # ========================================================

    rider_time_cost = (
        (
            total_active_minutes
            / 60.0
        )
        * vehicle.rider_time_value_per_hour
    )


    # ========================================================
    # STOP WORK
    # ========================================================

    pickup_work_cost = (
        max(
            int(
                route.pickup_count
            ),
            0,
        )
        * vehicle.pickup_service_pay
    )


    delivery_work_cost = (
        max(
            int(
                route.delivery_count
            ),
            0,
        )
        * vehicle.delivery_service_pay
    )


    # ========================================================
    # LOAD WORK
    #
    # This is intentionally route-level.
    #
    # Twenty small orders sharing one vehicle should NOT cause
    # the same payout as twenty completely separate trips.
    # ========================================================

    utilization_for_pay = clamp(
        limiting_utilization,
        0.0,
        1.5,
    )


    load_work_cost = (
        vehicle.full_load_work_pay
        * (
            utilization_for_pay
            ** 1.6
        )
    )


    # ========================================================
    # COMPLEXITY
    #
    # handling_score / fragility_score are deliberately
    # compressed because their raw totals may increase with
    # item count.
    # ========================================================

    handling = max(
        float(
            route.handling_score
        ),
        0.0,
    )


    fragility = max(
        float(
            route.fragility_score
        ),
        0.0,
    )


    access = clamp(
        route.access_difficulty,
        0.0,
        1.0,
    )


    urgency = clamp(
        route.urgency_score,
        0.0,
        1.0,
    )


    complexity_cost = (
        vehicle.minimum_route_payout
        * (
            0.05
            * min(
                handling,
                4.0,
            )

            + 0.04
            * min(
                fragility,
                4.0,
            )

            + 0.12
            * access

            + 0.15
            * urgency
        )
    )


    # ========================================================
    # MODELED ROUTE COST
    #
    # What the route appears to cost before rider earnings.
    # ========================================================

    modeled_route_cost = (
        fuel_cost
        + maintenance_cost
        + rider_time_cost
        + pickup_work_cost
        + delivery_work_cost
        + load_work_cost
        + complexity_cost
    )


    # ========================================================
    # DRIVER EARNINGS
    #
    # Driver gets reasonable upside over modeled operating /
    # labor cost.
    #
    # The final payout is NEVER derived from 75% of customer
    # revenue.
    # ========================================================

    earnings_margin = clamp(
        vehicle.driver_earnings_margin,
        0.0,
        1.0,
    )


    driver_base_payout = max(
        vehicle.minimum_route_payout,

        modeled_route_cost
        * (
            1.0
            + earnings_margin
        ),
    )


    # ========================================================
    # LIVE CONDITIONS
    #
    # These are intended to come from real inputs eventually.
    #
    # They are intentionally bounded so one faulty upstream
    # signal cannot generate a ridiculous payout.
    # ========================================================

    market_multiplier = clamp(
        route.live_market_multiplier,
        0.80,
        1.50,
    )


    weather_multiplier = clamp(
        route.weather_risk_multiplier,
        0.90,
        1.40,
    )


    time_multiplier = clamp(
        route.time_of_day_multiplier,
        0.90,
        1.35,
    )


    driver_final_payout = (
        driver_base_payout
        * market_multiplier
        * weather_multiplier
        * time_multiplier
    )


    driver_final_payout = (
        round_up_money(
            driver_final_payout
        )
    )


    payout_per_order = (
        driver_final_payout
        / route.order_count
    )


    return RouteEconomics(
        engine_version=
            ROUTE_ENGINE_VERSION,

        vehicle_type=
            vehicle.vehicle_type,

        order_count=
            route.order_count,

        feasible=
            feasible,

        infeasibility_reasons=
            tuple(
                infeasibility
            ),

        operational_payload_kg=
            round(
                operational_payload,
                3,
            ),

        operational_volume_l=
            round(
                operational_volume,
                3,
            ),

        weight_utilization=
            round(
                weight_utilization,
                6,
            ),

        volume_utilization=
            round(
                volume_utilization,
                6,
            ),

        limiting_utilization=
            round(
                limiting_utilization,
                6,
            ),

        total_route_km=
            round(
                total_route_km,
                3,
            ),

        total_active_minutes=
            round(
                total_active_minutes,
                3,
            ),

        fuel_liters=
            round(
                fuel_liters,
                4,
            ),

        fuel_cost=
            round(
                fuel_cost,
                2,
            ),

        maintenance_cost=
            round(
                maintenance_cost,
                2,
            ),

        rider_time_cost=
            round(
                rider_time_cost,
                2,
            ),

        pickup_work_cost=
            round(
                pickup_work_cost,
                2,
            ),

        delivery_work_cost=
            round(
                delivery_work_cost,
                2,
            ),

        load_work_cost=
            round(
                load_work_cost,
                2,
            ),

        complexity_cost=
            round(
                complexity_cost,
                2,
            ),

        modeled_route_cost=
            round(
                modeled_route_cost,
                2,
            ),

        driver_base_payout=
            round_up_money(
                driver_base_payout
            ),

        driver_final_payout=
            driver_final_payout,

        payout_per_order_equivalent=
            round(
                payout_per_order,
                2,
            ),
    )


@dataclass(
    frozen=True
)
class BatchedRouteEconomics:

    customer_delivery_revenue: float

    driver_route_payout: float

    storedash_route_contribution: float

    storedash_route_margin_rate: float

    average_customer_delivery_fee: float

    driver_equivalent_per_order: float

    commercially_viable: bool

    def to_dict(
        self
    ) -> dict:

        return asdict(
            self
        )


def evaluate_batched_route(
    *,
    customer_delivery_fees: list[float],
    route_economics: RouteEconomics,
) -> BatchedRouteEconomics:

    if not customer_delivery_fees:
        raise ValueError(
            "Route must contain customer delivery fees."
        )


    delivery_revenue = sum(
        max(
            float(
                fee
            ),
            0.0,
        )
        for fee in customer_delivery_fees
    )


    payout = float(
        route_economics.driver_final_payout
    )


    contribution = (
        delivery_revenue
        - payout
    )


    margin_rate = (
        contribution
        / delivery_revenue
        if delivery_revenue > 0
        else 0.0
    )


    return BatchedRouteEconomics(
        customer_delivery_revenue=
            round(
                delivery_revenue,
                2,
            ),

        driver_route_payout=
            round(
                payout,
                2,
            ),

        storedash_route_contribution=
            round(
                contribution,
                2,
            ),

        storedash_route_margin_rate=
            round(
                margin_rate,
                6,
            ),

        average_customer_delivery_fee=
            round(
                delivery_revenue
                /
                len(
                    customer_delivery_fees
                ),
                2,
            ),

        driver_equivalent_per_order=
            round(
                payout
                /
                len(
                    customer_delivery_fees
                ),
                2,
            ),

        commercially_viable=(
            route_economics.feasible
            and
            contribution
            > 0
        ),
    )
