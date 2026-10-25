from __future__ import annotations

from dataclasses import (
    asdict,
    dataclass,
)


EPSILON = 1e-6


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
class EffectiveVehicleCapacity:

    max_payload_kg: float

    max_volume_l: float

    safe_capacity_ratio: float

    physical_payload_kg: float

    physical_volume_l: float

    seat_volume_enabled: bool

    def to_dict(self) -> dict:
        return asdict(self)


def calculate_effective_capacity(
    *,
    spec_payload_kg: float,
    spec_cargo_volume_l: float,
    spec_seat_cargo_volume_l: float = 0,
    seat_area_available_for_cargo: bool = False,
    payload_override_kg: float | None = None,
    cargo_volume_override_l: float | None = None,
    seat_volume_override_l: float | None = None,
    safe_capacity_ratio: float = 0.90,
) -> EffectiveVehicleCapacity:

    physical_payload = float(
        payload_override_kg
        if payload_override_kg is not None
        else spec_payload_kg
    )

    physical_cargo_volume = float(
        cargo_volume_override_l
        if cargo_volume_override_l is not None
        else spec_cargo_volume_l
    )

    physical_seat_volume = float(
        seat_volume_override_l
        if seat_volume_override_l is not None
        else spec_seat_cargo_volume_l
    )

    if physical_payload <= 0:
        raise ValueError(
            "Vehicle payload must be positive."
        )

    if physical_cargo_volume <= 0:
        raise ValueError(
            "Vehicle cargo volume must be positive."
        )

    physical_volume = physical_cargo_volume

    if seat_area_available_for_cargo:
        physical_volume += max(
            physical_seat_volume,
            0,
        )

    ratio = clamp(
        safe_capacity_ratio,
        0.50,
        1.00,
    )

    return EffectiveVehicleCapacity(
        max_payload_kg=round(
            physical_payload * ratio,
            3,
        ),

        max_volume_l=round(
            physical_volume * ratio,
            3,
        ),

        safe_capacity_ratio=ratio,

        physical_payload_kg=round(
            physical_payload,
            3,
        ),

        physical_volume_l=round(
            physical_volume,
            3,
        ),

        seat_volume_enabled=(
            seat_area_available_for_cargo
        ),
    )


@dataclass(
    frozen=True
)
class LoadStop:

    sequence: int

    stop_type: str

    weight_delta_kg: float

    volume_delta_l: float


@dataclass(
    frozen=True
)
class SimulatedStop:

    sequence: int

    stop_type: str

    weight_delta_kg: float

    volume_delta_l: float

    load_weight_after_kg: float

    load_volume_after_l: float

    weight_utilization: float

    volume_utilization: float


@dataclass(
    frozen=True
)
class CapacitySimulation:

    feasible: bool

    rejection_reason: str | None

    peak_weight_kg: float

    peak_volume_l: float

    peak_weight_utilization: float

    peak_volume_utilization: float

    stops: tuple[
        SimulatedStop,
        ...
    ]

    def to_dict(self) -> dict:
        return {
            "feasible":
                self.feasible,

            "rejection_reason":
                self.rejection_reason,

            "peak_weight_kg":
                self.peak_weight_kg,

            "peak_volume_l":
                self.peak_volume_l,

            "peak_weight_utilization":
                self.peak_weight_utilization,

            "peak_volume_utilization":
                self.peak_volume_utilization,

            "stops": [
                asdict(stop)
                for stop in self.stops
            ],
        }


def single_order_fits(
    *,
    order_weight_kg: float,
    order_volume_l: float,
    capacity: EffectiveVehicleCapacity,
) -> bool:

    return (
        max(
            float(order_weight_kg),
            0,
        )
        <= capacity.max_payload_kg
        + EPSILON
        and
        max(
            float(order_volume_l),
            0,
        )
        <= capacity.max_volume_l
        + EPSILON
    )


def simulate_route_capacity(
    *,
    capacity: EffectiveVehicleCapacity,
    stops: list[LoadStop],
) -> CapacitySimulation:
    """
    Simulates ONE physical trip.

    There is no second trip.

    If the route exceeds capacity at any stop,
    the route is rejected.
    """

    ordered = sorted(
        stops,
        key=lambda item:
            item.sequence,
    )

    current_weight = 0.0
    current_volume = 0.0

    peak_weight = 0.0
    peak_volume = 0.0

    peak_weight_util = 0.0
    peak_volume_util = 0.0

    simulated = []

    rejection_reason = None

    for stop in ordered:

        current_weight += float(
            stop.weight_delta_kg
        )

        current_volume += float(
            stop.volume_delta_l
        )

        # A negative vehicle load means something was
        # delivered before it was actually picked up.
        if current_weight < -EPSILON:
            rejection_reason = (
                "delivery_before_pickup_weight"
            )
            break

        if current_volume < -EPSILON:
            rejection_reason = (
                "delivery_before_pickup_volume"
            )
            break

        current_weight = max(
            current_weight,
            0.0,
        )

        current_volume = max(
            current_volume,
            0.0,
        )

        weight_util = (
            current_weight
            / capacity.max_payload_kg
        )

        volume_util = (
            current_volume
            / capacity.max_volume_l
        )

        peak_weight = max(
            peak_weight,
            current_weight,
        )

        peak_volume = max(
            peak_volume,
            current_volume,
        )

        peak_weight_util = max(
            peak_weight_util,
            weight_util,
        )

        peak_volume_util = max(
            peak_volume_util,
            volume_util,
        )

        simulated.append(
            SimulatedStop(
                sequence=
                    stop.sequence,

                stop_type=
                    stop.stop_type,

                weight_delta_kg=
                    round(
                        float(
                            stop.weight_delta_kg
                        ),
                        3,
                    ),

                volume_delta_l=
                    round(
                        float(
                            stop.volume_delta_l
                        ),
                        3,
                    ),

                load_weight_after_kg=
                    round(
                        current_weight,
                        3,
                    ),

                load_volume_after_l=
                    round(
                        current_volume,
                        3,
                    ),

                weight_utilization=
                    round(
                        weight_util,
                        6,
                    ),

                volume_utilization=
                    round(
                        volume_util,
                        6,
                    ),
            )
        )

        if (
            current_weight
            >
            capacity.max_payload_kg
            + EPSILON
        ):
            rejection_reason = (
                "vehicle_weight_capacity_exceeded"
            )
            break

        if (
            current_volume
            >
            capacity.max_volume_l
            + EPSILON
        ):
            rejection_reason = (
                "vehicle_volume_capacity_exceeded"
            )
            break


    if (
        rejection_reason is None
        and
        (
            current_weight > EPSILON
            or
            current_volume > EPSILON
        )
    ):
        rejection_reason = (
            "route_ends_with_undelivered_cargo"
        )


    return CapacitySimulation(
        feasible=(
            rejection_reason
            is None
        ),

        rejection_reason=
            rejection_reason,

        peak_weight_kg=
            round(
                peak_weight,
                3,
            ),

        peak_volume_l=
            round(
                peak_volume,
                3,
            ),

        peak_weight_utilization=
            round(
                peak_weight_util,
                6,
            ),

        peak_volume_utilization=
            round(
                peak_volume_util,
                6,
            ),

        stops=tuple(
            simulated
        ),
    )
