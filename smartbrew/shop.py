"""Customer-facing screens: menu, customiser, recipes, mood and assistant.

Covers FR-07–FR-21: browsing, real-time customisation, nutrition, blocking
unavailable drinks, custom recipes, recommendations, mood suggestions and
the natural-language assistant.
"""

import json

from flask import (Blueprint, abort, flash, g, jsonify, redirect, render_template,
                   request, session, url_for)

from . import catalog, machine, mood as mood_mod, nl_agent, recommend
from .auth import login_required
from .db import get_db, now_iso

bp = Blueprint("shop", __name__)

CATEGORIES = ["Coffee", "Milk coffee", "Chocolate", "Tea", "Cold drinks"]


def get_drink(drink_id):
    """Load one drink by id or abort with 404.

    Inputs:  drink_id – int.
    Returns: sqlite Row of the drink.
    """
    drink = get_db().execute("SELECT * FROM drinks WHERE id = ?", (drink_id,)).fetchone()
    if drink is None:
        abort(404)
    return drink


def get_drink_by_name(name):
    """Load one drink by its exact name.

    Inputs:  name – drink name.
    Returns: sqlite Row or None.
    """
    return get_db().execute("SELECT * FROM drinks WHERE name = ?", (name,)).fetchone()


def parse_options_arg(raw):
    """Parse a JSON options string from a query string or form field.

    Inputs:  raw – str or None.
    Returns: dict (empty if missing or invalid).
    """
    try:
        value = json.loads(raw) if raw else {}
        return value if isinstance(value, dict) else {}
    except (TypeError, ValueError):
        return {}


def build_menu_items():
    """Compute every drink's default options, price, availability and score.

    Inputs:  none (uses ``g.user`` and the mood stored in the session).
    Returns: tuple (items: list[dict] ranked by ``recommend.rank_menu``,
             ctx: dict from ``recommend.current_context``).
    """
    db = get_db()
    ingredients = machine.ingredients_map()
    faults = machine.active_faults()
    halted = machine.halt_reason()
    items = []
    for drink in db.execute("SELECT * FROM drinks ORDER BY id"):
        opts = catalog.default_options(drink, g.user)
        ok, reason, opts = machine.menu_availability(drink, opts, ingredients, faults, halted)
        items.append({"drink": drink, "options": opts, "available": ok, "reason": reason,
                      "price": catalog.price(drink, opts)})
    ctx = recommend.current_context()
    history = recommend.user_history(g.user["id"] if g.user else None)
    recommend.rank_menu(items, ctx, history, session.get("mood"))
    return items, ctx


@bp.route("/")
def menu():
    """Show the menu, sorted and highlighted by recommendation score (FR-08, FR-09, FR-12, FR-18).

    Inputs:  optional query arg ``category``.
    Returns: rendered menu page.
    """
    category = request.args.get("category")
    items, ctx = build_menu_items()
    shown = [i for i in items if not category or i["drink"]["category"] == category]
    recipes = []
    if g.user:
        recipes = get_db().execute(
            "SELECT r.*, d.name AS drink_name FROM recipes r JOIN drinks d ON d.id = r.drink_id"
            " WHERE r.user_id = ? ORDER BY r.name", (g.user["id"],)).fetchall()
    return render_template("menu.html", items=shown, top=[i for i in items if i["recommended"]],
                           categories=CATEGORIES, category=category, ctx=ctx,
                           halted=machine.halt_reason(), recipes=recipes,
                           mood=session.get("mood"))


