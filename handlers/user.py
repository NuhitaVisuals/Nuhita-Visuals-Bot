from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from config.database import get_db
from config.settings import settings

db = get_db()

# የዘርፎች መዝገበ-ቃላት (Database Value -> User Display Name)
CATEGORY_MAP = {
    "Brand": "🎨 Brand Design",
    "Print": "🖨️ Print Design",
    "Social_Media": "📱 Social Media Design",
    "Event": "🎉 Event & Celebration Design",
    "Package": "📦 Package & Label Design",
    "Merchandise": "👕 Merchandise Design"
}


def get_main_menu_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📂 Show My Portfolio",
                              callback_data="user_portfolio")],
        [InlineKeyboardButton(
            "🛍️ Order Now", callback_data="user_order_start")],
        [InlineKeyboardButton("📞 Contact Us", callback_data="user_contact")],
        [InlineKeyboardButton("ℹ️ About Us", callback_data="user_about")]
    ])


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    username = update.effective_user.username
    full_name = update.effective_user.full_name

    try:
        db.table("users").upsert({
            "chat_id": chat_id,
            "username": username,
            "full_name": full_name
        }).execute()
    except Exception as e:
        print(f"Error saving user: {e}")

    welcome_text = (
        "✨ **Welcome to Nuhita Graphics Portfolio Bot!** ✨\n\n"
        "የፈጠራ እና የዲጂታል መፍትሄዎች ማዕከል። እዚህ አዳዲስ የዲዛይን ስራዎቻችንን ማየት፣ "
        "ትዕዛዝ ማስተናገድ እና እኛን ማግኘት ይችላሉ።"
    )
    await update.message.reply_text(text=welcome_text, reply_markup=get_main_menu_keyboard(), parse_mode="Markdown")


