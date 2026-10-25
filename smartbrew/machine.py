"""Machine state service: inventory, bins, faults, availability and the event log.

This is the software side of the physical machine. Real sensors and
actuators would call the same functions (e.g. ``raise_fault`` from the
grinder controller).
"""

from .catalog import MILKS, WASTE_ML_PER_DRINK, has_milk, ingredient_usage, normalize_options
from .db import get_db, now_iso

LOW_STOCK_RATIO = 0.20     # FR-33: warn below 20 % of capacity
BIN_WARNING_RATIO = 0.80   # FR-34: warn at 80 %, halt at 100 %

# code -> (default message, severity, what it blocks)
FAULT_CATALOGUE = {
    "GRINDER_JAMMED": ("Grinder Jammed", "critical", "coffee"),
    "WATER_HEATER_FAULT": ("Water Heater Fault", "critical", "hot"),
    "MILK_FROTHER_FAULT": ("Milk Frother Fault", "critical", "milk"),
    "LOW_INGREDIENT": ("Low Ingredient Threshold", "warning", None),
    "BIN_WARNING": ("Bin almost full", "warning", None),
    "BIN_FULL": ("Bin full - operations halted", "critical", "all"),
}


def log_event(type_, message, severity="info", actor=None):
    """Append one entry to the persistent event log (FR-37). The caller commits.

    Inputs:  type_ – category (auth, order, payment, refill, bin, fault, admin,
             mood, settings); message – text; severity – info|warning|critical;
             actor – username or role that caused the event (optional).
    Returns: None.
    """
    get_db().execute(
        "INSERT INTO events (ts, type, severity, message, actor) VALUES (?,?,?,?,?)",
        (now_iso(), type_, severity, message, actor),
    )


def ingredients_map():
    """Load all ingredients keyed by name.

    Inputs:  none.
    Returns: dict name -> sqlite Row.
    """
    return {r["name"]: r for r in get_db().execute("SELECT * FROM ingredients")}


def active_faults():
    """List unresolved faults, newest first.

    Inputs:  none.
    Returns: list of sqlite Rows from the ``faults`` table.
    """
    return get_db().execute(
        "SELECT * FROM faults WHERE resolved_at IS NULL ORDER BY id DESC"
    ).fetchall()


def raise_fault(code, message=None, actor="machine"):
    """Open a fault unless an identical one is already open, and log it (FR-36).

    Inputs:  code – key of ``FAULT_CATALOGUE``; message – optional specific text;
             actor – who or what reported it.
    Returns: int id of the (new or existing) fault.
    Raises:  ValueError for an unknown code.
    """
    if code not in FAULT_CATALOGUE:
        raise ValueError(f"Unknown fault code: {code}")
    default_msg, severity, _ = FAULT_CATALOGUE[code]
    message = message or default_msg
    db = get_db()
    existing = db.execute(
        "SELECT id FROM faults WHERE code = ? AND message = ? AND resolved_at IS NULL",
        (code, message),
    ).fetchone()
    if existing:
        return existing["id"]
    cur = db.execute(
        "INSERT INTO faults (code, message, severity, created_at) VALUES (?,?,?,?)",
        (code, message, severity, now_iso()),
    )
    log_event("fault", message, severity, actor)
    return cur.lastrowid


def resolve_fault(fault_id, actor):
    """Mark a fault as resolved and log who resolved it.

    Inputs:  fault_id – id of the fault; actor – technician identifier.
    Returns: bool, True if an open fault was resolved.
    """
    db = get_db()
    row = db.execute(
        "SELECT * FROM faults WHERE id = ? AND resolved_at IS NULL", (fault_id,)
    ).fetchone()
    if row is None:
        return False
    db.execute("UPDATE faults SET resolved_at = ?, resolved_by = ? WHERE id = ?",
               (now_iso(), actor, fault_id))
    log_event("fault", f"Resolved: {row['message']}", "info", actor)
    return True


