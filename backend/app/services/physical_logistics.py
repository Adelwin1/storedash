import math


PHYSICAL_PROFILE_VERSION = "ghana-physical-v1"


# weight kg, cargo volume litres,
# handling score, fragility 0..1
PACKAGE_PROFILES = {
    "unit": (1.0, 2.0, 1.0, 0.15),

    "bottle": (1.2, 1.5, 1.0, 0.25),
    "can": (0.4, 0.5, 0.8, 0.15),
    "tin": (1.0, 1.2, 1.0, 0.10),

    "sachet": (0.25, 0.4, 0.7, 0.05),
    "pouch": (0.5, 0.8, 0.8, 0.05),
    "packet": (1.0, 1.5, 1.0, 0.05),

    "pack": (5.0, 10.0, 1.5, 0.15),
    "box": (3.0, 8.0, 1.5, 0.20),
    "carton": (10.0, 22.0, 2.0, 0.20),

    "bag": (10.0, 18.0, 2.5, 0.10),
    "sack": (25.0, 38.0, 4.0, 0.05),

    "crate": (18.0, 30.0, 3.0, 0.35),

    "tray": (5.0, 12.0, 2.5, 0.60),
    "half_tray": (2.5, 6.0, 2.0, 0.60),

    "gallon": (5.0, 6.0, 2.0, 0.10),
    "jerrycan": (18.0, 22.0, 3.0, 0.05),
    "bucket": (15.0, 18.0, 2.5, 0.10),

    "jar": (0.8, 1.0, 1.0, 0.25),
    "tub": (1.0, 2.0, 1.0, 0.15),

    "bar": (0.1, 0.2, 0.4, 0.05),
    "loaf": (0.5, 2.0, 1.0, 0.20),

    "roll": (0.5, 3.0, 1.0, 0.05),

    "bale": (12.0, 80.0, 3.0, 0.10),
}


# Multipliers alter physical characteristics,
# NOT delivery prices.
#
# weight, volume, handling, fragility override
CATEGORY_ADJUSTMENTS = {
    "water": (1.35, 1.00, 1.10, 0.10),

    "rice_grains": (1.80, 0.90, 1.35, 0.05),

    "flour_sugar_salt":
        (1.70, 0.90, 1.35, 0.05),

    "eggs":
        (0.55, 1.25, 1.50, 0.95),

    "tissue_paper":
        (0.35, 2.40, 1.10, 0.10),

    "diapers_wipes":
        (0.40, 2.00, 1.10, 0.10),

    "soft_drinks":
        (1.15, 1.00, 1.15, 0.35),

    "malt_energy":
        (1.15, 1.00, 1.15, 0.35),

    "milk_dairy":
        (1.10, 1.00, 1.10, 0.20),

    "cooking_oil":
        (1.40, 1.00, 1.20, 0.10),

    "frozen_food":
        (1.20, 1.00, 1.40, 0.25),
}


SIZE_MULTIPLIERS = {
    "small": 0.70,
    "medium": 1.00,
    "large": 1.55,
}


def estimate_physical_profile(
    *,
    category_code: str,
    package_type: str | None,
    size_class: str,
    load_units: float,

    weight_kg_each: float | None = None,
    volume_l_each: float | None = None,
    handling_score_each: float | None = None,
    fragility_score_each: float | None = None,
) -> dict:

    load = max(
        float(load_units),
        0.1,
    )

    package = (
        (package_type or "unit")
        .strip()
        .lower()
    )

    if package in PACKAGE_PROFILES:
        base_weight, base_volume, base_handling, base_fragility = (
            PACKAGE_PROFILES[package]
        )
    else:
        # Continuous generic fallback.
        base_weight = max(
            0.5,
            load * 2.0,
        )

        base_volume = max(
            1.0,
            load * 4.0,
        )

        base_handling = max(
            0.8,
            0.8 + math.sqrt(load) * 0.7,
        )

        base_fragility = 0.15

    adjustment = CATEGORY_ADJUSTMENTS.get(
        category_code,
        (1.0, 1.0, 1.0, base_fragility),
    )

    weight_factor, volume_factor, handling_factor, category_fragility = (
        adjustment
    )

    size_factor = SIZE_MULTIPLIERS.get(
        size_class,
        1.0,
    )

    weight = (
        float(weight_kg_each)
        if weight_kg_each is not None
        else
        base_weight
        * weight_factor
        * size_factor
    )

    volume = (
        float(volume_l_each)
        if volume_l_each is not None
        else
        base_volume
        * volume_factor
        * size_factor
    )

    handling = (
        float(handling_score_each)
        if handling_score_each is not None
        else
        base_handling
        * handling_factor
        * math.sqrt(size_factor)
    )

    fragility = (
        float(fragility_score_each)
        if fragility_score_each is not None
        else
        max(
            base_fragility,
            category_fragility,
        )
    )

    return {
        "weight_kg_each":
            round(weight, 3),

        "volume_l_each":
            round(volume, 3),

        "handling_score_each":
            round(handling, 3),

        "fragility_score_each":
            round(
                min(max(fragility, 0.0), 1.0),
                3,
            ),

        "version":
            PHYSICAL_PROFILE_VERSION,
    }
