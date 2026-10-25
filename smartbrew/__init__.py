"""SmartBrew AI – Flask application factory."""

import os
import time

from flask import Flask, flash, g, redirect, session, url_for

from . import db as database


def create_app(test_config=None):
    """Create and configure the SmartBrew Flask application.

    Inputs:  test_config – optional dict that overrides the configuration
             (used by the test-suite, e.g. a temporary DATABASE path).
    Returns: a configured ``flask.Flask`` instance with all blueprints
             registered and the database initialised and seeded.
    """
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_mapping(
        SECRET_KEY=os.environ.get("SMARTBREW_SECRET", "dev-only-change-me"),
        DATABASE=os.path.join(app.instance_path, "smartbrew.sqlite"),
        OUTBOX=os.path.join(app.instance_path, "outbox"),
        INACTIVITY_SECONDS=int(os.environ.get("SMARTBREW_INACTIVITY", "60")),
        ADMIN_TIMEOUT_SECONDS=600,
        MAX_FAILED_LOGINS=5,
        LOCKOUT_MINUTES=5,
        WEATHER_LIVE=os.environ.get("SMARTBREW_WEATHER_LIVE") == "1",
        WEATHER_LAT=float(os.environ.get("SMARTBREW_LAT", "59.33")),
        WEATHER_LON=float(os.environ.get("SMARTBREW_LON", "18.07")),
        SMTP_HOST=os.environ.get("SMARTBREW_SMTP_HOST"),
        SMTP_PORT=int(os.environ.get("SMARTBREW_SMTP_PORT", "25")),
        MAIL_FROM=os.environ.get("SMARTBREW_MAIL_FROM", "receipts@smartbrew.local"),
        MAX_CONTENT_LENGTH=8 * 1024 * 1024,
    )
    if test_config:
        app.config.update(test_config)
    os.makedirs(app.instance_path, exist_ok=True)
    os.makedirs(app.config["OUTBOX"], exist_ok=True)

    app.teardown_appcontext(database.close_db)
    with app.app_context():
        database.init_db()

    from . import admin, auth, orders, shop
    app.register_blueprint(auth.bp)
    app.register_blueprint(shop.bp)
    app.register_blueprint(orders.bp)
    app.register_blueprint(admin.bp)

    @app.before_request
    def load_session_user():
        """Load the logged-in user into ``g.user`` and enforce the inactivity timeout.

        Inputs:  none (reads the Flask session).
        Returns: None, or a redirect to the menu when the session expired (FR-05).
        """
        g.user = None
        uid = session.get("user_id")
        if uid is None:
            return None
        last = session.get("last_active", 0)
        if time.time() - last > app.config["INACTIVITY_SECONDS"]:
            session.pop("user_id", None)
            session.pop("mood", None)
            flash("You were logged out after a period of inactivity.", "info")
            return redirect(url_for("shop.menu"))
        session["last_active"] = time.time()
        g.user = database.get_db().execute(
            "SELECT * FROM users WHERE id = ?", (uid,)).fetchone()
        return None

    @app.context_processor
    def inject_globals():
        """Expose machine-wide values to every template.

        Inputs:  none.
        Returns: dict with ``online`` (bool), ``is_admin`` (bool) and
                 ``inactivity_seconds`` (int).
        """
        return {
            "online": database.get_setting("network_online", "1") == "1",
            "is_admin": bool(session.get("admin")),
            "inactivity_seconds": app.config["INACTIVITY_SECONDS"],
        }

    return app
