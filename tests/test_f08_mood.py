"""F8 – Camera mood detection (in memory only) and tailored suggestions; optional NL assistant."""

import base64
import os

from conftest import query

SAMPLES = os.path.join(os.path.dirname(__file__), "..", "samples")


def _data_url(name):
    """Encode a sample image as a browser data URL.

    Inputs:  name – sample file stem (tired | happy | stressed).
    Returns: str data URL.
    """
    with open(os.path.join(SAMPLES, f"{name}.png"), "rb") as fh:
        return "data:image/png;base64," + base64.b64encode(fh.read()).decode()


def _snapshot(folder):
    """List all files below a folder (to detect unexpected writes).

    Inputs:  folder – path.
    Returns: set of relative file paths.
    """
    return {os.path.relpath(os.path.join(d, f), folder)
            for d, _, files in os.walk(folder) for f in files}


def test_consent_is_required(client):
    """Camera analysis is refused without explicit consent.

    Inputs:  pytest fixtures (client).
    Returns: None; fails through assert if the behaviour is wrong.
    """
    r = client.post("/api/mood", json={"image": _data_url("tired")})
    assert r.status_code == 400 and "consent" in r.json["error"]


def test_tired_face_gets_extra_shot(client):
    """A tired face yields a double espresso with an extra shot.

    Inputs:  pytest fixtures (client).
    Returns: None; fails through assert if the behaviour is wrong.
    """
    r = client.post("/api/mood", json={"consent": True, "image": _data_url("tired")}).json
    assert r["mood"] == "tired" and r["source"] == "camera"
    assert r["suggestion"]["drink"] == "Double Espresso"
    assert r["suggestion"]["options"]["extra_shot"] is True


def test_happy_and_stressed_faces(client):
    """Happy and stressed sample faces are classified as such.

    Inputs:  pytest fixtures (client).
    Returns: None; fails through assert if the behaviour is wrong.
    """
    assert client.post("/api/mood", json={"consent": True, "image": _data_url("happy")}).json["mood"] == "happy"
    stressed = client.post("/api/mood", json={"consent": True, "image": _data_url("stressed")}).json
    assert stressed["mood"] == "stressed" and stressed["suggestion"]["drink"] == "Chai Latte"


def test_image_is_never_stored(client, app, tmp_path):
    """No file, DB row or log entry contains the image (NFR-01).

    Inputs:  pytest fixtures (client, app, tmp_path).
    Returns: None; fails through assert if the behaviour is wrong.
    """
    before = _snapshot(tmp_path)
    db_size = os.path.getsize(app.config["DATABASE"])
    image = _data_url("happy")
    client.post("/api/mood", json={"consent": True, "image": image})
    after = _snapshot(tmp_path)
    assert after - before <= {"test.sqlite-journal"}  # no new files besides SQLite's own journal
    assert os.path.getsize(app.config["DATABASE"]) - db_size < 8192  # one small log row at most
    events = " ".join(r["message"] for r in query(app, "SELECT message FROM events"))
    assert "base64" not in events and image[30:60] not in events


def test_mood_reorders_menu(client):
    """After a 'tired' estimate, caffeine-heavy drinks lead the menu.

    Inputs:  pytest fixtures (client).
    Returns: None; fails through assert if the behaviour is wrong.
    """
    client.post("/api/mood", json={"mood": "tired"})
    page = client.get("/").data.decode()
    assert page.index('data-drink="Double Espresso"') < page.index('data-drink="Hot Chocolate"')
    assert "You look tired" in page


def test_invalid_image_rejected(client):
    """Garbage input is rejected cleanly.

    Inputs:  pytest fixtures (client).
    Returns: None; fails through assert if the behaviour is wrong.
    """
    r = client.post("/api/mood", json={"consent": True, "image": "data:image/png;base64,AAAA"})
    assert r.status_code == 400


def test_assistant_translates_free_text(client):
    """'Sweet with a kick, low on dairy' becomes explicit machine parameters.

    Inputs:  pytest fixtures (client).
    Returns: None; fails through assert if the behaviour is wrong.
    """
    r = client.post("/api/assistant",
                    json={"text": "Give me something sweet with a kick, but low on dairy"}).json
    assert r["drink"] == "Americano"
    assert r["options"]["milk"] == "oat" and r["options"]["syrup"] == 2
    assert r["options"]["strength"] == 5 and r["options"]["extra_shot"] is True
    r = client.post("/api/assistant", json={"text": "large iced coffee, no milk"}).json
    assert r["drink"] == "Iced Americano" and r["options"]["size"] == "L"
