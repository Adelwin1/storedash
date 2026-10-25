from __future__ import annotations

import math

from dataclasses import (
    asdict,
    dataclass,
)


# ============================================================
# STOREDASH UPFRONT DELIVERY MODEL
#
# Architecture inspired by modern marketplace pricing:
#
# - capacity / dispatch minimum
# - route distance
# - expected route duration
# - multiple pickup stops
# - cargo utilization
# - handling / fragility
# - historical market calibration
#
# PUBLIC MARKET ANCHORS:
#
# Current CargoMov published "from" prices.
#
# IMPORTANT:
# These are STARTING market anchors, not guaranteed trip
# prices and not CargoMov vehicle capacity claims.
#
# The planning capacities below are StoreDash bootstrap
# assumptions used only for feature engineering.
# Real CargoMov bids will recalibrate them.
# ============================================================


MODEL_ENGINE_VERSION = (
    "storedash-upfront-engine-v1"
)


VOLUMETRIC_KG_PER_L = 0.25


CAPACITY_CLASSES = (
    {
        "key": "mini_van",
        "planning_capacity_kg": 250.0,
        "market_anchor_ghs": 120.0,
    },
    {
        "key": "van",
        "planning_capacity_kg": 600.0,
        "market_anchor_ghs": 160.0,
    },
    {
        "key": "pickup",
        "planning_capacity_kg": 1200.0,
        "market_anchor_ghs": 220.0,
    },
    {
        "key": "kia_truck",
        "planning_capacity_kg": 3000.0,
        "market_anchor_ghs": 320.0,
    },
    {
        "key": "truck_16ft",
        "planning_capacity_kg": 7000.0,
        "market_anchor_ghs": 650.0,
    },
    {
        "key": "truck_20ft",
        "planning_capacity_kg": 14000.0,
        "market_anchor_ghs": 1300.0,
    },
)


DEFAULT_COEFFICIENTS = {
    "global_multiplier":
        1.0,

    "target_margin":
        0.25,

    "route_extra_km_rate":
        0.035,

    "route_extra_minute_rate":
        0.010,

    "extra_stop_rate":
        0.08,

    "capacity_utilization_rate":
        0.35,

    "handling_rate":
        0.05,

    "fragility_rate":
        0.04,

    "capacity_multipliers": {
        item["key"]: 1.0
        for item in CAPACITY_CLASSES
    }
    | {
        "heavy_project": 1.0,
    },

    "distance_band_multipliers": {
        "0_5_km": 1.0,
        "5_15_km": 1.0,
        "15_30_km": 1.0,
        "30_60_km": 1.0,
        "60_plus_km": 1.0,
    },
}


def round_up_half(
    value: float,
) -> float:

    return round(
        math.ceil(
            max(
                float(value),
                0.0,
            )
            * 2.0
            - 1e-9
        )
        / 2.0,
        2,
    )


def distance_band(
    distance_km: float,
) -> str:

    distance = max(
        float(distance_km),
        0.0,
    )

    if distance <= 5:
        return "0_5_km"

    if distance <= 15:
        return "5_15_km"

    if distance <= 30:
        return "15_30_km"

    if distance <= 60:
        return "30_60_km"

    return "60_plus_km"


def choose_capacity_class(
    chargeable_weight_kg: float,
) -> dict:

    chargeable = max(
        float(
            chargeable_weight_kg
        ),
        0.0,
    )

    for item in CAPACITY_CLASSES:

        if (
            chargeable
            <= item[
                "planning_capacity_kg"
            ]
        ):
            return dict(
                item
            )


    return {
        "key":
            "heavy_project",

        "planning_capacity_kg":
            max(
                chargeable,
                20000.0,
            ),

        # No fixed CargoMov public quote exists for
        # very heavy/project freight.
        #
        # We use the 20-ft anchor only as a bootstrap
        # numerical floor. A live carrier quote remains
        # mandatory before customer pricing.
        "market_anchor_ghs":
            1300.0,
    }


@dataclass(
    frozen=True
)
class UpfrontDeliveryEstimate:

    engine_version: str

    capacity_class: str

    planning_capacity_kg: float

    public_market_anchor: float

    chargeable_weight_kg: float

    distance_band: str

    route_factor: float

    stop_factor: float

    utilization_factor: float

    handling_factor: float

    fragility_factor: float

    calibration_multiplier: float

    predicted_carrier_cost: float

    predicted_customer_price: float

    requires_live_quote: bool

    def to_dict(
        self
    ) -> dict:

        return asdict(
            self
        )


