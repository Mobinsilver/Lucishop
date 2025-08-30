# راهنمای راه‌اندازی ربات روی Railway

## پیش‌نیازها

1. **حساب Railway**: در [railway.app](https://railway.app) ثبت‌نام کنید
2. **توکن ربات تلگرام**: از [@BotFather](https://t.me/BotFather) دریافت کنید
3. **GitHub**: پروژه را در GitHub push کنید

## مراحل راه‌اندازی

### 1. آماده‌سازی پروژه

پروژه شما آماده است و فایل‌های زیر اضافه شده‌اند:
- `Procfile` - تعریف نحوه اجرا
- `railway.json` - تنظیمات Railway
- `Dockerfile` - کانتینر Docker
- `runtime.txt` - نسخه Python
- `.dockerignore` - فایل‌های غیرضروری

### 2. Push به GitHub

```bash
git add .
git commit -m "Add Railway deployment files"
git push origin main
```

### 3. اتصال به Railway

1. وارد Railway شوید
2. روی "New Project" کلیک کنید
3. "Deploy from GitHub repo" را انتخاب کنید
4. مخزن GitHub خود را انتخاب کنید

### 4. تنظیم متغیرهای محیطی

در Railway، به بخش "Variables" بروید و این متغیرها را اضافه کنید:

```
TELEGRAM_BOT_TOKEN=8308884100:AAEfcSUiiBKV-YIUZs8PUaV6Ik9Gh-3nvZE
OWNER_ID=5803428693
ADMIN_ID=6041119040
BOT_USERNAME=Crypto_navasan_bot
ENVIRONMENT=production
```

**نکته مهم**: فایل `railway-variables.txt` شامل تمام متغیرهای مورد نیاز است.

### 5. تنظیم Webhook

پس از deploy موفق، URL دامنه Railway را کپی کنید و در BotFather تنظیم کنید:

```
https://your-domain.railway.app/webhook
```

## ساختار فایل‌ها

```
bot/
├── main.py                    # فایل اصلی ربات
├── config.py                  # تنظیمات ربات
├── requirements.txt           # وابستگی‌های Python
├── Procfile                  # تعریف Railway
├── railway.json              # تنظیمات Railway
├── Dockerfile                # کانتینر Docker
├── runtime.txt               # نسخه Python
├── .dockerignore             # فایل‌های غیرضروری
├── railway-start.sh          # اسکریپت راه‌اندازی
├── railway-variables.txt     # متغیرهای محیطی Railway
├── store.json                # تنظیمات اولیه ربات
└── README-RAILWAY.md         # این فایل
```

## عیب‌یابی

### مشکل: ربات پاسخ نمی‌دهد
- بررسی کنید که `TELEGRAM_BOT_TOKEN` درست تنظیم شده باشد
- Webhook URL را در BotFather بررسی کنید
- Log های Railway را چک کنید

### مشکل: خطای Port
- Railway به طور خودکار PORT را تنظیم می‌کند
- فایل `main.py` به طور خودکار از متغیر محیطی PORT استفاده می‌کند

### مشکل: خطای Dependencies
- همه وابستگی‌ها در `requirements.txt` موجود است
- Railway به طور خودکار آنها را نصب می‌کند

## نکات مهم

1. **Webhook vs Polling**: در Railway از webhook استفاده می‌شود، در local از polling
2. **Environment Variables**: همه متغیرهای محیطی باید در Railway تنظیم شوند
3. **Health Check**: endpoint `/health` برای بررسی وضعیت ربات
4. **Auto-restart**: Railway به طور خودکار ربات را restart می‌کند

## پشتیبانی

در صورت بروز مشکل:
1. Log های Railway را بررسی کنید
2. متغیرهای محیطی را چک کنید
3. Webhook URL را در BotFather بررسی کنید
4. از endpoint `/health` برای تست استفاده کنید
