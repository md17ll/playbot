from telegram import Update
from telegram.ext import ContextTypes

import texts
import keyboards
from utils import safe_edit_or_send, is_admin, nav_push, nav_pop, money
from db import fetch_all, fetch_one, execute
from config import SUPPORT_USERNAME


# ======================
# Admin Panel
# ======================

async def show_admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return

    nav_push(context, "admin_panel")

    await safe_edit_or_send(
        update,
        context,
        texts.ADMIN_PANEL_MESSAGE,
        keyboards.kb_admin_panel()
    )


# ======================
# Edit Start Message
# ======================

async def admin_edit_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return

    nav_push(context, "admin_edit_start")

    context.user_data["awaiting_new_start_message"] = True

    await safe_edit_or_send(
        update,
        context,
        "📝 أرسل الآن رسالة /start الجديدة (نص فقط).",
        keyboards.kb_back()
    )


async def handle_admin_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    هذا الهاندلر يستقبل رسائل الأدمن عندما يكون في وضع تعديل رسالة البدء
    أو بحث طلبات أو إذاعة.
    """
    if not is_admin(update.effective_user.id):
        return

    text = (update.message.text or "").strip()

    # تعديل رسالة البدء
    if context.user_data.get("awaiting_new_start_message"):
        context.user_data["awaiting_new_start_message"] = False
        texts.START_MESSAGE = text  # تعديل داخل الذاكرة (سنربطه بقاعدة البيانات في main.py)
        await update.message.reply_text("✅ تم تعديل رسالة البدء بنجاح.\nجرّب /start.")
        return

    # بحث بالطلبات
    if context.user_data.get("awaiting_order_search"):
        context.user_data["awaiting_order_search"] = False
        await admin_search_execute(update, context, text)
        return

    # إذاعة
    if context.user_data.get("awaiting_broadcast"):
        context.user_data["awaiting_broadcast"] = False
        await admin_broadcast_execute(update, context, text)
        return


# ======================
# Orders List
# ======================

async def admin_orders(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return

    nav_push(context, "admin_orders")

    rows = fetch_all("""
        SELECT o.id, o.user_id, o.amount, o.status, o.created_at, p.title
        FROM orders o
        LEFT JOIN products p ON p.id = o.product_id
        ORDER BY o.id DESC
        LIMIT 15
    """)

    if not rows:
        await safe_edit_or_send(update, context, "لا يوجد طلبات حالياً.", keyboards.kb_back())
        return

    lines = ["🧾 آخر الطلبات:\n"]
    for r in rows:
        title = r["title"] or "طلب"
        lines.append(f"#{r['id']} | {title} | {money(r['amount'])} | {r['status']} | user:{r['user_id']}")

    lines.append("\n📌 لبحث الطلبات استخدم زر (🔎 بحث بالطلبات) من لوحة الأدمن.")
    await safe_edit_or_send(update, context, "\n".join(lines), keyboards.kb_back())


# ======================
# Mark Order Done / Cancel
# ======================

async def admin_order_done(update: Update, context: ContextTypes.DEFAULT_TYPE, order_id: int):
    if not is_admin(update.effective_user.id):
        return

    execute("UPDATE orders SET status=%s WHERE id=%s", ("delivered", order_id))
    await safe_edit_or_send(update, context, f"✅ تم تعليم الطلب #{order_id} كمُسلّم.", keyboards.kb_back())


async def admin_order_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE, order_id: int):
    if not is_admin(update.effective_user.id):
        return

    execute("UPDATE orders SET status=%s WHERE id=%s", ("canceled", order_id))
    await safe_edit_or_send(update, context, f"❌ تم إلغاء الطلب #{order_id}.", keyboards.kb_back())


# ======================
# Search Orders
# ======================

async def admin_search_orders(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return

    nav_push(context, "admin_search_orders")
    context.user_data["awaiting_order_search"] = True

    await safe_edit_or_send(
        update,
        context,
        "🔎 أرسل رقم الطلب (مثال: 120) أو user_id للبحث:",
        keyboards.kb_back()
    )


async def admin_search_execute(update: Update, context: ContextTypes.DEFAULT_TYPE, query: str):
    q = query.strip().replace("#", "")

    # إذا رقم
    try:
        num = int(q)
    except Exception:
        await update.message.reply_text("أرسل رقم صحيح.")
        return

    # حاول البحث كـ order_id أولاً
    order = fetch_one("""
        SELECT o.id, o.user_id, o.amount, o.status, o.created_at, o.proof, o.admin_note, p.title
        FROM orders o
        LEFT JOIN products p ON p.id=o.product_id
        WHERE o.id=%s
    """, (num,))

    if order:
        title = order["title"] or "طلب"
        text = (
            f"🧾 نتيجة البحث (طلب #{order['id']})\n\n"
            f"• المستخدم: {order['user_id']}\n"
            f"• المنتج: {title}\n"
            f"• المبلغ: {money(order['amount'])}\n"
            f"• الحالة: {order['status']}\n"
            f"• إثبات: {order['proof'] or '—'}\n"
            f"• ملاحظة: {order['admin_note'] or '—'}\n"
        )
        await update.message.reply_text(text)
        return

    # إذا لم يوجد كطلب، اعتبره user_id وابحث طلباته
    rows = fetch_all("""
        SELECT o.id, o.amount, o.status, o.created_at, p.title
        FROM orders o
        LEFT JOIN products p ON p.id=o.product_id
        WHERE o.user_id=%s
        ORDER BY o.id DESC
        LIMIT 15
    """, (num,))

    if not rows:
        await update.message.reply_text("لا توجد نتائج.")
        return

    lines = [f"📦 طلبات المستخدم {num}:\n"]
    for r in rows:
        title = r["title"] or "طلب"
        lines.append(f"#{r['id']} | {title} | {money(r['amount'])} | {r['status']}")
    await update.message.reply_text("\n".join(lines))


# ======================
# Broadcast
# ======================

async def admin_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return

    nav_push(context, "admin_broadcast")
    context.user_data["awaiting_broadcast"] = True

    await safe_edit_or_send(
        update,
        context,
        "📢 أرسل الآن رسالة الإذاعة (نص فقط):",
        keyboards.kb_back()
    )


async def admin_broadcast_execute(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str):
    users = fetch_all("SELECT user_id FROM users")

    ok = 0
    fail = 0

    for u in users:
        try:
            await context.bot.send_message(chat_id=int(u["user_id"]), text=text)
            ok += 1
        except Exception:
            fail += 1

    await update.message.reply_text(f"✅ تم الإرسال.\nنجح: {ok}\nفشل: {fail}")


# ======================
# Stats
# ======================

async def admin_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return

    nav_push(context, "admin_stats")

    users_count = fetch_one("SELECT COUNT(*) AS c FROM users")["c"]
    orders_count = fetch_one("SELECT COUNT(*) AS c FROM orders")["c"]
    pending_count = fetch_one("SELECT COUNT(*) AS c FROM orders WHERE status='pending'")["c"]
    delivered_count = fetch_one("SELECT COUNT(*) AS c FROM orders WHERE status='delivered'")["c"]

    text = (
        "📊 إحصائيات البوت\n\n"
        f"👤 المستخدمين: {users_count}\n"
        f"🧾 الطلبات: {orders_count}\n"
        f"⏳ قيد التنفيذ: {pending_count}\n"
        f"✅ تم التسليم: {delivered_count}\n"
    )

    await safe_edit_or_send(update, context, text, keyboards.kb_back())


# ======================
# Back (Admin side optional)
# ======================

async def admin_back(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # حالياً الرجوع العام سيتم التعامل معه في user_flow.go_back
    state = nav_pop(context)
    await safe_edit_or_send(update, context, "🔙 رجوع", keyboards.kb_back())
