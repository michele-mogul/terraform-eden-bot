import html
import random
import re
from datetime import date
from html.parser import HTMLParser

from PIL import Image

from eden.plugins.wirth.deck import (Draw, by_number, card_caption, card_of_the_day, deck, draw,
                                     spread_caption, spread_text, synthesis, wirth_spread)
from eden.plugins.wirth.images import card_photo, cross


class _Tags(HTMLParser):
    ALLOWED = {"b", "i", "code", "blockquote"}

    def __init__(self):
        super().__init__()
        self.stack = []

    def handle_starttag(self, tag, attrs):
        assert tag in self.ALLOWED, tag
        self.stack.append(tag)

    def handle_endtag(self, tag):
        assert self.stack.pop() == tag


def _valid(text):
    t = _Tags()
    t.feed(text)
    return t.stack == []


def test_deck_is_wirths_22_arcana_with_pictures_and_meanings():
    cards = deck()
    assert [c.number for c in cards] == list(range(22))
    assert by_number(8).name == "La Giustizia" and by_number(11).name == "La Forza"   # Wirth's order
    assert by_number(0).value == 22 and by_number(21).value == 21
    for c in cards:
        assert c.path.is_file() and c.essence and c.favorable and c.unfavorable


def test_synthesis_follows_wirth_examples():
    assert synthesis([1, 15, 8, 22])[0].number == 10           # 46 → 4 + 6
    assert synthesis([5, 5, 6, 6])[0].number == 0              # 22 is the Fool
    assert synthesis([5, 6, 6, 6])[0].number == 5              # 23 → 2 + 3 (Wirth's example)
    assert synthesis([22, 22, 7, 6])[0].number == 12           # 57 → 5 + 7 (Wirth's example)
    assert synthesis([1, 1, 1, 1])[0].number == 4
    assert synthesis([22, 22, 22, 22])[1].endswith("= 16")     # the largest sum


def test_captions_fit_telegram_photo_limit():
    head = "🌅 Arcano del giorno di " + "N" * 64 + " ·"
    for c in deck():
        for rev in (False, True):
            text = card_caption(Draw(c, rev), head)
            assert _valid(text)
            # Telegram counts the text without the tags: 1024 characters for a caption
            assert len(html.unescape(re.sub(r"<[^>]+>", "", text))) <= 1024


def test_spread_text_is_valid_and_fits_one_message():
    rng = random.Random(1)
    for q in ("<b>amore?</b> & lavoro", ""):
        for _ in range(300):
            s = wirth_spread(q, rng)
            assert len(s.cards) == 5
            assert _valid(spread_text(s)) and _valid(spread_caption(s))
            assert len(spread_text(s)) < 4096 and len(spread_caption(s)) < 1024
    worst = max((wirth_spread("x" * 200, rng) for _ in range(2000)), key=lambda s: len(spread_text(s)))
    assert len(spread_text(worst)) < 4096


def test_card_of_the_day_is_stable_per_person_and_day():
    d = date(2026, 10, 5)
    assert card_of_the_day(1, d) == card_of_the_day(1, d)
    assert len({card_of_the_day(1, date(2026, 10, n)) for n in range(1, 29)}) > 5
    assert isinstance(draw(random.Random(3)), Draw)


def test_pictures_are_jpegs_reversed_and_cross(tmp_path):
    c = by_number(13)
    upright, rev = card_photo(Draw(c, False)), card_photo(Draw(c, True))
    for i, data in enumerate((upright, rev)):
        (tmp_path / f"{i}.jpg").write_bytes(data)
    a = Image.open(tmp_path / "0.jpg").convert("L").resize((50, 84))
    b = Image.open(tmp_path / "1.jpg").convert("L").resize((50, 84))

    def diff(x, y):
        return sum(abs(p - q) for p, q in zip(x.tobytes(), y.tobytes())) / len(x.tobytes())
    assert diff(a, b.rotate(180)) < 3 < diff(a, b)      # the reversed card is the same, upside down
    (tmp_path / "x.jpg").write_bytes(cross(wirth_spread("", random.Random(2)).cards))
    assert Image.open(tmp_path / "x.jpg").size == (3 * 300 + 4 * 28, 3 * 508 + 4 * 28)
