import asyncio
import logging
import os
import sys
from datetime import datetime

from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ChatMemberStatus, ParseMode
from telegram.error import BadRequest, Forbidden, RetryAfter, TelegramError
from telegram.ext import (
    Application, CallbackQueryHandler, ChatMemberHandler,
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

TOKEN       = os.environ.get("TOKEN", "")
CHANNEL_ID  = os.environ.get("CHANNEL_ID", "")
CANAL_NOM   = os.environ.get("CANAL_NOM", "Notre Serveur")
ADMIN1      = os.environ.get("ADMIN1", "@irk14")
ADMIN2      = os.environ.get("ADMIN2", "@ilyan_dugafe")
INTERVAL    = int(os.environ.get("INTERVAL_SECONDS", "3600"))

pinned_message_id: int | None = None


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
        except (Forbidden, TelegramError) as e:
            logger.error(f"send [{attempt+1}/3]: {e}")
            return None
    return None


def texte_canal() -> str:
    ts = datetime.now().strftime("%d/%m/%Y à %H:%M")
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
        f"👇 *Clique sur un bouton pour en savoir plus*\n\n"
        f"🕐 _Mis à jour : {ts}_"
    )


def kb_canal() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("💎 Obtenir le Premium", callback_data="premium")],
        [InlineKeyboardButton("🎥 Contenu gratuit",    callback_data="gratuit")],
    ])


async def poster_message_canal(bot: Bot):
    global pinned_message_id

    if not CHANNEL_ID:
        logger.warning("CHANNEL_ID non défini.")
        return

    if pinned_message_id:
        await safe_delete(bot, CHANNEL_ID, pinned_message_id)
        pinned_message_id = None

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
    logger.info(f"Message posté (id={pinned_message_id})")

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
        await poster_message_canal(bot)
        await asyncio.sleep(INTERVAL)


# ── Supprime juste les messages système "X a rejoint" ─────────────────────────

async def on_chat_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Supprime silencieusement le message système quand quelqu'un rejoint."""
    result = update.chat_member
    if not result:
        return
    LEFT   = {ChatMemberStatus.BANNED, ChatMemberStatus.LEFT, ChatMemberStatus.RESTRICTED}
    JOINED = {ChatMemberStatus.MEMBER, ChatMemberStatus.OWNER, ChatMemberStatus.ADMINISTRATOR}
    if result.old_chat_member.status in LEFT and result.new_chat_member.status in JOINED:
        if not result.new_chat_member.user.is_bot:
            logger.info(f"Nouveau membre : {result.new_chat_member.user.full_name} — aucun message envoyé.")


async def on_new_member_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Supprime le message système 'X a rejoint le groupe', c'est tout."""
    if update.message and update.message.new_chat_members:
        await safe_delete(context.bot, update.effective_chat.id, update.message.message_id)


# ── Boutons ───────────────────────────────────────────────────────────────────

async def on_bouton(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data  = query.data
    user  = query.from_user

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


# ── Commande admin ────────────────────────────────────────────────────────────

async def cmd_post(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await poster_message_canal(context.bot)
    await update.message.reply_text("✅ Message re-posté.")


async def post_init(application: Application):
    asyncio.create_task(boucle_canal(application.bot))


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
