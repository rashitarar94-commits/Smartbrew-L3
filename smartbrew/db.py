"""Database access layer for SmartBrew AI.

The prototype stores all state in one SQLite file. This module creates the
schema, seeds the demo data, and gives request-scoped connections.
"""

import json
import sqlite3
from datetime import datetime, timedelta

from flask import current_app, g
from werkzeug.security import generate_password_hash

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    username         TEXT NOT NULL UNIQUE,
    email            TEXT NOT NULL UNIQUE,
    password_hash    TEXT NOT NULL,
    nfc_uid          TEXT UNIQUE,
    prepaid_balance  REAL NOT NULL DEFAULT 0,
    failed_attempts  INTEGER NOT NULL DEFAULT 0,
    locked_until     TEXT,
    pref_milk        TEXT NOT NULL DEFAULT 'whole',
    pref_strength    INTEGER NOT NULL DEFAULT 3,
    pref_temperature TEXT NOT NULL DEFAULT 'hot',
    created_at       TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS ingredients (
    name           TEXT PRIMARY KEY,
    label          TEXT NOT NULL,
    unit           TEXT NOT NULL,
    level          REAL NOT NULL,
    capacity       REAL NOT NULL,
    min_threshold  REAL NOT NULL,
    kcal           REAL NOT NULL DEFAULT 0,
    sugar          REAL NOT NULL DEFAULT 0,
    fat            REAL NOT NULL DEFAULT 0,
    caffeine       REAL NOT NULL DEFAULT 0,
    allergen       TEXT
);
CREATE TABLE IF NOT EXISTS drinks (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT NOT NULL UNIQUE,
    category    TEXT NOT NULL,
    base_price  REAL NOT NULL,
    description TEXT NOT NULL,
    recipe      TEXT NOT NULL,
    is_cold     INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS bins (
    name     TEXT PRIMARY KEY,
    label    TEXT NOT NULL,
    unit     TEXT NOT NULL,
    level    REAL NOT NULL,
    capacity REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS recipes (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id    INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name       TEXT NOT NULL,
    drink_id   INTEGER NOT NULL REFERENCES drinks(id),
    options    TEXT NOT NULL,
    created_at TEXT NOT NULL,
    UNIQUE (user_id, name)
);
CREATE TABLE IF NOT EXISTS transactions (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    receipt_no     TEXT NOT NULL UNIQUE,
    user_id        INTEGER REFERENCES users(id),
    drink_id       INTEGER NOT NULL REFERENCES drinks(id),
    drink_name     TEXT NOT NULL,
    options        TEXT NOT NULL,
    price          REAL NOT NULL,
    payment_method TEXT NOT NULL,
    payment_ref    TEXT NOT NULL,
    offline        INTEGER NOT NULL DEFAULT 0,
    created_at     TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS faults (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    code        TEXT NOT NULL,
    message     TEXT NOT NULL,
    severity    TEXT NOT NULL,
    created_at  TEXT NOT NULL,
    resolved_at TEXT,
    resolved_by TEXT
);
CREATE TABLE IF NOT EXISTS events (
    id       INTEGER PRIMARY KEY AUTOINCREMENT,
    ts       TEXT NOT NULL,
    type     TEXT NOT NULL,
    severity TEXT NOT NULL,
    message  TEXT NOT NULL,
    actor    TEXT
);
CREATE TABLE IF NOT EXISTS settings (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
"""

# (name, label, unit, level, capacity, min_threshold, kcal, sugar, fat, caffeine, allergen)
# Nutrition values are per unit (per g, ml or piece).
INGREDIENTS = [
    ("coffee_beans", "Coffee beans", "g", 1000, 1000, 30, 0.2, 0, 0, 7.0, None),
    ("water", "Water", "ml", 5000, 5000, 300, 0, 0, 0, 0, None),
    ("milk_whole", "Whole milk", "ml", 2000, 2000, 100, 0.64, 0.048, 0.036, 0, "milk"),
    ("milk_oat", "Oat milk", "ml", 1500, 1500, 100, 0.46, 0.04, 0.015, 0, "oats (gluten)"),
    ("milk_lactose_free", "Lactose-free milk", "ml", 1500, 1500, 100, 0.6, 0.03, 0.035, 0, "milk"),
    ("cocoa", "Cocoa powder", "g", 600, 600, 30, 3.8, 0.7, 0.06, 0.2, None),
    ("tea", "Tea bags", "pcs", 50, 50, 2, 2, 0, 0, 40, None),
    ("syrup", "Vanilla syrup", "ml", 500, 500, 20, 3.3, 0.8, 0, 0, None),
    ("ice", "Ice", "g", 3000, 3000, 150, 0, 0, 0, 0, None),
    ("cups", "Cups", "pcs", 100, 100, 3, 0, 0, 0, 0, None),
]

# (name, category, base price EUR, description, recipe for size M, is_cold)
DRINKS = [
    ("Espresso", "Coffee", 1.80, "Short, intense shot of coffee.",
     {"coffee_beans": 9, "water": 40}, 0),
    ("Double Espresso", "Coffee", 2.50, "Two shots for a real boost.",
     {"coffee_beans": 18, "water": 60}, 0),
    ("Americano", "Coffee", 2.20, "Espresso lengthened with hot water.",
     {"coffee_beans": 9, "water": 200}, 0),
    ("Cappuccino", "Milk coffee", 2.80, "Espresso with foamed milk.",
     {"coffee_beans": 9, "water": 40, "milk": 120}, 0),
    ("Latte", "Milk coffee", 3.00, "Mild espresso with lots of steamed milk.",
     {"coffee_beans": 9, "water": 40, "milk": 200}, 0),
    ("Flat White", "Milk coffee", 3.10, "Double ristretto with velvety milk.",
     {"coffee_beans": 18, "water": 40, "milk": 120}, 0),
    ("Mocha", "Chocolate", 3.30, "Espresso, cocoa and steamed milk.",
     {"coffee_beans": 9, "water": 40, "milk": 150, "cocoa": 15}, 0),
    ("Hot Chocolate", "Chocolate", 2.90, "Creamy cocoa with steamed milk.",
     {"milk": 200, "cocoa": 25}, 0),
    ("Black Tea", "Tea", 1.90, "Classic black tea.",
     {"tea": 1, "water": 250}, 0),
    ("Chai Latte", "Tea", 3.00, "Spiced tea with steamed milk.",
     {"tea": 1, "water": 100, "milk": 150, "syrup": 10}, 0),
    ("Iced Latte", "Cold drinks", 3.40, "Espresso over ice and cold milk.",
     {"coffee_beans": 9, "milk": 180, "ice": 120}, 1),
    ("Iced Americano", "Cold drinks", 2.80, "Espresso over ice and water.",
     {"coffee_beans": 9, "water": 150, "ice": 120}, 1),
]

BINS = [
    ("grounds_bin", "Coffee grounds bin", "g", 0, 400),
    ("waste_tank", "Liquid waste tank", "ml", 0, 1000),
]

DEFAULT_SETTINGS = {
    "network_online": "1",
    "weather_temp": "14",
    "weather_condition": "cloudy",
    "time_override": "",
    "technician_pin_hash": None,  # filled in seed_db (hashed)
    "master_card_uid": "MASTER-0001",
    "physical_key_id": "KEY-SB-01",
}


def get_db():
    """Return the SQLite connection of the current request, opening it if needed.

    Inputs:  none (uses the Flask application context and ``DATABASE`` config).
    Returns: sqlite3.Connection whose rows behave like dicts (``sqlite3.Row``).
    """
    if "db" not in g:
        g.db = sqlite3.connect(current_app.config["DATABASE"])
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


def close_db(_exc=None):
    """Close the request's database connection, if one was opened.

    Inputs:  _exc – exception passed by Flask's teardown hook (ignored).
    Returns: None.
    """
    db = g.pop("db", None)
    if db is not None:
        db.close()


def now_iso():
    """Return the current local time as an ISO-8601 string (seconds precision).

    Inputs:  none.
    Returns: str, e.g. ``"2026-10-25T08:15:00"``.
    """
    return datetime.now().replace(microsecond=0).isoformat()


def init_db(seed=True):
    """Create all tables and optionally insert the demo data.

    Inputs:  seed – when True and the database is empty, insert demo data.
    Returns: None.
    """
    db = get_db()
    db.executescript(SCHEMA)
    if seed and db.execute("SELECT COUNT(*) FROM drinks").fetchone()[0] == 0:
        seed_db(db)
    db.commit()


def seed_db(db):
    """Insert ingredients, drinks, bins, settings, demo users and order history.

    Demo accounts (test credentials for this local prototype only):
    ``alice`` / ``password123`` (NFC card ``04AA11BB``, 20 EUR prepaid) and
    ``bob`` / ``password123``. Technician PIN: ``4321``.

    Inputs:  db – open sqlite3 connection.
    Returns: None.
    """
    db.executemany(
        "INSERT INTO ingredients VALUES (?,?,?,?,?,?,?,?,?,?,?)", INGREDIENTS
    )
    db.executemany(
        "INSERT INTO drinks (name, category, base_price, description, recipe, is_cold)"
        " VALUES (?,?,?,?,?,?)",
        [(n, c, p, d, json.dumps(r), cold) for n, c, p, d, r, cold in DRINKS],
    )
    db.executemany("INSERT INTO bins VALUES (?,?,?,?,?)", BINS)
    settings = dict(DEFAULT_SETTINGS)
    settings["technician_pin_hash"] = generate_password_hash("4321")
    db.executemany("INSERT INTO settings VALUES (?,?)", settings.items())

    created = now_iso()
    pw = generate_password_hash("password123")
    db.execute(
        "INSERT INTO users (username, email, password_hash, nfc_uid, prepaid_balance,"
        " pref_milk, created_at) VALUES (?,?,?,?,?,?,?)",
        ("alice", "alice@example.com", pw, "04AA11BB", 20.0, "oat", created),
    )
    db.execute(
        "INSERT INTO users (username, email, password_hash, prepaid_balance, created_at)"
        " VALUES (?,?,?,?,?)",
        ("bob", "bob@example.com", pw, 5.0, created),
    )
    _seed_history(db)


def _seed_history(db):
    """Insert past transactions so that the recommendation engine has history.

    alice mostly drinks lattes; bob mostly espressos.

    Inputs:  db – open sqlite3 connection.
    Returns: None.
    """
    drinks = {r["name"]: r for r in db.execute("SELECT * FROM drinks")}
    users = {r["username"]: r["id"] for r in db.execute("SELECT id, username FROM users")}
    history = [("alice", "Latte")] * 6 + [("alice", "Cappuccino")] * 2 + \
              [("bob", "Espresso")] * 5 + [("bob", "Americano")] * 2
    base = datetime.now() - timedelta(days=len(history))
    for i, (user, drink) in enumerate(history):
        d = drinks[drink]
        options = {"size": "M", "milk": "oat" if user == "alice" else "none",
                   "strength": 3, "temperature": "hot", "syrup": 0, "extra_shot": False}
        db.execute(
            "INSERT INTO transactions (receipt_no, user_id, drink_id, drink_name, options,"
            " price, payment_method, payment_ref, created_at) VALUES (?,?,?,?,?,?,?,?,?)",
            (f"SEED{i:04d}", users[user], d["id"], drink, json.dumps(options),
             d["base_price"], "prepaid", "SEED",
             (base + timedelta(days=i)).replace(microsecond=0).isoformat()),
        )


def get_setting(key, default=None):
    """Read one machine/simulation setting.

    Inputs:  key – setting name; default – value returned if the key is missing.
    Returns: str setting value, or ``default``.
    """
    row = get_db().execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
    return row["value"] if row else default


def set_setting(key, value):
    """Create or update one setting (the caller commits).

    Inputs:  key – setting name; value – new value (stored as text).
    Returns: None.
    """
    get_db().execute(
        "INSERT INTO settings (key, value) VALUES (?, ?)"
        " ON CONFLICT(key) DO UPDATE SET value = excluded.value",
        (key, str(value)),
    )
