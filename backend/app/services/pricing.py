import json
import math
import ssl
import urllib.request

import certifi


OSRM_BASE = "https://router.project-osrm.org"

PRICING_VERSION = "ghana-market-optimizer-v7-capacity-split-safe"


# ============================================================
# STOREDASH MARKET MODEL
#
# No vehicle categories.
# No load brackets.
# No arbitrary "heavy = +X" pricing.
#
# We model:
#
# 1. Expected driver market cost
# 2. Probability a driver accepts a payout
# 3. Probability a customer accepts a delivery fee
# 4. Platform margin
#
# Then search for a price that balances all three sides.
# ============================================================


# ------------------------------------------------------------
# DRIVER MARKET-COST PRIORS
#
# These are initial priors, NOT permanent truths.
# We will later fit them from StoreDash delivery data.
# ------------------------------------------------------------

DRIVER_INTERCEPT = 4.00

DISTANCE_COEF = 0.80

TIME_COEF = 0.035

STOP_COEF = 1.50

LOAD_COEF = 0.10
LOAD_POWER = 1.13

DISTANCE_LOAD_COEF = 0.012
DISTANCE_LOAD_POWER = 0.88


# ------------------------------------------------------------
# ACCEPTANCE CURVES
# ------------------------------------------------------------

DRIVER_SIGMA_FLOOR = 1.50
DRIVER_SIGMA_FRACTION = 0.10

CUSTOMER_COST_MULTIPLIER = 1.28
CUSTOMER_BASE_CONVENIENCE = 3.00
CUSTOMER_BASKET_COEF = 1.20

CUSTOMER_SIGMA_FLOOR = 2.00
CUSTOMER_SIGMA_FRACTION = 0.12


# We require a reasonably attractive driver offer.
MIN_DRIVER_ACCEPTANCE = 0.75


# ------------------------------------------------------------
# PLATFORM ECONOMICS
# ------------------------------------------------------------

MIN_DELIVERY_MARGIN = 1.00

SEARCH_STEP = 0.25


# ------------------------------------------------------------
# SERVICE FEE
#
# Continuous function of basket value + sourcing complexity.
# Separate from transportation economics.
# ------------------------------------------------------------

SERVICE_BASE = 2.00
SERVICE_GOODS_RATE = 0.025
SERVICE_SUPPLIER_COEF = 1.20
SERVICE_ITEM_COEF = 0.40


# Tax stays disabled until StoreDash's Ghana tax treatment
# is formally configured.
TAX_RATE = 0.00


def round_money(
    value: float,
) -> float:
    return round(
        value + 1e-9,
        2,
    )


def round_up_half_cedi(
    value: float,
) -> float:
    return (
        math.ceil(
            value * 2
        )
        / 2
    )


def sigmoid(
    value: float,
) -> float:
    """
    Numerically stable logistic function.
    """

    if value >= 0:
        return (
            1.0
            /
            (
                1.0
                + math.exp(
                    -value
                )
            )
        )

    exp_value = math.exp(
        value
    )

    return (
        exp_value
        /
        (
            1.0
            + exp_value
        )
    )


# ============================================================
# ROUTING
# ============================================================

def calculate_route(
    supplier_coordinates:
        list[
            tuple[
                float,
                float,
            ]
        ],

    customer_coordinate:
        tuple[
            float,
            float,
        ],
) -> dict:

    if not supplier_coordinates:
        raise ValueError(
            "At least one supplier location is required."
        )


    points = [
        f"{longitude},{latitude}"
        for latitude, longitude
        in supplier_coordinates
    ]


    customer_lat, customer_lon = (
        customer_coordinate
    )


    points.append(
        f"{customer_lon},{customer_lat}"
    )


    coordinates = ";".join(
        points
    )


    if len(
        supplier_coordinates
    ) == 1:

        url = (
            f"{OSRM_BASE}"
            f"/route/v1/driving/"
            f"{coordinates}"
            "?overview=false"
        )

    else:

        url = (
            f"{OSRM_BASE}"
            f"/trip/v1/driving/"
            f"{coordinates}"
            "?roundtrip=false"
            "&source=any"
            "&destination=last"
            "&overview=false"
        )


    request = urllib.request.Request(
        url,
        headers={
            "User-Agent":
                "StoreDash-MVP/1.0 "
                "(internal logistics application)",
        },
    )


    ssl_context = (
        ssl.create_default_context(
            cafile=
                certifi.where()
        )
    )


    with urllib.request.urlopen(
        request,
        timeout=15,
        context=ssl_context,
    ) as response:

        data = json.loads(
            response
            .read()
            .decode(
                "utf-8"
            )
        )


    if data.get(
        "code"
    ) != "Ok":

        raise ValueError(
            "Routing failed: "
            f"{data.get('code', 'unknown')}"
        )


    routes = (
        data.get(
            "routes"
        )
        or
        data.get(
            "trips"
        )
    )


    if not routes:
        raise ValueError(
            "Routing service returned no usable route."
        )


    route = routes[0]


    return {
        "distance_km":
            round(
                float(
                    route[
                        "distance"
                    ]
                )
                / 1000,
                2,
            ),

        "duration_minutes":
            round(
                float(
                    route[
                        "duration"
                    ]
                )
                / 60,
                1,
            ),
    }


