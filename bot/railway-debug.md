# 🐛 راهنمای Debug ربات روی Railway

## 🔍 مشکلات رایج و راه‌حل‌ها:

### 1️⃣ ربات شروع نمی‌شود:

#### مشکل: `TELEGRAM_BOT_TOKEN is not set`
```bash
# راه‌حل: بررسی متغیرهای محیطی در Railway Dashboard
# Variables > Add Variable
TELEGRAM_BOT_TOKEN=8308884100:AAEfcSUiiBKV-YIUZs8PUaV6Ik9Gh-3nvZE
```

#### مشکل: `ModuleNotFoundError`
```bash
# راه‌حل: بررسی requirements.txt
pip install -r requirements.txt
```

#### مشکل: `Permission denied`
```bash
# راه‌حل: بررسی دسترسی فایل‌ها
chmod +x railway-start.sh
```

### 2️⃣ ربات شروع می‌شود اما پاسخ نمی‌دهد:

#### مشکل: Webhook تنظیم نشده
```bash
# بررسی لاگ‌ها
railway logs

# بررسی متغیر WEBHOOK_URL
echo $WEBHOOK_URL
```

#### مشکل: Rate Limiting
```bash
# بررسی تنظیمات Rate Limit
# در config.py: RATE_LIMIT_PER_MINUTE = 30
```

### 3️⃣ خطاهای API:

#### مشکل: `API Error: 429 Too Many Requests`
```bash
# راه‌حل: کاهش تعداد درخواست‌ها
# در config.py: REQUEST_TIMEOUT = 30
```

#### مشکل: `API Error: 401 Unauthorized`
```bash
# راه‌حل: بررسی API Keys
# در Railway Variables:
TABDEAL_API_KEY=your_key_here
BRS_API_KEY=your_key_here
```

### 4️⃣ مشکلات Database:

#### مشکل: `File not found: store.json`
```bash
# راه‌حل: ایجاد فایل store.json
# فایل قبلاً ایجاد شده است
```

#### مشکل: `Permission denied: store.json`
```bash
# راه‌حل: بررسی دسترسی نوشتن
# Railway به صورت خودکار دسترسی می‌دهد
```

## 🔧 دستورات Debug:

### 📊 بررسی وضعیت:
```bash
# بررسی لاگ‌های Railway
railway logs

# بررسی متغیرهای محیطی
railway variables

# بررسی وضعیت Deploy
railway status
```

### 🔄 Restart:
```bash
# Restart ربات
railway redeploy

# Restart با لاگ‌های جدید
railway redeploy --detach
```

### 📁 بررسی فایل‌ها:
```bash
# بررسی محتویات دایرکتوری
railway run ls -la

# بررسی محتویات store.json
railway run cat store.json
```

## 🚨 هشدارهای مهم:

### ⚠️ امنیت:
- **هرگز توکن ربات را در کد قرار ندهید**
- **از متغیرهای محیطی استفاده کنید**
- **API Keys را محرمانه نگه دارید**

### ⚠️ عملکرد:
- **Rate Limiting را فعال نگه دارید**
- **لاگ‌ها را مرتب بررسی کنید**
- **Backup منظم انجام دهید**

## 📞 پشتیبانی:

### 🔗 لینک‌های مفید:
- **Railway Docs:** https://docs.railway.app/
- **Telegram Bot API:** https://core.telegram.org/bots/api
- **Python Telegram Bot:** https://python-telegram-bot.readthedocs.io/

### 📧 تماس:
- **مالک ربات:** `5803428693`
- **ادمین:** `6041119040`

---

## ✅ چک‌لیست Debug:

### 🔍 قبل از درخواست کمک:
- [ ] **لاگ‌ها را بررسی کردم**
- [ ] **متغیرهای محیطی را چک کردم**
- [ ] **مستندات را خواندم**
- [ ] **مشکل را تکرار کردم**

### 🛠️ اقدامات انجام شده:
- [ ] **Restart کردم**
- [ ] **متغیرها را بررسی کردم**
- [ ] **لاگ‌ها را خواندم**
- [ ] **مستندات را چک کردم**

---

**🎯 موفق باشید در Debug!**