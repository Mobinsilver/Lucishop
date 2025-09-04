# راهنمای نصب ربات کریپتو ناواسان در Railway

## 🚀 مراحل نصب

### 1. آماده‌سازی پروژه
```bash
# کلون کردن پروژه
git clone <repository-url>
cd bot

# بررسی فایل‌های موجود
ls -la
```

### 2. ایجاد پروژه در Railway
1. وارد [Railway.app](https://railway.app) شوید
2. روی "New Project" کلیک کنید
3. "Deploy from GitHub repo" را انتخاب کنید
4. ریپازیتوری خود را انتخاب کنید

### 3. تنظیم متغیرهای محیطی
در پنل Railway، به بخش "Variables" بروید و متغیرهای زیر را اضافه کنید:

#### متغیرهای ضروری:
```
TELEGRAM_BOT_TOKEN=8308884100:AAEfcSUiiBKV-YIUZs8PUaV6Ik9Gh-3nvZE
OWNER_ID=5803428693
ADMIN_ID=6041119040
BOT_USERNAME=Crypto_navasan_bot
```

#### متغیرهای Railway:
```
WEBHOOK_URL=https://your-app-name.railway.app/webhook
PORT=8000
ENVIRONMENT=production
```

#### متغیرهای اختیاری:
```
DEBUG=false
LOG_LEVEL=INFO
MAX_USERS=1000
REQUEST_TIMEOUT=30
```

### 4. تنظیم Webhook URL
1. بعد از deploy، URL پروژه خود را کپی کنید
2. متغیر `WEBHOOK_URL` را به صورت زیر تنظیم کنید:
```
WEBHOOK_URL=https://your-app-name.railway.app/webhook
```

### 5. Deploy
1. روی "Deploy" کلیک کنید
2. منتظر بمانید تا deploy کامل شود
3. لاگ‌ها را بررسی کنید

## 📋 فایل‌های مورد نیاز

### فایل‌های اصلی:
- `main.py` - فایل اصلی ربات
- `admin_panel.py` - پنل مدیریت
- `price_service.py` - سرویس قیمت‌ها
- `crypto_list.py` - لیست ارزها
- `store.py` - مدیریت داده‌ها
- `cache.py` - سیستم کش
- `config.py` - تنظیمات
- `security.py` - امنیت

### فایل‌های Railway:
- `Dockerfile` - کانتینر Docker
- `Procfile` - فرآیند Railway
- `railway-start.sh` - اسکریپت شروع
- `requirements.txt` - وابستگی‌ها

### فایل‌های داده:
- `store.json` - داده‌های ربات
- `.env` - متغیرهای محیطی (اختیاری)

## 🔧 تنظیمات پیشرفته

### تنظیم Domain:
1. در Railway، به بخش "Settings" بروید
2. "Custom Domain" را فعال کنید
3. Domain خود را تنظیم کنید

### تنظیم SSL:
- Railway به صورت خودکار SSL را فعال می‌کند
- نیازی به تنظیم دستی نیست

### تنظیم Auto-Deploy:
1. در بخش "Settings"
2. "Auto-Deploy" را فعال کنید
3. هر push به main branch، خودکار deploy می‌شود

## 🐛 عیب‌یابی

### مشکلات رایج:

#### 1. ربات شروع نمی‌شود:
- متغیرهای محیطی را بررسی کنید
- لاگ‌ها را در Railway بررسی کنید
- `TELEGRAM_BOT_TOKEN` را بررسی کنید

#### 2. Webhook کار نمی‌کند:
- `WEBHOOK_URL` را بررسی کنید
- URL باید با `/webhook` تمام شود
- SSL باید فعال باشد

#### 3. خطای Port:
- `PORT=8000` را تنظیم کنید
- Railway به صورت خودکار port را مدیریت می‌کند

### بررسی لاگ‌ها:
```bash
# در Railway، به بخش "Deployments" بروید
# روی آخرین deployment کلیک کنید
# لاگ‌ها را بررسی کنید
```

## 📊 مانیتورینگ

### بررسی وضعیت:
1. در Railway، بخش "Metrics" را بررسی کنید
2. CPU و Memory usage را مانیتور کنید
3. Response time را بررسی کنید

### آمار کاربران:
- از پنل مدیریت ربات استفاده کنید
- آمار کامل در دسترس است

## 🔒 امنیت

### تنظیمات امنیتی:
- تمام متغیرهای حساس در Railway Variables ذخیره شده‌اند
- API Key ها محافظت شده‌اند
- Rate limiting فعال است

### دسترسی‌ها:
- فقط Owner و Admin ها به پنل مدیریت دسترسی دارند
- لیست سیاه و سفید فعال است
- قفل اجباری عضویت پشتیبانی می‌شود

## 🎯 ویژگی‌های ربات

### قابلیت‌های اصلی:
- ✅ قیمت ارزهای دیجیتال
- ✅ قیمت ارزهای فیات
- ✅ اخبار کریپتو
- ✅ تحلیل تکنیکال
- ✅ P2P
- ✅ واچ‌لیست
- ✅ پرتفوی
- ✅ هشدارها

### قابلیت‌های مدیریتی:
- ✅ پنل مدیریت کامل
- ✅ مدیریت کاربران
- ✅ ارسال همگانی
- ✅ تنظیم متن‌ها
- ✅ مدیریت API
- ✅ قفل اجباری
- ✅ آمار و گزارش
- ✅ تنظیمات ربات

## 📞 پشتیبانی

در صورت بروز مشکل:
1. لاگ‌های Railway را بررسی کنید
2. متغیرهای محیطی را چک کنید
3. با تیم پشتیبانی تماس بگیرید

---

**🎉 ربات شما آماده استفاده است!**




