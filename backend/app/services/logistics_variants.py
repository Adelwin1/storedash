from __future__ import annotations


def v(
    key: str,
    label: str,
    physical_size_text: str = "",
    size_class: str = "medium",
):
    return {
        "key": key,
        "label": label,
        "physical_size_text": physical_size_text,
        "size_class": size_class,
    }


# ============================================================
# GENERIC PHYSICAL VARIANTS
#
# These are fallbacks for package types across categories.
# Category-specific variants below override these.
# ============================================================

GENERIC = {
    "sachet": [
        v("sachet_25g", "25 g sachet", "25g", "small"),
        v("sachet_50g", "50 g sachet", "50g", "small"),
        v("sachet_100g", "100 g sachet", "100g", "small"),
        v("sachet_250g", "250 g sachet", "250g", "medium"),
        v("sachet_500g", "500 g sachet", "500g", "large"),
    ],

    "packet": [
        v("packet_100g", "100 g packet", "100g", "small"),
        v("packet_250g", "250 g packet", "250g", "small"),
        v("packet_500g", "500 g packet", "500g", "medium"),
        v("packet_1kg", "1 kg packet", "1kg", "medium"),
        v("packet_2kg", "2 kg packet", "2kg", "large"),
        v("packet_5kg", "5 kg packet", "5kg", "large"),
    ],

    "pouch": [
        v("pouch_100g", "100 g pouch", "100g", "small"),
        v("pouch_250g", "250 g pouch", "250g", "small"),
        v("pouch_500g", "500 g pouch", "500g", "medium"),
        v("pouch_1kg", "1 kg pouch", "1kg", "large"),
        v("pouch_2kg", "2 kg pouch", "2kg", "large"),
    ],

    "bag": [
        v("bag_1kg", "1 kg bag", "1kg", "small"),
        v("bag_2kg", "2 kg bag", "2kg", "small"),
        v("bag_5kg", "5 kg bag", "5kg", "medium"),
        v("bag_10kg", "10 kg bag", "10kg", "medium"),
        v("bag_15kg", "15 kg bag", "15kg", "large"),
        v("bag_20kg", "20 kg bag", "20kg", "large"),
        v("bag_25kg", "25 kg bag", "25kg", "large"),
    ],

    "sack": [
        v("sack_10kg", "10 kg sack", "10kg", "small"),
        v("sack_25kg", "25 kg sack", "25kg", "medium"),
        v("sack_50kg", "50 kg sack", "50kg", "large"),
        v("sack_100kg", "100 kg sack", "100kg", "large"),
    ],

    "bottle": [
        v("bottle_200ml", "200 ml bottle", "200ml", "small"),
        v("bottle_250ml", "250 ml bottle", "250ml", "small"),
        v("bottle_330ml", "330 ml bottle", "330ml", "small"),
        v("bottle_500ml", "500 ml bottle", "500ml", "small"),
        v("bottle_750ml", "750 ml bottle", "750ml", "medium"),
        v("bottle_1l", "1 L bottle", "1L", "medium"),
        v("bottle_1_5l", "1.5 L bottle", "1.5L", "large"),
        v("bottle_2l", "2 L bottle", "2L", "large"),
        v("bottle_5l", "5 L bottle", "5L", "large"),
    ],

    "can": [
        v("can_250ml", "250 ml can", "250ml", "small"),
        v("can_330ml", "330 ml can", "330ml", "medium"),
        v("can_500ml", "500 ml can", "500ml", "large"),
    ],

    "tin": [
        v("tin_100g", "100 g tin", "100g", "small"),
        v("tin_150g", "150 g tin", "150g", "small"),
        v("tin_400g", "400 g tin", "400g", "medium"),
        v("tin_800g", "800 g tin", "800g", "large"),
        v("tin_1kg", "1 kg tin", "1kg", "large"),
    ],

    "jar": [
        v("jar_250g", "250 g jar", "250g", "small"),
        v("jar_500g", "500 g jar", "500g", "medium"),
        v("jar_1kg", "1 kg jar", "1kg", "large"),
    ],

    "gallon": [
        v("gallon_2_5l", "2.5 L gallon", "2.5L", "small"),
        v("gallon_5l", "5 L gallon", "5L", "medium"),
        v("gallon_10l", "10 L gallon", "10L", "large"),
    ],

    "jerrycan": [
        v("jerrycan_5l", "5 L jerrycan", "5L", "small"),
        v("jerrycan_10l", "10 L jerrycan", "10L", "medium"),
        v("jerrycan_20l", "20 L jerrycan", "20L", "large"),
        v("jerrycan_25l", "25 L jerrycan", "25L", "large"),
    ],

    "bucket": [
        v("bucket_5l", "5 L bucket", "5L", "small"),
        v("bucket_10l", "10 L bucket", "10L", "medium"),
        v("bucket_20l", "20 L bucket", "20L", "large"),
    ],

    "pack": [
        v("pack_small", "Small pack", "", "small"),
        v("pack_medium", "Medium pack", "", "medium"),
        v("pack_large", "Large pack", "", "large"),
    ],

    "carton": [
        v("carton_small", "Small carton", "", "small"),
        v("carton_medium", "Medium carton", "", "medium"),
        v("carton_large", "Large carton", "", "large"),
    ],

    "box": [
        v("box_small", "Small box", "", "small"),
        v("box_medium", "Medium box", "", "medium"),
        v("box_large", "Large box", "", "large"),
    ],

    "crate": [
        v("crate_small", "Small crate", "", "small"),
        v("crate_medium", "Medium crate", "", "medium"),
        v("crate_large", "Large crate", "", "large"),
    ],

    "tray": [
        v("tray_small", "Small tray", "", "small"),
        v("tray_medium", "Standard tray", "", "medium"),
        v("tray_large", "Large tray", "", "large"),
    ],

    "half_tray": [
        v("half_tray", "Half tray", "", "small"),
    ],

    "bale": [
        v("bale_small", "Small bale", "", "small"),
        v("bale_medium", "Medium bale", "", "medium"),
        v("bale_large", "Large bale", "", "large"),
    ],

    "roll": [
        v("roll_small", "Small roll", "", "small"),
        v("roll_medium", "Medium roll", "", "medium"),
        v("roll_large", "Large roll", "", "large"),
    ],

    "loaf": [
        v("loaf_350g", "350 g loaf", "350g", "small"),
        v("loaf_500g", "500 g loaf", "500g", "medium"),
        v("loaf_800g", "800 g loaf", "800g", "large"),
        v("loaf_1kg", "1 kg loaf", "1kg", "large"),
    ],

    "bar": [
        v("bar_small", "Small bar", "", "small"),
        v("bar_medium", "Medium bar", "", "medium"),
        v("bar_large", "Large bar", "", "large"),
    ],
}


