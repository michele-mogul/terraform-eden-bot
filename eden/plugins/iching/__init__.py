"""I Ching: a hexagram for a question, or a full prophecy with moving lines."""

from telegram import Update
from telegram.ext import ContextTypes

from eden.core.plugin import Command, Plugin
from eden.plugins.iching.oracle import cast, hexagram_text, prophecy_text


def _question(context: ContextTypes.DEFAULT_TYPE) -> str:
    return " ".join(context.args or []).strip()


async def esagramma(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.effective_message.reply_text(hexagram_text(cast(_question(context))))


async def profetizza(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.effective_message.reply_text(prophecy_text(cast(_question(context))))


PLUGIN = Plugin(
    name="iching",
    description="☯️ I Ching",
    commands=(
        Command("esagramma", "Estrai un esagramma per la tua domanda", esagramma, "<domanda>"),
        Command("profetizza", "Esagramma, linee mobili e trasformazione", profetizza, "<domanda>"),
    ),
)
