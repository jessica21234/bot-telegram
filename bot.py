"""
1 message dans le canal, boutons avec réponses éphémères (visibles que par le cliqueur)
"""

import asyncio
import logging
import os
import sys
from datetime import datetime

from telegram import (
    Bot,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Update,
)
from telegram.constants import ChatMemberStatus, ParseMode
from telegram.error import BadRequest, Forbidden, RetryAfter, TelegramError
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    ChatMemberHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

# ─── LOGGING ──────────────────────────────────────────────────────────────────

logging.basicConfig(
    format="%(asctime)s │ %(levelname)-8s │ %(message)s",
    level=logging.INFO,
    handlers=[logging.StreamHandler(sys.stdout)],
)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("telegram").setLevel(logging.WARNING)
logger = logging.getLogger("BOT")

# ─── CONFIG ───────────────────────────────────────────────────────────────────

TOKEN        = os.environ.get("TOKEN", "")
CHANNEL_ID   = os.environ.get("CHANNEL_ID", "")  # @canal ou -100xxx
CANAL_NOM    = os.environ.get("CANAL_NOM", "Notre Serveur")
ADMIN1       = os.environ.get("ADMIN1", "@irk14")
ADMIN2       = os.environ.get("ADMIN2", "@ilyan_dugafe")
INTERVAL     = int(os.environ.get("INTERVAL_SECONDS", "3600"))

# ─── ÉTAT ─────────────────────────────────────────────────────────────────────

pinned_message_id: int | None = None
membres_accueillis: set[int] = set()

# ─── HELPERS ──────────────────────────────────────────────────────────────────

async def safe_delete(bot: Bot, chat_id, message_id: int):
    try:
        await bot.delete_message(chat_id=chat_id, message_id=message_id)
    except Exception:
        pass


async def safe_send(bot: Bot, chat_id, text: str, **kwargs):
    for attempt in range(3):
        try:
            return await bot.send_message(chat_id=chat_id, text=text, **kwargs)
        except RetryAfter as e:
            await asyncio.sleep(e.retry_after + 1)
        except Forbidden:
            return None
        except TelegramError as e:
            logger.error(f"send [{attempt+1}/3]: {e}")
            return None
    return None

# ─── TEXTES ───────────────────────────────────────────────────────────────────

def texte_canal() -> str:
    ts = datetime.now().strftime("%d/%m/%Y à %H:%M")
    return (
        f"📌 *BIENVENUE SUR {CANAL_NOM.upper()} !*\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"🎥 *Contenu gratuit*\n"
        f"Tout le contenu gratuit est disponible — fais défiler vers le haut !\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"💎 *Accès PREMIUM — 4,99€ à vie*\n\n"
        f"✅ Tout le contenu exclusif\n"
        f"✅ Vidéos & ressources premium\n"
        f"✅ Mises à jour régulières\n"
        f"✅ Paiement unique, zéro abonnement\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"👇 *Clique sur un bouton pour en savoir plus*\n\n"
        f"🕐 _Mis à jour : {ts}_"
    )

# ─── CLAVIER ──────────────────────────────────────────────────────────────────

def kb_canal() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("💎 Obtenir le Premium", callback_data="premium")],
        [InlineKeyboardButton("🎥 Contenu gratuit",    callback_data="gratuit")],
    ])

# ─── POST MESSAGE CANAL ───────────────────────────────────────────────────────

async def poster_message_canal(bot: Bot):
    global pinned_message_id

    if not CHANNEL_ID:
        logger.warning("CHANNEL_ID non défini.")
        return

    # Supprimer l'ancien message
    if pinned_message_id:
        await safe_delete(bot, CHANNEL_ID, pinned_message_id)
        pinned_message_id = None

    # Poster le nouveau
    msg = await safe_send(
        bot, CHANNEL_ID,
        texte_canal(),
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=kb_canal(),
    )
    if not msg:
        logger.error("Échec du post canal.")
        return

    pinned_message_id = msg.message_id
    logger.info(f"Message canal posté (id={pinned_message_id})")

    # Épingler
    try:
        await bot.pin_chat_message(
            chat_id=CHANNEL_ID,
            message_id=pinned_message_id,
            disable_notification=True,
        )
        logger.info("Épinglé ✅")
    except TelegramError as e:
        logger.warning(f"Pin échoué : {e}")


