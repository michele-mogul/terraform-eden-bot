"""I Ching: a hexagram for a question, or a full prophecy with moving lines."""

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ChatAction, ParseMode
from telegram.ext import ContextTypes

from eden.core.plugin import Callback, Command, Plugin
from eden.core.ui import CURRENT, fits_caption, only_owner, pressed_is_current, suspense
from eden.plugins.iching.images import figure
from eden.plugins.iching.oracle import (Reading, cast, from_values, header, hexagram_text,
                                        moving_text, relating_text)

PREFIX = "iching"
VIEWS = {"hex": "☯️ Esagramma", "lines": "📜 Linee mobili", "rel": "↪ Trasformazione"}


def _question(context: ContextTypes.DEFAULT_TYPE) -> str:
    return " ".join(context.args or []).strip()


def view_text(r: Reading, view: str) -> str:
    if view == "lines":
        return header(r) + moving_text(r)
    if view == "rel":
        return header(r) + relating_text(r)
    return hexagram_text(r)


def keyboard(r: Reading, owner: int, current: str = "hex") -> InlineKeyboardMarkup | None:
    """Views of one reading; the line values and the asker travel in the callback data."""
    if not r.moving:
        return None
    values = "".join(map(str, r.values))
    return InlineKeyboardMarkup([[
        InlineKeyboardButton((CURRENT if view == current else "") + label,
                             callback_data=f"{PREFIX}:{view}:{values}:{owner}")
        for view, label in VIEWS.items()]])


async def esagramma(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """The hexagram as a picture, its text as caption (or just below when too long)."""
    r = cast(_question(context))
    await suspense(update, context, ChatAction.UPLOAD_PHOTO)
    text = hexagram_text(r)
    if fits_caption(text):
        await update.effective_message.reply_photo(figure(r), caption=text, parse_mode=ParseMode.HTML)
    else:
        photo = await update.effective_message.reply_photo(figure(r))
        await photo.reply_text(text, parse_mode=ParseMode.HTML)


async def profetizza(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """The picture, then one message whose buttons switch between the pages of the reading."""
    r = cast(_question(context))
    await suspense(update, context, ChatAction.UPLOAD_PHOTO)
    photo = await update.effective_message.reply_photo(figure(r))
    text = hexagram_text(r)
    if not r.moving:
        text += "\n\n" + moving_text(r)
    await photo.reply_text(text, parse_mode=ParseMode.HTML,
                           reply_markup=keyboard(r, update.effective_user.id))


async def on_button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    _, view, values, owner = query.data.split(":")
    if not await only_owner(query, int(owner)):
        return
    if pressed_is_current(query):
        await query.answer()
        return
    # The question is the first line of the message itself ("❓ ..."); in private chats the
    # reading is not a reply to the command, so it cannot be read from there
    first = (query.message.text or "").split("\n", 1)[0]
    question = first.removeprefix("❓").strip() if first.startswith("❓") else ""
    r = from_values([int(v) for v in values], question)
    await query.answer()
    await query.edit_message_text(view_text(r, view), parse_mode=ParseMode.HTML,
                                  reply_markup=keyboard(r, int(owner), view))


PLUGIN = Plugin(
    name="iching",
    description="☯️ I Ching",
    commands=(
        Command("esagramma", "Estrai un esagramma per la tua domanda", esagramma, "<domanda>"),
        Command("profetizza", "Esagramma, linee mobili e trasformazione, da sfogliare", profetizza,
                "<domanda>"),
    ),
    callbacks=(Callback(PREFIX, on_button),),
)
