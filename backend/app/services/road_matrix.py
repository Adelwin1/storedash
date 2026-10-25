from __future__ import annotations

from dataclasses import (
    asdict,
    dataclass,
)

import json
import ssl
import urllib.request

import certifi


OSRM_BASE = (
    "https://router.project-osrm.org"
)

MAX_MATRIX_POINTS = 60


@dataclass(
    frozen=True
)
class RoadPoint:
    key: str
    latitude: float
    longitude: float

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(
    frozen=True
)
class RoadMatrix:
    points: tuple[
        RoadPoint,
        ...
    ]

    distance_meters: tuple[
        tuple[
            float,
            ...
        ],
        ...
    ]

    duration_seconds: tuple[
        tuple[
            float,
            ...
        ],
        ...
    ]

    provider: str

    # Public OSRM does NOT provide live traffic.
    traffic_aware: bool

    def to_dict(self) -> dict:
        return {
            "points": [
                point.to_dict()
                for point in self.points
            ],

            "distance_meters": [
                list(row)
                for row
                in self.distance_meters
            ],

            "duration_seconds": [
                list(row)
                for row
                in self.duration_seconds
            ],

            "provider":
                self.provider,

            "traffic_aware":
                self.traffic_aware,
        }


def _matrix_value(
    value,
) -> float:

    if value is None:
        return float("inf")

    return float(value)


def get_road_matrix(
    points: list[
        RoadPoint
    ],
) -> RoadMatrix:
    """
    Gets road distance/time between every pair of points.

    The planner is deliberately separate from OSRM so StoreDash
    can later replace this provider with a traffic-aware provider
    without rewriting the batching algorithm.
    """

    if len(points) < 2:
        raise ValueError(
            "Road matrix needs at least two points."
        )

    if (
        len(points)
        > MAX_MATRIX_POINTS
    ):
        raise ValueError(
            "Too many route points for one matrix request. "
            f"Maximum supported by StoreDash right now: "
            f"{MAX_MATRIX_POINTS}."
        )

    coordinates = ";".join(
        (
            f"{float(point.longitude):.7f},"
            f"{float(point.latitude):.7f}"
        )
        for point in points
    )

    url = (
        f"{OSRM_BASE}"
        f"/table/v1/driving/"
        f"{coordinates}"
        "?annotations=duration,distance"
    )

    request = urllib.request.Request(
        url,
        headers={
            "User-Agent":
                "StoreDash-MVP/1.0 "
                "(internal logistics application)",
        },
    )

    context = (
        ssl.create_default_context(
            cafile=
                certifi.where()
        )
    )

    with urllib.request.urlopen(
        request,
        timeout=20,
        context=context,
    ) as response:

        data = json.loads(
            response
            .read()
            .decode(
                "utf-8"
            )
        )

    if data.get("code") != "Ok":
        raise ValueError(
            "Road-matrix request failed: "
            f"{data.get('code', 'unknown')}"
        )

    raw_distances = (
        data.get("distances")
    )

    raw_durations = (
        data.get("durations")
    )

    if (
        not raw_distances
        or
        not raw_durations
    ):
        raise ValueError(
            "Road service returned no usable matrix."
        )

    distances = tuple(
        tuple(
            _matrix_value(
                value
            )
            for value
            in row
        )
        for row
        in raw_distances
    )

    durations = tuple(
        tuple(
            _matrix_value(
                value
            )
            for value
            in row
        )
        for row
        in raw_durations
    )

    return RoadMatrix(
        points=
            tuple(points),

        distance_meters=
            distances,

        duration_seconds=
            durations,

        provider=
            "osrm",

        traffic_aware=
            False,
    )
