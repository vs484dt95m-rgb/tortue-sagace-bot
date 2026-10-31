
import os
import logging
from pathlib import Path

from fastapi import FastAPI, Request, HTTPException
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
WEBHOOK_SECRET = os.environ.get("WEBHOOK_SECRET", "")

app = FastAPI()

telegram_app = Application.builder().token(TOKEN).build()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Bonjour ! Je suis Tortue Sagace 🐢\n\n"
        "Ton assistant documentaire consacré à L'Avenir en commun.\n\n"
        "Pose-moi tes questions sur les retraites, "
        "les salaires, l'écologie, l'économie, la santé "
        "ou les institutions.\n\n"
        "Utilise /aide pour découvrir mes fonctionnalités."
    )


async def aide(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Pose-moi tes questions avec tes propres mots.\n\n"
        "Je recherche les réponses dans ma documentation."
    )


telegram_app.add_handler(CommandHandler("start", start))
telegram_app.add_handler(CommandHandler("aide", aide))


@app.on_event("startup")
async def startup():
    await telegram_app.initialize()
    await telegram_app.start()

    external_url = os.environ["RENDER_EXTERNAL_URL"]

    await telegram_app.bot.set_webhook(
        url=external_url.rstrip("/") + "/telegram",
        secret_token=WEBHOOK_SECRET or None
    )

    logger.info("Tortue Sagace est démarré")


@app.on_event("shutdown")
async def shutdown():
    await telegram_app.stop()
    await telegram_app.shutdown()


@app.get("/")
async def health():
    return {
        "status": "ok",
        "bot": "Tortue Sagace"
    }


@app.post("/telegram")
async def telegram_webhook(request: Request):

    if WEBHOOK_SECRET:
        supplied_secret = request.headers.get(
            "X-Telegram-Bot-Api-Secret-Token"
        )

        if supplied_secret != WEBHOOK_SECRET:
            raise HTTPException(status_code=403)

    data = await request.json()

    update = Update.de_json(data, telegram_app.bot)

    await telegram_app.process_update(update)

    return {"ok": True}
