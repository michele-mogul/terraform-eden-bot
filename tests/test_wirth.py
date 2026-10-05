import asyncio
import random
from datetime import date
from html.parser import HTMLParser
from io import BytesIO
from types import SimpleNamespace
from unittest.mock import AsyncMock

from PIL import Image

from eden.plugins import wirth
from eden.plugins.wirth.deck import (by_number, card_of_the_day, card_text, deck, fits_caption,
                                     plain_length, spread_caption, synthesis, wirth_spread)
from eden.plugins.wirth.images import cross


class _Tags(HTMLParser):
    ALLOWED = {"b", "i"}

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


def test_deck_is_wirths_22_arcana_with_pictures_and_texts():
    cards = deck()
    assert [c.number for c in cards] == list(range(22))
    assert by_number(8).name == "La Giustizia" and by_number(11).name == "La Forza"   # Wirth's order
    assert by_number(16).name == "La Casa di Dio"                                       # La Maison-Dieu
    assert by_number(0).value == 22 and by_number(21).value == 21
    for c in cards:
        assert c.path.is_file() and len(c.paragraphs) >= 2 and all(p.strip() for p in c.paragraphs)


def test_synthesis_follows_wirth_examples():
    assert synthesis([1, 15, 8, 22]).number == 10           # 46 → 4 + 6
    assert synthesis([5, 5, 6, 6]).number == 0              # 22 is the Fool
    assert synthesis([5, 6, 6, 6]).number == 5              # 23 → 2 + 3 (Wirth's example)
    assert synthesis([22, 22, 7, 6]).number == 12           # 57 → 5 + 7 (Wirth's example)
    assert synthesis([22, 22, 22, 22]).number == 16         # the largest sum, 88


def test_texts_are_valid_html_and_fit_a_message():
    for c in deck():
        text = card_text(c, "🌅 " + "N" * 64 + " · ")
        assert _valid(text) and plain_length(text) < 4096
    # most cards fit a photo caption; the longest go below the picture
    assert sum(fits_caption(card_text(c)) for c in deck()) >= 14


def test_spread_caption_lists_the_five_places():
    cards = wirth_spread(random.Random(1))
    caption = spread_caption("<b>amore?</b> & lavoro", cards)
    assert _valid(caption) and "&lt;b&gt;amore?" in caption
    assert caption.count("\n") == 6 and "Sintesi" in caption and "Giudice" in caption


def test_card_of_the_day_is_stable_per_person_and_day():
    d = date(2026, 10, 5)
    assert card_of_the_day(1, d) == card_of_the_day(1, d)
    assert len({card_of_the_day(1, date(2026, 10, n)) for n in range(1, 29)}) > 5


def test_cross_image():
    im = Image.open(BytesIO(cross(wirth_spread(random.Random(2)))))
    assert im.size == (3 * 300 + 4 * 28, 3 * 508 + 4 * 28)


def _query(data, markup, user=42):
    message = SimpleNamespace(reply_markup=markup)
    query = SimpleNamespace(data=data, message=message, answer=AsyncMock(),
                            from_user=SimpleNamespace(id=user), edit_message_text=AsyncMock())
    return SimpleNamespace(callback_query=query), query


def test_places_change_one_message_and_only_for_the_asker():
    numbers = [1, 15, 8, 0]                                   # the Fool is card 0, worth 22
    markup = wirth.keyboard(numbers, 42, 0)
    buttons = [b for row in markup.inline_keyboard for b in row]
    assert len(buttons) == 5 and buttons[0].text.startswith("▸ ")
    assert all(len(b.callback_data.encode()) <= 64 for b in buttons)
    assert wirth.place_text(wirth_spread(random.Random(1)), 0).startswith("<b>Affermazione · Pro</b>")

    update, query = _query(buttons[4].callback_data, markup)  # Sintesi: 46 → 10
    asyncio.run(wirth.on_button(update, None))
    text = query.edit_message_text.call_args.args[0]
    assert text.startswith("<b>Sintesi</b>") and "La Ruota della Fortuna" in text
    new = query.edit_message_text.call_args.kwargs["reply_markup"]
    assert [b.text.startswith("▸ ") for row in new.inline_keyboard for b in row] == [False] * 4 + [True]

    update, query = _query(buttons[1].callback_data, markup, user=7)   # someone else
    asyncio.run(wirth.on_button(update, None))
    query.edit_message_text.assert_not_called()

    update, query = _query(buttons[0].callback_data, markup)  # already shown
    asyncio.run(wirth.on_button(update, None))
    query.edit_message_text.assert_not_called()
