"""F1 – Accounts: registration, credential login with lockout, NFC card login, auto-logout."""

import time

from conftest import login, query


def test_register_creates_account_and_logs_in(client, app):
    """A valid registration stores a hashed password and logs the user in.

    Inputs:  pytest fixtures (client, app).
    Returns: None; fails through assert if the behaviour is wrong.
    """
    r = client.post("/register", data={"username": "carol", "email": "carol@example.com",
                                       "password": "secret123", "confirm": "secret123"},
                    follow_redirects=True)
    assert r.status_code == 200 and b"carol" in r.data
    row = query(app, "SELECT password_hash FROM users WHERE username = 'carol'")[0]
    assert row["password_hash"] != "secret123" and row["password_hash"].startswith(("scrypt", "pbkdf2"))


def test_register_rejects_duplicate_and_weak_password(client):
    """Duplicate emails and weak passwords are refused with HTTP 400.

    Inputs:  pytest fixtures (client).
    Returns: None; fails through assert if the behaviour is wrong.
    """
    r = client.post("/register", data={"username": "alice2", "email": "alice@example.com",
                                       "password": "secret123", "confirm": "secret123"})
    assert r.status_code == 400 and b"already exists" in r.data
    r = client.post("/register", data={"username": "dave", "email": "dave@example.com",
                                       "password": "short", "confirm": "short"})
    assert r.status_code == 400 and b"at least 8" in r.data


def test_login_success_and_generic_error(client):
    """Correct credentials log in; wrong ones give a generic error.

    Inputs:  pytest fixtures (client).
    Returns: None; fails through assert if the behaviour is wrong.
    """
    assert login(client, "alice", "wrong").status_code == 401
    r = login(client)
    assert r.status_code == 302
    assert b"alice" in client.get("/").data


def test_lockout_after_five_failures(client):
    """Five failed attempts lock the account, even for the correct password.

    Inputs:  pytest fixtures (client).
    Returns: None; fails through assert if the behaviour is wrong.
    """
    for _ in range(5):
        login(client, "bob", "nope")
    assert login(client, "bob", "password123").status_code == 403


def test_nfc_link_and_tap_login(client, app):
    """A user links a card in the profile and then logs in by tapping it.

    Inputs:  pytest fixtures (client, app).
    Returns: None; fails through assert if the behaviour is wrong.
    """
    login(client, "bob")
    client.post("/profile", data={"action": "link_card", "card_uid": "04a1b2c3"})
    assert query(app, "SELECT nfc_uid FROM users WHERE username='bob'")[0]["nfc_uid"] == "04A1B2C3"
    client.get("/logout")
    r = client.post("/login/nfc", data={"card_uid": "04A1B2C3"})
    assert r.status_code == 302
    assert b"bob" in client.get("/").data


def test_card_already_linked_and_unknown_card(client):
    """A card linked to someone else is refused; unknown cards cannot log in.

    Inputs:  pytest fixtures (client).
    Returns: None; fails through assert if the behaviour is wrong.
    """
    login(client, "bob")
    r = client.post("/profile", data={"action": "link_card", "card_uid": "04AA11BB"},
                    follow_redirects=True)
    assert b"already linked" in r.data
    client.get("/logout")
    assert client.post("/login/nfc", data={"card_uid": "DEADBEEF"}).status_code == 401


def test_inactivity_auto_logout(client):
    """A session idle longer than the timeout is logged out on the next request.

    Inputs:  pytest fixtures (client).
    Returns: None; fails through assert if the behaviour is wrong.
    """
    login(client)
    with client.session_transaction() as s:
        s["last_active"] = time.time() - 3600
    r = client.get("/", follow_redirects=True)
    assert b"inactivity" in r.data
    assert client.get("/recipes").status_code == 302


def test_preferences_prefill_customiser(client, app):
    """Saved preferences become the default options of a drink.

    Inputs:  pytest fixtures (client, app).
    Returns: None; fails through assert if the behaviour is wrong.
    """
    login(client, "bob")
    client.post("/profile", data={"action": "prefs", "pref_milk": "lactose_free",
                                  "pref_strength": "5", "pref_temperature": "extra_hot"})
    did = query(app, "SELECT id FROM drinks WHERE name='Latte'")[0]["id"]
    page = client.get(f"/drink/{did}").data
    assert b'id="milk-lactose_free" value="lactose_free" checked' in page
