import re
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
from config.database import get_db
from config.settings import settings

db = get_db()

# የትዕዛዝ ሂደቱ ስምንት ደረጃዎች (States)
ORDER_NAME, ORDER_PHONE, ORDER_TYPE, ORDER_LOCATION, ORDER_REQUIREMENTS, ORDER_QUANTITY, ORDER_CUSTOM_QUANTITY, ORDER_CONFIRMATION = range(
    8)

# ---- ደረጃዎችን መልሶ ለመጥራት የሚያገለግሉ የረዳት ተግባራት (PROMPT HELPERS) ----


async def prompt_name(update: Update, context: ContextTypes.DEFAULT_TYPE, text_prefix="", edit=False):
    msg = f"{text_prefix}የ Nuhita Graphics የትዕዛዝ መስጫ ቅጽ\n\nለመጀመር እባክዎን የእርስዎን ወይም የድርጅትዎን ሙሉ ስም ያስገቡ："
    kb = [[InlineKeyboardButton(
        "❌ Cancel Order", callback_data="order_cancel")]]

    if edit and update.callback_query:
        await update.callback_query.edit_message_text(text=msg, reply_markup=InlineKeyboardMarkup(kb))
    else:
        await context.bot.send_message(chat_id=update.effective_chat.id, text=msg, reply_markup=InlineKeyboardMarkup(kb))
    return ORDER_NAME


async def prompt_phone(update: Update, context: ContextTypes.DEFAULT_TYPE, text_prefix="", edit=False):
    msg = f"{text_prefix}እባክዎን ስልክ ቁጥርዎን ያስገቡ (ለምሳሌ፦ 09xxxxxxxx ወይም +2519xxxxxxxx)："
    kb = [
        [InlineKeyboardButton("🔄 Update Name (ስም ማስተካከያ)",
                              callback_data="back_to_name")],
        [InlineKeyboardButton("❌ Cancel Order", callback_data="order_cancel")]
    ]
    if edit and update.callback_query:
        await update.callback_query.edit_message_text(text=msg, reply_markup=InlineKeyboardMarkup(kb))
    else:
        await context.bot.send_message(chat_id=update.effective_chat.id, text=msg, reply_markup=InlineKeyboardMarkup(kb))
    return ORDER_PHONE


async def prompt_type(update: Update, context: ContextTypes.DEFAULT_TYPE, text_prefix="", edit=False):
    msg = f"{text_prefix}ምን አይነት አገልግሎት ይፈልጋሉ？"
    kb = [
        [InlineKeyboardButton("1. Print & Delivery", callback_data="type_print"),
         InlineKeyboardButton("2. Design Only", callback_data="type_design")],
        [InlineKeyboardButton("🔄 Update Phone (ስልክ ማስተካከያ)",
                              callback_data="back_to_phone")],
        [InlineKeyboardButton("❌ Cancel Order", callback_data="order_cancel")]
    ]
    if edit and update.callback_query:
        await update.callback_query.edit_message_text(text=msg, reply_markup=InlineKeyboardMarkup(kb))
    else:
        await context.bot.send_message(chat_id=update.effective_chat.id, text=msg, reply_markup=InlineKeyboardMarkup(kb))
    return ORDER_TYPE


async def prompt_location(update: Update, context: ContextTypes.DEFAULT_TYPE, text_prefix="", edit=False):
    msg = f"{text_prefix}እባክዎን ዲዛይኑ ታትሞ የሚደርስበትን ትክክለኛ ቦታ (Location/Address) በፅሁፍ ያስገቡ："
    kb = [
        [InlineKeyboardButton(
            "🔄 Update Order Type (አይነት ማስተካከያ)", callback_data="back_to_type")],
        [InlineKeyboardButton("❌ Cancel Order", callback_data="order_cancel")]
    ]
    if edit and update.callback_query:
        await update.callback_query.edit_message_text(text=msg, reply_markup=InlineKeyboardMarkup(kb))
    else:
        await context.bot.send_message(chat_id=update.effective_chat.id, text=msg, reply_markup=InlineKeyboardMarkup(kb))
    return ORDER_LOCATION


async def prompt_requirements(update: Update, context: ContextTypes.DEFAULT_TYPE, text_prefix="", edit=False):
    msg = f"{text_prefix}ምን ማሰራት ፈለጉ? ስለ ስራው ዝርዝር መግለጫ እዚህ ይፃፉሌን："
    kb = [
        [InlineKeyboardButton(
            "🔄 Update Previous Step (ወደ ኋላ መመለሻ)", callback_data="back_from_req")],
        [InlineKeyboardButton("❌ Cancel Order", callback_data="order_cancel")]
    ]
    if edit and update.callback_query:
        await update.callback_query.edit_message_text(text=msg, reply_markup=InlineKeyboardMarkup(kb))
    else:
        await context.bot.send_message(chat_id=update.effective_chat.id, text=msg, reply_markup=InlineKeyboardMarkup(kb))
    return ORDER_REQUIREMENTS


