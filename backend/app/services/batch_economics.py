from __future__ import annotations

from dataclasses import (
    asdict,
    dataclass,
)

from app.services.batch_planner import (
    BatchPlan,
)

from app.services.route_economics import (
    RouteEconomics,
    RouteWorkload,
    VehicleEconomics,
    calculate_route_economics,
)


BATCH_ECONOMICS_VERSION = (
    "storedash-batch-economics-v1"
)


@dataclass(
    frozen=True
)
class BatchEconomicEvaluation:
    version: str

    feasible: bool

    customer_delivery_revenue: float

    driver_route_payout: float

    storedash_contribution: float

    storedash_margin_rate: float

    contribution_per_order: float

    route_economics: RouteEconomics

    def to_dict(self) -> dict:
        return {
            "version":
                self.version,

            "feasible":
                self.feasible,

            "customer_delivery_revenue":
                self.customer_delivery_revenue,

            "driver_route_payout":
                self.driver_route_payout,

            "storedash_contribution":
                self.storedash_contribution,

            "storedash_margin_rate":
                self.storedash_margin_rate,

            "contribution_per_order":
                self.contribution_per_order,

            "route_economics":
                self.route_economics.to_dict(),
        }


@dataclass(
    frozen=True
)
class MarginalBatchDecision:
    economically_better: bool

    added_order_count: int

    added_delivery_revenue: float

    added_driver_payout: float

    added_storedash_contribution: float

    extra_distance_km: float

    extra_route_minutes: float

    contribution_per_extra_minute: float

    previous_contribution: float

    new_contribution: float

    previous_margin_rate: float

    new_margin_rate: float

    def to_dict(self) -> dict:
        return asdict(self)


def evaluate_batch_plan(
    *,
    plan: BatchPlan,
    vehicle: VehicleEconomics,
    handling_score: float = 0.0,
    fragility_score: float = 0.0,
    access_difficulty: float = 0.0,
    urgency_score: float = 0.0,
    live_market_multiplier: float = 1.0,
    weather_risk_multiplier: float = 1.0,
    time_of_day_multiplier: float = 1.0,
    pickup_service_minutes: float | None = None,
    delivery_service_minutes: float | None = None,
) -> BatchEconomicEvaluation:

    if not plan.feasible:
        raise ValueError(
            "Cannot price an infeasible batch route."
        )

    if plan.order_count <= 0:
        raise ValueError(
            "Batch must contain at least one order."
        )

    first_leg_km = 0.0

    if plan.stops:
        first_leg_km = max(
            float(
                plan.stops[
                    0
                ].travel_from_previous_km
            ),
            0.0,
        )

    service_route_km = max(
        float(
            plan.total_distance_km
        )
        - first_leg_km,
        0.0,
    )

    if (
        pickup_service_minutes is None
        or
        delivery_service_minutes is None
    ):
        pickup_minutes_from_stops = sum(
            max(
                float(
                    stop.service_minutes
                ),
                0.0,
            )
            for stop
            in plan.stops
            if stop.stop_type == "pickup"
        )

        delivery_minutes_from_stops = sum(
            max(
                float(
                    stop.service_minutes
                ),
                0.0,
            )
            for stop
            in plan.stops
            if stop.stop_type == "delivery"
        )

        if plan.stops:
            if pickup_service_minutes is None:
                pickup_service_minutes = (
                    pickup_minutes_from_stops
                )

            if delivery_service_minutes is None:
                delivery_service_minutes = (
                    delivery_minutes_from_stops
                )

        else:
            # Synthetic/manual BatchPlans may not contain the
            # stop list. Never silently erase service work.
            #
            # In that case use the known total service time and
            # divide it according to pickup/drop stop counts.
            total_service = max(
                float(
                    plan.total_service_minutes
                ),
                0.0,
            )

            stop_count = max(
                plan.pickup_count
                +
                plan.delivery_count,
                1,
            )

            estimated_pickup_minutes = (
                total_service
                *
                (
                    plan.pickup_count
                    /
                    stop_count
                )
            )

            estimated_delivery_minutes = (
                total_service
                -
                estimated_pickup_minutes
            )

            if pickup_service_minutes is None:
                pickup_service_minutes = (
                    estimated_pickup_minutes
                )

            if delivery_service_minutes is None:
                delivery_service_minutes = (
                    estimated_delivery_minutes
                )

    workload = RouteWorkload(
        order_count=
            plan.order_count,

        pickup_count=
            plan.pickup_count,

        delivery_count=
            plan.delivery_count,

        deadhead_km=
            first_leg_km,

        service_route_km=
            service_route_km,

        reposition_km=
            0.0,

        driving_minutes=
            plan.total_driving_minutes,

        pickup_wait_minutes=
            0.0,

        # For now the pickup-stop service time represents
        # loading / supplier handling time.
        loading_minutes=
            pickup_service_minutes,

        delivery_service_minutes=
            delivery_service_minutes,

        peak_weight_kg=
            plan.peak_weight_kg,

        peak_volume_l=
            plan.peak_volume_l,

        handling_score=
            handling_score,

        fragility_score=
            fragility_score,

        access_difficulty=
            access_difficulty,

        urgency_score=
            urgency_score,

        live_market_multiplier=
            live_market_multiplier,

        weather_risk_multiplier=
            weather_risk_multiplier,

        time_of_day_multiplier=
            time_of_day_multiplier,
    )

    route_result = (
        calculate_route_economics(
            vehicle=vehicle,
            route=workload,
        )
    )

    revenue = max(
        float(
            plan.customer_delivery_revenue
        ),
        0.0,
    )

    payout = float(
        route_result.driver_final_payout
    )

    contribution = (
        revenue
        - payout
    )

    margin = (
        contribution
        / revenue
        if revenue > 0
        else 0.0
    )

    contribution_per_order = (
        contribution
        / plan.order_count
    )

    return BatchEconomicEvaluation(
        version=
            BATCH_ECONOMICS_VERSION,

        feasible=
            route_result.feasible,

        customer_delivery_revenue=
            round(
                revenue,
                2,
            ),

        driver_route_payout=
            round(
                payout,
                2,
            ),

        storedash_contribution=
            round(
                contribution,
                2,
            ),

        storedash_margin_rate=
            round(
                margin,
                6,
            ),

        contribution_per_order=
            round(
                contribution_per_order,
                2,
            ),

        route_economics=
            route_result,
    )


