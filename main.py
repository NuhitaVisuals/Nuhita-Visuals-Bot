# ከላይ ከነበረው መስመር ጋር እንዲህ አድርገህ አስተካክለው
from handlers.feedback import feedback_conv, admin_reply_conv
from handlers.feedback import feedback_conv
import logging
import threading
import uvicorn
import os
from fastapi import FastAPI
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ConversationHandler, MessageHandler, filters
from config.settings import settings
from handlers.user import start_command, handle_static_buttons, show_portfolio_categories, navigate_portfolio

# --- Admin & Order Imports (አንተ ካለህበት ኮድ እንደነበሩ ናቸው) ---
from handlers.admin import (
    start_add_portfolio, category_chosen, media_uploaded,
    topic_entered, description_entered, confirm_post, cancel_action,
    admin_toggle_main, admin_handle_toggle, admin_delete_main, admin_handle_delete, admin_back_button,
    CHOOSING_CATEGORY, UPLOADING_MEDIA, ENTERING_TOPIC, ENTERING_DESCRIPTION, CONFIRMING_POST,
    admin_menu, verify_command, handle_admin_callbacks,
    broadcast_command, broadcast_start_btn, receive_broadcast_message, cancel_admin, BROADCAST_WAITING
)

from handlers.order import (
    start_order_flow, order_name_entered, order_phone_entered, order_type_chosen,
    order_location_entered, order_requirements_entered, order_quantity_chosen,
    order_custom_quantity_entered, order_confirmed, cancel_order,
    ORDER_NAME, ORDER_PHONE, ORDER_TYPE, ORDER_LOCATION, ORDER_REQUIREMENTS, ORDER_QUANTITY, ORDER_CUSTOM_QUANTITY, ORDER_CONFIRMATION
)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)

# --- FastAPI Setup (Render Keep-Alive) ---
app = FastAPI()


@app.get("/ping")
async def ping():
    return {"status": "ok"}


def run_web_server():
    # Render የሚጠቀምበትን port በ Environment variable ይፈልጋል፣ ካልሆነ 10000 ይጠቀማል
    port = int(os.environ.get("PORT", 10000))
    uvicorn.run(app, host="0.0.0.0", port=port)


def main():
    # 1. ዌብ ሰርቨሩን በሌላ Thread አስጀምር
    threading.Thread(target=run_web_server, daemon=True).start()

    # 2. የቴሌግራም ቦት Application
    application = Application.builder().token(settings.BOT_TOKEN).build()

    # --- Handlers (አንተ የጻፍካቸው) ---
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CallbackQueryHandler(
        handle_static_buttons, pattern="^user_(main_menu|contact|about)$"))
    application.add_handler(CallbackQueryHandler(
        show_portfolio_categories, pattern="^user_portfolio$"))
    application.add_handler(CallbackQueryHandler(
        navigate_portfolio, pattern="^view_cat_"))
    application.add_handler(feedback_conv)
    application.add_handler(admin_reply_conv)  # ይህንን አዲስ መስመር ጨምር

    # Orders Handler
    order_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(start_order_flow, pattern="^user_order_start$"),
                      CallbackQueryHandler(start_order_flow, pattern="^order_item_")],
        states={
            ORDER_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, order_name_entered)],
            ORDER_PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, order_phone_entered),
                          CallbackQueryHandler(order_phone_entered, pattern="^back_to_name$")],
            ORDER_TYPE: [CallbackQueryHandler(order_type_chosen, pattern="^(type_|back_to_phone)")],
            ORDER_LOCATION: [MessageHandler(filters.TEXT & ~filters.COMMAND, order_location_entered),
                             CallbackQueryHandler(order_location_entered, pattern="^back_to_type$")],
            ORDER_REQUIREMENTS: [MessageHandler(filters.TEXT & ~filters.COMMAND, order_requirements_entered),
                                 CallbackQueryHandler(order_requirements_entered, pattern="^back_from_req$")],
            ORDER_QUANTITY: [CallbackQueryHandler(order_quantity_chosen, pattern="^(qty_|back_to_req)")],
            ORDER_CUSTOM_QUANTITY: [MessageHandler(filters.TEXT & ~filters.COMMAND, order_custom_quantity_entered),
                                    CallbackQueryHandler(order_custom_quantity_entered, pattern="^back_to_qty_opt$")],
            ORDER_CONFIRMATION: [CallbackQueryHandler(
                order_confirmed, pattern="^(order_confirm_submit|back_to_qty_opt)")]
        },
        fallbacks=[CallbackQueryHandler(
            cancel_order, pattern="^order_cancel$"), CommandHandler("cancel", cancel_order)]
    )
    application.add_handler(order_conv)

    # Admin Portfolio Handler
    # 2. የ Add Portfolio (የፖርትፎሊዮ መመዝገቢያ) Conversation Handler
    portfolio_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(
            start_add_portfolio, pattern="^admin_add_portfolio$")],
        states={
            CHOOSING_CATEGORY: [CallbackQueryHandler(category_chosen, pattern="^cat_")],
            # 🚨 የጎደለው እና ዋናው ስህተት የነበረው መስመር ይህ ነው (ፎቶ እና ቪዲዮ ይቀበላል)፦
            UPLOADING_MEDIA: [MessageHandler(filters.PHOTO | filters.VIDEO, media_uploaded)],
            ENTERING_TOPIC: [MessageHandler(filters.TEXT & ~filters.COMMAND, topic_entered)],
            ENTERING_DESCRIPTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, description_entered)],
            CONFIRMING_POST: [CallbackQueryHandler(
                confirm_post, pattern="^post_(confirm|cancel)$")]
        },
        fallbacks=[CommandHandler("cancel", cancel_action)],
        per_chat=True
    )
    application.add_handler(portfolio_conv)

    # Broadcast Handler
    broadcast_conv = ConversationHandler(
        entry_points=[CommandHandler("broadcast", broadcast_command),
                      CallbackQueryHandler(broadcast_start_btn, pattern="^admin_send_broadcast$")],
        states={BROADCAST_WAITING: [MessageHandler(
            filters.ALL & ~filters.COMMAND, receive_broadcast_message)]},
        fallbacks=[CommandHandler("cancel", cancel_admin)]
    )
    application.add_handler(broadcast_conv)

    # Other Admin Handlers
    application.add_handler(CommandHandler("admin", admin_menu))
    application.add_handler(CommandHandler("verify", verify_command))
    application.add_handler(CallbackQueryHandler(
        admin_toggle_main, pattern="^admin_toggle_active$"))
    application.add_handler(CallbackQueryHandler(
        admin_handle_toggle, pattern="^adm_tg_"))
    application.add_handler(CallbackQueryHandler(
        admin_delete_main, pattern="^admin_delete_main$"))
    application.add_handler(CallbackQueryHandler(
        admin_handle_delete, pattern="^adm_del_"))
    application.add_handler(CallbackQueryHandler(
        admin_back_button, pattern="^admin_back_to_menu$"))
    application.add_handler(CallbackQueryHandler(
        handle_admin_callbacks, pattern="^(admin_verify_orders|v_nav_|v_close_|admin_export_csv|back_to_admin_main)"))

    print("🚀 Nuhita Graphics Bot is running with Web Server...")

    # 3. Polling (read_timeout በመጨመር የTimeout ችግርን ይቀንሳል)
    application.run_polling(
        read_timeout=30, write_timeout=30, connect_timeout=30)


if __name__ == "__main__":
    main()
