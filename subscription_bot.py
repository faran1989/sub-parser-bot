"""
ربات تلگرام - پارسر لینک ساب‌اسکریپشن
این ربات لینک ساب را دریافت کرده و کانفیگ‌ها را تکی‌تکی
به صورت متن + QR Code ارسال می‌کند.
"""

import os
import io
import base64
import logging
from urllib.parse import unquote, urlparse, parse_qs

import qrcode
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)

# ─── تنظیمات ───
BOT_TOKEN = os.getenv("BOT_TOKEN", "8606806760:AAGV4Bro5rnFUZyVPWaAvBPL9SwDahvo_Y8")
LOG_LEVEL = logging.INFO

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=LOG_LEVEL,
)
logger = logging.getLogger(__name__)

# ─── پروتکل‌های شناخته‌شده ───
KNOWN_PROTOCOLS = [
    "vmess://",
    "vless://",
    "trojan://",
    "ss://",
    "ssr://",
    "hysteria://",
    "hysteria2://",
    "hy2://",
    "tuic://",
    "warp://",
    "wireguard://",
]


# ═══════════════════════════════════════════
#  توابع کمکی
# ═══════════════════════════════════════════

def fetch_subscription(url: str) -> str:
    """دانلود محتوای لینک ساب‌اسکریپشن."""
    headers = {
        "User-Agent": "v2rayNG/1.8.5",
        "Accept": "*/*",
    }
    resp = requests.get(url, headers=headers, timeout=20)
    resp.raise_for_status()
    return resp.text.strip()


def decode_content(raw: str) -> str:
    """تلاش برای دیکد کردن Base64؛ در صورت شکست، متن خام برمی‌گردد."""
    try:
        decoded = base64.b64decode(raw + "==").decode("utf-8", errors="ignore")
        # بررسی اینکه آیا واقعاً کانفیگ معتبر است
        if any(proto in decoded for proto in KNOWN_PROTOCOLS):
            return decoded.strip()
    except Exception:
        pass
    return raw.strip()


def split_configs(content: str) -> list[str]:
    """جدا کردن کانفیگ‌ها از محتوای دیکد شده."""
    configs = []
    lines = content.replace("\r\n", "\n").split("\n")

    for line in lines:
        line = line.strip()
        if not line:
            continue
        if any(line.startswith(proto) for proto in KNOWN_PROTOCOLS):
            configs.append(line)

    return configs


def get_config_name(config: str) -> str:
    """استخراج نام/رمارک کانفیگ."""
    try:
        if config.startswith("vmess://"):
            raw = config[8:]
            padding = 4 - len(raw) % 4
            if padding != 4:
                raw += "=" * padding
            data = base64.b64decode(raw).decode("utf-8", errors="ignore")
            import json
            obj = json.loads(data)
            return obj.get("ps", "بدون نام")

        # برای بقیه پروتکل‌ها، نام معمولاً بعد از # است
        if "#" in config:
            name = config.split("#")[-1]
            return unquote(name).strip() or "بدون نام"
    except Exception:
        pass
    return "بدون نام"


def get_config_protocol(config: str) -> str:
    """استخراج نوع پروتکل."""
    for proto in KNOWN_PROTOCOLS:
        if config.startswith(proto):
            return proto.replace("://", "").upper()
    return "نامشخص"


def generate_qr(data: str) -> io.BytesIO:
    """تولید QR Code از کانفیگ."""
    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=8,
        border=3,
    )
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf


