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
        [InlineKeyboardButton("➕ Add Portfolio", callback_data="admin_add_port"),
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

# አድሚን ሜኑን ለmain.py እንዲስማማ አሊያስ (Alias) ማድረግ
admin_command = admin_menu

# ==========================================
# 1. ADD PORTFOLIO LOGIC
# ==========================================


async def start_add_portfolio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    keyboard = [
        [InlineKeyboardButton(
            "🎨 Brand Design", callback_data="add_cat_Brand")],
        [InlineKeyboardButton(
            "🖨️ Print Design", callback_data="add_cat_Print")],
        [InlineKeyboardButton("📱 Social Media Design",
                              callback_data="add_cat_Social_Media")],
        [InlineKeyboardButton("🎉 Event & Celebration",
                              callback_data="add_cat_Event")],
        [InlineKeyboardButton("📦 Package & Label",
                              callback_data="add_cat_Package")],
        [InlineKeyboardButton("👕 Merchandise Design",
                              callback_data="add_cat_Merchandise")],
        [InlineKeyboardButton("❌ Cancel", callback_data="admin_cancel")]
    ]
    await query.edit_message_text("📂 እባክዎን የዲዛይኑን ዘርፍ (Category) ይምረጡ፦", reply_markup=InlineKeyboardMarkup(keyboard))
    return CHOOSING_CATEGORY


async def category_chosen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data["add_port_category"] = query.data.replace("add_cat_", "")
    await query.edit_message_text("📸 እባክዎን የዲዛይኑን ፎቶ ወይም ቪዲዮ ይልኩ፦\n(ለማቋረጥ /cancel ይበሉ)")
    return UPLOADING_MEDIA


async def media_uploaded(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.photo:
        file_id = update.message.photo[-1].file_id
    elif update.message.video:
        file_id = update.message.video.file_id
    else:
        await update.message.reply_text("❌ እባክዎን ትክክለኛ ፎቶ ወይም ቪዲዮ ብቻ ይላኩ።")
        return UPLOADING_MEDIA

    context.user_data["add_port_file_id"] = file_id
    await update.message.reply_text("📝 አሁን ደግሞ የዲዛይኑን ርዕስ (Topic) ያስገቡ፦\n(English & Amharic Mixed መሆን ይችላል)")
    return ENTERING_TOPIC


async def topic_entered(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["add_port_topic"] = update.message.text
    await update.message.reply_text("📝 ስለ ዲዛይኑ ዝርዝር መግለጫ (Description) ያስገቡ፦")
    return ENTERING_DESCRIPTION


async def description_entered(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["add_port_description"] = update.message.text

    keyboard = [
        [InlineKeyboardButton("✅ Post Portfolio",
                              callback_data="admin_confirm_post")],
        [InlineKeyboardButton("❌ Cancel", callback_data="admin_cancel")]
    ]

    summary = (
        f"📌 **Category:** {context.user_data['add_port_category']}\n"
        f"📌 **Topic:** {context.user_data['add_port_topic']}\n"
        f"📝 **Description:** {context.user_data['add_port_description']}\n\n"
        "ይህ ስራ በፖርትፎሊዮ ውስጥ ይግባ?"
    )
    await update.message.reply_text(summary, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
    return CONFIRMING_POST


async def confirm_post(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    cat = context.user_data.get("add_port_category")
    f_id = context.user_data.get("add_port_file_id")
    top = context.user_data.get("add_port_topic")
    desc = context.user_data.get("add_port_description")

    if cat == "Social":
        cat = "Social_Media"
    if cat == "Merchandise Design":
        cat = "Merchandise"

    try:
        db.table("portfolio_items").insert({
            "category": cat,
            "file_id": f_id,
            "topic": top,
            "description": desc,
            "is_active": True
        }).execute()
        await query.edit_message_text("✅ **የዲዛይን ስራው በስኬት ተመዝግቧል!**", parse_mode="Markdown")
    except Exception as e:
        print(f"🚨 SUPABASE INSERTION ERROR DETAILED: {e}")
        await query.edit_message_text("❌ ስራውን በዳታቤዝ ላይ ለመመዝገብ ስህተት አጋጥሟል።")

    context.user_data.clear()
    return ConversationHandler.END


async def cancel_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query:
        await query.answer()
        await query.edit_message_text("❌ እርምጃው ተቋርጧል።")
    else:
        await update.message.reply_text("❌ እርምጃው ተቋርጧል።")
    context.user_data.clear()
    return ConversationHandler.END

# ==========================================
# 2. ACTIVE/INACTIVE & DELETE LOGIC
# ==========================================


async def admin_toggle_main(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    try:
        response = db.table("portfolio_items").select(
            "id", "topic", "is_active").order("id").execute()
        items = response.data
    except Exception as e:
        await query.edit_message_text("❌ ስራዎችን ከዳታቤዝ ለመጫን አልተቻለም።")
        return

    if not items:
        keyboard = [[InlineKeyboardButton(
            "🔙 Back to Admin Menu", callback_data="admin_back_to_menu")]]
        await query.edit_message_text("📭 በዳታቤዝ ውስጥ ምንም የዲዛይን ስራ የለም።", reply_markup=InlineKeyboardMarkup(keyboard))
        return

    keyboard = []
    for item in items:
        status_icon = "🟢" if item.get("is_active") else "🔴"
        keyboard.append([InlineKeyboardButton(
            f"{status_icon} {item['topic']}", callback_data=f"adm_tg_{item['id']}")])

    keyboard.append([InlineKeyboardButton(
        "🔙 Back to Admin Menu", callback_data="admin_back_to_menu")])

    await query.edit_message_text(
        "🔄 **የስራዎችን መታየት (Visibility) ለመቀየር አንዱን ይጫኑ፦**",
        reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown"
    )


async def admin_handle_toggle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    item_id = int(query.data.split("_")[2])

    try:
        res = db.table("portfolio_items").select(
            "is_active").eq("id", item_id).execute()
        if res.data:
            current_status = res.data[0]["is_active"]
            db.table("portfolio_items").update(
                {"is_active": not current_status}).eq("id", item_id).execute()
            await admin_toggle_main(update, context)
    except Exception as e:
        print(f"🚨 Toggle Error: {e}")


async def admin_delete_main(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    try:
        response = db.table("portfolio_items").select(
            "id", "topic").order("id").execute()
        items = response.data
    except Exception:
        await query.edit_message_text("❌ ስራዎችን ለመጫን አልተቻለም።")
        return

    if not items:
        keyboard = [[InlineKeyboardButton(
            "🔙 Back to Admin Menu", callback_data="admin_back_to_menu")]]
        await query.edit_message_text("📭 የሚሰረዝ ምንም የዲዛይን ስራ የለም።", reply_markup=InlineKeyboardMarkup(keyboard))
        return

    keyboard = [[InlineKeyboardButton(
        f"🗑️ {item['topic']}", callback_data=f"adm_del_{item['id']}")] for item in items]
    keyboard.append([InlineKeyboardButton(
        "🔙 Back to Admin Menu", callback_data="admin_back_to_menu")])

    await query.edit_message_text(
        "🗑️ **ከዳታቤዝ ለማጥፋት የሚፈልጉትን ስራ ይምረጡ፦**",
        reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown"
    )


async def admin_handle_delete(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    item_id = int(query.data.split("_")[2])

    try:
        db.table("portfolio_items").delete().eq("id", item_id).execute()
        await query.edit_message_text("🗑️ **የዲዛይን ስራው ተሰርዟል!**", parse_mode="Markdown")
    except Exception:
        await query.edit_message_text("❌ ስራውን መሰረዝ አልተቻለም።")


async def admin_back_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await admin_menu(update, context, edit=True)

# ==========================================
# 3. VERIFY ORDERS, EXPORT CSV & BROADCAST
# ==========================================


async def verify_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if not is_admin(chat_id):
        await update.message.reply_text("❌ This is for admin only! መዳረሻ አልተፈቀደሎትም።")
        return
    context.user_data["verify_index"] = 0
    return await show_pending_order(update, context, edit=False)


async def handle_admin_callbacks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    chat_id = update.effective_chat.id
    if not is_admin(chat_id):
        return

    data = query.data

    if data == "admin_verify_orders":
        context.user_data["verify_index"] = 0
        await show_pending_order(update, context, edit=True)
    elif data.startswith("v_nav_"):
        direction = data.split("_")[2]
        if direction == "next":
            context.user_data["verify_index"] = context.user_data.get(
                "verify_index", 0) + 1
        elif direction == "prev":
            context.user_data["verify_index"] = context.user_data.get(
                "verify_index", 0) - 1
        await show_pending_order(update, context, edit=True)
    elif data.startswith("v_close_"):
        order_id = data.split("_")[2]
        await close_order_action(update, context, order_id)
    elif data == "admin_export_csv":
        await export_csv_action(update, context)
    elif data == "back_to_admin_main":
        await admin_menu(update, context, edit=True)


async def show_pending_order(update: Update, context: ContextTypes.DEFAULT_TYPE, edit=False):
    try:
        response = db.table("orders").select(
            "*").eq("status", "Pending").order("order_id").execute()
        orders = response.data
    except Exception:
        msg = "🚨 ትዕዛዞችን ማምጣት አልተቻለም።"
        if edit and update.callback_query:
            await update.callback_query.edit_message_text(msg)
        else:
            await context.bot.send_message(chat_id=update.effective_chat.id, text=msg)
        return

    if not orders:
        msg = "📥 Nuhamin, በአሁኑ ሰዓት ምንም ያልተረጋገጠ (Pending) ትዕዛዝ የለም።"
        kb = [[InlineKeyboardButton(
            "⬅️ Back to Admin Panel", callback_data="back_to_admin_main")]]
        if edit and update.callback_query:
            await update.callback_query.edit_message_text(text=msg, reply_markup=InlineKeyboardMarkup(kb))
        else:
            await context.bot.send_message(chat_id=update.effective_chat.id, text=msg, reply_markup=InlineKeyboardMarkup(kb))
        return

    index = context.user_data.get("verify_index", 0)
    if index < 0:
        index = 0
    if index >= len(orders):
        index = len(orders) - 1
    context.user_data["verify_index"] = index

    order = orders[index]
    msg = (
        f"የትዕዛዝ ማረጋገጫ ገጽ (Verify Order) - {index + 1}/{len(orders)}\n\n"
        f"Order ID: {order['order_id']}\n"
        f"Client Name: {order['client_name']}\n"
        f"Phone Number: {order['phone_number']}\n"
        f"Order Type: {order['order_type']}\n"
        f"Location: {order['location'] if order['location'] else 'N/A'}\n"
        f"Details: {order['what_to_make']}\n"
        f"Quantity: {order['quantity']}\n"
        f"Status: {order['status']}"
    )

    nav_row = []
    if index > 0:
        nav_row.append(InlineKeyboardButton(
            "⬅️ Previous", callback_data="v_nav_prev"))
    if index < len(orders) - 1:
        nav_row.append(InlineKeyboardButton(
            "Next ➡️", callback_data="v_nav_next"))

    kb = [
        nav_row,
        [InlineKeyboardButton("✅ Verify & Close Order",
                              callback_data=f"v_close_{order['order_id']}")],
        [InlineKeyboardButton("⬅️ Back to Admin Panel",
                              callback_data="back_to_admin_main")]
    ]

    if edit and update.callback_query:
        await update.callback_query.edit_message_text(text=msg, reply_markup=InlineKeyboardMarkup(kb))
    else:
        await context.bot.send_message(chat_id=update.effective_chat.id, text=msg, reply_markup=InlineKeyboardMarkup(kb))


async def close_order_action(update: Update, context: ContextTypes.DEFAULT_TYPE, order_id: str):
    query = update.callback_query
    try:
        res = db.table("orders").select("*").eq("order_id", order_id).execute()
        if not res.data:
            return await query.edit_message_text("❌ ትዕዛዙ አልተገኘም።")

        order_data = res.data[0]
        db.table("orders").update({"status": "Order Closed"}).eq(
            "order_id", order_id).execute()

        kb = [[InlineKeyboardButton(
            "⬅️ Back to Orders List", callback_data="admin_verify_orders")]]
        await query.edit_message_text(f"✅ Order ID {order_id} ተዘግቷል (Order Closed)።", reply_markup=InlineKeyboardMarkup(kb))

        success_msg = (
            "🎉 ስራዎ በስኬት ተጠናቋል! (Order Successfully Completed!)\n\n"
            "Dear client, ከእኛ ጋር አብረው ስለሰሩ እና ስላመኑን እጅግ አድርገን እናመሰግናለን። "
            "በቀጣይም አብረን ትልልቅ ለውጥ የሚያመጡ እና ለቢዝነስዎ እሴት የሚጨምሩ ስራዎችን እንደምንሰራ ሙሉ ተስፋ አለን!\n\n"
            "Nuhita Visuals🤝"
        )
        try:
            await context.bot.send_message(chat_id=order_data["chat_id"], text=success_msg)
        except Exception:
            pass
    except Exception:
        await query.edit_message_text("❌ ትዕዛዙን በማጽደቅ ሂደት ላይ ስህተት አጋጥሟል።")


async def export_csv_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query:
        await query.edit_message_text("⏳ ዳታውን እያዘጋጀሁ ነው፣ እባክዎ ይጠብቁ...")

    try:
        response = db.table("orders").select("*").execute()
        orders = response.data
        if not orders:
            return await context.bot.send_message(chat_id=update.effective_chat.id, text="📥 እስካሁን ምንም የተመዘገበ ትዕዛዝ የለም።")

        formatted_orders = []
        for o in orders:
            local_time = "N/A"
            if o.get("ordered_at"):
                try:
                    utc_time = datetime.fromisoformat(
                        o["ordered_at"].replace("Z", "+00:00"))
                    eth_time = utc_time + timedelta(hours=3)
                    local_time = eth_time.strftime("%Y-%m-%d %I:%M %p")
                except:
                    local_time = o["ordered_at"]

            formatted_orders.append({
                "Order_ID": o.get("order_id"),
                "Client_Name": o.get("client_name"),
                "Phone": o.get("phone_number"),
                "Type": o.get("order_type"),
                "Location": o.get("location", "N/A"),
                "Details": o.get("what_to_make"),
                "Quantity": o.get("quantity"),
                "Status": o.get("status"),
                "Date_Time": local_time
            })

        df = pd.DataFrame(formatted_orders)
        csv_buffer = io.BytesIO()
        df.to_csv(csv_buffer, index=False, encoding='utf-8-sig')
        csv_buffer.seek(0)

        await context.bot.send_document(
            chat_id=update.effective_chat.id,
            document=csv_buffer,
            filename="orders_report.csv",
            caption="📊 የ Nuhita Visuals ትዕዛዞች ሪፖርት (በኢትዮጵያ ሰዓት)"
        )
    except Exception as e:
        await context.bot.send_message(chat_id=update.effective_chat.id, text="❌ ሪፖርቱን ማውረድ አልተቻለም።")


async def broadcast_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_chat.id):
        return ConversationHandler.END
    await update.message.reply_text("📢 ለሁሉም ተጠቃሚዎች ማሰራጨት የሚፈልጉትን መልዕክት አሁን ይላኩ። (ለማቋረጥ /cancel ይበሉ)")
    return BROADCAST_WAITING


async def broadcast_start_btn(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_chat.id):
        return ConversationHandler.END
    await context.bot.send_message(chat_id=update.effective_chat.id, text="📢 ማሰራጨት የሚፈልጉትን መልዕክት አሁን ይላኩ። (ለማቋረጥ /cancel ይበሉ)")
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
    await update.message.reply_text(f"✅ ብሮድካስት ተጠናቋል! ለ {success_count} ሰዎች በተሳካ ሁኔታ ደርሷል።")
    return ConversationHandler.END


async def cancel_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ እርምጃው ተቋርጧል።")
    return ConversationHandler.END
