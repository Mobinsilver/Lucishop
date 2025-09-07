# 🔧 تصحیح متغیرهای محیطی Railway

## ❌ مشکل:
```
ValueError: invalid literal for int() with base 10: 'OWNER_ID'
```

## ✅ راه حل:

### 1. بررسی متغیرهای محیطی در Railway:
در داشبورد Railway، بخش **Variables** را بررسی کنید:

#### ❌ اشتباه:
```
OWNER_ID=OWNER_ID
BOT_TOKEN=BOT_TOKEN
```

#### ✅ درست:
```
OWNER_ID=5803428693
BOT_TOKEN=8308884100:AAEfcSUiiBKV-YIUZs8PUaV6Ik9Gh-3nvZE
```

### 2. متغیرهای صحیح برای Railway:

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

### 3. مراحل تصحیح:

1. **وارد داشبورد Railway شوید**
2. **پروژه خود را انتخاب کنید**
3. **روی "Variables" کلیک کنید**
4. **متغیرهای اشتباه را حذف کنید**
5. **متغیرهای صحیح را اضافه کنید**
6. **"Deploy" را بزنید**

### 4. نکات مهم:

- ✅ **OWNER_ID** باید عدد باشد: `5803428693`
- ✅ **BOT_TOKEN** باید کامل باشد
- ✅ **API_KEY** ها باید کامل باشند
- ❌ **نام متغیر** را به عنوان مقدار نگذارید

### 5. بررسی نهایی:

پس از تصحیح، در لاگ‌ها باید ببینید:
```
✅ Bot started successfully
✅ All handlers registered
✅ Ready to receive updates
```

### 6. تست:

1. `/start` - تست دستور اصلی
2. `/admin` - تست پنل مدیریتی
3. `ربات` در گروه - تست ماشین حساب

## 🚨 اگر مشکل ادامه داشت:

1. **متغیرها را دوباره بررسی کنید**
2. **پروژه را دوباره deploy کنید**
3. **لاگ‌ها را بررسی کنید**