# ═══════════════════════════════════════════
#  هندلرهای ربات
# ═══════════════════════════════════════════

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """هندلر دستور /start."""
    welcome = (
        "👋 <b>سلام! به ربات پارسر ساب‌اسکریپشن خوش آمدید</b>\n\n"
        "📌 <b>راهنما:</b>\n"
        "لینک ساب‌اسکریپشن خود را ارسال کنید تا کانفیگ‌ها را "
        "به صورت تکی برای شما ارسال کنم.\n\n"
        "هر کانفیگ شامل:\n"
        "• 📝 متن کانفیگ (قابل کپی)\n"
        "• 📱 QR Code\n\n"
        "🔹 /help - راهنما\n"
        "🔹 /about - درباره ربات"
    )
    await update.message.reply_text(welcome, parse_mode="HTML")


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """هندلر دستور /help."""
    text = (
        "📖 <b>راهنمای استفاده</b>\n\n"
        "1️⃣ لینک ساب‌اسکریپشن خود را کپی کنید\n"
        "2️⃣ لینک را در چت ربات ارسال کنید\n"
        "3️⃣ منتظر بمانید تا کانفیگ‌ها پارس شوند\n"
        "4️⃣ هر کانفیگ به صورت جداگانه ارسال می‌شود\n\n"
        "⚠️ <b>نکته:</b> لینک باید با <code>http</code> یا "
        "<code>https</code> شروع شود.\n\n"
        "📌 <b>پروتکل‌های پشتیبانی شده:</b>\n"
        "VMess, VLESS, Trojan, Shadowsocks, ShadowsocksR, "
        "Hysteria, Hysteria2, TUIC, WireGuard"
    )
    await update.message.reply_text(text, parse_mode="HTML")


