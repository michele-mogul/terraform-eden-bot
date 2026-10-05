"""Oswald Wirth's tarot: the 22 Major Arcana of his 1889 deck and his divinatory interpretations.

The texts are the "Interprétations divinatoires" of Le Tarot des imagiers du Moyen Âge (1927),
translated literally and in full, one entry per paragraph of the book. The spread is the one Wirth
gives in "La consultation du Tarot".
"""

import html
import json
import random
import re
from dataclasses import dataclass
from datetime import date
from functools import lru_cache
from pathlib import Path

HERE = Path(__file__).parent
ROMAN = ("0 I II III IV V VI VII VIII IX X XI XII XIII XIV XV XVI XVII XVIII XIX XX XXI").split()
FOOL_VALUE = 22   # the Fool is unnumbered and counts as 22 in the spread
CAPTION_LIMIT = 1024


@dataclass(frozen=True)
class Card:
    number: int
    name: str
    paragraphs: tuple[str, ...]

    @property
    def path(self) -> Path:
        return HERE / "cards" / f"{self.number:02d}.jpg"

    @property
    def value(self) -> int:
        return self.number or FOOL_VALUE

    @property
    def title(self) -> str:
        return f"{ROMAN[self.number]} · {self.name}"


@lru_cache(maxsize=1)
def deck() -> tuple[Card, ...]:
    data = json.loads((HERE / "data" / "wirth.json").read_text(encoding="utf-8"))
    return tuple(Card(c["number"], c["name"], tuple(c["paragraphs"])) for c in data["cards"])


def by_number(n: int) -> Card:
    return deck()[n]


def draw(rng: random.Random) -> Card:
    return rng.choice(deck())


def card_of_the_day(user_id: int, day: date) -> Card:
    """The same card for the same person all day long."""
    return draw(random.Random(f"eden arcano {user_id} {day.isoformat()}"))


# ---------- Wirth's spread ----------

# Wirth's names for the five places of the cross, in drawing order; the fifth is computed
POSITIONS = (("Affermazione", "Pro"), ("Negazione", "Contro"), ("Discussione", "Giudice"),
             ("Soluzione", "Sentenza"), ("Sintesi", ""))
# How each place is read, in Wirth's words ("L'interprétation de l'oracle"), translated literally;
# for the Synthesis the pronoun "Celle-ci" is replaced by its noun
READING = (
    "L'Affermazione mette sulla via di ciò che è favorevole e indica ciò che è bene fare, la "
    "qualità, la virtù, l'amico, il protettore su cui si può contare.",
    "Inversamente, la Negazione designa ciò che è ostile o sfavorevole, ciò che bisogna evitare o "
    "temere, il difetto, il vizio, il nemico, il pericolo, la tentazione perniciosa.",
    "La Discussione illumina sul partito da prendere, sul genere di risoluzione che conviene "
    "adottare, sull'intervento che sarà decisivo.",
    "La Soluzione permette di presagire un risultato tenendo conto del pro e del contro, ma "
    "soprattutto della Sintesi.",
    "La Sintesi si riferisce, in effetti, a ciò che è d'importanza capitale, a ciò da cui tutto "
    "dipende.",
)


def synthesis(values: list[int]) -> Card:
    """Sum of the four arcana (Fool = 22); above 22 its digits are added (theosophical reduction)."""
    n = sum(values)
    if n > 22:
        n = sum(int(d) for d in str(n))
    return by_number(0 if n == FOOL_VALUE else n)


def spread_from_numbers(numbers: list[int]) -> tuple[Card, ...]:
    drawn = [by_number(n) for n in numbers]
    return (*drawn, synthesis([c.value for c in drawn]))


def wirth_spread(rng: random.Random) -> tuple[Card, ...]:
    # Wirth reshuffles the whole deck before each draw, so a card can come out twice
    return spread_from_numbers([draw(rng).number for _ in range(4)])


# ---------- text (Telegram HTML) ----------

def _e(text: str) -> str:
    return html.escape(text.strip(), quote=False)


def position_label(i: int) -> str:
    name, role = POSITIONS[i]
    return f"{name} · {role}" if role else name


def card_text(c: Card, head: str = "") -> str:
    return f"{head}<b>{_e(c.title)}</b>\n\n" + "\n\n".join(_e(p) for p in c.paragraphs)


def plain_length(text: str) -> int:
    """Length as Telegram counts it: without tags, entities decoded."""
    return len(html.unescape(re.sub(r"<[^>]+>", "", text)))


def fits_caption(text: str) -> bool:
    return plain_length(text) <= CAPTION_LIMIT


def spread_caption(question: str, cards: tuple[Card, ...]) -> str:
    q = f"❓ <i>{_e(question)}</i>\n\n" if question.strip() else ""
    legend = "\n".join(f"<b>{position_label(i)}</b>: {_e(c.title)}" for i, c in enumerate(cards))
    return q + legend
