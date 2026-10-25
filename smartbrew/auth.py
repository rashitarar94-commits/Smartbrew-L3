"""Accounts: registration, credential and NFC login, logout, profile (FR-01–FR-06)."""

import functools
import re
import time
from datetime import datetime, timedelta

from flask import (Blueprint, current_app, flash, g, redirect, render_template,
                   request, session, url_for)
from werkzeug.security import check_password_hash, generate_password_hash

from .catalog import MILK_LABEL, TEMPERATURES
from .db import get_db, now_iso
from .machine import log_event

bp = Blueprint("auth", __name__)

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
USERNAME_RE = re.compile(r"^[A-Za-z0-9_.-]{3,30}$")


def login_required(view):
    """Decorator that redirects anonymous visitors to the login page.

    Inputs:  view – Flask view function.
    Returns: wrapped view function.
    """
    @functools.wraps(view)
    def wrapped(**kwargs):
        """Run the view only when ``g.user`` is set.

        Inputs:  kwargs – URL parameters of the view.
        Returns: the view's response, or a redirect to the login page.
        """
        if g.user is None:
            flash("Please log in first.", "warning")
            return redirect(url_for("auth.login", next=request.path))
        return view(**kwargs)
    return wrapped


def start_session(user, method):
    """Log a user in: reset the session and record the login event.

    Inputs:  user – sqlite Row of the user; method – "password" or "nfc".
    Returns: None.
    """
    admin = {k: session[k] for k in ("admin", "admin_since", "admin_actor") if k in session}
    session.clear()
    session.update(admin)  # keep an open technician session
    session["user_id"] = user["id"]
    session["last_active"] = time.time()
    log_event("auth", f"{user['username']} logged in via {method}", "info", user["username"])


def validate_registration(username, email, password, confirm):
    """Check registration input against the FR-01 rules.

    Inputs:  username, email, password, confirm – strings from the form.
    Returns: list of error messages (empty when everything is valid).
    """
    errors = []
    if not USERNAME_RE.match(username or ""):
        errors.append("Username must be 3–30 letters, digits, '.', '_' or '-'.")
    if not EMAIL_RE.match(email or ""):
        errors.append("Please enter a valid email address.")
    if len(password or "") < 8 or not re.search(r"[A-Za-z]", password) \
            or not re.search(r"\d", password):
        errors.append("Password needs at least 8 characters, including a letter and a digit.")
    if password != confirm:
        errors.append("Passwords do not match.")
    return errors


@bp.route("/register", methods=("GET", "POST"))
def register():
    """Show the registration form and create an account (FR-01).

    Inputs:  POST form fields username, email, password, confirm.
    Returns: the form with errors, or a redirect to the menu, logged in.
    """
    if request.method == "POST":
        f = request.form
        username, email = f.get("username", "").strip(), f.get("email", "").strip().lower()
        errors = validate_registration(username, email, f.get("password", ""), f.get("confirm", ""))
        db = get_db()
        if not errors and db.execute(
                "SELECT 1 FROM users WHERE username = ? OR email = ?", (username, email)).fetchone():
            errors.append("An account with this username or email already exists.")
        if errors:
            for e in errors:
                flash(e, "error")
            return render_template("register.html", form=f), 400
        db.execute(
            "INSERT INTO users (username, email, password_hash, created_at) VALUES (?,?,?,?)",
            (username, email, generate_password_hash(f["password"]), now_iso()))
        log_event("auth", f"Account created: {username}", "info", username)
        db.commit()
        user = db.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
        start_session(user, "password")
        db.commit()
        flash(f"Welcome, {username}! Your account was created.", "success")
        return redirect(url_for("shop.menu"))
    return render_template("register.html", form={})


