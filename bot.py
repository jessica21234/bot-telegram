import asyncio
import logging
import os
import sys

from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ParseMode
from telegram.error import Forbidden, RetryAfter, TelegramError
from telegram.ext import (
    Application, CallbackQueryHandler,
    CommandHandler, ContextTypes, MessageHandler, filters,
)

logging.basicConfig(
    format="%(asctime)s │ %(levelname)-8s │ %(message)s",
    level=logging.INFO,
    handlers=[logging.StreamHandler(sys.stdout)],
)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("telegram").setLevel(logging.WARNING)
logger = logging.getLogger("BOT")

TOKEN      = os.environ.get("TOKEN", "")
CHANNEL_ID = os.environ.get("CHANNEL_ID", "")
CANAL_NOM  = os.environ.get("CANAL_NOM", "Notre Serveur")
ADMIN1     = os.environ.get("ADMIN1", "@irk14")
ADMIN2     = os.environ.get("ADMIN2", "@ilyan_dugafe")


async def safe_send(bot: Bot, chat_id, text: str, **kwargs):
    for attempt in range(3):
        try:
            return await bot.send_message(chat_id=chat_id, text=text, **kwargs)
        except RetryAfter as e:
            await asyncio.sleep(e.retry_after + 1)
        except (Forbidden, TelegramError) as e:
            logger.error(f"send [{attempt+1}/3]: {e}")
            return None
    return None


def texte_canal() -> str:
    return (
        f"👋 *Bienvenue sur {CANAL_NOM} !*\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"🎥 *Contenu gratuit*\n"
        f"Fais défiler vers le haut — tout est disponible !\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"💎 *Accès PREMIUM — 4,99€ à vie*\n\n"
        f"✅ Contenu exclusif\n"
        f"✅ Vidéos & ressources premium\n"
        f"✅ Mises à jour régulières\n"
        f"✅ Paiement unique, zéro abonnement\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"👇 *Clique sur un bouton pour en savoir plus*"
    )


def kb_canal() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("💎 Obtenir le Premium", callback_data="premium")],
        [InlineKeyboardButton("🎥 Contenu gratuit",    callback_data="gratuit")],
    ])


async def on_bouton(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data  = query.data

    if data == "premium":
        await query.answer(
            f"💎 Pour le Premium (4,99€ à vie), contacte un admin en DM :\n\n"
            f"{ADMIN1}\n"
            f"{ADMIN2}\n\n"
            f"Dis-leur : « Je veux le Premium » 🙌",
            show_alert=True,
        )
    elif data == "gratuit":
        await query.answer(
            "🎥 Fais défiler vers le haut — tout le contenu gratuit est déjà là !",
            show_alert=False,
        )


async def on_new_member_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Supprime le message système 'X a rejoint', c'est tout."""
    if update.message and update.message.new_chat_members:
        try:
            await update.message.delete()
        except Exception:
            pass


async def post_init(application: Application):
    """Envoie le message UNE seule fois au démarrage, puis épingle."""
    bot = application.bot

    if not CHANNEL_ID:
        logger.warning("CHANNEL_ID non défini, message non envoyé.")
        return

    msg = await safe_send(
        bot, CHANNEL_ID,
        texte_canal(),
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=kb_canal(),
    )

    if msg:
        logger.info(f"Message envoyé une fois (id={msg.message_id}) ✅")
        try:
            await bot.pin_chat_message(
                chat_id=CHANNEL_ID,
                message_id=msg.message_id,
                disable_notification=True,
            )
            logger.info("Épinglé ✅")
        except TelegramError as e:
            logger.warning(f"Pin échoué : {e}")
    else:
        logger.error("Échec envoi message.")


def main():
    if not TOKEN:
        logger.critical("TOKEN manquant !")
        sys.exit(1)

    logger.info(f"Canal: {CANAL_NOM} | Channel: {CHANNEL_ID} | Admins: {ADMIN1}, {ADMIN2}")

    app = (
        Application.builder()
        .token(TOKEN)
        .post_init(post_init)
        .build()
    )

    app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, on_new_member_message))
    app.add_handler(CallbackQueryHandler(on_bouton))

    logger.info("✅ Bot en écoute !")
    app.run_polling(
        allowed_updates=[Update.MESSAGE, Update.CALLBACK_QUERY],
        drop_pending_updates=True,
    )

if __name__ == "__main__":
    main()
