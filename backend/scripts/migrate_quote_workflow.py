import sqlite3

connection = sqlite3.connect(
    "storedash.db"
)

cursor = connection.cursor()

columns = {
    row[1]
    for row in cursor.execute(
        "PRAGMA table_info(orders)"
    ).fetchall()
}

needed = {
    "quote_generated_at":
        "DATETIME",

    "customer_approved_at":
        "DATETIME",
}

for name, data_type in needed.items():
    if name not in columns:
        cursor.execute(
            f"""
            ALTER TABLE orders
            ADD COLUMN {name} {data_type}
            """
        )

        print(
            "Added:",
            name,
        )

connection.commit()
connection.close()

print(
    "Quote workflow migration complete."
)
