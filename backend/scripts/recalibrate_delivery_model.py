from __future__ import annotations

from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(
        0,
        str(PROJECT_ROOT),
    )


import argparse
import json

from collections import defaultdict
from datetime import datetime, timedelta
from statistics import median

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.db import engine

from app.models import (
    DeliveryPricingSnapshot,
    PricingCalibrationRun,
    PricingModelVersion,
)

from app.services.upfront_delivery import (
    DEFAULT_COEFFICIENTS,
)


# ============================================================
# STOREDASH MODEL LEARNING POLICY
# ============================================================

RECALIBRATION_DAYS = 14

LOOKBACK_DAYS = 90

MIN_TOTAL_SAMPLES = 20

MIN_VALIDATION_SAMPLES = 4

MIN_GROUP_SAMPLES = 5

MIN_MAE_IMPROVEMENT = 0.03

MAX_GLOBAL_CHANGE = 0.20

MAX_GROUP_CHANGE = 0.10


def clamp(
    value: float,
    low: float,
    high: float,
) -> float:
    return max(
        low,
        min(
            high,
            value,
        ),
    )


def actual_cost(
    row: DeliveryPricingSnapshot,
) -> float:

    if row.actual_carrier_cost is not None:
        return float(
            row.actual_carrier_cost
        )

    return float(
        row.selected_carrier_cost
        or 0
    )


def predicted_cost(
    row: DeliveryPricingSnapshot,
) -> float:

    return float(
        row.model_predicted_carrier_cost
        or 0
    )


def mae(
    actuals: list[float],
    predictions: list[float],
) -> float:

    if not actuals:
        return 0.0

    return sum(
        abs(
            actual - prediction
        )
        for actual, prediction
        in zip(
            actuals,
            predictions,
        )
    ) / len(
        actuals
    )


def mape(
    actuals: list[float],
    predictions: list[float],
) -> float:

    pairs = [
        (
            actual,
            prediction,
        )
        for actual, prediction
        in zip(
            actuals,
            predictions,
        )
        if actual > 0
    ]

    if not pairs:
        return 0.0

    return sum(
        abs(
            actual - prediction
        )
        / actual
        for actual, prediction
        in pairs
    ) / len(
        pairs
    )


def bias(
    actuals: list[float],
    predictions: list[float],
) -> float:

    if not actuals:
        return 0.0

    return sum(
        prediction - actual
        for actual, prediction
        in zip(
            actuals,
            predictions,
        )
    ) / len(
        actuals
    )


def load_coefficients(
    model: PricingModelVersion | None,
) -> dict:

    result = json.loads(
        json.dumps(
            DEFAULT_COEFFICIENTS
        )
    )

    if not model:
        return result

    try:
        saved = json.loads(
            model.coefficients_json
            or "{}"
        )
    except Exception:
        saved = {}


    for key, value in saved.items():

        if key not in {
            "capacity_multipliers",
            "distance_band_multipliers",
        }:
            result[key] = value


    result[
        "capacity_multipliers"
    ].update(
        saved.get(
            "capacity_multipliers",
            {},
        )
    )


    result[
        "distance_band_multipliers"
    ].update(
        saved.get(
            "distance_band_multipliers",
            {},
        )
    )


    return result


