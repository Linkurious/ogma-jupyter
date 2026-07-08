"""Generate a lightweight *placeholder* demo animation for the README.

This is NOT a recording of the real widget — it is a stylized, illustrative
graph animation so the README renders a finished-looking hero image before a
real screencast is available. Replace docs/assets/ogma-jupyter-demo.gif with an
actual recording of the widget (see docs/RECORDING.md) when you have one.

Run:  .venv/bin/python scripts/gen-demo-placeholder.py
Deps: Pillow (dev-only, not a package dependency).
"""

from __future__ import annotations

import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

OUT = Path(__file__).resolve().parents[1] / "docs" / "assets" / "ogma-jupyter-demo.gif"

# Output geometry. We render at 2x (SS) and downscale with LANCZOS for smooth,
# anti-aliased edges since Pillow's drawing is otherwise aliased.
W, H = 760, 380
SS = 2
FRAMES = 60
BG = (17, 21, 28)
EDGE = (86, 96, 112)

# Categorical palette mirrors the README's rules.map() example.
PALETTE = {
    "engineer": (78, 121, 167),
    "manager": (242, 142, 43),
    "designer": (89, 161, 79),
}

# A small graph: (id, base_x, base_y, role). Positions are normalized [-1, 1].
NODES = [
    ("alice", 0.00, -0.55, "engineer"),
    ("bob", -0.62, -0.05, "manager"),
    ("carol", 0.60, -0.10, "designer"),
    ("dave", -0.40, 0.55, "engineer"),
    ("erin", 0.38, 0.58, "designer"),
    ("frank", 0.02, 0.10, "manager"),
]
EDGES = [
    ("alice", "bob"), ("alice", "carol"), ("bob", "frank"),
    ("carol", "frank"), ("dave", "frank"), ("erin", "frank"),
    ("dave", "bob"), ("erin", "carol"),
]
IDX = {n[0]: i for i, n in enumerate(NODES)}


def _font(size: int):
    for name in ("Helvetica.ttc", "Arial.ttf", "DejaVuSans.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


def _positions(t: float):
    """Node pixel positions at animation phase t in [0, 1), looping smoothly."""
    cx, cy = W * SS / 2, H * SS / 2 + 14 * SS
    scale = min(W, H) * SS * 0.42
    phase = 2 * math.pi * t
    pts = []
    for i, (_id, bx, by, _role) in enumerate(NODES):
        # Gentle, seamless orbital drift so the graph looks "alive".
        wobble = 0.05
        dx = wobble * math.cos(phase + i * 1.7)
        dy = wobble * math.sin(phase + i * 2.3)
        pts.append((cx + (bx + dx) * scale, cy + (by + dy) * scale))
    return pts


def _frame(t: float) -> Image.Image:
    img = Image.new("RGB", (W * SS, H * SS), BG)
    d = ImageDraw.Draw(img)
    pos = _positions(t)

    for a, b in EDGES:
        x1, y1 = pos[IDX[a]]
        x2, y2 = pos[IDX[b]]
        d.line((x1, y1, x2, y2), fill=EDGE, width=2 * SS)

    r = 20 * SS
    label_font = _font(15 * SS)
    for (nid, _bx, _by, role), (x, y) in zip(NODES, pos):
        color = PALETTE[role]
        d.ellipse((x - r, y - r, x + r, y + r), fill=color, outline=BG, width=3 * SS)
        tb = d.textbbox((0, 0), nid, font=label_font)
        d.text((x - (tb[2] - tb[0]) / 2, y + r + 3 * SS), nid, font=label_font, fill=(200, 208, 218))

    title_font = _font(26 * SS)
    sub_font = _font(14 * SS)
    d.text((28 * SS, 22 * SS), "ogma-jupyter", font=title_font, fill=(236, 240, 245))
    d.text((28 * SS, 56 * SS), "interactive graph visualization for Jupyter",
            font=sub_font, fill=(140, 150, 162))

    return img.resize((W, H), Image.LANCZOS)


def main() -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    frames = [_frame(i / FRAMES) for i in range(FRAMES)]
    frames[0].save(
        OUT, save_all=True, append_images=frames[1:], duration=70, loop=0, optimize=True
    )
    print(f"wrote {OUT} ({OUT.stat().st_size // 1024} KB, {FRAMES} frames)")


if __name__ == "__main__":
    main()
