from telegram import Update
from telegram.ext import ContextTypes

import texts
import keyboards
from utils import (
    safe_edit_or_send,
    nav_push,
    nav_pop,
    nav_reset,
)

from db import fetch_one, execute


# ====== User input states ======
AWAITING_COUPON_KEY = "awaiting_coupon_code"


# ======================
# HOME
# ======================

async def show_home(update: Update, context: ContextTypes.DEFAULT_TYPE):
    nav_reset(context)

    await safe_edit_or_send(
        update,
        context,
        texts.START_MESSAGE,
        keyboards.kb_home(update.effective_user.id)
    )


# ======================
# SHOP
# ======================

async def show_shop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    nav_push(context, "shop")

    await safe_edit_or_send(
        update,
        context,
        texts.SHOP_MESSAGE,
        keyboards.kb_shop()
    )


# ======================
# SUBSCRIPTIONS
# ======================

async def show_subscriptions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    nav_push(context, "subscriptions")

    await safe_edit_or_send(
        update,
        context,
        texts.SUBSCRIPTIONS_MESSAGE,
        keyboards.kb_subscriptions()
    )


# ======================
# GAMES
# ======================

async def show_games(update: Update, context: ContextTypes.DEFAULT_TYPE):
    nav_push(context, "games")

    await safe_edit_or_send(
        update,
        context,
        texts.GAMES_MESSAGE,
        keyboards.kb_back()
    )


# ======================
# BALANCE
# ======================

async def show_balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    nav_push(context, "balance")

    await safe_edit_or_send(
        update,
        context,
        texts.BALANCE_MESSAGE,
        keyboards.kb_back()
    )


# ======================
# COUPON
# ======================

async def show_coupon(update: Update, context: ContextTypes.DEFAULT_TYPE):
    nav_push(context, "coupon")

    # ✅ FIX: set state so next user text is treated as coupon code
    context.user_data[AWAITING_COUPON_KEY] = True

    await safe_edit_or_send(
        update,
        context,
        texts.COUPON_MESSAGE,
        keyboards.kb_back()
    )


# ======================
# REFERRAL
# ======================

async def show_referral(update: Update, context: ContextTypes.DEFAULT_TYPE):
    nav_push(context, "referral")

    await safe_edit_or_send(
        update,
        context,
        texts.REFERRAL_MESSAGE,
        keyboards.kb_back()
    )


# ======================
# ORDERS
# ======================

async def show_orders(update: Update, context: ContextTypes.DEFAULT_TYPE):
    nav_push(context, "orders")

    await safe_edit_or_send(
        update,
        context,
        texts.ORDERS_MESSAGE,
        keyboards.kb_back()
    )


# ======================
# BACK
# ======================

async def go_back(update: Update, context: ContextTypes.DEFAULT_TYPE):
    state = nav_pop(context)

    # إذا رجعنا نلغي وضع إدخال الكوبون
    context.user_data.pop(AWAITING_COUPON_KEY, None)

    if state == "home":
        await safe_edit_or_send(
            update,
            context,
            texts.START_MESSAGE,
            keyboards.kb_home(update.effective_user.id)
        )

    elif state == "shop":
        await safe_edit_or_send(
            update,
            context,
            texts.SHOP_MESSAGE,
            keyboards.kb_shop()
        )

    elif state == "subscriptions":
        await safe_edit_or_send(
            update,
            context,
            texts.SUBSCRIPTIONS_MESSAGE,
            keyboards.kb_subscriptions()
        )

    elif state == "games":
        await safe_edit_or_send(
            update,
            context,
            texts.GAMES_MESSAGE,
            keyboards.kb_back()
        )

    elif state == "balance":
        await safe_edit_or_send(
            update,
            context,
            texts.BALANCE_MESSAGE,
            keyboards.kb_back()
        )

    elif state == "coupon":
        # رجوع إلى شاشة الكوبون يعيد تفعيل وضع الإدخال
        context.user_data[AWAITING_COUPON_KEY] = True
        await safe_edit_or_send(
            update,
            context,
            texts.COUPON_MESSAGE,
            keyboards.kb_back()
        )

    elif state == "referral":
        await safe_edit_or_send(
            update,
            context,
            texts.REFERRAL_MESSAGE,
            keyboards.kb_back()
        )

    elif state == "orders":
        await safe_edit_or_send(
            update,
            context,
            texts.ORDERS_MESSAGE,
            keyboards.kb_back()
        )

    else:
        await safe_edit_or_send(
            update,
            context,
            texts.START_MESSAGE,
            keyboards.kb_home(update.effective_user.id)
        )


# ======================
# Coupon processing (DB)
# ======================

def _get_balance_cents(user_id: int) -> int:
    row = fetch_one("SELECT balance FROM balances WHERE user_id=%s", (user_id,))
    return int(row["balance"]) if row else 0


def _add_balance_cents(user_id: int, delta: int) -> None:
    current = _get_balance_cents(user_id)
    execute("UPDATE balances SET balance=%s WHERE user_id=%s", (current + int(delta), user_id))


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """
    ✅ مهم: يرجع True إذا تعاملنا مع الرسالة
    حتى main.py ما يرسل الرد العام.
    """
    if not update.message or not update.message.text:
        return False

    text = (update.message.text or "").strip()
    user_id = update.effective_user.id

    # ✅ FIX: if awaiting coupon code, process it
    if context.user_data.get(AWAITING_COUPON_KEY):
        context.user_data[AWAITING_COUPON_KEY] = False

        code = text.upper().strip()
        c = fetch_one("SELECT * FROM coupons WHERE code=%s", (code,))
        if not c:
            await update.message.reply_text("❌ Invalid code.")
            return True

        if not c.get("is_active", True):
            await update.message.reply_text("❌ Code is disabled.")
            return True

        max_uses = c.get("max_uses")
        uses = int(c.get("uses") or 0)
        if max_uses is not None and uses >= int(max_uses):
            await update.message.reply_text("❌ Code limit reached.")
            return True

        # increment uses
        execute("UPDATE coupons SET uses = uses + 1 WHERE code=%s", (code,))

        ctype = (c.get("type") or "").lower()
        val = int(c.get("value") or 0)

        if ctype == "credit":
            _add_balance_cents(user_id, val)
            await update.message.reply_text(f"✅ Credit added: {val} cents.")
            return True

        if ctype == "discount":
            # نخزنه للطلب القادم (جلسة فقط) — بدون تغيير أي نظام آخر
            context.user_data["next_discount_percent"] = val
            await update.message.reply_text(f"✅ Discount activated: {val}% (next order).")
            return True

        await update.message.reply_text("❌ Invalid coupon type.")
        return True

    return False


async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    # حالياً ما عندنا خطوة صور للمستخدم ضمن هذا الإصلاح
    return False
