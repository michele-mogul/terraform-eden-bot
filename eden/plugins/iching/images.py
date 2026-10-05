"""The hexagram as a picture: drawn lines render the same on every phone, unlike text art."""

import textwrap
from io import BytesIO
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from eden.plugins.iching.oracle import Reading

FONT = Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf")
FONT_BOLD = Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf")
PAPER, INK, RED, GREY = (246, 239, 222), (43, 35, 64), (176, 48, 48), (150, 140, 160)
BAR_W, BAR_H, GAP, YIN_GAP = 300, 34, 24, 56   # one line of a hexagram
MARK_W = 70                                     # room for ○ / ✕ right of the primary hexagram
ARROW_W = 120
PAD, TITLE_H = 48, 120


def _font(size: int, bold: bool = False) -> ImageFont.ImageFont:
    path = FONT_BOLD if bold else FONT
    return ImageFont.truetype(str(path), size) if path.exists() else ImageFont.load_default(size=size)


def _title(draw: ImageDraw.ImageDraw, x: int, h: dict) -> None:
    draw.text((x, PAD), f"{h['number']} · {h['wilhelm']}", font=_font(30, True), fill=INK)
    for i, line in enumerate(textwrap.wrap(h["name"], 22)[:2]):
        draw.text((x, PAD + 40 + i * 32), line, font=_font(26), fill=INK)


def _hexagram(draw: ImageDraw.ImageDraw, x: int, lines: list[int], values: tuple[int, ...] = ()) -> None:
    """Lines bottom to top; with values, the moving ones are marked and numbered on the left."""
    top = PAD + TITLE_H
    for i in range(6):
        y = top + (5 - i) * (BAR_H + GAP)
        if lines[i]:
            draw.rectangle((x, y, x + BAR_W, y + BAR_H), fill=INK)
        else:
            half = (BAR_W - YIN_GAP) // 2
            draw.rectangle((x, y, x + half, y + BAR_H), fill=INK)
            draw.rectangle((x + BAR_W - half, y, x + BAR_W, y + BAR_H), fill=INK)
        if values:
            draw.text((x - 34, y + 2), str(i + 1), font=_font(24), fill=GREY)
            cx, cy, r = x + BAR_W + 36, y + BAR_H // 2, 14
            if values[i] == 9:      # old yang
                draw.ellipse((cx - r, cy - r, cx + r, cy + r), outline=RED, width=5)
            elif values[i] == 6:    # old yin
                draw.line((cx - r, cy - r, cx + r, cy + r), fill=RED, width=5)
                draw.line((cx - r, cy + r, cx + r, cy - r), fill=RED, width=5)


def figure(r: Reading) -> bytes:
    width = PAD + 34 + BAR_W + MARK_W + PAD
    if r.relating:
        width += ARROW_W + BAR_W
    height = PAD + TITLE_H + 6 * BAR_H + 5 * GAP + PAD
    im = Image.new("RGB", (width, height), PAPER)
    draw = ImageDraw.Draw(im)
    x = PAD + 34
    _title(draw, x, r.primary)
    _hexagram(draw, x, r.primary["lines"], r.values)
    if r.relating:
        ax = x + BAR_W + MARK_W
        ay = PAD + TITLE_H + 3 * (BAR_H + GAP) - GAP // 2
        draw.line((ax + 10, ay, ax + ARROW_W - 24, ay), fill=INK, width=5)
        draw.polygon([(ax + ARROW_W - 10, ay), (ax + ARROW_W - 30, ay - 14), (ax + ARROW_W - 30, ay + 14)], fill=INK)
        rx = ax + ARROW_W
        _title(draw, rx, r.relating)
        _hexagram(draw, rx, r.relating["lines"])
    buf = BytesIO()
    im.save(buf, "PNG", optimize=True)
    return buf.getvalue()
