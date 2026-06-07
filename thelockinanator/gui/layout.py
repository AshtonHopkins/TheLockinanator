"""Placement and loading of the silly background art.

Each :class:`ArtPiece` is positioned in fractional window coordinates so the
collage scales with the window, and sized to fit a fractional bounding box while
preserving aspect ratio. Missing files (e.g. a kitten you haven't drawn yet)
render as a clearly-labeled placeholder so the layout is complete from day one
and real PNGs drop in with no code changes.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageDraw, ImageTk

ASSETS_DIR = Path(__file__).resolve().parent.parent / "assets" / "images"


@dataclass(frozen=True)
class ArtPiece:
    key: str
    filename: str
    rel_x: float        # 0..1 position of the anchor within the window
    rel_y: float
    anchor: str         # tk anchor: nw, ne, sw, se, e, w, center, ...
    max_w_frac: float   # bounding box as a fraction of window size
    max_h_frac: float
    label: str          # shown if the file is missing


# Corner/edge decoration that frames the central control panel.
ART: tuple[ArtPiece, ...] = (
    ArtPiece("eagle", "Eagle.png", 0.00, 0.00, "nw", 0.30, 0.36, "EAGLE"),
    ArtPiece("mushroom", "Mushroom.png", 1.00, 0.00, "ne", 0.30, 0.34, "MUSHROOM"),
    ArtPiece("monster", "Monster.png", 1.00, 0.52, "e", 0.18, 0.70, "MONSTER"),
    ArtPiece("tank", "Tank.png", 0.00, 1.00, "sw", 0.34, 0.30, "TANK"),
    ArtPiece("kitten", "Kitten.png", 1.00, 1.00, "se", 0.20, 0.26, "KITTEN"),
)


@dataclass(frozen=True)
class PlacedArt:
    piece: ArtPiece
    x: int
    y: int
    image: ImageTk.PhotoImage
    is_placeholder: bool


def _placeholder(box_w: int, box_h: int, label: str) -> Image.Image:
    """A translucent dashed box labeled with the missing art's name."""
    img = Image.new("RGBA", (max(1, box_w), max(1, box_h)), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.rounded_rectangle(
        (2, 2, box_w - 3, box_h - 3), radius=12,
        outline=(120, 120, 130, 200), width=3, fill=(200, 200, 210, 60),
    )
    text = f"{label}\n(add {label.title()}.png)"
    # Default bitmap font; multiline centered.
    bbox = draw.multiline_textbbox((0, 0), text, align="center")
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    draw.multiline_text(
        ((box_w - tw) / 2, (box_h - th) / 2), text,
        fill=(80, 80, 90, 230), align="center",
    )
    return img


def load_art(width: int, height: int) -> list[PlacedArt]:
    """Load, size, and position every art piece for a ``width`` x ``height`` window."""
    placed: list[PlacedArt] = []
    for piece in ART:
        box_w = int(width * piece.max_w_frac)
        box_h = int(height * piece.max_h_frac)
        path = ASSETS_DIR / piece.filename
        is_placeholder = not path.exists()
        if is_placeholder:
            img = _placeholder(box_w, box_h, piece.label)
        else:
            img = Image.open(path).convert("RGBA")
            img.thumbnail((box_w, box_h), Image.LANCZOS)

        x, y = _anchor_to_xy(piece, width, height, img.width, img.height)
        placed.append(
            PlacedArt(piece, x, y, ImageTk.PhotoImage(img), is_placeholder)
        )
    return placed


def _anchor_to_xy(
    piece: ArtPiece, win_w: int, win_h: int, img_w: int, img_h: int
) -> tuple[int, int]:
    """Convert a fractional anchored position into a top-left (x, y) for canvas."""
    ax = piece.rel_x * win_w
    ay = piece.rel_y * win_h
    a = piece.anchor
    if "e" in a:
        x = ax - img_w
    elif "w" in a:
        x = ax
    else:
        x = ax - img_w / 2
    if "s" in a:
        y = ay - img_h
    elif "n" in a:
        y = ay
    else:
        y = ay - img_h / 2
    return int(x), int(y)
