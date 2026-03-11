"""
ربات تلگرام - پارسر لینک ساب‌اسکریپشن (نسخه حرفه‌ای)
قابلیت‌ها:
- دریافت لینک ساب و پارس کانفیگ‌ها
- نمایش تمیز حجم/مدت از اسم کانفیگ
- راهنمای کپی-پیست وقتی لینک ارور میده
- دکمه ارسال همه کانفیگ‌ها یکجا
- فیلتر بر اساس پروتکل
- نمایش پرچم کشور سرور
- تست پینگ کانفیگ‌ها
- ذخیره لینک ساب و آپدیت خودکار
- پشتیبانی از چند لینک ساب همزمان
"""

import os
import io
import re
import json
import base64
import logging
import asyncio
import socket
from urllib.parse import unquote
from datetime import datetime

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
DATA_FILE = "user_subs.json"

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=LOG_LEVEL,
)
logger = logging.getLogger(__name__)

# ─── پروتکل‌های شناخته‌شده ───
KNOWN_PROTOCOLS = [
    "vmess://", "vless://", "trojan://", "ss://", "ssr://",
    "hysteria://", "hysteria2://", "hy2://", "tuic://",
    "warp://", "wireguard://",
]

# ─── پرچم کشورها ───
COUNTRY_FLAGS = {
    "us": "🇺🇸", "usa": "🇺🇸", "united states": "🇺🇸", "america": "🇺🇸",
    "uk": "🇬🇧", "gb": "🇬🇧", "united kingdom": "🇬🇧", "england": "🇬🇧",
    "de": "🇩🇪", "germany": "🇩🇪", "آلمان": "🇩🇪",
    "fr": "🇫🇷", "france": "🇫🇷", "فرانسه": "🇫🇷",
    "nl": "🇳🇱", "netherlands": "🇳🇱", "holland": "🇳🇱", "هلند": "🇳🇱",
    "ae": "🇦🇪", "uae": "🇦🇪", "emirates": "🇦🇪", "dubai": "🇦🇪", "امارات": "🇦🇪",
    "tr": "🇹🇷", "turkey": "🇹🇷", "ترکیه": "🇹🇷",
    "ir": "🇮🇷", "iran": "🇮🇷", "ایران": "🇮🇷",
    "ca": "🇨🇦", "canada": "🇨🇦", "کانادا": "🇨🇦",
    "fi": "🇫🇮", "finland": "🇫🇮", "فنلاند": "🇫🇮",
    "se": "🇸🇪", "sweden": "🇸🇪", "سوئد": "🇸🇪",
    "no": "🇳🇴", "norway": "🇳🇴", "نروژ": "🇳🇴",
    "jp": "🇯🇵", "japan": "🇯🇵", "ژاپن": "🇯🇵",
    "sg": "🇸🇬", "singapore": "🇸🇬", "سنگاپور": "🇸🇬",
    "hk": "🇭🇰", "hong kong": "🇭🇰",
    "kr": "🇰🇷", "korea": "🇰🇷", "کره": "🇰🇷",
    "in": "🇮🇳", "india": "🇮🇳", "هند": "🇮🇳",
    "au": "🇦🇺", "australia": "🇦🇺", "استرالیا": "🇦🇺",
    "ru": "🇷🇺", "russia": "🇷🇺", "روسیه": "🇷🇺",
    "it": "🇮🇹", "italy": "🇮🇹", "ایتالیا": "🇮🇹",
    "es": "🇪🇸", "spain": "🇪🇸", "اسپانیا": "🇪🇸",
    "pl": "🇵🇱", "poland": "🇵🇱", "لهستان": "🇵🇱",
    "ch": "🇨🇭", "switzerland": "🇨🇭", "سوئیس": "🇨🇭",
    "at": "🇦🇹", "austria": "🇦🇹", "اتریش": "🇦🇹",
    "ro": "🇷🇴", "romania": "🇷🇴",
    "bg": "🇧🇬", "bulgaria": "🇧🇬",
    "ua": "🇺🇦", "ukraine": "🇺🇦",
    "za": "🇿🇦", "south africa": "🇿🇦",
    "br": "🇧🇷", "brazil": "🇧🇷",
    "mx": "🇲🇽", "mexico": "🇲🇽",
    "tw": "🇹🇼", "taiwan": "🇹🇼",
    "id": "🇮🇩", "indonesia": "🇮🇩",
    "my": "🇲🇾", "malaysia": "🇲🇾",
    "th": "🇹🇭", "thailand": "🇹🇭",
    "vn": "🇻🇳", "vietnam": "🇻🇳",
}


