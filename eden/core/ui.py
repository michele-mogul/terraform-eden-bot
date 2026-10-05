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
