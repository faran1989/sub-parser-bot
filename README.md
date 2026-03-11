# 🤖 ربات پارسر ساب‌اسکریپشن تلگرام

ربات تلگرامی که لینک ساب‌اسکریپشن V2Ray/Xray را دریافت کرده و کانفیگ‌ها را تکی‌تکی به صورت **متن + QR Code** ارسال می‌کند.

---

## ✨ قابلیت‌ها

- دریافت لینک ساب‌اسکریپشن و پارس خودکار
- دیکد Base64 خودکار
- ارسال هر کانفیگ به صورت جداگانه
- تولید QR Code برای هر کانفیگ
- نمایش نام و پروتکل هر کانفیگ
- دکمه‌های ناوبری (قبلی / بعدی)
- پشتیبانی از کانفیگ مستقیم (بدون لینک ساب)
- رابط کاربری فارسی

## 📡 پروتکل‌های پشتیبانی شده

VMess, VLESS, Trojan, Shadowsocks, ShadowsocksR, Hysteria, Hysteria2, TUIC, WireGuard

---

## 🚀 نصب و راه‌اندازی

### 1. نصب پیش‌نیازها

```bash
pip install -r requirements.txt
```

### 2. دریافت توکن ربات

1. به [@BotFather](https://t.me/BotFather) در تلگرام بروید
2. دستور `/newbot` را ارسال کنید
3. نام و یوزرنیم ربات را انتخاب کنید
4. توکن دریافتی را کپی کنید

### 3. تنظیم توکن

**روش اول - متغیر محیطی (توصیه شده):**

```bash
export BOT_TOKEN="1234567890:ABCdefGHIjklMNOpqrsTUVwxyz"
```

**روش دوم - مستقیم در کد:**

فایل `subscription_bot.py` را باز کرده و مقدار `BOT_TOKEN` را تغییر دهید.

### 4. اجرا

```bash
python subscription_bot.py
```

---

## 📖 نحوه استفاده

1. ربات را در تلگرام استارت کنید (`/start`)
2. لینک ساب‌اسکریپشن خود را ارسال کنید
3. ربات کانفیگ‌ها را پارس کرده و تکی ارسال می‌کند
4. با دکمه‌های ⬅️ و ➡️ بین کانفیگ‌ها جابجا شوید

---

## 🐳 اجرا با Docker (اختیاری)

```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY subscription_bot.py .
ENV BOT_TOKEN=""
CMD ["python", "subscription_bot.py"]
```

```bash
docker build -t sub-parser-bot .
docker run -d -e BOT_TOKEN="YOUR_TOKEN" sub-parser-bot
```
