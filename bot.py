import asyncio
import logging
import os
import sys

from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ParseMode
from telegram.error import Forbidden, RetryAfter, TelegramError
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

logging.basicConfig(
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    level=logging.INFO,
    handlers=[logging.StreamHandler(sys.stdout)],
)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("telegram.ext").setLevel(logging.WARNING)
logger = logging.getLogger("BOT")

TOKEN      = os.environ.get("TOKEN", "")
CHANNEL_ID = os.environ.get("CHANNEL_ID", "")
CANAL_NOM  = os.environ.get("CANAL_NOM", "Notre Serveur")
ADMIN1     = os.environ.get("ADMIN1", "@irk14")
ADMIN2     = os.environ.get("ADMIN2", "@ilyan_dugafe")

logger.info("=== VARIABLES CHARGÉES ===")
logger.info(f"TOKEN      : {'OK' if TOKEN else 'MANQUANT'}")
logger.info(f"CHANNEL_ID : {CHANNEL_ID if CHANNEL_ID else 'MANQUANT'}")
logger.info(f"CANAL_NOM  : {CANAL_NOM}")
logger.info(f"ADMIN1     : {ADMIN1}")
logger.info(f"ADMIN2     : {ADMIN2}")
logger.info("==========================")


def texte_canal() -> str:
    return (
        f"👋 *Bienvenue sur {CANAL_NOM} !*\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"🎥 *Contenu gratuit*\n"
        f"Fais défiler vers le haut — tout est disponible gratuitement !\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"💎 *Accès PREMIUM — 4,99€ à vie*\n\n"
        f"✅ Contenu exclusif\n"
        f"✅ Vidéos & ressources premium\n"
        f"✅ Mises à jour régulières\n"
        f"✅ Paiement unique, zéro abonnement\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"👇 *Clique sur un bouton ci-dessous*"
    )


def kb_canal() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("💎 Obtenir le Premium", callback_data="premium")],
        [InlineKeyboardButton("🎥 Contenu gratuit",    callback_data="gratuit")],
    ])


async def envoyer_message_canal(bot: Bot):
    logger.info(f"Envoi dans CHANNEL_ID='{CHANNEL_ID}'")

    if not CHANNEL_ID:
        logger.error("CHANNEL_ID vide, abandon.")
        return

    try:
        chat = await bot.get_chat(CHANNEL_ID)
        logger.info(f"Canal trouvé : {chat.title}")
    except TelegramError as e:
        logger.error(f"Canal inaccessible : {e}")
        return

    try:
        msg = await bot.send_message(
            chat_id=CHANNEL_ID,
            text=texte_canal(),
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=kb_canal(),
        )
        logger.info(f"Message envoyé (id={msg.message_id}) ✅")
        try:
            await bot.pin_chat_message(chat_id=CHANNEL_ID, message_id=msg.message_id, disable_notification=True)
            logger.info("Épinglé ✅")
        except TelegramError as e:
            logger.warning(f"Pin échoué : {e}")
    except RetryAfter as e:
        await asyncio.sleep(e.retry_after + 1)
    except Forbidden as e:
        logger.error(f"Accès refusé (bot admin du canal ?) : {e}")
    except TelegramError as e:
        logger.error(f"Erreur envoi : {e}")


async def on_bouton(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query.data == "premium":
        await query.answer(
            f"💎 Pour le Premium (4,99€ à vie), contacte un admin en DM :\n\n"
            f"{ADMIN1}\n{ADMIN2}\n\n"
            f"Dis-leur : « Je veux le Premium » 🙌",
            show_alert=True,
        )
    elif query.data == "gratuit":
        await query.answer(
            "🎥 Fais défiler vers le haut — tout le contenu gratuit est là !",
            show_alert=False,
        )


async def on_new_member_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message and update.message.new_chat_members:
        try:
            await update.message.delete()
        except Exception:
            pass


async def post_init(application: Application):
    await envoyer_message_canal(application.bot)


def main():
    if not TOKEN:
        logger.critical("TOKEN manquant !")
        sys.exit(1)

    app = (
        Application.builder()
        .token(TOKEN)
        .post_init(post_init)
        .build()
    )

    app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, on_new_member_message))
    app.add_handler(CallbackQueryHandler(on_bouton))

    app.run_polling(
        allowed_updates=[Update.MESSAGE, Update.CALLBACK_QUERY],
        drop_pending_updates=True,
    )


if __name__ == "__main__":
    main()
