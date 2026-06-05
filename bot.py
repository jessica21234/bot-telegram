import logging
import os
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ChatMemberUpdated
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
ADMIN3    = os.environ.get("ADMIN3", "@admin")

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
        f"💎 *PREMIUM — seulement 4,99€/mois*\n"
        f"Accès illimité à tout le contenu exclusif, priorité sur "
        f"les nouveautés, et bien plus encore.\n\n"
        f"👇 *Que veux-tu faire ?*"
    )

def texte_premium() -> str:
    return (
        f"💎 *Passer Premium — 4,99€/mois*\n\n"
        f"Tu seras parmi nos membres exclusifs avec accès à tout le contenu !\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"📩 *Option 1 — Contacter un admin directement :*\n"
        f"Envoie un DM à l'un de nos admins, ils t'activeront l'accès :\n\n"
        f"👤 {ADMIN1}\n"
        f"👤 {ADMIN2}\n"
        f"👤 {ADMIN3}\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"💳 *Option 2 — Payer directement par PayPal :*\n"
        f"Clique sur le bouton ci-dessous pour les instructions de paiement 👇"
    )

def texte_paiement(username: str) -> str:
    return (
        f"💳 *Paiement direct PayPal*\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"💰 *Montant :* 4,99€ ou 5€\n\n"
        f"📧 *Adresse PayPal :*\n"
        f"`{PAYPAL}`\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"📝 *IMPORTANT — Dans le message PayPal, écris EXACTEMENT :*\n\n"
        f"`{username} — {CANAL_NOM}`\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"✅ *Après le paiement :*\n"
        f"Contacte un admin pour confirmer et activer ton accès :\n"
        f"👤 {ADMIN1} • {ADMIN2} • {ADMIN3}\n\n"
        f"⚡ Activation en moins de 24h !"
    )

def texte_gratuit() -> str:
    return (
        f"🎥 *Contenu gratuit disponible*\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"Tu peux dès maintenant :\n"
        f"• 📺 Regarder toutes les vidéos déjà postées dans ce canal\n"
        f"• 📖 Lire les posts publics\n"
        f"• 💬 Participer aux discussions\n\n"
        f"Fais défiler vers le haut pour tout voir !\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"💡 *Tu veux plus ?*\n"
        f"Passe Premium pour seulement *4,99€/mois* et accède à "
        f"tout le contenu exclusif 🚀"
    )

def texte_question() -> str:
    return (
        f"❓ *Tu as une question ?*\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"Nos admins sont disponibles et répondent rapidement en DM :\n\n"
        f"👤 {ADMIN1}\n"
        f"👤 {ADMIN2}\n"
        f"👤 {ADMIN3}\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"💬 *N'hésite pas à les contacter pour :*\n"
        f"• Des infos sur le Premium\n"
        f"• Un problème d'accès\n"
        f"• Toute autre question\n\n"
        f"Ils te répondront dès que possible ! 🙌"
    )

def texte_confirmation_paiement(username: str) -> str:
    return (
        f"🎉 *Paiement envoyé ?*\n\n"
        f"Super ! Maintenant contacte un admin avec ta preuve de paiement :\n\n"
        f"👤 {ADMIN1}\n"
        f"👤 {ADMIN2}\n"
        f"👤 {ADMIN3}\n\n"
        f"Dis-leur : *J'ai payé le Premium* et montre le reçu PayPal.\n"
        f"Ton accès sera activé rapidement ✅"
    )

# ─── KEYBOARDS ───────────────────────────────────────────────────────────────

def kb_principal() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("💎 Obtenir le Premium (4,99€)", callback_data="premium")],
        [InlineKeyboardButton("🎥 Voir le contenu gratuit", callback_data="gratuit")],
        [InlineKeyboardButton("❓ J'ai une question", callback_data="question")],
    ])

def kb_premium() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("💳 Payer directement via PayPal", callback_data="payer")],
        [InlineKeyboardButton("📩 Contacter un admin", callback_data="question")],
        [InlineKeyboardButton("⬅️ Retour", callback_data="retour")],
    ])

def kb_paiement() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ J'ai payé, activer mon accès", callback_data="confirmer")],
        [InlineKeyboardButton("⬅️ Retour", callback_data="premium")],
    ])

def kb_retour() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("💎 Passer Premium", callback_data="premium")],
        [InlineKeyboardButton("⬅️ Menu principal", callback_data="retour")],
    ])

def kb_retour_simple() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("⬅️ Menu principal", callback_data="retour")],
    ])

# ─── HANDLER : CHAT MEMBER (méthode la plus fiable) ──────────────────────────

