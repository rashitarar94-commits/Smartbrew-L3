"""F5 – Payment + dispensing + transaction recording + offline fallback; F6 – receipts."""

import json
import os

from conftest import drink_id, execute, login, query


def _order(client, app, drink="Latte", method="card", options=None, **extra):
    """Place an order through the real checkout form.

    Inputs:  client, app – fixtures; drink – drink name; method – payment method;
             options – option dict; extra – additional form fields.
    Returns: response of the POST (not followed).
    """
    data = {"drink_id": drink_id(app, drink), "options": json.dumps(options or {}),
            "payment_method": method, **extra}
    return client.post("/order", data=data)


def test_prepaid_payment_records_transaction_with_parameters(client, app):
    """Paying with the prepaid badge debits the balance and stores all parameters.

    Inputs:  pytest fixtures (client, app).
    Returns: None; fails through assert if the behaviour is wrong.
    """
    login(client)
    opts = {"milk": "oat", "strength": 4, "syrup": 2, "temperature": "extra_hot", "size": "L"}
    r = _order(client, app, "Latte", "prepaid", opts, prepaid_uid="04AA11BB")
    assert r.status_code == 302 and "/receipt/" in r.location
    tx = query(app, "SELECT * FROM transactions ORDER BY id DESC LIMIT 1")[0]
    stored = json.loads(tx["options"])
    assert stored["milk"] == "oat" and stored["syrup"] == 2 and stored["temperature"] == "extra_hot"
    expected = round(3.00 + 0.50 + 0.40 + 2 * 0.40, 2)
    assert tx["price"] == expected
    balance = query(app, "SELECT prepaid_balance FROM users WHERE username='alice'")[0][0]
    assert round(balance, 2) == round(20 - expected, 2)


def test_insufficient_prepaid_balance_is_declined(client, app):
    """A prepaid card without enough balance is declined and nothing is dispensed.

    Inputs:  pytest fixtures (client, app).
    Returns: None; fails through assert if the behaviour is wrong.
    """
    execute(app, "UPDATE users SET prepaid_balance = 1 WHERE username='alice'")
    before = query(app, "SELECT level FROM ingredients WHERE name='cups'")[0][0]
    r = _order(client, app, "Latte", "prepaid", prepaid_uid="04AA11BB")
    assert r.status_code == 302 and "/checkout" in r.location
    assert query(app, "SELECT level FROM ingredients WHERE name='cups'")[0][0] == before
    assert query(app, "SELECT COUNT(*) FROM transactions WHERE payment_ref LIKE 'PREPAID%'")[0][0] == 0


def test_dispense_deducts_ingredients_and_fills_bins(client, app):
    """A brew consumes ingredients (incl. a cup) and fills the grounds bin and waste tank.

    Inputs:  pytest fixtures (client, app).
    Returns: None; fails through assert if the behaviour is wrong.
    """
    _order(client, app, "Cappuccino", "card", {"milk": "whole"})
    levels = {r["name"]: r["level"] for r in query(app, "SELECT name, level FROM ingredients")}
    assert levels["cups"] == 99 and levels["milk_whole"] == 2000 - 120
    bins = {r["name"]: r["level"] for r in query(app, "SELECT name, level FROM bins")}
    assert bins["grounds_bin"] > 0 and bins["waste_tank"] == 25


def test_wallets_and_cards(client, app):
    """Apple/Google Pay and cards are accepted online; no card number is stored.

    Inputs:  pytest fixtures (client, app).
    Returns: None; fails through assert if the behaviour is wrong.
    """
    for method in ("apple_pay", "google_pay", "card"):
        assert "/receipt/" in _order(client, app, "Espresso", method).location
    refs = [r[0] for r in query(app, "SELECT payment_ref FROM transactions WHERE receipt_no NOT LIKE 'SEED%'")]
    assert refs[0].startswith("APPLE_PAY-") and refs[2].startswith("CARD-")


def test_offline_fallback(client, app):
    """Offline: wallets are refused, cards are accepted offline (queued), weather is ignored.

    Inputs:  pytest fixtures (client, app).
    Returns: None; fails through assert if the behaviour is wrong.
    """
    execute(app, "UPDATE settings SET value = '0' WHERE key = 'network_online'")
    page = client.get("/").data
    assert b"Offline mode" in page and b"Weather unavailable" in page
    r = _order(client, app, "Espresso", "apple_pay")
    assert "/checkout" in r.location
    r = _order(client, app, "Espresso", "card")
    assert "/receipt/" in r.location
    tx = query(app, "SELECT * FROM transactions ORDER BY id DESC LIMIT 1")[0]
    assert tx["offline"] == 1 and tx["payment_ref"].startswith("OFFLINE-")


def test_receipt_page_and_qr_code(client, app):
    """The receipt page shows the transaction and a PNG QR code.

    Inputs:  pytest fixtures (client, app).
    Returns: None; fails through assert if the behaviour is wrong.
    """
    loc = _order(client, app, "Mocha", "card").location
    page = client.get(loc).data
    assert b"Mocha" in page and b"qr.png" in page
    qr = client.get(loc + "/qr.png")
    assert qr.status_code == 200 and qr.mimetype == "image/png" and qr.data[:8] == b"\x89PNG\r\n\x1a\n"


def test_email_receipt_written_to_outbox(client, app):
    """Without SMTP, the emailed receipt is written as an .eml file to the outbox.

    Inputs:  pytest fixtures (client, app).
    Returns: None; fails through assert if the behaviour is wrong.
    """
    loc = _order(client, app, "Mocha", "card", receipt_method="email",
                 email="someone@example.com").location
    receipt_no = loc.rsplit("/", 1)[1]
    path = os.path.join(app.config["OUTBOX"], f"receipt-{receipt_no}.eml")
    assert os.path.exists(path)
    content = open(path, encoding="utf-8").read()
    assert "someone@example.com" in content and "Mocha" in content
    r = client.post(f"/receipt/{receipt_no}/email", data={"email": "not-an-email"},
                    follow_redirects=True)
    assert b"valid email" in r.data


def test_history_lists_transactions(client):
    """The history page shows the user's recorded transactions.

    Inputs:  pytest fixtures (client).
    Returns: None; fails through assert if the behaviour is wrong.
    """
    login(client)
    page = client.get("/history").data
    assert page.count(b"Latte") >= 6