# ============================================================
# DRIVER MARKET COST
# ============================================================

def cargo_pressure(
    *,
    total_load_units: float,
    total_weight_kg: float,
    total_volume_l: float,
    total_handling_score: float,
    total_fragility_score: float,
) -> float:
    """
    Combine correlated physical characteristics into
    one continuous cargo-pressure variable.

    We deliberately do NOT add weight, volume,
    handling and load costs independently because
    they describe overlapping physical difficulty.
    """

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

    load = max(
        float(total_load_units),
        0.0,
    )


    # Reference scales describe approximately
    # one modest commercial delivery.
    #
    # These are normalization constants,
    # NOT price brackets.

    weight_ratio = (
        weight / 25.0
    )

    volume_ratio = (
        volume / 60.0
    )

    handling_ratio = (
        handling / 5.0
    )

    fragility_ratio = (
        fragility / 1.0
    )

    load_ratio = (
        load / 10.0
    )


    # Weighted generalized mean.
    #
    # Power > 1 gives extra influence to whichever
    # physical dimension is genuinely difficult,
    # without simply summing the same burden five times.

    power = 1.40

    pressure = (
        (
            0.35
            * (
                weight_ratio
                ** power
            )
        )

        + (
            0.25
            * (
                volume_ratio
                ** power
            )
        )

        + (
            0.20
            * (
                handling_ratio
                ** power
            )
        )

        + (
            0.10
            * (
                fragility_ratio
                ** power
            )
        )

        + (
            0.10
            * (
                load_ratio
                ** power
            )
        )
    ) ** (
        1.0 / power
    )


    return max(
        pressure,
        0.0,
    )


