"""Checkout, payment, dispensing, transaction records and receipts (FR-22–FR-30)."""

import io
import json
import os
import secrets
import smtplib
from email.message import EmailMessage

import qrcode
from flask import (Blueprint, abort, current_app, flash, g, redirect, render_template,
                   request, send_file, url_for)

from . import catalog, machine
from .auth import EMAIL_RE, login_required
from .db import get_db, get_setting, now_iso
from .shop import get_drink, parse_options_arg, quote

bp = Blueprint("orders", __name__)

PAYMENT_METHODS = {
    "card": "Credit/Debit card (EMV chip / contactless)",
    "apple_pay": "Apple Pay",
    "google_pay": "Google Pay",
    "prepaid": "Prepaid employee card",
}


class PaymentError(Exception):
    """Raised when a payment is declined or the method is unavailable."""


def process_payment(method, amount, prepaid_uid, online):
    """Authorise a payment with the simulated payment providers (FR-22–FR-24, FR-30).

    * card: approved online, or accepted offline (store-and-forward) when the
      network is down. No card number is ever collected (NFR-04).
    * apple_pay / google_pay: only when online.
    * prepaid: debits the local balance of the card's owner; works offline.

    Inputs:  method – key of PAYMENT_METHODS; amount – EUR; prepaid_uid – card
             UID for prepaid payments; online – network status.
    Returns: tuple (payment_ref: str, offline: bool).
    Raises:  PaymentError with a user-facing message.
    """
    if method not in PAYMENT_METHODS:
        raise PaymentError("Please choose a payment method.")
    if method == "card":
        token = secrets.token_hex(4).upper()
        return (f"CARD-{token}", False) if online else (f"OFFLINE-{token}", True)
    if method in ("apple_pay", "google_pay"):
        if not online:
            raise PaymentError("Mobile wallets are unavailable in offline mode. Please use a card.")
        return f"{method.upper()}-{secrets.token_hex(4).upper()}", False
    uid = (prepaid_uid or "").strip().upper()
    db = get_db()
    owner = db.execute("SELECT * FROM users WHERE nfc_uid = ?", (uid,)).fetchone() if uid else None
    if owner is None:
        raise PaymentError("Prepaid card not recognised.")
    if owner["prepaid_balance"] + 1e-9 < amount:
        raise PaymentError(
            f"Insufficient prepaid balance ({owner['prepaid_balance']:.2f} EUR).")
    db.execute("UPDATE users SET prepaid_balance = prepaid_balance - ? WHERE id = ?",
               (amount, owner["id"]))
    return f"PREPAID-{uid[-4:]}", False


@bp.route("/checkout")
def checkout():
    """Show the order summary and payment choices (FR-16, FR-22–FR-24).

    Inputs:  query args drink_id, options (JSON), optional recipe (name).
    Returns: rendered checkout page.
    """
    drink = get_drink(request.args.get("drink_id", type=int) or 0)
    q = quote(drink, parse_options_arg(request.args.get("options")))
    return render_template("checkout.html", drink=drink, q=q, methods=PAYMENT_METHODS,
                           recipe=request.args.get("recipe"),
                           options_json=json.dumps(q["options"]))


@bp.route("/order", methods=("POST",))
def place_order():
    """Pay, dispense and record an order atomically (FR-12, FR-25, FR-26, NFR-08).

    Inputs:  form fields drink_id, options (JSON), payment_method, prepaid_uid,
             receipt_method (qr|email), email.
    Returns: redirect to the receipt page, or back to checkout with an error.
    """
    form = request.form
    drink = get_drink(int(form.get("drink_id", 0)))
    opts = catalog.normalize_options(drink, parse_options_arg(form.get("options")))
    back = url_for("orders.checkout", drink_id=drink["id"], options=json.dumps(opts))
    db = get_db()
    ok, reason = machine.check_availability(drink, opts)
    if not ok:  # enforced on the server too, not only by greying out the UI
        flash(f"{drink['name']} cannot be prepared right now: {reason}.", "error")
        return redirect(url_for("shop.menu"))

    amount = catalog.price(drink, opts)
    online = get_setting("network_online", "1") == "1"
    actor = g.user["username"] if g.user else "guest"
    method = form.get("payment_method")
    try:
        payment_ref, offline = process_payment(method, amount, form.get("prepaid_uid"), online)
    except PaymentError as exc:
        db.rollback()
        machine.log_event("payment", f"Payment declined ({method}): {exc}", "warning", actor)
        db.commit()
        flash(str(exc), "error")
        return redirect(back)

    usage = catalog.ingredient_usage(drink, opts)
    receipt_no = secrets.token_hex(5).upper()
    try:
        machine.dispense(usage, actor)
        db.execute(
            "INSERT INTO transactions (receipt_no, user_id, drink_id, drink_name, options, price,"
            " payment_method, payment_ref, offline, created_at) VALUES (?,?,?,?,?,?,?,?,?,?)",
            (receipt_no, g.user["id"] if g.user else None, drink["id"], drink["name"],
             json.dumps(opts), amount, method, payment_ref, int(offline), now_iso()))
        machine.log_event("order", f"{drink['name']} dispensed ({catalog.describe_options(drink, opts)})"
                          f" – {amount:.2f} EUR via {method}{' [offline]' if offline else ''}",
                          "info", actor)
        db.commit()
    except Exception:
        db.rollback()  # nothing is half-written: payment, stock and record roll back together
        machine.log_event("fault", f"Dispense failed for {drink['name']}; payment reversed",
                          "critical", actor)
        db.commit()
        raise

    if form.get("receipt_method") == "email":
        email = (form.get("email") or "").strip()
        if not deliver_email(receipt_no, email):
            flash("Receipt email could not be sent – please check the address.", "error")
    flash(f"Enjoy your {drink['name']}!", "success")
    return redirect(url_for("orders.receipt", receipt_no=receipt_no))


