# Eden bot

Telegram bot for a group of friends: tarot cards and I Ching, built from plugins.

| Command | What it does |
|---|---|
| `/tarocco` | Draws one of the 22 Major Arcana (Rider-Waite-Smith), with its Italian name |
| `/esagramma <domanda>` | An I Ching hexagram for the question (yarrow-stalk method) |
| `/profetizza <domanda>` | Hexagram, moving lines and the hexagram it changes into |
| `/help` | Generated list of commands |

In groups commands also work as `/tarocco@botname`. Each user has a short cooldown (`COOLDOWN_SECONDS`).

## Run

```
cp .env.example .env            # set TELEGRAM_TOKEN
docker run --env-file .env ghcr.io/michele-mogul/eden-bot:latest
# or, without Docker:
pip install -r requirements.txt && python -m eden
```
Long polling: no public URL is needed. Starting the bot removes any webhook set on the token.

## Add a feature

Create a package in `eden/plugins/<name>/` whose `__init__.py` exposes:

```python
from eden.core.plugin import Command, Plugin

async def ciao(update, context):
    await update.effective_message.reply_text("Ciao!")

PLUGIN = Plugin(name="hello", description="👋 Saluti",
                commands=(Command("ciao", "Saluta", ciao),))
```
The core finds it at start-up, registers the command, adds it to Telegram's command menu and to
`/help`, and wraps it with the cooldown and error handling. Put data files next to the code
(`eden/plugins/<name>/data/`) and tests in `tests/`.

Inline buttons: give them `callback_data="<prefix>:..."` (max 64 bytes) and declare
`callbacks=(Callback("<prefix>", handler),)` in the plugin; the core routes the presses, applies
`ALLOWED_CHATS` and answers the query. `eden.core.ui.suspense()` shows "typing…" for a moment
before a reading.

## Development

```
pip install -r requirements-dev.txt
python -m pytest
```
CI runs the tests on every push; pushes to `master` publish `ghcr.io/michele-mogul/eden-bot`
(linux/amd64 and linux/arm64).

## History

v1 ran on AWS Lambda behind a Function URL webhook (Terraform). That version is kept in the
`aws-lambda` branch. v2 (this) runs as a container on the homelab Raspberry Pi.
The I Ching readings of v2 were checked against v1: same hexagrams, moving lines and changes
for 5 000 seeded questions.
