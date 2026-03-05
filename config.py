import os

# توكن البوت
BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()

# ايدي الأدمن الرئيسي
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))

# رابط قاعدة البيانات PostgreSQL
DATABASE_URL = os.getenv("DATABASE_URL", "").strip()

# اسم البوت
BOT_NAME = os.getenv("BOT_NAME", "StoreBot")

# يوزر الدعم
SUPPORT_USERNAME = os.getenv("SUPPORT_USERNAME", "support").replace("@", "")

# مكافأة الإحالة (بالسنت)
REFERRAL_REWARD = int(os.getenv("REFERRAL_REWARD", "100"))

# حماية تكرار الطلبات
MAX_ORDERS_PER_MINUTE = int(os.getenv("MAX_ORDERS_PER_MINUTE", "3"))

# وقت الحماية بالثواني
ORDER_COOLDOWN = int(os.getenv("ORDER_COOLDOWN", "60"))
