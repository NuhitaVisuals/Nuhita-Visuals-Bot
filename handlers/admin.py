import pandas as pd
import io
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
from config.database import get_db
from config.settings import settings

db = get_db()

# የ Add Portfolio እና Broadcast ስቴቶች
CHOOSING_CATEGORY, UPLOADING_MEDIA, ENTERING_TOPIC, ENTERING_DESCRIPTION, CONFIRMING_POST = range(
    5)
BROADCAST_WAITING = 5


def is_admin(chat_id: int) -> bool:
    """ላኪው አድሚን መሆኑን ያረጋግጣል"""
    return chat_id in settings.ADMIN_IDS


async def admin_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, edit=False):
    """የአድሚን መቆጣጠሪያ ዋና ሜኑ"""
    chat_id = update.effective_chat.id
    if not is_admin(chat_id):
        msg = "❌ This is for admin only! መዳረሻ አልተፈቀደሎትም።"
        if update.callback_query:
            await update.callback_query.message.reply_text(msg)
        else:
            await update.message.reply_text(msg)
        return

    msg = "⚙️ **የአድሚን መቆጣጠሪያ ሰሌዳ (Admin Panel)፦**"
    kb = [
        [InlineKeyboardButton("➕ Add Portfolio", callback_data="admin_add_portfolio"),
         InlineKeyboardButton("👁️ Active/Inactive", callback_data="admin_toggle_active")],
        [InlineKeyboardButton("🗑️ Delete", callback_data="admin_delete_main"),
         InlineKeyboardButton("📥 Verify Orders", callback_data="admin_verify_orders")],
        [InlineKeyboardButton("📊 Export CSV", callback_data="admin_export_csv"),
         InlineKeyboardButton("📢 Send Broadcast", callback_data="admin_send_broadcast")]
    ]

    if edit and update.callback_query:
        await update.callback_query.edit_message_text(text=msg, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")
    else:
        await context.bot.send_message(chat_id=chat_id, text=msg, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

# --- 1. ADD PORTFOLIO FLOW (የፖርትፎሊዮ መመዝገቢያ ሎጅክ) ---


async def start_add_portfolio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if not is_admin(update.effective_chat.id):
        return ConversationHandler.END

    msg = "📂 **ለመመዝገብ የሚፈልጉትን የሥራ ዘርፍ (Category) ይምረጡ፦**"
    kb = [
        [InlineKeyboardButton("🎨 Brand Design", callback_data="cat_Brand"),
         InlineKeyboardButton("🖨️ Print Design", callback_data="cat_Print")],
        [InlineKeyboardButton("📱 Social Media", callback_data="cat_Social_Media"),
         InlineKeyboardButton("🎉 Event Design", callback_data="cat_Event")],
        [InlineKeyboardButton("📦 Package Design", callback_data="cat_Package"),
         InlineKeyboardButton("👕 Merchandise", callback_data="cat_Merchandise")],
        [InlineKeyboardButton(
            "🔙 Back to Menu", callback_data="admin_back_to_menu")]
    ]
    await query.edit_message_text(text=msg, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")
    return CHOOSING_CATEGORY


async def category_chosen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    category = query.data.replace("cat_", "")
    context.user_data["p_category"] = category

    await query.message.reply_text("📸 **አሁን ደግሞ የሥራውን ፎቶ ወይም ቪዲዮ ይላኩሉኝ፦**\n_(ለማቋረጥ /cancel ማለት ይችላሉ)_")
    return UPLOADING_MEDIA


async def media_uploaded(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """አድሚኑ የላከውን ፎቶ ወይም ቪዲዮ ይቀበላል"""
    if not is_admin(update.effective_chat.id):
        return ConversationHandler.END

    if update.message.photo:
        file_id = update.message.photo[-1].file_id
        media_type = "photo"
    elif update.message.video:
        file_id = update.message.video.file_id
        media_type = "video"
    else:
        await update.message.reply_text("❌ እባክዎን ትክክለኛ ፎቶ ወይም ቪዲዮ ብቻ ይላኩ!")
        return UPLOADING_MEDIA

    context.user_data["p_file_id"] = file_id
    context.user_data["p_media_type"] = media_type

    await update.message.reply_text("📝 **አሁን ለዚህ ሥራ የሚሆን አጭር ርዕስ (Topic) ያስገቡ፦**")
    return ENTERING_TOPIC


async def topic_entered(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["p_topic"] = update.message.text
    await update.message.reply_text("✍️ **በመጨረሻም ስለ ሥራው ዝርዝር ማብራሪያ (Description) ይጻፉ፦**")
    return ENTERING_DESCRIPTION


async def description_entered(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["p_description"] = update.message.text

    caption = (
        f"✨ **የሥራው ርዕስ፦** {context.user_data['p_topic']}\n"
        f"📂 **ዘርፍ፦** {context.user_data['p_category']}\n\n"
        f"📝 **ማብራሪያ፦**\n{context.user_data['p_description']}"
    )

    kb = [
        [InlineKeyboardButton("✅ Confirm & Post", callback_data="post_confirm"),
         InlineKeyboardButton("❌ Cancel", callback_data="post_cancel")]
    ]

    if context.user_data["p_media_type"] == "photo":
        await update.message.reply_photo(photo=context.user_data["p_file_id"], caption=caption, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")
    else:
        await update.message.reply_video(video=context.user_data["p_file_id"], caption=caption, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

    return CONFIRMING_POST


async def confirm_post(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "post_confirm":
        try:
            # 🚨 እዚህ ጋር የሰንጠረዡ ስም ከ "portfolio" ወደ "portfolio_items" ተስተካክሏል፡
            db.table("portfolio_items").insert({
                "category": context.user_data["p_category"],
                "file_id": context.user_data["p_file_id"],
                "topic": context.user_data["p_topic"],
                "description": context.user_data["p_description"],
                "is_active": True
            }).execute()
            await query.edit_message_caption(caption="✅ ሥራው በተሳካ ሁኔታ ወደ ፖርትፎሊዮ ተጨምሯል!")
        except Exception as e:
            await query.edit_message_caption(caption=f"❌ ስህተት አጋጥሟል፤ መመዝገብ አልተቻለም። ስህተት፦ {e}")
    else:
        await query.edit_message_caption(caption="❌ የፖርትፎሊዮ ምዝገባው ተሰርዟል።")

    context.user_data.clear()
    return ConversationHandler.END


async def cancel_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ ሂደትዎ ተቋርጧል።")
    context.user_data.clear()
    return ConversationHandler.END

# --- 2. TOGGLE ACTIVE/INACTIVE ---


async def admin_toggle_main(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    try:
        # 🚨 የሰንጠረዥ ስም እዚህም ወደ portfolio_items ተቀይሯል
        items = db.table("portfolio_items").select(
            "id, topic, is_active").execute().data
    except Exception:
        await query.edit_message_text("🚨 የፖርትፎሊዮ መረጃዎችን ከዳታቤዝ ማግኘት አልተቻለም።")
        return

    if not items:
        await query.edit_message_text("📂 ምንም የተመዘገበ የፖርትፎሊዮ ስራ የለም።",
                                      reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="back_to_admin_main")]]))
        return

    msg = "👁️ **የስራዎች መታያ ሁኔታ ለመቀየር ይምረጡ (Active/Inactive)፦**"
    kb = []
    for item in items:
        status_icon = "🟢" if item['is_active'] else "🔴"
        kb.append([InlineKeyboardButton(
            f"{status_icon} {item['topic']}", callback_data=f"adm_tg_{item['id']}")])
    kb.append([InlineKeyboardButton("🔙 Back to Menu",
              callback_data="back_to_admin_main")])
    await query.edit_message_text(text=msg, reply_markup=InlineKeyboardMarkup(kb))


async def admin_handle_toggle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    item_id = int(query.data.replace("adm_tg_", ""))
    try:
        # 🚨 የሰንጠረዥ ስም እዚህም ወደ portfolio_items ተቀይሯል
        current = db.table("portfolio_items").select(
            "is_active").eq("id", item_id).execute().data[0]
        new_status = not current['is_active']
        db.table("portfolio_items").update(
            {"is_active": new_status}).eq("id", item_id).execute()
    except Exception:
        pass
    await admin_toggle_main(update, context)

# --- 3. DELETE PORTFOLIO ITEM ---


async def admin_delete_main(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    try:
        # 🚨 portfolio_items ተስተካክሏል
        items = db.table("portfolio_items").select("id, topic").execute().data
    except Exception:
        await query.edit_message_text("🚨 የፖርትፎሊዮ መረጃዎችን ማግኘት አልተቻለም።")
        return

    if not items:
        await query.edit_message_text("📂 ለመሰረዝ የሚችል ምንም ስራ የለም።",
                                      reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="back_to_admin_main")]]))
        return

    msg = "🗑️ **ለመሰረዝ የሚፈልጉትን ስራ በጥንቃቄ ይምረጡ፦**"
    kb = []
    for item in items:
        kb.append([InlineKeyboardButton(
            f"🗑️ {item['topic']}", callback_data=f"adm_del_{item['id']}")])
    kb.append([InlineKeyboardButton("🔙 Back to Menu",
              callback_data="back_to_admin_main")])
    await query.edit_message_text(text=msg, reply_markup=InlineKeyboardMarkup(kb))


async def admin_handle_delete(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    item_id = int(query.data.replace("adm_del_", ""))
    try:
        # 🚨 portfolio_items ተስተካክሏል
        db.table("portfolio_items").delete().eq("id", item_id).execute()
    except Exception:
        pass
    await admin_delete_main(update, context)


async def admin_back_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await admin_menu(update, context, edit=True)

# --- 4. VERIFY ORDERS ---


async def verify_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_chat.id):
        return
    context.user_data["v_index"] = 0
    await show_verify_page(update, context)


async def show_verify_page(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    try:
        orders = db.table("orders").select("*").eq("status",
                                                   "Pending").order("ordered_at").execute().data
    except Exception:
        msg = "🚨 ትዕዛዞችን ማግኘት አልተቻለም።"
        if query:
            await query.edit_message_text(msg)
        else:
            await update.message.reply_text(msg)
        return

    if not orders:
        msg = "📥 በአሁኑ ሰዓት ምንም ያልተመረመረ (Pending) ትዕዛዝ የለም።"
        if query:
            await query.edit_message_text(msg, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="back_to_admin_main")]]))
        else:
            await update.message.reply_text(msg)
        return

    idx = context.user_data.get("v_index", 0)
    if idx >= len(orders):
        idx = len(orders) - 1
        context.user_data["v_index"] = idx
    if idx < 0:
        idx = 0
        context.user_data["v_index"] = idx

    order = orders[idx]
    date_str = order['ordered_at'].split(
        "T")[0] if "T" in order['ordered_at'] else order['ordered_at']

    text = (
        f"📋 **የማረጋገጫ ቅጽ ({idx + 1}/{len(orders)})**\n\n"
        f"👤 **ደንበኛ፦** {order['client_name']}\n"
        f"📞 **ስልክ፦** `{order['phone_number']}`\n"
        f"📂 **የስራ ዘርፍ፦** {order['order_type']}\n"
        f"📍 **ቦታ፦** {order['location'] or 'ያልተጠቀሰ'}\n"
        f"📝 **ፍላጎት፦** {order['what_to_make']}\n"
        f"🔢 **ብዛት፦** {order['quantity']}\n"
        f"📅 **ቀን፦** {date_str}\n"
    )

    kb = [
        [InlineKeyboardButton("✅ Approve", callback_data=f"v_app_{order['order_id']}"),
         InlineKeyboardButton("❌ Reject", callback_data=f"v_rej_{order['order_id']}")]
    ]
    nav_buttons = []
    if idx > 0:
        nav_buttons.append(InlineKeyboardButton(
            "⬅️ Prev", callback_data="v_nav_prev"))
    if idx < len(orders) - 1:
        nav_buttons.append(InlineKeyboardButton(
            "Next ➡️", callback_data="v_nav_next"))
    if nav_buttons:
        kb.append(nav_buttons)
    kb.append([InlineKeyboardButton(
        "✖️ Close Verifier", callback_data="v_close_ver")])

    if query:
        await query.edit_message_text(text=text, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")
    else:
        await context.bot.send_message(chat_id=update.effective_chat.id, text=text, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")


async def handle_admin_callbacks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data
    await query.answer()

    if data == "back_to_admin_main":
        await admin_menu(update, context, edit=True)
        return
    if data == "admin_verify_orders":
        context.user_data["v_index"] = 0
        await show_verify_page(update, context)
        return
    if data == "v_close_ver":
        await admin_menu(update, context, edit=True)
        return
    if data.startswith("v_nav_"):
        direction = data.replace("v_nav_", "")
        curr = context.user_data.get("v_index", 0)
        context.user_data["v_index"] = curr - \
            1 if direction == "prev" else curr + 1
        await show_verify_page(update, context)
        return
    if data.startswith("v_app_") or data.startswith("v_rej_"):
        order_id = int(data.split("_")[-1])
        new_status = "Approved" if "v_app_" in data else "Rejected"
        try:
            db.table("orders").update({"status": new_status}).eq(
                "order_id", order_id).execute()
            order_data = db.table("orders").select("chat_id, what_to_make").eq(
                "order_id", order_id).execute().data[0]
            user_msg = f"🎉 ሰላም፣ በትዕዛዝ ቅጽዎ ላይ የቀረበው የ **'{order_data['what_to_make']}'** ስራ ፍላጎት በአድሚን **{new_status}** ሆኗል።" if new_status == "Approved" else f"❌ ይቅርታ፣ በትዕዛዝ ቅጽዎ ላይ የቀረበው የ **'{order_data['what_to_make']}'** ስራ ጥያቄ በአድሚን **ውድቅ (Rejected)** ተደርጓል።"
            await context.bot.send_message(chat_id=order_data['chat_id'], text=user_msg)
        except Exception:
            pass
        await show_verify_page(update, context)
        return

    if data == "admin_export_csv":
        try:
            orders = db.table("orders").select("*").execute().data
            if not orders:
                await query.edit_message_text("📊 በዳታቤዙ ውስጥ ምንም አይነት የትዕዛዝ መረጃ የለም።", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="back_to_admin_main")]]))
                return
            df = pd.DataFrame(orders)
            csv_buffer = io.StringIO()
            df.to_csv(csv_buffer, index=False, encoding='utf-8')
            csv_buffer.seek(0)
            bio = io.BytesIO(csv_buffer.getvalue().encode('utf-8'))
            bio.name = f"Nuhita_Orders_{datetime.now().strftime('%Y%m%d')}.csv"
            await context.bot.send_document(chat_id=update.effective_chat.id, document=bio, caption="📊 ይኸው የሁሉም ትዕዛዞች ዝርዝር በ CSV ፎርማት ተዘጋጅቶ ቀርቧል።")
            await admin_menu(update, context, edit=False)
        except Exception as e:
            await query.edit_message_text(f"❌ የ CSV ፋይል ማመንጨት አልተቻለም። ስህተት፦ {e}", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="back_to_admin_main")]]))

