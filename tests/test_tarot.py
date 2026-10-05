import random

from eden.plugins.tarot import NAMES, deck, draw


def test_deck_is_the_22_major_arcana_with_files_and_italian_names():
    cards = deck()
    assert [c.number for c in cards] == list(range(22))
    assert all(c.path.is_file() and c.name == NAMES[c.number] for c in cards)


def test_draw_is_reproducible_with_a_seed():
    assert draw(random.Random(42)) == draw(random.Random(42))