async def prompt_quantity(update: Update, context: ContextTypes.DEFAULT_TYPE, text_prefix="", edit=False):
    msg = f"{text_prefix}ምን ያህል ብዛት (Quantity) ይፈልጋሉ？"
    kb = [
        [InlineKeyboardButton("1", callback_data="qty_1"),
         InlineKeyboardButton("2", callback_data="qty_2"),
         InlineKeyboardButton("3", callback_data="qty_3")],
        [InlineKeyboardButton("4", callback_data="qty_4"),
         InlineKeyboardButton("5", callback_data="qty_5"),
         InlineKeyboardButton("Other (ሌላ ቁጥር)", callback_data="qty_other")],
        [InlineKeyboardButton(
            "🔄 Update Details (መግለጫ ማስተካከያ)", callback_data="back_to_req")],
        [InlineKeyboardButton("❌ Cancel Order", callback_data="order_cancel")]
    ]
    if edit and update.callback_query:
        await update.callback_query.edit_message_text(text=msg, reply_markup=InlineKeyboardMarkup(kb))
    else:
        await context.bot.send_message(chat_id=update.effective_chat.id, text=msg, reply_markup=InlineKeyboardMarkup(kb))
    return ORDER_QUANTITY


async def prompt_custom_quantity(update: Update, context: ContextTypes.DEFAULT_TYPE, text_prefix="", edit=False):
    msg = f"{text_prefix}እባክዎን የሚፈልጉትን ብዛት በቁጥር ብቻ ያስገቡ："
    kb = [
        [InlineKeyboardButton(
            "🔄 Update Quantity Choice (ምርጫ ማስተካከያ)", callback_data="back_to_qty_opt")],
        [InlineKeyboardButton("❌ Cancel Order", callback_data="order_cancel")]
    ]
    if edit and update.callback_query:
        await update.callback_query.edit_message_text(text=msg, reply_markup=InlineKeyboardMarkup(kb))
    else:
        await context.bot.send_message(chat_id=update.effective_chat.id, text=msg, reply_markup=InlineKeyboardMarkup(kb))
    return ORDER_CUSTOM_QUANTITY


async def prompt_confirmation(update: Update, context: ContextTypes.DEFAULT_TYPE, edit=False):
    data = context.user_data
    msg = (
        "የማዘዣ ቅጽ ማጠቃለያ (Order Summary)\n\n"
        f"Client Name: {data.get('client_name')}\n"
        f"Phone Number: {data.get('phone_number')}\n"
        f"Order Type: {data.get('order_type')}\n"
        f"Location: {data.get('location', 'N/A')}\n"
        f"Details: {data.get('what_to_make')}\n"
        f"Quantity: {data.get('quantity')}\n\n"
        "ይህ ትዕዛዝዎ በትክክል ተመዝግቦ ለ Nuhita Graphics ቡድን ይላክ?"
    )
    kb = [
        [InlineKeyboardButton("✅ Confirm & Send Order",
                              callback_data="order_confirm_submit")],
        [InlineKeyboardButton("🔄 Update Quantity (ብዛት ማስተካከያ)",
                              callback_data="back_to_qty_opt")],
        [InlineKeyboardButton("❌ Cancel Order", callback_data="order_cancel")]
    ]
    if edit and update.callback_query:
        await update.callback_query.edit_message_text(text=msg, reply_markup=InlineKeyboardMarkup(kb))
    else:
        await context.bot.send_message(chat_id=update.effective_chat.id, text=msg, reply_markup=InlineKeyboardMarkup(kb))
    return ORDER_CONFIRMATION

# ---- የውሂብ መቀበያ እና የክስተት አያያዝ ሎጅኮች (FLOW LOGIC HANDLERS) ----


