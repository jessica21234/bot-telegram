import asyncio
import logging
import os
import sys

from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ParseMode
from telegram.error import Forbidden, RetryAfter, TelegramError
from telegram.ext import (
    Application,
    CommandHandler,
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
BOT_USERNAME = ""

# Fichier qui indique que le message a déjà été envoyé
SENT_FLAG = "/app/message_sent.flag"

logger.info("=== VARIABLES CHARGÉES ===")
logger.info(f"TOKEN      : {'OK' if TOKEN else 'MANQUANT'}")
logger.info(f"CHANNEL_ID : {repr(CHANNEL_ID)}")
logger.info(f"CANAL_NOM  : {CANAL_NOM}")
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
    bot_url = f"https://t.me/{BOT_USERNAME}?start=premium" if BOT_USERNAME else f"https://t.me/{ADMIN1.lstrip('@')}"
    canal_url = f"https://t.me/{CHANNEL_ID.lstrip('@')}"
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("💎 Obtenir le Premium", url=bot_url)],
        [InlineKeyboardButton("🎥 Contenu gratuit", url=canal_url)],
    ])


def normaliser_channel_id(channel_id: str):
    cid = channel_id.strip()
    if cid.lstrip("-").isdigit():
        return int(cid)
    return cid if cid.startswith("@") else "@" + cid


async def envoyer_message_canal(bot: Bot):
    # Si le flag existe → message déjà envoyé, on ne fait RIEN
    if os.path.exists(SENT_FLAG):
        logger.info("Message déjà envoyé (flag présent) — rien à faire ✅")
        return

    channel_id = os.environ.get("CHANNEL_ID", "").strip()
    if not channel_id:
        logger.error("CHANNEL_ID vide.")
        return

    chat_id = normaliser_channel_id(channel_id)

    try:
        chat = await bot.get_chat(chat_id)
        logger.info(f"Canal : {chat.title}")
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

        # Épingler
        try:
            await bot.pin_chat_message(chat_id=chat_id, message_id=msg.message_id, disable_notification=True)
            logger.info("Épinglé ✅")
        except TelegramError as e:
            logger.warning(f"Pin échoué : {e}")

        # Écrire le flag → plus jamais d'envoi
        with open(SENT_FLAG, "w") as f:
            f.write(str(msg.message_id))
        logger.info("Flag écrit — message ne sera plus jamais renvoyé ✅")

    except RetryAfter as e:
        await asyncio.sleep(e.retry_after + 1)
        await envoyer_message_canal(bot)
    except Forbidden as e:
        logger.error(f"Accès refusé : {e}")
    except TelegramError as e:
        logger.error(f"Erreur envoi : {e}")


async def on_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return
    args = context.args
    if args and args[0] == "premium":
        a1 = ADMIN1.lstrip("@")
        a2 = ADMIN2.lstrip("@")
        await update.message.reply_text(
            f"💎 *Accès Premium — 4,99€ à vie*\n\n"
            f"Contacte un admin :\n\n"
            f"👤 [{_esc(ADMIN1)}](https://t.me/{a1})\n"
            f"👤 [{_esc(ADMIN2)}](https://t.me/{a2})\n\n"
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
    global BOT_USERNAME
    me = await application.bot.get_me()
    BOT_USERNAME = me.username or ""
    logger.info(f"Bot username : @{BOT_USERNAME}")
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

    app.add_handler(CommandHandler("start", on_start))
    app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, on_new_member_message))

    logger.info("Bot démarré ✅")
    app.run_polling(
        allowed_updates=[Update.MESSAGE, Update.CALLBACK_QUERY],
        drop_pending_updates=True,
    )


if __name__ == "__main__":
    main()
