import random
from collections import Counter
from datetime import datetime

from eden.plugins.iching.oracle import by_lines, cast, cast_line, hexagrams, prophecy_text


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