# ═══════════════════════════════════════════
#  ذخیره و بازیابی اطلاعات کاربران
# ═══════════════════════════════════════════

def load_user_data() -> dict:
    try:
        if os.path.exists(DATA_FILE):
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass
    return {}


def save_user_data(data: dict):
    try:
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"Error saving: {e}")


def get_user_subs(user_id: int) -> list:
    data = load_user_data()
    return data.get(str(user_id), {}).get("subs", [])


def add_user_sub(user_id: int, url: str, name: str = ""):
    data = load_user_data()
    uid = str(user_id)
    if uid not in data:
        data[uid] = {"subs": []}
    for sub in data[uid]["subs"]:
        if sub["url"] == url:
            sub["updated"] = datetime.now().strftime("%Y-%m-%d %H:%M")
            save_user_data(data)
            return False
    data[uid]["subs"].append({
        "url": url,
        "name": name or f"ساب {len(data[uid]['subs']) + 1}",
        "added": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "updated": datetime.now().strftime("%Y-%m-%d %H:%M"),
    })
    save_user_data(data)
    return True


def remove_user_sub(user_id: int, index: int) -> bool:
    data = load_user_data()
    uid = str(user_id)
    if uid in data and 0 <= index < len(data[uid]["subs"]):
        data[uid]["subs"].pop(index)
        save_user_data(data)
        return True
    return False


# ═══════════════════════════════════════════
#  توابع کمکی
# ═══════════════════════════════════════════

def fetch_subscription(url: str) -> str:
    headers = {"User-Agent": "v2rayNG/1.8.5", "Accept": "*/*"}
    resp = requests.get(url, headers=headers, timeout=60)
    resp.raise_for_status()
    return resp.text.strip()


def decode_content(raw: str) -> str:
    try:
        decoded = base64.b64decode(raw + "==").decode("utf-8", errors="ignore")
        if any(proto in decoded for proto in KNOWN_PROTOCOLS):
            return decoded.strip()
    except Exception:
        pass
    return raw.strip()


def split_configs(content: str) -> list[str]:
    configs = []
    lines = content.replace("\r\n", "\n").split("\n")
    for line in lines:
        line = line.strip()
        if line and any(line.startswith(proto) for proto in KNOWN_PROTOCOLS):
            configs.append(line)
    return configs


def get_config_name(config: str) -> str:
    try:
        if config.startswith("vmess://"):
            raw = config[8:]
            padding = 4 - len(raw) % 4
            if padding != 4:
                raw += "=" * padding
            data = base64.b64decode(raw).decode("utf-8", errors="ignore")
            obj = json.loads(data)
            return obj.get("ps", "بدون نام")
        if "#" in config:
            name = config.split("#")[-1]
            return unquote(name).strip() or "بدون نام"
    except Exception:
        pass
    return "بدون نام"


def get_config_protocol(config: str) -> str:
    for proto in KNOWN_PROTOCOLS:
        if config.startswith(proto):
            return proto.replace("://", "").upper()
    return "نامشخص"


def get_config_host(config: str) -> str:
    try:
        if config.startswith("vmess://"):
            raw = config[8:]
            padding = 4 - len(raw) % 4
            if padding != 4:
                raw += "=" * padding
            data = base64.b64decode(raw).decode("utf-8", errors="ignore")
            obj = json.loads(data)
            return obj.get("add", "")
        proto_end = config.index("://") + 3
        rest = config[proto_end:]
        if "@" in rest:
            after_at = rest.split("@")[1]
            host_part = after_at.split(":")[0].split("?")[0].split("/")[0]
            return host_part
    except Exception:
        pass
    return ""


