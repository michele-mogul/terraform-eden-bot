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
    """The 64 hexagrams: number, names, character, lines, judgement, images, linesDescription."""
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

# Trigrams by their lines, bottom to top: symbol and the Italian name of their image
TRIGRAMS = {
    (1, 1, 1): ("☰", "Cielo"), (0, 0, 0): ("☷", "Terra"), (1, 0, 0): ("☳", "Tuono"),
    (0, 1, 0): ("☵", "Acqua"), (0, 0, 1): ("☶", "Monte"), (0, 1, 1): ("☴", "Vento"),
    (1, 0, 1): ("☲", "Fuoco"), (1, 1, 0): ("☱", "Lago"),
}
YANG, YIN = "━━━━━━━━━", "━━━   ━━━"
MARK = {6: "✕", 9: "○"}             # old yin and old yang: the moving lines


def _e(text: str) -> str:
    return html.escape(text.strip(), quote=False)


def trigrams(h: dict) -> str:
    top, bottom = TRIGRAMS[tuple(h["lines"][3:])], TRIGRAMS[tuple(h["lines"][:3])]
    return f"{top[0]} {top[1]} sopra · {bottom[0]} {bottom[1]} sotto"


def figure(r: Reading) -> str:
    """The hexagram drawn top to bottom, moving lines marked, and the relating one beside it."""
    rows = []
    for i in range(5, -1, -1):
        v = r.values[i]
        row = f"{i + 1} {YANG if v in (7, 9) else YIN} {MARK.get(v, ' ')}"
        if r.relating:
            row += f"   {YANG if r.relating['lines'][i] else YIN}"
        rows.append(row)
    return "<code>" + "\n".join(rows) + "</code>"


def title(h: dict) -> str:
    return f"<b>{h['character']} {h['number']} · {_e(', '.join(h['names']))}</b>"


def describe(h: dict) -> str:
    return (f"{title(h)}\n<i>{trigrams(h)}</i>\n\n"
            f"<b>Giudizio</b>\n{_e(h['judgement'])}\n\n<b>Immagine</b>\n{_e(h['images'])}")


def hexagram_text(r: Reading) -> str:
    head = f"❓ <i>{_e(r.question)}</i>\n\n" if r.question.strip() else ""
    return head + figure(r) + "\n\n" + describe(r.primary)


def moving_text(r: Reading) -> str:
    if not r.moving:
        return "Nessuna linea mobile: la situazione è stabile."
    desc = r.primary["linesDescription"]
    out = [f"<b>Linee mobili di {r.primary['character']} {r.primary['number']}</b>"]
    for n in r.moving:
        out.append(f"\n{MARK[r.values[n - 1]]} <b>Linea {n}</b>\n{_e(desc[n - 1]['meaning'])}")
    return "\n".join(out)


def relating_text(r: Reading) -> str:
    if not r.relating:
        return "Nessuna linea mobile: l'esagramma non si trasforma."
    return "↪ <b>Si trasforma in</b>\n\n" + describe(r.relating)


def prophecy_text(r: Reading) -> str:
    out = [hexagram_text(r), moving_text(r)]
    if r.relating:
        out.append(relating_text(r))
    return "\n\n〰️〰️〰️\n\n".join(out)
