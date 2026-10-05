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


async def reading(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """The hexagram picture with the reading as caption; buttons switch its pages in place.

    When a page is too long for a caption, the pages go in a text message below the picture.
    """
    r = cast(_question(context))
    await suspense(update, context, ChatAction.UPLOAD_PHOTO)
    first = hexagram_text(r)
    if not r.moving:
        first += "\n\n" + moving_text(r)
    pages = [view_text(r, v) for v in VIEWS] if r.moving else [first]
    markup = keyboard(r, update.effective_user.id)
    if all(fits_caption(p) for p in pages):
        await update.effective_message.reply_photo(figure(r), caption=first, parse_mode=ParseMode.HTML,
                                                   reply_markup=markup)
    else:
        photo = await update.effective_message.reply_photo(figure(r))
        await photo.reply_text(first, parse_mode=ParseMode.HTML, reply_markup=markup)


async def on_button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    _, view, values, owner = query.data.split(":")
    if not await only_owner(query, int(owner)):
        return
    if pressed_is_current(query):
        await query.answer()
        return
    message = query.message
    shown = (message.caption if message.photo else message.text) or ""
    # The question is the first line of the reading itself ("❓ ..."); in private chats the
    # reading is not a reply to the command, so it cannot be read from there
    first = shown.split("\n", 1)[0]
    question = first.removeprefix("❓").strip() if first.startswith("❓") else ""
    r = from_values([int(v) for v in values], question)
    await query.answer()
    text, markup = view_text(r, view), keyboard(r, int(owner), view)
    if message.photo:
        await query.edit_message_caption(caption=text, parse_mode=ParseMode.HTML, reply_markup=markup)
    else:
        await query.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=markup)


PLUGIN = Plugin(
    name="iching",
    description="☯️ I Ching",
    commands=(
        Command("esagramma", "Esagramma, linee mobili e trasformazione per la tua domanda", reading,
                "<domanda>"),
        Command("profetizza", "Come /esagramma", reading, "<domanda>"),
    ),
    callbacks=(Callback(PREFIX, on_button),),
)
