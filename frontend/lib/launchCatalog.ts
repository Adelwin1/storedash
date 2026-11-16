export type MarketCategoryKey = "provisions" | "foodstuffs" | "utensils";
export type SizeClass = "small" | "medium" | "large";

export type CatalogPackage = {
  label: string;
  unit: string;
  packageType: string;
  sizeClass: SizeClass;
  physicalSizeText: string;
  variantKey: string;
};

export type CatalogProduct = {
  id: string;
  name: string;
  logisticsCategoryCode: string;
  packages: CatalogPackage[];
};

export type CatalogSection = {
  key: string;
  label: string;
  products: CatalogProduct[];
};

export type MarketCategory = {
  key: MarketCategoryKey;
  label: string;
  description: string;
  accent: string;
  soft: string;
  sections: CatalogSection[];
};

const q = (
  label: string,
  packageType: string,
  sizeClass: SizeClass,
  physicalSizeText: string,
  unit = packageType,
): CatalogPackage => ({
  label,
  unit,
  packageType,
  sizeClass,
  physicalSizeText,
  variantKey: ("launch:" + packageType + ":" + physicalSizeText)
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-|-$/g, ""),
});

const T: Record<string, CatalogPackage[]> = {
  grain: [q("1 kg packet", "packet", "small", "1kg"), q("5 kg bag", "bag", "small", "5kg"), q("10 kg bag", "bag", "medium", "10kg"), q("25 kg bag", "bag", "large", "25kg"), q("50 kg sack", "sack", "large", "50kg")],
  dense: [q("500 g packet", "packet", "small", "500g"), q("1 kg packet", "packet", "small", "1kg"), q("5 kg bag", "bag", "small", "5kg"), q("25 kg bag", "bag", "large", "25kg"), q("50 kg sack", "sack", "large", "50kg")],
  oil: [q("1 L bottle", "bottle", "small", "1L"), q("2 L bottle", "bottle", "medium", "2L"), q("5 L bottle", "bottle", "large", "5L"), q("10 L gallon", "gallon", "large", "10L"), q("20 L jerrycan", "jerrycan", "large", "20L")],
  noodles: [q("Single packet", "packet", "small", "70g"), q("40-pack carton", "carton", "large", "40 x 70g")],
  pasta: [q("500 g packet", "packet", "small", "500g"), q("Carton", "carton", "large", "1 carton")],
  cereal: [q("500 g box", "box", "small", "500g"), q("1 kg bag", "bag", "medium", "1kg"), q("Carton", "carton", "large", "1 carton")],
  cans: [q("Small tin / can", "tin", "small", "155g"), q("Large tin / can", "tin", "medium", "425g"), q("24-count carton", "carton", "large", "24 x 425g")],
  tomato: [q("210 g tin", "tin", "small", "210g"), q("400 g tin", "tin", "medium", "400g"), q("Carton", "carton", "large", "24 x 400g")],
  milk: [q("170 g tin", "tin", "small", "170g"), q("410 g tin", "tin", "medium", "410g"), q("24-count carton", "carton", "large", "24 x 410g")],
  milkPowder: [q("400 g tin", "tin", "medium", "400g"), q("1 kg pouch", "pouch", "large", "1kg"), q("Carton", "carton", "large", "1 carton")],
  cocoa: [q("400 g tin", "tin", "medium", "400g"), q("400 g sachet", "sachet", "medium", "400g"), q("12-count carton", "carton", "large", "12 x 400g")],
  tea: [q("Tea box", "box", "small", "25 tea bags"), q("Carton", "carton", "large", "1 carton")],
  coffee: [q("250 g jar", "jar", "small", "250g"), q("100 g sachet", "sachet", "small", "100g"), q("Carton", "carton", "large", "1 carton")],
  seasoning: [q("Sachet", "sachet", "small", "100g"), q("Box", "box", "medium", "1 box"), q("Carton", "carton", "large", "1 carton")],
  sauce: [q("500 ml bottle", "bottle", "small", "500ml"), q("1 L bottle", "bottle", "medium", "1L"), q("Carton", "carton", "large", "1 carton")],
  spread: [q("500 g tub", "tub", "medium", "500g"), q("1 kg tub", "tub", "large", "1kg"), q("Carton", "carton", "large", "1 carton")],
  sachetWater: [q("30 × 500 ml bag", "bag", "medium", "30 x 500ml")],
  bottledWater: [q("500 ml bottle", "bottle", "small", "500ml"), q("12 × 500 ml pack", "pack", "small", "12 x 500ml"), q("24 × 500 ml pack", "pack", "medium", "24 x 500ml"), q("6 × 1.5 L pack", "pack", "medium", "6 x 1.5L")],
  softDrink: [q("330 ml can", "can", "small", "330ml"), q("500 ml bottle", "bottle", "small", "500ml"), q("24 × 330 ml pack", "pack", "large", "24 x 330ml"), q("Standard crate", "crate", "medium", "standard drink crate")],
  malt: [q("330 ml bottle", "bottle", "small", "330ml"), q("24 × 330 ml pack", "pack", "large", "24 x 330ml"), q("Standard crate", "crate", "medium", "standard malt crate")],
  energy: [q("250 ml can", "can", "small", "250ml"), q("500 ml can", "can", "large", "500ml"), q("24-count pack", "pack", "large", "24 x 500ml")],
  juice: [q("500 ml bottle", "bottle", "small", "500ml"), q("1 L bottle", "bottle", "medium", "1L"), q("6 × 1 L pack", "pack", "medium", "6 x 1L"), q("12 × 1 L carton", "carton", "large", "12 x 1L")],
  powderDrink: [q("Sachet", "sachet", "small", "100g"), q("500 g pouch", "pouch", "medium", "500g"), q("Carton", "carton", "large", "1 carton")],
  snack: [q("Packet", "packet", "small", "1 packet"), q("Box", "box", "medium", "1 box"), q("Carton", "carton", "large", "1 carton")],
  sweets: [q("Packet", "packet", "small", "1 packet"), q("Jar", "jar", "medium", "1 jar"), q("Carton", "carton", "large", "1 carton")],
  chocolate: [q("Bar", "bar", "small", "1 bar"), q("Box", "box", "medium", "1 box"), q("Carton", "carton", "large", "1 carton")],
  bread: [q("Standard loaf", "loaf", "medium", "500g"), q("Large loaf", "loaf", "large", "800g")],
  cleaningPowder: [q("500 g sachet", "sachet", "small", "500g"), q("1 kg bag", "bag", "medium", "1kg"), q("Carton", "carton", "large", "1 carton")],
  cleaningLiquid: [q("500 ml bottle", "bottle", "small", "500ml"), q("1 L bottle", "bottle", "medium", "1L"), q("5 L jerrycan", "jerrycan", "large", "5L"), q("20 L jerrycan", "jerrycan", "large", "20L")],
  soap: [q("Single bar", "bar", "small", "200g"), q("Pack", "pack", "medium", "1 retail pack"), q("Carton", "carton", "large", "1 carton")],
  tissue: [q("Retail pack", "pack", "small", "1 retail pack"), q("Bale", "bale", "large", "1 bale"), q("Carton", "carton", "large", "1 carton")],
  tube: [q("Single tube", "tube", "small", "160g"), q("Retail pack", "pack", "medium", "1 retail pack"), q("Carton", "carton", "large", "1 carton")],
  toothbrush: [q("Single toothbrush", "single", "small", "1 toothbrush"), q("Retail pack", "pack", "medium", "1 retail pack"), q("Carton", "carton", "large", "1 carton")],
  pads: [q("Retail pack", "pack", "small", "1 retail pack"), q("Carton", "carton", "large", "1 carton")],
  deodorant: [q("Roll-on", "roll_on", "small", "1 roll-on"), q("Spray can", "spray_can", "small", "1 spray can"), q("Carton", "carton", "large", "1 carton")],
  jar: [q("250 g jar", "jar", "small", "250g"), q("500 g jar", "jar", "medium", "500g"), q("Carton", "carton", "large", "1 carton")],
  bottleCare: [q("500 ml bottle", "bottle", "small", "500ml"), q("1 L bottle", "bottle", "medium", "1L"), q("Carton", "carton", "large", "1 carton")],
  hairCream: [q("500 ml bottle", "bottle", "small", "500ml"), q("250 g jar", "jar", "small", "250g"), q("500 g tub", "tub", "medium", "500g"), q("Carton", "carton", "large", "1 carton")],
  diapers: [q("Retail pack", "pack", "medium", "1 retail pack"), q("Carton", "carton", "large", "1 carton"), q("Bale", "bale", "large", "1 bale")],
  wipes: [q("Retail pack", "pack", "small", "1 retail pack"), q("Carton", "carton", "large", "1 carton")],
  formula: [q("400 g tin", "tin", "medium", "400g"), q("800 g tin", "tin", "large", "800g"), q("Carton", "carton", "large", "1 carton")],
  roots: [q("5 kg bag", "bag", "small", "5kg"), q("10 kg bag", "bag", "medium", "10kg"), q("25 kg sack", "sack", "large", "25kg")],
  yam: [q("Small tuber (~1 kg)", "unit", "small", "1kg"), q("Medium tuber (~2 kg)", "unit", "medium", "2kg"), q("Large tuber (~4 kg)", "unit", "large", "4kg"), q("25 kg sack", "sack", "large", "25kg")],
  plantain: [q("Small bunch (~5 kg)", "bunch", "small", "5kg"), q("Medium bunch (~10 kg)", "bunch", "medium", "10kg"), q("Large bunch (~15 kg)", "bunch", "large", "15kg")],
  banana: [q("Small bunch (~3 kg)", "bunch", "small", "3kg"), q("Medium bunch (~6 kg)", "bunch", "medium", "6kg"), q("Large bunch (~10 kg)", "bunch", "large", "10kg")],
  vegBag: [q("5 kg bag", "bag", "small", "5kg"), q("10 kg bag", "bag", "medium", "10kg"), q("20 kg crate", "crate", "large", "20kg")],
  tomatoCrate: [q("10 kg crate", "crate", "small", "10kg"), q("20 kg crate", "crate", "medium", "20kg"), q("30 kg crate", "crate", "large", "30kg")],
  onion: [q("5 kg bag", "bag", "small", "5kg"), q("10 kg bag", "bag", "medium", "10kg"), q("25 kg sack", "sack", "large", "25kg")],
  leafy: [q("Small bag", "bag", "small", "2kg"), q("Large bag", "bag", "medium", "5kg")],
  fruitBag: [q("5 kg bag", "bag", "small", "5kg"), q("10 kg bag", "bag", "medium", "10kg"), q("20 kg crate", "crate", "large", "20kg")],
  fruitUnit: [q("Small", "unit", "small", "1kg"), q("Medium", "unit", "medium", "2kg"), q("Large", "unit", "large", "4kg")],
  driedFish: [q("2 kg bag", "bag", "small", "2kg"), q("5 kg bag", "bag", "medium", "5kg"), q("10 kg box", "box", "large", "10kg")],
  eggs: [q("15-egg half tray", "half_tray", "small", "15 eggs"), q("30-egg tray", "tray", "medium", "30 eggs"), q("Egg crate", "crate", "large", "1 egg crate")],
  bucket: [q("5 L bucket", "bucket", "small", "5L"), q("10 L bucket", "bucket", "medium", "10L"), q("20 L bucket", "bucket", "large", "20L")],
  basin: [q("Small basin", "basin", "small", "small basin"), q("Medium basin", "basin", "medium", "medium basin"), q("Large basin", "basin", "large", "large basin")],
  basket: [q("Small basket", "basket", "small", "small basket"), q("Medium basket", "basket", "medium", "medium basket"), q("Large basket", "basket", "large", "large basket")],
  jerrycan: [q("5 L jerrycan", "jerrycan", "small", "5L"), q("10 L jerrycan", "jerrycan", "medium", "10L"), q("20 L jerrycan", "jerrycan", "large", "20L"), q("25 L jerrycan", "jerrycan", "large", "25L")],
  household: [q("Small", "unit", "small", "small item"), q("Medium", "unit", "medium", "medium item"), q("Large", "unit", "large", "large item")],
  single: [q("Single unit", "unit", "small", "1 unit"), q("Retail pack", "pack", "medium", "1 retail pack"), q("Carton", "carton", "large", "1 carton")],
  tray: [q("Small tray", "tray", "small", "small tray"), q("Standard tray", "tray", "medium", "standard tray"), q("Large tray", "tray", "large", "large tray")],
  cutlery: [q("Retail set", "pack", "small", "1 cutlery set"), q("Bulk pack", "pack", "medium", "1 bulk pack"), q("Carton", "carton", "large", "1 carton")],
};