# --- 5. BROADCAST SYSTEM ---


async def broadcast_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_chat.id):
        return ConversationHandler.END
    await update.message.reply_text("📢 **ማሰራጨት የሚፈልጉትን መልዕክት አሁን ይላኩ።**\n_(ፎቶ፣ ቪዲዮ ወይም ፅሁፍ መላክ ይችላሉ፤ ለማቋረጥ /cancel ይበሉ)_")
    return BROADCAST_WAITING


async def broadcast_start_btn(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_chat.id):
        return ConversationHandler.END
    await context.bot.send_message(chat_id=update.effective_chat.id, text="📢 **ማሰራጨት የሚፈልጉትን መልዕክት አሁን ይላኩ።**\n_(ለማቋረጥ /cancel ይበሉ)_")
    return BROADCAST_WAITING


async def receive_broadcast_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    admin_msg = update.message
    try:
        users = db.table("users").select("chat_id").execute().data
    except Exception:
        await update.message.reply_text("🚨 ተጠቃሚዎችን ከዳታቤዝ ማግኘት አልተቻለም።")
        return ConversationHandler.END

    if not users:
        await update.message.reply_text("ምንም ተጠቃሚ አልተገኘም።")
        return ConversationHandler.END

    success_count = 0
    await update.message.reply_text(f"⏳ መልዕክቱ ለ {len(users)} ሰዎች እየተላከ ነው...")
    for u in users:
        try:
            await admin_msg.copy(chat_id=u["chat_id"])
            success_count += 1
        except Exception:
            pass

    await update.message.reply_text(f"📢 ማሰራጨቱ ተጠናቋል።\n✅ በተሳካ ሁኔታ የደረሳቸው፦ **{success_count}/{len(users)}**")
    return ConversationHandler.END


async def cancel_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ የማሰራጨት ሂደቱ ተሰርዟል።")
    return ConversationHandler.END
