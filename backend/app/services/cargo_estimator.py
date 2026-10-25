from __future__ import annotations

import math
import re


PROFILE_VERSION = "ghana-deep-cargo-v2"


# ============================================================
# MATERIAL PHYSICS
#
# density:
# approximate kg per litre of actual product material.
#
# fill_ratio:
# how much of the transport envelope tends to be product.
#
# handling:
# baseline difficulty before package/weight effects.
#
# fragility:
# 0 = extremely robust
# 1 = extremely fragile
# ============================================================

MATERIALS = {
    "general": {
        "density": 0.35,
        "fill_ratio": 0.75,
        "handling": 0.8,
        "fragility": 0.20,
    },

    "water": {
        "density": 1.00,
        "fill_ratio": 0.94,
        "handling": 0.9,
        "fragility": 0.12,
    },

    "drink_liquid": {
        "density": 1.03,
        "fill_ratio": 0.92,
        "handling": 0.9,
        "fragility": 0.20,
    },

    "oil": {
        "density": 0.92,
        "fill_ratio": 0.93,
        "handling": 1.0,
        "fragility": 0.12,
    },

    "dairy_liquid": {
        "density": 1.03,
        "fill_ratio": 0.92,
        "handling": 0.9,
        "fragility": 0.18,
    },

    "dense_grain": {
        "density": 0.78,
        "fill_ratio": 0.94,
        "handling": 1.0,
        "fragility": 0.04,
    },

    "dense_powder": {
        "density": 0.68,
        "fill_ratio": 0.90,
        "handling": 1.0,
        "fragility": 0.06,
    },

    "light_dry": {
        "density": 0.18,
        "fill_ratio": 0.72,
        "handling": 0.7,
        "fragility": 0.16,
    },

    "canned_dense": {
        "density": 0.88,
        "fill_ratio": 0.74,
        "handling": 1.0,
        "fragility": 0.12,
    },

    "sauce_liquid": {
        "density": 1.05,
        "fill_ratio": 0.88,
        "handling": 0.9,
        "fragility": 0.18,
    },

    "snack_light": {
        "density": 0.10,
        "fill_ratio": 0.58,
        "handling": 0.6,
        "fragility": 0.28,
    },

    "bakery": {
        "density": 0.14,
        "fill_ratio": 0.70,
        "handling": 1.0,
        "fragility": 0.62,
    },

    "eggs": {
        "density": 0.24,
        "fill_ratio": 0.55,
        "handling": 1.5,
        "fragility": 0.98,
    },

    "frozen": {
        "density": 0.68,
        "fill_ratio": 0.86,
        "handling": 1.3,
        "fragility": 0.25,
    },

    "bulky_soft": {
        "density": 0.065,
        "fill_ratio": 0.82,
        "handling": 0.9,
        "fragility": 0.10,
    },

    "paper": {
        "density": 0.055,
        "fill_ratio": 0.78,
        "handling": 0.8,
        "fragility": 0.12,
    },

    "cleaning_liquid": {
        "density": 1.04,
        "fill_ratio": 0.92,
        "handling": 1.0,
        "fragility": 0.18,
    },

    "personal_liquid": {
        "density": 0.98,
        "fill_ratio": 0.84,
        "handling": 0.8,
        "fragility": 0.25,
    },

    "beauty_general": {
        "density": 0.55,
        "fill_ratio": 0.65,
        "handling": 0.7,
        "fragility": 0.32,
    },

    "hair_light": {
        "density": 0.045,
        "fill_ratio": 0.60,
        "handling": 0.7,
        "fragility": 0.20,
    },

    "appliance": {
        "density": 0.20,
        "fill_ratio": 0.52,
        "handling": 1.2,
        "fragility": 0.40,
    },
}


# ============================================================
# CATEGORY -> MATERIAL
# ============================================================

