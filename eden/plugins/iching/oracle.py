"""I Ching readings with the yarrow-stalk method (same algorithm and seeding as Eden v1).

Lines are listed bottom to top. A reading has a primary hexagram, its moving lines and, if any
line moves, the relating hexagram (primary lines XOR moving lines).
"""

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


def cast(question: str, rng: random.Random | None = None, now: datetime | None = None) -> Reading:
    if rng is None:
        # Eden v1 seeding: the question plus the current second
        now = now or datetime.now()
        rng = random.Random(f"{question} in this time: {now:%y%m%d%H%M%S}")
    values = [cast_line(rng) for _ in range(6)]
    lines = [1 if v in (7, 9) else 0 for v in values]
    changing = [1 if v in (6, 9) else 0 for v in values]
    primary = by_lines(lines)
    moving = tuple(i + 1 for i, c in enumerate(changing) if c)
    relating = by_lines([l ^ c for l, c in zip(lines, changing)]) if moving else None
    return Reading(question, primary, moving, relating)


# ---------- text ----------

def describe(h: dict) -> str:
    return (f"{h['character']} {h['number']} · {', '.join(h['names'])}\n\n"
            f"Giudizio:\n{h['judgement']}\n\nImmagine:\n{h['images']}")


def hexagram_text(r: Reading) -> str:
    head = f"❓ {r.question}\n\n" if r.question else ""
    return head + describe(r.primary)


def prophecy_text(r: Reading) -> str:
    out = [hexagram_text(r)]
    if not r.moving:
        out.append("\n\nNessuna linea mobile: la situazione è stabile.")
    else:
        desc = r.primary["linesDescription"]
        out.append("\n\nLinee mobili:")
        out += [f"\n• Linea {n}: {desc[n - 1]['meaning']}" for n in r.moving]
        out.append("\n\n↪ Si trasforma in:\n" + describe(r.relating))
    return "".join(out)
