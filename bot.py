import logging
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ChatMemberStatus
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    CallbackQueryHandler, filters, ContextTypes,
    ChatMemberHandler
)

# ─── LOGGING ─────────────────────────────────────────────────────────────────

logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ─── CONFIG ──────────────────────────────────────────────────────────────────

TOKEN     = os.environ.get("TOKEN")
PAYPAL    = os.environ.get("PAYPAL_EMAIL", "ton@email.com")
CANAL_NOM = os.environ.get("CANAL_NOM", "Notre Serveur")
ADMIN1    = os.environ.get("ADMIN1", "@irk14")
ADMIN2    = os.environ.get("ADMIN2", "@ilyan_dugafe")

# IDs des membres ayant déjà reçu le message (anti-doublon)
membres_accueillis = set()

# ─── TEXTES ──────────────────────────────────────────────────────────────────

def texte_bienvenue(prenom: str) -> str:
    return (
        f"👋 *Bienvenue {prenom} sur {CANAL_NOM} !*\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"🎯 *C'est quoi ce serveur ?*\n"
        f"Un espace exclusif avec du contenu premium de qualité : "
        f"conseils, tutoriels, ressources et bien plus.\n\n"
        f"📦 *Ce que tu trouveras ici :*\n"
        f"• 🎥 Des vidéos déjà postées accessibles *gratuitement*\n"
        f"• 💎 Du contenu premium réservé aux membres payants\n"
        f"• 🔥 Des mises à jour régulières\n"
        f"• 🎁 Des exclusivités pour les membres Premium\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"💎 *PREMIUM — seulement 4,99€ à vie*\n"
        f"Accès illimité à tout le contenu exclusif, une seule fois !\n\n"
        f"👇 *Que veux-tu faire ?*"
    )

def texte_premium() -> str:
    return (
        f"💎 *Passer Premium — 4,99€ une seule fois*\n\n"
        f"Tu seras parmi nos membres exclusifs avec accès à tout le contenu !\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"📩 *Contacte un admin en DM pour activer ton accès :*\n\n"
        f"👤 {ADMIN1}\n"
        f"👤 {ADMIN2}\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"Dis-leur simplement : *Je veux le Premium* et ils t'expliqueront comment payer 👌"
    )

def texte_question() -> str:
    return (
        f"❓ *Tu as une question ?*\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"Nos admins sont disponibles et répondent rapidement en DM :\n\n"
        f"👤 {ADMIN1}\n"
        f"👤 {ADMIN2}\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"💬 *N'hésite pas à les contacter pour :*\n"
        f"• Des infos sur le Premium\n"
        f"• Un problème d'accès\n"
        f"• Toute autre question\n\n"
        f"Ils te répondront dès que possible ! 🙌"
    )

# ─── KEYBOARDS ───────────────────────────────────────────────────────────────

def kb_principal() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("💎 Obtenir le Premium (4,99€ à vie)", callback_data="premium")],
        [InlineKeyboardButton("🎥 Voir le contenu gratuit", callback_data="gratuit")],
        [InlineKeyboardButton("❓ J'ai une question", callback_data="question")],
    ])

def kb_premium() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("⬅️ Retour", callback_data="retour")],
    ])

def kb_retour_simple() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("⬅️ Menu principal", callback_data="retour")],
    ])

# ─── ENVOI DU MESSAGE DE BIENVENUE ───────────────────────────────────────────

async def envoyer_bienvenue(context, chat_id: int, user_id: int, prenom: str, message_id_a_supprimer=None):
    """
    Envoie le message de bienvenue uniquement à la personne concernée
    en utilisant reply_markup avec un message ciblé.
    Anti-doublon : si déjà accueilli dans cette session, on skip.
    """
    if user_id in membres_accueillis:
        logger.info(f"Anti-doublon : {user_id} déjà accueilli, skip.")
        return

    membres_accueillis.add(user_id)

    # Supprimer le message système "X a rejoint" si présent
    if message_id_a_supprimer:
        try:
            await context.bot.delete_message(chat_id=chat_id, message_id=message_id_a_supprimer)
        except Exception as e:
            logger.warning(f"Suppression message système échouée : {e}")

    try:
        # Envoi en DM d'abord (seule la personne voit)
        await context.bot.send_message(
            chat_id=user_id,
            text=texte_bienvenue(prenom),
            parse_mode="Markdown",
            reply_markup=kb_principal()
        )
        logger.info(f"Message de bienvenue envoyé en DM à {prenom} ({user_id})")
    except Exception:
        # Si DM bloqué, on envoie dans le groupe mais avec un message discret
        try:
            msg = await context.bot.send_message(
                chat_id=chat_id,
                text=texte_bienvenue(prenom),
                parse_mode="Markdown",
                reply_markup=kb_principal()
            )
            logger.info(f"Message de bienvenue envoyé dans le groupe pour {prenom} (DM bloqué)")
            # Épingler
            try:
                await context.bot.pin_chat_message(
                    chat_id=chat_id,
                    message_id=msg.message_id,
                    disable_notification=True
                )
            except Exception as e:
                logger.warning(f"Pin échoué : {e}")
        except Exception as e:
            logger.error(f"Erreur envoi bienvenue : {e}")


