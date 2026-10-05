"""Card pictures: Wirth's spread laid out as a cross."""

from io import BytesIO

from PIL import Image, ImageOps

from eden.plugins.wirth.deck import Card

W, H, GAP = 300, 508, 28           # card size in the cross (the scans are about 500 x 845)
BACKGROUND = (36, 30, 52)
GOLD = (212, 175, 55)
# Wirth's cross: 3 Discussion on top, 1 Affirmation left, 5 Synthesis centre, 2 Negation right,
# 4 Solution below (column, row) in drawing order
CROSS = ((0, 1), (2, 1), (1, 0), (1, 2), (1, 1))


def cross(cards: tuple[Card, ...]) -> bytes:
    canvas = Image.new("RGB", (3 * W + 4 * GAP, 3 * H + 4 * GAP), BACKGROUND)
    for i, (card, (col, row)) in enumerate(zip(cards, CROSS)):
        with Image.open(card.path) as im:
            im = im.convert("RGB").resize((W, H), Image.LANCZOS)
        if i == 4:   # the synthesis, framed in gold
            im = ImageOps.expand(im.resize((W - 12, H - 12), Image.LANCZOS), border=6, fill=GOLD)
        canvas.paste(im, (GAP + col * (W + GAP), GAP + row * (H + GAP)))
    buf = BytesIO()
    canvas.save(buf, "JPEG", quality=88)
    return buf.getvalue()
