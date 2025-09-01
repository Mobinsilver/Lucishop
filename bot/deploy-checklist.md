# ✅ چک‌لیست راه‌اندازی ربات

## 📋 اطلاعات ربات شما
- **نام ربات**: Crypto_navasan_bot
- **توکن**: 8308884100:AAEfcSUiiBKV-YIUZs8PUaV6Ik9Gh-3nvZE
- **مالک**: 5803428693
- **ادمین**: 6041119040

## 🔧 قبل از راه‌اندازی

### 1. تنظیمات تلگرام ✅
- [x] ربات در @BotFather ایجاد شده
- [x] توکن ربات دریافت شده: 8308884100:AAEfcSUiiBKV-YIUZs8PUaV6Ik9Gh-3nvZE
- [x] تنظیم webhook (اختیاری)

### 2. تنظیمات Railway
- [ ] اتصال مخزن GitHub به Railway
- [ ] تنظیم متغیرهای محیطی:
  - [ ] `TELEGRAM_BOT_TOKEN=8308884100:AAEfcSUiiBKV-YIUZs8PUaV6Ik9Gh-3nvZE`
  - [ ] `OWNER_ID=5803428693`
  - [ ] `BOT_USERNAME=Crypto_navasan_bot`
  - [ ] `ENVIRONMENT=production`
  - [ ] `TABDEAL_API_URL=https://api1.tabdeal.org/r/api/v1`
  - [ ] `TABDEAL_API_KEY=einA3WTAOWYvNeBR9cdHIB6Tqbw3dkajeWJ8FSRqp3JHy5gr2STfoYMYWBXNa86X`
  - [ ] `TABDEAL_API_SECRET=TCzV5MY85pJe5O8NmhnsO6kGKo1X1jwIZm2XJifJtDbVaylEotj5TaNSykXnGWZP`
  - [ ] `BRS_API_URL=https://brsapi.ir/Api/Panel`
  - [ ] `BRS_API_KEY=BcFwJ8XAXX2SixD6f5UXuIx3cA5b7CBq`
  - [ ] `WEBHOOK_URL` = آدرس webhook (خودکار)
  - [ ] `PORT` = 8000
  - [ ] `ENVIRONMENT` = production

### 3. بررسی فایل‌ها ✅
- [x] `main.py` - فایل اصلی ربات
- [x] `config.py` - تنظیمات (با توکن ربات)
- [x] `requirements.txt` - وابستگی‌ها
- [x] `Procfile` - تنظیمات Railway
- [x] `railway-start.sh` - اسکریپت راه‌اندازی
- [x] `store.json` - فایل ذخیره‌سازی (با آیدی مالک و ادمین)
- [x] `Dockerfile` - کانتینر داکر
- [x] `ta.py` - تحلیل تکنیکال
- [x] `railway-variables.txt` - متغیرهای محیطی

## 🚀 راه‌اندازی

### 1. Railway Deployment
- [ ] Deploy پروژه در Railway
- [ ] بررسی لاگ‌ها برای خطا
- [ ] تست health check endpoint: `https://your-app-name.railway.app/health`

### 2. تست ربات
- [ ] ارسال `/start` به ربات
- [ ] تست دستورات اصلی: `/price btc`
- [ ] تست منوی کیبورد
- [ ] تست تحلیل تکنیکال: 📈 تحلیل تکنیکال
- [ ] تست P2P: 🔄 P2P
- [ ] تست اخبار: 📰 اخبار

### 3. بررسی عملکرد
- [ ] سرعت پاسخ‌دهی
- [ ] کیفیت داده‌ها
- [ ] مدیریت خطاها
- [ ] امنیت

## 🔍 عیب‌یابی

### مشکلات رایج

#### 1. ربات پاسخ نمی‌دهد
- [ ] بررسی توکن ربات: 8308884100:AAEfcSUiiBKV-YIUZs8PUaV6Ik9Gh-3nvZE
- [ ] بررسی webhook URL
- [ ] بررسی لاگ‌های Railway

