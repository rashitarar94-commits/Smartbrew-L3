"""F4 – Custom recipes: save, name, modify, delete, one-touch ordering."""

import json

from conftest import drink_id, login, query


def _create(client, app, name="Monday fuel"):
    """Save a customised Flat White recipe for the logged-in user.

    Inputs:  client, app – fixtures; name – recipe name.
    Returns: response of the POST.
    """
    opts = {"milk": "oat", "strength": 5, "syrup": 1, "size": "L"}
    return client.post("/recipes", data={"drink_id": drink_id(app, "Flat White"), "name": name,
                                         "options": json.dumps(opts)})


def test_save_and_list_recipe(client, app):
    """A saved recipe appears in the list with its customisation.

    Inputs:  pytest fixtures (client, app).
    Returns: None; fails through assert if the behaviour is wrong.
    """
    login(client)
    _create(client, app)
    page = client.get("/recipes").data
    assert b"Monday fuel" in page and b"Oat milk" in page and b"Strength 5" in page


def test_duplicate_name_rejected(client, app):
    """The same recipe name cannot be used twice by one user (case-insensitive).

    Inputs:  pytest fixtures (client, app).
    Returns: None; fails through assert if the behaviour is wrong.
    """
    login(client)
    _create(client, app)
    r = _create(client, app, "monday FUEL")
    assert r.status_code == 302
    assert len(query(app, "SELECT * FROM recipes")) == 1


def test_modify_and_delete_recipe(client, app):
    """A recipe can be renamed/re-parameterised and then deleted.

    Inputs:  pytest fixtures (client, app).
    Returns: None; fails through assert if the behaviour is wrong.
    """
    login(client)
    _create(client, app)
    rid = query(app, "SELECT id FROM recipes")[0]["id"]
    client.post(f"/recipes/{rid}/update", data={"name": "Friday chill",
                                                "options": json.dumps({"milk": "whole", "strength": 2})})
    row = query(app, "SELECT * FROM recipes WHERE id = ?", (rid,))[0]
    assert row["name"] == "Friday chill" and json.loads(row["options"])["strength"] == 2
    client.post(f"/recipes/{rid}/delete")
    assert query(app, "SELECT * FROM recipes") == []


def test_one_touch_order_goes_to_checkout(client, app):
    """Ordering a recipe jumps straight to checkout with the stored options.

    Inputs:  pytest fixtures (client, app).
    Returns: None; fails through assert if the behaviour is wrong.
    """
    login(client)
    _create(client, app)
    rid = query(app, "SELECT id FROM recipes")[0]["id"]
    r = client.get(f"/recipes/{rid}/order", follow_redirects=True)
    assert b"Checkout" in r.data and b"Monday fuel" in r.data and b"Oat milk" in r.data


def test_recipes_are_private(client, app):
    """Another user cannot edit, delete or order someone else's recipe.

    Inputs:  pytest fixtures (client, app).
    Returns: None; fails through assert if the behaviour is wrong.
    """
    login(client)
    _create(client, app)
    rid = query(app, "SELECT id FROM recipes")[0]["id"]
    client.get("/logout")
    login(client, "bob")
    assert client.post(f"/recipes/{rid}/delete").status_code == 404
    assert client.get(f"/recipes/{rid}/order").status_code == 404


def test_recipes_require_login(client):
    """Anonymous users are redirected to the login page.

    Inputs:  pytest fixtures (client).
    Returns: None; fails through assert if the behaviour is wrong.
    """
    assert client.get("/recipes").status_code == 302
