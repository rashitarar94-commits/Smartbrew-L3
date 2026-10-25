"""Secure administrative mode for maintenance staff (FR-31–FR-37).

Admin mode is entered with a technician PIN, an NFC master card, or the
physical key switch (simulated). It holds the inventory, bin, fault and
event-log screens, plus a simulation panel for demo-only environment
inputs (weather, time, network).
"""

import functools
import time

from flask import (Blueprint, current_app, flash, jsonify, redirect, render_template,
                   request, session, url_for)
from werkzeug.security import check_password_hash

from . import machine
from .db import get_db, get_setting, set_setting

bp = Blueprint("admin", __name__, url_prefix="/admin")

WEATHER_CONDITIONS = ("sunny", "cloudy", "rainy", "snowy")


def admin_required(view):
    """Decorator that only allows active, non-expired admin sessions (NFR-03).

    Inputs:  view – Flask view function.
    Returns: wrapped view; anonymous calls get 403 (JSON) or a redirect.
    """
    @functools.wraps(view)
    def wrapped(**kwargs):
        """Check the admin session and its timeout before running the view.

        Inputs:  kwargs – URL parameters of the view.
        Returns: the view's response, HTTP 403 JSON, or a redirect to admin login.
        """
        since = session.get("admin_since", 0)
        if not session.get("admin") or time.time() - since > current_app.config["ADMIN_TIMEOUT_SECONDS"]:
            for k in ("admin", "admin_since", "admin_actor"):
                session.pop(k, None)
            if request.path.startswith("/admin/api/"):
                return jsonify(error="admin mode required"), 403
            flash("Administrative mode required.", "warning")
            return redirect(url_for("admin.login"))
        session["admin_since"] = time.time()
        return view(**kwargs)
    return wrapped


def actor():
    """Return the identifier of the current admin for the audit log (NFR-11).

    Inputs:  none.
    Returns: str such as "technician (PIN)".
    """
    return session.get("admin_actor", "technician")


@bp.route("/login", methods=("GET", "POST"))
def login():
    """Enter administrative mode with a PIN, NFC master card, or physical key (FR-31).

    Inputs:  POST form field ``method`` (pin | master_card | key) and ``secret``.
    Returns: admin login page (with an error) or a redirect to the dashboard.
    """
    if request.method == "POST":
        method = request.form.get("method")
        secret = request.form.get("secret", "").strip()
        ok = False
        if method == "pin":
            ok = check_password_hash(get_setting("technician_pin_hash"), secret)
        elif method == "master_card":
            ok = secret.upper() == get_setting("master_card_uid")
        elif method == "key":
            ok = secret.upper() == get_setting("physical_key_id")
        db = get_db()
        if ok:
            labels = {"pin": "PIN", "master_card": "NFC master card", "key": "physical key"}
            session.update(admin=True, admin_since=time.time(),
                           admin_actor=f"technician ({labels[method]})")
            machine.log_event("admin", f"Admin mode entered via {labels[method]}", "info", actor())
            db.commit()
            return redirect(url_for("admin.dashboard"))
        machine.log_event("admin", f"Admin access denied (method: {method})", "warning")
        db.commit()
        flash("Access denied.", "error")
        return render_template("admin/login.html"), 401
    return render_template("admin/login.html")


@bp.route("/logout", methods=("POST",))
def logout():
    """Leave administrative mode.

    Inputs:  none.
    Returns: redirect to the menu.
    """
    if session.get("admin"):
        machine.log_event("admin", "Admin mode exited", "info", actor())
        get_db().commit()
    for k in ("admin", "admin_since", "admin_actor"):
        session.pop(k, None)
    return redirect(url_for("shop.menu"))


@bp.route("/")
@admin_required
def dashboard():
    """Show the maintenance dashboard (inventory, bins, live faults, simulation).

    Inputs:  none.
    Returns: rendered dashboard page.
    """
    return render_template("admin/dashboard.html", faults=machine.FAULT_CATALOGUE,
                           conditions=WEATHER_CONDITIONS,
                           sim={k: get_setting(k, "") for k in
                                ("network_online", "weather_temp", "weather_condition",
                                 "time_override")})


@bp.route("/api/status")
@admin_required
def api_status():
    """Live machine status, polled by the dashboard every few seconds (FR-36).

    Inputs:  none.
    Returns: JSON {ingredients, bins, faults, halted, events}.
    """
    db = get_db()
    ingredients = [{**dict(i), "pct": round(100 * i["level"] / i["capacity"]),
                    "low": i["level"] < machine.LOW_STOCK_RATIO * i["capacity"]}
                   for i in db.execute("SELECT * FROM ingredients ORDER BY label")]
    events = [dict(e) for e in db.execute("SELECT * FROM events ORDER BY id DESC LIMIT 12")]
    return jsonify(ingredients=ingredients, bins=machine.bin_status(),
                   faults=[dict(f) for f in machine.active_faults()],
                   halted=machine.halt_reason(), events=events)


@bp.route("/refill", methods=("POST",))
@admin_required
def refill():
    """Register a refill or reset an ingredient counter to max (FR-32).

    Inputs:  form fields ingredient, quantity (number) or reset=1.
    Returns: redirect to the dashboard with a status message.
    """
    name = request.form.get("ingredient")
    reset = request.form.get("reset") == "1"
    try:
        qty = None if reset else float(request.form.get("quantity", "0"))
        ing = machine.refill(name, actor(), quantity=qty, reset=reset)
        flash(f"{ing['label']}: now {ing['level']:g} {ing['unit']}.", "success")
    except ValueError as exc:
        flash(str(exc), "error")
    get_db().commit()
    return redirect(url_for("admin.dashboard"))


