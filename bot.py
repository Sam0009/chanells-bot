import os
import time
import asyncio
import logging
from collections import defaultdict
from datetime import datetime, timezone, timedelta

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo, MessageEntity
from telegram.error import Forbidden, BadRequest
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

from supabase import create_client, Client

logging.basicConfig(level=logging.INFO)

# ضع التوكن هنا مباشرة أو عبر متغير بيئة BOT_TOKEN
BOT_TOKEN = os.environ.get("BOT_TOKEN", "ضع_التوكن_هنا")

# آيدي حسابك بتيليجرام (رقم) — بس هالحساب يقدر يستخدم أمر /stats
# للحصول عليه: كلم بوت @userinfobot وبيرجعلك رقمك
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

# --- إعدادات الحماية من السبام (Flood Protection) ---
FLOOD_LIMIT = 5          # أقصى عدد رسائل/أوامر مسموحة
FLOOD_WINDOW = 10        # خلال كم ثانية
FLOOD_MUTE_SECONDS = 30  # مدة التجاهل المؤقت بعد تجاوز الحد

# سجل بالذاكرة: user_id -> [أوقات آخر الرسائل]
_user_activity = defaultdict(list)
# سجل بالذاكرة: user_id -> وقت انتهاء الحظر المؤقت
_muted_until = {}


def utf16_len(text: str) -> int:
    # تيليجرام يحسب المواقع بوحدات UTF-16، مو بعدد الأحرف العادي
    return len(text.encode("utf-16-le")) // 2


def log_user(user) -> None:
    """يسجل المستخدم بقاعدة البيانات إذا كانت هاي أول مرة يدخل فيها، وإلا يحدث آخر ظهور له."""
    try:
        existing = supabase.table("users").select("user_id").eq("user_id", user.id).execute()
        now = datetime.now(timezone.utc).isoformat()

        if existing.data:
            # مستخدم موجود من قبل -> حدث آخر ظهور بس
            supabase.table("users").update({"last_seen": now}).eq("user_id", user.id).execute()
        else:
            # مستخدم جديد -> أضفه
            supabase.table("users").insert({
                "user_id": user.id,
                "username": user.username or "",
                "first_name": user.first_name or "",
                "first_seen": now,
                "last_seen": now,
            }).execute()
    except Exception as e:
        logging.error(f"Supabase log_user error: {e}")


def is_banned(user_id: int) -> bool:
    try:
        res = supabase.table("users").select("banned").eq("user_id", user_id).execute()
        if res.data:
            return bool(res.data[0].get("banned"))
        return False
    except Exception as e:
        logging.error(f"Supabase is_banned error: {e}")
        return False


def is_flooding(user_id: int) -> bool:
    """يرجع True إذا المستخدم تجاوز حد الرسائل المسموح، ويحطه بحظر مؤقت."""
    now = time.time()

    # إذا محظور مؤقتاً وما زالت المدة سارية
    if user_id in _muted_until:
        if now < _muted_until[user_id]:
            return True
        else:
            del _muted_until[user_id]

    # سجل الوقت الحالي واحذف الأوقات الأقدم من النافذة الزمنية
    activity = _user_activity[user_id]
    activity.append(now)
    _user_activity[user_id] = [t for t in activity if now - t <= FLOOD_WINDOW]

    if len(_user_activity[user_id]) > FLOOD_LIMIT:
        _muted_until[user_id] = now + FLOOD_MUTE_SECONDS
        _user_activity[user_id] = []
        return True

    return False


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user

    if is_flooding(user.id):
        return  # يتجاهل الرسائل بصمت خلال فترة الحظر المؤقت

    if is_banned(user.id):
        await update.message.reply_text("🚫 تم حظرك من استخدام هذا البوت.")
        return

    log_user(user)

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
        offset += utf16_len(line) + 1  # +1 لسطر جديد

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
        return  # يتجاهل أي حدا مش الأدمن بصمت

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


async def ban(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_user.id != ADMIN_ID:
        return

    if not context.args:
        await update.message.reply_text("الاستخدام: /ban <user_id>")
        return

    try:
        target_id = int(context.args[0])
        supabase.table("users").update({"banned": True}).eq("user_id", target_id).execute()
        await update.message.reply_text(f"✅ تم حظر المستخدم {target_id}")
    except Exception as e:
        logging.error(f"ban error: {e}")
        await update.message.reply_text("⚠️ صار خطأ، تأكد إنك كاتب رقم آيدي صحيح.")


async def unban(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_user.id != ADMIN_ID:
        return

    if not context.args:
        await update.message.reply_text("الاستخدام: /unban <user_id>")
        return

    try:
        target_id = int(context.args[0])
        supabase.table("users").update({"banned": False}).eq("user_id", target_id).execute()
        await update.message.reply_text(f"✅ تم رفع الحظر عن المستخدم {target_id}")
    except Exception as e:
        logging.error(f"unban error: {e}")
        await update.message.reply_text("⚠️ صار خطأ، تأكد إنك كاتب رقم آيدي صحيح.")


def get_stats_text() -> str:
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
    banned = supabase.table("users").select("user_id", count="exact") \
        .eq("banned", True).execute()

    return (
        "📊 إحصائيات البوت\n\n"
        f"👥 إجمالي المستخدمين: {total_count}\n"
        f"🆕 مستخدمين جدد اليوم: {today.count or 0}\n"
        f"🆕 مستخدمين جدد آخر 7 أيام: {week.count or 0}\n"
        f"🟢 نشطين اليوم: {active_today.count or 0}\n"
        f"🚫 محظورين: {banned.count or 0}\n"
    )


def admin_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("👥 المستخدمين", callback_data="admin_users"),
         InlineKeyboardButton("📊 الإحصائيات", callback_data="admin_stats")],
        [InlineKeyboardButton("🚫 إدارة الحظر", callback_data="admin_ban")],
        [InlineKeyboardButton("📢 الإذاعة", callback_data="admin_broadcast")],
    ])