def estimate_driver_market_cost(
    *,
    distance_km: float,
    duration_minutes: float,
    supplier_count: int,
    total_load_units: float,
    total_weight_kg: float | None = None,
    total_volume_l: float | None = None,
    total_handling_score: float | None = None,
    total_fragility_score: float | None = None,
) -> float:
    """
    Estimate the underlying transport-work cost.

    V5 principle:
    ----------------
    Small and normal orders mostly pay for the route.

    As physical cargo becomes large, StoreDash estimates
    how many STANDARD COMMERCIAL TRANSPORT-WORK UNITS
    the order represents.

    This is NOT vehicle pricing.

    We do not ask the operator whether a motorcycle,
    tricycle, van or truck will be used.

    Instead, physical burden itself increases the amount
    of transport work implied by the order.

    This prevents multi-tonne orders from being priced
    almost the same as ~100 kg orders.
    """

    distance = max(
        float(distance_km),
        0.0,
    )

    duration = max(
        float(duration_minutes),
        0.0,
    )

    load = max(
        float(total_load_units),
        0.0,
    )


    # ========================================================
    # PHYSICAL VALUES
    # ========================================================

    weight = max(
        (
            float(total_weight_kg)
            if total_weight_kg
            is not None
            else load * 2.0
        ),
        0.0,
    )

    volume = max(
        (
            float(total_volume_l)
            if total_volume_l
            is not None
            else load * 4.0
        ),
        0.0,
    )

    handling = max(
        (
            float(total_handling_score)
            if total_handling_score
            is not None
            else load ** 0.60
        ),
        0.0,
    )

    fragility = max(
        (
            float(total_fragility_score)
            if total_fragility_score
            is not None
            else (
                0.15
                * (
                    load ** 0.50
                )
            )
        ),
        0.0,
    )


    # ========================================================
    # BASE ROUTE WORK
    #
    # This approximates one ordinary commercial movement.
    # ========================================================

    extra_stops = max(
        int(supplier_count)
        - 1,
        0,
    )


    single_movement_route = (
        4.00

        + (
            2.20
            * distance
        )

        + (
            0.04
            * duration
        )

        + (
            1.50
            * math.log1p(
                extra_stops
            )
        )
    )


    # ========================================================
    # CAPACITY PRESSURE
    #
    # Reference capacities are calibration scales,
    # NOT vehicle limits and NOT price brackets.
    #
    # Roughly:
    #
    # 350 kg
    # 900 litres
    # 70 handling points
    # 100 dynamic load points
    #
    # represent one substantial commercial movement.
    #
    # The values are combined continuously.
    # ========================================================

    weight_work = (
        weight
        / 350.0
    )

    volume_work = (
        volume
        / 900.0
    )

    handling_work = (
        handling
        / 70.0
    )

    load_work = (
        load
        / 100.0
    )


    # Generalized mean heavily respects whichever
    # physical dimension is the real constraint.
    #
    # Example:
    # heavy but compact rice should still be recognized.
    # bulky but light tissue should also be recognized.

    power = 4.0

    physical_work = (
        (
            0.50
            * (
                weight_work
                ** power
            )
        )

        + (
            0.25
            * (
                volume_work
                ** power
            )
        )

        + (
            0.15
            * (
                handling_work
                ** power
            )
        )

        + (
            0.10
            * (
                load_work
                ** power
            )
        )
    ) ** (
        1.0 / power
    )


    # ========================================================
    # SMOOTH TRANSPORT-WORK UNITS
    #
    # Near-zero cargo still requires one route.
    #
    # Large cargo increasingly represents multiple
    # equivalent transport movements.
    #
    # This is continuous: there are no sudden brackets.
    # ========================================================

    transport_work_units = (
        (
            1.0
            + (
                physical_work
                ** 4.0
            )
        )
        ** 0.25
    )


    extra_transport_work = max(
        transport_work_units
        - 1.0,
        0.0,
    )


    # ========================================================
    # ROUTE × CARGO INTERACTION
    #
    # A 5-tonne movement over 15 km must cost materially
    # more than a 100 kg movement over the same 15 km.
    #
    # Exponent below 1 preserves some bulk efficiency,
    # so price does not scale perfectly linearly.
    # ========================================================

    route_work_multiplier = (
        1.0

        + (
            0.72
            * (
                extra_transport_work
                ** 0.88
            )
        )
    )


    route_work_cost = (
        single_movement_route
        * route_work_multiplier
    )


    # ========================================================
    # LOADING / PHYSICAL COMPLEXITY
    #
    # Still logarithmic because this part represents
    # handling complexity, NOT total transport capacity.
    #
    # Capacity itself is already handled above.
    # ========================================================

    loading_component = (
        4.50
        * math.log1p(
            physical_work
        )
    )


    # Fragility should matter but never turn into the
    # dominant freight cost by itself.

    fragility_component = (
        1.80
        * math.sqrt(
            fragility
        )
    )


    market_cost = (
        route_work_cost
        + loading_component
        + fragility_component
    )


    return max(
        market_cost,
        0.50,
    )


def driver_acceptance_probability(
    *,
    payout: float,
    market_cost: float,
) -> float:

    sigma = max(
        DRIVER_SIGMA_FLOOR,

        market_cost
        * DRIVER_SIGMA_FRACTION,
    )


    return sigmoid(
        (
            payout
            - market_cost
        )
        / sigma
    )


# ============================================================
# CUSTOMER WILLINGNESS
# ============================================================

def estimate_customer_willingness(
    *,
    driver_market_cost: float,
    goods_total: float,
) -> float:

    goods = max(
        float(
            goods_total
        ),
        0.0,
    )


    # Basket value has only a weak logarithmic effect.
    #
    # A GH₵1,000 basket may tolerate somewhat more
    # logistics cost than a GH₵10 basket, but we do NOT
    # simply multiply delivery by basket value.

    basket_component = (
        CUSTOMER_BASKET_COEF
        * math.log1p(
            goods
            / 100.0
        )
    )


    return (
        (
            driver_market_cost
            * CUSTOMER_COST_MULTIPLIER
        )
        + CUSTOMER_BASE_CONVENIENCE
        + basket_component
    )