@bp.route("/login", methods=("GET", "POST"))
def login():
    """Log in with username/email and password, with lockout (FR-02).

    Inputs:  POST form fields login, password; optional ``next`` query arg.
    Returns: the login page (with an error) or a redirect after success.
    """
    if request.method == "POST":
        ident = request.form.get("login", "").strip()
        password = request.form.get("password", "")
        db = get_db()
        user = db.execute("SELECT * FROM users WHERE username = ? OR email = ?",
                          (ident, ident.lower())).fetchone()
        now = datetime.now()
        if user and user["locked_until"] and datetime.fromisoformat(user["locked_until"]) > now:
            flash("Too many failed attempts. Account locked for a few minutes.", "error")
            log_event("auth", f"Login attempt on locked account {user['username']}", "warning")
            db.commit()
            return render_template("login.html"), 403
        if user and check_password_hash(user["password_hash"], password):
            db.execute("UPDATE users SET failed_attempts = 0, locked_until = NULL WHERE id = ?",
                       (user["id"],))
            start_session(user, "password")
            db.commit()
            return redirect(request.args.get("next") or url_for("shop.menu"))
        if user:
            attempts = user["failed_attempts"] + 1
            locked = None
            if attempts >= current_app.config["MAX_FAILED_LOGINS"]:
                locked = (now + timedelta(minutes=current_app.config["LOCKOUT_MINUTES"])) \
                    .replace(microsecond=0).isoformat()
                attempts = 0
                log_event("auth", f"Account {user['username']} locked after failed logins", "warning")
            db.execute("UPDATE users SET failed_attempts = ?, locked_until = ? WHERE id = ?",
                       (attempts, locked, user["id"]))
            db.commit()
        flash("Invalid credentials.", "error")  # generic on purpose (no user enumeration)
        return render_template("login.html"), 401
    return render_template("login.html")


@bp.route("/login/nfc", methods=("POST",))
def login_nfc():
    """Log in by tapping a linked NFC card (FR-04). The reader is simulated by a form field.

    Inputs:  POST form field card_uid.
    Returns: a redirect to the menu, or the login page with an error.
    """
    uid = request.form.get("card_uid", "").strip().upper()
    db = get_db()
    user = db.execute("SELECT * FROM users WHERE nfc_uid = ?", (uid,)).fetchone() if uid else None
    if user is None:
        flash("Unknown card. Log in with your password and link the card in your profile.", "error")
        log_event("auth", f"Unknown NFC card tapped ({uid or 'empty'})", "warning")
        db.commit()
        return render_template("login.html"), 401
    start_session(user, "nfc")
    db.commit()
    return redirect(url_for("shop.menu"))


@bp.route("/logout", methods=("GET", "POST"))
def logout():
    """Log the current user out (FR-05). An open technician session is kept.

    Inputs:  none.
    Returns: a redirect to the public menu.
    """
    admin = {k: session[k] for k in ("admin", "admin_since", "admin_actor") if k in session}
    session.clear()
    session.update(admin)
    flash("You are logged out.", "info")
    return redirect(url_for("shop.menu"))


@bp.route("/profile", methods=("GET", "POST"))
@login_required
def profile():
    """Show and update the profile: preferences, NFC card, prepaid balance (FR-03, FR-06).

    Inputs:  POST form field ``action`` = prefs | link_card | unlink_card | topup,
             plus the fields of that action.
    Returns: the rendered profile page.
    """
    db = get_db()
    if request.method == "POST":
        action = request.form.get("action")
        if action == "prefs":
            milk = request.form.get("pref_milk")
            temp = request.form.get("pref_temperature")
            try:
                strength = min(5, max(1, int(request.form.get("pref_strength", 3))))
            except ValueError:
                strength = 3
            if milk in MILK_LABEL and temp in TEMPERATURES:
                db.execute("UPDATE users SET pref_milk=?, pref_strength=?, pref_temperature=?"
                           " WHERE id=?", (milk, strength, temp, g.user["id"]))
                flash("Preferences saved.", "success")
        elif action == "link_card":
            uid = request.form.get("card_uid", "").strip().upper()
            owner = db.execute("SELECT id FROM users WHERE nfc_uid = ?", (uid,)).fetchone()
            if not re.match(r"^[0-9A-F]{8,20}$", uid):
                flash("Card UID must be 8–20 hexadecimal characters.", "error")
            elif owner and owner["id"] != g.user["id"]:
                flash("This card is already linked to another account.", "error")
            else:
                db.execute("UPDATE users SET nfc_uid = ? WHERE id = ?", (uid, g.user["id"]))
                log_event("auth", f"NFC card linked by {g.user['username']}", "info", g.user["username"])
                flash("Card linked. You can now log in by tapping it.", "success")
        elif action == "unlink_card":
            db.execute("UPDATE users SET nfc_uid = NULL WHERE id = ?", (g.user["id"],))
            flash("Card unlinked.", "info")
        elif action == "topup":
            db.execute("UPDATE users SET prepaid_balance = prepaid_balance + 10 WHERE id = ?",
                       (g.user["id"],))
            log_event("payment", f"Prepaid top-up +10.00 EUR for {g.user['username']}", "info",
                      g.user["username"])
            flash("Employer top-up of 10.00 EUR added (simulated).", "success")
        db.commit()
        return redirect(url_for("auth.profile"))
    return render_template("profile.html", milks=MILK_LABEL, temps=TEMPERATURES)