CATEGORY_MATERIAL = {
    "general_goods": "general",

    "soft_drinks": "drink_liquid",
    "water": "water",
    "juice": "drink_liquid",
    "malt_energy": "drink_liquid",

    "milk_dairy": "dairy_liquid",
    "powdered_drinks": "dense_powder",
    "tea_coffee_cocoa": "dense_powder",

    "rice_grains": "dense_grain",
    "flour_sugar_salt": "dense_powder",

    "pasta_noodles": "light_dry",
    "breakfast_cereal": "light_dry",

    "cooking_oil": "oil",
    "spreads": "dense_powder",

    "canned_foods": "canned_dense",
    "tomato_sauces": "sauce_liquid",
    "spices_seasoning": "dense_powder",

    "biscuits_snacks": "snack_light",
    "sweets_chocolate": "dense_powder",

    "bakery": "bakery",
    "eggs": "eggs",
    "frozen_food": "frozen",

    "baby_food": "dense_powder",
    "diapers_wipes": "bulky_soft",

    "laundry_cleaning": "cleaning_liquid",

    "tissue_paper": "paper",
    "disposables": "bulky_soft",

    "oral_care": "personal_liquid",
    "soap_bodywash": "personal_liquid",
    "personal_care": "personal_liquid",
    "skincare": "personal_liquid",
    "haircare": "personal_liquid",

    "fragrance": "beauty_general",
    "makeup": "beauty_general",
    "nails": "beauty_general",

    "hair_extensions": "hair_light",
    "beauty_tools": "general",
    "beauty_appliances": "appliance",
}


# ============================================================
# TRANSPORT ENVELOPE VOLUME BY PACKAGE AND SIZE
#
# These are not claimed product dimensions.
# They are priors used only when exact size/weight is unknown.
# ============================================================

PACKAGE_VOLUME_L = {
    "unit": {
        "small": 0.8,
        "medium": 3.0,
        "large": 10.0,
    },

    "sachet": {
        "small": 0.08,
        "medium": 0.25,
        "large": 0.55,
    },

    "packet": {
        "small": 0.35,
        "medium": 1.5,
        "large": 4.0,
    },

    "pouch": {
        "small": 0.25,
        "medium": 1.2,
        "large": 3.5,
    },

    "bag": {
        "small": 6.5,
        "medium": 15.0,
        "large": 30.0,
    },

    "sack": {
        "small": 15.0,
        "medium": 35.0,
        "large": 65.0,
    },

    "bottle": {
        "small": 0.55,
        "medium": 1.10,
        "large": 1.75,
    },

    "can": {
        "small": 0.35,
        "medium": 0.55,
        "large": 0.85,
    },

    "tin": {
        "small": 0.30,
        "medium": 0.65,
        "large": 1.25,
    },

    "pack": {
        "small": 4.0,
        "medium": 12.0,
        "large": 28.0,
    },

    "carton": {
        "small": 10.0,
        "medium": 30.0,
        "large": 70.0,
    },

    "box": {
        "small": 2.0,
        "medium": 8.0,
        "large": 25.0,
    },

    "crate": {
        "small": 12.0,
        "medium": 25.0,
        "large": 45.0,
    },

    "jar": {
        "small": 0.30,
        "medium": 0.80,
        "large": 2.0,
    },

    "tub": {
        "small": 0.55,
        "medium": 2.0,
        "large": 5.0,
    },

    "gallon": {
        "small": 2.7,
        "medium": 5.5,
        "large": 10.5,
    },

    "jerrycan": {
        "small": 5.5,
        "medium": 11.0,
        "large": 22.0,
    },

    "bucket": {
        "small": 5.5,
        "medium": 15.5,
        "large": 26.0,
    },

    "tray": {
        "small": 4.0,
        "medium": 8.0,
        "large": 15.0,
    },

    "half_tray": {
        "small": 3.5,
        "medium": 4.5,
        "large": 6.0,
    },

    "bale": {
        "small": 55.0,
        "medium": 120.0,
        "large": 240.0,
    },

    "roll": {
        "small": 1.5,
        "medium": 4.0,
        "large": 9.0,
    },

    "loaf": {
        "small": 2.5,
        "medium": 4.5,
        "large": 7.5,
    },

    "bar": {
        "small": 0.10,
        "medium": 0.25,
        "large": 0.55,
    },
}


PACKAGE_TARE_KG = {
    "unit": 0.02,
    "sachet": 0.005,
    "packet": 0.015,
    "pouch": 0.02,
    "bag": 0.08,
    "sack": 0.16,

    "bottle": 0.06,
    "can": 0.03,
    "tin": 0.05,

    "pack": 0.15,
    "carton": 0.35,
    "box": 0.18,
    "crate": 1.20,

    "jar": 0.12,
    "tub": 0.08,

    "gallon": 0.25,
    "jerrycan": 0.55,
    "bucket": 0.45,

    "tray": 0.15,
    "half_tray": 0.10,

    "bale": 0.35,
    "roll": 0.02,
    "loaf": 0.02,
    "bar": 0.005,
}