def customer_acceptance_probability(
    *,
    delivery_fee: float,
    willingness: float,
) -> float:

    sigma = max(
        CUSTOMER_SIGMA_FLOOR,

        willingness
        * CUSTOMER_SIGMA_FRACTION,
    )


    return sigmoid(
        (
            willingness
            - delivery_fee
        )
        / sigma
    )


# ============================================================
# INVERSE DRIVER ACCEPTANCE
#
# Gives us useful negotiation boundaries.
# ============================================================

def payout_for_driver_acceptance(
    *,
    probability: float,
    market_cost: float,
) -> float:

    probability = min(
        max(
            probability,
            0.001,
        ),
        0.999,
    )


    sigma = max(
        DRIVER_SIGMA_FLOOR,

        market_cost
        * DRIVER_SIGMA_FRACTION,
    )


    log_odds = math.log(
        probability
        /
        (
            1.0
            - probability
        )
    )


    return (
        market_cost
        + (
            sigma
            * log_odds
        )
    )


# ============================================================
# TWO-SIDED MARKET OPTIMIZER
# ============================================================

def optimize_delivery_market(
    *,
    goods_total: float,
    distance_km: float,
    duration_minutes: float,
    supplier_count: int,
    total_load_units: float,
    total_weight_kg: float | None = None,
    total_volume_l: float | None = None,
    total_handling_score: float | None = None,
    total_fragility_score: float | None = None,
) -> dict:

    market_cost = (
        estimate_driver_market_cost(
            distance_km=
                distance_km,

            duration_minutes=
                duration_minutes,

            supplier_count=
                supplier_count,

            total_load_units=
                total_load_units,

            total_weight_kg=
                total_weight_kg,

            total_volume_l=
                total_volume_l,

            total_handling_score=
                total_handling_score,

            total_fragility_score=
                total_fragility_score,
        )
    )


    willingness = (
        estimate_customer_willingness(
            driver_market_cost=
                market_cost,

            goods_total=
                goods_total,
        )
    )


    # ------------------------------------------
    # Search ranges
    #
    # We are NOT categorizing the order.
    #
    # We search a continuous economic space:
    #
    # driver payout × customer delivery fee
    # ------------------------------------------

    payout_low = max(
        0.50,
        market_cost
        * 0.65,
    )


    payout_high = (
        market_cost
        * 1.60
        + 8.00
    )


    best = None


    payout = payout_low


    while payout <= payout_high:

        driver_probability = (
            driver_acceptance_probability(
                payout=
                    payout,

                market_cost=
                    market_cost,
            )
        )


        # Operational constraint:
        # don't intentionally choose driver offers
        # predicted to fail most of the time.

        if (
            driver_probability
            >= MIN_DRIVER_ACCEPTANCE
        ):

            # ------------------------------------------------
            # STOREDASH DELIVERY ECONOMICS HARD RULE
            #
            # Driver payout may NEVER exceed 75% of the
            # customer delivery fee.
            #
            # Therefore:
            #
            # delivery_fee >= payout / 0.75
            #
            # This guarantees StoreDash retains at least
            # 25% of delivery revenue before the separate
            # service fee.
            # ------------------------------------------------

            minimum_fee_for_split = (
                payout
                / 0.75
            )


            fee_low = max(
                payout
                + MIN_DELIVERY_MARGIN,

                minimum_fee_for_split,
            )


            fee_high = max(
                (
                    willingness
                    * 1.50
                )
                + 6.00,

                fee_low
                + 10.00,
            )


            delivery_fee = (
                fee_low
            )


            while (
                delivery_fee
                <= fee_high
            ):

                customer_probability = (
                    customer_acceptance_probability(
                        delivery_fee=
                            delivery_fee,

                        willingness=
                            willingness,
                    )
                )


                platform_margin = (
                    delivery_fee
                    - payout
                )


                # ----------------------------------
                # Nash-style surplus balance
                #
                # Driver gets surplus above expected
                # market cost.
                #
                # Customer gets surplus below their
                # estimated willingness.
                #
                # StoreDash gets delivery margin.
                #
                # The geometric mean punishes a plan
                # that benefits one side while nearly
                # crushing another.
                # ----------------------------------

                driver_surplus = max(
                    payout
                    - market_cost,

                    0.05,
                )


                customer_surplus = max(
                    willingness
                    - delivery_fee,

                    0.05,
                )


                platform_surplus = max(
                    platform_margin,

                    0.05,
                )


                nash_balance = (
                    driver_surplus
                    * customer_surplus
                    * platform_surplus
                ) ** (
                    1.0
                    / 3.0
                )


                # Reliability matters too.
                #
                # A theoretically beautiful margin
                # is useless if drivers/customers
                # constantly reject it.

                score = (
                    nash_balance
                    * (
                        driver_probability
                        ** 1.20
                    )
                    * (
                        customer_probability
                        ** 1.10
                    )
                )


                candidate = {
                    "score":
                        score,

                    "driver_payout":
                        payout,

                    "delivery_fee":
                        delivery_fee,

                    "driver_probability":
                        driver_probability,

                    "customer_probability":
                        customer_probability,

                    "platform_margin":
                        platform_margin,
                }


                if (
                    best is None
                    or
                    candidate[
                        "score"
                    ]
                    >
                    best[
                        "score"
                    ]
                ):
                    best = candidate


                delivery_fee += (
                    SEARCH_STEP
                )


        payout += (
            SEARCH_STEP
        )


    if best is None:
        raise ValueError(
            "StoreDash could not find a viable "
            "delivery-market price."
        )


    driver_target = (
        round_up_half_cedi(
            best[
                "driver_payout"
            ]
        )
    )


    delivery_fee = (
        round_up_half_cedi(
            best[
                "delivery_fee"
            ]
        )
    )


    # Negotiation band comes from acceptance
    # probabilities rather than arbitrary ±10%.

    driver_floor = (
        round_up_half_cedi(
            payout_for_driver_acceptance(
                probability=
                    0.68,

                market_cost=
                    market_cost,
            )
        )
    )


    driver_ceiling = (
        round_up_half_cedi(
            payout_for_driver_acceptance(
                probability=
                    0.93,

                market_cost=
                    market_cost,
            )
        )
    )


    driver_probability = (
        driver_acceptance_probability(
            payout=
                driver_target,

            market_cost=
                market_cost,
        )
    )


    customer_probability = (
        customer_acceptance_probability(
            delivery_fee=
                delivery_fee,

            willingness=
                willingness,
        )
    )


    return {
        "estimated_driver_market_cost":
            round_money(
                market_cost
            ),

        "estimated_customer_willingness":
            round_money(
                willingness
            ),

        "driver_floor":
            driver_floor,

        "driver_target":
            driver_target,

        "driver_ceiling":
            driver_ceiling,

        "delivery_fee":
            delivery_fee,

        "driver_acceptance_probability":
            round(
                driver_probability,
                4,
            ),

        "customer_acceptance_probability":
            round(
                customer_probability,
                4,
            ),

        "delivery_margin":
            round_money(
                delivery_fee
                - driver_target
            ),

        "optimizer_score":
            round(
                best[
                    "score"
                ],
                6,
            ),
    }


