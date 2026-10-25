"""F7 – Personalised recommendations (time, weather, history) and menu reordering."""

import re

from conftest import execute, login


def _order_of_menu(client):
    """Return the drink names in menu order.

    Inputs:  client – test client.
    Returns: list of drink names as shown on the "All" menu.
    """
    return re.findall(r'data-drink="([^"]+)" data-available="1"', client.get("/").data.decode())


def _set(app, **values):
    """Change simulation settings.

    Inputs:  app – Flask app; values – setting key/value pairs.
    Returns: None.
    """
    for k, v in values.items():
        execute(app, "UPDATE settings SET value = ? WHERE key = ?", (str(v), k))


def test_history_drives_ranking(client, app):
    """alice drinks lattes, so Latte is recommended first for her (morning, mild weather).

    Inputs:  pytest fixtures (client, app).
    Returns: None; fails through assert if the behaviour is wrong.
    """
    login(client)
    order = _order_of_menu(client)
    assert order[0] == "Latte"
    assert b"You often order Latte" in client.get("/").data


def test_cold_rainy_weather_promotes_warming_drinks(client, app):
    """For a guest on a cold, rainy afternoon, warm drinks beat iced ones.

    Inputs:  pytest fixtures (client, app).
    Returns: None; fails through assert if the behaviour is wrong.
    """
    _set(app, weather_temp=3, weather_condition="rainy", time_override=15)
    order = _order_of_menu(client)
    assert order.index("Hot Chocolate") < order.index("Iced Latte")
    assert order[-1].startswith("Iced") or order[-2].startswith("Iced")


def test_hot_weather_promotes_iced_drinks(client, app):
    """On a hot afternoon, iced drinks are highlighted at the top.

    Inputs:  pytest fixtures (client, app).
    Returns: None; fails through assert if the behaviour is wrong.
    """
    _set(app, weather_temp=30, weather_condition="sunny", time_override=14)
    order = _order_of_menu(client)
    assert set(order[:2]) == {"Iced Latte", "Iced Americano"}


def test_evening_reduces_caffeine(client, app):
    """In the evening, tea/chocolate rank above espresso.

    Inputs:  pytest fixtures (client, app).
    Returns: None; fails through assert if the behaviour is wrong.
    """
    _set(app, time_override=20)
    order = _order_of_menu(client)
    assert order.index("Black Tea") < order.index("Espresso")


def test_unavailable_drinks_never_highlighted(client, app):
    """Unavailable drinks go to the end and are not recommended.

    Inputs:  pytest fixtures (client, app).
    Returns: None; fails through assert if the behaviour is wrong.
    """
    _set(app, weather_temp=30, weather_condition="sunny", time_override=14)
    execute(app, "UPDATE ingredients SET level = 0 WHERE name = 'ice'")
    page = client.get("/").data.decode()
    assert "Iced Latte" not in _order_of_menu(client)
    assert re.search(r'recommended\s+disabled', page) is None