PACKAGE_HANDLING = {
    "unit": 0.25,
    "sachet": 0.10,
    "packet": 0.20,
    "pouch": 0.20,

    "bag": 0.75,
    "sack": 1.40,

    "bottle": 0.35,
    "can": 0.25,
    "tin": 0.30,

    "pack": 0.65,
    "carton": 0.85,
    "box": 0.60,
    "crate": 1.30,

    "jar": 0.45,
    "tub": 0.35,

    "gallon": 0.95,
    "jerrycan": 1.25,
    "bucket": 1.10,

    "tray": 1.20,
    "half_tray": 1.00,

    "bale": 1.35,

    "roll": 0.35,
    "loaf": 0.45,
    "bar": 0.10,
}


PACKAGE_FRAGILITY = {
    "bottle": 0.20,
    "jar": 0.28,
    "crate": 0.12,
    "tray": 0.30,
    "half_tray": 0.30,

    "carton": 0.08,
    "box": 0.08,

    "bag": 0.03,
    "sack": 0.02,

    "bale": 0.01,
}


# ============================================================
# NORMALIZATION
# ============================================================

def _normalize(
    value: str | None,
) -> str:
    if not value:
        return ""

    return " ".join(
        str(value)
        .strip()
        .casefold()
        .replace("×", "x")
        .split()
    )


def _size_key(
    size_class: str | None,
) -> str:
    value = _normalize(
        size_class
    )

    if value == "small":
        return "small"

    if value == "large":
        return "large"

    return "medium"


# ============================================================
# MEASUREMENT PARSING
# ============================================================

MASS_FACTORS = {
    "kg": 1.0,
    "kgs": 1.0,
    "kilogram": 1.0,
    "kilograms": 1.0,

    "g": 0.001,
    "gram": 0.001,
    "grams": 0.001,
}


VOLUME_FACTORS = {
    "l": 1.0,
    "lt": 1.0,
    "ltr": 1.0,
    "litre": 1.0,
    "litres": 1.0,
    "liter": 1.0,
    "liters": 1.0,

    "ml": 0.001,

    "cl": 0.01,
}


MEASURE_UNITS = (
    r"kg|kgs|kilogram|kilograms|"
    r"g|gram|grams|"
    r"ml|cl|"
    r"l|lt|ltr|litre|litres|liter|liters"
)


def _convert_measurement(
    value: float,
    unit: str,
):
    unit = unit.casefold()

    if unit in MASS_FACTORS:
        return (
            "mass",
            value
            * MASS_FACTORS[
                unit
            ],
        )

    if unit in VOLUME_FACTORS:
        return (
            "volume",
            value
            * VOLUME_FACTORS[
                unit
            ],
        )

    return (
        None,
        None,
    )