# ============================================================
# SERVICE FEE
# ============================================================

def calculate_service_fee(
    *,
    goods_total: float,
    supplier_count: int,
    item_count: int,
) -> float:

    goods = max(
        float(goods_total),
        0.0,
    )

    suppliers = max(
        int(supplier_count),
        1,
    )

    items = max(
        int(item_count),
        1,
    )


    # Value matters slightly because larger procurement
    # has more commercial responsibility, but it should
    # not make service fees explode.

    value_component = (
        2.00
        * math.log1p(
            goods / 100.0
        )
    )


    supplier_component = (
        1.20
        * math.log1p(
            suppliers
        )
    )


    item_component = (
        0.60
        * math.log1p(
            items
        )
    )


    service_fee = (
        2.50
        + value_component
        + supplier_component
        + item_component
    )


    return round_money(
        service_fee
    )



# ============================================================
# PUBLIC PRICING FUNCTION
#
# Keeps the same interface expected by order_workflow.py.
# ============================================================

def calculate_pricing(
    *,
    goods_total: float,
    distance_km: float,
    duration_minutes: float,
    supplier_count: int,
    total_load_units: float,
    total_weight_kg: float | None = None,
    total_volume_l: float | None = None,
    total_handling_score: float | None = None,
    total_fragility_score: float | None = None,
    item_count: int = 1,
) -> dict:

    market = (
        optimize_delivery_market(
            goods_total=
                goods_total,

            distance_km=
                distance_km,

            duration_minutes=
                duration_minutes,

            supplier_count=
                supplier_count,

            total_load_units=
                total_load_units,

            total_weight_kg=
                total_weight_kg,

            total_volume_l=
                total_volume_l,

            total_handling_score=
                total_handling_score,

            total_fragility_score=
                total_fragility_score,
        )
    )


    service_fee = (
        calculate_service_fee(
            goods_total=
                goods_total,

            supplier_count=
                supplier_count,

            item_count=
                item_count,
        )
    )


    delivery_fee = float(
        market[
            "delivery_fee"
        ]
    )


    # ========================================================
    # FINAL 75 / 25 ECONOMIC INVARIANT
    #
    # The optimizer works with continuous values and later
    # rounds money to operational increments.
    #
    # Rounding must NEVER allow the driver target or ceiling
    # to exceed 75% of the customer delivery fee.
    #
    # If rounding creates a violation, increase the customer
    # delivery fee to the next GH₵0.50 that safely supports
    # the authorized driver amount.
    # ========================================================

    driver_target = float(
        market.get(
            "driver_target",
            0.0,
        )
        or 0.0
    )


    driver_ceiling = float(
        market.get(
            "driver_ceiling",
            driver_target,
        )
        or driver_target
    )


    highest_authorized_driver_amount = max(
        driver_target,
        driver_ceiling,
        0.0,
    )


    required_delivery_fee = (
        highest_authorized_driver_amount
        / 0.75
        if highest_authorized_driver_amount
        > 0
        else 0.0
    )


    # Round UP to next GH₵0.50 rather than nearest.
    # We must never round back below the economic minimum.
    required_delivery_fee = (
        math.ceil(
            required_delivery_fee
            * 2.0
            - 1e-9
        )
        / 2.0
    )


    delivery_fee = max(
        delivery_fee,
        required_delivery_fee,
    )


    # Absolute customer-fee hard cap available to drivers.
    split_hard_cap = (
        delivery_fee
        * 0.75
    )


    # Preserve optimizer ordering:
    #
    # floor <= target <= ceiling <= 75% delivery fee

    market[
        "driver_ceiling"
    ] = min(
        float(
            market.get(
                "driver_ceiling",
                split_hard_cap,
            )
            or split_hard_cap
        ),
        split_hard_cap,
    )


    market[
        "driver_target"
    ] = min(
        float(
            market.get(
                "driver_target",
                market[
                    "driver_ceiling"
                ],
            )
            or market[
                "driver_ceiling"
            ]
        ),
        market[
            "driver_ceiling"
        ],
    )


    market[
        "driver_floor"
    ] = min(
        float(
            market.get(
                "driver_floor",
                market[
                    "driver_target"
                ],
            )
            or market[
                "driver_target"
            ]
        ),
        market[
            "driver_target"
        ],
    )


    # Margin snapshot should reflect the corrected rounded
    # customer delivery fee and target.
    market[
        "delivery_margin"
    ] = round_money(
        delivery_fee
        - market[
            "driver_target"
        ]
    )


    subtotal_before_tax = (
        goods_total
        + delivery_fee
        + service_fee
    )


    tax_total = round_money(
        subtotal_before_tax
        * TAX_RATE
    )


    final_total = round_money(
        subtotal_before_tax
        + tax_total
    )


    return {
        "delivery_fee":
            delivery_fee,

        "service_fee":
            service_fee,

        "tax_total":
            tax_total,

        "final_total":
            final_total,

        "driver_floor":
            market[
                "driver_floor"
            ],

        "driver_target":
            market[
                "driver_target"
            ],

        "driver_ceiling":
            market[
                "driver_ceiling"
            ],

        "estimated_driver_market_cost":
            market[
                "estimated_driver_market_cost"
            ],

        "estimated_customer_willingness":
            market[
                "estimated_customer_willingness"
            ],

        "driver_acceptance_probability":
            market[
                "driver_acceptance_probability"
            ],

        "customer_acceptance_probability":
            market[
                "customer_acceptance_probability"
            ],

        "delivery_margin":
            market[
                "delivery_margin"
            ],

        "optimizer_score":
            market[
                "optimizer_score"
            ],

        "pricing_version":
            PRICING_VERSION,
    }
