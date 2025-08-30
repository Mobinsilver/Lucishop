# 🔧 راهنمای عیب‌یابی Railway

## 🚨 مشکلات رایج و راه‌حل‌ها

### 1. خطای "ImportError: cannot import name 'get_store'"
**مشکل**: `ImportError: cannot import name 'get_store' from 'store'`
**راه‌حل**: 
- تابع `get_store` در `admin_panel.py` به `load_store` تغییر یافته
- Import های circular برطرف شده‌اند
- Cache import ها اصلاح شده‌اند

### 2. خطای "ModuleNotFoundError"
**مشکل**: `ModuleNotFoundError: No module named 'flask'`
**راه‌حل**: Flask از requirements.txt حذف شده. ربات حالا فقط از Telegram webhook استفاده می‌کند.

### 3. خطای "Port already in use"
**مشکل**: دو سرویس سعی می‌کنند روی همان پورت اجرا شوند
**راه‌حل**: Flask app حذف شده. فقط Telegram webhook استفاده می‌شود.

### 4. خطای "TELEGRAM_BOT_TOKEN not set"
**مشکل**: متغیر محیطی تنظیم نشده
**راه‌حل**: در Railway Dashboard، متغیرهای زیر را اضافه کنید:
```
TELEGRAM_BOT_TOKEN=8308884100:AAEfcSUiiBKV-YIUZs8PUaV6Ik9Gh-3nvZE
OWNER_ID=5803428693
ADMIN_ID=6041119040
BOT_USERNAME=Crypto_navasan_bot
ENVIRONMENT=production
```

### 5. خطای "Import Error"
**مشکل**: فایل‌های ضروری وجود ندارند
**راه‌حل**: مطمئن شوید که تمام فایل‌های زیر در مخزن GitHub موجود هستند:
- main.py
- config.py
- requirements.txt
- store.json
- ta.py
- price_service.py
- fiat_service.py
- news_service.py
- history.py
- arbitrage.py
- p2p_service.py
- store.py
- cache.py
- security.py

### 6. خطای "Permission denied"
**مشکل**: دسترسی به فایل‌ها
**راه‌حل**: فایل‌ها باید قابل خواندن باشند. Dockerfile کاربر botuser را ایجاد می‌کند.

### 7. خطای "Webhook URL not set"
**مشکل**: WEBHOOK_URL تنظیم نشده
**راه‌حل**: Railway به صورت خودکار WEBHOOK_URL را تنظیم می‌کند. نیازی به تنظیم دستی نیست.

## 🔍 بررسی لاگ‌ها

### Railway Logs
1. وارد Railway Dashboard شوید
2. پروژه خود را انتخاب کنید
3. به بخش "Deployments" بروید
4. آخرین deployment را انتخاب کنید
5. لاگ‌ها را بررسی کنید

### لاگ‌های مهم
```
🚀 Starting Telegram Bot on Railway...
✅ Bot token is configured
✅ main.py exists
✅ config.py exists
✅ requirements.txt exists
✅ store.json exists
🤖 Starting bot...
Bot is running...
Starting webhook on port 8000
```

## 🛠️ مراحل عیب‌یابی

### مرحله 1: بررسی متغیرهای محیطی
```bash
# در Railway Dashboard بررسی کنید:
TELEGRAM_BOT_TOKEN=8308884100:AAEfcSUiiBKV-YIUZs8PUaV6Ik9Gh-3nvZE
OWNER_ID=5803428693
ADMIN_ID=6041119040
BOT_USERNAME=Crypto_navasan_bot
ENVIRONMENT=production
```

### مرحله 2: بررسی فایل‌ها
مطمئن شوید که تمام فایل‌های ضروری در GitHub موجود هستند.

### مرحله 3: Redeploy
1. در Railway Dashboard، روی "Deploy" کلیک کنید
2. منتظر بمانید تا build کامل شود
3. لاگ‌ها را بررسی کنید

### مرحله 4: تست ربات
1. به ربات پیام `/start` بدهید
2. بررسی کنید که ربات پاسخ دهد
3. دستور `/price btc` را تست کنید

## 📊 وضعیت فعلی

### ✅ مشکلات حل شده:
- [x] Flask conflict حذف شد
- [x] Webhook-only mode فعال شد
- [x] Requirements.txt بهینه شد
- [x] Railway startup script بهبود یافت
- [x] Dockerfile ساده شد
- [x] Error handling اضافه شد

### 🔄 در حال بررسی:
- [ ] Railway deployment
- [ ] Webhook functionality
- [ ] Bot responsiveness

## 📞 پشتیبانی

اگر مشکل همچنان ادامه دارد:
1. لاگ‌های کامل Railway را کپی کنید
2. خطای دقیق را مشخص کنید
3. مراحل انجام شده را توضیح دهید

---

**نکته**: این فایل برای عیب‌یابی مشکلات Railway ایجاد شده است.
