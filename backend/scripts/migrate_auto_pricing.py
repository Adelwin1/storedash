import sqlite3

db = sqlite3.connect("storedash.db")
cursor = db.cursor()

existing = {
    row[1]
    for row in cursor.execute(
        "PRAGMA table_info(orders)"
    )
}

columns = {
    "tax_total": "NUMERIC(12,2) DEFAULT 0",
    "route_distance_km": "FLOAT",
    "route_duration_minutes": "FLOAT",
    "supplier_stop_count": "INTEGER",
    "total_load_units": "FLOAT",
    "driver_floor": "NUMERIC(12,2)",
    "driver_target": "NUMERIC(12,2)",
    "driver_ceiling": "NUMERIC(12,2)",
    "pricing_version": "VARCHAR(40)",
}

for name, sql_type in columns.items():
    if name not in existing:
        cursor.execute(
            f"ALTER TABLE orders ADD COLUMN {name} {sql_type}"
        )
        print("Added:", name)

db.commit()
db.close()

print("Automatic pricing migration complete.")
