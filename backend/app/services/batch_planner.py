from __future__ import annotations

from dataclasses import (
    asdict,
    dataclass,
)

from typing import Iterable

from app.services.road_matrix import (
    RoadMatrix,
    RoadPoint,
    get_road_matrix,
)

from app.services.vehicle_capacity import (
    EffectiveVehicleCapacity,
)


PLANNER_VERSION = (
    "storedash-batch-planner-v1"
)

EPSILON = 1e-6

DEFAULT_BEAM_WIDTH = 700

MAX_ROUTE_NODES = 45


@dataclass(
    frozen=True
)
class PickupInput:
    supplier_id: int

    latitude: float
    longitude: float

    weight_kg: float
    volume_l: float

    service_minutes: float = 4.0

    location_label: (
        str | None
    ) = None


@dataclass(
    frozen=True
)
class BatchOrderInput:
    order_id: int

    customer_latitude: float
    customer_longitude: float

    delivery_fee: float

    pickups: tuple[
        PickupInput,
        ...
    ]

    delivery_service_minutes: float = 3.0

    # Optional maximum time from route start
    # until this customer should be reached.
    max_delivery_minutes: float | None = None

    customer_label: str | None = None


@dataclass(
    frozen=True
)
class PlannedStop:
    sequence: int

    key: str
    stop_type: str

    latitude: float
    longitude: float

    supplier_id: int | None

    order_id: int | None

    related_order_ids: tuple[
            int,
            ...
        ]

    location_label: str | None

    travel_from_previous_km: float

    travel_from_previous_minutes: float

    arrival_minutes: float

    service_minutes: float

    weight_delta_kg: float

    volume_delta_l: float

    load_weight_after_kg: float

    load_volume_after_l: float

    weight_utilization: float

    volume_utilization: float

    def to_dict(
        self
    ) -> dict:

        return asdict(
            self
        )


@dataclass(
    frozen=True
)
class BatchPlan:
    planner_version: str

    feasible: bool

    rejection_reason: str | None

    order_ids: tuple[
            int,
            ...
        ]

    order_count: int
    pickup_count: int
    delivery_count: int

    total_distance_km: float
    total_driving_minutes: float
    total_service_minutes: float
    total_route_minutes: float

    peak_weight_kg: float
    peak_volume_l: float

    peak_weight_utilization: float
    peak_volume_utilization: float

    customer_delivery_revenue: float

    road_provider: str | None

    traffic_aware: bool

    stops: tuple[
        PlannedStop,
        ...
    ]

    def to_dict(
        self
    ) -> dict:

        return {
            "planner_version":
                self.planner_version,

            "feasible":
                self.feasible,

            "rejection_reason":
                self.rejection_reason,

            "order_ids":
                list(
                    self.order_ids
                ),

            "order_count":
                self.order_count,

            "pickup_count":
                self.pickup_count,

            "delivery_count":
                self.delivery_count,

            "total_distance_km":
                self.total_distance_km,

            "total_driving_minutes":
                self.total_driving_minutes,

            "total_service_minutes":
                self.total_service_minutes,

            "total_route_minutes":
                self.total_route_minutes,

            "peak_weight_kg":
                self.peak_weight_kg,

            "peak_volume_l":
                self.peak_volume_l,

            "peak_weight_utilization":
                self.peak_weight_utilization,

            "peak_volume_utilization":
                self.peak_volume_utilization,

            "customer_delivery_revenue":
                self.customer_delivery_revenue,

            "road_provider":
                self.road_provider,

            "traffic_aware":
                self.traffic_aware,

            "stops": [
                stop.to_dict()
                for stop
                in self.stops
            ],
        }


@dataclass(
    frozen=True
)
class _Node:
    key: str

    stop_type: str

    latitude: float
    longitude: float

    supplier_id: int | None

    order_id: int | None

    related_order_ids: tuple[
            int,
            ...
        ]

    location_label: str | None

    weight_delta_kg: float
    volume_delta_l: float

    service_minutes: float

    prerequisite_keys: tuple[
            str,
            ...
        ]

    delivery_deadline_minutes: float | None


