"""Telegram application: registers every plugin command, /start and /help, guards and polling."""

import html
import logging

from telegram import BotCommand, Update
from telegram.constants import ParseMode
from telegram.ext import Application, CallbackQueryHandler, CommandHandler, ContextTypes, filters

from eden import __version__
from eden.config import Config, load
from eden.core.plugin import Callback, Command, Handler, Plugin, discover
from eden.core.ratelimit import Cooldown

log = logging.getLogger("eden")

SHORT_DESCRIPTION = "🔮 Tarocchi e I Ching per il gruppo"
DESCRIPTION = ("🔮 Eden consulta gli oracoli per te.\n\n"
               "🃏 /tarocco estrae un arcano maggiore\n"
               "☯️ /esagramma e /profetizza interrogano l'I Ching\n\n"
               "/help per tutti i comandi")


def guarded(command: Command, cooldown: Cooldown) -> Handler:
    """Wrap a plugin handler: per-user cooldown and a friendly message instead of a crash."""
    async def run(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        chat, user = update.effective_chat, update.effective_user
        if chat and user:
            wait = cooldown.hit(chat.id, user.id)
            if wait > 0:
                await update.effective_message.reply_text(f"⏳ Un attimo di pazienza: riprova tra {wait:.0f} s.")
                return
        try:
            await command.handler(update, context)
        except Exception:
            log.exception("/%s failed", command.name)
            await update.effective_message.reply_text("😵 Qualcosa è andato storto, riprova più tardi.")
    return run


def guarded_callback(callback: Callback, allowed_chats: frozenset[int]) -> Handler:
    """Wrap a plugin's button handler: allow-list, always answer the query, never crash."""
    async def run(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        query = update.callback_query
        chat = update.effective_chat
        if allowed_chats and (not chat or chat.id not in allowed_chats):
            await query.answer()
            return
        try:
            await callback.handler(update, context)
        except Exception:
            log.exception("callback %s failed", query.data)
            await query.answer("😵 Qualcosa è andato storto.", show_alert=True)
            return
        try:
            await query.answer()   # no-op if the handler already answered
        except Exception:
            pass
    return run


def help_text(plugins: list[Plugin]) -> str:
    lines = ["🔮 <b>Eden</b>", ""]
    for p in plugins:
        lines.append(f"<b>{html.escape(p.description)}</b>")
        for c in p.commands:
            usage = f" {html.escape(c.usage)}" if c.usage else ""
            lines.append(f"/{c.name}{usage} — {html.escape(c.description)}")
        lines.append("")
    lines.append(f"<i>v{__version__}</i>")
    return "\n".join(lines)


def build(cfg: Config, plugins: list[Plugin]) -> Application:
    commands = [c for p in plugins for c in p.commands]

    async def post_init(app: Application) -> None:
        # The menu shown when typing "/" in Telegram, generated from the plugins
        await app.bot.set_my_commands([BotCommand(c.name, c.description) for c in commands] +
                                      [BotCommand("help", "Cosa so fare")])
        try:   # the profile shown in Telegram before the first /start
            await app.bot.set_my_short_description(SHORT_DESCRIPTION)
            await app.bot.set_my_description(DESCRIPTION)
        except Exception:
            log.warning("could not set the bot description", exc_info=True)
        log.info("Eden v%s started: %s", __version__, ", ".join(f"/{c.name}" for c in commands))

    app = Application.builder().token(cfg.token).post_init(post_init).build()
    # In groups, /cmd@thisbot is matched automatically by CommandHandler
    chats = filters.Chat(chat_id=list(cfg.allowed_chats)) if cfg.allowed_chats else filters.ALL
    cooldown = Cooldown(cfg.cooldown)
    text = help_text(plugins)

    async def show_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        await update.effective_message.reply_text(text, parse_mode=ParseMode.HTML)

    app.add_handler(CommandHandler(["start", "help"], show_help, filters=chats))
    for c in commands:
        app.add_handler(CommandHandler(c.name, guarded(c, cooldown), filters=chats))
    for cb in (cb for p in plugins for cb in p.callbacks):
        app.add_handler(CallbackQueryHandler(guarded_callback(cb, frozenset(cfg.allowed_chats)),
                                             pattern=f"^{cb.prefix}:"))
    return app


def main() -> None:
    cfg = load()
    logging.basicConfig(format="%(asctime)s %(levelname)s %(name)s %(message)s", level=cfg.log_level)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    app = build(cfg, discover())
    # Polling: no public endpoint needed. Starting it also deletes any webhook (the AWS Lambda one).
    app.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)
