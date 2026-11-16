from sqlalchemy import select

from app.core.db import (
    Base,
    SessionLocal,
    engine,
)

from app.models import (
    LogisticsCategory,
    LogisticsType,
)


Base.metadata.create_all(
    bind=engine
)


CATEGORIES = [
    # code, name, small, medium, large
    ("general_goods", "General Goods", 1, 4, 8),

    ("soft_drinks", "Soft Drinks", 1, 5, 10),
    ("water", "Water", 1, 5, 10),
    ("juice", "Juice", 1, 4, 8),
    ("malt_energy", "Malt & Energy Drinks", 1, 5, 10),

    ("milk_dairy", "Milk & Dairy", 1, 4, 8),
    ("powdered_drinks", "Powdered Drinks", 1, 4, 8),
    ("tea_coffee_cocoa", "Tea, Coffee & Cocoa", 1, 3, 7),

    ("rice_grains", "Rice, Grains & Pulses", 2, 6, 12),
    ("flour_sugar_salt", "Flour, Sugar & Salt", 2, 6, 12),
    ("pasta_noodles", "Pasta & Noodles", 1, 4, 8),
    ("breakfast_cereal", "Breakfast Cereal", 1, 4, 8),

    ("cooking_oil", "Cooking Oil", 1, 5, 10),
    ("spreads", "Spreads & Margarine", 1, 3, 7),
    ("canned_foods", "Canned & Tinned Foods", 1, 4, 8),
    ("tomato_sauces", "Tomato, Sauces & Condiments", 1, 4, 9),
    ("spices_seasoning", "Spices & Seasoning", 1, 3, 6),

    ("biscuits_snacks", "Biscuits & Snacks", 1, 4, 8),
    ("sweets_chocolate", "Sweets & Chocolate", 1, 3, 7),
    ("bakery", "Bread & Bakery", 1, 4, 8),
    ("eggs", "Eggs", 2, 5, 10),

    ("frozen_food", "Frozen Food", 2, 6, 12),

    # Agogo launch foodstuffs. These are logistics categories,
    # separate from the three market-facing operator categories.
    ("roots_tubers", "Roots & Tubers", 2, 6, 12),
    ("plantain_banana", "Plantain & Banana", 2, 6, 12),
    ("fresh_vegetables", "Fresh Vegetables", 1, 5, 10),
    ("fresh_fruits", "Fresh Fruits", 1, 5, 10),
    ("dried_fish", "Smoked & Dried Fish", 1, 4, 8),

    ("baby_food", "Baby Food & Formula", 1, 4, 8),
    ("diapers_wipes", "Diapers & Baby Wipes", 2, 6, 12),

    ("laundry_cleaning", "Laundry & Cleaning", 1, 5, 10),
    ("tissue_paper", "Tissue & Paper Products", 2, 6, 12),
    ("disposables", "Disposable Household Items", 1, 4, 8),

    ("oral_care", "Oral Care", 1, 3, 6),
    ("soap_bodywash", "Soap & Body Wash", 1, 4, 8),
    ("personal_care", "Personal Care", 1, 3, 7),

    ("skincare", "Skincare", 1, 3, 6),
    ("haircare", "Haircare", 1, 4, 8),
    ("fragrance", "Perfume & Fragrance", 1, 3, 6),
    ("makeup", "Makeup", 1, 3, 6),
    ("nails", "Nail Products", 1, 3, 6),

    ("hair_extensions", "Wigs & Hair Extensions", 1, 4, 9),
    ("beauty_tools", "Beauty Tools & Accessories", 1, 4, 8),
    ("beauty_appliances", "Beauty Appliances", 2, 5, 10),

    # Agogo launch utensils/plastics.
    ("household_plastics", "Household Plastics", 1, 4, 8),
    ("kitchenware", "Kitchenware", 1, 4, 8),
    ("household_tools", "Household Tools", 1, 4, 8),
]


