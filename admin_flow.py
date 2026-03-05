from telegram import Update
from telegram.ext import ContextTypes

import texts
import keyboards
from utils import safe_edit_or_send, is_admin, nav_push, nav_pop, money
from db import fetch_all, fetch_one, execute


# ===== Admin input states =====
AWAIT_START_EDIT = "awaiting_new_start_message"
AWAIT_ORDER_SEARCH = "awaiting_order_search"
AWAIT_BROADCAST = "awaiting_broadcast"

AWAIT_PRODUCTS_CMD = "awaiting_admin_products_cmd"
AWAIT_COUPONS_CMD = "awaiting_admin_coupons_cmd"
AWAIT_BALANCE_CMD = "awaiting_admin_balance_cmd"


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
    context.user_data[AWAIT_START_EDIT] = True

    await safe_edit_or_send(
        update,
        context,
        "📝 Send the new /start message (text only).",
        keyboards.kb_back()
    )


# ======================
# Admin: Products
# ======================
async def admin_products(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return

    nav_push(context, "admin_products")
    context.user_data[AWAIT_PRODUCTS_CMD] = True

    rows = fetch_all(
        "SELECT id, section, title, price, is_active FROM products ORDER BY id DESC LIMIT 30"
    )

    lines = ["📦 Products (latest 30):\n"]
    if not rows:
        lines.append("— No products yet.\n")
    else:
        for r in rows:
            st = "✅" if r["is_active"] else "⛔"
            lines.append(f"{st} #{r['id']} [{r['section']}] {r['title']} — {money(int(r['price']))}")

    lines.append(
        "\nCommands:\n"
        "ADD section | title | price_cents | description(optional)\n"
        "TOGGLE product_id\n"
        "DEL product_id\n\n"
        "Example:\n"
        "ADD subscriptions | Netflix 1 Month | 1000 | Standard plan\n"
    )

    await safe_edit_or_send(update, context, "\n".join(lines), keyboards.kb_back())


# ======================
# Admin: Coupons
# ======================
async def admin_coupons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return

    nav_push(context, "admin_coupons")
    context.user_data[AWAIT_COUPONS_CMD] = True

    rows = fetch_all("SELECT code, type, value, uses, max_uses, is_active FROM coupons ORDER BY code ASC")

    lines = ["🎟 Coupons:\n"]
    if not rows:
        lines.append("— No coupons yet.\n")
    else:
        for c in rows:
            st = "✅" if c["is_active"] else "⛔"
            lines.append(
                f"{st} {c['code']} [{c['type']}] value={c['value']} uses={c['uses']}/{c['max_uses']}"
            )

    lines.append(
        "\nCommands:\n"
        "NEW code | type(credit/discount) | value | max_uses\n"
        "TOGGLE code\n"
        "DEL code\n\n"
        "Examples:\n"
        "NEW RAMADAN10 | discount | 10 | 100\n"
        "NEW CREDIT5 | credit | 500 | 50\n"
    )

    await safe_edit_or_send(update, context, "\n".join(lines), keyboards.kb_back())


# ======================
# Admin: Balance
# ======================
async def admin_balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return

    nav_push(context, "admin_balance")
    context.user_data[AWAIT_BALANCE_CMD] = True

    msg = (
        "💰 Balance Manager\n\n"
        "Commands:\n"
        "SHOW user_id\n"
        "ADD user_id | cents\n"
        "SUB user_id | cents\n\n"
        "Example:\n"
        "ADD 123456789 | 500\n"
    )

    await safe_edit_or_send(update, context, msg, keyboards.kb_back())


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
        await safe_edit_or_send(update, context, "No orders yet.", keyboards.kb_back())
        return

    lines = ["🧾 Latest orders (15):\n"]
    for r in rows:
        title = r["title"] or "Order"
        lines.append(f"#{r['id']} | {title} | {money(int(r['amount']))} | {r['status']} | user:{r['user_id']}")

    await safe_edit_or_send(update, context, "\n".join(lines), keyboards.kb_back())


async def admin_order_done(update: Update, context: ContextTypes.DEFAULT_TYPE, order_id: int):
    if not is_admin(update.effective_user.id):
        return

    execute("UPDATE orders SET status=%s WHERE id=%s", ("delivered", order_id))
    await safe_edit_or_send(update, context, f"✅ Order #{order_id} marked as delivered.", keyboards.kb_back())


async def admin_order_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE, order_id: int):
    if not is_admin(update.effective_user.id):
        return

    execute("UPDATE orders SET status=%s WHERE id=%s", ("canceled", order_id))
    await safe_edit_or_send(update, context, f"❌ Order #{order_id} canceled.", keyboards.kb_back())