def _parse_measurements(
    text: str,
):
    """
    Returns:
        explicit_mass_kg,
        explicit_volume_l,
        used_multipack
    """

    text = _normalize(
        text
    )

    mass = None
    volume = None
    used_multipack = False


    # 24 x 500ml
    # 30 x 500 g
    pattern_a = re.compile(
        rf"\b(\d{{1,4}})\s*x\s*"
        rf"(\d+(?:\.\d+)?)\s*"
        rf"({MEASURE_UNITS})\b"
    )


    # 500ml x 24
    pattern_b = re.compile(
        rf"\b(\d+(?:\.\d+)?)\s*"
        rf"({MEASURE_UNITS})\s*x\s*"
        rf"(\d{{1,4}})\b"
    )


    match = pattern_a.search(
        text
    )

    if match:
        count = int(
            match.group(1)
        )

        value = float(
            match.group(2)
        )

        unit = (
            match.group(3)
            .casefold()
        )

        kind, converted = (
            _convert_measurement(
                value,
                unit,
            )
        )

        if kind == "mass":
            mass = (
                converted
                * count
            )

        elif kind == "volume":
            volume = (
                converted
                * count
            )

        used_multipack = True


    if not used_multipack:
        match = pattern_b.search(
            text
        )

        if match:
            value = float(
                match.group(1)
            )

            unit = (
                match.group(2)
                .casefold()
            )

            count = int(
                match.group(3)
            )

            kind, converted = (
                _convert_measurement(
                    value,
                    unit,
                )
            )

            if kind == "mass":
                mass = (
                    converted
                    * count
                )

            elif kind == "volume":
                volume = (
                    converted
                    * count
                )

            used_multipack = True


    # Ordinary single measurement.
    # Example: 5kg rice bag
    # Example: cooking oil 5L

    if mass is None:
        pattern = re.compile(
            r"\b(\d+(?:\.\d+)?)\s*"
            r"(kg|kgs|kilogram|kilograms|g|gram|grams)\b"
        )

        match = pattern.search(
            text
        )

        if match:
            kind, converted = (
                _convert_measurement(
                    float(
                        match.group(1)
                    ),
                    match.group(2),
                )
            )

            if kind == "mass":
                mass = converted


    if volume is None:
        pattern = re.compile(
            r"\b(\d+(?:\.\d+)?)\s*"
            r"(ml|cl|l|lt|ltr|litre|litres|liter|liters)\b"
        )

        match = pattern.search(
            text
        )

        if match:
            kind, converted = (
                _convert_measurement(
                    float(
                        match.group(1)
                    ),
                    match.group(2),
                )
            )

            if kind == "volume":
                volume = converted


    return (
        mass,
        volume,
        used_multipack,
    )


# ============================================================
# MATERIAL RESOLUTION
# ============================================================

def _resolve_material(
    category_code: str,
    package_type: str,
    text: str,
) -> str:

    category_code = _normalize(
        category_code
    )

    package_type = _normalize(
        package_type
    )

    text = _normalize(
        text
    )


    # Cleaning can be liquid OR powder.
    if category_code == "laundry_cleaning":

        if (
            package_type
            in {
                "bottle",
                "gallon",
                "jerrycan",
                "bucket",
            }
            or
            any(
                word in text
                for word in {
                    "bleach",
                    "liquid",
                    "dishwash",
                }
            )
        ):
            return "cleaning_liquid"

        return "dense_powder"


    # Milk can be liquid or powdered.
    if category_code == "milk_dairy":

        if any(
            word in text
            for word in {
                "powder",
                "powdered",
                "formula",
            }
        ):
            return "dense_powder"

        return "dairy_liquid"


    # Tea / coffee / cocoa can vary.
    if category_code == "tea_coffee_cocoa":

        if (
            package_type
            in {
                "bottle",
            }
            or "drink" in text
        ):
            return "drink_liquid"

        return "dense_powder"


    # Tomato category may eventually include
    # fresh produce. Detect obvious fresh wording.
    if category_code == "tomato_sauces":

        if any(
            word in text
            for word in {
                "fresh tomato",
                "fresh tomatoes",
                "tomato basket",
            }
        ):
            return "general"

        return "sauce_liquid"


    return CATEGORY_MATERIAL.get(
        category_code,
        "general",
    )


# ============================================================
# SPECIAL HIGH-VALUE PROFILES
# ============================================================

