import random
from collections import Counter
from datetime import datetime

import asyncio
from html.parser import HTMLParser
from types import SimpleNamespace
from unittest.mock import AsyncMock

from eden.plugins import iching
from eden.plugins.iching.images import figure
from eden.plugins.iching.oracle import (TRIGRAMS, by_lines, cast, cast_line, from_values,
                                        hexagram_text, hexagrams, trigrams)


def test_data_has_64_hexagrams_with_consistent_lines():
    hs = hexagrams()
    assert sorted(h["number"] for h in hs) == list(range(1, 65))
    assert len({tuple(h["lines"]) for h in hs}) == 64
    assert all(h["binary"] == "".join(map(str, reversed(h["lines"]))) for h in hs)
    assert all(len(h["lineTexts"]) == 6 and h["judgement"] and h["image"] and h["name"] for h in hs)
    assert [h["number"] for h in hs if h["allLines"]] == [1, 2]


def test_yarrow_line_values_and_probabilities():
    rng = random.Random(1)
    counts = Counter(cast_line(rng) for _ in range(40000))
    assert set(counts) <= {6, 7, 8, 9}
    # yarrow-stalk probabilities: 6 = 1/16, 7 = 5/16, 8 = 7/16, 9 = 3/16
    for value, p in {6: 1 / 16, 7: 5 / 16, 8: 7 / 16, 9: 3 / 16}.items():
        assert abs(counts[value] / 40000 - p) < 0.02


def test_same_question_and_second_give_the_same_reading():
    now = datetime(2026, 10, 5, 12, 0, 0)
    assert cast("domanda", now=now) == cast("domanda", now=now)


def test_relating_hexagram_flips_exactly_the_moving_lines():
    rng = random.Random(7)
    for _ in range(500):
        r = cast("x", rng=rng)
        if r.moving:
            flipped = [1 - l if i + 1 in r.moving else l for i, l in enumerate(r.primary["lines"])]
            assert r.relating == by_lines(flipped)
        else:
            assert r.relating is None


def _pages(r):
    return [iching.view_text(r, v) for v in iching.VIEWS]


def test_every_page_fits_a_telegram_message():
    rng = random.Random(3)
    for _ in range(300):
        pages = _pages(cast("x" * 200, rng=rng))
        assert "Il giudizio" in pages[0] and all(len(p) < 4096 for p in pages)


class _Tags(HTMLParser):
    """Telegram rejects unbalanced or unknown tags: check what we send."""
    ALLOWED = {"b", "i", "code"}

    def __init__(self):
        super().__init__()
        self.stack = []

    def handle_starttag(self, tag, attrs):
        assert tag in self.ALLOWED, tag
        self.stack.append(tag)

    def handle_endtag(self, tag):
        assert self.stack.pop() == tag


def test_texts_are_valid_telegram_html():
    rng = random.Random(5)
    for q in ["<script> & co", "", "amore?"]:
        for _ in range(100):
            t = _Tags()
            t.feed("".join(_pages(cast(q, rng=rng))))
            assert t.stack == []
    assert "&lt;script&gt; &amp; co" in hexagram_text(cast("<script> & co", rng=rng))


def test_trigrams_match_the_data_for_all_64():
    for h in hexagrams():
        # the data's trigram numbers follow the trigram list; our table is keyed by lines
        assert trigrams(h).startswith("sopra: " + TRIGRAMS[tuple(h["lines"][3:])][0])
    assert trigrams(by_lines([1, 1, 1, 0, 0, 0])) == ("sopra: ☷ Kun, il ricettivo, la terra\n"
                                                      "sotto: ☰ Kiën, il creativo, il cielo")   # 11


def test_figure_picture_has_one_or_two_hexagrams():
    from io import BytesIO
    from PIL import Image
    single = Image.open(BytesIO(figure(from_values([7, 8, 7, 8, 7, 8]))))
    double = Image.open(BytesIO(figure(from_values([9, 8, 8, 8, 8, 6]))))
    assert single.format == "PNG" and double.height == single.height
    assert double.width > single.width + 300           # the relating hexagram beside it


def test_from_values_rebuilds_the_same_reading():
    rng = random.Random(9)
    for _ in range(200):
        r = cast("", rng=rng)
        assert from_values(r.values) == r


def _query(data, markup, user=42, shown="❓ amore & <odio>?\n\n䷀ 1", photo=False):
    # as Telegram returns it: plain text (or caption), no reply_to_message in private chats
    message = SimpleNamespace(reply_markup=markup, reply_to_message=None,
                              photo=["p"] if photo else None,
                              caption=shown if photo else None, text=None if photo else shown)
    query = SimpleNamespace(data=data, message=message, answer=AsyncMock(),
                            from_user=SimpleNamespace(id=user), edit_message_text=AsyncMock(),
                            edit_message_caption=AsyncMock())
    return SimpleNamespace(callback_query=query), query


def test_buttons_change_one_message_and_only_for_the_asker():
    r = from_values([9, 7, 8, 7, 8, 6])
    markup = iching.keyboard(r, 42)
    buttons = markup.inline_keyboard[0]
    assert [b.text[:2] for b in buttons][0] == "▸ " and len(buttons) == 3
    assert all(len(b.callback_data.encode()) <= 64 for b in buttons)
    assert iching.keyboard(from_values([7, 8, 7, 8, 7, 8]), 42) is None

    update, query = _query(buttons[1].callback_data, markup)            # "Linee mobili"
    asyncio.run(iching.on_button(update, None))
    text, kwargs = query.edit_message_text.call_args.args[0], query.edit_message_text.call_args.kwargs
    assert "❓ <i>amore &amp; &lt;odio&gt;?</i>" in text and "All'inizio un nove significa:" in text
    assert [b.text.startswith("▸ ") for b in kwargs["reply_markup"].inline_keyboard[0]] == [False, True, False]

    update, query = _query(buttons[2].callback_data, markup, user=7)    # someone else
    asyncio.run(iching.on_button(update, None))
    query.edit_message_text.assert_not_called()
    assert "Solo chi" in query.answer.call_args.args[0]

    update, query = _query(buttons[0].callback_data, markup)            # the view already shown
    asyncio.run(iching.on_button(update, None))
    query.edit_message_text.assert_not_called()


def test_line_headings_and_all_nines():
    from eden.plugins.iching.oracle import line_heading, moving_text
    assert line_heading(1, 9) == "All'inizio un nove significa:"
    assert line_heading(3, 6) == "Sei al terzo posto significa:"
    assert line_heading(6, 6) == "In alto un sei significa:"
    text = moving_text(from_values([9] * 6))
    assert "Se appaiono soltanto nove" in text and "draghi" in text
    assert moving_text(from_values([7, 8, 7, 8, 7, 8])) == "Nessuna linea mobile."


def test_buttons_edit_the_caption_of_the_picture():
    r = from_values([9, 7, 8, 7, 8, 6])
    buttons = iching.keyboard(r, 42).inline_keyboard[0]
    update, query = _query(buttons[2].callback_data, iching.keyboard(r, 42), photo=True)
    asyncio.run(iching.on_button(update, None))
    query.edit_message_text.assert_not_called()
    caption = query.edit_message_caption.call_args.kwargs["caption"]
    assert caption.startswith("❓ <i>amore &amp; &lt;odio&gt;?</i>") and "Si trasforma in" in caption