#### 2. خطای Import
- [ ] بررسی requirements.txt
- [ ] بررسی نسخه Python (3.11.7)
- [ ] بررسی وابستگی‌ها

#### 3. خطای API
- [ ] بررسی دسترسی به اینترنت
- [ ] بررسی محدودیت‌های API
- [ ] بررسی rate limiting

#### 4. خطای ذخیره‌سازی
- [ ] بررسی دسترسی به store.json
- [ ] بررسی فرمت JSON
- [ ] بررسی permissions

## 📊 مانیتورینگ

### 1. Railway Dashboard
- [ ] بررسی آمار استفاده
- [ ] بررسی لاگ‌ها
- [ ] بررسی خطاها

### 2. ربات Analytics
- [ ] تعداد کاربران
- [ ] تعداد پیام‌ها
- [ ] محبوب‌ترین دستورات

### 3. عملکرد API
- [ ] سرعت پاسخ‌دهی
- [ ] نرخ خطا
- [ ] محدودیت‌های API

## 🔒 امنیت

### 1. محافظت از داده‌ها
- [x] رمزگذاری توکن‌ها (در متغیرهای محیطی)
- [ ] محدودیت دسترسی
- [ ] پشتیبان‌گیری

### 2. Rate Limiting
- [x] محدودیت درخواست‌ها (12 درخواست در 10 ثانیه)
- [x] Blacklist/Whitelist برای کنترل دسترسی
- [x] محافظت از اسپم

### 3. به‌روزرسانی‌ها
- [ ] به‌روزرسانی وابستگی‌ها
- [ ] به‌روزرسانی کد
- [ ] تست امنیت

## 📈 بهینه‌سازی

### 1. عملکرد
- [x] بهینه‌سازی کش (TTL Cache)
- [ ] کاهش درخواست‌های API
- [ ] بهبود سرعت پاسخ

### 2. تجربه کاربری
- [x] بهبود رابط کاربری (منوی کیبورد)
- [x] اضافه کردن ویژگی‌های جدید (تحلیل تکنیکال)
- [ ] بهینه‌سازی پیام‌ها

### 3. مقیاس‌پذیری
- [ ] آماده‌سازی برای کاربران بیشتر
- [ ] بهینه‌سازی ذخیره‌سازی
- [ ] بهبود معماری

## 📞 پشتیبانی

### 1. مستندات
- [x] README کامل
- [x] راهنمای Railway
- [ ] API documentation

### 2. پشتیبانی فنی
- [ ] سیستم گزارش خطا
- [ ] کانال پشتیبانی
- [ ] FAQ

### 3. به‌روزرسانی‌ها
- [ ] برنامه به‌روزرسانی
- [ ] تغییرات نسخه
- [ ] Migration guide

## 🎯 قابلیت‌های فعال

### ✅ پیاده‌سازی شده
- [x] قیمت ارزهای دیجیتال (CoinGecko + Binance)
- [x] نرخ ارزهای فیات (ExchangeRate API)
- [x] اخبار ارزهای دیجیتال (RSS Feeds)
- [x] نمودار sparkline (7 روزه)
- [x] تحلیل تکنیکال (RSI, MACD, Bollinger Bands)
- [x] مقایسه قیمت (CoinGecko vs Binance)
- [x] قیمت‌های P2P (Binance P2P)
- [x] واچ‌لیست شخصی
- [x] پرتفوی شخصی
- [x] هشدارهای قیمت
- [x] تنظیمات چندزبانه (فارسی، انگلیسی، عربی)
- [x] سیستم کش
- [x] Rate limiting
- [x] Blacklist/Whitelist
- [x] Webhook support

### 🔄 در حال توسعه
- [ ] اعلان‌های خودکار
- [ ] نمودارهای پیشرفته
- [ ] تحلیل‌های بیشتر

---

**نکته**: این چک‌لیست باید قبل از هر deployment بررسی شود تا از عملکرد صحیح ربات اطمینان حاصل شود.

**وضعیت فعلی**: ربات آماده برای deployment روی Railway است. ✅
