from pathlib import Path
import sqlite3


ROOT = Path(
    __file__
).resolve().parents[1]

db = sqlite3.connect(
    ROOT / "storedash.db"
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


def add(
    name: str,
    definition: str,
):

    if name in columns(
        "orders"
    ):
        print(
            name,
            "already exists"
        )
        return

    db.execute(
        f'''
        ALTER TABLE orders
        ADD COLUMN "{name}" {definition}
        '''
    )

    print(
        name,
        "added"
    )


add(
    "payment_amount",
    "NUMERIC(12,2)",
)

add(
    "payment_method",
    "VARCHAR(40)",
)

add(
    "payment_reference",
    "VARCHAR(120)",
)

add(
    "payment_notes",
    "TEXT",
)

add(
    "payment_confirmed_at",
    "DATETIME",
)

add(
    "preparation_started_at",
    "DATETIME",
)

add(
    "ready_for_dispatch_at",
    "DATETIME",
)


db.commit()
db.close()

print(
    "Payment workflow migration complete."
)
