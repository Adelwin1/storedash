import sqlite3

db = sqlite3.connect("storedash.db")
cur = db.cursor()


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
            f"ALTER TABLE {table} ADD COLUMN {name} {sql_type}"
        )

        print(f"Added {table}.{name}")


add_columns(
    "logistics_types",
    {
        "weight_kg_each": "FLOAT",
        "volume_l_each": "FLOAT",
        "handling_score_each": "FLOAT",
        "fragility_score_each": "FLOAT",
    },
)

add_columns(
    "order_items",
    {
        "logistics_package_type": "TEXT",
        "weight_kg_each": "FLOAT",
        "volume_l_each": "FLOAT",
        "handling_score_each": "FLOAT",
        "fragility_score_each": "FLOAT",
        "total_weight_kg": "FLOAT",
        "total_volume_l": "FLOAT",
        "total_handling_score": "FLOAT",
        "total_fragility_score": "FLOAT",
        "physical_profile_version": "TEXT",
    },
)

add_columns(
    "orders",
    {
        "total_weight_kg": "FLOAT",
        "total_volume_l": "FLOAT",
        "total_handling_score": "FLOAT",
        "total_fragility_score": "FLOAT",
    },
)

db.commit()
db.close()

print("Physical pricing migration complete.")
