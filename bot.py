import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import Application, CommandHandler, ContextTypes

logging.basicConfig(level=logging.INFO)

# ضع التوكن هنا مباشرة أو عبر متغير بيئة BOT_TOKEN
BOT_TOKEN = os.environ.get("BOT_TOKEN", "ضع_التوكن_هنا")

# رابط صفحة القنوات (GitHub Pages)
MINI_APP_URL = "https://sam0009.github.io/chanells/"

WELCOME_TEXT = (
    "😀 أهلاً فيك في شبكة قنواتنا الرسمية!\n\n"
    "يسرّنا انضمامك لأفضل محتوى رياضي 🔥\n"
    "اضغط الزر تحت لتصفح جميع القنوات دفعة وحدة، "
    "أو اختر رابط مباشر من الأسفل."
)

CHANNELS = [
    ("🇪🇸 برشا برشا بالعربية", "https://t.me/+FovoXWz0fLRhOTBk"),
    ("❤️ برشا برشا بالعربية (البديلة)", "https://t.me/+kSDCZZdUq8JmYmE0"),
    ("🐐 الأسطورة ميسي", "https://t.me/+i-dR3foyYqY5ZWEx"),
    ("⚽️ نادي برشلونة", "https://t.me/+cH6eGL-Y4_9mMzlh"),
    ("😍 برشا ساخر", "https://t.me/+QINP4DoQabQ4MTM0"),
    ("🖼 خلفيات | Wallpapers", "https://t.me/+dL4CJEcE1gNmYjRi"),
    ("🦁 البريميرليغ بالعربي", "https://t.me/+CfUPe5f9qpVhYTFk"),
    ("⚽️ أهداف المباريات", "https://t.me/+jrOHJcpB2WExY2Vk"),
]


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    buttons = [
        [InlineKeyboardButton("📺 تصفح جميع القنوات", web_app=WebAppInfo(url=MINI_APP_URL))]
    ]
    for name, link in CHANNELS:
        buttons.append([InlineKeyboardButton(name, url=link)])

    await update.message.reply_text(
        WELCOME_TEXT,
        reply_markup=InlineKeyboardMarkup(buttons),
    )


def main() -> None:
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.run_polling()


if __name__ == "__main__":
    main()