def _special_profile(
    *,
    category_code: str,
    package_type: str,
    size_class: str,
    text: str,
    explicit_mass: float | None,
    explicit_volume: float | None,
):

    # --------------------------------------------------------
    # SACHET WATER BAG
    #
    # Typical bag is usually count x sachet volume.
    # If the text gives exact ml x count, the parser above
    # takes priority and this is skipped.
    # --------------------------------------------------------

    if (
        category_code == "water"
        and package_type == "bag"
        and explicit_mass is None
        and explicit_volume is None
    ):

        volumes = {
            "small": 10.0,
            "medium": 15.0,
            "large": 20.0,
        }

        volume = volumes[
            size_class
        ]

        return {
            "weight": (
                volume
                + 0.20
            ),

            "volume": (
                volume
                * 1.10
            ),

            "handling": {
                "small": 1.7,
                "medium": 2.3,
                "large": 2.8,
            }[
                size_class
            ],

            "fragility": 0.15,

            "confidence": 0.84,

            "source":
                "water_sachet_bag_prior",
        }


    # --------------------------------------------------------
    # EGGS
    # --------------------------------------------------------

    if (
        category_code == "eggs"
        and package_type
        in {
            "tray",
            "half_tray",
        }
        and explicit_mass is None
        and explicit_volume is None
    ):

        if package_type == "half_tray":
            count = 15
        else:
            count = {
                "small": 15,
                "medium": 30,
                "large": 30,
            }[
                size_class
            ]


        weight = (
            count * 0.060
            + 0.15
        )

        volume = (
            count * 0.24
        )


        return {
            "weight":
                weight,

            "volume":
                volume,

            "handling":
                2.8,

            "fragility":
                0.98,

            "confidence":
                0.88,

            "source":
                "egg_tray_prior",
        }


    # --------------------------------------------------------
    # BREAD LOAF
    # --------------------------------------------------------

    if (
        category_code == "bakery"
        and package_type == "loaf"
        and explicit_mass is None
        and explicit_volume is None
    ):

        return {
            "weight": {
                "small": 0.35,
                "medium": 0.60,
                "large": 0.95,
            }[
                size_class
            ],

            "volume": {
                "small": 2.5,
                "medium": 4.5,
                "large": 7.0,
            }[
                size_class
            ],

            "handling":
                1.5,

            "fragility":
                0.62,

            "confidence":
                0.78,

            "source":
                "bread_loaf_prior",
        }


    return None


# ============================================================
# DYNAMIC LOAD SCORE
# ============================================================

def _dynamic_load_units(
    *,
    weight_kg: float,
    volume_l: float,
    handling: float,
    fragility: float,
) -> float:
    """
    Continuous cargo burden.

    Weight is strongest.
    Volume is second.
    Handling remains meaningful.
    Fragility affects the score but does not dominate.

    This replaces crude package constants such as:
        bag = 5
        sack = 9
    at the ORDER ITEM level.
    """

    power = 1.35


    components = [
        (
            0.45,
            max(
                weight_kg
                / 5.0,
                0.01,
            ),
        ),

        (
            0.30,
            max(
                volume_l
                / 12.0,
                0.01,
            ),
        ),

        (
            0.20,
            max(
                handling
                / 2.0,
                0.01,
            ),
        ),

        (
            0.05,
            max(
                fragility
                / 0.50,
                0.01,
            ),
        ),
    ]


    pressure = (
        sum(
            weight
            * (
                value
                ** power
            )
            for (
                weight,
                value,
            )
            in components
        )
        ** (
            1.0
            / power
        )
    )


    units = (
        pressure
        * 2.0
    )


    return round(
        max(
            0.25,
            min(
                units,
                40.0,
            ),
        ),
        2,
    )


# ============================================================
# MAIN ESTIMATOR
# ============================================================