async def start_order_flow(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """የማዘዝ ሂደቱን መጀመሪያ ያስነሳል"""
    if update.callback_query:
        query = update.callback_query
        await query.answer()
        try:
            await query.message.delete()
        except Exception:
            pass
    context.user_data.clear()
    return await prompt_name(update, context, edit=False)


async def order_name_entered(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """ስም ሲገባ ይቀበላል"""
    if update.callback_query:
        await update.callback_query.answer()
        return await prompt_name(update, context, edit=True)

    context.user_data["client_name"] = update.message.text
    return await prompt_phone(update, context, edit=False)


async def order_phone_entered(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """ስልክ ሲገባ በRegex ያረጋግጣል"""
    if update.callback_query:
        query = update.callback_query
        await query.answer()
        if query.data == "back_to_name":
            return await prompt_name(update, context, edit=True)

    phone = update.message.text
    if not re.match(r"^(\+251|0)(9|7)\d{8}$", phone):
        return await prompt_phone(update, context, text_prefix="የተሳሳተ የስልክ ቁጥር ነው። እባክዎን እንደገና በደንብ ያስገቡ፦\n", edit=False)

    context.user_data["phone_number"] = phone
    return await prompt_type(update, context, edit=False)


async def order_type_chosen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """የአገልግሎት ዓይነት ምርጫን ያስተናግዳል"""
    if not update.callback_query:
        return ORDER_TYPE

    query = update.callback_query
    await query.answer()

    if query.data == "back_to_phone":
        return await prompt_phone(update, context, edit=True)

    if query.data == "type_print":
        context.user_data["order_type"] = "Print and Delivery"
        return await prompt_location(update, context, edit=True)
    elif query.data == "type_design":
        context.user_data["order_type"] = "Design Only"
        context.user_data["location"] = "N/A"
        return await prompt_requirements(update, context, edit=True)


async def order_location_entered(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """የማድረሻ ቦታ ሲገባ ይቀበላል"""
    if update.callback_query:
        query = update.callback_query
        await query.answer()
        if query.data == "back_to_type":
            return await prompt_type(update, context, edit=True)

    context.user_data["location"] = update.message.text
    return await prompt_requirements(update, context, edit=False)


async def order_requirements_entered(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """ስለ ስራው ማብራሪያ ሲገባ ይቀበላል"""
    if update.callback_query:
        query = update.callback_query
        await query.answer()
        if query.data == "back_from_req":
            if context.user_data.get("order_type") == "Print and Delivery":
                return await prompt_location(update, context, edit=True)
            else:
                return await prompt_type(update, context, edit=True)

    context.user_data["what_to_make"] = update.message.text
    return await prompt_quantity(update, context, edit=False)


async def order_quantity_chosen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """የብዛት ቁልፍ ሲጫን ያስተናግዳል"""
    if not update.callback_query:
        return ORDER_QUANTITY

    query = update.callback_query
    await query.answer()

    if query.data == "back_to_req":
        return await prompt_requirements(update, context, edit=True)

    if query.data == "qty_other":
        return await prompt_custom_quantity(update, context, edit=True)

    if query.data.startswith("qty_"):
        qty = query.data.split("_")[1]
        context.user_data["quantity"] = qty
        return await prompt_confirmation(update, context, edit=True)


async def order_custom_quantity_entered(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """የራስን የብዛት ቁጥር በፅሁፍ ሲያስገቡ በኮድ ያረጋግጣል"""
    if update.callback_query:
        query = update.callback_query
        await query.answer()
        if query.data == "back_to_qty_opt":
            return await prompt_quantity(update, context, edit=True)

    text = update.message.text
    if not text.isdigit():
        return await prompt_custom_quantity(update, context, text_prefix="እባክዎን ቁጥር ብቻ ያስገቡ፦\n", edit=False)

    context.user_data["quantity"] = text
    return await prompt_confirmation(update, context, edit=False)


async def order_confirmation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """ትዕዛዙን አረጋግጦ ዳታቤዝ ላይ ይጭናል"""
    if not update.callback_query:
        return ORDER_CONFIRMATION

    query = update.callback_query
    await query.answer()

    if query.data == "back_to_qty_opt":
        return await prompt_quantity(update, context, edit=True)

    if query.data == "order_confirm_submit":
        chat_id = query.message.chat_id
        user = query.from_user
        data = context.user_data

        try:
            db.table("orders").insert({
                "chat_id": chat_id,
                "client_name": data.get("client_name"),
                "phone_number": data.get("phone_number"),
                "order_type": data.get("order_type"),
                "location": data.get("location"),
                "what_to_make": data.get("what_to_make"),
                "quantity": data.get("quantity"),
                "status": "Pending"
            }).execute()

            await query.edit_message_text("✅Your order has been accepted! We will contact you soon. Dear client, ስለመረጡን እናመሰግናለን።")

            # ለአድሚን የሚደርስ ፈጣን የትዕዛዝ ማሳወቂያ
            admin_alert = (
                "🔔 Nuhamin አዲስ የትዕዛዝ መልዕክት ደርሷል! (New Order)\n\n"
                f"Client Name: {data.get('client_name')}\n"
                f"Phone Number: {data.get('phone_number')}\n"
                f"Order Type: {data.get('order_type')}\n"
                f"Location: {data.get('location')}\n"
                f"Telegram Address: @{user.username if user.username else 'No Username'}\n"
                f"What to Make: {data.get('what_to_make')}\n"
                f"Quantity: {data.get('quantity')}"
            )

            for admin_id in settings.ADMIN_IDS:
                try:
                    await context.bot.send_message(chat_id=admin_id, text=admin_alert)
                except Exception as admin_err:
                    print(f"Admin Notification Error: {admin_err}")

        except Exception as e:
            print(f"🚨 Supabase Insertion Error Detail: {e}")
            await query.edit_message_text("❌ ይቅርታ ትዕዛዝዎን መመዝገብ አልተቻለም። እባክዎን ቆይተው ይሞክሩ።")

        context.user_data.clear()
        return ConversationHandler.END


async def cancel_order(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """ሂደቱን ሙሉ በሙሉ ያቋርጣል"""
    query = update.callback_query if update.callback_query else update
    cancel_msg = "❌ የትዕዛዝ ሂደቱ ተሰርዟል። በማንኛውም ጊዜ ማዘዝ ይችላሉ።"

    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(text=cancel_msg)
    else:
        await update.message.reply_text(text=cancel_msg)

    context.user_data.clear()
    return ConversationHandler.END
