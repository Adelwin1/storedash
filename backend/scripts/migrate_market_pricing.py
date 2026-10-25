import sqlite3


DB_PATH = "storedash.db"


COLUMNS = {
    "estimated_driver_market_cost":
        "NUMERIC(12, 2)",

    "estimated_customer_willingness":
        "NUMERIC(12, 2)",

    "driver_acceptance_probability":
        "FLOAT",

    "customer_acceptance_probability":
        "FLOAT",

    "delivery_margin":
        "NUMERIC(12, 2)",

    "optimizer_score":
        "FLOAT",
}


connection = sqlite3.connect(
    DB_PATH
)

cursor = connection.cursor()


existing = {
    row[1]
    for row in cursor.execute(
        "PRAGMA table_info(orders)"
    ).fetchall()
}


for name, sql_type in COLUMNS.items():

    if name in existing:
        print(
            f"{name} already exists"
        )
        continue

    cursor.execute(
        f"""
        ALTER TABLE orders
        ADD COLUMN {name} {sql_type}
        """
    )

    print(
        f"Added {name}"
    )


connection.commit()
connection.close()

print(
    "Market pricing migration complete."
)