# ======================
# Search Orders
# ======================
async def admin_search_orders(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return

    nav_push(context, "admin_search_orders")
    context.user_data[AWAIT_ORDER_SEARCH] = True

    await safe_edit_or_send(
        update,
        context,
        "🔎 Send order_id (e.g. 120) OR user_id to search:",
        keyboards.kb_back()
    )


async def _admin_search_execute(update: Update, context: ContextTypes.DEFAULT_TYPE, query: str):
    q = query.strip().replace("#", "")
    try:
        num = int(q)
    except Exception:
        await update.message.reply_text("Send a valid number.")
        return

    # Try as order_id
    order = fetch_one("""
        SELECT o.id, o.user_id, o.amount, o.status, o.created_at, o.proof, o.admin_note, p.title
        FROM orders o
        LEFT JOIN products p ON p.id=o.product_id
        WHERE o.id=%s
    """, (num,))

    if order:
        title = order["title"] or "Order"
        text = (
            f"🧾 Result (Order #{order['id']})\n\n"
            f"User: {order['user_id']}\n"
            f"Product: {title}\n"
            f"Amount: {money(int(order['amount']))}\n"
            f"Status: {order['status']}\n"
            f"Proof: {order['proof'] or '—'}\n"
            f"Note: {order['admin_note'] or '—'}\n"
        )
        await update.message.reply_text(text)
        return

    # Else as user_id
    rows = fetch_all("""
        SELECT o.id, o.amount, o.status, o.created_at, p.title
        FROM orders o
        LEFT JOIN products p ON p.id=o.product_id
        WHERE o.user_id=%s
        ORDER BY o.id DESC
        LIMIT 15
    """, (num,))

    if not rows:
        await update.message.reply_text("No results.")
        return

    lines = [f"📦 Orders for user {num}:\n"]
    for r in rows:
        title = r["title"] or "Order"
        lines.append(f"#{r['id']} | {title} | {money(int(r['amount']))} | {r['status']}")
    await update.message.reply_text("\n".join(lines))


# ======================
# Broadcast
# ======================
async def admin_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return

    nav_push(context, "admin_broadcast")
    context.user_data[AWAIT_BROADCAST] = True

    await safe_edit_or_send(
        update,
        context,
        "📢 Send broadcast message (text only):",
        keyboards.kb_back()
    )


async def _admin_broadcast_execute(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str):
    users = fetch_all("SELECT user_id FROM users")

    ok = 0
    fail = 0
    for u in users:
        try:
            await context.bot.send_message(chat_id=int(u["user_id"]), text=text)
            ok += 1
        except Exception:
            fail += 1

    await update.message.reply_text(f"✅ Broadcast sent.\nOK: {ok}\nFail: {fail}")


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
        "📊 Stats\n\n"
        f"Users: {users_count}\n"
        f"Orders: {orders_count}\n"
        f"Pending: {pending_count}\n"
        f"Delivered: {delivered_count}\n"
    )

    await safe_edit_or_send(update, context, text, keyboards.kb_back())