async def boucle_canal(bot: Bot):
    while True:
        logger.info(f"─── Re-post ({datetime.now().strftime('%H:%M')}) ───")
        await poster_message_canal(bot)
        await asyncio.sleep(INTERVAL)

# ─── HANDLER : BOUTONS ────────────────────────────────────────────────────────

async def on_bouton(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data  = query.data
    user  = query.from_user

    logger.info(f"Bouton '{data}' — {user.first_name} ({user.id})")

    if data == "premium":
        # Réponse éphémère avec alerte modale — visible UNIQUEMENT par celui qui clique
        await query.answer(
            f"💎 Pour obtenir le Premium (4,99€ à vie), contacte un admin en DM :\n\n"
            f"{ADMIN1}\n"
            f"{ADMIN2}\n\n"
            f"Dis-leur juste : « Je veux le Premium » 🙌",
            show_alert=True,   # pop-up modal, personne d'autre ne voit rien
        )

    elif data == "gratuit":
        # Juste fermer le spinner, rien d'autre — le canal reste intact
        await query.answer(
            "🎥 Fais défiler vers le haut — tout le contenu gratuit est déjà là !",
            show_alert=False,  # toast discret en bas de l'écran, invisible pour les autres
        )

# ─── HANDLER : NOUVEAU MEMBRE ─────────────────────────────────────────────────

async def on_chat_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    result = update.chat_member
    if not result:
        return

    LEFT   = {ChatMemberStatus.BANNED, ChatMemberStatus.LEFT, ChatMemberStatus.RESTRICTED}
    JOINED = {ChatMemberStatus.MEMBER, ChatMemberStatus.OWNER, ChatMemberStatus.ADMINISTRATOR}

    user = result.new_chat_member.user
    if user.is_bot:
        return
    if result.old_chat_member.status not in LEFT:
        return
    if result.new_chat_member.status not in JOINED:
        return
    if user.id in membres_accueillis:
        return

    membres_accueillis.add(user.id)
    logger.info(f"Nouveau : {user.full_name} ({user.id})")

    await safe_send(
        context.bot,
        result.chat.id,
        f"👋 Bienvenue *{user.first_name}* sur *{CANAL_NOM}* !\nClique sur le message épinglé 📌 pour tout découvrir.",
        parse_mode=ParseMode.MARKDOWN,
    )


async def on_new_member_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.new_chat_members:
        return

    for user in update.message.new_chat_members:
        if user.is_bot:
            continue
        if user.id in membres_accueillis:
            continue
        membres_accueillis.add(user.id)

        await safe_delete(context.bot, update.effective_chat.id, update.message.message_id)
        await safe_send(
            context.bot,
            update.effective_chat.id,
            f"👋 Bienvenue *{user.first_name}* sur *{CANAL_NOM}* !\nClique sur le message épinglé 📌 pour tout découvrir.",
            parse_mode=ParseMode.MARKDOWN,
        )

# ─── COMMANDES ────────────────────────────────────────────────────────────────

async def cmd_post(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await poster_message_canal(context.bot)
    await update.message.reply_text("✅ Message re-posté.")

# ─── POST_INIT ────────────────────────────────────────────────────────────────

async def post_init(application: Application):
    asyncio.create_task(boucle_canal(application.bot))

# ─── MAIN ─────────────────────────────────────────────────────────────────────

def main():
    if not TOKEN:
        logger.critical("TOKEN manquant !")
        sys.exit(1)

    logger.info(f"Canal: {CANAL_NOM} | Channel: {CHANNEL_ID} | Admins: {ADMIN1}, {ADMIN2} | Interval: {INTERVAL}s")

    app = (
        Application.builder()
        .token(TOKEN)
        .post_init(post_init)
        .build()
    )

    app.add_handler(CommandHandler("post", cmd_post))
    app.add_handler(ChatMemberHandler(on_chat_member, ChatMemberHandler.CHAT_MEMBER))
    app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, on_new_member_message))
    app.add_handler(CallbackQueryHandler(on_bouton))

    logger.info("✅ Bot en écoute !")
    app.run_polling(
        allowed_updates=[Update.MESSAGE, Update.CALLBACK_QUERY, Update.CHAT_MEMBER],
        drop_pending_updates=True,
    )

if __name__ == "__main__":
    main()
