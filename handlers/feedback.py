from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler, MessageHandler, filters, CallbackQueryHandler, CommandHandler
from config.database import get_db
from config.settings import settings

db = get_db()
FEEDBACK_WAITING = 1
ADMIN_REPLY_WAITING = 2

# --- 1. የተጠቃሚው የአስተያየት መስጫ ሎጅክ ---


async def start_feedback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    item_id = query.data.replace("give_fb_", "")
    context.user_data["feedback_item_id"] = item_id

    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="✍️ **እባክዎን ለዚህ የዲዛይን ስራ ያለዎትን አስተያየት (Feedback) ይጻፉልን፦**\n\n_(ሂደቱን ለማቋረጥ /cancel ማለትን ይችላሉ)_",
        parse_mode="Markdown"
    )
    return FEEDBACK_WAITING


async def receive_feedback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_msg = update.message
    chat_id = update.effective_chat.id
    username = update.effective_user.username or "No Username"
    full_name = update.effective_user.full_name or "Unknown"
    item_id = context.user_data.get("feedback_item_id", "Unknown")

    feedback_report = (
        "💡 **Dear Nuhita, አዲስ አስተያየት (New Feedback) ደርሷል!**\n\n"
        f"👤 **ከተጠቃሚ፦** {full_name} (@{username})\n"
        f"🆔 **የተጠቃሚ ID፦** `{chat_id}`\n"
        f"🖼️ **የስራው (Portfolio) ID፦** `{item_id}`\n\n"
        f"💬 **የተሰጠ አስተያየት፦**\n{user_msg.text}"
    )

    # ለአድሚኑ የሚላከው ቁልፍ (ከተጠቃሚው chat_id ጋር ተያይዞ ይሄዳል)
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("✍️ Reply to User",
                              callback_data=f"adm_rply_{chat_id}")]
    ])

    for admin_id in settings.ADMIN_IDS:
        try:
            await context.bot.send_message(
                chat_id=admin_id,
                text=feedback_report,
                reply_markup=keyboard,
                parse_mode="Markdown"
            )
        except Exception as e:
            print(f"Failed to forward feedback to admin {admin_id}: {e}")

    await update.message.reply_text("🙏 ስላስተያየትዎ እጅግ እናመሰግናለን! አስተያየትዎ ለድርጅቱ አድሚን ተላልፏል።")
    context.user_data.clear()
    return ConversationHandler.END


async def cancel_feedback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ የአስተያየት መስጫው ተቋርጧል።")
    context.user_data.clear()
    return ConversationHandler.END


# --- 2. የአድሚን ምላሽ (Admin Reply) መስጫ ሎጅክ ---
async def start_admin_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    # ምላሽ የሚላክለትን ተጠቃሚ ID ከማሳያው ላይ እንለያለን
    target_user_id = query.data.replace("adm_rply_", "")
    context.user_data["reply_target_user"] = target_user_id

    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=f"🔄 ለተጠቃሚው (ID: {target_user_id}) የሚልኩትን ምላሽ ይጻፉ✍🏿፦\n\n_(ለማቋረጥ /cancel ይበሉ)_"
    )
    return ADMIN_REPLY_WAITING


async def send_admin_reply_to_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    admin_msg = update.message
    target_user_id = context.user_data.get("reply_target_user")

    if not target_user_id:
        await update.message.reply_text("🚨 ስህተት፡ ተጠቃሚው አልተገኘም።")
        return ConversationHandler.END

    try:
        # ለአድሚኑ መልዕክት የተላከበትን ፎርማት ማዘጋጀት
        reply_text = (
            "✉️ **ከ Nuhita Graphics አድሚን የተላከ ምላሽ፦**\n\n"
            f"{admin_msg.text}"
        )
        # ለተጠቃሚው ይላካል
        await context.bot.send_message(chat_id=int(target_user_id), text=reply_text, parse_mode="Markdown")
        await update.message.reply_text("✅ ምላሽዎ ለተጠቃሚው በተሳካ ሁኔታ ተላልፏል!")
    except Exception as e:
        await update.message.reply_text(f"❌ መልዕክቱን መላክ አልተቻለም። ተጠቃሚው ቦቱን አቁሞት ሊሆን ይችላል። ስህተት፦ {e}")

    context.user_data.clear()
    return ConversationHandler.END


async def cancel_admin_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ የአድሚን ምላሽ ተሰርዟል።")
    context.user_data.clear()
    return ConversationHandler.END


# --- 3. ለ main.py የሚዘጋጁ የ Conversation Handlers ---
feedback_conv = ConversationHandler(
    entry_points=[CallbackQueryHandler(start_feedback, pattern="^give_fb_")],
    states={
        FEEDBACK_WAITING: [MessageHandler(
            filters.TEXT & ~filters.COMMAND, receive_feedback)]
    },
    fallbacks=[CommandHandler("cancel", cancel_feedback)]
)

admin_reply_conv = ConversationHandler(
    entry_points=[CallbackQueryHandler(
        start_admin_reply, pattern="^adm_rply_")],
    states={
        ADMIN_REPLY_WAITING: [MessageHandler(
            filters.TEXT & ~filters.COMMAND, send_admin_reply_to_user)]
    },
    fallbacks=[CommandHandler("cancel", cancel_admin_reply)]
)
