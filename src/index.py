# main.py
import json
import os
from telegram import Update, InputFile
from telegram.ext import Application, CommandHandler
from telegram.ext._contexttypes import ContextTypes
import asyncio
from commands.tarrot import extract_tarot_file


# Example handler
async def tarot(update, _: ContextTypes.DEFAULT_TYPE):
    with open(extract_tarot_file(), 'rb') as f:
        contents = f.read()
        await update.message.reply_photo(
            InputFile(contents)
        )
        f.close()

def lambda_handler(event=None, context=None):
    try:
        asyncio.run(run(event))
    except Exception as e:
        print(e)
        return {"statusCode": 500}

    return {"statusCode": 200}


async def run(event):
    BOT_TOKEN = os.environ.get('telegram_key')
    app = (
        Application.builder()
        .updater(None)
        .token(BOT_TOKEN)
        .build()
    )

    app.add_handler(CommandHandler("tarocco", tarot))
    message = json.loads(event['body'])
    print("Incoming:", message)

    await app.initialize()
    await app.start()
    await app.process_update(Update.de_json(message, app.bot))
    await app.stop()
    await app.shutdown()