TYPES = {
    "soft_drinks": [
        ("Soft drink bottle", "bottle", 1),
        ("Soft drink can", "can", 1),
        ("Soft drink pack", "pack", 3),
        ("Soft drink crate", "crate", 7),
        ("Soft drink carton", "carton", 5),
    ],

    "water": [
        ("Water bottle", "bottle", 1),
        ("Water sachet bag", "bag", 5),
        ("Water bottle pack", "pack", 4),
        ("Water carton", "carton", 6),
    ],

    "juice": [
        ("Juice bottle", "bottle", 1),
        ("Juice carton", "carton", 5),
        ("Juice pack", "pack", 3),
        ("Juice box", "box", 2),
    ],

    "malt_energy": [
        ("Malt bottle", "bottle", 1),
        ("Malt can", "can", 1),
        ("Malt crate", "crate", 7),
        ("Energy drink can", "can", 1),
        ("Energy drink pack", "pack", 3),
    ],

    "milk_dairy": [
        ("Milk tin", "tin", 1),
        ("Milk can", "can", 1),
        ("Milk sachet", "sachet", 1),
        ("Milk pouch", "pouch", 2),
        ("Milk carton", "carton", 4),
        ("Milk bottle", "bottle", 1),
        ("Milk tub", "tub", 2),
    ],

    "powdered_drinks": [
        ("Powdered drink sachet", "sachet", 1),
        ("Powdered drink pouch", "pouch", 1),
        ("Powdered drink tin", "tin", 1),
        ("Powdered drink carton", "carton", 4),
    ],

    "tea_coffee_cocoa": [
        ("Tea box", "box", 1),
        ("Coffee jar", "jar", 1),
        ("Coffee sachet", "sachet", 1),
        ("Cocoa tin", "tin", 1),
        ("Tea or coffee carton", "carton", 4),
    ],

    "rice_grains": [
        ("Grain packet", "packet", 1),
        ("Grain bag", "bag", 5),
        ("Grain sack", "sack", 9),
    ],

    "flour_sugar_salt": [
        ("Flour or sugar packet", "packet", 1),
        ("Flour or sugar bag", "bag", 5),
        ("Flour or sugar sack", "sack", 9),
    ],

    "pasta_noodles": [
        ("Noodle packet", "packet", 1),
        ("Pasta packet", "packet", 1),
        ("Noodle carton", "carton", 4),
        ("Pasta carton", "carton", 4),
    ],

    "breakfast_cereal": [
        ("Cereal box", "box", 1),
        ("Cereal bag", "bag", 2),
        ("Cereal carton", "carton", 4),
    ],

    "cooking_oil": [
        ("Oil sachet", "sachet", 1),
        ("Oil bottle", "bottle", 1),
        ("Oil gallon", "gallon", 5),
        ("Oil jerrycan", "jerrycan", 6),
        ("Oil carton", "carton", 5),
    ],

    "spreads": [
        ("Spread sachet", "sachet", 1),
        ("Spread tub", "tub", 1),
        ("Spread jar", "jar", 1),
        ("Spread carton", "carton", 4),
    ],

    "canned_foods": [
        ("Canned food tin", "tin", 1),
        ("Canned food can", "can", 1),
        ("Canned food pack", "pack", 2),
        ("Canned food carton", "carton", 5),
    ],

    "tomato_sauces": [
        ("Tomato sachet", "sachet", 1),
        ("Tomato tin", "tin", 1),
        ("Sauce bottle", "bottle", 1),
        ("Sauce jar", "jar", 1),
        ("Sauce gallon", "gallon", 5),
        ("Tomato or sauce carton", "carton", 5),
    ],

    "spices_seasoning": [
        ("Seasoning sachet", "sachet", 1),
        ("Seasoning packet", "packet", 1),
        ("Seasoning jar", "jar", 1),
        ("Seasoning box", "box", 2),
        ("Seasoning carton", "carton", 4),
    ],

    "biscuits_snacks": [
        ("Snack packet", "packet", 1),
        ("Snack bag", "bag", 1),
        ("Biscuit box", "box", 2),
        ("Snack carton", "carton", 4),
    ],

    "sweets_chocolate": [
        ("Chocolate bar", "bar", 1),
        ("Sweet packet", "packet", 1),
        ("Sweet jar", "jar", 1),
        ("Sweet box", "box", 2),
        ("Sweet carton", "carton", 4),
    ],

    "bakery": [
        ("Bread loaf", "loaf", 1),
        ("Bakery pack", "pack", 2),
        ("Bakery tray", "tray", 3),
        ("Bakery carton", "carton", 4),
    ],

    "eggs": [
        ("Half egg tray", "half_tray", 2),
        ("Egg tray", "tray", 3),
        ("Egg crate", "crate", 7),
    ],

    "frozen_food": [
        ("Frozen food pack", "pack", 2),
        ("Frozen food bag", "bag", 4),
        ("Frozen food carton", "carton", 7),
    ],

    "roots_tubers": [
        ("Root or tuber single", "unit", 1),
        ("Root or tuber bag", "bag", 5),
        ("Root or tuber sack", "sack", 9),
    ],

    "plantain_banana": [
        ("Plantain or banana bunch", "bunch", 5),
    ],

    "fresh_vegetables": [
        ("Vegetable bag", "bag", 4),
        ("Vegetable sack", "sack", 8),
        ("Vegetable crate", "crate", 7),
    ],

    "fresh_fruits": [
        ("Fruit single", "unit", 1),
        ("Fruit bag", "bag", 4),
        ("Fruit crate", "crate", 7),
    ],

    "dried_fish": [
        ("Dried fish bag", "bag", 4),
        ("Dried fish box", "box", 4),
    ],

    "baby_food": [
        ("Baby formula tin", "tin", 1),
        ("Baby food box", "box", 2),
        ("Baby food carton", "carton", 4),
    ],

    "diapers_wipes": [
        ("Diaper pack", "pack", 3),
        ("Diaper carton", "carton", 7),
        ("Diaper bale", "bale", 10),
        ("Baby wipes pack", "pack", 1),
        ("Baby wipes carton", "carton", 5),
    ],

    "laundry_cleaning": [
        ("Detergent sachet", "sachet", 1),
        ("Detergent bag", "bag", 3),
        ("Detergent box", "box", 3),
        ("Cleaning bottle", "bottle", 1),
        ("Cleaning gallon", "gallon", 5),
        ("Cleaning jerrycan", "jerrycan", 6),
        ("Cleaning bucket", "bucket", 6),
        ("Cleaning carton", "carton", 5),
    ],

    "tissue_paper": [
        ("Tissue roll", "roll", 1),
        ("Tissue pack", "pack", 3),
        ("Tissue bale", "bale", 9),
        ("Tissue carton", "carton", 6),
    ],

    "disposables": [
        ("Disposable pack", "pack", 2),
        ("Disposable sleeve", "sleeve", 2),
        ("Disposable carton", "carton", 5),
    ],

    "oral_care": [
        ("Toothpaste tube", "tube", 1),
        ("Toothbrush single", "single", 1),
        ("Oral care pack", "pack", 2),
        ("Oral care carton", "carton", 4),
    ],

    "soap_bodywash": [
        ("Soap bar", "bar", 1),
        ("Soap pack", "pack", 2),
        ("Body wash bottle", "bottle", 1),
        ("Body wash gallon", "gallon", 5),
        ("Soap carton", "carton", 5),
    ],

    "personal_care": [
        ("Deodorant roll-on", "roll_on", 1),
        ("Deodorant spray", "spray_can", 1),
        ("Sanitary pad pack", "pack", 2),
        ("Sanitary pad carton", "carton", 5),
        ("Petroleum jelly jar", "jar", 1),
        ("Personal care carton", "carton", 4),
    ],

    "skincare": [
        ("Skincare tube", "tube", 1),
        ("Skincare bottle", "bottle", 1),
        ("Skincare pump bottle", "pump_bottle", 1),
        ("Skincare jar", "jar", 1),
        ("Skincare tub", "tub", 2),
        ("Skincare carton", "carton", 4),
    ],

    "haircare": [
        ("Haircare bottle", "bottle", 1),
        ("Haircare jar", "jar", 1),
        ("Haircare tub", "tub", 2),
        ("Haircare sachet", "sachet", 1),
        ("Haircare gallon", "gallon", 5),
        ("Haircare carton", "carton", 4),
    ],

    "fragrance": [
        ("Perfume bottle", "bottle", 1),
        ("Boxed perfume", "box", 1),
        ("Body spray", "spray_can", 1),
        ("Fragrance carton", "carton", 4),
    ],

    "makeup": [
        ("Makeup tube", "tube", 1),
        ("Makeup bottle", "bottle", 1),
        ("Makeup compact", "compact", 1),
        ("Makeup palette", "palette", 1),
        ("Makeup pencil", "pencil", 1),
        ("Makeup set", "set", 2),
        ("Makeup carton", "carton", 4),
    ],

    "nails": [
        ("Nail polish bottle", "bottle", 1),
        ("Nail product jar", "jar", 1),
        ("Nail tip box", "box", 1),
        ("Nail product set", "set", 2),
        ("Nail carton", "carton", 4),
    ],

    "hair_extensions": [
        ("Hair extension pack", "pack", 1),
        ("Hair bundle", "bundle", 1),
        ("Wig box", "box", 3),
        ("Hair extension bale", "bale", 9),
    ],

    "beauty_tools": [
        ("Beauty tool single", "single", 1),
        ("Beauty tool pack", "pack", 2),
        ("Beauty tool set", "set", 3),
        ("Beauty tool box", "box", 3),
    ],

    "beauty_appliances": [
        ("Clipper box", "box", 2),
        ("Hair dryer box", "box", 3),
        ("Straightener box", "box", 2),
        ("Beauty appliance carton", "carton", 6),
    ],

    "household_plastics": [
        ("Plastic item", "unit", 1),
        ("Plastic pack", "pack", 3),
        ("Plastic carton", "carton", 6),
        ("Plastic bucket", "bucket", 4),
        ("Plastic basin", "basin", 4),
        ("Plastic basket", "basket", 4),
        ("Plastic jerrycan", "jerrycan", 5),
    ],

    "kitchenware": [
        ("Kitchenware item", "unit", 1),
        ("Kitchenware pack", "pack", 3),
        ("Kitchenware carton", "carton", 6),
        ("Serving tray", "tray", 3),
    ],

    "household_tools": [
        ("Household tool", "unit", 1),
        ("Household tools pack", "pack", 3),
        ("Household tools carton", "carton", 6),
    ],
}


