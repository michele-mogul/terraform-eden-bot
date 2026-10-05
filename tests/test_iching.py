import random
from collections import Counter
from datetime import datetime

import asyncio
from html.parser import HTMLParser
from types import SimpleNamespace
from unittest.mock import AsyncMock

from eden.plugins import iching
from eden.plugins.iching.oracle import (TRIGRAMS, by_lines, cast, cast_line, figure, from_values,
                                        hexagram_text, hexagrams, prophecy_text, trigrams)


def test_data_has_64_hexagrams_with_consistent_lines():
    hs = hexagrams()
    assert sorted(h["number"] for h in hs) == list(range(1, 65))
    assert len({tuple(h["lines"]) for h in hs}) == 64
    assert all(h["binary"] == "".join(map(str, reversed(h["lines"]))) for h in hs)
    assert all(len(h["linesDescription"]) == 6 for h in hs)


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


def test_prophecy_text_fits_a_telegram_message():
    rng = random.Random(3)
    for _ in range(300):
        text = prophecy_text(cast("una domanda", rng=rng))
        assert "Giudizio" in text and len(text) < 4096


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
            t.feed(prophecy_text(cast(q, rng=rng)))
            assert t.stack == []
    assert "&lt;script&gt; &amp; co" in hexagram_text(cast("<script> & co", rng=rng))


def test_trigrams_match_the_data_for_all_64():
    for h in hexagrams():
        # the data's trigram numbers follow the trigram list; our table is keyed by lines
        assert trigrams(h).startswith(TRIGRAMS[tuple(h["lines"][3:])][0])
    assert trigrams(by_lines([1, 1, 1, 0, 0, 0])) == "☷ Terra sopra · ☰ Cielo sotto"   # 11 Peace


def test_figure_is_drawn_top_down_with_moving_marks_and_relating():
    r = from_values([9, 8, 8, 8, 8, 6])          # moving: line 1 (old yang), line 6 (old yin)
    rows = figure(r).removeprefix("<code>").removesuffix("</code>").split("\n")
    assert [row[0] for row in rows] == list("654321")
    assert rows[0].startswith("6 ━━━   ━━━ ✕") and rows[0].endswith("━━━━━━━━━")
    assert rows[5].startswith("1 ━━━━━━━━━ ○") and rows[5].endswith("━━━   ━━━")
    assert len({len(row) for row in rows}) == 1
    assert "   ━" not in figure(from_values([7, 8, 7, 8, 7, 8]))[-12:]   # no relating column


def test_from_values_rebuilds_the_same_reading():
    rng = random.Random(9)
    for _ in range(200):
        r = cast("", rng=rng)
        assert from_values(r.values) == r


def _query(data, markup, user=42, asked="/esagramma amore?"):
    message = SimpleNamespace(reply_markup=markup, reply_to_message=SimpleNamespace(text=asked))
    query = SimpleNamespace(data=data, message=message, answer=AsyncMock(),
                            from_user=SimpleNamespace(id=user), edit_message_text=AsyncMock())
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
    assert "amore?" in text and "Linea 1" in text and "<code>" in text
    assert [b.text.startswith("▸ ") for b in kwargs["reply_markup"].inline_keyboard[0]] == [False, True, False]

    update, query = _query(buttons[2].callback_data, markup, user=7)    # someone else
    asyncio.run(iching.on_button(update, None))
    query.edit_message_text.assert_not_called()
    assert "Solo chi" in query.answer.call_args.args[0]

    update, query = _query(buttons[0].callback_data, markup)            # the view already shown
    asyncio.run(iching.on_button(update, None))
    query.edit_message_text.assert_not_called()
