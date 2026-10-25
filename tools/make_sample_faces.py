"""Generate synthetic sample images for demonstrating the mood feature without a webcam.

The images are simple drawn faces whose lighting and colour match the
heuristic classifier in ``smartbrew/mood.py``: a dim face (tired), a bright,
colourful face (happy), and a harsh, desaturated high-contrast face (stressed).

Usage:  python tools/make_sample_faces.py   -> writes samples/*.png
"""

import os

from PIL import Image, ImageDraw

OUT = os.path.join(os.path.dirname(__file__), "..", "samples")


def face(bg, skin, feature, mouth, size=(320, 240), stripes=False):
    """Draw one cartoon face.

    Inputs:  bg, skin, feature – RGB tuples for background, face and eyes/mouth;
             mouth – "smile" | "flat" | "frown"; size – image size;
             stripes – add harsh black/white stripes (raises contrast).
    Returns: PIL.Image.Image.
    """
    img = Image.new("RGB", size, bg)
    d = ImageDraw.Draw(img)
    if stripes:
        for x in range(0, size[0], 24):
            d.rectangle([x, 0, x + 11, size[1]], fill=(15, 15, 15))
    cx, cy = size[0] // 2, size[1] // 2
    d.ellipse([cx - 80, cy - 95, cx + 80, cy + 95], fill=skin)
    d.ellipse([cx - 45, cy - 35, cx - 20, cy - 15], fill=feature)
    d.ellipse([cx + 20, cy - 35, cx + 45, cy - 15], fill=feature)
    if mouth == "smile":
        d.arc([cx - 45, cy, cx + 45, cy + 55], 20, 160, fill=feature, width=6)
    elif mouth == "frown":
        d.arc([cx - 45, cy + 30, cx + 45, cy + 85], 200, 340, fill=feature, width=6)
    else:
        d.line([cx - 35, cy + 45, cx + 35, cy + 45], fill=feature, width=6)
    return img


def main():
    """Write the three sample images to the samples/ folder.

    Inputs:  none.
    Returns: None.
    """
    os.makedirs(OUT, exist_ok=True)
    face((25, 25, 35), (70, 55, 50), (20, 20, 20), "flat").save(os.path.join(OUT, "tired.png"))
    face((255, 210, 80), (255, 190, 140), (200, 40, 40), "smile").save(os.path.join(OUT, "happy.png"))
    face((235, 235, 235), (150, 150, 150), (10, 10, 10), "frown", stripes=True) \
        .save(os.path.join(OUT, "stressed.png"))
    print("Sample faces written to", os.path.abspath(OUT))


if __name__ == "__main__":
    main()
