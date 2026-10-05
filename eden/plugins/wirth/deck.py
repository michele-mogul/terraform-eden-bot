"""Oswald Wirth's tarot: the 22 Major Arcana of his 1889 deck and his divinatory meanings.

Wirth reads every arcanum "in good or in bad part", from its highest sense down to vices and
misfortunes (Le Tarot des imagiers du Moyen Âge, 1927). Eden draws a card upright or reversed to
choose between the two. The spread is the one Wirth gives in "La consultation du Tarot".
"""

import html
import json
import random
from dataclasses import dataclass
from datetime import date
from functools import lru_cache
from pathlib import Path

HERE = Path(__file__).parent
ROMAN = ("0 I II III IV V VI VII VIII IX X XI XII XIII XIV XV XVI XVII XVIII XIX XX XXI").split()
FOOL_VALUE = 22   # the Fool is unnumbered and counts as 22 in the spread


@dataclass(frozen=True)
class Card:
    number: int
    name: str
    essence: str
    favorable: str
    unfavorable: str

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
def _data() -> dict:
    return json.loads((HERE / "data" / "wirth.json").read_text(encoding="utf-8"))


def deck() -> tuple[Card, ...]:
    return tuple(Card(**c) for c in _data()["cards"])


def by_number(n: int) -> Card:
    return deck()[n]


@dataclass(frozen=True)
class Draw:
    card: Card
    reversed: bool


def draw(rng: random.Random) -> Draw:
    return Draw(rng.choice(deck()), rng.random() < 0.5)


def card_of_the_day(user_id: int, day: date) -> Draw:
    """The same card for the same person all day long."""
    return draw(random.Random(f"eden arcano {user_id} {day.isoformat()}"))


# ---------- Wirth's spread ----------

# (emoji, name, what the position tells) in drawing order; the fifth is computed
POSITIONS = (
    ("➕", "Affermazione", "ciò che è favorevole, ciò che conviene fare, l'alleato"),
    ("➖", "Negazione", "ciò che è ostile, da evitare o da temere"),
    ("⚖️", "Discussione", "il partito da prendere, l'intervento decisivo"),
    ("🎯", "Soluzione", "il risultato, alla luce del pro, del contro e soprattutto della Sintesi"),
    ("✴️", "Sintesi", "ciò che conta di più, ciò da cui tutto dipende"),
)


def synthesis(values: list[int]) -> tuple[Card, str]:
    """Sum of the four arcana (Fool = 22); above 22 its digits are added (theosophical reduction)."""
    total = sum(values)
    how = " + ".join(map(str, values)) + f" = {total}"
    n = total
    if total > 22:
        n = sum(int(d) for d in str(total))
        how += " → " + " + ".join(str(total)) + f" = {n}"
    return by_number(0 if n == FOOL_VALUE else n), how


@dataclass(frozen=True)
class Spread:
    question: str
    cards: tuple[Card, ...]   # affirmation, negation, discussion, solution, synthesis
    how: str                  # how the synthesis was computed


def wirth_spread(question: str, rng: random.Random) -> Spread:
    # Wirth reshuffles the whole deck before each draw, so a card can come out twice
    drawn = [rng.choice(deck()) for _ in range(4)]
    synth, how = synthesis([c.value for c in drawn])
    return Spread(question, (*drawn, synth), how)


# ---------- text (Telegram HTML) ----------

def _e(text: str) -> str:
    return html.escape(text.strip(), quote=False)


CREDIT = "<i>Significati da Oswald Wirth, Le Tarot des imagiers du Moyen Âge (1927)</i>"


def card_caption(d: Draw, head: str = "🃏") -> str:
    c = d.card
    sense = ("🙃 rovesciata · in senso sfavorevole" if d.reversed else "☀️ dritta · in senso favorevole")
    meaning = c.unfavorable if d.reversed else c.favorable
    return (f"{head} <b>{_e(c.title)}</b>\n<i>{sense}</i>\n\n"
            f"<i>{_e(c.essence)}</i>\n\n{_e(meaning)}\n\n{CREDIT}")


def spread_caption(s: Spread) -> str:
    q = f"\n❓ <i>{_e(s.question)}</i>" if s.question.strip() else ""
    legend = "\n".join(f"{e} {name}: {_e(c.title)}" for (e, name, _), c in zip(POSITIONS, s.cards))
    return f"🔮 <b>La croce di Wirth</b>{q}\n\n{legend}"


def spread_text(s: Spread) -> str:
    out = []
    for i, ((emoji, name, role), c) in enumerate(zip(POSITIONS, s.cards)):
        if i == 0:
            body = _e(c.favorable)
        elif i == 1:
            body = _e(c.unfavorable)
        elif i == 4:
            body = _e(c.essence)
        else:   # the diviner weighs both senses
            body = f"☀️ {_e(c.favorable)}\n\n🌑 {_e(c.unfavorable)}"
        note = f" · {s.how}" if i == 4 else ""
        out.append(f"{emoji} <b>{name}</b> — {_e(c.title)}\n<i>{role}{note}</i>\n"
                   f"<blockquote expandable>{body}</blockquote>")
    q = f"❓ <i>{_e(s.question)}</i>\n\n" if s.question.strip() else ""
    return q + "\n".join(out) + "\n" + CREDIT
