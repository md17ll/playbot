import time
from typing import Optional

from telegram import Update
from telegram.ext import ContextTypes

from config import MAX_ORDERS_PER_MINUTE, ORDER_COOLDOWN, ADMIN_ID


# مفاتيح التخزين داخل user_data
NAV_STACK_KEY = "nav_stack"
LAST_MSG_ID_KEY = "last_message_id"
RATE_LIMIT_KEY = "rate_limit"  # dict: {key: [timestamps]}


def is_admin(user_id: int) -> bool:
    return ADMIN_ID != 0 and user_id == ADMIN_ID


# -----------------------------
# Navigation Stack (Back)
# -----------------------------
def nav_push(context: ContextTypes.DEFAULT_TYPE, state: str) -> None:
    stack = context.user_data.get(NAV_STACK_KEY)
    if not isinstance(stack, list):
        stack = []
    stack.append(state)
    context.user_data[NAV_STACK_KEY] = stack


def nav_current(context: ContextTypes.DEFAULT_TYPE) -> str:
    stack = context.user_data.get(NAV_STACK_KEY)
    if isinstance(stack, list) and stack:
        return stack[-1]
    return "home"


def nav_pop(context: ContextTypes.DEFAULT_TYPE) -> str:
    """
    يرجع للشاشة السابقة فعلاً.
    إذا ما في صفحات يرجع home.
    """
    stack = context.user_data.get(NAV_STACK_KEY)
    if not isinstance(stack, list) or len(stack) <= 1:
        context.user_data[NAV_STACK_KEY] = ["home"]
        return "home"
    stack.pop()
    context.user_data[NAV_STACK_KEY] = stack
    return stack[-1]


def nav_reset(context: ContextTypes.DEFAULT_TYPE) -> None:
    context.user_data[NAV_STACK_KEY] = ["home"]


# -----------------------------
# Safe Edit (edit same message)
# -----------------------------
async def safe_edit_or_send(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    text: str,
    reply_markup=None,
) -> None:
    """
    يحاول يعدّل نفس الرسالة دائماً.
    - إذا كان CallbackQuery: يعدّل رسالة الزر نفسها.
    - إذا كان Message (مثل /start): يحاول تعديل آخر رسالة محفوظة
      وإلا يرسل رسالة جديدة مرة واحدة ويحفظ message_id.
    """
    chat_id = update.effective_chat.id

    # 1) لو في callback query نعدل نفس الرسالة مباشرة
    if update.callback_query:
        q = update.callback_query
        try:
            await q.edit_message_text(text=text, reply_markup=reply_markup)
            context.user_data[LAST_MSG_ID_KEY] = q.message.message_id
            return
        except Exception:
            # إذا فشل لأي سبب (رسالة قديمة/تعديل غير مسموح) نكمل fallback
            pass

    # 2) لو عندنا آخر message_id محفوظ نحاول نعدله
    last_id = context.user_data.get(LAST_MSG_ID_KEY)
    if isinstance(last_id, int):
        try:
            await context.bot.edit_message_text(
                chat_id=chat_id,
                message_id=last_id,
                text=text,
                reply_markup=reply_markup,
            )
            return
        except Exception:
            pass

    # 3) fallback: إرسال رسالة جديدة (مرة واحدة عند الضرورة) ثم حفظ id
    msg = await update.effective_message.reply_text(text, reply_markup=reply_markup)
    context.user_data[LAST_MSG_ID_KEY] = msg.message_id


# -----------------------------
# Rate Limit / Anti-Spam
# -----------------------------
def _rl_get_bucket(context: ContextTypes.DEFAULT_TYPE) -> dict:
    bucket = context.user_data.get(RATE_LIMIT_KEY)
    if not isinstance(bucket, dict):
        bucket = {}
        context.user_data[RATE_LIMIT_KEY] = bucket
    return bucket


def rate_limit_allow(
    context: ContextTypes.DEFAULT_TYPE,
    key: str,
    max_calls: int,
    per_seconds: int,
) -> bool:
    """
    Rate-limit عام.
    key مثل: "order_create" أو "proof_send"
    """
    now = int(time.time())
    bucket = _rl_get_bucket(context)
    timestamps = bucket.get(key)

    if not isinstance(timestamps, list):
        timestamps = []
        bucket[key] = timestamps

    # حذف القديم خارج النافذة
    cutoff = now - per_seconds
    timestamps[:] = [t for t in timestamps if t > cutoff]

    if len(timestamps) >= max_calls:
        return False

    timestamps.append(now)
    return True


def can_create_order(context: ContextTypes.DEFAULT_TYPE) -> bool:
    """
    حماية إنشاء الطلبات:
    - حد أقصى MAX_ORDERS_PER_MINUTE خلال 60 ثانية
    - كول داون ORDER_COOLDOWN ثانية بين كل طلب
    """
    # 1) حد أقصى خلال دقيقة
    if not rate_limit_allow(context, "order_create_minute", MAX_ORDERS_PER_MINUTE, 60):
        return False

    # 2) كول داون
    now = int(time.time())
    last = context.user_data.get("last_order_time")
    if isinstance(last, int) and (now - last) < ORDER_COOLDOWN:
        return False

    context.user_data["last_order_time"] = now
    return True


def format_cooldown_hint(context: ContextTypes.DEFAULT_TYPE) -> str:
    """
    رسالة مساعدة للمستخدم عند منع الطلب بسبب الكولداون.
    """
    now = int(time.time())
    last = context.user_data.get("last_order_time")
    if not isinstance(last, int):
        return "⏳ حاول بعد قليل."
    remaining = ORDER_COOLDOWN - (now - last)
    if remaining < 1:
        remaining = 1
    return f"⏳ رجاءً انتظر {remaining} ثانية ثم حاول مرة أخرى."


# -----------------------------
# Helpers
# -----------------------------
def money(cents: int) -> str:
    # نخزن كـ سنت لتجنب مشاكل float
    return f"${cents / 100:.2f}"


def to_int_safe(s: str) -> Optional[int]:
    try:
        return int(str(s).strip())
    except Exception:
        return None
