"""Small helpers shared by plugins."""

import asyncio

from telegram import Update
from telegram.constants import ChatAction
from telegram.ext import ContextTypes

SUSPENSE_SECONDS = 1.5   # set to 0 in tests


async def suspense(update: Update, context: ContextTypes.DEFAULT_TYPE,
                   action: str = ChatAction.TYPING) -> None:
    """Show "Eden is typing…" for a moment before revealing a reading."""
    if SUSPENSE_SECONDS <= 0 or not update.effective_chat:
        return
    try:
        await context.bot.send_chat_action(update.effective_chat.id, action)
    except Exception:
        return   # cosmetic only
    await asyncio.sleep(SUSPENSE_SECONDS)


async def only_owner(query, owner_id: int) -> bool:
    """True when the button was pressed by who asked for the reading; others get a short notice."""
    if query.from_user and query.from_user.id == owner_id:
        return True
    await query.answer("Solo chi ha chiesto la lettura può sfogliarla.")
    return False


def pressed_is_current(query) -> bool:
    """The pressed button is the view already shown (its label starts with CURRENT)."""
    markup = query.message.reply_markup
    for row in (markup.inline_keyboard if markup else ()):
        for b in row:
            if b.callback_data == query.data:
                return b.text.startswith(CURRENT)
    return False


CURRENT = "▸ "   # marks the view shown in a message that changes in place
