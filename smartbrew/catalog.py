"""Drink catalogue: customisation options, ingredient usage, price and nutrition.

Everything here is a pure function of the drink row, the chosen options and
the ingredient table. The menu, the live quote API, checkout and the
recommendation engine all compute prices the same way through this module.
"""

import json

SIZES = {"S": (0.75, -0.30), "M": (1.0, 0.0), "L": (1.3, 0.50)}  # (qty factor, price delta)
MILKS = {"none": None, "whole": "milk_whole", "oat": "milk_oat",
         "lactose_free": "milk_lactose_free"}
MILK_PRICE = {"none": 0.0, "whole": 0.0, "oat": 0.40, "lactose_free": 0.30}
MILK_LABEL = {"none": "No milk", "whole": "Whole milk", "oat": "Oat milk",
              "lactose_free": "Lactose-free milk"}
TEMPERATURES = ("warm", "hot", "extra_hot")
SPLASH_ML = 50          # milk added to a non-milk drink
SYRUP_ML_PER_SHOT = 10
SYRUP_PRICE = 0.40
EXTRA_SHOT = {"coffee_beans": 9, "water": 30}
EXTRA_SHOT_PRICE = 0.50
WASTE_ML_PER_DRINK = 25  # rinse water sent to the waste tank per brew


def drink_recipe(drink):
    """Decode the base (size M) recipe of a drink row.

    Inputs:  drink – sqlite Row/dict with a JSON ``recipe`` column.
    Returns: dict ingredient-key -> quantity (``"milk"`` is a generic milk slot).
    """
    return json.loads(drink["recipe"])


def has_milk(drink):
    """Tell whether a drink is milk-based (its recipe has a milk slot).

    Inputs:  drink – drink row.
    Returns: bool.
    """
    return "milk" in drink_recipe(drink)


def has_coffee(drink):
    """Tell whether a drink contains coffee (so strength / extra shot apply).

    Inputs:  drink – drink row.
    Returns: bool.
    """
    return "coffee_beans" in drink_recipe(drink)


def default_options(drink, user=None):
    """Build the default customisation for a drink, using the user's preferences.

    Inputs:  drink – drink row; user – optional user row with pref_* columns.
    Returns: dict with keys size, milk, strength, temperature, syrup, extra_shot.
    """
    pref_milk = user["pref_milk"] if user else "whole"
    return {
        "size": "M",
        "milk": pref_milk if has_milk(drink) else "none",
        "strength": user["pref_strength"] if user else 3,
        "temperature": "cold" if drink["is_cold"] else (user["pref_temperature"] if user else "hot"),
        "syrup": 0,
        "extra_shot": False,
    }


def normalize_options(drink, raw):
    """Validate and clamp user-supplied options so they are safe to price and brew.

    Invalid or missing values fall back to defaults. Milk-based drinks cannot
    be made with "none", and cold drinks always have temperature "cold".

    Inputs:  drink – drink row; raw – dict (e.g. from JSON or a form), may be None.
    Returns: dict of normalised options (same keys as ``default_options``).
    """
    raw = raw or {}
    opts = default_options(drink)
    if raw.get("size") in SIZES:
        opts["size"] = raw["size"]
    if raw.get("milk") in MILKS:
        opts["milk"] = raw["milk"]
    if has_milk(drink) and opts["milk"] == "none":
        opts["milk"] = "whole"
    try:
        opts["strength"] = min(5, max(1, int(raw.get("strength", opts["strength"]))))
    except (TypeError, ValueError):
        pass
    if drink["is_cold"]:
        opts["temperature"] = "cold"
    elif raw.get("temperature") in TEMPERATURES:
        opts["temperature"] = raw["temperature"]
    try:
        opts["syrup"] = min(3, max(0, int(raw.get("syrup", 0))))
    except (TypeError, ValueError):
        pass
    extra = raw.get("extra_shot", False)
    opts["extra_shot"] = has_coffee(drink) and extra in (True, "true", "1", "on", 1)
    return opts


def ingredient_usage(drink, opts):
    """Compute the exact ingredient quantities needed for one customised drink.

    Inputs:  drink – drink row; opts – normalised options.
    Returns: dict ingredient-name -> quantity (always includes one cup).
    """
    factor = SIZES[opts["size"]][0]
    usage = {}
    for key, qty in drink_recipe(drink).items():
        if key == "milk":
            key = MILKS[opts["milk"]]
        if key in ("tea",):
            usage[key] = usage.get(key, 0) + qty  # one bag regardless of size
        else:
            usage[key] = usage.get(key, 0) + qty * factor
    if "coffee_beans" in usage:
        usage["coffee_beans"] *= 0.7 + 0.15 * (opts["strength"] - 1)
    if not has_milk(drink) and opts["milk"] != "none":
        milk_key = MILKS[opts["milk"]]
        usage[milk_key] = usage.get(milk_key, 0) + SPLASH_ML
    if opts["extra_shot"]:
        for key, qty in EXTRA_SHOT.items():
            usage[key] = usage.get(key, 0) + qty
    if opts["syrup"]:
        usage["syrup"] = usage.get("syrup", 0) + opts["syrup"] * SYRUP_ML_PER_SHOT
    usage["cups"] = 1
    return {k: round(v, 1) for k, v in usage.items()}


def price(drink, opts):
    """Compute the price of a customised drink in EUR.

    Inputs:  drink – drink row; opts – normalised options.
    Returns: float rounded to 2 decimals.
    """
    total = drink["base_price"] + SIZES[opts["size"]][1] + MILK_PRICE[opts["milk"]]
    total += opts["syrup"] * SYRUP_PRICE
    if opts["extra_shot"]:
        total += EXTRA_SHOT_PRICE
    return round(total, 2)


def nutrition(usage, ingredients):
    """Sum nutrition values and allergens of an ingredient usage.

    Inputs:  usage – dict from ``ingredient_usage``;
             ingredients – dict name -> ingredient row (with kcal, sugar, fat,
             caffeine, allergen per unit).
    Returns: dict with kcal, sugar_g, fat_g, caffeine_mg (rounded) and
             allergens (sorted list of str).
    """
    totals = {"kcal": 0.0, "sugar_g": 0.0, "fat_g": 0.0, "caffeine_mg": 0.0}
    allergens = set()
    for name, qty in usage.items():
        ing = ingredients.get(name)
        if ing is None:
            continue
        totals["kcal"] += ing["kcal"] * qty
        totals["sugar_g"] += ing["sugar"] * qty
        totals["fat_g"] += ing["fat"] * qty
        totals["caffeine_mg"] += ing["caffeine"] * qty
        if ing["allergen"]:
            allergens.add(ing["allergen"])
    result = {k: round(v) if k in ("kcal", "caffeine_mg") else round(v, 1)
              for k, v in totals.items()}
    result["allergens"] = sorted(allergens)
    return result


def describe_options(drink, opts):
    """Produce a short, human-readable summary of a customisation.

    Inputs:  drink – drink row; opts – normalised options.
    Returns: str such as ``"Size L · Oat milk · Strength 4 · 2 syrup · extra shot · hot"``.
    """
    parts = [f"Size {opts['size']}"]
    if opts["milk"] != "none":
        parts.append(MILK_LABEL[opts["milk"]])
    if has_coffee(drink):
        parts.append(f"Strength {opts['strength']}")
    if opts["syrup"]:
        parts.append(f"{opts['syrup']} syrup")
    if opts["extra_shot"]:
        parts.append("extra shot")
    parts.append(opts["temperature"].replace("_", " "))
    return " · ".join(parts)
