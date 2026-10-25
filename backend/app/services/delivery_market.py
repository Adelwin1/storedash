from __future__ import annotations

from dataclasses import asdict, dataclass
from math import ceil
from statistics import median
from typing import Iterable


# ============================================================
# STOREDASH DELIVERY MARKET POLICY
# ============================================================

POLICY_VERSION = "delivery-market-v1"

TARGET_MARGIN = 0.25
NORMAL_MIN_MARGIN = 0.15
MARKET_RESCUE_MARGIN = 0.10

MONEY_INCREMENT = 0.50


def round_up_money(
    value: float,
    increment: float = MONEY_INCREMENT,
) -> float:
    """
    Always round UP so rounding never accidentally destroys
    the required StoreDash margin.
    """

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
            value / increment - 1e-12
        )
        * increment,
        2,
    )


def margin_rate(
    *,
    customer_price: float,
    carrier_cost: float,
) -> float:

    customer_price = float(
        customer_price
    )

    carrier_cost = float(
        carrier_cost
    )

    if customer_price <= 0:
        return 0.0

    return (
        customer_price
        - carrier_cost
    ) / customer_price


def price_for_margin(
    *,
    carrier_cost: float,
    margin: float,
) -> float:

    carrier_cost = max(
        float(carrier_cost),
        0.0,
    )

    margin = float(
        margin
    )

    if margin >= 1:
        raise ValueError(
            "Margin must be below 100%."
        )

    if margin < 0:
        raise ValueError(
            "Margin cannot be negative."
        )

    return round_up_money(
        carrier_cost
        / (
            1.0
            - margin
        )
    )


@dataclass(frozen=True)
class DeliveryQuoteDecision:
    policy_version: str

    storedash_model_price: float
    carrier_cost: float

    customer_delivery_fee: float

    storedash_delivery_profit: float
    storedash_margin_rate: float

    target_margin_rate: float

    pricing_mode: str

    model_price_was_under_market: bool
    model_price_was_over_market: bool

    def to_dict(self) -> dict:
        return asdict(
            self
        )


def reconcile_delivery_quote(
    *,
    storedash_model_price: float,
    carrier_cost: float,
) -> DeliveryQuoteDecision:
    """
    Reconcile StoreDash's internally-calculated fair customer
    price with the actual live carrier/CargoMov cost.

    RULES

    1. If a 25% StoreDash margin fits BELOW the StoreDash
       fair-price estimate:
           charge only enough for 25%.

    2. Otherwise, if charging the StoreDash model price still
       gives at least 15% margin:
           charge the StoreDash model price.

    3. If carrier cost is still below our model but the model
       price gives less than 15%:
           increase only enough to secure 15%.

    4. If live market cost is at/above our model estimate:
           our prediction missed the live market.
           Protect StoreDash with only a 10% rescue margin
           rather than forcing the full 25%.

    Customer sees one final non-negotiated delivery fee.
    """

    model_price = round_up_money(
        storedash_model_price
    )

    carrier_cost = round_up_money(
        carrier_cost
    )

    if model_price <= 0:
        raise ValueError(
            "StoreDash model price must be positive."
        )

    if carrier_cost <= 0:
        raise ValueError(
            "Carrier cost must be positive."
        )


    target_price = price_for_margin(
        carrier_cost=carrier_cost,
        margin=TARGET_MARGIN,
    )


    # --------------------------------------------------------
    # CASE 1
    # Full 25% fits comfortably within our fair customer price.
    # --------------------------------------------------------

    if target_price <= model_price:

        final_price = (
            target_price
        )

        pricing_mode = (
            "target_margin"
        )

        target_margin = (
            TARGET_MARGIN
        )


    else:

        margin_at_model_price = (
            margin_rate(
                customer_price=model_price,
                carrier_cost=carrier_cost,
            )
        )


        # ----------------------------------------------------
        # CASE 2
        # Full 25% would exceed our fair price, but our fair
        # price already gives StoreDash at least 15%.
        # ----------------------------------------------------

        if (
            carrier_cost
            < model_price
            and
            margin_at_model_price
            >= NORMAL_MIN_MARGIN
        ):

            final_price = (
                model_price
            )

            pricing_mode = (
                "model_price_flexible_margin"
            )

            target_margin = (
                margin_at_model_price
            )


        # ----------------------------------------------------
        # CASE 3
        # Carrier is below our estimate, but not enough margin
        # remains. Increase only enough to secure 15%.
        # ----------------------------------------------------

        elif carrier_cost < model_price:

            final_price = (
                price_for_margin(
                    carrier_cost=carrier_cost,
                    margin=NORMAL_MIN_MARGIN,
                )
            )

            pricing_mode = (
                "normal_margin_floor"
            )

            target_margin = (
                NORMAL_MIN_MARGIN
            )


        # ----------------------------------------------------
        # CASE 4
        # Live carrier market is already at/above StoreDash's
        # model estimate.
        #
        # Prediction missed current supply conditions.
        # Use a smaller 10% rescue margin.
        # ----------------------------------------------------

        else:

            final_price = (
                price_for_margin(
                    carrier_cost=carrier_cost,
                    margin=MARKET_RESCUE_MARGIN,
                )
            )

            pricing_mode = (
                "live_market_rescue"
            )

            target_margin = (
                MARKET_RESCUE_MARGIN
            )


    profit = round(
        final_price
        - carrier_cost,
        2,
    )

    actual_margin = round(
        margin_rate(
            customer_price=final_price,
            carrier_cost=carrier_cost,
        ),
        6,
    )


    return DeliveryQuoteDecision(
        policy_version=POLICY_VERSION,

        storedash_model_price=model_price,

        carrier_cost=carrier_cost,

        customer_delivery_fee=final_price,

        storedash_delivery_profit=profit,

        storedash_margin_rate=actual_margin,

        target_margin_rate=round(
            target_margin,
            6,
        ),

        pricing_mode=pricing_mode,

        model_price_was_under_market=(
            model_price
            < carrier_cost
        ),

        model_price_was_over_market=(
            model_price
            > carrier_cost
        ),
    )


