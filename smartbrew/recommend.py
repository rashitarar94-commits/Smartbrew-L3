"""Personalised recommendation engine (FR-17, FR-18).

Every drink gets a score from four signals:
time of day, weather, the user's ordering history, and an optional mood
estimate. The menu is then sorted by score and the top-3 available drinks
are highlighted. Each score comes with readable reasons (NFR-12).
"""

import json
import urllib.request
from collections import Counter
from datetime import datetime

from flask import current_app

from .catalog import has_coffee
from .db import get_db, get_setting

BASE_SCORE = 50


def time_period(hour):
    """Map an hour of the day to a period name.

    Inputs:  hour – int 0..23.
    Returns: "morning" | "afternoon" | "evening" | "night".
    """
    if 5 <= hour < 11:
        return "morning"
    if 11 <= hour < 17:
        return "afternoon"
    if 17 <= hour < 22:
        return "evening"
    return "night"


def fetch_live_weather():
    """Fetch the current temperature from Open-Meteo for the configured location.

    Only used when ``WEATHER_LIVE`` is enabled. Any error returns None, so
    the caller falls back gracefully (FR-30).

    Inputs:  none (uses WEATHER_LAT / WEATHER_LON config).
    Returns: dict {"temp": float, "condition": str} or None.
    """
    cfg = current_app.config
    url = ("https://api.open-meteo.com/v1/forecast?current=temperature_2m,precipitation"
           f"&latitude={cfg['WEATHER_LAT']}&longitude={cfg['WEATHER_LON']}")
    try:
        with urllib.request.urlopen(url, timeout=2) as resp:
            cur = json.load(resp)["current"]
        condition = "rainy" if cur.get("precipitation", 0) > 0 else "cloudy"
        return {"temp": float(cur["temperature_2m"]), "condition": condition}
    except Exception:  # network/API failure -> offline fallback
        return None


def current_context():
    """Collect the time and weather context used for scoring.

    The weather comes from the simulation settings, or from the live API
    when enabled. It is ``None`` when the machine is offline (FR-30).

    Inputs:  none.
    Returns: dict with hour, period, weather (dict or None), online (bool).
    """
    override = get_setting("time_override", "")
    hour = int(override) if override.strip().isdigit() else datetime.now().hour
    online = get_setting("network_online", "1") == "1"
    weather = None
    if online:
        if current_app.config.get("WEATHER_LIVE"):
            weather = fetch_live_weather()
        if weather is None:
            weather = {"temp": float(get_setting("weather_temp", "15")),
                       "condition": get_setting("weather_condition", "cloudy")}
    return {"hour": hour, "period": time_period(hour), "weather": weather, "online": online}


def user_history(user_id, limit=30):
    """Return the names of a user's most recent drinks.

    Inputs:  user_id – int or None; limit – max number of transactions.
    Returns: list of drink names (empty for guests).
    """
    if not user_id:
        return []
    rows = get_db().execute(
        "SELECT drink_name FROM transactions WHERE user_id = ? ORDER BY id DESC LIMIT ?",
        (user_id, limit),
    ).fetchall()
    return [r["drink_name"] for r in rows]


def score_drink(drink, ctx, history, mood=None):
    """Compute the recommendation score of one drink.

    Inputs:  drink – drink row; ctx – dict from ``current_context``;
             history – list of past drink names; mood – optional mood string
             (tired, happy, stressed, neutral).
    Returns: tuple (score: float, reasons: list[str], best reasons first).
    """
    score, reasons = BASE_SCORE, []
    coffee = has_coffee(drink)
    cat, cold = drink["category"], bool(drink["is_cold"])
    warming = cat in ("Tea", "Chocolate", "Milk coffee") and not cold

    period = ctx["period"]
    if period == "morning" and coffee:
        score += 15
        reasons.append((15, "Morning → coffee"))
    elif period == "afternoon" and (cat == "Milk coffee" or cold):
        score += 5
        reasons.append((5, "Afternoon pick-me-up"))
    elif period in ("evening", "night"):
        if coffee:
            score -= 15
        if cat in ("Tea", "Chocolate") and not coffee:
            score += 15
            reasons.append((15, "Evening → less caffeine"))

    w = ctx.get("weather")
    if w:
        chilly = w["temp"] <= 10 or w["condition"] in ("rainy", "snowy")
        hot = w["temp"] >= 24 or (w["condition"] == "sunny" and w["temp"] >= 20)
        if chilly:
            if warming:
                score += 15
                reasons.append((15, f"{w['condition'].capitalize()}, {w['temp']:g}°C → warming drink"))
            if cold:
                score -= 20
        elif hot:
            if cold:
                score += 25
                reasons.append((25, f"{w['temp']:g}°C outside → iced drink"))
            else:
                score -= 5

    if history:
        counts = Counter(history)
        share = counts.get(drink["name"], 0) / len(history)
        if share:
            score += 40 * share
            reasons.append((40 * share, f"You often order {drink['name']}"))

    if mood == "tired" and coffee:
        bonus = 35 if drink["name"] in ("Double Espresso", "Flat White") else 25
        score += bonus
        reasons.append((bonus, "You look tired → caffeine boost"))
    elif mood == "stressed":
        if cat in ("Tea", "Chocolate") and not coffee:
            score += 20
            reasons.append((20, "Feeling stressed → calming drink"))
        elif coffee:
            score -= 10
    elif mood == "happy" and (cold or cat == "Chocolate"):
        score += 10
        reasons.append((10, "Good mood → treat yourself"))

    reasons.sort(key=lambda r: -r[0])
    return round(score, 1), [text for _, text in reasons[:2]]


def rank_menu(items, ctx, history, mood=None, top_n=3):
    """Score, sort and highlight menu items (FR-18).

    Unavailable drinks always go to the end and are never highlighted.

    Inputs:  items – list of dicts each holding at least ``drink`` and
             ``available``; ctx, history, mood – see ``score_drink``;
             top_n – number of items to highlight.
    Returns: the same list, sorted, with ``score``, ``reasons`` and
             ``recommended`` (bool) added to every item.
    """
    for item in items:
        item["score"], item["reasons"] = score_drink(item["drink"], ctx, history, mood)
    items.sort(key=lambda i: (not i["available"], -i["score"], i["drink"]["name"]))
    for rank, item in enumerate(items):
        item["recommended"] = item["available"] and rank < top_n
    return items
