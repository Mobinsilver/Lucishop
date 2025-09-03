# 🚀 ربات آماده Deploy روی Railway

## 📋 اطلاعات ربات شما

- **نام ربات**: Crypto_navasan_bot
- **توکن**: 8308884100:AAEfcSUiiBKV-YIUZs8PUaV6Ik9Gh-3nvZE
- **مالک**: 5803428693
- **ادمین**: 6041119040

## 🔧 متغیرهای ضروری برای Railway

### متغیرهای اصلی:
```
TELEGRAM_BOT_TOKEN=8308884100:AAEfcSUiiBKV-YIUZs8PUaV6Ik9Gh-3nvZE
OWNER_ID=5803428693
ADMIN_ID=6041119040
BOT_USERNAME=Crypto_navasan_bot
WEBHOOK_URL=https://your-app-name.railway.app
PORT=8000
ENVIRONMENT=production
LOG_LEVEL=INFO
DEBUG=false
```

### متغیرهای اختیاری:
```
MAX_USERS=1000
REQUEST_TIMEOUT=30
RATE_LIMIT_PER_MINUTE=30
CACHE_TTL_SECONDS=180
MAX_CACHE_SIZE=1000
ALERT_CHECK_INTERVAL=60
MAX_ALERTS_PER_USER=10
MAX_WATCHLIST_ITEMS=50
MAX_PORTFOLIO_ITEMS=100
```

### متغیرهای API:
```
COINGECKO_API_URL=https://api.coingecko.com/api/v3
EXCHANGERATE_API_URL=https://api.exchangerate.host
BINANCE_API_URL=https://api.binance.com/api/v3
TABDEAL_API_URL=https://api1.tabdeal.org/r/api/v1
TABDEAL_API_KEY=einA3WTAOWYvNeBR9cdHIB6Tqbw3dkajeWJ8FSRqp3JHy5gr2STfoYMYWBXNa86X
TABDEAL_API_SECRET=TCzV5MY85pJe5O8NmhnsO6kGKo1X1jwIZm2XJifJtDbVaylEotj5TaNSykXnGWZP
BRS_API_URL=https://brsapi.ir/Api/Panel
BRS_API_KEY=BcFwJ8XAXX2SixD6f5UXuIx3cA5b7CBq
```

## 🎯 مراحل Deploy

