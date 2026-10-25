"""F9 – Secure admin mode, refills/reset, bins; F10 – real-time errors and event log."""

from conftest import admin_login, drink_id, execute, query


def test_admin_endpoints_require_admin_mode(client):
    """Without admin mode, the dashboard redirects and the APIs return 403.

    Inputs:  pytest fixtures (client).
    Returns: None; fails through assert if the behaviour is wrong.
    """
    assert client.get("/admin/").status_code == 302
    assert client.get("/admin/api/status").status_code == 403
    assert client.get("/admin/api/events").status_code == 403
    assert client.post("/admin/refill", data={"ingredient": "milk_whole", "reset": "1"}).status_code == 302


def test_wrong_pin_denied_and_logged(client, app):
    """A wrong PIN is denied and appears in the event log.

    Inputs:  pytest fixtures (client, app).
    Returns: None; fails through assert if the behaviour is wrong.
    """
    assert admin_login(client, "0000").status_code == 401
    assert query(app, "SELECT COUNT(*) FROM events WHERE message LIKE 'Admin access denied%'")[0][0] == 1


def test_all_three_access_methods(client):
    """PIN, NFC master card and physical key all open admin mode.

    Inputs:  pytest fixtures (client).
    Returns: None; fails through assert if the behaviour is wrong.
    """
    for method, secret in (("pin", "4321"), ("master_card", "master-0001"), ("key", "KEY-SB-01")):
        client.post("/admin/logout")
        r = client.post("/admin/login", data={"method": method, "secret": secret})
        assert r.status_code == 302 and r.location.endswith("/admin/")


def test_refill_reset_reenables_drinks(client, app):
    """Resetting milk to max makes milk drinks available again and is logged.

    Inputs:  pytest fixtures (client, app).
    Returns: None; fails through assert if the behaviour is wrong.
    """
    execute(app, "UPDATE ingredients SET level = 0 WHERE name LIKE 'milk_%'")
    assert 'data-drink="Latte" data-available="0"' in client.get("/").data.decode()
    admin_login(client)
    client.post("/admin/refill", data={"ingredient": "milk_whole", "reset": "1"})
    assert query(app, "SELECT level FROM ingredients WHERE name='milk_whole'")[0][0] == 2000
    assert 'data-drink="Latte" data-available="1"' in client.get("/").data.decode()
    assert query(app, "SELECT actor FROM events WHERE type='refill'")[0][0] == "technician (PIN)"


def test_refill_add_quantity_capped(client, app):
    """Adding a quantity never exceeds capacity; low-stock warnings auto-clear.

    Inputs:  pytest fixtures (client, app).
    Returns: None; fails through assert if the behaviour is wrong.
    """
    admin_login(client)
    client.post("/admin/level", data={"ingredient": "coffee_beans", "level": "100"})
    assert any("Coffee beans" in f["message"] for f in client.get("/admin/api/status").json["faults"])
    client.post("/admin/refill", data={"ingredient": "coffee_beans", "quantity": "5000"})
    assert query(app, "SELECT level FROM ingredients WHERE name='coffee_beans'")[0][0] == 1000
    assert not any("Coffee beans" in f["message"] for f in client.get("/admin/api/status").json["faults"])


def test_bins_warning_halt_and_empty(client, app):
    """≥80 % warns, 100 % halts ordering, 'emptied' resumes.

    Inputs:  pytest fixtures (client, app).
    Returns: None; fails through assert if the behaviour is wrong.
    """
    admin_login(client)
    client.post("/admin/bins/grounds_bin/simulate", data={"pct": "85"})
    status = client.get("/admin/api/status").json
    assert status["halted"] is None and any(f["code"] == "BIN_WARNING" for f in status["faults"])
    client.post("/admin/bins/grounds_bin/simulate", data={"pct": "100"})
    assert "full" in client.get("/admin/api/status").json["halted"]
    assert b"Operations halted" in client.get("/").data
    r = client.post("/order", data={"drink_id": drink_id(app, "Black Tea"), "options": "{}",
                                    "payment_method": "card"}, follow_redirects=True)
    assert b"cannot be prepared" in r.data
    client.post("/admin/bins/grounds_bin/empty")
    status = client.get("/admin/api/status").json
    assert status["halted"] is None and not any(f["code"].startswith("BIN") for f in status["faults"])


def test_brewing_fills_bins_until_halt(client, app):
    """Real brewing raises the bin level and eventually halts the machine.

    Inputs:  pytest fixtures (client, app).
    Returns: None; fails through assert if the behaviour is wrong.
    """
    execute(app, "UPDATE bins SET level = 395 WHERE name = 'grounds_bin'")
    client.post("/order", data={"drink_id": drink_id(app, "Espresso"), "options": "{}",
                                "payment_method": "card"})
    assert b"Operations halted" in client.get("/").data


def test_fault_shown_live_blocks_coffee_and_resolves(client, app):
    """'Grinder Jammed' appears on the dashboard, blocks coffee drinks, and resolution is logged.

    Inputs:  pytest fixtures (client, app).
    Returns: None; fails through assert if the behaviour is wrong.
    """
    admin_login(client)
    client.post("/admin/faults", data={"code": "GRINDER_JAMMED"})
    faults = client.get("/admin/api/status").json["faults"]
    assert faults[0]["message"] == "Grinder Jammed" and faults[0]["severity"] == "critical"
    page = client.get("/").data.decode()
    assert 'data-drink="Espresso" data-available="0"' in page
    assert 'data-drink="Black Tea" data-available="1"' in page
    client.post(f"/admin/faults/{faults[0]['id']}/resolve")
    assert client.get("/admin/api/status").json["faults"] == []
    assert query(app, "SELECT COUNT(*) FROM events WHERE message = 'Resolved: Grinder Jammed'")[0][0] == 1


def test_event_log_filter_and_export(client):
    """The event log can be filtered and exported as JSON for remote diagnostics.

    Inputs:  pytest fixtures (client).
    Returns: None; fails through assert if the behaviour is wrong.
    """
    admin_login(client)
    client.post("/admin/faults", data={"code": "WATER_HEATER_FAULT"})
    crit = client.get("/admin/api/events?severity=critical").json
    assert crit and all(e["severity"] == "critical" for e in crit)
    dl = client.get("/admin/api/events?type=fault&download=1")
    assert "attachment" in dl.headers["Content-Disposition"]
    assert all(e["type"] == "fault" for e in dl.json)
    assert b"Water Heater Fault" in client.get("/admin/events?type=fault").data
