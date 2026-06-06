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
CHANNEL_ID = os.environ.get("CHANNEL_ID", "").strip()
CANAL_NOM  = os.environ.get("CANAL_NOM", "Notre Serveur")
ADMIN1     = os.environ.get("ADMIN1", "@irk14")
ADMIN2     = os.environ.get("ADMIN2", "@ilyan_dugafe")
BOT_USERNAME = os.environ.get("BOT_USERNAME", "")  # ex: monbot (sans @)

logger.info("=== VARIABLES CHARGÉES ===")
logger.info(f"TOKEN        : {'OK' if TOKEN else 'MANQUANT'}")
logger.info(f"CHANNEL_ID   : {repr(CHANNEL_ID)}")
logger.info(f"CANAL_NOM    : {CANAL_NOM}")
logger.info(f"BOT_USERNAME : {BOT_USERNAME}")
logger.info(f"ADMIN1       : {ADMIN1}")
logger.info(f"ADMIN2       : {ADMIN2}")
logger.info("==========================")


def _esc(text: str) -> str:
    special = r"\_*[]()~`>#+-=|{}.!"
    return "".join(f"\\{c}" if c in special else c for c in text)


def texte_canal() -> str:
    nom = _esc(CANAL_NOM)
    return (
        f"👋 *Bienvenue sur {nom} \\!*\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"🎥 *Contenu gratuit*\n"
        f"Fais défiler vers le haut — tout est disponible gratuitement \\!\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"💎 *Accès PREMIUM — 4,99€ à vie*\n\n"
        f"✅ Contenu exclusif\n"
        f"✅ Vidéos & ressources premium\n"
        f"✅ Mises à jour régulières\n"
        f"✅ Paiement unique, zéro abonnement\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"👇 *Clique sur un bouton ci\\-dessous*"
    )


def kb_canal() -> InlineKeyboardMarkup:
    # Boutons URL → ouvrent le bot en DM directement, pas de callback
    admin1_clean = ADMIN1.lstrip("@")
    admin2_clean = ADMIN2.lstrip("@")

    # Lien vers le bot avec commande start encodée
    if BOT_USERNAME:
        premium_url = f"https://t.me/{BOT_USERNAME.lstrip('@')}?start=premium"
    else:
        # Fallback : lien direct vers admin1
        premium_url = f"https://t.me/{admin1_clean}"

    return InlineKeyboardMarkup([
        [InlineKeyboardButton("💎 Obtenir le Premium", url=premium_url)],
        [InlineKeyboardButton("🎥 Contenu gratuit", url=f"https://t.me/{CHANNEL_ID.lstrip('@')}")],
    ])


def normaliser_channel_id(channel_id: str):
    cid = channel_id.strip()
    if cid.lstrip("-").isdigit():
        return int(cid)
    if not cid.startswith("@"):
        cid = "@" + cid
    return cid


async def envoyer_message_canal(bot: Bot):
    channel_id = os.environ.get("CHANNEL_ID", "").strip()
    if not channel_id:
        logger.error("CHANNEL_ID vide.")
        return

    chat_id = normaliser_channel_id(channel_id)
    logger.info(f"Envoi → {chat_id!r}")

    try:
        chat = await bot.get_chat(chat_id)
        logger.info(f"Canal trouvé : {chat.title}")
    except TelegramError as e:
        logger.error(f"Canal inaccessible : {e}")
        return

    try:
        msg = await bot.send_message(
            chat_id=chat_id,
            text=texte_canal(),
            parse_mode=ParseMode.MARKDOWN_V2,
            reply_markup=kb_canal(),
        )
        logger.info(f"Message envoyé (id={msg.message_id}) ✅")
        try:
            await bot.pin_chat_message(chat_id=chat_id, message_id=msg.message_id, disable_notification=True)
            logger.info("Épinglé ✅")
        except TelegramError as e:
            logger.warning(f"Pin échoué : {e}")
    except RetryAfter as e:
        await asyncio.sleep(e.retry_after + 1)
        await envoyer_message_canal(bot)
    except Forbidden as e:
        logger.error(f"Accès refusé : {e}")
    except TelegramError as e:
        logger.error(f"Erreur envoi : {e}")


# Gestion du /start premium en DM
async def on_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return

    args = context.args
    if args and args[0] == "premium":
        admin1_clean = ADMIN1.lstrip("@")
        admin2_clean = ADMIN2.lstrip("@")
        await update.message.reply_text(
            f"💎 *Accès Premium — 4,99€ à vie*\n\n"
            f"Pour finaliser ton accès, contacte un admin :\n\n"
            f"👤 [{_esc(ADMIN1)}](https://t.me/{admin1_clean})\n"
            f"👤 [{_esc(ADMIN2)}](https://t.me/{admin2_clean})\n\n"
            f"Dis\\-leur : « Je veux le Premium » 🙌",
            parse_mode=ParseMode.MARKDOWN_V2,
        )
    else:
        await update.message.reply_text(
            f"👋 Bienvenue \\! Rejoins notre canal : @{CHANNEL_ID.lstrip('@')}",
            parse_mode=ParseMode.MARKDOWN_V2,
        )


async def on_new_member_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message and update.message.new_chat_members:
        try:
            await update.message.delete()
        except Exception:
            pass


async def post_init(application: Application):
    # Récupère le username du bot automatiquement si pas défini
    global BOT_USERNAME
    if not BOT_USERNAME:
        me = await application.bot.get_me()
        BOT_USERNAME = me.username or ""
        logger.info(f"BOT_USERNAME auto-détecté : @{BOT_USERNAME}")
    await envoyer_message_canal(application.bot)


def main():
    if not TOKEN:
        logger.critical("TOKEN manquant !")
        sys.exit(1)

    from telegram.ext import CommandHandler

    app = (
        Application.builder()
        .token(TOKEN)
        .post_init(post_init)
        .build()
    )

    app.add_handler(CommandHandler("start", on_start))
    app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, on_new_member_message))
    app.add_handler(CallbackQueryHandler(lambda u, c: None))  # ignore callbacks résiduels

    logger.info("Bot démarré ✅")
    app.run_polling(
        allowed_updates=[Update.MESSAGE, Update.CALLBACK_QUERY],
        drop_pending_updates=True,
    )


if __name__ == "__main__":
    main()