def estimate_upfront_delivery(
    *,
    distance_km: float,
    duration_minutes: float,
    supplier_count: int,

    total_load_units: float,
    total_weight_kg: float,
    total_volume_l: float,
    total_handling_score: float,
    total_fragility_score: float,

    coefficients: dict | None = None,
) -> UpfrontDeliveryEstimate:

    coefficients = (
        coefficients
        or DEFAULT_COEFFICIENTS
    )


    distance = max(
        float(distance_km),
        0.0,
    )

    duration = max(
        float(duration_minutes),
        0.0,
    )

    stops = max(
        int(supplier_count),
        1,
    )

    weight = max(
        float(total_weight_kg),
        0.0,
    )

    volume = max(
        float(total_volume_l),
        0.0,
    )

    handling = max(
        float(total_handling_score),
        0.0,
    )

    fragility = max(
        float(total_fragility_score),
        0.0,
    )


    volumetric_weight = (
        volume
        * VOLUMETRIC_KG_PER_L
    )


    chargeable_weight = max(
        weight,
        volumetric_weight,
    )


    capacity = (
        choose_capacity_class(
            chargeable_weight
        )
    )


    capacity_key = (
        capacity[
            "key"
        ]
    )

    planning_capacity = (
        float(
            capacity[
                "planning_capacity_kg"
            ]
        )
    )

    market_anchor = (
        float(
            capacity[
                "market_anchor_ghs"
            ]
        )
    )


    # --------------------------------------------------------
    # ROUTE
    #
    # Starting anchors are treated as local dispatch anchors.
    # Additional route burden grows continuously from there.
    # --------------------------------------------------------

    extra_distance = max(
        distance
        - 5.0,
        0.0,
    )

    extra_minutes = max(
        duration
        - 15.0,
        0.0,
    )


    route_factor = (
        1.0
        + float(
            coefficients.get(
                "route_extra_km_rate",
                0.035,
            )
        )
        * extra_distance

        + float(
            coefficients.get(
                "route_extra_minute_rate",
                0.010,
            )
        )
        * extra_minutes
    )


    route_factor = min(
        max(
            route_factor,
            1.0,
        ),
        2.50,
    )


    # --------------------------------------------------------
    # STOPS
    # --------------------------------------------------------

    stop_factor = (
        1.0
        + float(
            coefficients.get(
                "extra_stop_rate",
                0.08,
            )
        )
        * max(
            stops
            - 1,
            0,
        )
    )

    stop_factor = min(
        stop_factor,
        1.60,
    )


    # --------------------------------------------------------
    # CAPACITY UTILIZATION
    #
    # A nearly-full commercial vehicle should not price the
    # same as a lightly-loaded vehicle in the same broad class.
    # --------------------------------------------------------

    utilization = min(
        (
            chargeable_weight
            / planning_capacity
        )
        if planning_capacity
        else 0.0,
        1.50,
    )


    utilization_factor = (
        1.0
        + float(
            coefficients.get(
                "capacity_utilization_rate",
                0.35,
            )
        )
        * (
            utilization
            ** 2
        )
    )


    # --------------------------------------------------------
    # HANDLING
    #
    # Normalize against cargo scale so quantity does not
    # explode handling cost linearly.
    # --------------------------------------------------------

    handling_denominator = max(
        chargeable_weight
        / 50.0,
        1.0,
    )

    handling_density = (
        handling
        / handling_denominator
    )


    handling_factor = (
        1.0
        + float(
            coefficients.get(
                "handling_rate",
                0.05,
            )
        )
        * math.log1p(
            handling_density
        )
    )


    fragility_denominator = max(
        float(total_load_units),
        1.0,
    )

    fragility_density = (
        fragility
        / fragility_denominator
    )


    fragility_factor = (
        1.0
        + float(
            coefficients.get(
                "fragility_rate",
                0.04,
            )
        )
        * math.log1p(
            fragility_density
        )
    )


    band = distance_band(
        distance
    )


    global_multiplier = float(
        coefficients.get(
            "global_multiplier",
            1.0,
        )
    )


    capacity_multiplier = float(
        coefficients.get(
            "capacity_multipliers",
            {},
        ).get(
            capacity_key,
            1.0,
        )
    )


    distance_multiplier = float(
        coefficients.get(
            "distance_band_multipliers",
            {},
        ).get(
            band,
            1.0,
        )
    )


    calibration_multiplier = (
        global_multiplier
        * capacity_multiplier
        * distance_multiplier
    )


    predicted_carrier = (
        market_anchor
        * route_factor
        * stop_factor
        * utilization_factor
        * handling_factor
        * fragility_factor
        * calibration_multiplier
    )


    # Heavy project jobs deliberately get extra uncertainty.
    # They still REQUIRE a live quote before customer pricing.

    requires_live_quote = (
        capacity_key
        == "heavy_project"
    )


    if requires_live_quote:

        overage = max(
            (
                chargeable_weight
                / 14000.0
            )
            - 1.0,
            0.0,
        )

        predicted_carrier *= (
            1.0
            + 0.30
            * math.log1p(
                overage
            )
        )


    predicted_carrier = (
        round_up_half(
            predicted_carrier
        )
    )


    target_margin = float(
        coefficients.get(
            "target_margin",
            0.25,
        )
    )


    predicted_customer = (
        round_up_half(
            predicted_carrier
            /
            max(
                1.0
                - target_margin,
                0.01,
            )
        )
    )


    return UpfrontDeliveryEstimate(
        engine_version=
            MODEL_ENGINE_VERSION,

        capacity_class=
            capacity_key,

        planning_capacity_kg=
            planning_capacity,

        public_market_anchor=
            market_anchor,

        chargeable_weight_kg=
            round(
                chargeable_weight,
                3,
            ),

        distance_band=
            band,

        route_factor=
            round(
                route_factor,
                6,
            ),

        stop_factor=
            round(
                stop_factor,
                6,
            ),

        utilization_factor=
            round(
                utilization_factor,
                6,
            ),

        handling_factor=
            round(
                handling_factor,
                6,
            ),

        fragility_factor=
            round(
                fragility_factor,
                6,
            ),

        calibration_multiplier=
            round(
                calibration_multiplier,
                6,
            ),

        predicted_carrier_cost=
            predicted_carrier,

        predicted_customer_price=
            predicted_customer,

        requires_live_quote=
            requires_live_quote,
    )