def get_config_port(config: str) -> int:
    try:
        if config.startswith("vmess://"):
            raw = config[8:]
            padding = 4 - len(raw) % 4
            if padding != 4:
                raw += "=" * padding
            obj = json.loads(base64.b64decode(raw).decode())
            return int(obj.get("port", 443))
        proto_end = config.index("://") + 3
        rest = config[proto_end:]
        if "@" in rest:
            after_at = rest.split("@")[1]
            port_str = after_at.split(":")[1].split("?")[0].split("/")[0].split("#")[0]
            return int(port_str)
    except Exception:
        pass
    return 443


def extract_volume_duration(name: str) -> dict:
    info = {"volume": None, "duration": None, "clean_name": name}
    vol_match = re.search(r'(\d+(?:\.\d+)?)\s*(?:GB|gb|گیگ)', name)
    if vol_match:
        info["volume"] = vol_match.group(1) + " GB"
    dur_match = re.search(r'(\d+)\s*(?:D|d|روز|روزه|day|days)', name)
    if dur_match:
        info["duration"] = dur_match.group(1) + " روز"
    clean = name
    clean = re.sub(r'[\-_]?\d+(?:\.\d+)?\s*(?:GB|gb|گیگ)[📊📈]*', '', clean)
    clean = re.sub(r'[\-_]?\d+\s*(?:D|d|روز|روزه|day|days)[⏳⌛]*', '', clean)
    clean = re.sub(r'[📊📈⏳⌛🔋💾]', '', clean)
    clean = re.sub(r'\s+', ' ', clean).strip().strip('-_').strip()
    if clean:
        info["clean_name"] = clean
    return info


def detect_country(name: str, host: str) -> str:
    flag_pattern = re.findall(r'[\U0001F1E0-\U0001F1FF]{2}', name)
    if flag_pattern:
        return flag_pattern[0]
    name_lower = name.lower()
    for key, flag in COUNTRY_FLAGS.items():
        if key in name_lower:
            return flag
    host_lower = host.lower()
    for key, flag in COUNTRY_FLAGS.items():
        if key in host_lower:
            return flag
    return "🌍"


async def ping_host(host: str, port: int = 443) -> str:
    try:
        loop = asyncio.get_event_loop()
        start = loop.time()

        def _connect():
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            try:
                sock.connect((host, port))
                return True
            except Exception:
                return False
            finally:
                sock.close()

        result = await loop.run_in_executor(None, _connect)
        end = loop.time()

        if result:
            ms = int((end - start) * 1000)
            if ms < 100:
                return f"🟢 {ms}ms"
            elif ms < 300:
                return f"🟡 {ms}ms"
            else:
                return f"🔴 {ms}ms"
        return "❌ غیرفعال"
    except Exception:
        return "❌ خطا"


def generate_qr(data: str) -> io.BytesIO:
    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=8, border=3,
    )
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf


def build_config_text(config: str, index: int, total: int) -> str:
    raw_name = get_config_name(config)
    protocol = get_config_protocol(config)
    host = get_config_host(config)
    info = extract_volume_duration(raw_name)
    country = detect_country(raw_name, host)

    text = f"📦 <b>کانفیگ {index + 1} از {total}</b>\n\n"
    text += f"📛 <b>نام:</b> {info['clean_name']}\n"
    text += f"🔹 <b>پروتکل:</b> {protocol}\n"
    text += f"{country} <b>کشور:</b> {country}\n"
    if info["volume"]:
        text += f"📊 <b>حجم:</b> {info['volume']}\n"
    if info["duration"]:
        text += f"⏳ <b>مدت:</b> {info['duration']}\n"
    if host:
        text += f"🖥 <b>سرور:</b> <code>{host}</code>\n"
    text += f"\n<code>{config}</code>"
    return text


