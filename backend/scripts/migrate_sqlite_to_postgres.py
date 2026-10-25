import argparse
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

from sqlalchemy import create_engine, func, select, text

from app.core.db import Base
import app.models.entities  # noqa: F401


DEFAULT_SOURCE = BACKEND_DIR / "storedash.db"


def parse_args():
    parser = argparse.ArgumentParser(
        description="Migrate StoreDash SQLite data to PostgreSQL."
    )

    parser.add_argument(
        "--source",
        default=str(DEFAULT_SOURCE),
    )

    parser.add_argument(
        "--target",
        required=True,
    )

    return parser.parse_args()


def build_engines(source_path: str, target_url: str):
    source = Path(source_path).resolve()

    source_engine = create_engine(
        f"sqlite+pysqlite:///file:{source}?mode=ro&uri=true"
    )

    target_engine = create_engine(
        target_url
    )

    return source_engine, target_engine


def ensure_target_empty(target_engine):
    dirty = []

    with target_engine.connect() as conn:
        for table in Base.metadata.sorted_tables:
            count = conn.scalar(
                select(func.count()).select_from(table)
            )

            if count:
                dirty.append(
                    (table.name, count)
                )

    if dirty:
        raise SystemExit(
            f"STOP: target database is not empty: {dirty}"
        )


def copy_rows(source_engine, target_engine):
    with source_engine.connect() as src, target_engine.begin() as dst:
        for table in Base.metadata.sorted_tables:
            rows = src.execute(
                select(table)
            ).mappings().all()

            if rows:
                dst.execute(
                    table.insert(),
                    [dict(row) for row in rows],
                )

            print(
                f"{table.name}: copied {len(rows)}"
            )

    print("DATA COPY COMPLETE")


def validate_counts(source_engine, target_engine):
    all_good = True

    with source_engine.connect() as src, target_engine.connect() as dst:
        for table in Base.metadata.sorted_tables:
            source_count = src.scalar(
                select(func.count()).select_from(table)
            )
            target_count = dst.scalar(
                select(func.count()).select_from(table)
            )

            status = (
                "OK"
                if source_count == target_count
                else "MISMATCH"
            )

            print(
                f"{table.name}: "
                f"sqlite={source_count} "
                f"postgres={target_count} "
                f"{status}"
            )

            if source_count != target_count:
                all_good = False

    if not all_good:
        raise SystemExit(
            "STOP: table count validation failed."
        )

    print("ALL TABLE COUNTS MATCH")


def reset_sequences(target_engine):
    with target_engine.begin() as conn:
        for table in Base.metadata.sorted_tables:
            if "id" not in table.c:
                continue

            sequence = conn.scalar(
                text(
                    "SELECT pg_get_serial_sequence("
                    ":table_name, 'id'"
                    ")"
                ),
                {"table_name": table.name},
            )

            if not sequence:
                continue

            max_id = conn.scalar(
                text(
                    f'SELECT MAX(id) FROM "{table.name}"'
                )
            )

            if max_id is None:
                conn.execute(
                    text(
                        "SELECT setval("
                        "CAST(:sequence AS regclass), "
                        "1, false)"
                    ),
                    {"sequence": sequence},
                )
            else:
                conn.execute(
                    text(
                        "SELECT setval("
                        "CAST(:sequence AS regclass), "
                        ":max_id, true)"
                    ),
                    {
                        "sequence": sequence,
                        "max_id": max_id,
                    },
                )

    print("POSTGRESQL SEQUENCES RESET")


def main():
    args = parse_args()

    source_engine, target_engine = build_engines(
        args.source,
        args.target,
    )

    print("Checking target database...")
    ensure_target_empty(target_engine)

    print("Copying StoreDash data...")
    copy_rows(source_engine, target_engine)

    print("Validating migrated data...")
    validate_counts(source_engine, target_engine)

    print("Resetting PostgreSQL sequences...")
    reset_sequences(target_engine)

    print("MIGRATION COMPLETE")


if __name__ == "__main__":
    main()
