"""I Ching readings with the yarrow-stalk method (same algorithm and seeding as Eden v1).

Lines are listed bottom to top. A reading has a primary hexagram, its moving lines and, if any
line moves, the relating hexagram (primary lines XOR moving lines).
"""

import html
import json
import random
from dataclasses import dataclass
from datetime import datetime
from functools import lru_cache
from pathlib import Path

DATA = Path(__file__).parent / "data" / "iching.json"


@lru_cache(maxsize=1)
def hexagrams() -> list[dict]:
    """The 64 hexagrams: number, character, lines, Wilhelm's name and texts in Italian."""
    return json.loads(DATA.read_text(encoding="utf-8"))["hexagrams"]


def by_lines(lines: list[int]) -> dict:
    return next(h for h in hexagrams() if h["lines"] == lines)


# ---------- yarrow stalks ----------

def _remainder(pile: int) -> int:
    r = pile % 4
    return r if r else 4


def _composite(stalks: int, rng: random.Random) -> tuple[int, int]:
    """One division of the stalks: (stalks used, value 2 or 3)."""
    left = int(rng.uniform(4, stalks - 5))
    right = stalks - left - 1          # one stalk set aside
    used = 1 + _remainder(left) + _remainder(right)
    if used in (9, 8):
        return used, 2
    if used in (5, 4):
        return used, 3
    raise ValueError(f"unexpected number of stalks used: {used}")


def cast_line(rng: random.Random) -> int:
    """6 old yin (moving), 7 young yang, 8 young yin, 9 old yang (moving)."""
    stalks, total = 49, 0
    for _ in range(3):
        used, value = _composite(stalks, rng)
        stalks -= used
        total += value
    return total


@dataclass(frozen=True)
class Reading:
    question: str
    primary: dict
    moving: tuple[int, ...]          # 1-based positions of the moving lines (bottom = 1)
    relating: dict | None
    values: tuple[int, ...] = ()     # the six line values 6/7/8/9, bottom to top


def from_values(values: list[int] | tuple[int, ...], question: str = "") -> Reading:
    """Rebuild a reading from its line values (used by the inline buttons)."""
    if len(values) != 6 or not set(values) <= {6, 7, 8, 9}:
        raise ValueError(f"invalid line values: {values}")
    lines = [1 if v in (7, 9) else 0 for v in values]
    changing = [1 if v in (6, 9) else 0 for v in values]
    moving = tuple(i + 1 for i, c in enumerate(changing) if c)
    relating = by_lines([l ^ c for l, c in zip(lines, changing)]) if moving else None
    return Reading(question, by_lines(lines), moving, relating, tuple(values))


def cast(question: str, rng: random.Random | None = None, now: datetime | None = None) -> Reading:
    if rng is None:
        # Eden v1 seeding: the question plus the current second
        now = now or datetime.now()
        rng = random.Random(f"{question} in this time: {now:%y%m%d%H%M%S}")
    return from_values([cast_line(rng) for _ in range(6)], question)


# ---------- text (Telegram HTML) ----------

# Trigrams by their lines, bottom to top: symbol and Wilhelm's name, attribute and image
TRIGRAMS = {
    (1, 1, 1): ("☰", "Kiën, il creativo, il cielo"), (0, 0, 0): ("☷", "Kun, il ricettivo, la terra"),
    (1, 0, 0): ("☳", "Dschen, l'eccitante, il tuono"), (0, 1, 0): ("☵", "Kan, l'abissale, l'acqua"),
    (0, 0, 1): ("☶", "Gen, il tener fermo, il monte"), (0, 1, 1): ("☴", "Sun, il mite, il vento"),
    (1, 0, 1): ("☲", "Li, l'aderente, il fuoco"), (1, 1, 0): ("☱", "Dui, il sereno, il lago"),
}
MARK = {6: "✕", 9: "○"}             # old yin and old yang: the moving lines
VALUE = {6: "sei", 9: "nove"}
PLACE = {2: "secondo", 3: "terzo", 4: "quarto", 5: "quinto"}


def _e(text: str) -> str:
    return html.escape(text.strip(), quote=False)


def trigrams(h: dict) -> str:
    top, bottom = TRIGRAMS[tuple(h["lines"][3:])], TRIGRAMS[tuple(h["lines"][:3])]
    return f"sopra: {top[0]} {top[1]}\nsotto: {bottom[0]} {bottom[1]}"


def line_heading(position: int, value: int) -> str:
    """Wilhelm's heading of a line, e.g. "Nove al secondo posto significa:"."""
    v = VALUE[value]
    if position == 1:
        return f"All'inizio un {v} significa:"
    if position == 6:
        return f"In alto un {v} significa:"
    return f"{v.capitalize()} al {PLACE[position]} posto significa:"


def title(h: dict) -> str:
    return f"<b>{h['character']} {h['number']} · {_e(h['wilhelm'])} · {_e(h['name'])}</b>"


def describe(h: dict) -> str:
    return (f"{title(h)}\n<i>{_e(trigrams(h))}</i>\n\n"
            f"<b>Il giudizio</b>\n{_e(h['judgement'])}\n\n<b>L'immagine</b>\n{_e(h['image'])}")


def header(r: Reading) -> str:
    """The question, first line of every page (the buttons read it back from there)."""
    return f"❓ <i>{_e(r.question)}</i>\n\n" if r.question.strip() else ""


def hexagram_text(r: Reading) -> str:
    return header(r) + describe(r.primary)


def moving_text(r: Reading) -> str:
    if not r.moving:
        return "Nessuna linea mobile."
    h = r.primary
    out = [f"<b>Linee mobili di {h['character']} {h['number']}</b>"]
    for n in r.moving:
        v = r.values[n - 1]
        out.append(f"\n{MARK[v]} <b>{line_heading(n, v)}</b>\n{_e(h['lineTexts'][n - 1])}")
    if len(r.moving) == 6 and h.get("allLines"):   # only 1 and 2: all nines, all sixes
        v = r.values[0]
        out.append(f"\n<b>Se appaiono soltanto {VALUE[v]}, ciò significa:</b>\n{_e(h['allLines'])}")
    return "\n".join(out)


def relating_text(r: Reading) -> str:
    if not r.relating:
        return "Nessuna linea mobile."
    return "↪ <b>Si trasforma in</b>\n\n" + describe(r.relating)
