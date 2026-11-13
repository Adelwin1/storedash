from __future__ import annotations

from dataclasses import (
    asdict,
    dataclass,
    is_dataclass,
)

import os

from app.services.batch_economics import (
    evaluate_batch_plan,
)

from app.services.route_economics import (
    VehicleEconomics,
    round_up_money,
)


PRICING_POLICY_VERSION = (
    "storedash-batch-route-pricing-bootstrap-v2"
)


@dataclass(
    frozen=True
)
class BatchRoutePricing:

    policy_version: str

    economics_version: str

    predicted_driver_payout: float

    predicted_contribution: float

    predicted_margin_rate: float


def _env_float(
    name: str,
    default: float,
) -> float:

    raw = os.getenv(
        name
    )

    if (
        raw is None
        or not raw.strip()
    ):
        return float(
            default
        )

    try:
        return float(
            raw
        )

    except ValueError as exc:
        raise ValueError(
            f"{name} must be numeric."
        ) from exc


def _find_value(
    value,
    target: str,
):

    if isinstance(
        value,
        dict,
    ):

        if target in value:
            return value[
                target
            ]

        for child in value.values():

            found = _find_value(
                child,
                target,
            )

            if found is not None:
                return found

    elif isinstance(
        value,
        (
            list,
            tuple,
        ),
    ):

        for child in value:

            found = _find_value(
                child,
                target,
            )

            if found is not None:
                return found

    return None


def _vehicle_economics(
    context,
) -> VehicleEconomics:

    safe_ratio = float(
        context.vehicle.safe_capacity_ratio
        or
        1.0
    )

    if not (
        0
        <
        safe_ratio
        <=
        1.0
    ):
        raise ValueError(
            "Driver vehicle safe capacity ratio "
            "must be greater than 0 and at most 1."
        )


    # context.capacity already contains the operational
    # post-safety capacities.
    #
    # Recover the underlying verified/override capacity so
    # route_economics can apply the same safety ratio itself.

    verified_payload = (
        float(
            context.capacity.max_payload_kg
        )
        /
        safe_ratio
    )

    verified_volume = (
        float(
            context.capacity.max_volume_l
        )
        /
        safe_ratio
    )


    observed_efficiency = (
        context.vehicle.observed_km_per_liter
        or
        context.spec.reference_km_per_liter
        or
        _env_float(
            "STOREDASH_ROUTE_DEFAULT_KM_PER_LITER",
            20.0,
        )
    )


    vehicle_name = " ".join(
        str(value)
        for value in (
            context.spec.manufacturer,
            context.spec.model,
            context.spec.variant,
        )
        if value
    )


    # IMPORTANT:
    #
    # These defaults are bootstrap coefficients so the
    # integration can operate before StoreDash has enough
    # observed Ghana route data.
    #
    # They are configuration inputs, NOT claimed market truth.
    # Replace/recalibrate them from StoreDash actual outcomes.

    return VehicleEconomics(
        vehicle_type=
            vehicle_name,

        verified_payload_kg=
            verified_payload,

        verified_volume_l=
            verified_volume,

        safe_capacity_ratio=
            safe_ratio,

        fuel_price_per_liter=
            _env_float(
                "STOREDASH_ROUTE_FUEL_PRICE_PER_LITER",
                15.0,
            ),

        observed_km_per_liter=
            float(
                observed_efficiency
            ),

        maintenance_cost_per_km=
            _env_float(
                "STOREDASH_ROUTE_MAINTENANCE_PER_KM",
                0.90,
            ),

        rider_time_value_per_hour=
            _env_float(
                "STOREDASH_ROUTE_RIDER_TIME_PER_HOUR",
                30.0,
            ),

        pickup_service_pay=
            _env_float(
                "STOREDASH_ROUTE_PICKUP_SERVICE_PAY",
                8.0,
            ),

        delivery_service_pay=
            _env_float(
                "STOREDASH_ROUTE_DELIVERY_SERVICE_PAY",
                6.0,
            ),

        full_load_work_pay=
            _env_float(
                "STOREDASH_ROUTE_FULL_LOAD_WORK_PAY",
                15.0,
            ),

        minimum_route_payout=
            _env_float(
                "STOREDASH_ROUTE_MINIMUM_PAYOUT",
                30.0,
            ),

        driver_earnings_margin=
            _env_float(
                "STOREDASH_ROUTE_DRIVER_MARGIN",
                0.25,
            ),
    )


def price_batch_plan(
    *,
    context,
    plan,
    orders,
) -> BatchRoutePricing:

    vehicle = (
        _vehicle_economics(
            context
        )
    )


    handling_score = sum(
        float(
            getattr(
                order,
                "total_handling_score",
                0,
            )
            or
            0
        )
        for order in orders
    )

    fragility_score = sum(
        float(
            getattr(
                order,
                "total_fragility_score",
                0,
            )
            or
            0
        )
        for order in orders
    )


    evaluation = (
        evaluate_batch_plan(
            plan=
                plan,

            vehicle=
                vehicle,

            handling_score=
                handling_score,

            fragility_score=
                fragility_score,
        )
    )


    if is_dataclass(
        evaluation
    ):
        data = asdict(
            evaluation
        )
    else:
        data = vars(
            evaluation
        )


    payout = _find_value(
        data,
        "driver_final_payout",
    )

    contribution = _find_value(
        data,
        "storedash_route_contribution",
    )

    margin_rate = _find_value(
        data,
        "storedash_route_margin_rate",
    )

    engine_version = _find_value(
        data,
        "engine_version",
    )


    if payout is None:
        raise ValueError(
            "Route economics did not produce "
            "a driver payout."
        )


    payout = float(
        payout
    )

    revenue = float(
        plan.customer_delivery_revenue
    )

    # StoreDash hard rule:
    # driver compensation can come only from delivery revenue.
    # Service fees and other StoreDash fees are never available
    # for driver payout.
    payout = min(
        max(payout, 0.0),
        max(revenue, 0.0),
    )

    contribution = (
        revenue
        - payout
    )

    margin_rate = (
        contribution
        / revenue
        if revenue > 0
        else 0.0
    )


    return BatchRoutePricing(
        policy_version=
            PRICING_POLICY_VERSION,

        economics_version=
            str(
                engine_version
                or
                "storedash-route-economics"
            ),

        predicted_driver_payout=
            round(
                payout,
                2,
            ),

        predicted_contribution=
            round(
                contribution,
                2,
            ),

        predicted_margin_rate=
            round(
                margin_rate,
                6,
            ),
    )


def default_driver_offer_ceiling(
    recommended_payout: float,
) -> float:

    uplift = max(
        0.0,
        _env_float(
            "STOREDASH_ROUTE_MAX_OFFER_UPLIFT",
            0.10,
        ),
    )

    return round_up_money(
        float(
            recommended_payout
        )
        *
        (
            1.0
            +
            uplift
        ),
        increment=0.5,
    )