def compare_batch_expansion(
    *,
    current_plan: BatchPlan,
    expanded_plan: BatchPlan,
    vehicle: VehicleEconomics,
    current_handling_score: float = 0.0,
    expanded_handling_score: float = 0.0,
    current_fragility_score: float = 0.0,
    expanded_fragility_score: float = 0.0,
    access_difficulty: float = 0.0,
    urgency_score: float = 0.0,
    live_market_multiplier: float = 1.0,
    weather_risk_multiplier: float = 1.0,
    time_of_day_multiplier: float = 1.0,
) -> MarginalBatchDecision:

    if not current_plan.feasible:
        raise ValueError(
            "Current batch must be feasible."
        )

    if not expanded_plan.feasible:
        return MarginalBatchDecision(
            economically_better=False,

            added_order_count=max(
                expanded_plan.order_count
                - current_plan.order_count,
                0,
            ),

            added_delivery_revenue=0.0,
            added_driver_payout=0.0,
            added_storedash_contribution=0.0,

            extra_distance_km=0.0,
            extra_route_minutes=0.0,

            contribution_per_extra_minute=0.0,

            previous_contribution=0.0,
            new_contribution=0.0,

            previous_margin_rate=0.0,
            new_margin_rate=0.0,
        )

    current = evaluate_batch_plan(
        plan=current_plan,
        vehicle=vehicle,

        handling_score=
            current_handling_score,

        fragility_score=
            current_fragility_score,

        access_difficulty=
            access_difficulty,

        urgency_score=
            urgency_score,

        live_market_multiplier=
            live_market_multiplier,

        weather_risk_multiplier=
            weather_risk_multiplier,

        time_of_day_multiplier=
            time_of_day_multiplier,
    )

    expanded = evaluate_batch_plan(
        plan=expanded_plan,
        vehicle=vehicle,

        handling_score=
            expanded_handling_score,

        fragility_score=
            expanded_fragility_score,

        access_difficulty=
            access_difficulty,

        urgency_score=
            urgency_score,

        live_market_multiplier=
            live_market_multiplier,

        weather_risk_multiplier=
            weather_risk_multiplier,

        time_of_day_multiplier=
            time_of_day_multiplier,
    )

    added_revenue = (
        expanded.customer_delivery_revenue
        - current.customer_delivery_revenue
    )

    added_payout = (
        expanded.driver_route_payout
        - current.driver_route_payout
    )

    added_contribution = (
        expanded.storedash_contribution
        - current.storedash_contribution
    )

    extra_distance = max(
        expanded_plan.total_distance_km
        - current_plan.total_distance_km,
        0.0,
    )

    extra_minutes = max(
        expanded_plan.total_route_minutes
        - current_plan.total_route_minutes,
        0.0,
    )

    if extra_minutes > 0:
        contribution_per_extra_minute = (
            added_contribution
            / extra_minutes
        )
    else:
        contribution_per_extra_minute = (
            added_contribution
        )

    return MarginalBatchDecision(
        economically_better=(
            added_revenue > 0
            and
            added_contribution > 0
            and
            expanded.feasible
        ),

        added_order_count=max(
            expanded_plan.order_count
            - current_plan.order_count,
            0,
        ),

        added_delivery_revenue=
            round(
                added_revenue,
                2,
            ),

        added_driver_payout=
            round(
                added_payout,
                2,
            ),

        added_storedash_contribution=
            round(
                added_contribution,
                2,
            ),

        extra_distance_km=
            round(
                extra_distance,
                3,
            ),

        extra_route_minutes=
            round(
                extra_minutes,
                2,
            ),

        contribution_per_extra_minute=
            round(
                contribution_per_extra_minute,
                4,
            ),

        previous_contribution=
            current.storedash_contribution,

        new_contribution=
            expanded.storedash_contribution,

        previous_margin_rate=
            current.storedash_margin_rate,

        new_margin_rate=
            expanded.storedash_margin_rate,
    )
