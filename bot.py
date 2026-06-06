"""
╔══════════════════════════════════════════════════════════╗
║           BOT TELEGRAM — BIENVENUE + MESSAGE BAS         ║
║   • Accueille chaque nouveau membre (DM ou groupe)       ║
║   • Maintient un message épinglé en bas du canal         ║
║   • Anti-doublon, retry automatique, zéro crash          ║
╚══════════════════════════════════════════════════════════╝

Variables d'environnement requises :
  TOKEN           → token du bot BotFather
  CHANNEL_ID      → @moncanal  ou  -100xxxxxxxx
  CANAL_NOM       → nom affiché dans les messages
  ADMIN1          → @pseudo1
  ADMIN2          → @pseudo2
  ADMIN3          → @pseudo3  (optionnel)
  PAYPAL_EMAIL    → email PayPal (optionnel, affiché si renseigné)
  INTERVAL_SECONDS→ intervalle re-post en secondes (défaut 3600)
  PIN_MSG         → "true" pour activer le message épinglé (défaut true)
  WELCOME_MSG     → "true" pour activer les bienvenus (défaut true)
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
    format="%(asctime)s │ %(levelname)-8s │ %(name)s │ %(message)s",
    level=logging.INFO,
    handlers=[logging.StreamHandler(sys.stdout)],
)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("telegram").setLevel(logging.WARNING)
logger = logging.getLogger("BOT")

# ─── CONFIG ───────────────────────────────────────────────────────────────────

TOKEN            = os.environ.get("TOKEN", "")
CHANNEL_ID       = os.environ.get("CHANNEL_ID", "")          # @canal ou -100xxx
CANAL_NOM        = os.environ.get("CANAL_NOM", "Notre Serveur")
ADMIN1           = os.environ.get("ADMIN1", "@irk14")
ADMIN2           = os.environ.get("ADMIN2", "@ilyan_dugafe")
ADMIN3           = os.environ.get("ADMIN3", "")
PAYPAL_EMAIL     = os.environ.get("PAYPAL_EMAIL", "")
INTERVAL         = int(os.environ.get("INTERVAL_SECONDS", "3600"))
FEATURE_PIN      = os.environ.get("PIN_MSG", "true").lower() == "true"
FEATURE_WELCOME  = os.environ.get("WELCOME_MSG", "true").lower() == "true"

# ─── ÉTAT GLOBAL ──────────────────────────────────────────────────────────────

membres_accueillis: set[int] = set()   # anti-doublon (session)
pinned_message_id: int | None = None   # dernier message épinglé

# ─── HELPERS ──────────────────────────────────────────────────────────────────

def admins_block() -> str:
    lines = [f"👤 {ADMIN1}", f"👤 {ADMIN2}"]
    if ADMIN3:
        lines.append(f"👤 {ADMIN3}")
    return "\n".join(lines)


async def safe_delete(bot: Bot, chat_id, message_id: int) -> bool:
    """Supprime un message sans lever d'exception."""
    try:
        await bot.delete_message(chat_id=chat_id, message_id=message_id)
        return True
    except BadRequest as e:
        if "Message to delete not found" in str(e):
            return True   # déjà supprimé, c'est ok
        logger.warning(f"delete_message – BadRequest : {e}")
    except TelegramError as e:
        logger.warning(f"delete_message – {type(e).__name__} : {e}")
    return False


async def safe_send(bot: Bot, chat_id, text: str, **kwargs) -> "Message | None":
    """Envoie un message avec gestion RetryAfter et erreurs courantes."""
    for attempt in range(3):
        try:
            return await bot.send_message(chat_id=chat_id, text=text, **kwargs)
        except RetryAfter as e:
            wait = e.retry_after + 1
            logger.warning(f"RetryAfter {wait}s (tentative {attempt+1}/3)")
            await asyncio.sleep(wait)
        except Forbidden:
            logger.info(f"DM bloqué pour chat_id={chat_id}")
            return None
        except TelegramError as e:
            logger.error(f"send_message – {type(e).__name__} : {e}")
            return None
    return None


