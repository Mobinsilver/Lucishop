import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# ===== اطلاعات ضروری ربات =====
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "8308884100:AAEfcSUiiBKV-YIUZs8PUaV6Ik9Gh-3nvZE")
OWNER_ID = int(os.getenv("OWNER_ID", "5803428693"))
ADMIN_ID = int(os.getenv("ADMIN_ID", "6041119040"))
BOT_USERNAME = os.getenv("BOT_USERNAME", "Crypto_navasan_bot")

# ===== تنظیمات Railway =====
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
PORT = int(os.getenv("PORT", 8000))

# ===== تنظیمات محیط =====
ENVIRONMENT = os.getenv("ENVIRONMENT", "production")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
DEBUG = os.getenv("DEBUG", "false").lower() == "true"

# ===== تنظیمات اختیاری =====
MAX_USERS = int(os.getenv("MAX_USERS", 1000))
REQUEST_TIMEOUT = int(os.getenv("REQUEST_TIMEOUT", 30))

# ===== تنظیمات پیش‌فرض =====
DEFAULT_LANGUAGE = "FA"
DEFAULT_BASE_FIAT = "USD"
DEFAULT_SHOW_IRR = True
DEFAULT_DISPLAY_TOMAN = True

# ===== تنظیمات امنیتی =====
RATE_LIMIT_PER_MINUTE = 30
CAPTCHA_TIMEOUT = 300  # 5 minutes
MAX_LOGIN_ATTEMPTS = 3

# ===== تنظیمات API =====
COINGECKO_API_URL = "https://api.coingecko.com/api/v3"
EXCHANGERATE_API_URL = "https://api.exchangerate.host"
BINANCE_API_URL = "https://api.binance.com/api/v3"

# ===== تنظیمات کش =====
CACHE_TTL_SECONDS = 180  # 3 minutes
MAX_CACHE_SIZE = 1000

# ===== تنظیمات اعلان‌ها =====
ALERT_CHECK_INTERVAL = 60  # 1 minute
MAX_ALERTS_PER_USER = 10

# ===== تنظیمات پورتفوی =====
MAX_WATCHLIST_ITEMS = 50
MAX_PORTFOLIO_ITEMS = 100

# ===== تنظیمات اخبار =====
NEWS_FEED_URLS = [
    "https://cointelegraph.com/rss",
    "https://coindesk.com/arc/outboundfeeds/rss/",
    "https://www.newsbtc.com/feed/"
]
MAX_NEWS_ITEMS = 10