async def handle_static_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "user_main_menu":
        welcome_text = (
            "✨ **Welcome to Nuhita Graphics Portfolio Bot!** ✨\n\n"
            "የፈጠራ እና የዲጂታል መፍትሄዎች ማዕከል። እዚህ አዳዲስ የዲዛይን ስራዎቻችንን ማየት፣ "
            "ትዕዛዝ ማስተናገድ እና እኛን ማግኘት ይችላሉ።"
        )
        await query.edit_message_text(text=welcome_text, reply_markup=get_main_menu_keyboard(), parse_mode="Markdown")

    elif query.data == "user_contact":
        # parse_mode="HTML" በመጠቀም የ Markdown ስህተትን እንከላከላለን
        contact_text = (
            "📞 <b>Contact Us / ያግኙን</b>\n\n"
            f"📱 <b>Phone:</b> {settings.DESIGNER_PHONE}\n"
            f"✈️ <b>Telegram Address:</b> @{settings.DESIGNER_USERNAME}\n\n"
            "💡 ማንኛውንም ጥያቄ ወይም ተጨማሪ መረጃ ከፈለጉ ከላይ ባለው አድራሻ ሊያገኙን ይችላሉ።"
        )
        keyboard = [[InlineKeyboardButton(
            "🏠 Main Menu", callback_data="user_main_menu")]]

        # እዚህ ጋር parse_mode="HTML" መደረጉን ልብ በል
        await query.edit_message_text(
            text=contact_text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="HTML"
        )

    elif query.data == "user_about":
        about_text = (
            "ℹ️ **About Nuhita Graphics (ስለ Nuhita Graphics):**\n\n"
            "እኛ ዲዛይንን ከቢዝነስ እይታ ጋር አቆራኝተን የምንሰራ የፈጠራ ባለሙያዎች ነን። "
            "ስራዎቻችን ዝም ብለው የሚያምሩ ብቻ ሳይሆኑ ለድርጅትዎ ሽያጭ እና እድገት እሴት የሚጨምሩ "
            "(Business-Minded Designs) ናቸው። አብረን ስለሰራን ደስ ብሎናል።"
        )
        keyboard = [[InlineKeyboardButton(
            "🔙 Back to Menu", callback_data="user_main_menu")]]
        await query.edit_message_text(text=about_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")


async def show_portfolio_categories(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """የ 7ቱን የፖርትፎሊዮ ዘርፍ ቁልፎች ያሳያል"""
    query = update.callback_query
    await query.answer()

    keyboard = [
        [InlineKeyboardButton(
            "🎨 Brand Design", callback_data="view_cat_Brand_0")],
        [InlineKeyboardButton(
            "🖨️ Print Design", callback_data="view_cat_Print_0")],
        [InlineKeyboardButton("📱 Social Media Design",
                              callback_data="view_cat_Social_Media_0")],
        [InlineKeyboardButton("🎉 Event & Celebration Design",
                              callback_data="view_cat_Event_0")],
        [InlineKeyboardButton("📦 Package & Label Design",
                              callback_data="view_cat_Package_0")],
        [InlineKeyboardButton("👕 Merchandise Design",
                              callback_data="view_cat_Merchandise_0")],
        [InlineKeyboardButton("🌐 All in One", callback_data="view_cat_All_0")],
        [InlineKeyboardButton("🔙 Back to Main Menu",
                              callback_data="user_main_menu")]
    ]

    text = "📂 **እባክዎን ማየት የሚፈልጉትን የዲዛይን ዘርፍ ይምረጡ፦**"

    # ተጠቃሚው ከሚዲያ እይታ (Back) ሲል ወደ ካቴጎሪ ለመመለስ edit_message_text ፅሁፍ ላይ ብቻ ስለሚሰራ
    # ስህተት እንዳይፈጥር በ try/except አዲስ መልዕክት እንዲልክ እናደርገዋለን
    try:
        await query.edit_message_text(text=text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
    except Exception:
        try:
            await query.message.delete()
        except Exception:
            pass
        await context.bot.send_message(chat_id=query.message.chat_id, text=text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")


async def navigate_portfolio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """በፖርትፎሊዮ ስራዎች መካከል Next/Previous እያሉ ለመንቀሳቀስ የሚያስችል ዋና ሎጅክ"""
    query = update.callback_query
    await query.answer()

    # የ callback_data ፎርማት: view_cat_[Category]_[Index]
    # 'view_cat_' የሚለውን አጥፍቶ ከቀኝ በኩል ያለውን የመጨረሻውን _ በመቁረጥ ኢንዴክሱን እና ካቴጎሪውን በሰላም ይለያል
    raw_data = query.data.replace("view_cat_", "")
    category, index_str = raw_data.rsplit("_", 1)
    current_index = int(index_str)

    # ከዳታቤዝ ውስጥ ንቁ (is_active=True) የሆኑ ስራዎችን መጫን
    try:
        if category == "All":
            response = db.table("portfolio_items").select(
                "*").eq("is_active", True).order("id").execute()
        else:
            response = db.table("portfolio_items").select(
                "*").eq("category", category).eq("is_active", True).order("id").execute()

        items = response.data
    except Exception as e:
        print(f"Database error: {e}")
        await context.bot.send_message(chat_id=query.message.chat_id, text="❌ ዳታቤዝ ላይ ስህተት አጋጥሟል። እባክዎን ቆይተው ይሞክሩ።")
        return

    # ስራዎች በዚያ ዘርፍ ከሌሉ
    if not items:
        keyboard = [[InlineKeyboardButton(
            "🔙 Back to Categories", callback_data="user_portfolio")]]
        try:
            await query.edit_message_text(
                text="📭 **Dear Client, በዚህ ዘርፍ በአሁን ሰዓት የተቀመጡ የዲዛይን ስራዎች የሉም።**",
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode="Markdown"
            )
        except Exception:
            try:
                await query.message.delete()
            except Exception:
                pass
            await context.bot.send_message(
                chat_id=query.message.chat_id,
                text="📭 **Dear Client, በዚህ ዘርፍ በአሁን ሰዓት የተቀመጡ የዲዛይን ስራዎች የሉም።**",
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode="Markdown"
            )
        return

    # ማውጫው ከክልል ውጭ እንዳይሆን መቆጣጠሪያ
    if current_index < 0:
        current_index = 0
    if current_index >= len(items):
        current_index = len(items) - 1

    item = items[current_index]
    total_items = len(items)

    # መግለጫ ፅሁፍ (Mixed Format)
    caption = (
        f"📌 **Topic (ርዕስ):** {item['topic']}\n"
        f"📝 **Description (መግለጫ):** {item['description']}\n\n"
        f"🔢 *Item {current_index + 1} of {total_items}*"
    )

    # የቁልፎች (Dynamic Inline Keyboards) ዝግጅት
    nav_row = []
    if current_index > 0:
        nav_row.append(InlineKeyboardButton(
            "⬅️ Previous", callback_data=f"view_cat_{category}_{current_index - 1}"))
    if current_index < total_items - 1:
        nav_row.append(InlineKeyboardButton(
            "Next ➡️", callback_data=f"view_cat_{category}_{current_index + 1}"))

    keyboard = []
    if nav_row:
        keyboard.append(nav_row)

    keyboard.extend([
        [InlineKeyboardButton("🛍️ Order This Now",
                              callback_data=f"order_item_{item['id']}")],
        [InlineKeyboardButton(
            "💬 Contact Designer", url=f"https://t.me/{settings.DESIGNER_USERNAME}")],
        [InlineKeyboardButton(
            "💡 Give Feedback", callback_data=f"give_fb_{item['id']}")],
        [InlineKeyboardButton("🔙 Back", callback_data="user_portfolio"), InlineKeyboardButton(
            "🏠 Main Menu", callback_data="user_main_menu")]
    ])

    # ፅሁፍ ብቻ የነበረውን ሜሴጅ አጥፍቶ አዲስ ሚዲያ ለመላክ
    try:
        await query.message.delete()
    except Exception:
        pass

    # ሚዲያው ፎቶ ወይም ቪዲዮ መሆኑን በራስ-ሰር ለይቶ መላኪያ ሎጅክ
    try:
        # መጀመሪያ በፎቶ ለመላክ ይሞክራል
        await context.bot.send_photo(
            chat_id=query.message.chat_id,
            photo=item['file_id'],
            caption=caption,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )
    except Exception:
        # ፎቶ መላክ ካልቻለ ቪዲዮ ነው ማለት ስለሆነ በቪዲዮ ይልከዋል
        try:
            await context.bot.send_video(
                chat_id=query.message.chat_id,
                video=item['file_id'],
                caption=caption,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode="Markdown"
            )
        except Exception as video_error:
            print(f"Media sending error: {video_error}")
            # ሁለቱም ካልሰሩ ስህተት እንዳይፈጥር በፅሁፍ ብቻ ይልከዋል
            await context.bot.send_message(
                chat_id=query.message.chat_id,
                text=caption,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode="Markdown"
            )
