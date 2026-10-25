"""F2 – Browse + real-time customisation + nutrition; F3 – block unavailable drinks."""

import json

from conftest import drink_id, execute, login


def test_menu_shows_categories_and_drinks(client):
    """The menu lists categories and drinks with prices.

    Inputs:  pytest fixtures (client).
    Returns: None; fails through assert if the behaviour is wrong.
    """
    page = client.get("/").data
    for text in (b"Coffee", b"Milk coffee", b"Tea", b"Cappuccino", b"Hot Chocolate", b"\xe2\x82\xac"):
        assert text in page
    tea = client.get("/?category=Tea").data
    assert b"Chai Latte" in tea and b"data-drink=\"Espresso\"" not in tea


def test_live_quote_updates_price_and_nutrition(client, app):
    """Changing milk, syrup, size and shots changes price and nutrition.

    Inputs:  pytest fixtures (client, app).
    Returns: None; fails through assert if the behaviour is wrong.
    """
    did = drink_id(app, "Cappuccino")
    base = client.post("/api/quote", json={"drink_id": did, "options": {"milk": "whole"}}).json
    custom = client.post("/api/quote", json={"drink_id": did, "options": {
        "milk": "oat", "syrup": 2, "size": "L", "extra_shot": True, "strength": 5}}).json
    assert base["price"] == 2.80
    assert custom["price"] == round(2.80 + 0.50 + 0.40 + 2 * 0.40 + 0.50, 2)
    assert custom["nutrition"]["sugar_g"] > base["nutrition"]["sugar_g"]
    assert custom["nutrition"]["caffeine_mg"] > base["nutrition"]["caffeine_mg"]
    assert "oats (gluten)" in custom["nutrition"]["allergens"]
    assert custom["summary"].startswith("Size L · Oat milk · Strength 5")


def test_invalid_options_are_clamped(client, app):
    """Out-of-range or bogus options are normalised instead of trusted.

    Inputs:  pytest fixtures (client, app).
    Returns: None; fails through assert if the behaviour is wrong.
    """
    did = drink_id(app, "Latte")
    q = client.post("/api/quote", json={"drink_id": did, "options": {
        "milk": "none", "strength": 99, "syrup": -4, "size": "XXL"}}).json
    assert q["options"] == {**q["options"], "milk": "whole", "strength": 5, "syrup": 0, "size": "M"}


def test_milk_out_disables_milk_drinks_with_reason(client, app):
    """With every milk below threshold, milk drinks are greyed out with a reason.

    Inputs:  pytest fixtures (client, app).
    Returns: None; fails through assert if the behaviour is wrong.
    """
    execute(app, "UPDATE ingredients SET level = 0 WHERE name LIKE 'milk_%'")
    page = client.get("/").data.decode()
    assert 'data-drink="Latte" data-available="0"' in page
    assert 'data-drink="Espresso" data-available="1"' in page
    assert "Out of" in page and "milk" in page


def test_server_rejects_order_for_unavailable_drink(client, app):
    """Even a hand-crafted request cannot order a drink that cannot be made.

    Inputs:  pytest fixtures (client, app).
    Returns: None; fails through assert if the behaviour is wrong.
    """
    execute(app, "UPDATE ingredients SET level = 10 WHERE name = 'cocoa'")  # below threshold 30
    did = drink_id(app, "Hot Chocolate")
    r = client.post("/order", data={"drink_id": did, "options": "{}", "payment_method": "card"},
                    follow_redirects=True)
    assert b"cannot be prepared" in r.data


def test_other_milk_keeps_drink_available(client, app):
    """If only the preferred milk is out, the drink stays available with another milk.

    Inputs:  pytest fixtures (client, app).
    Returns: None; fails through assert if the behaviour is wrong.
    """
    execute(app, "UPDATE ingredients SET level = 0 WHERE name = 'milk_whole'")
    page = client.get("/").data.decode()
    assert 'data-drink="Latte" data-available="1"' in page
    did = drink_id(app, "Latte")
    q = client.post("/api/quote", json={"drink_id": did, "options": {"milk": "whole"}}).json
    assert not q["available"] and q["milk_available"]["oat"] is True


def test_no_cups_blocks_everything(client, app):
    """Cups are an ingredient too: with no cups nothing can be ordered.

    Inputs:  pytest fixtures (client, app).
    Returns: None; fails through assert if the behaviour is wrong.
    """
    execute(app, "UPDATE ingredients SET level = 0 WHERE name = 'cups'")
    assert 'data-available="1"' not in client.get("/").data.decode()