const p = (id: string, name: string, code: string, template: string): CatalogProduct => ({ id, name, logisticsCategoryCode: code, packages: T[template] });
const s = (key: string, label: string, products: CatalogProduct[]): CatalogSection => ({ key, label, products });

export const LAUNCH_CATALOG: MarketCategory[] = [
  {
    key: "provisions", label: "Provisions", accent: "#dc2626", soft: "#fff1f2",
    description: "Packaged food, drinks, cleaning, toiletries and everyday shop stock.",
    sections: [
      s("staples", "Staples & Cooking", [p("rice", "Rice", "rice_grains", "grain"), p("sugar", "Sugar", "flour_sugar_salt", "dense"), p("flour", "Flour", "flour_sugar_salt", "dense"), p("salt", "Salt", "flour_sugar_salt", "dense"), p("cooking-oil", "Cooking oil", "cooking_oil", "oil")]),
      s("noodles-breakfast", "Noodles, Pasta & Breakfast", [p("instant-noodles", "Instant noodles", "pasta_noodles", "noodles"), p("spaghetti", "Spaghetti", "pasta_noodles", "pasta"), p("macaroni", "Macaroni / pasta", "pasta_noodles", "pasta"), p("cereal", "Breakfast cereal / cornflakes", "breakfast_cereal", "cereal"), p("oats", "Oats", "breakfast_cereal", "cereal")]),
      s("canned", "Canned & Packaged Foods", [p("tomato-paste", "Tomato paste", "tomato_sauces", "tomato"), p("sardines", "Sardines", "canned_foods", "cans"), p("mackerel", "Canned mackerel", "canned_foods", "cans"), p("corned-beef", "Corned beef", "canned_foods", "cans"), p("baked-beans", "Baked beans", "canned_foods", "cans"), p("tuna", "Canned tuna", "canned_foods", "cans"), p("evaporated-milk", "Evaporated milk", "milk_dairy", "milk"), p("powdered-milk", "Powdered milk", "milk_dairy", "milkPowder")]),
      s("breakfast-seasoning", "Breakfast Drinks, Sauces & Seasoning", [p("cocoa-drink", "Milo / cocoa drink powder", "tea_coffee_cocoa", "cocoa"), p("tea", "Tea", "tea_coffee_cocoa", "tea"), p("coffee", "Coffee", "tea_coffee_cocoa", "coffee"), p("seasoning", "Seasoning cubes / powder", "spices_seasoning", "seasoning"), p("ketchup", "Ketchup / table sauce", "tomato_sauces", "sauce"), p("margarine", "Margarine / spread", "spreads", "spread")]),
      s("drinks", "Drinks", [p("sachet-water", "Sachet water", "water", "sachetWater"), p("bottled-water", "Bottled water", "water", "bottledWater"), p("soft-drink", "Soft drinks", "soft_drinks", "softDrink"), p("malt", "Malt", "malt_energy", "malt"), p("energy-drink", "Energy drinks", "malt_energy", "energy"), p("fruit-juice", "Fruit juice", "juice", "juice"), p("powdered-drink", "Powdered drink", "powdered_drinks", "powderDrink")]),
      s("snacks", "Snacks & Bakery", [p("biscuits", "Biscuits / crackers", "biscuits_snacks", "snack"), p("snacks", "Chips / packaged snacks", "biscuits_snacks", "snack"), p("sweets", "Sweets / candy", "sweets_chocolate", "sweets"), p("chocolate", "Chocolate", "sweets_chocolate", "chocolate"), p("bread", "Bread", "bakery", "bread")]),
      s("cleaning", "Cleaning & Laundry", [p("detergent-powder", "Laundry detergent powder", "laundry_cleaning", "cleaningPowder"), p("liquid-detergent", "Liquid detergent", "laundry_cleaning", "cleaningLiquid"), p("bleach", "Bleach", "laundry_cleaning", "cleaningLiquid"), p("dishwashing", "Dishwashing liquid", "laundry_cleaning", "cleaningLiquid"), p("disinfectant", "Disinfectant / floor cleaner", "laundry_cleaning", "cleaningLiquid")]),
      s("personal-care", "Toiletries & Personal Care", [p("bath-soap", "Bath soap", "soap_bodywash", "soap"), p("body-wash", "Body wash", "soap_bodywash", "bottleCare"), p("tissue", "Toilet tissue", "tissue_paper", "tissue"), p("paper-towel", "Paper towel / napkins", "tissue_paper", "tissue"), p("toothpaste", "Toothpaste", "oral_care", "tube"), p("toothbrush", "Toothbrush", "oral_care", "toothbrush"), p("sanitary-pads", "Sanitary pads", "personal_care", "pads"), p("deodorant", "Deodorant / body spray", "personal_care", "deodorant"), p("petroleum-jelly", "Petroleum jelly", "personal_care", "jar"), p("lotion", "Body lotion", "skincare", "bottleCare"), p("shampoo", "Shampoo", "haircare", "bottleCare"), p("conditioner", "Hair conditioner / cream", "haircare", "hairCream")]),
      s("baby", "Baby & Family", [p("diapers", "Diapers", "diapers_wipes", "diapers"), p("baby-wipes", "Baby wipes", "diapers_wipes", "wipes"), p("baby-formula", "Baby formula / baby food", "baby_food", "formula")]),
    ],
  },
  {
    key: "foodstuffs", label: "Foodstuffs", accent: "#a16207", soft: "#fffbeb",
    description: "Agogo staples: tubers, plantain, vegetables, fruit, grains and smoked/dried fish.",
    sections: [
      s("roots-tubers", "Roots & Tubers", [p("yam", "Yam", "roots_tubers", "yam"), p("cassava", "Cassava", "roots_tubers", "roots"), p("cocoyam", "Cocoyam", "roots_tubers", "roots"), p("sweet-potato", "Sweet potato", "roots_tubers", "roots")]),
      s("plantain-banana", "Plantain & Banana", [p("plantain", "Plantain", "plantain_banana", "plantain"), p("banana", "Banana", "plantain_banana", "banana")]),
      s("vegetables", "Vegetables", [p("tomatoes", "Fresh tomatoes", "fresh_vegetables", "tomatoCrate"), p("onions", "Onions", "fresh_vegetables", "onion"), p("pepper", "Fresh pepper", "fresh_vegetables", "vegBag"), p("garden-eggs", "Garden eggs", "fresh_vegetables", "vegBag"), p("okra", "Okra", "fresh_vegetables", "vegBag"), p("cabbage", "Cabbage", "fresh_vegetables", "vegBag"), p("lettuce", "Lettuce", "fresh_vegetables", "leafy"), p("carrots", "Carrots", "fresh_vegetables", "onion"), p("cucumber", "Cucumber", "fresh_vegetables", "vegBag"), p("kontomire", "Kontomire / leafy greens", "fresh_vegetables", "leafy"), p("ginger", "Ginger", "fresh_vegetables", "vegBag"), p("garlic", "Garlic", "fresh_vegetables", "vegBag")]),
      s("fruits", "Fruits", [p("orange", "Oranges", "fresh_fruits", "fruitBag"), p("pineapple", "Pineapple", "fresh_fruits", "fruitUnit"), p("watermelon", "Watermelon", "fresh_fruits", "fruitUnit"), p("pawpaw", "Pawpaw / papaya", "fresh_fruits", "fruitUnit"), p("mango", "Mangoes", "fresh_fruits", "fruitBag"), p("avocado", "Avocado", "fresh_fruits", "fruitBag"), p("coconut", "Coconut", "fresh_fruits", "fruitUnit")]),
      s("grains-legumes", "Grains, Legumes & Dry Staples", [p("maize", "Maize", "rice_grains", "grain"), p("beans", "Beans / cowpeas", "rice_grains", "grain"), p("groundnuts", "Groundnuts / peanuts", "rice_grains", "grain"), p("millet", "Millet", "rice_grains", "grain"), p("sorghum", "Sorghum", "rice_grains", "grain"), p("gari", "Gari", "rice_grains", "grain")]),
      s("fish-eggs", "Smoked / Dried Fish & Eggs", [p("smoked-fish", "Smoked fish", "dried_fish", "driedFish"), p("dried-fish", "Dried fish", "dried_fish", "driedFish"), p("stockfish", "Stockfish", "dried_fish", "driedFish"), p("eggs", "Eggs", "eggs", "eggs")]),
    ],
  },
  {
    key: "utensils", label: "Utensils & Plastics", accent: "#2563eb", soft: "#eff6ff",
    description: "Kitchenware, plastic storage and household utility goods.",
    sections: [
      s("plastics-storage", "Plastics & Storage", [p("bucket", "Plastic bucket", "household_plastics", "bucket"), p("basin", "Plastic basin", "household_plastics", "basin"), p("plastic-bowl", "Plastic bowl", "household_plastics", "household"), p("plastic-cup", "Plastic cup", "household_plastics", "single"), p("plastic-plate", "Plastic plate", "household_plastics", "single"), p("food-container", "Food storage container", "household_plastics", "household"), p("jerrycan", "Jerrycan", "household_plastics", "jerrycan"), p("dustbin", "Plastic dustbin", "household_plastics", "household"), p("laundry-basket", "Laundry basket", "household_plastics", "basket")]),
      s("kitchenware", "Kitchenware", [p("cooking-pot", "Cooking pot", "kitchenware", "household"), p("frying-pan", "Frying pan", "kitchenware", "household"), p("kettle", "Kettle", "kitchenware", "household"), p("serving-tray", "Serving tray", "kitchenware", "tray"), p("chopping-board", "Chopping board", "kitchenware", "household"), p("ladle", "Ladle", "kitchenware", "single"), p("cooking-spoon", "Cooking spoon", "kitchenware", "single"), p("kitchen-knife", "Kitchen knife", "kitchenware", "single"), p("grater", "Grater", "kitchenware", "single"), p("sieve", "Sieve / strainer", "kitchenware", "household"), p("colander", "Colander", "kitchenware", "household"), p("cutlery", "Spoons / forks / cutlery", "kitchenware", "cutlery"), p("mug", "Mug / cup", "kitchenware", "single"), p("flask", "Thermos / flask", "kitchenware", "household")]),
      s("household-tools", "Cleaning & Household Tools", [p("broom", "Broom", "household_tools", "household"), p("mop", "Mop", "household_tools", "household"), p("dustpan", "Dustpan", "household_tools", "single"), p("scrub-brush", "Scrub brush", "household_tools", "single"), p("toilet-brush", "Toilet brush", "household_tools", "single"), p("clothes-pegs", "Clothes pegs", "household_tools", "single"), p("hangers", "Clothes hangers", "household_tools", "single")]),
    ],
  },
];

export const getMarketCategory = (key: MarketCategoryKey): MarketCategory =>
  LAUNCH_CATALOG.find((category) => category.key === key) ?? LAUNCH_CATALOG[0];

export const getSection = (
  categoryKey: MarketCategoryKey,
  sectionKey: string,
): CatalogSection => {
  const category = getMarketCategory(categoryKey);
  return category.sections.find((section) => section.key === sectionKey)
    ?? category.sections[0];
};

export const getProduct = (
  categoryKey: MarketCategoryKey,
  sectionKey: string,
  productId: string,
): CatalogProduct | null =>
  getSection(categoryKey, sectionKey).products.find((entry) => entry.id === productId)
  ?? null;
