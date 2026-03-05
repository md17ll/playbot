from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from config import ADMIN_ID, SUPPORT_USERNAME


def is_admin(user_id: int) -> bool:
    return ADMIN_ID != 0 and user_id == ADMIN_ID


def kb_home(user_id: int) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton("🛍 المتجر", callback_data="home:shop")],
        [InlineKeyboardButton("💰 شحن الرصيد", callback_data="home:topup")],
        [InlineKeyboardButton("🎟 كود / كوبون", callback_data="home:coupon")],
        [InlineKeyboardButton("👥 الإحالة", callback_data="home:referral")],
        [InlineKeyboardButton("📦 طلباتي", callback_data="home:orders")],
        [InlineKeyboardButton("📞 الدعم", url=f"https://t.me/{SUPPORT_USERNAME}")],
    ]

    if is_admin(user_id):
        rows.append([InlineKeyboardButton("⚙ لوحة الأدمن", callback_data="admin:panel")])

    return InlineKeyboardMarkup(rows)


def kb_back() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔙 رجوع", callback_data="nav:back")]
    ])


def kb_shop() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🎬 اشتراكات", callback_data="shop:subscriptions")],
        [InlineKeyboardButton("🎮 شحن ألعاب", callback_data="shop:games")],
        [InlineKeyboardButton("🔙 رجوع", callback_data="nav:back")],
    ])


def kb_subscriptions() -> InlineKeyboardMarkup:
    # لاحقاً سيتم استبدالها بقائمة ديناميكية من قاعدة البيانات (Netflix / Shahid / ...)
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("Netflix", callback_data="subs:netflix")],
        [InlineKeyboardButton("Shahid", callback_data="subs:shahid")],
        [InlineKeyboardButton("🔙 رجوع", callback_data="nav:back")],
    ])


def kb_admin_panel() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📦 إدارة المنتجات", callback_data="admin:products")],
        [InlineKeyboardButton("🧾 إدارة الطلبات", callback_data="admin:orders")],
        [InlineKeyboardButton("🎟 إدارة الأكواد", callback_data="admin:coupons")],
        [InlineKeyboardButton("💰 إدارة الرصيد", callback_data="admin:balance")],
        [InlineKeyboardButton("📝 تعديل رسالة البدء", callback_data="admin:edit_start")],
        [InlineKeyboardButton("🔎 بحث بالطلبات", callback_data="admin:search_orders")],
        [InlineKeyboardButton("📢 إذاعة للكل", callback_data="admin:broadcast")],
        [InlineKeyboardButton("📊 إحصائيات", callback_data="admin:stats")],
        [InlineKeyboardButton("🔙 رجوع", callback_data="nav:back")],
    ])


def kb_admin_order_actions(order_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ تم التسليم", callback_data=f"order:done:{order_id}"),
            InlineKeyboardButton("❌ إلغاء", callback_data=f"order:cancel:{order_id}"),
        ],
        [InlineKeyboardButton("🔙 رجوع", callback_data="nav:back")],
    ])
