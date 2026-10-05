"""Oswald Wirth's tarot: a card with its meaning, Wirth's cross spread, the card of the day."""

import html
import random
from datetime import date

from telegram import Update
from telegram.constants import ChatAction, ParseMode
from telegram.ext import ContextTypes

from eden.core.plugin import Command, Plugin
from eden.core.ui import suspense
from eden.plugins.wirth.deck import (card_caption, card_of_the_day, draw, spread_caption,
                                     spread_text, wirth_spread)
from eden.plugins.wirth.images import card_photo, cross

_rng = random.SystemRandom()


async def carta(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    d = draw(_rng)
    await suspense(update, context, ChatAction.UPLOAD_PHOTO)
    await update.effective_message.reply_photo(card_photo(d), caption=card_caption(d),
                                               parse_mode=ParseMode.HTML)


async def stesa(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    s = wirth_spread(" ".join(context.args or []).strip(), _rng)
    await suspense(update, context, ChatAction.UPLOAD_PHOTO)
    sent = await update.effective_message.reply_photo(cross(s.cards), caption=spread_caption(s),
                                                      parse_mode=ParseMode.HTML)
    await sent.reply_text(spread_text(s), parse_mode=ParseMode.HTML)


async def arcano(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    d = card_of_the_day(user.id, date.today())
    await suspense(update, context, ChatAction.UPLOAD_PHOTO)
    head = f"🌅 Arcano del giorno di {html.escape(user.first_name)} ·"
    await update.effective_message.reply_photo(card_photo(d), caption=card_caption(d, head),
                                               parse_mode=ParseMode.HTML)


PLUGIN = Plugin(
    name="wirth",
    description="📜 Tarocchi di Wirth",
    commands=(
        Command("wirth", "Un arcano di Wirth con il suo significato", carta),
        Command("stesa", "La croce di Wirth: pro, contro, discussione, soluzione, sintesi", stesa,
                "<domanda>"),
        Command("arcano", "Il tuo arcano del giorno", arcano),
    ),
)
