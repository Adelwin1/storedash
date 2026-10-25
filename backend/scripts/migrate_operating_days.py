import sqlite3

from datetime import (
    date,
    datetime,
)


DATABASE = "storedash.db"


connection = sqlite3.connect(
    DATABASE
)

connection.row_factory = (
    sqlite3.Row
)

cursor = connection.cursor()


cursor.execute(
    """
    CREATE TABLE IF NOT EXISTS operating_days (
        id INTEGER PRIMARY KEY,
        business_date DATE NOT NULL UNIQUE,
        opened_at DATETIME NOT NULL,
        closed_at DATETIME,
        is_closed BOOLEAN NOT NULL DEFAULT 0,
        closed_by_id INTEGER,
        notes TEXT,
        created_at DATETIME NOT NULL,
        updated_at DATETIME NOT NULL
    )
    """
)


columns = {
    row["name"]
    for row
    in cursor.execute(
        "PRAGMA table_info(orders)"
    ).fetchall()
}


needed_columns = {
    "operating_day_id":
        "INTEGER",

    "daily_number":
        "INTEGER",

    "finalized_at":
        "DATETIME",

    "completed_at":
        "DATETIME",
}


for (
    column_name,
    column_type,
) in needed_columns.items():

    if column_name not in columns:

        cursor.execute(
            f"""
            ALTER TABLE orders
            ADD COLUMN
            {column_name}
            {column_type}
            """
        )

        print(
            "Added column:",
            column_name,
        )


cursor.execute(
    """
    CREATE UNIQUE INDEX IF NOT EXISTS
    uq_orders_operating_day_daily_number
    ON orders(
        operating_day_id,
        daily_number
    )
    """
)


rows = cursor.execute(
    """
    SELECT
        id,
        created_at,
        operating_day_id,
        daily_number,
        status
    FROM orders
    ORDER BY created_at, id
    """
).fetchall()


orders_by_date = {}


for row in rows:

    created_at = (
        row["created_at"]
        or datetime.utcnow().isoformat()
    )

    business_date = (
        str(created_at)[0:10]
    )

    orders_by_date.setdefault(
        business_date,
        []
    ).append(
        row
    )


today = str(
    date.today()
)


for (
    business_date,
    day_orders,
) in orders_by_date.items():

    existing_day = cursor.execute(
        """
        SELECT id
        FROM operating_days
        WHERE business_date = ?
        """,
        (
            business_date,
        ),
    ).fetchone()


    if existing_day:

        day_id = (
            existing_day["id"]
        )

    else:

        first_created = (
            day_orders[0][
                "created_at"
            ]
            or f"{business_date} 08:00:00"
        )


        is_closed = (
            1
            if business_date < today
            else 0
        )


        closed_at = (
            f"{business_date} 18:00:00"
            if is_closed
            else None
        )


        cursor.execute(
            """
            INSERT INTO operating_days (
                business_date,
                opened_at,
                closed_at,
                is_closed,
                created_at,
                updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                business_date,
                first_created,
                closed_at,
                is_closed,
                first_created,
                first_created,
            ),
        )


        day_id = (
            cursor.lastrowid
        )


    for (
        index,
        order,
    ) in enumerate(
        day_orders,
        start=1,
    ):

        cursor.execute(
            """
            UPDATE orders
            SET
                operating_day_id = ?,
                daily_number = ?
            WHERE id = ?
            """,
            (
                day_id,
                index,
                order["id"],
            ),
        )


connection.commit()


print()
print(
    "Operating-day migration complete."
)

print(
    f"Backfilled {len(rows)} existing order(s)."
)

print(
    f"Created/updated {len(orders_by_date)} operating day(s)."
)


for row in cursor.execute(
    """
    SELECT
        od.business_date,
        od.is_closed,
        COUNT(o.id) AS order_count,
        MIN(o.daily_number) AS first_number,
        MAX(o.daily_number) AS last_number
    FROM operating_days od
    LEFT JOIN orders o
        ON o.operating_day_id = od.id
    GROUP BY od.id
    ORDER BY od.business_date
    """
):

    print(
        dict(row)
    )


connection.close()