# ═══════════════════════════════════════════
#  هندلرهای ربات
# ═══════════════════════════════════════════

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome = (
        "👋 <b>سلام! به ربات پارسر ساب خوش آمدید</b>\n\n"
        "📌 <b>روش‌های استفاده:</b>\n\n"
        "1️⃣ <b>لینک ساب:</b> لینک ساب‌اسکریپشن ارسال کنید\n"
        "2️⃣ <b>متن خام:</b> متن Base64 یا کانفیگ‌ها را پیست کنید\n"
        "3️⃣ <b>کانفیگ تکی:</b> یک کانفیگ مستقیم ارسال کنید\n\n"
        "📋 <b>دستورات:</b>\n"
        "🔹 /help - راهنمای کامل\n"
        "🔹 /mysubs - لیست ساب‌های ذخیره شده\n"
        "🔹 /delsub - حذف ساب ذخیره شده\n"
        "🔹 /update - آپدیت همه ساب‌ها\n"
        "🔹 /about - درباره ربات"
    )
    await update.message.reply_text(welcome, parse_mode="HTML")


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "📖 <b>راهنمای کامل ربات</b>\n\n"
        "━━━━━━━━━━━━━━━\n"
        "📡 <b>روش ۱: ارسال لینک ساب</b>\n"
        "لینک ساب را ارسال کنید. کانفیگ‌ها پارس شده و "
        "لینک خودکار ذخیره می‌شود.\n\n"
        "📋 <b>روش ۲: کپی-پیست</b>\n"
        "اگر لینک ارور داد، متن خام Base64 یا کانفیگ‌ها "
        "را از اپ کپی و پیست کنید.\n\n"
        "📝 <b>روش ۳: کانفیگ مستقیم</b>\n"
        "یک کانفیگ تکی ارسال کنید.\n\n"
        "━━━━━━━━━━━━━━━\n"
        "🔘 <b>دکمه‌ها:</b>\n"
        "⬅️➡️ جابجایی بین کانفیگ‌ها\n"
        "📦 همه - دریافت همه یکجا\n"
        "🔍 فیلتر - فیلتر پروتکل\n"
        "📡 پینگ - تست اتصال\n\n"
        "━━━━━━━━━━━━━━━\n"
        "📌 <b>پروتکل‌ها:</b>\n"
        "VMess, VLESS, Trojan, SS, SSR, "
        "Hysteria, Hysteria2, TUIC, WireGuard"
    )
    await update.message.reply_text(text, parse_mode="HTML")


async def cmd_about(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "ℹ️ <b>ربات پارسر ساب v2.0</b>\n\n"
        "✨ <b>قابلیت‌ها:</b>\n"
        "• پارس لینک ساب و Base64\n"
        "• نمایش حجم، مدت، کشور\n"
        "• QR Code\n"
        "• تست پینگ\n"
        "• فیلتر پروتکل\n"
        "• ذخیره و آپدیت ساب‌ها\n"
        "• چند ساب همزمان"
    )
    await update.message.reply_text(text, parse_mode="HTML")


async def cmd_mysubs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    subs = get_user_subs(update.effective_user.id)
    if not subs:
        await update.message.reply_text(
            "📭 ساب‌اسکریپشنی ذخیره نشده.\n"
            "لینک ساب ارسال کنید تا خودکار ذخیره شود."
        )
        return

    text = "📋 <b>ساب‌های ذخیره شده:</b>\n\n"
    buttons = []
    for i, sub in enumerate(subs):
        text += f"{i + 1}. <b>{sub['name']}</b>\n"
        text += f"   🔗 <code>{sub['url'][:50]}...</code>\n"
        text += f"   📅 آپدیت: {sub.get('updated', '—')}\n\n"
        buttons.append([InlineKeyboardButton(
            f"📡 آپدیت ساب {i + 1}", callback_data=f"updatesub_{i}"
        )])

    keyboard = InlineKeyboardMarkup(buttons) if buttons else None
    await update.message.reply_text(text, parse_mode="HTML", reply_markup=keyboard)


async def cmd_delsub(update: Update, context: ContextTypes.DEFAULT_TYPE):
    subs = get_user_subs(update.effective_user.id)
    if not subs:
        await update.message.reply_text("📭 ساب‌اسکریپشنی برای حذف نیست.")
        return
    buttons = []
    for i, sub in enumerate(subs):
        buttons.append([InlineKeyboardButton(
            f"🗑 حذف: {sub['name']}", callback_data=f"delsub_{i}"
        )])
    await update.message.reply_text(
        "🗑 <b>کدام ساب حذف شود؟</b>",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(buttons),
    )