@dataclass(
    frozen=True
)
class _SearchState:
    visited_mask: int

    current_matrix_index: int

    elapsed_seconds: float
    distance_meters: float

    load_weight_kg: float
    load_volume_l: float

    peak_weight_kg: float
    peak_volume_l: float

    route_node_indexes: tuple[
            int,
            ...
        ]

    arrivals_seconds: tuple[
            float,
            ...
        ]


def _validate_orders(
    orders: Iterable[
        BatchOrderInput
    ],
):
    seen = set()

    for order in orders:

        if (
            order.order_id
            in seen
        ):
            raise ValueError(
                "Duplicate order in batch."
            )

        seen.add(
            order.order_id
        )

        if not order.pickups:
            raise ValueError(
                f"Order {order.order_id} "
                "has no pickup locations."
            )

        if (
            order.delivery_fee
            < 0
        ):
            raise ValueError(
                "Delivery fee cannot be negative."
            )

        for pickup in order.pickups:

            if (
                pickup.weight_kg
                < 0
                or
                pickup.volume_l
                < 0
            ):
                raise ValueError(
                    "Cargo dimensions cannot be negative."
                )


def _pickup_group_key(
    pickup: PickupInput,
) -> tuple:

    return (
        pickup.supplier_id,

        round(
            float(
                pickup.latitude
            ),
            6,
        ),

        round(
            float(
                pickup.longitude
            ),
            6,
        ),
    )


def _build_nodes(
    orders: list[
        BatchOrderInput
    ],
) -> list[
    _Node
]:
    """
    Same supplier/location across multiple customer orders becomes
    ONE pickup stop.

    This is one of the big batching advantages.
    """

    pickup_groups = {}

    order_pickup_keys = {
        order.order_id:
            set()
        for order in orders
    }

    for order in orders:

        for pickup in order.pickups:

            group = (
                _pickup_group_key(
                    pickup
                )
            )

            if (
                group
                not in pickup_groups
            ):
                pickup_groups[
                    group
                ] = {
                    "supplier_id":
                        pickup.supplier_id,

                    "latitude":
                        float(
                            pickup.latitude
                        ),

                    "longitude":
                        float(
                            pickup.longitude
                        ),

                    "weight_kg":
                        0.0,

                    "volume_l":
                        0.0,

                    "service_minutes":
                        0.0,

                    "order_ids":
                        set(),

                    "location_label":
                        pickup.location_label,
                }

            current = (
                pickup_groups[
                    group
                ]
            )

            current[
                "weight_kg"
            ] += float(
                pickup.weight_kg
            )

            current[
                "volume_l"
            ] += float(
                pickup.volume_l
            )

            # One supplier stop does not take
            # full setup time separately per order.
            current[
                "service_minutes"
            ] = max(
                current[
                    "service_minutes"
                ],

                float(
                    pickup.service_minutes
                ),
            )

            current[
                "order_ids"
            ].add(
                order.order_id
            )

    nodes = []

    pickup_key_lookup = {}

    for index, (
        group,
        data,
    ) in enumerate(
        pickup_groups.items(),
        start=1,
    ):
        key = (
            f"pickup:{index}:"
            f"{data['supplier_id']}"
        )

        pickup_key_lookup[
            group
        ] = key

        for order_id in (
            data[
                "order_ids"
            ]
        ):
            order_pickup_keys[
                order_id
            ].add(
                key
            )

        nodes.append(
            _Node(
                key=
                    key,

                stop_type=
                    "pickup",

                latitude=
                    data[
                        "latitude"
                    ],

                longitude=
                    data[
                        "longitude"
                    ],

                supplier_id=
                    data[
                        "supplier_id"
                    ],

                order_id=
                    None,

                related_order_ids=
                    tuple(
                        sorted(
                            data[
                                "order_ids"
                            ]
                        )
                    ),

                location_label=
                    data[
                        "location_label"
                    ],

                weight_delta_kg=
                    data[
                        "weight_kg"
                    ],

                volume_delta_l=
                    data[
                        "volume_l"
                    ],

                service_minutes=
                    data[
                        "service_minutes"
                    ],

                prerequisite_keys=
                    tuple(),

                delivery_deadline_minutes=
                    None,
            )
        )

    for order in orders:

        total_weight = sum(
            float(
                pickup.weight_kg
            )
            for pickup
            in order.pickups
        )

        total_volume = sum(
            float(
                pickup.volume_l
            )
            for pickup
            in order.pickups
        )

        nodes.append(
            _Node(
                key=
                    f"delivery:{order.order_id}",

                stop_type=
                    "delivery",

                latitude=
                    float(
                        order.customer_latitude
                    ),

                longitude=
                    float(
                        order.customer_longitude
                    ),

                supplier_id=
                    None,

                order_id=
                    order.order_id,

                related_order_ids=(
                    order.order_id,
                ),

                location_label=
                    order.customer_label,

                weight_delta_kg=
                    -total_weight,

                volume_delta_l=
                    -total_volume,

                service_minutes=
                    float(
                        order.delivery_service_minutes
                    ),

                prerequisite_keys=
                    tuple(
                        sorted(
                            order_pickup_keys[
                                order.order_id
                            ]
                        )
                    ),

                delivery_deadline_minutes=
                    order.max_delivery_minutes,
            )
        )

    return nodes