async def track_chat_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Détecte les nouveaux membres via ChatMemberHandler.
    C'est la méthode la plus fiable pour les supergroupes publics.
    """
    result: ChatMemberUpdated = update.chat_member

    if not result:
        return

    old_status = result.old_chat_member.status
    new_status = result.new_chat_member.status
    member = result.new_chat_member.user

    # On vérifie que c'est bien une entrée dans le groupe
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

    logger.info(f"[ChatMember] Nouveau membre détecté : {member.full_name} (@{member.username}) — ID: {member.id}")

    chat_id = result.chat.id

    try:
        msg = await context.bot.send_message(
            chat_id=chat_id,
            text=texte_bienvenue(member.first_name),
            parse_mode="Markdown",
            reply_markup=kb_principal()
        )
        logger.info(f"Message de bienvenue envoyé (msg_id={msg.message_id})")

        # Épingler
        try:
            await context.bot.pin_chat_message(
                chat_id=chat_id,
                message_id=msg.message_id,
                disable_notification=True
            )
            logger.info("Message épinglé avec succès")
        except Exception as e:
            logger.warning(f"Pin échoué : {e}")

    except Exception as e:
        logger.error(f"Erreur envoi bienvenue : {e}")


# ─── HANDLER : NOUVEAU MEMBRE (méthode de secours) ───────────────────────────

async def nouveau_membre(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Méthode de secours via StatusUpdate.NEW_CHAT_MEMBERS.
    Double filet pour ne rater aucun membre.
    """
    if not update.message or not update.message.new_chat_members:
        return

    # Supprimer le message système "X a rejoint"
    try:
        await update.message.delete()
        logger.info("Message système supprimé")
    except Exception as e:
        logger.warning(f"Suppression message système échouée : {e}")

    for member in update.message.new_chat_members:
        if member.is_bot:
            continue

        logger.info(f"[StatusUpdate] Nouveau membre : {member.full_name} ({member.id})")

        try:
            msg = await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=texte_bienvenue(member.first_name),
                parse_mode="Markdown",
                reply_markup=kb_principal()
            )
            logger.info(f"Message de bienvenue envoyé (msg_id={msg.message_id})")

            try:
                await context.bot.pin_chat_message(
                    chat_id=update.effective_chat.id,
                    message_id=msg.message_id,
                    disable_notification=True
                )
                logger.info("Message épinglé")
            except Exception as e:
                logger.warning(f"Pin échoué : {e}")

        except Exception as e:
            logger.error(f"Erreur envoi bienvenue : {e}")


# ─── HANDLER : BOUTONS ───────────────────────────────────────────────────────

async def bouton(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user = query.from_user
    username = f"@{user.username}" if user.username else user.first_name
    data = query.data

    logger.info(f"Bouton '{data}' cliqué par {username}")

    try:
        if data == "premium":
            await query.edit_message_text(
                texte_premium(),
                parse_mode="Markdown",
                reply_markup=kb_premium()
            )

        elif data == "payer":
            await query.edit_message_text(
                texte_paiement(username),
                parse_mode="Markdown",
                reply_markup=kb_paiement()
            )

        elif data == "confirmer":
            await query.edit_message_text(
                texte_confirmation_paiement(username),
                parse_mode="Markdown",
                reply_markup=kb_retour_simple()
            )

        elif data == "gratuit":
            await query.edit_message_text(
                texte_gratuit(),
                parse_mode="Markdown",
                reply_markup=kb_retour()
            )

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


# ─── COMMANDE /test (admin only) ─────────────────────────────────────────────

async def test(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Commande pour tester le message de bienvenue sans rejoindre."""
    user = update.effective_user
    logger.info(f"/test de {user.full_name} ({user.id})")

    msg = await update.message.reply_text(
        texte_bienvenue(user.first_name),
        parse_mode="Markdown",
        reply_markup=kb_principal()
    )

    try:
        await context.bot.pin_chat_message(
            chat_id=update.effective_chat.id,
            message_id=msg.message_id,
            disable_notification=True
        )
    except Exception as e:
        logger.warning(f"Pin /test échoué : {e}")


# ─── LANCEMENT ───────────────────────────────────────────────────────────────

def main():
    if not TOKEN:
        raise ValueError("❌ TOKEN manquant ! Ajoute-le dans les variables Railway.")

    logger.info("Démarrage du bot...")
    logger.info(f"Canal : {CANAL_NOM}")
    logger.info(f"PayPal : {PAYPAL}")
    logger.info(f"Admins : {ADMIN1}, {ADMIN2}, {ADMIN3}")

    app = Application.builder().token(TOKEN).build()

    # Handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("test", test))

    # Double détection nouveaux membres
    app.add_handler(ChatMemberHandler(track_chat_member, ChatMemberHandler.CHAT_MEMBER))
    app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, nouveau_membre))

    # Boutons
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