async def cmd_update(update: Update, context: ContextTypes.DEFAULT_TYPE):
    subs = get_user_subs(update.effective_user.id)
    if not subs:
        await update.message.reply_text("📭 ساب‌اسکریپشنی برای آپدیت نیست.")
        return

    status_msg = await update.message.reply_text("⏳ در حال آپدیت...")
    all_configs = []
    results = []
    for sub in subs:
        try:
            raw = fetch_subscription(sub["url"])
            decoded = decode_content(raw)
            configs = split_configs(decoded)
            all_configs.extend(configs)
            results.append(f"✅ {sub['name']}: {len(configs)} کانفیگ")
        except Exception:
            results.append(f"❌ {sub['name']}: خطا")

    if all_configs:
        context.user_data["configs"] = all_configs
        context.user_data["current_page"] = 0
        context.user_data["filter_protocol"] = None
        text = "📡 <b>نتیجه آپدیت:</b>\n\n" + "\n".join(results)
        text += f"\n\n📦 <b>مجموع: {len(all_configs)} کانفیگ</b>"
        await status_msg.edit_text(text, parse_mode="HTML")
        await send_config(update, context, 0)
    else:
        await status_msg.edit_text("❌ کانفیگی دریافت نشد.\n\n" + "\n".join(results))


async def handle_subscription_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text.strip()
    if not url.startswith(("http://", "https://")):
        return

    status_msg = await update.message.reply_text("⏳ در حال دریافت کانفیگ‌ها...")

    try:
        raw_content = fetch_subscription(url)
        if not raw_content:
            await status_msg.edit_text("❌ لینک ساب خالی است.")
            return

        decoded = decode_content(raw_content)
        configs = split_configs(decoded)

        if not configs:
            await status_msg.edit_text("❌ کانفیگ معتبری یافت نشد.")
            return

        is_new = add_user_sub(update.effective_user.id, url)
        context.user_data["configs"] = configs
        context.user_data["current_page"] = 0
        context.user_data["filter_protocol"] = None

        save_text = " (ذخیره شد ✅)" if is_new else ""

        protocols = {}
        for c in configs:
            p = get_config_protocol(c)
            protocols[p] = protocols.get(p, 0) + 1
        proto_text = " | ".join([f"{k}: {v}" for k, v in protocols.items()])

        await status_msg.edit_text(
            f"✅ <b>{len(configs)} کانفیگ یافت شد!</b>{save_text}\n"
            f"📊 {proto_text}\n\nدر حال ارسال...",
            parse_mode="HTML",
        )
        await send_config(update, context, 0)

    except (requests.exceptions.Timeout, requests.exceptions.ConnectionError):
        await status_msg.edit_text(
            "❌ <b>لینک ساب قابل دسترسی نیست</b>\n\n"
            "🔧 <b>راه‌حل:</b>\n"
            "احتمالاً این لینک فقط از داخل ایران باز می‌شود.\n\n"
            "📋 <b>لطفاً:</b>\n"
            "1️⃣ لینک ساب را در اپ (v2rayNG, V2Box, Happ) اضافه کنید\n"
            "2️⃣ کانفیگ‌ها را کپی کنید\n"
            "3️⃣ اینجا پیست کنید\n\n"
            "💡 یا متن خام Base64 ساب را پیست کنید.",
            parse_mode="HTML",
        )
    except requests.exceptions.RequestException as e:
        await status_msg.edit_text(f"❌ خطا:\n<code>{e}</code>", parse_mode="HTML")
    except Exception as e:
        logger.error(f"Error: {e}")
        await status_msg.edit_text("❌ خطای غیرمنتظره.")