def _empty_rejection(
    *,
    orders: list[
            BatchOrderInput
        ],

    reason: str,

) -> BatchPlan:

    return BatchPlan(
        planner_version=
            PLANNER_VERSION,

        feasible=
            False,

        rejection_reason=
            reason,

        order_ids=
            tuple(
                order.order_id
                for order in orders
            ),

        order_count=
            len(orders),

        pickup_count=
            0,

        delivery_count=
            len(orders),

        total_distance_km=
            0.0,

        total_driving_minutes=
            0.0,

        total_service_minutes=
            0.0,

        total_route_minutes=
            0.0,

        peak_weight_kg=
            0.0,

        peak_volume_l=
            0.0,

        peak_weight_utilization=
            0.0,

        peak_volume_utilization=
            0.0,

        customer_delivery_revenue=
            round(
                sum(
                    order.delivery_fee
                    for order in orders
                ),
                2,
            ),

        road_provider=
            None,

        traffic_aware=
            False,

        stops=
            tuple(),
    )


def plan_batch_route(
    *,
    orders: list[
            BatchOrderInput
        ],

    capacity: EffectiveVehicleCapacity,

    road_matrix: RoadMatrix | None = None,

    beam_width: int = DEFAULT_BEAM_WIDTH,

    duration_multiplier: float = 1.0,

    max_total_route_minutes: float | None = None,

) -> BatchPlan:
    """
    Plans ONE batch / ONE physical trip.

    Rules:
    - every order must be completely delivered
    - pickup must happen before its customer delivery
    - shared suppliers collapse into one pickup
    - weight checked after EVERY stop
    - volume checked after EVERY stop
    - no hidden second trip
    """

    if not orders:
        raise ValueError(
            "Batch needs at least one order."
        )

    _validate_orders(
        orders
    )

    nodes = _build_nodes(
        orders
    )

    if (
        len(nodes)
        > MAX_ROUTE_NODES
    ):
        return _empty_rejection(
            orders=
                orders,

            reason=(
                "too_many_route_nodes"
            ),
        )

    # --------------------------------------------------------
    # Immediate single-order feasibility.
    #
    # If an individual order itself is bigger than this vehicle,
    # there is no reason to run route optimization.
    # --------------------------------------------------------

    for order in orders:

        order_weight = sum(
            pickup.weight_kg
            for pickup
            in order.pickups
        )

        order_volume = sum(
            pickup.volume_l
            for pickup
            in order.pickups
        )

        if (
            order_weight
            >
            capacity.max_payload_kg
            + EPSILON
        ):
            return _empty_rejection(
                orders=
                    orders,

                reason=(
                    f"order_{order.order_id}"
                    "_exceeds_vehicle_weight"
                ),
            )

        if (
            order_volume
            >
            capacity.max_volume_l
            + EPSILON
        ):
            return _empty_rejection(
                orders=
                    orders,

                reason=(
                    f"order_{order.order_id}"
                    "_exceeds_vehicle_volume"
                ),
            )

    # StoreDash launch policy:
    #
    # Rider position is handled manually by the dispatch
    # operator. The calculated batch route therefore begins
    # at the first supplier pickup and does NOT include rider
    # deadhead travel to that first supplier.
    points = [
        RoadPoint(
            key=
                node.key,

            latitude=
                node.latitude,

            longitude=
                node.longitude,
        )
        for node in nodes
    ]

    if road_matrix is None:
        road_matrix = (
            get_road_matrix(
                points
            )
        )

    if (
        len(
            road_matrix.points
        )
        != len(points)
    ):
        raise ValueError(
            "Road matrix point count does not match planner points."
        )

    duration_multiplier = max(
        float(
            duration_multiplier
        ),
        0.1,
    )

    node_index_by_key = {
        node.key:
            index
        for index, node
        in enumerate(
            nodes
        )
    }

    prerequisite_masks = []

    for node in nodes:

        mask = 0

        for key in (
            node.prerequisite_keys
        ):

            dependency_index = (
                node_index_by_key[
                    key
                ]
            )

            mask |= (
                1
                <<
                dependency_index
            )

        prerequisite_masks.append(
            mask
        )

    all_mask = (
        (1 << len(nodes))
        - 1
    )

    start = _SearchState(
        visited_mask=
            0,

        current_matrix_index=
            0,

        elapsed_seconds=
            0.0,

        distance_meters=
            0.0,

        load_weight_kg=
            0.0,

        load_volume_l=
            0.0,

        peak_weight_kg=
            0.0,

        peak_volume_l=
            0.0,

        route_node_indexes=
            tuple(),

        arrivals_seconds=
            tuple(),
    )

    beam = [
        start
    ]

    for _depth in range(
        len(nodes)
    ):

        candidates = {}

        for state in beam:

            for node_index, node in enumerate(
                nodes
            ):

                bit = (
                    1
                    <<
                    node_index
                )

                if (
                    state.visited_mask
                    & bit
                ):
                    continue

                required = (
                    prerequisite_masks[
                        node_index
                    ]
                )

                if (
                    required
                    &
                    state.visited_mask
                ) != required:
                    continue

                next_matrix_index = (
                    node_index
                )

                # The rider's travel to the first supplier is
                # intentionally outside StoreDash's calculated
                # route for the launch workflow.
                if state.visited_mask == 0:
                    distance = 0.0
                    travel_seconds = 0.0
                else:
                    distance = (
                        road_matrix
                        .distance_meters[
                            state
                            .current_matrix_index
                        ][
                            next_matrix_index
                        ]
                    )

                    travel_seconds = (
                        road_matrix
                        .duration_seconds[
                            state
                            .current_matrix_index
                        ][
                            next_matrix_index
                        ]
                        *
                        duration_multiplier
                    )

                if (
                    distance
                    == float("inf")
                    or
                    travel_seconds
                    == float("inf")
                ):
                    continue

                arrival_seconds = (
                    state.elapsed_seconds
                    +
                    travel_seconds
                )

                if (
                    node.stop_type
                    == "delivery"
                    and
                    node.delivery_deadline_minutes
                    is not None
                    and
                    arrival_seconds
                    >
                    (
                        node.delivery_deadline_minutes
                        * 60.0
                    )
                    + EPSILON
                ):
                    continue

                new_weight = (
                    state.load_weight_kg
                    +
                    node.weight_delta_kg
                )

                new_volume = (
                    state.load_volume_l
                    +
                    node.volume_delta_l
                )

                if (
                    new_weight
                    <
                    -EPSILON
                    or
                    new_volume
                    <
                    -EPSILON
                ):
                    continue

                new_weight = max(
                    new_weight,
                    0.0,
                )

                new_volume = max(
                    new_volume,
                    0.0,
                )

                if (
                    new_weight
                    >
                    capacity.max_payload_kg
                    + EPSILON
                ):
                    continue

                if (
                    new_volume
                    >
                    capacity.max_volume_l
                    + EPSILON
                ):
                    continue

                service_seconds = (
                    max(
                        node.service_minutes,
                        0.0,
                    )
                    *
                    60.0
                )

                elapsed = (
                    arrival_seconds
                    +
                    service_seconds
                )

                if (
                    max_total_route_minutes
                    is not None
                    and
                    elapsed
                    >
                    (
                        max_total_route_minutes
                        * 60
                    )
                    + EPSILON
                ):
                    continue

                new_state = (
                    _SearchState(
                        visited_mask=
                            (
                                state.visited_mask
                                |
                                bit
                            ),

                        current_matrix_index=
                            next_matrix_index,

                        elapsed_seconds=
                            elapsed,

                        distance_meters=
                            (
                                state.distance_meters
                                +
                                distance
                            ),

                        load_weight_kg=
                            new_weight,

                        load_volume_l=
                            new_volume,

                        peak_weight_kg=
                            max(
                                state.peak_weight_kg,
                                new_weight,
                            ),

                        peak_volume_l=
                            max(
                                state.peak_volume_l,
                                new_volume,
                            ),

                        route_node_indexes=
                            (
                                state.route_node_indexes
                                +
                                (
                                    node_index,
                                )
                            ),

                        arrivals_seconds=
                            (
                                state.arrivals_seconds
                                +
                                (
                                    arrival_seconds,
                                )
                            ),
                    )
                )

                # For the same visited stops and current position,
                # vehicle load is deterministic, so keep only the
                # fastest state.
                key = (
                    new_state.visited_mask,
                    new_state.current_matrix_index,
                )

                existing = (
                    candidates.get(
                        key
                    )
                )

                if (
                    existing is None
                    or
                    new_state.elapsed_seconds
                    <
                    existing.elapsed_seconds
                ):
                    candidates[
                        key
                    ] = (
                        new_state
                    )

        if not candidates:
            return _empty_rejection(
                orders=
                    orders,

                reason=(
                    "no_capacity_feasible_"
                    "pickup_delivery_sequence"
                ),
            )

        beam = sorted(
            candidates.values(),

            key=lambda state: (
                state.elapsed_seconds,
                state.distance_meters,
            ),
        )[
            :max(
                int(
                    beam_width
                ),
                20,
            )
        ]

    finished = [
        state
        for state in beam
        if (
            state.visited_mask
            == all_mask
            and
            state.load_weight_kg
            <= EPSILON
            and
            state.load_volume_l
            <= EPSILON
        )
    ]

    if not finished:
        return _empty_rejection(
            orders=
                orders,

            reason=(
                "no_complete_single_trip_route"
            ),
        )

    best = min(
        finished,

        key=lambda state: (
            state.elapsed_seconds,
            state.distance_meters,
        ),
    )

    planned_stops = []

    previous_matrix_index = 0

    total_service_minutes = 0.0

    load_weight = 0.0
    load_volume = 0.0

    peak_weight_util = 0.0
    peak_volume_util = 0.0

    for sequence, (
        node_index,
        arrival_seconds,
    ) in enumerate(
        zip(
            best.route_node_indexes,
            best.arrivals_seconds,
        ),
        start=1,
    ):

        node = (
            nodes[
                node_index
            ]
        )

        matrix_index = (
            node_index
        )

        # Launch routing begins at the first supplier pickup.
        # There is no driver -> first-pickup GPS leg.
        if sequence == 1:
            leg_distance = 0.0
            leg_minutes = 0.0
        else:
            leg_distance = (
                road_matrix
                .distance_meters[
                    previous_matrix_index
                ][
                    matrix_index
                ]
            )

            leg_minutes = (
                road_matrix
                .duration_seconds[
                    previous_matrix_index
                ][
                    matrix_index
                ]
                *
                duration_multiplier
                /
                60.0
            )

        load_weight += (
            node.weight_delta_kg
        )

        load_volume += (
            node.volume_delta_l
        )

        load_weight = max(
            load_weight,
            0.0,
        )

        load_volume = max(
            load_volume,
            0.0,
        )

        weight_util = (
            load_weight
            /
            capacity.max_payload_kg
        )

        volume_util = (
            load_volume
            /
            capacity.max_volume_l
        )

        peak_weight_util = max(
            peak_weight_util,
            weight_util,
        )

        peak_volume_util = max(
            peak_volume_util,
            volume_util,
        )

        total_service_minutes += (
            node.service_minutes
        )

        planned_stops.append(
            PlannedStop(
                sequence=
                    sequence,

                key=
                    node.key,

                stop_type=
                    node.stop_type,

                latitude=
                    node.latitude,

                longitude=
                    node.longitude,

                supplier_id=
                    node.supplier_id,

                order_id=
                    node.order_id,

                related_order_ids=
                    node.related_order_ids,

                location_label=
                    node.location_label,

                travel_from_previous_km=
                    round(
                        leg_distance
                        / 1000.0,
                        3,
                    ),

                travel_from_previous_minutes=
                    round(
                        leg_minutes,
                        2,
                    ),

                arrival_minutes=
                    round(
                        arrival_seconds
                        / 60.0,
                        2,
                    ),

                service_minutes=
                    round(
                        node.service_minutes,
                        2,
                    ),

                weight_delta_kg=
                    round(
                        node.weight_delta_kg,
                        3,
                    ),

                volume_delta_l=
                    round(
                        node.volume_delta_l,
                        3,
                    ),

                load_weight_after_kg=
                    round(
                        load_weight,
                        3,
                    ),

                load_volume_after_l=
                    round(
                        load_volume,
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

        previous_matrix_index = (
            matrix_index
        )

    driving_minutes = (
        sum(
            stop.travel_from_previous_minutes
            for stop
            in planned_stops
        )
    )

    return BatchPlan(
        planner_version=
            PLANNER_VERSION,

        feasible=
            True,

        rejection_reason=
            None,

        order_ids=
            tuple(
                order.order_id
                for order
                in orders
            ),

        order_count=
            len(orders),

        pickup_count=
            sum(
                stop.stop_type
                == "pickup"
                for stop
                in planned_stops
            ),

        delivery_count=
            len(orders),

        total_distance_km=
            round(
                best.distance_meters
                / 1000.0,
                3,
            ),

        total_driving_minutes=
            round(
                driving_minutes,
                2,
            ),

        total_service_minutes=
            round(
                total_service_minutes,
                2,
            ),

        total_route_minutes=
            round(
                best.elapsed_seconds
                / 60.0,
                2,
            ),

        peak_weight_kg=
            round(
                best.peak_weight_kg,
                3,
            ),

        peak_volume_l=
            round(
                best.peak_volume_l,
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

        customer_delivery_revenue=
            round(
                sum(
                    order.delivery_fee
                    for order
                    in orders
                ),
                2,
            ),

        road_provider=
            road_matrix.provider,

        traffic_aware=
            road_matrix.traffic_aware,

        stops=
            tuple(
                planned_stops
            ),
    )