### 1. اتصال به Railway
1. وارد [railway.app](https://railway.app) شوید
2. روی "New Project" کلیک کنید
3. "Deploy from GitHub repo" را انتخاب کنید
4. مخزن GitHub خود را انتخاب کنید

### 2. تنظیم متغیرهای محیطی
1. در Railway Dashboard، به بخش "Variables" بروید
2. تمام متغیرهای بالا را اضافه کنید
3. **مهم**: `WEBHOOK_URL` را با آدرس واقعی Railway خود جایگزین کنید

### 3. انتظار برای Deploy
- Railway به صورت خودکار پروژه را build می‌کند
- منتظر بمانید تا سرویس شروع به کار کند
- لاگ‌ها را بررسی کنید

### 4. تست ربات
1. به ربات خود پیام `/start` بدهید
2. بررسی کنید که ربات پاسخ دهد
3. دستور `/price btc` را تست کنید
4. تمام قابلیت‌ها را بررسی کنید

## 🎉 ویژگی‌های ربات

### 💰 قیمت ارزهای دیجیتال
- قیمت لحظه‌ای از CoinGecko و Binance
- نمایش تغییرات ۲۴ ساعته
- پشتیبانی از ارزهای مختلف (USD, EUR, IRR)
- نمایش تومان برای کاربران ایرانی

### 💱 نرخ ارز
- نرخ ارزهای فیات از ExchangeRate API
- پشتیبانی از ارزهای مختلف جهانی
- تبدیل خودکار به ریال ایران

### 📰 اخبار
- اخبار لحظه‌ای ارزهای دیجیتال
- فیلتر اخبار بر اساس نماد ارز
- منابع معتبر: Cointelegraph, Coindesk, NewsBTC

### 📊 نمودار و تحلیل تکنیکال
- نمودار sparkline برای نمایش روند قیمت
- تحلیل تکنیکال کامل شامل:
  - RSI (شاخص قدرت نسبی)
  - MACD (واگرایی و همگرایی میانگین متحرک)
  - میانگین متحرک ساده و نمایی
  - باندهای بولینگر
  - سطوح حمایت و مقاومت

### ⚖️ مقایسه قیمت
- مقایسه قیمت بین CoinGecko و Binance
- نمایش اختلاف قیمت به درصد

### 🔄 P2P
- قیمت‌های P2P بایننس
- پشتیبانی از ارزهای مختلف
- نمایش حداقل و حداکثر معاملات

### 👁 واچ‌لیست
- مدیریت لیست ارزهای مورد علاقه
- اضافه و حذف ارزها

### 📚 پرتفوی
- مدیریت پرتفوی شخصی
- محاسبه ارزش کل
- نمایش سود/زیان

### 🔔 هشدارها
- تنظیم هشدار قیمت
- اعلان‌های خودکار

### 🛠 تنظیمات
- انتخاب زبان (فارسی، انگلیسی، عربی)
- تنظیم ارز پایه
- تنظیمات نمایش

### 🔧 پنل مدیریتی
- مدیریت کاربران
- مدیریت ادمین‌ها
- ارسال پیام گروهی
- مدیریت متن‌ها
- مدیریت API ها
- مدیریت ارزها و شاخص‌ها
- آمار و گزارش‌ها
- مدیریت کش
- پشتیبان‌گیری

## 📱 دستورات ربات

### دستورات اصلی
- `/start` - شروع ربات
- `/help` - راهنما
- `/price <symbol>` - قیمت ارز (مثل: `/price btc`)
- `/admin` - پنل مدیریتی (فقط برای ادمین‌ها)

### دستورات میانبر
- `/btc`, `/eth`, `/bnb`, `/sol`, `/xrp`, `/ada`, `/doge`, `/ton`, `/trx`, `/ltc`

## 🔍 عیب‌یابی

### مشکل: ربات پاسخ نمی‌دهد
**راه‌حل:**
1. لاگ‌های Railway را بررسی کنید
2. متغیرهای محیطی را چک کنید
3. از endpoint `/health` برای تست استفاده کنید

### مشکل: خطای Dependencies
**راه‌حل:**
1. `requirements.txt` را بررسی کنید
2. Railway را مجدداً deploy کنید
3. لاگ‌های build را بررسی کنید

### مشکل: خطای Port
**راه‌حل:**
- Railway به طور خودکار PORT را تنظیم می‌کند
- نیازی به تنظیم دستی نیست

## 📊 مانیتورینگ

### Railway Dashboard
- بررسی آمار استفاده
- بررسی لاگ‌ها
- بررسی خطاها

### Health Check
- آدرس: `https://your-app-name.railway.app/health`
- باید پاسخ `{"status": "healthy", "bot": "running"}` بدهد

## 🔒 امنیت

- Rate limiting برای جلوگیری از اسپم
- Blacklist/Whitelist برای کنترل دسترسی
- بررسی عضویت اجباری در کانال
- محدودیت تعداد درخواست‌ها

## 🎉 موفقیت

پس از تکمیل تمام مراحل:
- ربات شما روی Railway فعال خواهد بود
- 24/7 در دسترس خواهد بود
- به طور خودکار restart می‌شود
- از webhook برای دریافت پیام‌ها استفاده می‌کند
- تمام قابلیت‌های پیشرفته فعال هستند

## 📞 پشتیبانی

در صورت بروز مشکل:
1. لاگ‌های Railway را بررسی کنید
2. متغیرهای محیطی را چک کنید
3. از endpoint `/health` برای تست استفاده کنید
4. فایل `deploy-checklist.md` را بررسی کنید

---

**نکته**: این ربات برای استفاده شخصی و آموزشی طراحی شده است. لطفاً از آن مسئولانه استفاده کنید.

**🎊 تبریک! ربات شما آماده Deploy است!**