async def safe_pin(bot: Bot, chat_id, message_id: int) -> bool:
    """Épingle un message sans lever d'exception."""
    try:
        await bot.pin_chat_message(
            chat_id=chat_id,
            message_id=message_id,
            disable_notification=True,
        )
        return True
    except TelegramError as e:
        logger.warning(f"pin_chat_message – {type(e).__name__} : {e}")
        return False


# ─── TEXTES ───────────────────────────────────────────────────────────────────

def texte_bienvenue(prenom: str) -> str:
    return (
        f"👋 *Bienvenue {prenom} sur {CANAL_NOM} !*\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"🎯 *C'est quoi ce serveur ?*\n"
        f"Un espace exclusif avec du contenu premium de qualité : "
        f"conseils, tutoriels, ressources et bien plus.\n\n"
        f"📦 *Ce que tu trouveras ici :*\n"
        f"• 🎥 Vidéos accessibles *gratuitement*\n"
        f"• 💎 Contenu premium réservé aux membres payants\n"
        f"• 🔥 Mises à jour régulières\n"
        f"• 🎁 Exclusivités pour les membres Premium\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"💎 *PREMIUM — seulement 4,99€ à vie*\n"
        f"Accès illimité à tout le contenu exclusif, une seule fois !\n\n"
        f"👇 *Que veux-tu faire ?*"
    )


def texte_premium() -> str:
    return (
        f"💎 *Passer Premium — 4,99€ une seule fois*\n\n"
        f"Accès illimité à tout le contenu exclusif !\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"📩 *Contacte un admin en DM pour activer ton accès :*\n\n"
        f"{admins_block()}\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"Dis-leur simplement : *Je veux le Premium* 👌"
    )


def texte_question() -> str:
    return (
        f"❓ *Tu as une question ?*\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"Nos admins sont disponibles en DM :\n\n"
        f"{admins_block()}\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"💬 *Ils peuvent t'aider pour :*\n"
        f"• Des infos sur le Premium\n"
        f"• Un problème d'accès\n"
        f"• Toute autre question\n\n"
        f"Ils répondent rapidement ! 🙌"
    )


def texte_epingle() -> str:
    ts = datetime.now().strftime("%d/%m/%Y à %H:%M")
    paypal_line = f"\n💳 Paiement via PayPal : `{PAYPAL_EMAIL}`\n" if PAYPAL_EMAIL else ""
    return (
        f"📌 *{CANAL_NOM.upper()} — INFOS ESSENTIELLES*\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"🎥 *Contenu gratuit*\n"
        f"Fais défiler vers le haut pour tout voir gratuitement !\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"💎 *Accès PREMIUM — 4,99€ à vie*\n\n"
        f"✅ Tout le contenu exclusif\n"
        f"✅ Vidéos & ressources premium\n"
        f"✅ Mises à jour régulières\n"
        f"✅ Paiement unique, pas d'abonnement\n"
        f"{paypal_line}\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"📩 *Contact & infos :*\n\n"
        f"{admins_block()}\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"🕐 _Mis à jour : {ts}_"
    )


# ─── CLAVIERS ─────────────────────────────────────────────────────────────────

def kb_principal() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("💎 Obtenir le Premium (4,99€ à vie)", callback_data="premium")],
        [InlineKeyboardButton("🎥 Voir le contenu gratuit",          callback_data="gratuit")],
        [InlineKeyboardButton("❓ J'ai une question",                 callback_data="question")],
    ])


def kb_retour() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("⬅️ Retour au menu", callback_data="retour")],
    ])


# ─── BIENVENUE ────────────────────────────────────────────────────────────────