# ======================
# Admin text handler
# ======================
async def handle_admin_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handles admin-only text when admin is in a waiting state.
    """
    if not is_admin(update.effective_user.id):
        return

    if not update.message or not update.message.text:
        return

    text = (update.message.text or "").strip()

    # 1) Edit start text
    if context.user_data.get(AWAIT_START_EDIT):
        context.user_data[AWAIT_START_EDIT] = False
        texts.START_MESSAGE = text
        await update.message.reply_text("✅ Start message updated. Try /start.")
        return

    # 2) Order search
    if context.user_data.get(AWAIT_ORDER_SEARCH):
        context.user_data[AWAIT_ORDER_SEARCH] = False
        await _admin_search_execute(update, context, text)
        return

    # 3) Broadcast
    if context.user_data.get(AWAIT_BROADCAST):
        context.user_data[AWAIT_BROADCAST] = False
        await _admin_broadcast_execute(update, context, text)
        return

    # 4) Products commands
    if context.user_data.get(AWAIT_PRODUCTS_CMD):
        up = text.upper()

        if up.startswith("ADD "):
            # ADD section | title | price_cents | description(optional)
            try:
                payload = text[4:]
                parts = [p.strip() for p in payload.split("|")]
                section = parts[0]
                title = parts[1]
                price_cents = int(parts[2])
                desc = parts[3] if len(parts) > 3 else ""
                execute(
                    "INSERT INTO products(section, title, description, price, is_active) VALUES(%s,%s,%s,%s,TRUE)",
                    (section, title, desc, price_cents),
                )
                await update.message.reply_text("✅ Product added.")
            except Exception:
                await update.message.reply_text("❌ Invalid format. Example:\nADD subscriptions | Netflix 1 Month | 1000 | Standard")
            return

        if up.startswith("TOGGLE "):
            try:
                pid = int(text.split()[1])
                execute("UPDATE products SET is_active = NOT is_active WHERE id=%s", (pid,))
                await update.message.reply_text("✅ Product toggled.")
            except Exception:
                await update.message.reply_text("❌ Use: TOGGLE product_id")
            return

        if up.startswith("DEL "):
            try:
                pid = int(text.split()[1])
                execute("DELETE FROM products WHERE id=%s", (pid,))
                await update.message.reply_text("🗑 Product deleted.")
            except Exception:
                await update.message.reply_text("❌ Use: DEL product_id")
            return

        await update.message.reply_text("Unknown products command.")
        return

    # 5) Coupons commands
    if context.user_data.get(AWAIT_COUPONS_CMD):
        up = text.upper()

        if up.startswith("NEW "):
            # NEW code | type | value | max_uses
            try:
                payload = text[4:]
                code, ctype, val, max_uses = [p.strip() for p in payload.split("|")]
                execute(
                    """
                    INSERT INTO coupons(code, type, value, uses, max_uses, is_active)
                    VALUES(%s,%s,%s,0,%s,TRUE)
                    ON CONFLICT (code) DO UPDATE SET type=EXCLUDED.type, value=EXCLUDED.value, max_uses=EXCLUDED.max_uses, is_active=TRUE
                    """,
                    (code.upper(), ctype.lower(), int(val), int(max_uses)),
                )
                await update.message.reply_text("✅ Coupon created/updated.")
            except Exception:
                await update.message.reply_text("❌ Invalid format. Example:\nNEW RAMADAN10 | discount | 10 | 100")
            return

        if up.startswith("TOGGLE "):
            try:
                code = text.split()[1].upper()
                execute("UPDATE coupons SET is_active = NOT is_active WHERE code=%s", (code,))
                await update.message.reply_text("✅ Coupon toggled.")
            except Exception:
                await update.message.reply_text("❌ Use: TOGGLE CODE")
            return

        if up.startswith("DEL "):
            try:
                code = text.split()[1].upper()
                execute("DELETE FROM coupons WHERE code=%s", (code,))
                await update.message.reply_text("🗑 Coupon deleted.")
            except Exception:
                await update.message.reply_text("❌ Use: DEL CODE")
            return

        await update.message.reply_text("Unknown coupons command.")
        return

    # 6) Balance commands
    if context.user_data.get(AWAIT_BALANCE_CMD):
        up = text.upper()

        if up.startswith("SHOW "):
            try:
                uid = int(text.split()[1])
                row = fetch_one("SELECT balance FROM balances WHERE user_id=%s", (uid,))
                bal = int(row["balance"]) if row else 0
                await update.message.reply_text(f"User {uid} balance: {bal} cents.")
            except Exception:
                await update.message.reply_text("❌ Use: SHOW user_id")
            return

        if up.startswith("ADD ") or up.startswith("SUB "):
            try:
                cmd = text.split()[0].upper()
                payload = text[len(cmd):].strip()
                uid_s, cents_s = [p.strip() for p in payload.split("|")]
                uid = int(uid_s)
                cents = int(cents_s)

                row = fetch_one("SELECT balance FROM balances WHERE user_id=%s", (uid,))
                bal = int(row["balance"]) if row else 0

                if cmd == "ADD":
                    bal += cents
                else:
                    bal -= cents

                execute(
                    """
                    INSERT INTO balances(user_id, balance)
                    VALUES(%s,%s)
                    ON CONFLICT (user_id) DO UPDATE SET balance=EXCLUDED.balance
                    """,
                    (uid, bal),
                )
                await update.message.reply_text("✅ Balance updated.")
            except Exception:
                await update.message.reply_text("❌ Example:\nADD 123456 | 500\nSUB 123456 | 200")
            return

        await update.message.reply_text("Unknown balance command.")
        return