def quote(drink, raw_options):
    """Price, nutrition and availability for one configuration (shared by the API and checkout).

    Inputs:  drink – drink row; raw_options – unvalidated option dict.
    Returns: dict with options, price, nutrition, available, reason, summary and
             milk_available (dict milk -> bool).
    """
    opts = catalog.normalize_options(drink, raw_options)
    ingredients = machine.ingredients_map()
    faults = machine.active_faults()
    halted = machine.halt_reason()
    ok, reason = machine.check_availability(drink, opts, ingredients, faults, halted)
    usage = catalog.ingredient_usage(drink, opts)
    milk_ok = {}
    for milk in catalog.MILKS:
        alt = catalog.normalize_options(drink, {**opts, "milk": milk})
        milk_ok[milk] = alt["milk"] == milk and machine.check_availability(
            drink, alt, ingredients, faults, halted)[0]
    return {"options": opts, "price": catalog.price(drink, opts),
            "nutrition": catalog.nutrition(usage, ingredients),
            "available": ok, "reason": reason,
            "summary": catalog.describe_options(drink, opts), "milk_available": milk_ok}


@bp.route("/drink/<int:drink_id>")
def drink_page(drink_id):
    """Show the real-time customiser for one drink (FR-10, FR-11).

    Inputs:  drink_id – URL part; optional query args ``options`` (JSON) to
             pre-fill and ``recipe`` (id) to edit a saved recipe.
    Returns: rendered customiser page.
    """
    drink = get_drink(drink_id)
    recipe = None
    raw = parse_options_arg(request.args.get("options"))
    if request.args.get("recipe") and g.user:
        recipe = get_db().execute("SELECT * FROM recipes WHERE id = ? AND user_id = ?",
                                  (request.args["recipe"], g.user["id"])).fetchone()
        if recipe:
            raw = json.loads(recipe["options"])
    if not raw:
        raw = catalog.default_options(drink, g.user)
    q = quote(drink, raw)
    return render_template("drink.html", drink=drink, q=q, recipe=recipe,
                           has_milk=catalog.has_milk(drink), has_coffee=catalog.has_coffee(drink),
                           milks=catalog.MILK_LABEL, temps=catalog.TEMPERATURES)


@bp.route("/api/quote", methods=("POST",))
def api_quote():
    """JSON endpoint used by the customiser for live price/nutrition updates.

    Inputs:  JSON body {"drink_id": int, "options": {...}}.
    Returns: JSON from ``quote`` (HTTP 404 for an unknown drink).
    """
    data = request.get_json(silent=True) or {}
    drink = get_drink(int(data.get("drink_id", 0)))
    return jsonify(quote(drink, data.get("options")))


# ---------------------------------------------------------------- recipes (FR-13–FR-16)

def own_recipe(recipe_id):
    """Load a recipe that belongs to the logged-in user, or abort with 404.

    Inputs:  recipe_id – int.
    Returns: sqlite Row of the recipe.
    """
    recipe = get_db().execute("SELECT * FROM recipes WHERE id = ? AND user_id = ?",
                              (recipe_id, g.user["id"])).fetchone()
    if recipe is None:
        abort(404)
    return recipe


def validate_recipe_name(name, exclude_id=None):
    """Check that a recipe name is non-empty, short, and unique for the user.

    Inputs:  name – proposed name; exclude_id – recipe id ignored in the
             uniqueness check (when renaming).
    Returns: error message str, or None when valid.
    """
    if not name or len(name) > 40:
        return "Recipe name must be 1–40 characters."
    clash = get_db().execute(
        "SELECT id FROM recipes WHERE user_id = ? AND lower(name) = lower(?) AND id != ?",
        (g.user["id"], name, exclude_id or -1)).fetchone()
    return "You already have a recipe with this name." if clash else None


@bp.route("/recipes")
@login_required
def recipes():
    """List the user's saved recipes with price and availability.

    Inputs:  none.
    Returns: rendered recipes page.
    """
    rows = []
    for r in get_db().execute(
            "SELECT r.*, d.name AS drink_name FROM recipes r JOIN drinks d ON d.id = r.drink_id"
            " WHERE r.user_id = ? ORDER BY r.name", (g.user["id"],)):
        drink = get_drink(r["drink_id"])
        q = quote(drink, json.loads(r["options"]))
        rows.append({"recipe": r, "q": q})
    return render_template("recipes.html", rows=rows)


