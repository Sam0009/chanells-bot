import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo, MessageEntity
from telegram.ext import Application, CommandHandler, ContextTypes

logging.basicConfig(level=logging.INFO)

# ضع التوكن هنا مباشرة أو عبر متغير بيئة BOT_TOKEN
BOT_TOKEN = os.environ.get("BOT_TOKEN", "ضع_التوكن_هنا")

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


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
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


def main() -> None:
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.run_polling()


if __name__ == "__main__":
    main()