async def cmd_about(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """هندلر دستور /about."""
    text = (
        "ℹ️ <b>ربات پارسر ساب‌اسکریپشن</b>\n\n"
        "نسخه: 1.0.0\n"
        "زبان: Python\n"
        "فریمورک: python-telegram-bot\n\n"
        "این ربات لینک ساب‌اسکریپشن V2Ray/Xray را دریافت کرده "
        "و کانفیگ‌ها را به صورت تکی ارسال می‌کند."
    )
    await update.message.reply_text(text, parse_mode="HTML")


async def handle_subscription_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """پردازش لینک ساب‌اسکریپشن ارسال شده توسط کاربر."""
    url = update.message.text.strip()

    # بررسی اعتبار URL
    if not url.startswith(("http://", "https://")):
        await update.message.reply_text(
            "❌ لطفاً یک لینک معتبر ارسال کنید.\n"
            "لینک باید با <code>http://</code> یا <code>https://</code> شروع شود.",
            parse_mode="HTML",
        )
        return

    # پیام در حال پردازش
    status_msg = await update.message.reply_text("⏳ در حال دریافت کانفیگ‌ها...")

    try:
        # دریافت محتوای لینک
        raw_content = fetch_subscription(url)
        if not raw_content:
            await status_msg.edit_text("❌ لینک ساب خالی است یا پاسخی دریافت نشد.")
            return

        # دیکد کردن
        decoded = decode_content(raw_content)

        # جدا کردن کانفیگ‌ها
        configs = split_configs(decoded)

        if not configs:
            await status_msg.edit_text(
                "❌ هیچ کانفیگ معتبری در این لینک ساب یافت نشد.\n"
                "مطمئن شوید لینک ساب‌اسکریپشن معتبر است."
            )
            return

        # ذخیره کانفیگ‌ها در context برای صفحه‌بندی
        context.user_data["configs"] = configs
        context.user_data["current_page"] = 0

        await status_msg.edit_text(
            f"✅ <b>{len(configs)} کانفیگ یافت شد!</b>\n\n"
            f"در حال ارسال کانفیگ‌ها...",
            parse_mode="HTML",
        )

        # ارسال اولین کانفیگ
        await send_config(update, context, 0)

    except requests.exceptions.Timeout:
        await status_msg.edit_text("❌ زمان اتصال به لینک ساب به پایان رسید. لطفاً دوباره تلاش کنید.")
    except requests.exceptions.RequestException as e:
        await status_msg.edit_text(f"❌ خطا در دریافت لینک ساب:\n<code>{e}</code>", parse_mode="HTML")
    except Exception as e:
        logger.error(f"Error processing subscription: {e}")
        await status_msg.edit_text("❌ خطای غیرمنتظره. لطفاً دوباره تلاش کنید.")


async def send_config(update: Update, context: ContextTypes.DEFAULT_TYPE, index: int):
    """ارسال یک کانفیگ خاص به کاربر."""
    configs = context.user_data.get("configs", [])

    if index < 0 or index >= len(configs):
        return

    config = configs[index]
    total = len(configs)
    name = get_config_name(config)
    protocol = get_config_protocol(config)

    # ساخت متن پیام
    text = (
        f"📦 <b>کانفیگ {index + 1} از {total}</b>\n\n"
        f"📛 <b>نام:</b> {name}\n"
        f"🔹 <b>پروتکل:</b> {protocol}\n\n"
        f"<code>{config}</code>"
    )

    # ساخت دکمه‌های ناوبری
    buttons = []
    if index > 0:
        buttons.append(
            InlineKeyboardButton("⬅️ قبلی", callback_data=f"cfg_{index - 1}")
        )
    if index < total - 1:
        buttons.append(
            InlineKeyboardButton("بعدی ➡️", callback_data=f"cfg_{index + 1}")
        )

    keyboard = InlineKeyboardMarkup([buttons]) if buttons else None

    # تعیین chat_id
    chat_id = update.effective_chat.id

    # ارسال QR Code
    try:
        qr_buf = generate_qr(config)
        await context.bot.send_photo(
            chat_id=chat_id,
            photo=qr_buf,
            caption=text,
            parse_mode="HTML",
            reply_markup=keyboard,
        )
    except Exception as e:
        logger.error(f"QR generation error: {e}")
        # اگر QR خطا داشت، فقط متن ارسال شود
        await context.bot.send_message(
            chat_id=chat_id,
            text=text + "\n\n⚠️ تولید QR Code با خطا مواجه شد.",
            parse_mode="HTML",
            reply_markup=keyboard,
        )


async def callback_navigate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """هندلر دکمه‌های ناوبری بین کانفیگ‌ها."""
    query = update.callback_query
    await query.answer()

    data = query.data
    if not data.startswith("cfg_"):
        return

    try:
        index = int(data.split("_")[1])
    except (ValueError, IndexError):
        return

    configs = context.user_data.get("configs", [])
    if not configs or index < 0 or index >= len(configs):
        await query.answer("❌ کانفیگی یافت نشد.", show_alert=True)
        return

    context.user_data["current_page"] = index
    await send_config(update, context, index)


async def handle_direct_config(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """پردازش کانفیگ مستقیم (بدون لینک ساب)."""
    text = update.message.text.strip()

    # بررسی اینکه آیا یک کانفیگ مستقیم است
    if any(text.startswith(proto) for proto in KNOWN_PROTOCOLS):
        name = get_config_name(text)
        protocol = get_config_protocol(text)

        msg = (
            f"📦 <b>کانفیگ شناسایی شد</b>\n\n"
            f"📛 <b>نام:</b> {name}\n"
            f"🔹 <b>پروتکل:</b> {protocol}\n\n"
            f"<code>{text}</code>"
        )

        try:
            qr_buf = generate_qr(text)
            await update.message.reply_photo(
                photo=qr_buf,
                caption=msg,
                parse_mode="HTML",
            )
        except Exception:
            await update.message.reply_text(msg, parse_mode="HTML")
        return

    # اگر نه لینک بود و نه کانفیگ
    await update.message.reply_text(
        "🤔 متوجه نشدم! لطفاً یکی از موارد زیر را ارسال کنید:\n\n"
        "🔗 <b>لینک ساب‌اسکریپشن</b> (شروع با http)\n"
        "📝 <b>کانفیگ مستقیم</b> (مثل vmess://...)\n\n"
        "برای راهنما: /help",
        parse_mode="HTML",
    )


# ═══════════════════════════════════════════
#  اجرای ربات
# ═══════════════════════════════════════════

def main():
    """اجرای اصلی ربات."""
    if BOT_TOKEN == "YOUR_BOT_TOKEN_HERE":
        print("❌ لطفاً توکن ربات را تنظیم کنید!")
        print("   از @BotFather در تلگرام توکن بگیرید و در BOT_TOKEN قرار دهید.")
        print("   یا متغیر محیطی BOT_TOKEN را تنظیم کنید.")
        return

    app = Application.builder().token(BOT_TOKEN).build()

    # ثبت هندلرها
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(CommandHandler("about", cmd_about))
    app.add_handler(CallbackQueryHandler(callback_navigate, pattern=r"^cfg_\d+$"))

    # هندلر لینک‌ها
    app.add_handler(MessageHandler(filters.Regex(r"^https?://"), handle_subscription_link))

    # هندلر کانفیگ مستقیم و پیام‌های دیگر
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_direct_config))

    print("🤖 ربات در حال اجرا است...")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
