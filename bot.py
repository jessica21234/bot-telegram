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
CHANNEL_ID = os.environ.get("CHANNEL_ID", "")   # ex: @moncanal  OU  -1001234567890
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


def _esc(text: str) -> str:
    """Échappe les caractères spéciaux pour MarkdownV2."""
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
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("💎 Obtenir le Premium", callback_data="premium")],
        [InlineKeyboardButton("🎥 Contenu gratuit",    callback_data="gratuit")],
    ])


def normaliser_channel_id(channel_id: str) -> str | int:
    """
    Convertit CHANNEL_ID en int si c'est un ID numérique,
    sinon s'assure que le username commence bien par @.
    """
    cid = channel_id.strip()
    # ID numérique (peut commencer par - pour les supergroups/canaux)
    if cid.lstrip("-").isdigit():
        return int(cid)
    # Username : s'assurer qu'il y a un @
    if not cid.startswith("@"):
        cid = "@" + cid
    return cid


async def envoyer_message_canal(bot: Bot):
    if not CHANNEL_ID:
        logger.error("CHANNEL_ID vide, abandon.")
        return

    chat_id = normaliser_channel_id(CHANNEL_ID)
    logger.info(f"Envoi dans CHANNEL_ID='{chat_id}'")

    try:
        chat = await bot.get_chat(chat_id)
        logger.info(f"Canal trouvé : {chat.title}")
    except TelegramError as e:
        logger.error(
            f"Canal inaccessible : {e}\n"
            f"  → Vérifie que le bot est ADMIN du canal avec la permission 'Publier des messages'."
        )
        return

    try:
        msg = await bot.send_message(
            chat_id=chat_id,
            text=texte_canal(),
            parse_mode=ParseMode.MARKDOWN_V2,   # MarkdownV2 au lieu de Markdown v1
            reply_markup=kb_canal(),
        )
        logger.info(f"Message envoyé (id={msg.message_id}) ✅")
        try:
            await bot.pin_chat_message(
                chat_id=chat_id,
                message_id=msg.message_id,
                disable_notification=True,
            )
            logger.info("Épinglé ✅")
        except TelegramError as e:
            logger.warning(f"Pin échoué (bot admin avec permission épingle ?) : {e}")
    except RetryAfter as e:
        logger.warning(f"Rate-limit, attente {e.retry_after}s...")
        await asyncio.sleep(e.retry_after + 1)
        await envoyer_message_canal(bot)   # retry
    except Forbidden as e:
        logger.error(
            f"Accès refusé : {e}\n"
            f"  → Le bot doit être ADMIN du canal."
        )
    except TelegramError as e:
        logger.error(f"Erreur envoi : {e}")


async def on_bouton(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()   # accusé de réception immédiat (obligatoire)

    if query.data == "premium":
        # query.answer() est limité à 200 chars → on envoie le détail en DM
        try:
            await context.bot.send_message(
                chat_id=query.from_user.id,
                text=(
                    f"💎 *Accès Premium — 4,99€ à vie*\n\n"
                    f"Pour finaliser ton accès, contacte un admin en DM :\n\n"
                    f"👤 {ADMIN1}\n"
                    f"👤 {ADMIN2}\n\n"
                    f"Dis\\-leur : « Je veux le Premium » 🙌"
                ),
                parse_mode=ParseMode.MARKDOWN_V2,
            )
        except Forbidden:
            # L'utilisateur n'a pas encore démarré le bot en privé
            await query.answer(
                f"Contacte {ADMIN1} ou {ADMIN2} en DM pour le Premium (4,99€ à vie) !",
                show_alert=True,
            )

    elif query.data == "gratuit":
        await query.answer(
            "🎥 Fais défiler vers le haut — tout le contenu gratuit est là !",
            show_alert=True,
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

    if not CHANNEL_ID:
        logger.critical("CHANNEL_ID manquant !")
        sys.exit(1)

    app = (
        Application.builder()
        .token(TOKEN)
        .post_init(post_init)
        .build()
    )

    app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, on_new_member_message))
    app.add_handler(CallbackQueryHandler(on_bouton))

    logger.info("Bot démarré, en attente de mises à jour...")
    app.run_polling(
        allowed_updates=[Update.MESSAGE, Update.CALLBACK_QUERY],
        drop_pending_updates=True,
    )


if __name__ == "__main__":
    main()
