"""Oswald Wirth's tarot: a card with Wirth's interpretation, his cross spread, the card of the day."""

import html
import random
from datetime import date

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Message, Update
from telegram.constants import ChatAction, ParseMode
from telegram.ext import ContextTypes

from eden.core.plugin import Callback, Command, Plugin
from eden.core.ui import suspense
from eden.plugins.wirth.deck import (POSITIONS, Card, card_of_the_day, card_text, draw,
                                     fits_caption, position_label, spread_caption,
                                     spread_from_numbers, wirth_spread)
from eden.plugins.wirth.images import cross

PREFIX = "wirth"
_rng = random.SystemRandom()


async def send_card(message: Message, card: Card, head: str = "") -> None:
    """The card with Wirth's text as caption, or below the picture when it is too long."""
    text = card_text(card, head)
    with card.path.open("rb") as f:
        if fits_caption(text):
            await message.reply_photo(f, caption=text, parse_mode=ParseMode.HTML)
        else:
            sent = await message.reply_photo(f, caption=f"{head}<b>{html.escape(card.title)}</b>",
                                             parse_mode=ParseMode.HTML)
            await sent.reply_text(text, parse_mode=ParseMode.HTML)


async def carta(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    card = draw(_rng)
    await suspense(update, context, ChatAction.UPLOAD_PHOTO)
    await send_card(update.effective_message, card)


async def arcano(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    card = card_of_the_day(user.id, date.today())
    await suspense(update, context, ChatAction.UPLOAD_PHOTO)
    await send_card(update.effective_message, card, f"🌅 {html.escape(user.first_name)} · ")


def keyboard(numbers: list[int], used: set[int] = frozenset()) -> InlineKeyboardMarkup | None:
    """One button per place of the cross; the four drawn numbers travel in the callback data."""
    data = "-".join(map(str, numbers))
    buttons = [InlineKeyboardButton(POSITIONS[i][0], callback_data=f"{PREFIX}:{i}:{data}")
               for i in range(5) if i not in used]
    if not buttons:
        return None
    return InlineKeyboardMarkup([buttons[:3], buttons[3:]] if len(buttons) > 3 else [buttons])


async def stesa(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    cards = wirth_spread(_rng)
    numbers = [c.number for c in cards[:4]]
    await suspense(update, context, ChatAction.UPLOAD_PHOTO)
    await update.effective_message.reply_photo(
        cross(cards), caption=spread_caption(" ".join(context.args or []), cards),
        parse_mode=ParseMode.HTML, reply_markup=keyboard(numbers))


async def on_button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    _, pos, data = query.data.split(":")
    i, numbers = int(pos), [int(n) for n in data.split("-")]
    card = spread_from_numbers(numbers)[i]
    await query.answer()
    await query.message.reply_text(card_text(card, f"<b>{position_label(i)}</b>\n"),
                                   parse_mode=ParseMode.HTML)
    # Each place is revealed once: drop the pressed button
    markup = query.message.reply_markup
    shown = {int(b.callback_data.split(":")[1]) for row in markup.inline_keyboard for b in row} \
        if markup else set()
    await query.edit_message_reply_markup(keyboard(numbers, (set(range(5)) - shown) | {i}))


PLUGIN = Plugin(
    name="wirth",
    description="📜 Tarocchi di Wirth",
    commands=(
        Command("wirth", "Un arcano di Wirth con la sua interpretazione", carta),
        Command("stesa", "La croce di Wirth", stesa, "<domanda>"),
        Command("arcano", "Il tuo arcano del giorno", arcano),
    ),
    callbacks=(Callback(PREFIX, on_button),),
)