@bp.route("/recipes", methods=("POST",))
@login_required
def create_recipe():
    """Save the current customisation as a named recipe (FR-13).

    Inputs:  form fields drink_id, name, options (JSON).
    Returns: redirect to the recipe list, or back to the drink page on error.
    """
    drink = get_drink(int(request.form.get("drink_id", 0)))
    name = request.form.get("name", "").strip()
    opts = catalog.normalize_options(drink, parse_options_arg(request.form.get("options")))
    error = validate_recipe_name(name)
    if error:
        flash(error, "error")
        return redirect(url_for("shop.drink_page", drink_id=drink["id"], options=json.dumps(opts)))
    db = get_db()
    db.execute("INSERT INTO recipes (user_id, name, drink_id, options, created_at)"
               " VALUES (?,?,?,?,?)", (g.user["id"], name, drink["id"], json.dumps(opts), now_iso()))
    db.commit()
    flash(f"Recipe “{name}” saved.", "success")
    return redirect(url_for("shop.recipes"))


@bp.route("/recipes/<int:recipe_id>/update", methods=("POST",))
@login_required
def update_recipe(recipe_id):
    """Modify the name and/or parameters of a saved recipe (FR-14).

    Inputs:  recipe_id – URL part; form fields name, options (JSON).
    Returns: redirect to the recipe list (or back to the editor on error).
    """
    recipe = own_recipe(recipe_id)
    drink = get_drink(recipe["drink_id"])
    name = request.form.get("name", "").strip()
    opts = catalog.normalize_options(drink, parse_options_arg(request.form.get("options")))
    error = validate_recipe_name(name, exclude_id=recipe_id)
    if error:
        flash(error, "error")
        return redirect(url_for("shop.drink_page", drink_id=drink["id"], recipe=recipe_id))
    db = get_db()
    db.execute("UPDATE recipes SET name = ?, options = ? WHERE id = ?",
               (name, json.dumps(opts), recipe_id))
    db.commit()
    flash(f"Recipe “{name}” updated.", "success")
    return redirect(url_for("shop.recipes"))


@bp.route("/recipes/<int:recipe_id>/delete", methods=("POST",))
@login_required
def delete_recipe(recipe_id):
    """Delete a saved recipe (FR-15).

    Inputs:  recipe_id – URL part.
    Returns: redirect to the recipe list.
    """
    recipe = own_recipe(recipe_id)
    db = get_db()
    db.execute("DELETE FROM recipes WHERE id = ?", (recipe_id,))
    db.commit()
    flash(f"Recipe “{recipe['name']}” deleted.", "info")
    return redirect(url_for("shop.recipes"))


@bp.route("/recipes/<int:recipe_id>/order")
@login_required
def order_recipe(recipe_id):
    """One-touch ordering: jump straight to checkout with the saved recipe (FR-16).

    Inputs:  recipe_id – URL part.
    Returns: redirect to the checkout page.
    """
    recipe = own_recipe(recipe_id)
    return redirect(url_for("orders.checkout", drink_id=recipe["drink_id"],
                            options=recipe["options"], recipe=recipe["name"]))


# ---------------------------------------------------------------- mood (FR-19, FR-20)

def mood_suggestion(mood):
    """Build the tailored recipe for a mood, falling back to the best available drink.

    Inputs:  mood – one of ``mood.MOODS``.
    Returns: dict with drink_id, drink, options, summary, price, explanation, url.
    """
    name, overrides, explanation = mood_mod.MOOD_RECIPES[mood]
    drink = get_drink_by_name(name)
    opts = catalog.normalize_options(drink, {**catalog.default_options(drink, g.user), **overrides})
    ok, reason = machine.check_availability(drink, opts)
    if not ok:
        items, _ = build_menu_items()
        best = next((i for i in items if i["available"]), None)
        if best is None:
            return {"drink": None, "explanation": f"{explanation} Unfortunately: {reason}."}
        drink, opts = best["drink"], best["options"]
        explanation += f" ({name} is unavailable – {reason}; suggesting {drink['name']} instead.)"
    return {"drink_id": drink["id"], "drink": drink["name"], "options": opts,
            "summary": catalog.describe_options(drink, opts),
            "price": catalog.price(drink, opts), "explanation": explanation,
            "url": url_for("shop.drink_page", drink_id=drink["id"], options=json.dumps(opts))}


