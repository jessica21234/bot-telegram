from config import TOKEN, CANAL_NOM, ADMIN1, ADMIN2, ADMIN3, CHANNEL_ID 
import asyncio
import logging
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

# ─── LOGGING ─────────────────────────────────────────────────────────────────

logging.basicConfig(
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    level=logging.INFO,
    handlers=[logging.StreamHandler(sys.stdout)],
)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("telegram.ext").setLevel(logging.WARNING)
logger = logging.getLogger("BOT")

# ─── CONFIG ──────────────────────────────────────────────────────────────────

TOKEN      = os.environ.get("TOKEN", "")
CHANNEL_ID = os.environ.get("CHANNEL_ID", "")   # ex: @moncanal  OU  -1001234567890
CANAL_NOM  = os.environ.get("CANAL_NOM", "Notre Serveur")
ADMIN1     = os.environ.get("ADMIN1", "@irk14")
ADMIN2     = os.environ.get("ADMIN2", "@ilyan_dugafe")

# ─── TEXTE & CLAVIER ─────────────────────────────────────────────────────────

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

# ─── ENVOI DU MESSAGE ────────────────────────────────────────────────────────

async def envoyer_message_canal(bot: Bot):
    logger.info("=" * 50)
    logger.info("Tentative d'envoi du message dans le canal...")
    logger.info(f"CHANNEL_ID utilisé : '{CHANNEL_ID}'")

    if not CHANNEL_ID:
        logger.error("CHANNEL_ID est vide ! Ajoute-le dans tes variables d'environnement.")
        return

    # Test : est-ce que le bot peut accéder au canal ?
    try:
        chat = await bot.get_chat(CHANNEL_ID)
        logger.info(f"Canal trouvé : {chat.title} (id={chat.id})")
    except TelegramError as e:
        logger.error(f"Impossible d'accéder au canal : {e}")
        logger.error("=> Vérifie que le bot est ADMIN du canal et que CHANNEL_ID est correct.")
        return

    # Envoi du message
    for attempt in range(3):
        try:
            msg = await bot.send_message(
                chat_id=CHANNEL_ID,
                text=texte_canal(),
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=kb_canal(),
            )
            logger.info(f"Message envoyé avec succès ! (message_id={msg.message_id})")

            # Épingler
            try:
                await bot.pin_chat_message(
                    chat_id=CHANNEL_ID,
                    message_id=msg.message_id,
                    disable_notification=True,
                )
                logger.info("Message épinglé ✅")
            except TelegramError as e:
                logger.warning(f"Épinglage échoué (le bot a-t-il le droit d'épingler ?) : {e}")

            logger.info("=" * 50)
            return  # Succès, on arrête

        except RetryAfter as e:
            logger.warning(f"Rate limit Telegram, attente {e.retry_after}s...")
            await asyncio.sleep(e.retry_after + 1)

        except Forbidden as e:
            logger.error(f"Accès refusé : {e}")
            logger.error("=> Le bot est-il admin du canal avec droit d'envoyer des messages ?")
            return

        except TelegramError as e:
            logger.error(f"Erreur Telegram (tentative {attempt+1}/3) : {e}")
            if attempt < 2:
                await asyncio.sleep(3)

    logger.error("Échec après 3 tentatives.")
    logger.info("=" * 50)

# ─── BOUTONS ─────────────────────────────────────────────────────────────────

async def on_bouton(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data  = query.data
    user  = query.from_user

    logger.info(f"Bouton '{data}' cliqué par {user.first_name} ({user.id})")

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

# ─── SUPPRIME LES MESSAGES "X A REJOINT" ─────────────────────────────────────

async def on_new_member_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message and update.message.new_chat_members:
        try:
            await update.message.delete()
            logger.info("Message système 'X a rejoint' supprimé.")
        except Exception as e:
            logger.warning(f"Suppression message système échouée : {e}")

# ─── POST_INIT : lancé une seule fois au démarrage ───────────────────────────

async def post_init(application: Application):
    logger.info("Bot démarré, envoi du message unique...")
    await envoyer_message_canal(application.bot)

# ─── MAIN ────────────────────────────────────────────────────────────────────

def main():
    # Vérifications au démarrage
    if not TOKEN:
        logger.critical("TOKEN manquant ! Ajoute TOKEN dans tes variables d'environnement.")
        sys.exit(1)

    logger.info("=" * 50)
    logger.info("DÉMARRAGE DU BOT")
    logger.info(f"  CANAL_NOM  : {CANAL_NOM}")
    logger.info(f"  CHANNEL_ID : {CHANNEL_ID if CHANNEL_ID else '⚠️  MANQUANT'}")
    logger.info(f"  ADMIN1     : {ADMIN1}")
    logger.info(f"  ADMIN2     : {ADMIN2}")
    logger.info(f"  TOKEN      : {'✅ présent' if TOKEN else '❌ manquant'}")
    logger.info("=" * 50)

    app = (
        Application.builder()
        .token(TOKEN)
        .post_init(post_init)
        .build()
    )

    app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, on_new_member_message))
    app.add_handler(CallbackQueryHandler(on_bouton))

    logger.info("Bot en écoute des boutons...")
    app.run_polling(
        allowed_updates=[Update.MESSAGE, Update.CALLBACK_QUERY],
        drop_pending_updates=True,
    )

if __name__ == "__main__":
    main()