def main():

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--force",
        action="store_true",
        help=(
            "Ignore the 14-day timing gate. "
            "Sample-size protection still applies."
        ),
    )

    args = parser.parse_args()


    now = datetime.utcnow()

    window_start = (
        now
        - timedelta(
            days=LOOKBACK_DAYS
        )
    )


    with Session(engine) as db:

        # ====================================================
        # TIMING GATE
        # ====================================================

        last_run = db.scalars(
            select(
                PricingCalibrationRun
            )
            .where(
                PricingCalibrationRun.completed_at
                .is_not(None)
            )
            .order_by(
                PricingCalibrationRun.completed_at.desc()
            )
        ).first()


        if (
            last_run
            and
            last_run.completed_at
            and
            not args.force
        ):

            age = (
                now
                - last_run.completed_at
            )


            if (
                age
                < timedelta(
                    days=RECALIBRATION_DAYS
                )
            ):

                remaining = (
                    timedelta(
                        days=RECALIBRATION_DAYS
                    )
                    - age
                )

                print(
                    "Calibration not due yet."
                )

                print(
                    "Last run:",
                    last_run.completed_at,
                )

                print(
                    "Remaining:",
                    remaining,
                )

                return


        # ====================================================
        # ACTIVE MODEL
        # ====================================================

        active = db.scalars(
            select(
                PricingModelVersion
            )
            .where(
                PricingModelVersion.status
                == "active"
            )
            .order_by(
                PricingModelVersion.id.desc()
            )
        ).first()


        # ====================================================
        # HISTORICAL MARKET OBSERVATIONS
        #
        # We learn carrier-market pricing from:
        #
        # - actual carrier cost when available
        # - otherwise the selected qualified carrier bid
        #
        # Customer declines remain useful carrier-market data.
        # ====================================================

        rows = list(
            db.scalars(
                select(
                    DeliveryPricingSnapshot
                )
                .where(
                    DeliveryPricingSnapshot.created_at
                    >= window_start,

                    DeliveryPricingSnapshot.selected_carrier_cost
                    .is_not(None),

                    DeliveryPricingSnapshot.model_predicted_carrier_cost
                    > 0,
                )
                .order_by(
                    DeliveryPricingSnapshot.created_at.asc(),
                    DeliveryPricingSnapshot.id.asc(),
                )
            ).all()
        )


        usable = [
            row
            for row in rows
            if (
                actual_cost(row) > 0
                and
                predicted_cost(row) > 0
            )
        ]


        run = PricingCalibrationRun(
            window_start=
                window_start,

            window_end=
                now,

            active_model_version_id=(
                active.id
                if active
                else None
            ),

            sample_count=
                len(usable),

            validation_count=
                0,

            promoted=
                False,
        )


        db.add(run)

        db.flush()


        # ====================================================
        # SAMPLE PROTECTION
        # ====================================================

        if (
            len(usable)
            < MIN_TOTAL_SAMPLES
        ):

            run.notes = (
                "Insufficient market data. "
                f"Need at least {MIN_TOTAL_SAMPLES} "
                "qualified observations."
            )

            run.completed_at = now

            db.commit()

            print()
            print("CALIBRATION SKIPPED")
            print("=" * 60)
            print(
                "Usable samples:",
                len(usable),
            )
            print(
                "Required:",
                MIN_TOTAL_SAMPLES,
            )

            return


        # ====================================================
        # TIME-ORDERED TRAIN / VALIDATION SPLIT
        #
        # Older observations train.
        # Newest observations test.
        #
        # This is better than judging the candidate on the
        # same transactions used to fit it.
        # ====================================================

        split_index = int(
            len(usable)
            * 0.80
        )


        split_index = min(
            split_index,
            len(usable)
            - MIN_VALIDATION_SAMPLES,
        )


        split_index = max(
            split_index,
            1,
        )


        training = usable[
            :split_index
        ]

        validation = usable[
            split_index:
        ]


        run.validation_count = (
            len(validation)
        )


        # ====================================================
        # GLOBAL MARKET CORRECTION
        # ====================================================

        raw_ratios = [
            actual_cost(row)
            /
            predicted_cost(row)
            for row in training
        ]


        observed_global = median(
            raw_ratios
        )


        global_adjustment = clamp(
            observed_global,
            1.0 - MAX_GLOBAL_CHANGE,
            1.0 + MAX_GLOBAL_CHANGE,
        )


        # ====================================================
        # CAPACITY-CLASS CORRECTIONS
        # ====================================================

        capacity_groups = defaultdict(
            list
        )


        for row in training:

            residual = (
                actual_cost(row)
                /
                (
                    predicted_cost(row)
                    * global_adjustment
                )
            )

            capacity_groups[
                row.capacity_class
            ].append(
                residual
            )


        capacity_adjustments = {}


        for (
            capacity_class,
            values,
        ) in capacity_groups.items():

            if (
                len(values)
                < MIN_GROUP_SAMPLES
            ):
                continue


            capacity_adjustments[
                capacity_class
            ] = clamp(
                median(values),
                1.0 - MAX_GROUP_CHANGE,
                1.0 + MAX_GROUP_CHANGE,
            )


        # ====================================================
        # DISTANCE-BAND CORRECTIONS
        # ====================================================

        distance_groups = defaultdict(
            list
        )


        for row in training:

            capacity_adjustment = (
                capacity_adjustments.get(
                    row.capacity_class,
                    1.0,
                )
            )


            residual = (
                actual_cost(row)
                /
                (
                    predicted_cost(row)
                    * global_adjustment
                    * capacity_adjustment
                )
            )


            distance_groups[
                row.distance_band
            ].append(
                residual
            )


        distance_adjustments = {}


        for (
            distance_band,
            values,
        ) in distance_groups.items():

            if (
                len(values)
                < MIN_GROUP_SAMPLES
            ):
                continue


            distance_adjustments[
                distance_band
            ] = clamp(
                median(values),
                1.0 - MAX_GROUP_CHANGE,
                1.0 + MAX_GROUP_CHANGE,
            )


        # ====================================================
        # BUILD CANDIDATE COEFFICIENTS
        # ====================================================

        old_coefficients = (
            load_coefficients(
                active
            )
        )


        new_coefficients = json.loads(
            json.dumps(
                old_coefficients
            )
        )


        new_coefficients[
            "global_multiplier"
        ] = round(
            float(
                old_coefficients.get(
                    "global_multiplier",
                    1.0,
                )
            )
            * global_adjustment,
            6,
        )


        for (
            capacity_class,
            adjustment,
        ) in capacity_adjustments.items():

            previous = float(
                old_coefficients[
                    "capacity_multipliers"
                ].get(
                    capacity_class,
                    1.0,
                )
            )


            new_coefficients[
                "capacity_multipliers"
            ][
                capacity_class
            ] = round(
                previous
                * adjustment,
                6,
            )


        for (
            distance_band,
            adjustment,
        ) in distance_adjustments.items():

            previous = float(
                old_coefficients[
                    "distance_band_multipliers"
                ].get(
                    distance_band,
                    1.0,
                )
            )


            new_coefficients[
                "distance_band_multipliers"
            ][
                distance_band
            ] = round(
                previous
                * adjustment,
                6,
            )


        # ====================================================
        # VALIDATE CANDIDATE
        # ====================================================

        validation_actual = [
            actual_cost(row)
            for row in validation
        ]


        validation_active = [
            predicted_cost(row)
            for row in validation
        ]


        validation_candidate = []


        for row in validation:

            correction = (
                global_adjustment
                *
                capacity_adjustments.get(
                    row.capacity_class,
                    1.0,
                )
                *
                distance_adjustments.get(
                    row.distance_band,
                    1.0,
                )
            )


            validation_candidate.append(
                predicted_cost(row)
                * correction
            )


        active_mae = mae(
            validation_actual,
            validation_active,
        )


        candidate_mae = mae(
            validation_actual,
            validation_candidate,
        )


        active_mape = mape(
            validation_actual,
            validation_active,
        )


        candidate_mape = mape(
            validation_actual,
            validation_candidate,
        )


        candidate_bias = bias(
            validation_actual,
            validation_candidate,
        )


        underpricing_rate = (
            sum(
                prediction < actual
                for actual, prediction
                in zip(
                    validation_actual,
                    validation_candidate,
                )
            )
            / len(validation_actual)
        )


        overpricing_rate = (
            sum(
                prediction > actual
                for actual, prediction
                in zip(
                    validation_actual,
                    validation_candidate,
                )
            )
            / len(validation_actual)
        )


        # Customer acceptance is retained as a separate metric.
        # We DO NOT currently train carrier cost directly from
        # customer willingness.

        customer_decisions = [
            row.customer_decision
            for row in usable
            if row.customer_decision
            in {
                "accepted",
                "declined",
            }
        ]


        customer_acceptance_rate = (
            (
                sum(
                    decision
                    == "accepted"
                    for decision
                    in customer_decisions
                )
                /
                len(
                    customer_decisions
                )
            )
            if customer_decisions
            else None
        )


        if active_mae > 0:

            mae_improvement = (
                active_mae
                - candidate_mae
            ) / active_mae

        else:

            mae_improvement = 0.0


        # ====================================================
        # PROMOTION POLICY
        #
        # Candidate must:
        #
        # 1. lower MAE
        # 2. improve it meaningfully
        # 3. not materially worsen MAPE
        #
        # This prevents noisy 14-day windows from destabilizing
        # production pricing.
        # ====================================================

        should_promote = (
            candidate_mae
            < active_mae

            and

            mae_improvement
            >= MIN_MAE_IMPROVEMENT

            and

            candidate_mape
            <= (
                active_mape
                + 0.01
            )
        )


        version_name = (
            "storedash-market-"
            + now.strftime(
                "%Y%m%d-%H%M%S"
            )
        )


        candidate = PricingModelVersion(
            version_name=
                version_name,

            status=(
                "active"
                if should_promote
                else "rejected"
            ),

            source=
                "14-day-market-calibration",

            coefficients_json=
                json.dumps(
                    new_coefficients
                ),

            metrics_json=
                json.dumps(
                    {
                        "active_mae":
                            active_mae,

                        "candidate_mae":
                            candidate_mae,

                        "active_mape":
                            active_mape,

                        "candidate_mape":
                            candidate_mape,

                        "candidate_bias":
                            candidate_bias,

                        "mae_improvement":
                            mae_improvement,

                        "observed_global":
                            observed_global,

                        "global_adjustment":
                            global_adjustment,

                        "capacity_adjustments":
                            capacity_adjustments,

                        "distance_adjustments":
                            distance_adjustments,
                    }
                ),

            training_window_start=
                window_start,

            training_window_end=
                now,

            training_sample_count=
                len(training),

            validation_sample_count=
                len(validation),

            activated_at=(
                now
                if should_promote
                else None
            ),
        )


        db.add(
            candidate
        )

        db.flush()


        if (
            should_promote
            and active
        ):

            active.status = (
                "retired"
            )


        run.candidate_model_version_id = (
            candidate.id
        )

        run.active_mae = (
            active_mae
        )

        run.candidate_mae = (
            candidate_mae
        )

        run.active_mape = (
            active_mape
        )

        run.candidate_mape = (
            candidate_mape
        )

        run.candidate_bias = (
            candidate_bias
        )

        run.underpricing_rate = (
            underpricing_rate
        )

        run.overpricing_rate = (
            overpricing_rate
        )

        run.customer_acceptance_rate = (
            customer_acceptance_rate
        )

        run.promoted = (
            should_promote
        )

        run.notes = (
            "Candidate promoted."
            if should_promote
            else
            "Candidate rejected. "
            "Existing active model retained."
        )

        run.completed_at = now


        db.commit()


        print()
        print(
            "STOREDASH MARKET CALIBRATION"
        )

        print(
            "=" * 70
        )

        print(
            "Training samples:",
            len(training),
        )

        print(
            "Validation samples:",
            len(validation),
        )

        print()

        print(
            "Active MAE:",
            round(
                active_mae,
                2,
            ),
        )

        print(
            "Candidate MAE:",
            round(
                candidate_mae,
                2,
            ),
        )

        print()

        print(
            "Active MAPE:",
            round(
                active_mape
                * 100,
                2,
            ),
            "%",
        )

        print(
            "Candidate MAPE:",
            round(
                candidate_mape
                * 100,
                2,
            ),
            "%",
        )

        print()

        print(
            "Candidate bias:",
            round(
                candidate_bias,
                2,
            ),
        )

        print(
            "Underpricing rate:",
            round(
                underpricing_rate
                * 100,
                2,
            ),
            "%",
        )

        print(
            "Overpricing rate:",
            round(
                overpricing_rate
                * 100,
                2,
            ),
            "%",
        )

        print()

        print(
            "MAE improvement:",
            round(
                mae_improvement
                * 100,
                2,
            ),
            "%",
        )

        print()

        print(
            "Promoted:",
            should_promote,
        )

        print(
            "Candidate:",
            version_name,
        )


if __name__ == "__main__":
    main()