async def send_config(update: Update, context: ContextTypes.DEFAULT_TYPE, index: int):
    configs = context.user_data.get("configs", [])
    filter_proto = context.user_data.get("filter_protocol")

    filtered = [c for c in configs if get_config_protocol(c) == filter_proto] if filter_proto else configs

    if not filtered:
        await context.bot.send_message(
            chat_id=update.effective_chat.id, text="❌ کانفیگی یافت نشد."
        )
        return

    index = max(0, min(index, len(filtered) - 1))
    config = filtered[index]
    total = len(filtered)
    text = build_config_text(config, index, total)

    # دکمه‌ها
    nav = []
    if index > 0:
        nav.append(InlineKeyboardButton("⬅️ قبلی", callback_data=f"cfg_{index - 1}"))
    nav.append(InlineKeyboardButton(f"📄 {index + 1}/{total}", callback_data="noop"))
    if index < total - 1:
        nav.append(InlineKeyboardButton("بعدی ➡️", callback_data=f"cfg_{index + 1}"))

    actions = [
        InlineKeyboardButton("📦 همه", callback_data="send_all"),
        InlineKeyboardButton("🔍 فیلتر", callback_data="filter_menu"),
        InlineKeyboardButton("📡 پینگ", callback_data=f"ping_{index}"),
    ]

    keyboard = InlineKeyboardMarkup([nav, actions])

    try:
        qr_buf = generate_qr(config)
        await context.bot.send_photo(
            chat_id=update.effective_chat.id,
            photo=qr_buf, caption=text,
            parse_mode="HTML", reply_markup=keyboard,
        )
    except Exception as e:
        logger.error(f"QR error: {e}")
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=text + "\n\n⚠️ خطا در تولید QR Code.",
            parse_mode="HTML", reply_markup=keyboard,
        )


async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data.startswith("cfg_"):
        index = int(data.split("_")[1])
        context.user_data["current_page"] = index
        await send_config(update, context, index)

    elif data == "noop":
        pass

    elif data == "send_all":
        configs = context.user_data.get("configs", [])
        fp = context.user_data.get("filter_protocol")
        filtered = [c for c in configs if get_config_protocol(c) == fp] if fp else configs

        if not filtered:
            await query.answer("❌ کانفیگی نیست.", show_alert=True)
            return

        # فایل متنی
        content = ""
        for i, c in enumerate(filtered):
            name = get_config_name(c)
            proto = get_config_protocol(c)
            info = extract_volume_duration(name)
            content += f"# {i+1}. {info['clean_name']} ({proto})\n{c}\n\n"

        buf = io.BytesIO(content.encode("utf-8"))
        buf.name = "configs.txt"
        await context.bot.send_document(
            chat_id=update.effective_chat.id, document=buf,
            caption=f"📦 <b>{len(filtered)} کانفیگ</b>",
            parse_mode="HTML",
        )

        # متن قابل کپی
        all_text = "\n".join(filtered)
        if len(all_text) <= 4000:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=f"📋 <b>قابل کپی:</b>\n\n<code>{all_text}</code>",
                parse_mode="HTML",
            )
        else:
            chunks, current = [], ""
            for c in filtered:
                if len(current) + len(c) + 1 > 3900:
                    chunks.append(current)
                    current = c
                else:
                    current += "\n" + c if current else c
            if current:
                chunks.append(current)
            for i, chunk in enumerate(chunks):
                await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text=f"📋 <b>بخش {i+1}:</b>\n\n<code>{chunk}</code>",
                    parse_mode="HTML",
                )

    elif data == "filter_menu":
        configs = context.user_data.get("configs", [])
        protocols = {}
        for c in configs:
            p = get_config_protocol(c)
            protocols[p] = protocols.get(p, 0) + 1

        buttons = [[InlineKeyboardButton(
            f"{proto} ({count})", callback_data=f"filter_{proto}"
        )] for proto, count in protocols.items()]
        buttons.append([InlineKeyboardButton("🔄 همه", callback_data="filter_ALL")])

        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="🔍 <b>فیلتر پروتکل:</b>",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(buttons),
        )

    elif data.startswith("filter_"):
        proto = data.split("_", 1)[1]
        context.user_data["filter_protocol"] = None if proto == "ALL" else proto
        context.user_data["current_page"] = 0
        await send_config(update, context, 0)

    elif data.startswith("ping_"):
        index = int(data.split("_")[1])
        configs = context.user_data.get("configs", [])
        fp = context.user_data.get("filter_protocol")
        filtered = [c for c in configs if get_config_protocol(c) == fp] if fp else configs

        if 0 <= index < len(filtered):
            config = filtered[index]
            host = get_config_host(config)
            if not host:
                await query.answer("❌ آدرس سرور نامشخص.", show_alert=True)
                return

            port = get_config_port(config)
            ping_result = await ping_host(host, port)

            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=f"📡 <b>تست پینگ:</b>\n\n"
                     f"🖥 <code>{host}:{port}</code>\n"
                     f"📶 {ping_result}",
                parse_mode="HTML",
            )

    elif data.startswith("updatesub_"):
        index = int(data.split("_")[1])
        subs = get_user_subs(update.effective_user.id)
        if 0 <= index < len(subs):
            sub = subs[index]
            msg = await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=f"⏳ آپدیت {sub['name']}...",
            )
            try:
                raw = fetch_subscription(sub["url"])
                configs = split_configs(decode_content(raw))
                if configs:
                    context.user_data["configs"] = configs
                    context.user_data["current_page"] = 0
                    context.user_data["filter_protocol"] = None
                    await msg.edit_text(f"✅ <b>{len(configs)} کانفیگ آپدیت شد!</b>", parse_mode="HTML")
                    await send_config(update, context, 0)
                else:
                    await msg.edit_text("❌ کانفیگی نیست.")
            except Exception:
                await msg.edit_text("❌ خطا. کانفیگ‌ها را کپی-پیست کنید.")

    elif data.startswith("delsub_"):
        index = int(data.split("_")[1])
        if remove_user_sub(update.effective_user.id, index):
            await context.bot.send_message(
                chat_id=update.effective_chat.id, text="✅ ساب حذف شد."
            )


