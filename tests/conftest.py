"""Shared pytest fixtures: an isolated app with a temporary database per test."""

import os
import sys

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from smartbrew import create_app  # noqa: E402
from smartbrew.db import get_db  # noqa: E402


@pytest.fixture
def app(tmp_path):
    """Create a fresh, seeded app whose database and outbox live in a temp folder.

    Inputs:  tmp_path – pytest temporary directory.
    Returns: flask.Flask application (yielded).
    """
    app = create_app({
        "TESTING": True,
        "DATABASE": str(tmp_path / "test.sqlite"),
        "OUTBOX": str(tmp_path / "outbox"),
        "SECRET_KEY": "test",
    })
    with app.app_context():
        db = get_db()
        db.execute("UPDATE settings SET value = '9' WHERE key = 'time_override'")
        db.commit()
    yield app


@pytest.fixture
def client(app):
    """Return a test client for the app.

    Inputs:  app – fixture above.
    Returns: flask.testing.FlaskClient.
    """
    return app.test_client()


def login(client, username="alice", password="password123"):
    """Log a user in through the real login form.

    Inputs:  client – test client; username, password – credentials.
    Returns: the response of the POST request.
    """
    return client.post("/login", data={"login": username, "password": password})


def admin_login(client, pin="4321"):
    """Enter administrative mode with the technician PIN.

    Inputs:  client – test client; pin – technician PIN.
    Returns: the response of the POST request.
    """
    return client.post("/admin/login", data={"method": "pin", "secret": pin})


def drink_id(app, name):
    """Look up a drink id by name.

    Inputs:  app – Flask app; name – drink name.
    Returns: int id.
    """
    with app.app_context():
        return get_db().execute("SELECT id FROM drinks WHERE name = ?", (name,)).fetchone()["id"]


def query(app, sql, args=()):
    """Run a read-only SQL query inside the app context.

    Inputs:  app – Flask app; sql – SQL string; args – parameters.
    Returns: list of sqlite Rows.
    """
    with app.app_context():
        return get_db().execute(sql, args).fetchall()


def execute(app, sql, args=()):
    """Run a write SQL statement inside the app context and commit.

    Inputs:  app – Flask app; sql – SQL string; args – parameters.
    Returns: None.
    """
    with app.app_context():
        db = get_db()
        db.execute(sql, args)
        db.commit()