@bp.route("/mood")
def mood_page():
    """Show the mood-detection screen with consent, webcam, upload and manual picker.

    Inputs:  none.
    Returns: rendered mood page.
    """
    return render_template("mood.html", moods=mood_mod.MOODS, current=session.get("mood"))


@bp.route("/api/mood", methods=("POST",))
def api_mood():
    """Estimate the mood from a camera frame in memory, or accept a manual mood.

    The image bytes stay in local variables only and are deleted before the
    response is built (NFR-01). Only the mood label is kept in the session.

    Inputs:  JSON {"consent": true, "image": "data:image/...;base64,..."} or
             {"mood": "tired" | "happy" | "stressed" | "neutral"}.
    Returns: JSON {mood, confidence, source, suggestion} or {error} with HTTP 400.
    """
    data = request.get_json(silent=True) or {}
    if data.get("mood"):
        if data["mood"] not in mood_mod.MOODS:
            return jsonify(error="Unknown mood"), 400
        result = {"mood": data["mood"], "confidence": 1.0, "source": "manual"}
    else:
        if data.get("consent") is not True:
            return jsonify(error="Camera analysis requires explicit consent."), 400
        try:
            image_bytes = mood_mod.decode_data_url(data.get("image"))
            result = mood_mod.estimate_mood(image_bytes)
        except ValueError as exc:
            return jsonify(error=str(exc)), 400
        finally:
            image_bytes = None  # discard the frame immediately
            data.pop("image", None)
        result["source"] = "camera"
    session["mood"] = result["mood"]
    machine.log_event("mood", f"Mood estimated ({result['source']}): {result['mood']}", "info",
                      g.user["username"] if g.user else "guest")
    get_db().commit()
    result["suggestion"] = mood_suggestion(result["mood"])
    return jsonify(result)


@bp.route("/mood/clear", methods=("POST",))
def clear_mood():
    """Forget the stored mood so recommendations ignore it.

    Inputs:  none.
    Returns: redirect to the menu.
    """
    session.pop("mood", None)
    return redirect(url_for("shop.menu"))


# ---------------------------------------------------------------- assistant (FR-21)

@bp.route("/assistant")
def assistant_page():
    """Show the natural-language drink assistant.

    Inputs:  none.
    Returns: rendered assistant page.
    """
    return render_template("assistant.html")


@bp.route("/api/assistant", methods=("POST",))
def api_assistant():
    """Translate a free-form request into a proposed configuration for confirmation.

    Inputs:  JSON {"text": str}.
    Returns: JSON {drink_id, drink, options, summary, price, available, reason,
             steps, url} or {error} with HTTP 400 for empty input.
    """
    text = ((request.get_json(silent=True) or {}).get("text") or "").strip()
    if not text:
        return jsonify(error="Please describe the drink you want."), 400
    proposal = nl_agent.interpret(text[:300])
    drink = get_drink_by_name(proposal["drink"])
    q = quote(drink, {**catalog.default_options(drink, g.user), **proposal["options"]})
    return jsonify(drink_id=drink["id"], drink=drink["name"], options=q["options"],
                   summary=q["summary"], price=q["price"], available=q["available"],
                   reason=q["reason"], steps=proposal["steps"],
                   url=url_for("shop.drink_page", drink_id=drink["id"],
                               options=json.dumps(q["options"])))