# ─── HANDLER : CHAT MEMBER ───────────────────────────────────────────────────

async def track_chat_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    result = update.chat_member
    if not result:
        return

    old_status = result.old_chat_member.status
    new_status = result.new_chat_member.status
    member = result.new_chat_member.user

    was_member = old_status in [
        ChatMemberStatus.BANNED,
        ChatMemberStatus.LEFT,
        ChatMemberStatus.RESTRICTED,
    ]
    is_member = new_status in [
        ChatMemberStatus.MEMBER,
        ChatMemberStatus.OWNER,
        ChatMemberStatus.ADMINISTRATOR,
    ]

    if not was_member or not is_member:
        return
    if member.is_bot:
        return

    logger.info(f"[ChatMember] Nouveau : {member.full_name} ({member.id})")
    await envoyer_bienvenue(context, result.chat.id, member.id, member.first_name)


# ─── HANDLER : NOUVEAU MEMBRE (secours) ──────────────────────────────────────

async def nouveau_membre(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.new_chat_members:
        return

    for member in update.message.new_chat_members:
        if member.is_bot:
            continue
        logger.info(f"[StatusUpdate] Nouveau : {member.full_name} ({member.id})")
        await envoyer_bienvenue(
            context,
            update.effective_chat.id,
            member.id,
            member.first_name,
            message_id_a_supprimer=update.message.message_id
        )


# ─── HANDLER : BOUTONS ───────────────────────────────────────────────────────

async def bouton(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user = query.from_user
    data = query.data

    logger.info(f"Bouton '{data}' cliqué par {user.first_name} ({user.id})")

    try:
        if data == "premium":
            await query.edit_message_text(
                texte_premium(),
                parse_mode="Markdown",
                reply_markup=kb_premium()
            )

        elif data == "gratuit":
            # Ne fait rien de visible, juste un toast discret
            await query.answer("📺 Fais défiler vers le haut pour voir tout le contenu gratuit !", show_alert=True)

        elif data == "question":
            await query.edit_message_text(
                texte_question(),
                parse_mode="Markdown",
                reply_markup=kb_retour_simple()
            )

        elif data == "retour":
            await query.edit_message_text(
                texte_bienvenue(user.first_name),
                parse_mode="Markdown",
                reply_markup=kb_principal()
            )

    except Exception as e:
        logger.error(f"Erreur bouton '{data}' : {e}")


# ─── COMMANDE /start ─────────────────────────────────────────────────────────

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    logger.info(f"/start de {user.full_name} ({user.id})")
    await update.message.reply_text(
        texte_bienvenue(user.first_name),
        parse_mode="Markdown",
        reply_markup=kb_principal()
    )


# ─── COMMANDE /test ───────────────────────────────────────────────────────────

async def test(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    logger.info(f"/test de {user.full_name} ({user.id})")
    # Reset anti-doublon pour le test
    membres_accueillis.discard(user.id)
    await envoyer_bienvenue(context, update.effective_chat.id, user.id, user.first_name)


# ─── LANCEMENT ───────────────────────────────────────────────────────────────

def main():
    if not TOKEN:
        raise ValueError("❌ TOKEN manquant ! Ajoute-le dans les variables Railway.")

    logger.info("Démarrage du bot...")
    logger.info(f"Canal : {CANAL_NOM}")
    logger.info(f"Admins : {ADMIN1}, {ADMIN2}")

    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("test", test))
    app.add_handler(ChatMemberHandler(track_chat_member, ChatMemberHandler.CHAT_MEMBER))
    app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, nouveau_membre))
    app.add_handler(CallbackQueryHandler(bouton))

    logger.info("✅ Bot démarré et en écoute !")

    app.run_polling(
        allowed_updates=[
            Update.MESSAGE,
            Update.CALLBACK_QUERY,
            Update.CHAT_MEMBER,
        ]
    )


if __name__ == "__main__":
    main()
