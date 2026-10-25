"""In-memory mood estimation from a camera frame (FR-19, NFR-01).

Privacy rule from the System Description: the image is decoded and analysed
entirely in memory and discarded right away. Nothing in this module writes
to disk, the database, or the network.

Prototype note: a real machine would run an on-device facial-expression
model here (e.g. a small CNN in ONNX Runtime). This prototype uses a
lightweight, explainable image heuristic (brightness, contrast, colour
saturation of the central face region) behind the same interface
``estimate_mood(bytes) -> dict``, so the model can be swapped without
touching the rest of the system.
"""

import base64
import binascii
import io

from PIL import Image, ImageStat, UnidentifiedImageError

MOODS = ("tired", "happy", "stressed", "neutral")

# mood -> (drink name, option overrides, explanation)
MOOD_RECIPES = {
    "tired": ("Double Espresso", {"strength": 5, "extra_shot": True},
              "You look tired: double espresso, strength 5, with an extra shot."),
    "stressed": ("Chai Latte", {"temperature": "warm", "syrup": 1},
                 "You look stressed: a warm, gently sweet chai latte to slow down."),
    "happy": ("Iced Latte", {"syrup": 1},
              "You look happy: celebrate with an iced latte and a shot of vanilla."),
    "neutral": ("Cappuccino", {},
                "A balanced classic: cappuccino."),
}

MAX_IMAGE_BYTES = 5 * 1024 * 1024


def decode_data_url(data_url):
    """Decode a browser ``data:image/...;base64,...`` string into raw bytes.

    Inputs:  data_url – str from ``canvas.toDataURL()`` or FileReader.
    Returns: bytes of the encoded image.
    Raises:  ValueError if the string is not a valid base64 image data URL or
             is larger than 5 MB.
    """
    if not isinstance(data_url, str) or not data_url.startswith("data:image/"):
        raise ValueError("Expected an image data URL")
    try:
        raw = base64.b64decode(data_url.split(",", 1)[1], validate=True)
    except (IndexError, binascii.Error) as exc:
        raise ValueError("Invalid base64 image") from exc
    if len(raw) > MAX_IMAGE_BYTES:
        raise ValueError("Image too large")
    return raw


def image_features(image_bytes):
    """Extract simple appearance features from the central region of an image.

    Inputs:  image_bytes – encoded image (JPEG/PNG) as bytes.
    Returns: dict with brightness (0–255), contrast (std-dev 0–128) and
             saturation (0–255).
    Raises:  ValueError if the bytes are not a readable image.
    """
    try:
        with Image.open(io.BytesIO(image_bytes)) as img:
            img = img.convert("RGB")
            w, h = img.size
            face = img.crop((int(w * 0.2), int(h * 0.15), int(w * 0.8), int(h * 0.85)))
            face.thumbnail((96, 96))
            grey = ImageStat.Stat(face.convert("L"))
            sat = ImageStat.Stat(face.convert("HSV").split()[1])
            return {"brightness": round(grey.mean[0], 1),
                    "contrast": round(grey.stddev[0], 1),
                    "saturation": round(sat.mean[0], 1)}
    except (UnidentifiedImageError, OSError) as exc:
        raise ValueError("Unreadable image") from exc


def classify(features):
    """Map image features to one of the supported moods (heuristic classifier).

    Inputs:  features – dict from ``image_features``.
    Returns: tuple (mood: str, confidence: float 0–1).
    """
    b, c, s = features["brightness"], features["contrast"], features["saturation"]
    if b < 85:
        return "tired", round(min(1.0, (85 - b) / 60 + 0.5), 2)
    if c > 60 and s < 70:
        return "stressed", round(min(1.0, (c - 60) / 40 + 0.5), 2)
    if b > 135 and s > 80:
        return "happy", round(min(1.0, (s - 80) / 100 + 0.5), 2)
    return "neutral", 0.5


def estimate_mood(image_bytes):
    """Estimate the user's mood from one frame, entirely in memory.

    The caller must drop its reference to ``image_bytes`` afterwards. This
    function keeps no copy.

    Inputs:  image_bytes – encoded image bytes.
    Returns: dict {"mood": str, "confidence": float, "features": dict}.
    Raises:  ValueError for unreadable input.
    """
    features = image_features(image_bytes)
    mood, confidence = classify(features)
    return {"mood": mood, "confidence": confidence, "features": features}
