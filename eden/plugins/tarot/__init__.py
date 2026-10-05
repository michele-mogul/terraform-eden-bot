"""Tarot: draws one of the 22 Major Arcana of the Rider-Waite-Smith deck (images in cards/)."""

import random
import re
from dataclasses import dataclass
from pathlib import Path

from telegram import Update
from telegram.ext import ContextTypes

from eden.core.plugin import Command, Plugin

CARDS = Path(__file__).parent / "cards"
# Rider-Waite-Smith order (Strength 8, Justice 11), Italian names
NAMES = {
    0: "Il Matto", 1: "Il Bagatto", 2: "La Papessa", 3: "L'Imperatrice", 4: "L'Imperatore",
    5: "Il Papa", 6: "Gli Amanti", 7: "Il Carro", 8: "La Forza", 9: "L'Eremita",
    10: "La Ruota della Fortuna", 11: "La Giustizia", 12: "L'Appeso", 13: "La Morte",
    14: "La Temperanza", 15: "Il Diavolo", 16: "La Torre", 17: "La Stella", 18: "La Luna",
    19: "Il Sole", 20: "Il Giudizio", 21: "Il Mondo",
}
_rng = random.SystemRandom()


@dataclass(frozen=True)
class Card:
    number: int
    name: str
    path: Path


def deck() -> list[Card]:
    cards = []
    for p in sorted(CARDS.glob("RWS_Tarot_*.jpg")):
        m = re.match(r"RWS_Tarot_(\d+)_", p.name)
        if m:
            n = int(m.group(1))
            cards.append(Card(n, NAMES.get(n, p.stem), p))
    return cards


def draw(rng: random.Random = _rng) -> Card:
    return rng.choice(deck())


async def tarocco(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    card = draw()
    with card.path.open("rb") as f:
        await update.effective_message.reply_photo(f, caption=f"🃏 {card.number} · {card.name}")


PLUGIN = Plugin(
    name="tarot",
    description="🃏 Tarocchi",
    commands=(Command("tarocco", "Estrai un arcano maggiore", tarocco),),
)