async def envoyer_bienvenue(
    context: ContextTypes.DEFAULT_TYPE,
    group_chat_id: int,
    user_id: int,
    prenom: str,
    msg_systeme_id: int | None = None,
):
    """Envoie le message de bienvenue. Anti-doublon inclus."""
    if user_id in membres_accueillis:
        logger.info(f"Anti-doublon : {user_id} déjà accueilli, skip.")
        return

    membres_accueillis.add(user_id)
    logger.info(f"Bienvenue → {prenom} ({user_id})")

    # Supprimer le message "X a rejoint" si disponible
    if msg_systeme_id:
        await safe_delete(context.bot, group_chat_id, msg_systeme_id)

    texte = texte_bienvenue(prenom)
    kb    = kb_principal()

    # Tentative DM
    msg = await safe_send(
        context.bot, user_id, texte,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=kb,
    )
    if msg:
        logger.info(f"Bienvenue envoyée en DM à {prenom}")
        return

    # Fallback : message dans le groupe
    msg = await safe_send(
        context.bot, group_chat_id, texte,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=kb,
    )
    if msg:
        logger.info(f"Bienvenue envoyée dans le groupe pour {prenom} (DM bloqué)")
        # On n'épingle pas ici pour ne pas écraser le message épinglé principal


# ─── HANDLER : CHAT MEMBER (méthode principale) ───────────────────────────────

async def on_chat_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not FEATURE_WELCOME:
        return

    result = update.chat_member
    if not result:
        return

    old = result.old_chat_member.status
    new = result.new_chat_member.status
    user = result.new_chat_member.user

    if user.is_bot:
        return

    # L'utilisateur vient de rejoindre (depuis banned/left/restricted → member/owner/admin)
    LEFT_STATUSES   = {ChatMemberStatus.BANNED, ChatMemberStatus.LEFT, ChatMemberStatus.RESTRICTED}
    JOINED_STATUSES = {ChatMemberStatus.MEMBER, ChatMemberStatus.OWNER, ChatMemberStatus.ADMINISTRATOR}

    if old in LEFT_STATUSES and new in JOINED_STATUSES:
        logger.info(f"[ChatMember] Rejoint : {user.full_name} ({user.id})")
        await envoyer_bienvenue(context, result.chat.id, user.id, user.first_name)


# ─── HANDLER : MESSAGE SYSTÈME new_chat_members (fallback) ────────────────────

async def on_new_member_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not FEATURE_WELCOME:
        return
    if not update.message or not update.message.new_chat_members:
        return

    for user in update.message.new_chat_members:
        if user.is_bot:
            continue
        logger.info(f"[StatusUpdate] Rejoint : {user.full_name} ({user.id})")
        await envoyer_bienvenue(
            context,
            update.effective_chat.id,
            user.id,
            user.first_name,
            msg_systeme_id=update.message.message_id,
        )


# ─── HANDLER : BOUTONS ────────────────────────────────────────────────────────

