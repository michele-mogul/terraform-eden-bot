"""I Ching: a hexagram for a question, or a full prophecy with moving lines."""

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from eden.core.plugin import Callback, Command, Plugin
from eden.core.ui import suspense
from eden.plugins.iching.oracle import (Reading, cast, from_values, hexagram_text, moving_text,
                                        prophecy_text, relating_text)

PREFIX = "iching"
BUTTONS = {"lines": "📜 Linee mobili", "rel": "↪ Trasformazione"}


def _question(context: ContextTypes.DEFAULT_TYPE) -> str:
    return " ".join(context.args or []).strip()


def keyboard(r: Reading, used: set[str] = frozenset()) -> InlineKeyboardMarkup | None:
    """Buttons to reveal the moving lines and the relating hexagram; the reading travels in the data."""
    if not r.moving:
        return None
    values = "".join(map(str, r.values))
    row = [InlineKeyboardButton(label, callback_data=f"{PREFIX}:{kind}:{values}")
           for kind, label in BUTTONS.items() if kind not in used]
    return InlineKeyboardMarkup([row]) if row else None


async def esagramma(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    r = cast(_question(context))
    await suspense(update, context)
    text = hexagram_text(r)
    if not r.moving:
        text += "\n\n<i>Nessuna linea mobile: la situazione è stabile.</i>"
    await update.effective_message.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=keyboard(r))


async def profetizza(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    r = cast(_question(context))
    await suspense(update, context)
    await update.effective_message.reply_text(prophecy_text(r), parse_mode=ParseMode.HTML)


async def on_button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    _, kind, values = query.data.split(":")
    r = from_values([int(v) for v in values])
    text = moving_text(r) if kind == "lines" else relating_text(r)
    await query.answer()
    await query.message.reply_text(text, parse_mode=ParseMode.HTML)
    # Each detail is revealed once: drop the pressed button, keep the other
    markup = query.message.reply_markup
    shown = {b.callback_data.split(":")[1] for row in markup.inline_keyboard for b in row} if markup else set()
    await query.edit_message_reply_markup(keyboard(r, set(BUTTONS) - shown | {kind}))


PLUGIN = Plugin(
    name="iching",
    description="☯️ I Ching",
    commands=(
        Command("esagramma", "Estrai un esagramma per la tua domanda", esagramma, "<domanda>"),
        Command("profetizza", "Esagramma, linee mobili e trasformazione", profetizza, "<domanda>"),
    ),
    callbacks=(Callback(PREFIX, on_button),),
)