db = SessionLocal()

try:
    category_map = {}

    for (
        code,
        name,
        small,
        medium,
        large,
    ) in CATEGORIES:

        category = db.scalars(
            select(
                LogisticsCategory
            ).where(
                LogisticsCategory.code == code
            )
        ).first()

        if not category:
            category = LogisticsCategory(
                code=code,
                name=name,
                fallback_small_units=small,
                fallback_medium_units=medium,
                fallback_large_units=large,
            )

            db.add(category)
            db.flush()

        category_map[code] = category


    created_types = 0

    for code, types in TYPES.items():
        category = category_map[code]

        for (
            name,
            package_type,
            load_units,
        ) in types:

            existing = db.scalars(
                select(
                    LogisticsType
                ).where(
                    LogisticsType.category_id
                    == category.id,

                    LogisticsType.name
                    == name,
                )
            ).first()

            if existing:
                continue

            db.add(
                LogisticsType(
                    category_id=category.id,
                    name=name,
                    package_type=package_type,
                    load_units=load_units,
                )
            )

            created_types += 1


    db.commit()

    category_count = len(
        db.scalars(
            select(
                LogisticsCategory
            )
        ).all()
    )

    type_count = len(
        db.scalars(
            select(
                LogisticsType
            )
        ).all()
    )

    print(
        f"Logistics categories: {category_count}"
    )

    print(
        f"Logistics types: {type_count}"
    )

    print(
        f"New types created: {created_types}"
    )

finally:
    db.close()
