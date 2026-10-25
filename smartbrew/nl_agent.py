"""Natural-language drink assistant: the optional "Local LLM Agent" module (FR-21).

The System Description lists this feature as optional and modular. This
prototype ships a deterministic, rule-based interpreter behind the interface
``interpret(text) -> proposal``. A locally hosted LLM (for example a small
model served by llama.cpp) can replace ``interpret`` as long as it returns
the same structure. The proposal is always shown to the user for
confirmation and is never brewed directly.
"""

import re

CATEGORY_RULES = [
    # (regex, drink when milky/default, drink when explicitly black/no milk)
    (r"\b(chai)\b", "Chai Latte", "Chai Latte"),
    (r"\b(tea)\b", "Chai Latte", "Black Tea"),
    (r"\b(mocha)\b", "Mocha", "Mocha"),
    (r"\b(chocolate|cocoa)\b", "Hot Chocolate", "Hot Chocolate"),
    (r"\b(iced|cold|chilled|refreshing)\b", "Iced Latte", "Iced Americano"),
    (r"\b(double espresso|doppio)\b", "Double Espresso", "Double Espresso"),
    (r"\b(espresso|short)\b", "Espresso", "Espresso"),
    (r"\b(americano|black coffee)\b", "Americano", "Americano"),
    (r"\b(flat white)\b", "Flat White", "Flat White"),
    (r"\b(cappuccino|foam|foamy)\b", "Cappuccino", "Cappuccino"),
    (r"\b(latte|milky|creamy)\b", "Latte", "Latte"),
]


def _has(text, pattern):
    """Test whether a regex pattern occurs in the text.

    Inputs:  text – lower-cased request; pattern – regular expression.
    Returns: bool.
    """
    return re.search(pattern, text) is not None


def interpret(text):
    """Translate a free-form drink request into explicit machine parameters.

    Example: "something sweet with a kick, but low on dairy" ->
    Americano, oat-milk splash, 2 syrup shots, strength 5, extra shot.

    Inputs:  text – the user's request (any language style, English keywords).
    Returns: dict with
             drink   – proposed drink name (str),
             options – partial option dict (size, milk, strength, temperature,
                       syrup, extra_shot) to be normalised by the catalogue,
             steps   – list[str] explaining each interpretation decision.
    """
    t = (text or "").lower()
    steps, opts = [], {}

    no_milk = _has(t, r"\b(no milk|without milk|black)\b")
    low_dairy = _has(t, r"(low on dairy|low dairy|less dairy|dairy[- ]free|no dairy|vegan|plant)")
    lactose = _has(t, r"lactose")

    drink = None
    for pattern, milky, black in CATEGORY_RULES:
        if _has(t, pattern):
            drink = black if no_milk else milky
            steps.append(f"Matched '{re.search(pattern, t).group(0)}' → {drink}")
            break
    if drink is None:
        if no_milk or low_dairy:
            drink = "Americano"
            steps.append("No drink named; low/no dairy → Americano")
        elif _has(t, r"\b(sweet|dessert|treat)\b"):
            drink = "Latte"
            steps.append("No drink named; sweet → Latte")
        else:
            drink = "Cappuccino"
            steps.append("No drink named → house default Cappuccino")

    if lactose:
        opts["milk"] = "lactose_free"
        steps.append("Lactose mentioned → lactose-free milk")
    elif low_dairy:
        opts["milk"] = "oat"
        steps.append("Low on dairy → oat milk instead of cow's milk")
    elif no_milk:
        opts["milk"] = "none"
        steps.append("No milk requested")

    if _has(t, r"\b(very sweet|extra sweet|super sweet)\b"):
        opts["syrup"] = 3
        steps.append("Very sweet → 3 syrup shots")
    elif _has(t, r"\b(a bit sweet|slightly sweet|little sweet)\b"):
        opts["syrup"] = 1
        steps.append("Slightly sweet → 1 syrup shot")
    elif _has(t, r"\b(sweet)\b"):
        opts["syrup"] = 2
        steps.append("Sweet → 2 syrup shots")

    if _has(t, r"\b(kick|strong|energy|energi[sz]e|wake|boost|tired)\b"):
        opts["strength"] = 5
        opts["extra_shot"] = True
        steps.append("A kick → strength 5 + extra espresso shot")
    elif _has(t, r"\b(mild|light|weak|smooth)\b"):
        opts["strength"] = 2
        steps.append("Mild → strength 2")

    if _has(t, r"\b(large|big|huge)\b"):
        opts["size"] = "L"
        steps.append("Large → size L")
    elif _has(t, r"\b(small|little cup|tiny)\b"):
        opts["size"] = "S"
        steps.append("Small → size S")

    if _has(t, r"\b(extra hot|very hot|really hot)\b"):
        opts["temperature"] = "extra_hot"
        steps.append("Extra hot")
    elif _has(t, r"\b(warm|not too hot|lukewarm)\b"):
        opts["temperature"] = "warm"
        steps.append("Warm, not hot")

    return {"drink": drink, "options": opts, "steps": steps}
