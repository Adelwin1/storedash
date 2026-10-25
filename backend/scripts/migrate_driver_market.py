import sqlite3


conn = sqlite3.connect("storedash.db")
cur = conn.cursor()


def add_columns(table, columns):
    existing = {
        row[1]
        for row in cur.execute(
            f"PRAGMA table_info({table})"
        )
    }

    for name, sql_type in columns.items():
        if name in existing:
            print(f"{table}.{name} already exists")
            continue

        cur.execute(
            f"ALTER TABLE {table} "
            f"ADD COLUMN {name} {sql_type}"
        )

        print(f"Added {table}.{name}")


add_columns(
    "drivers",
    {
        "vehicle_registration": "TEXT",
        "payment_phone": "TEXT",
        "payment_name": "TEXT",
        "notes": "TEXT",
        "is_active": "BOOLEAN DEFAULT 1",
    },
)


add_columns(
    "orders",
    {
        "assigned_driver_id": "INTEGER",
        "driver_payout": "NUMERIC(12,2)",
        "driver_assigned_at": "DATETIME",
    },
)


add_columns(
    "driver_offers",
    {
        "driver_quote": "NUMERIC(12,2)",
        "auto_accept_limit": "NUMERIC(12,2)",
        "normal_negotiation_max": "NUMERIC(12,2)",
        "current_authorized_offer": "NUMERIC(12,2)",
        "counter_round": "INTEGER DEFAULT 0",
        "company_delivery_share": "NUMERIC(12,2)",
        "released_driver_reserve": "NUMERIC(12,2)",
        "locked_at": "DATETIME",
    },
)


cur.execute("""
CREATE TABLE IF NOT EXISTS driver_negotiation_events (
    id INTEGER PRIMARY KEY,
    driver_offer_id INTEGER NOT NULL,
    order_id INTEGER NOT NULL,
    driver_id INTEGER NOT NULL,
    operator_id INTEGER,
    event_type VARCHAR(60) NOT NULL,
    amount NUMERIC(12,2),
    details TEXT,
    created_at DATETIME,

    FOREIGN KEY(driver_offer_id)
        REFERENCES driver_offers(id),

    FOREIGN KEY(order_id)
        REFERENCES orders(id),

    FOREIGN KEY(driver_id)
        REFERENCES drivers(id),

    FOREIGN KEY(operator_id)
        REFERENCES users(id)
)
""")


cur.execute("""
CREATE INDEX IF NOT EXISTS
ix_driver_negotiation_events_offer
ON driver_negotiation_events(driver_offer_id)
""")


cur.execute("""
CREATE INDEX IF NOT EXISTS
ix_driver_negotiation_events_order
ON driver_negotiation_events(order_id)
""")


conn.commit()
conn.close()

print("Driver market migration complete.")