async def on_bouton(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user = query.from_user
    data = query.data

    logger.info(f"Bouton '{data}' — {user.first_name} ({user.id})")

    try:
        if data == "premium":
            await query.edit_message_text(
                texte_premium(),
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=kb_retour(),
            )

        elif data == "gratuit":
            await query.answer(
                "📺 Fais défiler vers le haut pour voir tout le contenu gratuit !",
                show_alert=True,
            )

        elif data == "question":
            await query.edit_message_text(
                texte_question(),
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=kb_retour(),
            )

        elif data == "retour":
            await query.edit_message_text(
                texte_bienvenue(user.first_name),
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=kb_principal(),
            )

    except BadRequest as e:
        # "Message is not modified" → pas grave
        if "not modified" not in str(e).lower():
            logger.error(f"Bouton '{data}' – BadRequest : {e}")
    except TelegramError as e:
        logger.error(f"Bouton '{data}' – {type(e).__name__} : {e}")


# ─── COMMANDES ────────────────────────────────────────────────────────────────

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    logger.info(f"/start — {user.full_name} ({user.id})")
    await update.message.reply_text(
        texte_bienvenue(user.first_name),
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=kb_principal(),
    )


async def cmd_test(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Force un message de bienvenue (reset anti-doublon)."""
    user = update.effective_user
    logger.info(f"/test — {user.full_name} ({user.id})")
    membres_accueillis.discard(user.id)
    await envoyer_bienvenue(
        context,
        update.effective_chat.id,
        user.id,
        user.first_name,
    )


async def cmd_pin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Force un re-post immédiat du message épinglé."""
    logger.info(f"/pin demandé par {update.effective_user.id}")
    await poster_et_epingler(context.bot)


# ─── MESSAGE ÉPINGLÉ (tâche de fond) ──────────────────────────────────────────

async def poster_et_epingler(bot: Bot):
    """Supprime l'ancien message épinglé, poste le nouveau, l'épingle."""
    global pinned_message_id

    if not CHANNEL_ID:
        logger.warning("CHANNEL_ID non défini, message épinglé désactivé.")
        return

    # Supprimer l'ancien
    if pinned_message_id:
        await safe_delete(bot, CHANNEL_ID, pinned_message_id)
        pinned_message_id = None

    # Poster le nouveau
    msg = await safe_send(
        bot, CHANNEL_ID, texte_epingle(),
        parse_mode=ParseMode.MARKDOWN,
    )
    if not msg:
        logger.error("Impossible de poster le message épinglé.")
        return

    pinned_message_id = msg.message_id
    logger.info(f"Message épinglé posté (id={pinned_message_id})")

    # Épingler
    ok = await safe_pin(bot, CHANNEL_ID, pinned_message_id)
    if ok:
        logger.info("Message épinglé ✅")
    else:
        logger.warning("Pin échoué — vérifie que le bot est admin avec droit d'épingler.")


async def boucle_epingle(bot: Bot):
    """Boucle infinie : re-poste le message épinglé toutes les INTERVAL secondes."""
    while True:
        logger.info(f"─── Cycle message épinglé ({datetime.now().strftime('%H:%M:%S')}) ───")
        await poster_et_epingler(bot)
        logger.info(f"⏳ Prochain cycle dans {INTERVAL // 60} min {INTERVAL % 60} sec")
        await asyncio.sleep(INTERVAL)


# ─── POST_INIT : lance la boucle épingle au démarrage ─────────────────────────

async def post_init(application: Application):
    if FEATURE_PIN and CHANNEL_ID:
        logger.info("Démarrage de la boucle message épinglé...")
        asyncio.create_task(boucle_epingle(application.bot))
    else:
        logger.info("Message épinglé désactivé (PIN_MSG=false ou CHANNEL_ID manquant).")


# ─── LANCEMENT ────────────────────────────────────────────────────────────────

def main():
    # ── Vérifications ──
    if not TOKEN:
        logger.critical("TOKEN manquant ! Ajoute-le dans les variables d'environnement.")
        sys.exit(1)

    logger.info("═══════════════════════════════════════")
    logger.info(f"  Canal    : {CANAL_NOM}")
    logger.info(f"  Channel  : {CHANNEL_ID or '(non défini)'}")
    logger.info(f"  Admins   : {ADMIN1}, {ADMIN2}" + (f", {ADMIN3}" if ADMIN3 else ""))
    logger.info(f"  Bienvenu : {'✅' if FEATURE_WELCOME else '❌'}")
    logger.info(f"  Épinglé  : {'✅' if FEATURE_PIN else '❌'}  ({INTERVAL}s)")
    logger.info("═══════════════════════════════════════")

    app = (
        Application.builder()
        .token(TOKEN)
        .post_init(post_init)
        .build()
    )

    # Commandes
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("test",  cmd_test))
    app.add_handler(CommandHandler("pin",   cmd_pin))

    # Nouveaux membres
    app.add_handler(ChatMemberHandler(on_chat_member, ChatMemberHandler.CHAT_MEMBER))
    app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, on_new_member_message))

    # Boutons inline
    app.add_handler(CallbackQueryHandler(on_bouton))

    logger.info("✅ Bot démarré et en écoute !")

    app.run_polling(
        allowed_updates=[
            Update.MESSAGE,
            Update.CALLBACK_QUERY,
            Update.CHAT_MEMBER,
        ],
        drop_pending_updates=True,   # ignore les events accumulés pendant le downtime
    )


if __name__ == "__main__":
    main()
