# راهنمای نصب ربات در Railway

## مراحل نصب:

### 1. ایجاد پروژه جدید در Railway
- به [railway.app](https://railway.app) بروید
- روی "New Project" کلیک کنید
- "Deploy from GitHub repo" را انتخاب کنید
- Repository خود را انتخاب کنید

### 2. تنظیم متغیرهای محیطی
در بخش Environment Variables، متغیرهای زیر را اضافه کنید:

```
BOT_TOKEN=8308884100:AAEfcSUiiBKV-YIUZs8PUaV6Ik9Gh-3nvZE
OWNER_ID=5803428693
BOT_USERNAME=Crypto_navasan_bot
TABDEAL_API_URL=https://api1.tabdeal.org/r/api/v1
TABDEAL_API_KEY=einA3WTAOWYvNeBR9cdHIB6Tqbw3dkajeWJ8FSRqp3JHy5gr2STfoYMYWBXNa86X
TABDEAL_API_SECRET=TCzV5MY85pJe5O8NmhnsO6kGKo1X1jwIZm2XJifJtDbVaylEotj5TaNSykXnGWZP
BRS_API_URL=https://brsapi.ir/Api/Panel
BRS_API_KEY=BcFwJ8XAXX2SixD6f5UXuIx3cA5b7CBq
ENVIRONMENT=production
DEBUG=false
LOG_LEVEL=INFO
PORT=8000
```

### 3. تنظیمات Railway
- **Start Command**: `python main.py`
- **Python Version**: 3.11.0
- **Build Command**: خودکار (Nixpacks)

### 4. ویژگی‌های ربات

#### ✅ ماشین حساب ارز برای گروه‌ها:
- فعال‌سازی: `ربات` در گروه
- محاسبه: `10 تتر`، `5 بیتکوین`، `100 دلار`
- تبدیل خودکار به تومان

#### ✅ پنل مدیریتی کامل:
- مدیریت ادمین‌ها
- ارسال همگانی
- تنظیم متن‌ها
- مدیریت API ها
- آمار و گزارش‌ها

#### ✅ قیمت‌گذاری ارزها:
- 5 ارز اصلی (شیشه‌ای): BTC, ETH, USDT, TON, TRX
- 238 ارز کامل (کیبورد)
- ارزهای داخلی (شیشه‌ای)

#### ✅ API های پشتیبانی شده:
- **Tabdeal**: ارزهای دیجیتال
- **BRS**: ارزهای داخلی و طلا
- **CoinGecko**: قیمت‌های جهانی
- **ExchangeRate**: نرخ ارزهای فیات

### 5. بررسی وضعیت
پس از نصب، در بخش Logs بررسی کنید:
- ✅ "Bot started successfully"
- ✅ "All handlers registered"
- ✅ "Ready to receive updates"

### 6. تست عملکرد
1. ربات را در گروه ادمین کنید
2. `ربات` بنویسید
3. `10 تتر` برای تست ماشین حساب
4. `/admin` برای تست پنل مدیریتی

## نکات مهم:
- ربات از webhook استفاده نمی‌کند (polling mode)
- همه handler ها تست شده‌اند
- ماشین حساب فقط در گروه‌ها کار می‌کند
- پنل مدیریتی فقط برای ادمین‌ها

## پشتیبانی:
در صورت مشکل، لاگ‌های Railway را بررسی کنید.