async def admin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_user.id != ADMIN_ID:
        return

    await update.message.reply_text(
        "🛠 لوحة تحكم البوت\n\nاختر من القائمة تحت:",
        reply_markup=admin_menu_keyboard(),
    )


async def admin_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query

    if query.from_user.id != ADMIN_ID:
        await query.answer("🚫 هذا القسم للأدمن فقط.", show_alert=True)
        return

    await query.answer()
    action = query.data

    try:
        if action == "admin_stats":
            text = get_stats_text()

        elif action == "admin_users":
            res = supabase.table("users").select("user_id, username, first_name, first_seen") \
                .order("first_seen", desc=True).limit(10).execute()
            lines = ["👥 آخر 10 مستخدمين:\n"]
            for u in res.data:
                uname = f"@{u['username']}" if u.get("username") else (u.get("first_name") or "بدون اسم")
                lines.append(f"• {uname} — ID: {u['user_id']}")
            text = "\n".join(lines) if res.data else "لا يوجد مستخدمين مسجلين بعد."

        elif action == "admin_ban":
            res = supabase.table("users").select("user_id, username, first_name") \
                .eq("banned", True).limit(20).execute()
            lines = ["🚫 المحظورين حالياً:\n"]
            for u in res.data:
                uname = f"@{u['username']}" if u.get("username") else (u.get("first_name") or "بدون اسم")
                lines.append(f"• {uname} — ID: {u['user_id']}")
            if not res.data:
                lines.append("لا يوجد أحد محظور حالياً.")
            lines.append("\nللحظر: /ban <user_id>\nلفك الحظر: /unban <user_id>")
            text = "\n".join(lines)

        elif action == "admin_broadcast":
            text = (
                "📢 لإرسال رسالة لجميع المستخدمين، استخدم:\n\n"
                "/broadcast نص الرسالة هنا\n\n"
                "بترسل لكل المستخدمين المسجلين بقاعدة البيانات."
            )

        else:
            text = "أمر غير معروف."

        await query.edit_message_text(text, reply_markup=admin_menu_keyboard())

    except Exception as e:
        logging.error(f"admin_callback error: {e}")
        await query.edit_message_text("⚠️ صار خطأ، حاول مرة ثانية.", reply_markup=admin_menu_keyboard())


async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_user.id != ADMIN_ID:
        return

    if not context.args:
        await update.message.reply_text("الاستخدام: /broadcast نص الرسالة")
        return

    message_text = update.message.text.split(None, 1)[1]

    try:
        res = supabase.table("users").select("user_id").eq("banned", False).execute()
        user_ids = [row["user_id"] for row in res.data]
    except Exception as e:
        logging.error(f"broadcast fetch users error: {e}")
        await update.message.reply_text("⚠️ صار خطأ بجلب قائمة المستخدمين.")
        return

    await update.message.reply_text(f"⏳ جاري الإرسال لـ {len(user_ids)} مستخدم...")

    sent = 0
    failed = 0
    for uid in user_ids:
        try:
            await context.bot.send_message(chat_id=uid, text=message_text)
            sent += 1
        except (Forbidden, BadRequest):
            failed += 1
        except Exception as e:
            logging.error(f"broadcast send error to {uid}: {e}")
            failed += 1
        await asyncio.sleep(0.05)  # تفادي حدود تيليجرام لسرعة الإرسال

    await update.message.reply_text(f"✅ تم الإرسال بنجاح لـ {sent} مستخدم.\n❌ فشل الإرسال لـ {failed} مستخدم.")


def main() -> None:
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("stats", stats))
    app.add_handler(CommandHandler("ban", ban))
    app.add_handler(CommandHandler("unban", unban))
    app.add_handler(CommandHandler("admin", admin))
    app.add_handler(CommandHandler("broadcast", broadcast))
    app.add_handler(CallbackQueryHandler(admin_callback, pattern="^admin_"))
    app.run_polling()


if __name__ == "__main__":
    main()
