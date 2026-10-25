from pathlib import Path
import sqlite3
import sys


ROOT = Path(
    __file__
).resolve().parents[1]

if str(ROOT) not in sys.path:
    sys.path.insert(
        0,
        str(ROOT),
    )


from app.core.db import (
    Base,
    engine,
)

import app.models  # noqa: F401


Base.metadata.create_all(
    bind=engine
)


db_path = (
    ROOT
    / "storedash.db"
)

db = sqlite3.connect(
    db_path
)


def columns(
    table: str,
) -> set[str]:
    return {
        row[1]
        for row in db.execute(
            f'PRAGMA table_info("{table}")'
        )
    }


def add_column(
    table: str,
    name: str,
    definition: str,
):
    existing = columns(
        table
    )

    if name in existing:
        print(
            table,
            name,
            "already exists"
        )
        return

    db.execute(
        f'''
        ALTER TABLE "{table}"
        ADD COLUMN "{name}" {definition}
        '''
    )

    print(
        table,
        name,
        "added"
    )


add_column(
    "delivery_batches",
    "planner_version",
    "TEXT",
)

add_column(
    "delivery_batches",
    "road_provider",
    "TEXT",
)

add_column(
    "delivery_batches",
    "traffic_aware",
    "BOOLEAN",
)

add_column(
    "delivery_batches",
    "recommended_at",
    "DATETIME",
)


add_column(
    "batch_stops",
    "planned_leg_distance_km",
    "FLOAT NOT NULL DEFAULT 0",
)

add_column(
    "batch_stops",
    "planned_leg_minutes",
    "FLOAT NOT NULL DEFAULT 0",
)

add_column(
    "batch_stops",
    "planned_arrival_offset_minutes",
    "FLOAT NOT NULL DEFAULT 0",
)


db.commit()
db.close()


print(
    "Batch dispatch migration complete."
)
