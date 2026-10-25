import sqlite3


db = sqlite3.connect(
    "storedash.db"
)

existing = {
    row[1]
    for row in db.execute(
        "PRAGMA table_info(order_items)"
    )
}


columns = {
    "logistics_variant_key":
        "TEXT",

    "logistics_size_detail":
        "TEXT",

    "physical_material_class":
        "TEXT",

    "physical_estimation_source":
        "TEXT",

    "physical_confidence":
        "REAL",
}


for name, sql_type in columns.items():

    if name in existing:
        print(
            name,
            "already exists"
        )
        continue

    db.execute(
        f"""
        ALTER TABLE order_items
        ADD COLUMN {name} {sql_type}
        """
    )

    print(
        "Added",
        name
    )


db.commit()
db.close()

print(
    "Logistics variant migration complete."
)
