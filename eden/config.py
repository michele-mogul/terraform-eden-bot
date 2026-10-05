"""Configuration from environment variables (see .env.example)."""

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Config:
    token: str
    allowed_chats: frozenset[int]   # empty: every chat
    cooldown: float                 # seconds between two commands of the same user in the same chat
    log_level: str


def load() -> Config:
    # TELEGRAM_TOKEN; "telegram_key" is the name used by the old AWS Lambda version
    token = os.environ.get("TELEGRAM_TOKEN") or os.environ.get("telegram_key")
    if not token:
        raise SystemExit("TELEGRAM_TOKEN is not set")
    chats = frozenset(int(c) for c in os.environ.get("ALLOWED_CHATS", "").replace(" ", "").split(",") if c)
    return Config(
        token=token,
        allowed_chats=chats,
        cooldown=float(os.environ.get("COOLDOWN_SECONDS", "5")),
        log_level=os.environ.get("LOG_LEVEL", "INFO").upper(),
    )