@bp.route("/level", methods=("POST",))
@admin_required
def set_level():
    """Set an ingredient level directly (demo helper, e.g. empty the milk).

    Inputs:  form fields ingredient, level.
    Returns: redirect to the dashboard.
    """
    try:
        machine.set_level(request.form["ingredient"], float(request.form["level"]), actor())
        get_db().commit()
    except (KeyError, ValueError):
        flash("Invalid level.", "error")
    return redirect(url_for("admin.dashboard"))


@bp.route("/bins/<name>/empty", methods=("POST",))
@admin_required
def empty_bin(name):
    """Register that a bin was emptied (FR-35).

    Inputs:  name – bin name in the URL.
    Returns: redirect to the dashboard.
    """
    try:
        machine.empty_bin(name, actor())
        flash("Bin emptied; operations resumed.", "success")
    except ValueError as exc:
        flash(str(exc), "error")
    get_db().commit()
    return redirect(url_for("admin.dashboard"))


@bp.route("/bins/<name>/simulate", methods=("POST",))
@admin_required
def simulate_bin(name):
    """Demo helper: set a bin to a fill percentage, as if many drinks were brewed.

    Inputs:  name – bin name; form field pct (0–100).
    Returns: redirect to the dashboard.
    """
    db = get_db()
    try:
        pct = max(0.0, min(100.0, float(request.form.get("pct", "0"))))
    except ValueError:
        pct = 0.0
    db.execute("UPDATE bins SET level = capacity * ? / 100.0 WHERE name = ?", (pct, name))
    machine.log_event("settings", f"[simulation] {name} set to {pct:g}%", "info", actor())
    machine.check_bins()
    db.commit()
    return redirect(url_for("admin.dashboard"))


@bp.route("/faults", methods=("POST",))
@admin_required
def inject_fault():
    """Demo helper: inject a hardware fault as if reported by a sensor (FR-36).

    Inputs:  form field code (key of FAULT_CATALOGUE).
    Returns: redirect to the dashboard.
    """
    try:
        machine.raise_fault(request.form.get("code", ""), actor="sensor (simulated)")
        get_db().commit()
    except ValueError as exc:
        flash(str(exc), "error")
    return redirect(url_for("admin.dashboard"))


@bp.route("/faults/<int:fault_id>/resolve", methods=("POST",))
@admin_required
def resolve_fault(fault_id):
    """Resolve an open fault; the resolution is logged with the technician (FR-36).

    Inputs:  fault_id – URL part.
    Returns: JSON {ok} for fetch calls, otherwise a redirect to the dashboard.
    """
    ok = machine.resolve_fault(fault_id, actor())
    get_db().commit()
    if request.accept_mimetypes.best == "application/json":
        return jsonify(ok=ok)
    return redirect(url_for("admin.dashboard"))


def query_events(type_=None, severity=None, limit=500):
    """Filter the event log.

    Inputs:  type_ – event type or None; severity – severity or None; limit – max rows.
    Returns: list of dicts, newest first.
    """
    sql, args = "SELECT * FROM events WHERE 1=1", []
    if type_:
        sql += " AND type = ?"
        args.append(type_)
    if severity:
        sql += " AND severity = ?"
        args.append(severity)
    sql += " ORDER BY id DESC LIMIT ?"
    args.append(limit)
    return [dict(r) for r in get_db().execute(sql, args)]


@bp.route("/events")
@admin_required
def events():
    """Show the filterable event log (FR-37).

    Inputs:  optional query args type, severity.
    Returns: rendered event-log page.
    """
    type_, sev = request.args.get("type") or None, request.args.get("severity") or None
    types = [r[0] for r in get_db().execute("SELECT DISTINCT type FROM events ORDER BY type")]
    return render_template("admin/events.html", events=query_events(type_, sev),
                           types=types, type_=type_, severity=sev)


@bp.route("/api/events")
@admin_required
def api_events():
    """Export the event log as JSON for remote diagnostics (FR-37).

    Inputs:  optional query args type, severity, limit.
    Returns: JSON list of events (downloaded as a file with ``?download=1``).
    """
    data = query_events(request.args.get("type") or None, request.args.get("severity") or None,
                        request.args.get("limit", 500, type=int))
    resp = jsonify(data)
    if request.args.get("download"):
        resp.headers["Content-Disposition"] = "attachment; filename=smartbrew-events.json"
    return resp


@bp.route("/simulation", methods=("POST",))
@admin_required
def simulation():
    """Update the demo environment: network status, weather and time of day.

    Inputs:  form fields network_online (checkbox), weather_temp,
             weather_condition, time_override (hour 0–23 or empty).
    Returns: redirect to the dashboard.
    """
    f = request.form
    online = "1" if f.get("network_online") else "0"
    if online != get_setting("network_online"):
        machine.log_event("settings", "Network " + ("restored" if online == "1" else
                          "lost – offline fallback active"), "info" if online == "1" else "warning",
                          actor())
    set_setting("network_online", online)
    try:
        set_setting("weather_temp", float(f.get("weather_temp", "15")))
    except ValueError:
        pass
    if f.get("weather_condition") in WEATHER_CONDITIONS:
        set_setting("weather_condition", f["weather_condition"])
    hour = f.get("time_override", "").strip()
    set_setting("time_override", hour if hour.isdigit() and 0 <= int(hour) <= 23 else "")
    get_db().commit()
    flash("Simulation settings updated.", "success")
    return redirect(url_for("admin.dashboard"))