# ============================================================
# CARGOMOV / EXTERNAL CARRIER BID MARKET
# ============================================================


@dataclass(frozen=True)
class CarrierBidInput:
    amount: float

    qualified: bool = True

    provider: str = "cargomov"

    external_bid_id: str | None = None

    pickup_eta_minutes: float | None = None

    rating: float | None = None

    capacity_ok: bool = True


@dataclass(frozen=True)
class CarrierMarketSummary:
    qualified_bid_count: int

    minimum_bid: float
    median_bid: float

    recommended_bid: float

    bid_spread: float

    provider: str

    def to_dict(self) -> dict:
        return asdict(
            self
        )


def summarize_carrier_market(
    bids: Iterable[
        CarrierBidInput
    ],
) -> CarrierMarketSummary:
    """
    Produce the StoreDash live-market benchmark.

    Unqualified / wrong-capacity bids are ignored.

    The recommended market amount is currently the median of
    up to the three cheapest qualified bids.

    This prevents one suspiciously-low outlier from defining
    the entire market.
    """

    qualified = [
        bid
        for bid in bids
        if (
            bid.qualified
            and
            bid.capacity_ok
            and
            float(
                bid.amount
            )
            > 0
        )
    ]

    if not qualified:
        raise ValueError(
            "No qualified carrier bids available."
        )

    qualified.sort(
        key=lambda bid: (
            float(
                bid.amount
            ),
            (
                bid.pickup_eta_minutes
                if
                bid.pickup_eta_minutes
                is not None
                else
                float("inf")
            ),
        )
    )

    amounts = [
        round_up_money(
            bid.amount
        )
        for bid in qualified
    ]

    cheapest_group = (
        amounts[:3]
    )

    recommended = (
        median(
            cheapest_group
        )
    )

    return CarrierMarketSummary(
        qualified_bid_count=len(
            amounts
        ),

        minimum_bid=min(
            amounts
        ),

        median_bid=round(
            median(
                amounts
            ),
            2,
        ),

        recommended_bid=round_up_money(
            recommended
        ),

        bid_spread=round(
            max(
                amounts
            )
            - min(
                amounts
            ),
            2,
        ),

        provider=(
            qualified[
                0
            ].provider
        ),
    )