# ============================================================
# CATEGORY-SPECIFIC OVERRIDES
# ============================================================

CATEGORY_OVERRIDES = {

    # --------------------------------------------------------
    # RICE / GRAINS / PULSES
    # --------------------------------------------------------

    "rice_grains": {
        "packet": [
            v("grain_packet_500g", "500 g packet", "500g", "small"),
            v("grain_packet_1kg", "1 kg packet", "1kg", "small"),
            v("grain_packet_2kg", "2 kg packet", "2kg", "medium"),
            v("grain_packet_5kg", "5 kg packet", "5kg", "large"),
        ],

        "bag": [
            v("grain_bag_2kg", "2 kg bag", "2kg", "small"),
            v("grain_bag_5kg", "5 kg bag", "5kg", "small"),
            v("grain_bag_10kg", "10 kg bag", "10kg", "medium"),
            v("grain_bag_15kg", "15 kg bag", "15kg", "medium"),
            v("grain_bag_20kg", "20 kg bag", "20kg", "large"),
            v("grain_bag_25kg", "25 kg bag", "25kg", "large"),
        ],

        "sack": [
            v("grain_sack_10kg", "10 kg sack", "10kg", "small"),
            v("grain_sack_25kg", "25 kg sack", "25kg", "medium"),
            v("grain_sack_50kg", "50 kg sack", "50kg", "large"),
            v("grain_sack_100kg", "100 kg sack", "100kg", "large"),
        ],
    },


    # --------------------------------------------------------
    # FLOUR / SUGAR / SALT
    # --------------------------------------------------------

    "flour_sugar_salt": {
        "packet": [
            v("dense_packet_500g", "500 g packet", "500g", "small"),
            v("dense_packet_1kg", "1 kg packet", "1kg", "small"),
            v("dense_packet_2kg", "2 kg packet", "2kg", "medium"),
            v("dense_packet_5kg", "5 kg packet", "5kg", "large"),
        ],

        "bag": [
            v("dense_bag_2kg", "2 kg bag", "2kg", "small"),
            v("dense_bag_5kg", "5 kg bag", "5kg", "small"),
            v("dense_bag_10kg", "10 kg bag", "10kg", "medium"),
            v("dense_bag_20kg", "20 kg bag", "20kg", "large"),
            v("dense_bag_25kg", "25 kg bag", "25kg", "large"),
        ],

        "sack": [
            v("dense_sack_25kg", "25 kg sack", "25kg", "medium"),
            v("dense_sack_50kg", "50 kg sack", "50kg", "large"),
            v("dense_sack_100kg", "100 kg sack", "100kg", "large"),
        ],
    },


    # --------------------------------------------------------
    # WATER
    # --------------------------------------------------------

    "water": {
        "bottle": [
            v("water_330ml", "330 ml bottle", "330ml", "small"),
            v("water_500ml", "500 ml bottle", "500ml", "small"),
            v("water_750ml", "750 ml bottle", "750ml", "medium"),
            v("water_1l", "1 L bottle", "1L", "medium"),
            v("water_1_5l", "1.5 L bottle", "1.5L", "large"),
            v("water_2l", "2 L bottle", "2L", "large"),
        ],

        "bag": [
            v(
                "sachet_water_30x500",
                "30 × 500 ml sachet bag",
                "30 x 500ml",
                "medium",
            ),
        ],

        "pack": [
            v("water_6x1_5l", "6 × 1.5 L", "6 x 1.5L", "medium"),
            v("water_12x500", "12 × 500 ml", "12 x 500ml", "small"),
            v("water_24x500", "24 × 500 ml", "24 x 500ml", "medium"),
            v("water_24x750", "24 × 750 ml", "24 x 750ml", "large"),
        ],
    },


    # --------------------------------------------------------
    # SOFT DRINKS
    # --------------------------------------------------------

    "soft_drinks": {
        "pack": [
            v("drink_6x330", "6 × 330 ml", "6 x 330ml", "small"),
            v("drink_6x500", "6 × 500 ml", "6 x 500ml", "small"),
            v("drink_12x330", "12 × 330 ml", "12 x 330ml", "medium"),
            v("drink_12x500", "12 × 500 ml", "12 x 500ml", "medium"),
            v("drink_24x330", "24 × 330 ml", "24 x 330ml", "large"),
            v("drink_24x500", "24 × 500 ml", "24 x 500ml", "large"),
        ],

        "carton": [
            v("drink_carton_12x1l", "12 × 1 L", "12 x 1L", "medium"),
            v("drink_carton_24x330", "24 × 330 ml", "24 x 330ml", "medium"),
            v("drink_carton_24x500", "24 × 500 ml", "24 x 500ml", "large"),
        ],

        "crate": [
            v("drink_crate_small", "Small drink crate", "", "small"),
            v("drink_crate_standard", "Standard drink crate", "", "medium"),
            v("drink_crate_large", "Large drink crate", "", "large"),
        ],
    },


    # --------------------------------------------------------
    # JUICE / MALT / ENERGY
    # --------------------------------------------------------

    "juice": {
        "pack": [
            v("juice_6x1l", "6 × 1 L", "6 x 1L", "medium"),
            v("juice_12x500", "12 × 500 ml", "12 x 500ml", "medium"),
            v("juice_24x250", "24 × 250 ml", "24 x 250ml", "medium"),
        ],
    },

    "malt_energy": {
        "pack": [
            v("malt_6x330", "6 × 330 ml", "6 x 330ml", "small"),
            v("malt_12x330", "12 × 330 ml", "12 x 330ml", "medium"),
            v("malt_24x330", "24 × 330 ml", "24 x 330ml", "large"),
            v("energy_24x500", "24 × 500 ml", "24 x 500ml", "large"),
        ],
    },


    # --------------------------------------------------------
    # COOKING OIL
    # --------------------------------------------------------

    "cooking_oil": {
        "bottle": [
            v("oil_500ml", "500 ml bottle", "500ml", "small"),
            v("oil_1l", "1 L bottle", "1L", "small"),
            v("oil_2l", "2 L bottle", "2L", "medium"),
            v("oil_5l", "5 L bottle", "5L", "large"),
        ],

        "gallon": [
            v("oil_gallon_5l", "5 L gallon", "5L", "medium"),
            v("oil_gallon_10l", "10 L gallon", "10L", "large"),
        ],

        "jerrycan": [
            v("oil_jerry_5l", "5 L jerrycan", "5L", "small"),
            v("oil_jerry_10l", "10 L jerrycan", "10L", "medium"),
            v("oil_jerry_20l", "20 L jerrycan", "20L", "large"),
            v("oil_jerry_25l", "25 L jerrycan", "25L", "large"),
        ],
    },


    # --------------------------------------------------------
    # EGGS
    # --------------------------------------------------------

    "eggs": {
        "half_tray": [
            v("eggs_15_half", "15 eggs / half tray", "", "small"),
        ],

        "tray": [
            v("eggs_15", "15-egg tray", "", "small"),
            v("eggs_30", "30-egg tray", "", "medium"),
        ],

        "crate": [
            v("eggs_crate_small", "Small egg crate", "", "small"),
            v("eggs_crate_medium", "Medium egg crate", "", "medium"),
            v("eggs_crate_large", "Large egg crate", "", "large"),
        ],
    },


    # --------------------------------------------------------
    # TISSUE / DIAPERS
    # --------------------------------------------------------

    "tissue_paper": {
        "pack": [
            v("tissue_pack_small", "Small tissue pack", "", "small"),
            v("tissue_pack_medium", "Medium tissue pack", "", "medium"),
            v("tissue_pack_large", "Large tissue pack", "", "large"),
        ],

        "bale": [
            v("tissue_bale_small", "Small tissue bale", "", "small"),
            v("tissue_bale_medium", "Medium tissue bale", "", "medium"),
            v("tissue_bale_large", "Large tissue bale", "", "large"),
        ],
    },

    "diapers_wipes": {
        "pack": [
            v("diaper_pack_small", "Small diaper pack", "", "small"),
            v("diaper_pack_medium", "Medium diaper pack", "", "medium"),
            v("diaper_pack_large", "Large diaper pack", "", "large"),
        ],

        "carton": [
            v("diaper_carton_small", "Small diaper carton", "", "small"),
            v("diaper_carton_medium", "Medium diaper carton", "", "medium"),
            v("diaper_carton_large", "Large diaper carton", "", "large"),
        ],

        "bale": [
            v("diaper_bale_small", "Small diaper bale", "", "small"),
            v("diaper_bale_medium", "Medium diaper bale", "", "medium"),
            v("diaper_bale_large", "Large diaper bale", "", "large"),
        ],
    },


    # --------------------------------------------------------
    # CLEANING
    # --------------------------------------------------------

    "laundry_cleaning": {
        "bottle": [
            v("cleaner_500ml", "500 ml bottle", "500ml", "small"),
            v("cleaner_1l", "1 L bottle", "1L", "medium"),
            v("cleaner_2l", "2 L bottle", "2L", "large"),
        ],

        "jerrycan": [
            v("cleaner_5l", "5 L jerrycan", "5L", "small"),
            v("cleaner_10l", "10 L jerrycan", "10L", "medium"),
            v("cleaner_20l", "20 L jerrycan", "20L", "large"),
        ],
    },


    # --------------------------------------------------------
    # BAKERY
    # --------------------------------------------------------

    "bakery": {
        "loaf": GENERIC["loaf"],
    },
}


def get_variants(
    category_code: str,
    package_type: str,
):
    category_code = (
        category_code
        .strip()
        .casefold()
    )

    package_type = (
        package_type
        .strip()
        .casefold()
    )


    category_specific = (
        CATEGORY_OVERRIDES
        .get(
            category_code,
            {},
        )
        .get(
            package_type
        )
    )


    rows = (
        category_specific
        if category_specific
        is not None
        else GENERIC.get(
            package_type,
            []
        )
    )


    result = [
        dict(row)
        for row in rows
    ]


    result.append({
        "key":
            "custom",

        "label":
            "Other / custom physical size",

        "physical_size_text":
            "",

        "size_class":
            "medium",
    })


    return result
