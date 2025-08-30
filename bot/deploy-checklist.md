# ✅ چک‌لیست راه‌اندازی ربات روی Railway

## 🎯 اطلاعات ربات شما
- **نام ربات**: Crypto_navasan_bot
- **توکن**: 8308884100:AAEfcSUiiBKV-YIUZs8PUaV6Ik9Gh-3nvZE
- **مالک**: 5803428693
- **ادمین**: 6041119040

## 📋 مراحل راه‌اندازی

### مرحله 1: آماده‌سازی پروژه ✅
- [x] فایل‌های Railway اضافه شدند
- [x] تنظیمات ربات تکمیل شد
- [x] فایل config.py ایجاد شد
- [x] store.json به‌روزرسانی شد

### مرحله 2: Push به GitHub
```bash
git add .
git commit -m "Complete bot configuration for Railway deployment"
git push origin main
```

### مرحله 3: اتصال به Railway
1. [ ] وارد [railway.app](https://railway.app) شوید
2. [ ] روی "New Project" کلیک کنید
3. [ ] "Deploy from GitHub repo" را انتخاب کنید
4. [ ] مخزن GitHub خود را انتخاب کنید

### مرحله 4: تنظیم متغیرهای محیطی
در Railway، به بخش "Variables" بروید و این متغیرها را اضافه کنید:

**متغیرهای ضروری:**
- [ ] `TELEGRAM_BOT_TOKEN` = `8308884100:AAEfcSUiiBKV-YIUZs8PUaV6Ik9Gh-3nvZE`
- [ ] `OWNER_ID` = `5803428693`
- [ ] `ADMIN_ID` = `6041119040`
- [ ] `BOT_USERNAME` = `Crypto_navasan_bot`
- [ ] `ENVIRONMENT` = `production`

**متغیرهای اختیاری:**
- [ ] `LOG_LEVEL` = `INFO`
- [ ] `DEBUG` = `false`

### مرحله 5: انتظار برای Deploy
- [ ] منتظر بمانید تا Railway پروژه را build کند
- [ ] بررسی کنید که همه dependencies نصب شوند
- [ ] منتظر بمانید تا سرویس شروع به کار کند

### مرحله 6: دریافت دامنه Railway
- [ ] دامنه Railway را کپی کنید (مثلاً: `https://your-bot.railway.app`)
- [ ] این دامنه را برای تنظیم webhook نیاز دارید

### مرحله 7: تنظیم Webhook در BotFather
1. [ ] به [@BotFather](https://t.me/BotFather) پیام دهید
2. [ ] `/mybots` را تایپ کنید
3. [ ] ربات `Crypto_navasan_bot` را انتخاب کنید
4. [ ] "Bot Settings" → "Domain" را انتخاب کنید
5. [ ] دامنه Railway را وارد کنید
6. [ ] Webhook URL را تنظیم کنید: `https://your-domain.railway.app/webhook`

### مرحله 8: تست ربات
- [ ] به ربات پیام `/start` بدهید
- [ ] بررسی کنید که ربات پاسخ دهد
- [ ] دستور `/price btc` را تست کنید
- [ ] بررسی کنید که قیمت‌ها به ریال نمایش داده شوند

## 🚨 عیب‌یابی

### مشکل: ربات پاسخ نمی‌دهد
**راه‌حل:**
1. Log های Railway را بررسی کنید
2. متغیرهای محیطی را چک کنید
3. Webhook URL را در BotFather بررسی کنید
4. از endpoint `/health` برای تست استفاده کنید

### مشکل: خطای Dependencies
**راه‌حل:**
1. `requirements.txt` را بررسی کنید
2. Railway را مجدداً deploy کنید
3. Log های build را بررسی کنید

### مشکل: خطای Port
**راه‌حل:**
- Railway به طور خودکار PORT را تنظیم می‌کند
- نیازی به تنظیم دستی نیست

## 📞 پشتیبانی

در صورت بروز مشکل:
1. Log های Railway را بررسی کنید
2. متغیرهای محیطی را چک کنید
3. Webhook URL را در BotFather بررسی کنید
4. از endpoint `/health` برای تست استفاده کنید

## 🎉 موفقیت

پس از تکمیل تمام مراحل:
- ربات شما روی Railway فعال خواهد بود
- 24/7 در دسترس خواهد بود
- به طور خودکار restart می‌شود
- از webhook برای دریافت پیام‌ها استفاده می‌کند