def get_transaction(receipt_no):
    """Load a transaction by receipt number or abort with 404.

    Inputs:  receipt_no – str.
    Returns: sqlite Row of the transaction.
    """
    tx = get_db().execute("SELECT * FROM transactions WHERE receipt_no = ?",
                          (receipt_no,)).fetchone()
    if tx is None:
        abort(404)
    return tx


def receipt_text(tx):
    """Render a plain-text receipt (used for the QR payload and the email body).

    Inputs:  tx – transaction row.
    Returns: multi-line str.
    """
    drink = get_drink(tx["drink_id"])
    opts = json.loads(tx["options"])
    return (f"SmartBrew AI receipt #{tx['receipt_no']}\n"
            f"Date: {tx['created_at'].replace('T', ' ')}\n"
            f"Item: {tx['drink_name']} ({catalog.describe_options(drink, opts)})\n"
            f"Total: {tx['price']:.2f} EUR\n"
            f"Paid with: {PAYMENT_METHODS.get(tx['payment_method'], tx['payment_method'])}"
            f"{' (offline, pending sync)' if tx['offline'] else ''}\n"
            f"Ref: {tx['payment_ref']}")


@bp.route("/receipt/<receipt_no>")
def receipt(receipt_no):
    """Show the receipt with its QR code and the email option (FR-27, FR-28).

    Inputs:  receipt_no – URL part.
    Returns: rendered receipt page.
    """
    tx = get_transaction(receipt_no)
    drink = get_drink(tx["drink_id"])
    return render_template("receipt.html", tx=tx, drink=drink,
                           summary=catalog.describe_options(drink, json.loads(tx["options"])),
                           method=PAYMENT_METHODS.get(tx["payment_method"]),
                           email=g.user["email"] if g.user else "")


@bp.route("/receipt/<receipt_no>/qr.png")
def receipt_qr(receipt_no):
    """Generate the receipt QR code as a PNG (FR-27).

    The QR contains the full receipt text and the receipt URL, so a phone
    can read it even if it cannot reach the machine.

    Inputs:  receipt_no – URL part.
    Returns: PNG image response.
    """
    tx = get_transaction(receipt_no)
    payload = receipt_text(tx) + "\n" + url_for("orders.receipt", receipt_no=receipt_no,
                                                _external=True)
    img = qrcode.make(payload, box_size=6, border=2)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return send_file(buf, mimetype="image/png")


def deliver_email(receipt_no, address):
    """Send the receipt by email (FR-28).

    The message goes through SMTP when ``SMARTBREW_SMTP_HOST`` is set.
    Otherwise it is written as an ``.eml`` file to the outbox folder, so
    the prototype also works offline. The address is not stored (privacy).

    Inputs:  receipt_no – receipt to send; address – recipient email.
    Returns: bool, True when the email was sent or written to the outbox.
    """
    if not EMAIL_RE.match(address or ""):
        return False
    tx = get_transaction(receipt_no)
    cfg = current_app.config
    msg = EmailMessage()
    msg["Subject"] = f"Your SmartBrew receipt #{receipt_no}"
    msg["From"] = cfg["MAIL_FROM"]
    msg["To"] = address
    msg.set_content(receipt_text(tx) + "\n\nThank you for using SmartBrew AI!")
    try:
        if cfg.get("SMTP_HOST"):
            with smtplib.SMTP(cfg["SMTP_HOST"], cfg["SMTP_PORT"], timeout=5) as smtp:
                smtp.send_message(msg)
            where = f"SMTP {cfg['SMTP_HOST']}"
        else:
            path = os.path.join(cfg["OUTBOX"], f"receipt-{receipt_no}.eml")
            with open(path, "wb") as fh:
                fh.write(bytes(msg))
            where = "outbox"
    except OSError:
        return False
    machine.log_event("order", f"Receipt {receipt_no} emailed ({where})", "info",
                      g.user["username"] if g.user else "guest")
    get_db().commit()
    return True


@bp.route("/receipt/<receipt_no>/email", methods=("POST",))
def email_receipt(receipt_no):
    """Handle the "send receipt by email" form on the receipt page.

    Inputs:  receipt_no – URL part; form field email.
    Returns: redirect back to the receipt page with a status message.
    """
    get_transaction(receipt_no)
    address = request.form.get("email", "").strip()
    if deliver_email(receipt_no, address):
        flash(f"Receipt sent to {address}.", "success")
    else:
        flash("Please enter a valid email address.", "error")
    return redirect(url_for("orders.receipt", receipt_no=receipt_no))


@bp.route("/history")
@login_required
def history():
    """List the logged-in user's recorded transactions (FR-26, FR-29).

    Inputs:  none.
    Returns: rendered history page.
    """
    rows = []
    for tx in get_db().execute("SELECT * FROM transactions WHERE user_id = ? ORDER BY id DESC",
                               (g.user["id"],)):
        drink = get_drink(tx["drink_id"])
        rows.append({"tx": tx, "summary": catalog.describe_options(drink, json.loads(tx["options"])),
                     "options_json": tx["options"]})
    return render_template("history.html", rows=rows, methods=PAYMENT_METHODS)
