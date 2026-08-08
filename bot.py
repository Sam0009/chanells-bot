 import os
import logging
from datetime import datetime, timezone, timedelta

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo, MessageEntity
from telegram.ext import Application, CommandHandler, ContextTypes

from supabase import create_client, Client

logging.basicConfig(level=logging.INFO)

# ضع التوكن هنا مباشرة أو عبر متغير بيئة BOT_TOKEN
BOT_TOKEN = os.environ.get("BOT_TOKEN", "ضع_التوكن_هنا")

# آيدي حسابك بتيليجرام (رقم) — بس هالحساب يقدر يستخدم أمر /stats
ADMIN_ID = int(os.environ.get("ADMIN_ID", "6094432183"))

# بيانات الاتصال بـ Supabase (تلاقيهم بمشروعك على supabase.com -> Settings -> API)
SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# رابط صفحة القنوات (GitHub Pages)
MINI_APP_URL = "https://sam0009.github.io/chanells/"

# كل عنصر: (الإيموجي الاحتياطي من الحزمة, custom_emoji_id, اسم القناة, الرابط)
CHANNELS = [
    ("🇪🇸", "6026062385867922158", "برشا برشا بالعربية", "https://t.me/+FovoXWz0fLRhOTBk"),
    ("❤️", "6026094632482381134", "برشا برشا بالعربية (البديلة)", "https://t.me/+kSDCZZdUq8JmYmE0"),
    ("⚽️", "6025894456941615230", "الأسطورة ميسي", "https://t.me/+i-dR3foyYqY5ZWEx"),
    ("⚽️", "6026340351856352617", "نادي برشلونة", "https://t.me/+cH6eGL-Y4_9mMzlh"),
    ("🏆", "6028463233931680730", "برشا ساخر", "https://t.me/+QINP4DoQabQ4MTM0"),
    ("🦁", "5976366487517011752", "خلفيات | Wallpapers", "https://t.me/+dL4CJEcE1gNmYjRi"),
    ("📸", "5916039535791185245", "البريميرليغ بالعربي", "https://t.me/+CfUPe5f9qpVhYTFk"),
    ("👑", "6023649241312795644", "أهداف المباريات", "https://t.me/+jrOHJcpB2WExY2Vk"),
]

HEADER_LINES = [
    "😀 أهلاً فيك في شبكة قنواتنا الرسمية!",
    "",
    "يسرّنا انضمامك لأفضل محتوى رياضي 🔥",
    "",
]


def utf16_len(text: str) -> int:
    # تيليجرام يحسب المواقع بوحدات UTF-16، مو بعدد الأحرف العادي
    return len(text.encode("utf-16-le")) // 2


def log_user(user) -> None:
    """يسجل المستخدم بقاعدة البيانات إذا كانت هاي أول مرة يدخل فيها، وإلا يحدث آخر ظهور له."""
    try:
        existing = supabase.table("users").select("user_id").eq("user_id", user.id).execute()
        now = datetime.now(timezone.utc).isoformat()

        if existing.data:
            supabase.table("users").update({"last_seen": now}).eq("user_id", user.id).execute()
        else:
            supabase.table("users").insert({
                "user_id": user.id,
                "username": user.username or "",
                "first_name": user.first_name or "",
                "first_seen": now,
                "last_seen": now,
            }).execute()
    except Exception as e:
        logging.error(f"Supabase log_user error: {e}")


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    log_user(update.effective_user)

    header = "\n".join(HEADER_LINES) + "\n"
    body = ""
    entities = []
    offset = utf16_len(header)

    for fallback, custom_id, name, _ in CHANNELS:
        line = f"{fallback} {name}"
        entities.append(
            MessageEntity(
                type=MessageEntity.CUSTOM_EMOJI,
                offset=offset,
                length=utf16_len(fallback),
                custom_emoji_id=custom_id,
            )
        )
        body += line + "\n"
        offset += utf16_len(line) + 1

    full_text = header + body

    buttons = [
        [InlineKeyboardButton("📺 تصفح جميع القنوات", web_app=WebAppInfo(url=MINI_APP_URL))]
    ]
    for _, _, name, link in CHANNELS:
        buttons.append([InlineKeyboardButton(name, url=link)])

    await update.message.reply_text(
        full_text,
        entities=entities,
        reply_markup=InlineKeyboardMarkup(buttons),
    )


async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_user.id != ADMIN_ID:
        return

    try:
        total = supabase.table("users").select("user_id", count="exact").execute()
        total_count = total.count or 0
 now = datetime.now(timezone.utc)
        since_today = now.replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
        since_week = (now - timedelta(days=7)).isoformat()

        today = supabase.table("users").select("user_id", count="exact") \
            .gte("first_seen", since_today).execute()
        week = supabase.table("users").select("user_id", count="exact") \
            .gte("first_seen", since_week).execute()

        active_today = supabase.table("users").select("user_id", count="exact") \
            .gte("last_seen", since_today).execute()

        text = (
            "📊 إحصائيات البوت\n\n"
            f"👥 إجمالي المستخدمين: {total_count}\n"
            f"🆕 مستخدمين جدد اليوم: {today.count or 0}\n"
            f"🆕 مستخدمين جدد آخر 7 أيام: {week.count or 0}\n"
            f"🟢 نشطين اليوم (فتحوا /start): {active_today.count or 0}\n"
        )
        await update.message.reply_text(text)
    except Exception as e:
        logging.error(f"Supabase stats error: {e}")
        await update.message.reply_text("⚠️ صار خطأ بجلب الإحصائيات.")


def main() -> None:
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("stats", stats))
    app.run_polling()


if __name__ == "__main__":
    main()
