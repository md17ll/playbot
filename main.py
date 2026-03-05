from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

from config import BOT_TOKEN, DATABASE_URL
from db import init_db, execute
import user_flow
import admin_flow


def upsert_user(update: Update):
    u = update.effective_user
    if not u:
        return
    execute(
        """
        INSERT INTO users (user_id, username, first_name)
        VALUES (%s, %s, %s)
        ON CONFLICT (user_id) DO UPDATE SET username=EXCLUDED.username, first_name=EXCLUDED.first_name
        """,
        (u.id, u.username or "", u.first_name or ""),
    )
    execute(
        """
        INSERT INTO balances (user_id, balance)
        VALUES (%s, 0)
        ON CONFLICT (user_id) DO NOTHING
        """,
        (u.id,),
    )


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    upsert_user(update)
    await user_flow.show_home(update, context)


async def on_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    if not q:
        return

    await q.answer()
    upsert_user(update)

    data = q.data or ""

    # Back
    if data == "nav:back":
        await user_flow.go_back(update, context)
        return

    # Home
    if data == "home:shop":
        await user_flow.show_shop(update, context)
        return
    if data == "home:topup":
        await user_flow.show_balance(update, context)
        return
    if data == "home:coupon":
        await user_flow.show_coupon(update, context)
        return
    if data == "home:referral":
        await user_flow.show_referral(update, context)
        return
    if data == "home:orders":
        await user_flow.show_orders(update, context)
        return

    # Shop
    if data == "shop:subscriptions":
        await user_flow.show_subscriptions(update, context)
        return
    if data == "shop:games":
        await user_flow.show_games(update, context)
        return

    # Admin Panel
    if data == "admin:panel":
        await admin_flow.show_admin_panel(update, context)
        return
    if data == "admin:edit_start":
        await admin_flow.admin_edit_start(update, context)
        return
    if data == "admin:orders":
        await admin_flow.admin_orders(update, context)
        return
    if data == "admin:search_orders":
        await admin_flow.admin_search_orders(update, context)
        return
    if data == "admin:broadcast":
        await admin_flow.admin_broadcast(update, context)
        return
    if data == "admin:stats":
        await admin_flow.admin_stats(update, context)
        return

    # ✅ FIX: wire missing admin buttons (they were "for show")
    if data == "admin:products":
        await admin_flow.admin_products(update, context)
        return
    if data == "admin:coupons":
        await admin_flow.admin_coupons(update, context)
        return
    if data == "admin:balance":
        await admin_flow.admin_balance(update, context)
        return

    # Admin order actions
    if data.startswith("order:done:"):
        try:
            order_id = int(data.split(":")[2])
            await admin_flow.admin_order_done(update, context, order_id)
        except Exception:
            pass
        return

    if data.startswith("order:cancel:"):
        try:
            order_id = int(data.split(":")[2])
            await admin_flow.admin_order_cancel(update, context, order_id)
        except Exception:
            pass
        return


async def on_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    upsert_user(update)

    # ✅ admin states (edit start / search / broadcast / products / coupons / balance commands)
    await admin_flow.handle_admin_text(update, context)

    # ✅ FIX: pass user text to user_flow (coupon/topup/etc)
    handled = await user_flow.handle_text(update, context)
    if handled:
        return

    # fallback (only if nothing handled)
    await update.message.reply_text("استخدم الأزرار 👇 أو اكتب /start لعرض القائمة.")


async def on_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    upsert_user(update)

    # ✅ FIX: allow user_flow to accept proofs as photo
    handled = await user_flow.handle_photo(update, context)
    if handled:
        return

    # إذا الصورة ليست ضمن أي خطوة
    await update.message.reply_text("استخدم الأزرار 👇 أو اكتب /start لعرض القائمة.")


def main():
    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN غير موجود. ضعه في Railway Variables.")
    if not DATABASE_URL:
        raise RuntimeError("DATABASE_URL غير موجود. فعّل PostgreSQL على Railway وسيظهر المتغير تلقائياً.")

    init_db()

    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(on_callback))

    # ✅ NEW: photos
    app.add_handler(MessageHandler(filters.PHOTO, on_photo))

    # texts
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_text))

    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