def _auto_resolve(code, message_prefix, actor="machine"):
    """Resolve open automatic faults of a code whose message starts with a prefix.

    Inputs:  code – fault code; message_prefix – text the message starts with;
             actor – resolver name.
    Returns: None.
    """
    for row in get_db().execute(
        "SELECT id FROM faults WHERE code = ? AND message LIKE ? AND resolved_at IS NULL",
        (code, message_prefix + "%"),
    ).fetchall():
        resolve_fault(row["id"], actor)


def bin_status():
    """Report the fill level and state of each waste bin (FR-34).

    Inputs:  none.
    Returns: list of dicts with name, label, unit, level, capacity, pct and
             state ("OK" | "Warning" | "Full").
    """
    result = []
    for b in get_db().execute("SELECT * FROM bins ORDER BY name"):
        pct = round(100 * b["level"] / b["capacity"])
        state = "Full" if pct >= 100 else "Warning" if pct >= BIN_WARNING_RATIO * 100 else "OK"
        result.append({**dict(b), "pct": min(pct, 100), "state": state})
    return result


def halt_reason():
    """Tell whether the whole machine must stop serving drinks.

    Inputs:  none.
    Returns: str reason (e.g. "Coffee grounds bin full") or None when operational.
    """
    for b in bin_status():
        if b["state"] == "Full":
            return f"{b['label']} full - please call a technician"
    return None


def blocked_by_fault(drink, usage, faults):
    """Check whether an open critical fault prevents making this drink.

    Inputs:  drink – drink row; usage – ingredient usage dict; faults – open faults.
    Returns: str fault message if blocked, else None.
    """
    for f in faults:
        scope = FAULT_CATALOGUE.get(f["code"], (None, None, None))[2]
        if scope == "all":
            return f["message"]
        if scope == "coffee" and "coffee_beans" in usage:
            return f["message"]
        if scope == "hot" and not drink["is_cold"]:
            return f["message"]
        if scope == "milk" and any(k.startswith("milk_") for k in usage):
            return f["message"]
    return None


def check_availability(drink, opts, ingredients=None, faults=None, halted=None):
    """Decide whether one customised drink can be prepared right now (FR-12).

    A drink is unavailable when the machine is halted, a critical fault blocks
    it, or any ingredient is depleted, below its minimum threshold, or below
    the quantity this configuration needs.

    Inputs:  drink – drink row; opts – normalised options; ingredients, faults,
             halted – optional pre-loaded state (loaded when None).
    Returns: tuple (available: bool, reason: str | None).
    """
    ingredients = ingredients if ingredients is not None else ingredients_map()
    faults = faults if faults is not None else active_faults()
    halted = halt_reason() if halted is None else halted
    if halted:
        return False, halted
    usage = ingredient_usage(drink, opts)
    fault = blocked_by_fault(drink, usage, faults)
    if fault:
        return False, fault
    for name, qty in usage.items():
        ing = ingredients[name]
        if ing["level"] < qty or ing["level"] < ing["min_threshold"]:
            return False, f"Out of {ing['label'].lower()}"
    return True, None


def menu_availability(drink, opts, ingredients, faults, halted):
    """Availability for the menu card: try the default options and other milk types.

    If the preferred milk is out but another milk works, the drink stays
    selectable and the working options are returned.

    Inputs:  drink – drink row; opts – default options; ingredients, faults,
             halted – pre-loaded machine state.
    Returns: tuple (available: bool, reason: str | None, options: dict).
    """
    ok, reason = check_availability(drink, opts, ingredients, faults, halted)
    if ok or not has_milk(drink):
        return ok, reason, opts
    for milk in MILKS:
        if milk in ("none", opts["milk"]):
            continue
        alt = normalize_options(drink, {**opts, "milk": milk})
        if check_availability(drink, alt, ingredients, faults, halted)[0]:
            return True, None, alt
    return False, reason, opts


def dispense(usage, actor):
    """Deduct ingredients and fill the bins for one brew (FR-25). The caller commits.

    Inputs:  usage – ingredient usage dict; actor – username or "guest".
    Returns: None. Afterwards it re-checks the low-stock and bin alerts.
    """
    db = get_db()
    for name, qty in usage.items():
        db.execute("UPDATE ingredients SET level = MAX(0, level - ?) WHERE name = ?",
                   (qty, name))
    grounds = usage.get("coffee_beans", 0)
    if grounds:
        db.execute("UPDATE bins SET level = level + ? WHERE name = 'grounds_bin'", (grounds,))
    db.execute("UPDATE bins SET level = level + ? WHERE name = 'waste_tank'",
               (WASTE_ML_PER_DRINK,))
    check_low_stock()
    check_bins()


