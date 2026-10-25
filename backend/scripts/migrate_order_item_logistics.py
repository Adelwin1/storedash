import sqlite3

connection = sqlite3.connect("storedash.db")
cursor = connection.cursor()

columns = {
    row[1]
    for row in cursor.execute(
        "PRAGMA table_info(order_items)"
    ).fetchall()
}

needed = {
    "logistics_category_id": "INTEGER",
    "logistics_type_id": "INTEGER",
    "logistics_size_class": "VARCHAR(20)",
    "load_units_each": "FLOAT",
    "total_load_units": "FLOAT",
}

for name, data_type in needed.items():
    if name not in columns:
        cursor.execute(
            f"""
            ALTER TABLE order_items
            ADD COLUMN {name} {data_type}
            """
        )
        print("Added:", name)

connection.commit()
connection.close()

print("Order item logistics migration complete.")