def estimate_cargo_profile(
    *,
    product_name: str,
    category_code: str,
    package_type: str | None,
    size_class: str | None,
    size_text: str | None = None,
    type_name: str | None = None,
    brand: str | None = None,
):
    size_key = _size_key(
        size_class
    )


    package = _normalize(
        package_type
    ) or "unit"


    combined_text = " ".join(
        part
        for part in [
            product_name,
            brand or "",
            size_text or "",
            type_name or "",
            package,
        ]
        if part
    )


    normalized_text = (
        _normalize(
            combined_text
        )
    )


    (
        explicit_mass,
        explicit_volume,
        used_multipack,
    ) = _parse_measurements(
        normalized_text
    )


    material_name = (
        _resolve_material(
            category_code,
            package,
            normalized_text,
        )
    )


    material = MATERIALS[
        material_name
    ]


    special = _special_profile(
        category_code=
            _normalize(
                category_code
            ),

        package_type=
            package,

        size_class=
            size_key,

        text=
            normalized_text,

        explicit_mass=
            explicit_mass,

        explicit_volume=
            explicit_volume,
    )


    if special:

        weight = float(
            special[
                "weight"
            ]
        )

        volume = float(
            special[
                "volume"
            ]
        )

        handling = float(
            special[
                "handling"
            ]
        )

        fragility = float(
            special[
                "fragility"
            ]
        )

        confidence = float(
            special[
                "confidence"
            ]
        )

        source = str(
            special[
                "source"
            ]
        )


    else:

        density = float(
            material[
                "density"
            ]
        )

        fill_ratio = float(
            material[
                "fill_ratio"
            ]
        )

        tare = float(
            PACKAGE_TARE_KG.get(
                package,
                0.08,
            )
        )


        prior_volume = (
            PACKAGE_VOLUME_L
            .get(
                package,
                PACKAGE_VOLUME_L[
                    "unit"
                ],
            )
            .get(
                size_key,
                3.0,
            )
        )


        # ====================================================
        # BOTH KNOWN
        # ====================================================

        if (
            explicit_mass
            is not None
            and
            explicit_volume
            is not None
        ):

            weight = (
                explicit_mass
                + tare
            )

            # Add a small transport-envelope allowance.
            volume = (
                explicit_volume
                * 1.08
            )

            confidence = (
                0.98
            )

            source = (
                "explicit_mass_and_volume"
            )


        # ====================================================
        # EXACT / STATED MASS
        # ====================================================

        elif (
            explicit_mass
            is not None
        ):

            weight = (
                explicit_mass
                + tare
            )


            estimated_material_volume = (
                explicit_mass
                / max(
                    density,
                    0.03,
                )
            )


            volume = max(
                estimated_material_volume
                * 1.08,

                min(
                    prior_volume,
                    estimated_material_volume
                    * 1.45,
                ),
            )


            confidence = (
                0.96
                if used_multipack
                else 0.94
            )


            source = (
                "explicit_multipack_mass"
                if used_multipack
                else
                "explicit_mass"
            )


        # ====================================================
        # EXACT / STATED VOLUME
        # ====================================================

        elif (
            explicit_volume
            is not None
        ):

            volume = (
                explicit_volume
                * 1.10
            )


            weight = (
                explicit_volume
                * density
                + tare
            )


            confidence = (
                0.95
                if used_multipack
                else 0.91
            )


            source = (
                "explicit_multipack_volume"
                if used_multipack
                else
                "explicit_volume"
            )


        # ====================================================
        # MATERIAL + PACKAGE + SIZE ESTIMATION
        # ====================================================

        else:

            volume = float(
                prior_volume
            )


            weight = (
                volume
                * density
                * fill_ratio
                + tare
            )


            confidence = (
                0.74
                if package != "unit"
                else 0.56
            )


            source = (
                "material_package_size_prior"
                if package != "unit"
                else
                "category_size_fallback"
            )


        # ====================================================
        # HANDLING
        # ====================================================

        handling = (
            float(
                material[
                    "handling"
                ]
            )

            + float(
                PACKAGE_HANDLING.get(
                    package,
                    0.40,
                )
            )

            + (
                math.log1p(
                    max(
                        weight,
                        0,
                    )
                    / 5.0
                )
                * 0.55
            )

            + (
                math.log1p(
                    max(
                        volume,
                        0,
                    )
                    / 20.0
                )
                * 0.28
            )
        )


        handling = max(
            0.5,
            min(
                handling,
                7.0,
            ),
        )


        fragility = max(
            float(
                material[
                    "fragility"
                ]
            ),

            float(
                PACKAGE_FRAGILITY.get(
                    package,
                    0.0,
                )
            ),
        )


        # Glass detection.
        if "glass" in normalized_text:
            fragility = max(
                fragility,
                0.72,
            )


    load_units = (
        _dynamic_load_units(
            weight_kg=
                weight,

            volume_l=
                volume,

            handling=
                handling,

            fragility=
                fragility,
        )
    )


    return {
        "profile_version":
            PROFILE_VERSION,

        "category_code":
            _normalize(
                category_code
            ),

        "material_class":
            material_name,

        "package_type":
            package,

        "size_class":
            size_key,

        "weight_kg_each":
            round(
                weight,
                3,
            ),

        "volume_l_each":
            round(
                volume,
                3,
            ),

        "handling_score_each":
            round(
                handling,
                3,
            ),

        "fragility_score_each":
            round(
                fragility,
                3,
            ),

        "load_units_each":
            load_units,

        "confidence":
            round(
                confidence,
                3,
            ),

        "estimation_source":
            source,

        "explicit_mass_found":
            (
                explicit_mass
                is not None
            ),

        "explicit_volume_found":
            (
                explicit_volume
                is not None
            ),

        "multipack_found":
            used_multipack,
    }