async def handle_direct_config(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()

    # کانفیگ مستقیم
    if any(text.startswith(proto) for proto in KNOWN_PROTOCOLS):
        lines = text.replace("\r\n", "\n").split("\n")
        multi = [l.strip() for l in lines if any(l.strip().startswith(p) for p in KNOWN_PROTOCOLS)]

        if len(multi) > 1:
            context.user_data["configs"] = multi
            context.user_data["current_page"] = 0
            context.user_data["filter_protocol"] = None
            await update.message.reply_text(
                f"✅ <b>{len(multi)} کانفیگ یافت شد!</b>", parse_mode="HTML"
            )
            await send_config(update, context, 0)
            return

        config = multi[0] if multi else text
        msg_text = build_config_text(config, 0, 1)
        try:
            qr_buf = generate_qr(config)
            await update.message.reply_photo(photo=qr_buf, caption=msg_text, parse_mode="HTML")
        except Exception:
            await update.message.reply_text(msg_text, parse_mode="HTML")
        return

    # Base64
    decoded = decode_content(text)
    configs = split_configs(decoded)
    if configs:
        context.user_data["configs"] = configs
        context.user_data["current_page"] = 0
        context.user_data["filter_protocol"] = None
        await update.message.reply_text(
            f"✅ <b>{len(configs)} کانفیگ یافت شد!</b>", parse_mode="HTML"
        )
        await send_config(update, context, 0)
        return

    await update.message.reply_text(
        "🤔 متوجه نشدم!\n\n"
        "🔗 <b>لینک ساب</b> (http...)\n"
        "📝 <b>کانفیگ</b> (vmess://...)\n"
        "📋 <b>متن Base64</b>\n\n"
        "/help برای راهنما",
        parse_mode="HTML",
    )


# ═══════════════════════════════════════════

def main():
    if BOT_TOKEN == "YOUR_BOT_TOKEN_HERE":
        print("❌ توکن ربات را تنظیم کنید!")
        return

    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(CommandHandler("about", cmd_about))
    app.add_handler(CommandHandler("mysubs", cmd_mysubs))
    app.add_handler(CommandHandler("delsub", cmd_delsub))
    app.add_handler(CommandHandler("update", cmd_update))
    app.add_handler(CallbackQueryHandler(callback_handler))
    app.add_handler(MessageHandler(filters.Regex(r"^https?://"), handle_subscription_link))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_direct_config))

    print("🤖 ربات v2.0 حرفه‌ای در حال اجرا...")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
