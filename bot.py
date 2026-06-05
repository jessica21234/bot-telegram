import logging
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    CallbackQueryHandler, filters, ContextTypes
)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ─── CONFIG ──────────────────────────────────────────────────────────────────

TOKEN       = os.environ.get("TOKEN")
PAYPAL      = os.environ.get("PAYPAL_EMAIL", "ton@email.com")
CANAL_NOM   = os.environ.get("CANAL_NOM", "Notre Serveur")
ADMIN1      = os.environ.get("ADMIN1", "@irk14")
ADMIN2      = os.environ.get("ADMIN2", "@ilyan_dugafe")
ADMIN3      = os.environ.get("ADMIN3", "@admin")

# ─── TEXTES ──────────────────────────────────────────────────────────────────

def texte_bienvenue(prenom):
    return (
        f"👋 *Bienvenue {prenom} sur {CANAL_NOM} !*\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"🎯 *C'est quoi ce serveur ?*\n"
        f"Un espace exclusif avec du contenu premium de qualité : conseils, tutoriels, ressources et bien plus.\n\n"
        f"📦 *Ce que tu trouveras ici :*\n"
        f"• 🎥 Des vidéos déjà postées accessibles gratuitement\n"
        f"• 💎 Du contenu premium réservé aux membres payants\n"
        f"• 🔥 Des mises à jour régulières\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"💎 *PREMIUM — 4,99€/mois*\n"
        f"Accès illimité à tout le contenu exclusif.\n\n"
        f"👇 *Que veux-tu faire ?*"
    )

def texte_premium():
    return (
        f"💎 *Passer Premium*\n\n"
        f"Pour obtenir ton accès Premium, tu as 2 options :\n\n"
        f"*Option 1 — Contacter un admin :*\n"
        f"👤 {ADMIN1}\n"
        f"👤 {ADMIN2}\n"
        f"👤 {ADMIN3}\n\n"
        f"*Option 2 — Payer directement :*\n"
        f"Clique sur le bouton ci-dessous 👇"
    )

def texte_paiement(username):
    return (
        f"💳 *Paiement direct PayPal*\n\n"
        f"Envoie *4,99€ ou 5€* à :\n"
        f"`{PAYPAL}`\n\n"
        f"📝 *Dans le message PayPal, écris EXACTEMENT :*\n"
        f"`{username} — {CANAL_NOM}`\n\n"
        f"✅ Ton accès sera activé dès réception !\n\n"
        f"Une fois payé, contacte un admin pour confirmation :\n"
        f"👤 {ADMIN1} • {ADMIN2} • {ADMIN3}"
    )

def texte_gratuit():
    return (
        f"🎥 *Vidéos gratuites*\n\n"
        f"Fais défiler vers le haut pour voir toutes les vidéos déjà postées !\n\n"
        f"💡 _Passe Premium pour accéder à tout le contenu exclusif._"
    )

def texte_question():
    return (
        f"❓ *Tu as une question ?*\n\n"
        f"Nos admins répondent rapidement en DM :\n\n"
        f"👤 {ADMIN1}\n"
        f"👤 {ADMIN2}\n"
        f"👤 {ADMIN3}\n\n"
        f"N'hésite pas à les contacter directement !"
    )

# ─── KEYBOARDS ───────────────────────────────────────────────────────────────

def kb_principal():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("💎 Obtenir le Premium (4,99€)", callback_data="premium")],
        [InlineKeyboardButton("🎥 Voir les vidéos gratuites", callback_data="gratuit")],
        [InlineKeyboardButton("❓ J'ai une question", callback_data="question")],
    ])

def kb_premium():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("💳 Payer directement via PayPal", callback_data="payer")],
        [InlineKeyboardButton("⬅️ Retour", callback_data="retour")],
    ])

def kb_retour():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("⬅️ Retour", callback_data="retour")],
    ])

# ─── HANDLER : NOUVEAU MEMBRE ────────────────────────────────────────────────

async def nouveau_membre(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return

    # Supprimer le message système "X a rejoint"
    try:
        await update.message.delete()
        logger.info("Message système supprimé")
    except Exception as e:
        logger.warning(f"Impossible de supprimer le message système : {e}")

    for member in update.message.new_chat_members:
        if member.is_bot:
            continue

        logger.info(f"Nouveau membre : {member.full_name} ({member.id})")

        try:
            msg = await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=texte_bienvenue(member.first_name),
                parse_mode="Markdown",
                reply_markup=kb_principal()
            )

            # Épingler le message
            try:
                await context.bot.pin_chat_message(
                    chat_id=update.effective_chat.id,
                    message_id=msg.message_id,
                    disable_notification=True
                )
                logger.info("Message épinglé")
            except Exception as e:
                logger.warning(f"Impossible d'épingler : {e}")

        except Exception as e:
            logger.error(f"Erreur envoi message bienvenue : {e}")

# ─── HANDLER : BOUTONS ───────────────────────────────────────────────────────

async def bouton(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user = query.from_user
    username = f"@{user.username}" if user.username else user.first_name
    data = query.data

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
                reply_markup=kb_retour()
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
                reply_markup=kb_retour()
            )

        elif data == "retour":
            await query.edit_message_text(
                texte_bienvenue(user.first_name),
                parse_mode="Markdown",
                reply_markup=kb_principal()
            )

    except Exception as e:
        logger.error(f"Erreur bouton {data} : {e}")

# ─── COMMANDE /start ─────────────────────────────────────────────────────────

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await update.message.reply_text(
        texte_bienvenue(user.first_name),
        parse_mode="Markdown",
        reply_markup=kb_principal()
    )

# ─── LANCEMENT ───────────────────────────────────────────────────────────────

def main():
    if not TOKEN:
        raise ValueError("TOKEN manquant ! Vérifie les variables Railway.")

    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(
        filters.StatusUpdate.NEW_CHAT_MEMBERS,
        nouveau_membre
    ))
    app.add_handler(CallbackQueryHandler(bouton))

    logger.info("✅ Bot démarré !")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
