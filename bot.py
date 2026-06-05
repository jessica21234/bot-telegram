import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    CallbackQueryHandler, filters, ContextTypes
)
from config import TOKEN, PAYPAL_EMAIL, CANAL_NOM, ADMIN1, ADMIN2, ADMIN3

logging.basicConfig(level=logging.INFO)

# ─── MESSAGE DE BIENVENUE ────────────────────────────────────────────────────

BIENVENUE_TEXT = f"""
👋 *Bienvenue sur {CANAL_NOM} !*

━━━━━━━━━━━━━━━━━━━━━
🎯 *C'est quoi ce serveur ?*
Un espace exclusif avec du contenu premium de qualité : conseils, tutoriels, ressources et bien plus encore.

📦 *Ce que tu trouveras ici :*
• 🎥 Des vidéos déjà postées accessibles gratuitement
• 💎 Du contenu premium réservé aux membres payants
• 🔥 Des mises à jour régulières

━━━━━━━━━━━━━━━━━━━━━
💎 *PREMIUM — 4,99€/mois*
Accès illimité à tout le contenu exclusif, priorité sur les nouveautés, et bien plus.

👇 *Que veux-tu faire ?*
"""

def bienvenue_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("💎 Obtenir le Premium (4,99€)", callback_data="premium")],
        [InlineKeyboardButton("🎥 Voir les vidéos gratuites", callback_data="gratuit")],
        [InlineKeyboardButton("❓ J'ai une question", callback_data="question")],
    ])

# ─── HANDLER : NOUVEAU MEMBRE ────────────────────────────────────────────────

async def nouveau_membre(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat

    # Supprimer les messages "X a rejoint le groupe" (service messages)
    if update.message:
        try:
            await update.message.delete()
        except Exception:
            pass

    for member in update.message.new_chat_members:
        if member.is_bot:
            continue

        msg = await context.bot.send_message(
            chat_id=chat.id,
            text=BIENVENUE_TEXT,
            parse_mode="Markdown",
            reply_markup=bienvenue_keyboard()
        )

        # Épingler le message en haut
        try:
            await context.bot.pin_chat_message(
                chat_id=chat.id,
                message_id=msg.message_id,
                disable_notification=True
            )
        except Exception as e:
            logging.warning(f"Impossible d'épingler : {e}")

# ─── HANDLER : BOUTONS ───────────────────────────────────────────────────────

async def bouton_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user = query.from_user
    username = f"@{user.username}" if user.username else user.first_name

    if query.data == "premium":
        texte = (
            f"💎 *Super choix, {user.first_name} !*\n\n"
            f"Pour obtenir ton accès Premium, contacte l'un de nos admins :\n\n"
            f"👤 {ADMIN1}\n"
            f"👤 {ADMIN2}\n"
            f"👤 {ADMIN3}\n\n"
            f"Ils te guideront pour le paiement et l'activation de ton accès 🚀"
        )
        await query.edit_message_text(texte, parse_mode="Markdown",
                                      reply_markup=retour_keyboard())

    elif query.data == "gratuit":
        texte = (
            "🎥 *Vidéos gratuites*\n\n"
            "Tu peux parcourir les vidéos déjà postées dans ce canal.\n"
            "Fais défiler vers le haut pour les retrouver !\n\n"
            "💡 _Passe Premium pour accéder à tout le contenu exclusif._"
        )
        await query.edit_message_text(texte, parse_mode="Markdown",
                                      reply_markup=retour_keyboard())

    elif query.data == "question":
        texte = (
            f"❓ *Tu as une question ?*\n\n"
            f"Contacte directement un admin, ils répondent rapidement :\n\n"
            f"👤 {ADMIN1}\n"
            f"👤 {ADMIN2}\n"
            f"👤 {ADMIN3}\n\n"
            f"Ou si tu es prêt à payer directement :\n\n"
            f"💳 *PayPal :* `{PAYPAL_EMAIL}`\n\n"
            f"📝 Dans le message PayPal, indique :\n"
            f"`{username} — {CANAL_NOM}`"
        )
        await query.edit_message_text(texte, parse_mode="Markdown",
                                      reply_markup=retour_keyboard())

    elif query.data == "retour":
        await query.edit_message_text(
            BIENVENUE_TEXT,
            parse_mode="Markdown",
            reply_markup=bienvenue_keyboard()
        )

    elif query.data == "payer_direct":
        user = query.from_user
        username = f"@{user.username}" if user.username else user.first_name
        texte = (
            f"💳 *Paiement direct par PayPal*\n\n"
            f"Envoie *4,99€ ou 5€* à :\n"
            f"`{PAYPAL_EMAIL}`\n\n"
            f"📝 *Dans le message PayPal, écris exactement :*\n"
            f"`{username} — {CANAL_NOM}`\n\n"
            f"✅ Ton accès sera activé dès réception du paiement !"
        )
        await query.edit_message_text(texte, parse_mode="Markdown",
                                      reply_markup=retour_keyboard())

def retour_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("💳 Payer directement (PayPal)", callback_data="payer_direct")],
        [InlineKeyboardButton("⬅️ Retour", callback_data="retour")],
    ])

# ─── COMMANDE /start ─────────────────────────────────────────────────────────

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        BIENVENUE_TEXT,
        parse_mode="Markdown",
        reply_markup=bienvenue_keyboard()
    )

# ─── LANCEMENT ───────────────────────────────────────────────────────────────

def main():
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, nouveau_membre))
    app.add_handler(CallbackQueryHandler(bouton_callback))

    print("✅ Bot démarré !")
    app.run_polling()

if __name__ == "__main__":
    main()