def check_low_stock():
    """Open or auto-resolve "Low Ingredient Threshold" warnings (FR-33).

    Inputs:  none.
    Returns: None.
    """
    for ing in ingredients_map().values():
        prefix = f"Low Ingredient Threshold: {ing['label']}"
        if ing["level"] < LOW_STOCK_RATIO * ing["capacity"]:
            raise_fault("LOW_INGREDIENT", prefix)
        else:
            _auto_resolve("LOW_INGREDIENT", prefix)


def check_bins():
    """Open or auto-resolve bin warnings and the bin-full halt (FR-34).

    Inputs:  none.
    Returns: None.
    """
    for b in bin_status():
        warn_msg = f"{b['label']} at {b['pct']}% - empty soon"
        full_msg = f"{b['label']} full - operations halted"
        if b["state"] == "Full":
            _auto_resolve("BIN_WARNING", b["label"])
            raise_fault("BIN_FULL", full_msg)
        elif b["state"] == "Warning":
            _auto_resolve("BIN_FULL", b["label"])
            if not get_db().execute(
                "SELECT 1 FROM faults WHERE code='BIN_WARNING' AND message LIKE ?"
                " AND resolved_at IS NULL", (b["label"] + "%",)
            ).fetchone():
                raise_fault("BIN_WARNING", warn_msg)
        else:
            _auto_resolve("BIN_WARNING", b["label"])
            _auto_resolve("BIN_FULL", b["label"])


def refill(name, actor, quantity=None, reset=False):
    """Register an ingredient refill or reset its counter to capacity (FR-32).

    Inputs:  name – ingredient name; actor – technician id; quantity – amount
             added (ignored when reset); reset – True to set the level to capacity.
    Returns: sqlite Row of the updated ingredient.
    Raises:  ValueError for an unknown ingredient or a non-positive quantity.
    """
    db = get_db()
    ing = db.execute("SELECT * FROM ingredients WHERE name = ?", (name,)).fetchone()
    if ing is None:
        raise ValueError("Unknown ingredient")
    if reset:
        new_level = ing["capacity"]
        msg = f"{ing['label']} counter reset to max ({ing['capacity']:g} {ing['unit']})"
    else:
        if quantity is None or quantity <= 0:
            raise ValueError("Refill quantity must be positive")
        new_level = min(ing["capacity"], ing["level"] + quantity)
        msg = f"{ing['label']} refilled +{quantity:g} {ing['unit']} (now {new_level:g})"
    db.execute("UPDATE ingredients SET level = ? WHERE name = ?", (new_level, name))
    log_event("refill", msg, "info", actor)
    check_low_stock()
    return db.execute("SELECT * FROM ingredients WHERE name = ?", (name,)).fetchone()


def set_level(name, level, actor):
    """Set an ingredient level directly (technician correction / demo helper).

    Inputs:  name – ingredient; level – new absolute level; actor – technician id.
    Returns: None.
    """
    db = get_db()
    db.execute("UPDATE ingredients SET level = MAX(0, MIN(capacity, ?)) WHERE name = ?",
               (level, name))
    log_event("refill", f"{name} level set to {level:g}", "info", actor)
    check_low_stock()


def empty_bin(name, actor):
    """Register that a bin was emptied: reset it to 0 and lift the halt (FR-35).

    Inputs:  name – bin name; actor – technician id.
    Returns: None.
    Raises:  ValueError for an unknown bin.
    """
    db = get_db()
    row = db.execute("SELECT * FROM bins WHERE name = ?", (name,)).fetchone()
    if row is None:
        raise ValueError("Unknown bin")
    db.execute("UPDATE bins SET level = 0 WHERE name = ?", (name,))
    log_event("bin", f"{row['label']} emptied", "info", actor)
    check_bins()
