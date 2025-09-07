import re
import asyncio
from typing import Optional, Tuple, Dict
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from price_service import get_crypto_price_with_provider
from fiat_service import get_fiat_rate_with_provider
from store import load_store, get_user_data
from cache import TTLCache

# ایجاد instance از cache و store
STORE = load_store()
CACHE = TTLCache()

# الگوهای regex برای تشخیص درخواست‌های محاسبه
CALCULATION_PATTERNS = [
    # الگوهای مختلف برای تشخیص درخواست‌های محاسبه
    r'(\d+(?:\.\d+)?)\s*(تتر|usdt|USDT)',
    r'(\d+(?:\.\d+)?)\s*(تون|ton|TON)',
    r'(\d+(?:\.\d+)?)\s*(بیتکوین|bitcoin|btc|BTC)',
    r'(\d+(?:\.\d+)?)\s*(اتریوم|ethereum|eth|ETH)',
    r'(\d+(?:\.\d+)?)\s*(ترون|tron|trx|TRX)',
    r'(\d+(?:\.\d+)?)\s*(دلار|dollar|usd|USD)',
    r'(\d+(?:\.\d+)?)\s*(یورو|euro|eur|EUR)',
    r'(\d+(?:\.\d+)?)\s*(پوند|pound|gbp|GBP)',
    r'(\d+(?:\.\d+)?)\s*(ین|yen|jpy|JPY)',
    r'(\d+(?:\.\d+)?)\s*(درهم|aed|AED)',
    r'(\d+(?:\.\d+)?)\s*(لیر|try|TRY)',
    r'(\d+(?:\.\d+)?)\s*(طلا|gold|GOLD)',
    r'(\d+(?:\.\d+)?)\s*(نقره|silver|SILVER)',
]

# مپینگ نام‌های فارسی به نمادهای انگلیسی
CURRENCY_MAPPING = {
    'تتر': 'USDT',
    'usdt': 'USDT',
    'USDT': 'USDT',
    'تون': 'TON',
    'ton': 'TON',
    'TON': 'TON',
    'بیتکوین': 'BTC',
    'bitcoin': 'BTC',
    'btc': 'BTC',
    'BTC': 'BTC',
    'اتریوم': 'ETH',
    'ethereum': 'ETH',
    'eth': 'ETH',
    'ETH': 'ETH',
    'ترون': 'TRX',
    'tron': 'TRX',
    'trx': 'TRX',
    'TRX': 'TRX',
    'دلار': 'USD',
    'dollar': 'USD',
    'usd': 'USD',
    'USD': 'USD',
    'یورو': 'EUR',
    'euro': 'EUR',
    'eur': 'EUR',
    'EUR': 'EUR',
    'پوند': 'GBP',
    'pound': 'GBP',
    'gbp': 'GBP',
    'GBP': 'GBP',
    'ین': 'JPY',
    'yen': 'JPY',
    'jpy': 'JPY',
    'JPY': 'JPY',
    'درهم': 'AED',
    'aed': 'AED',
    'AED': 'AED',
    'لیر': 'TRY',
    'try': 'TRY',
    'TRY': 'TRY',
    'طلا': 'GOLD',
    'gold': 'GOLD',
    'GOLD': 'GOLD',
    'نقره': 'SILVER',
    'silver': 'SILVER',
    'SILVER': 'SILVER',
}

async def get_usd_to_irr_rate() -> float:
    """دریافت نرخ دلار به ریال ایران"""
    cache_key = "fiat:USD->IRR"
    rate = CACHE.get(cache_key)
    if rate is None:
        prov = (STORE.get("providers", {}) or {}).get("fiat", "exchangerate_host")
        res = await get_fiat_rate_with_provider("IRR", prov, base="USD")
        if res:
            _, rate, _ = res
            CACHE.set(cache_key, rate, ttl_seconds=180)
        else:
            rate = 500000  # نرخ پیش‌فرض در صورت خطا
    return float(rate)

async def convert_to_toman(amount: float, currency: str) -> Optional[Tuple[float, str, float]]:
    """
    تبدیل مقدار ارز به تومان
    Returns: (toman_amount, currency_name, usd_rate) or None
    """
    try:
        currency_upper = currency.upper()
        
        # اگر ارز کریپتو است
        if currency_upper in ['BTC', 'ETH', 'USDT', 'TON', 'TRX']:
            result = await get_crypto_price_with_provider(currency_upper.lower(), "coingecko")
            if result:
                _, usd_price, _ = result
                usd_to_irr = await get_usd_to_irr_rate()
                toman_amount = (amount * usd_price * usd_to_irr) / 10  # تبدیل به تومان
                
                currency_names = {
                    'BTC': 'بیتکوین',
                    'ETH': 'اتریوم', 
                    'USDT': 'تتر',
                    'TON': 'تون',
                    'TRX': 'ترون'
                }
                
                return toman_amount, currency_names.get(currency_upper, currency_upper), usd_price
        
        # اگر ارز فیات است
        elif currency_upper in ['USD', 'EUR', 'GBP', 'JPY', 'AED', 'TRY']:
            result = await get_fiat_rate_with_provider(currency_upper, "exchangerate_host", base="USD")
            if result:
                _, usd_rate, _ = result
                usd_to_irr = await get_usd_to_irr_rate()
                toman_amount = (amount * usd_rate * usd_to_irr) / 10  # تبدیل به تومان
                
                currency_names = {
                    'USD': 'دلار آمریکا',
                    'EUR': 'یورو',
                    'GBP': 'پوند انگلیس',
                    'JPY': 'ین ژاپن',
                    'AED': 'درهم امارات',
                    'TRY': 'لیر ترکیه'
                }
                
                return toman_amount, currency_names.get(currency_upper, currency_upper), usd_rate
        
        # اگر طلا یا نقره است
        elif currency_upper in ['GOLD', 'SILVER']:
            # برای طلا و نقره از نرخ ثابت استفاده می‌کنیم
            if currency_upper == 'GOLD':
                usd_price = 2000  # قیمت تقریبی طلا به دلار
                currency_name = 'طلا'
            else:  # SILVER
                usd_price = 25  # قیمت تقریبی نقره به دلار
                currency_name = 'نقره'
            
            usd_to_irr = await get_usd_to_irr_rate()
            toman_amount = (amount * usd_price * usd_to_irr) / 10  # تبدیل به تومان
            
            return toman_amount, currency_name, usd_price
        
        return None
        
    except Exception as e:
        print(f"خطا در تبدیل ارز: {e}")
        return None

def parse_calculation_request(text: str) -> Optional[Tuple[float, str]]:
    """
    تجزیه درخواست محاسبه از متن
    Returns: (amount, currency) or None
    """
    text = text.strip()
    
    for pattern in CALCULATION_PATTERNS:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            amount = float(match.group(1))
            currency_name = match.group(2)
            currency_symbol = CURRENCY_MAPPING.get(currency_name.lower())
            
            if currency_symbol:
                return amount, currency_symbol
    
    return None

async def handle_calculation_request(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """
    مدیریت درخواست‌های محاسبه در گروه
    Returns: True if handled, False otherwise
    """
    if not update.message or not update.message.text:
        return False
    
    text = update.message.text.strip()
    
    # بررسی اینکه آیا درخواست محاسبه است
    calculation = parse_calculation_request(text)
    if not calculation:
        return False
    
    amount, currency = calculation
    
    # نمایش پیام در حال محاسبه
    loading_msg = await update.message.reply_text(
        f"⏳ در حال محاسبه {amount} {currency} به تومان..."
    )
    
    try:
        # تبدیل به تومان
        result = await convert_to_toman(amount, currency)
        
        if result:
            toman_amount, currency_name, usd_rate = result
            
            # فرمت کردن نتیجه
            if toman_amount >= 1000000:
                formatted_amount = f"{toman_amount/1000000:.2f} میلیون تومان"
            elif toman_amount >= 1000:
                formatted_amount = f"{toman_amount/1000:.2f} هزار تومان"
            else:
                formatted_amount = f"{toman_amount:.2f} تومان"
            
            # ایجاد پیام نتیجه
            result_text = f"""
💰 **محاسبه قیمت**

📊 **مقدار**: {amount:,.2f} {currency_name}
💵 **قیمت**: {formatted_amount}

📈 **نرخ فعلی**: 1 {currency} = {usd_rate:,.4f} USD
🔄 **آخرین بروزرسانی**: {asyncio.get_event_loop().time():.0f}
            """
            
            # دکمه‌های کنترلی
            keyboard = [
                [InlineKeyboardButton("🔄 محاسبه مجدد", callback_data=f"recalc:{amount}:{currency}")],
                [InlineKeyboardButton("📊 نمودار قیمت", callback_data=f"chart:{currency}")],
                [InlineKeyboardButton("🔔 تنظیم هشدار", callback_data=f"alert:{currency}")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await loading_msg.edit_text(result_text, reply_markup=reply_markup)
            
        else:
            await loading_msg.edit_text(
                f"❌ خطا در دریافت قیمت {currency}. لطفاً دوباره تلاش کنید."
            )
    
    except Exception as e:
        await loading_msg.edit_text(
            f"❌ خطا در محاسبه: {str(e)}"
        )
    
    return True

async def handle_calculator_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """مدیریت callback های ماشین حساب"""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    
    if data.startswith("recalc:"):
        # محاسبه مجدد
        parts = data.split(":")
        if len(parts) == 3:
            amount = float(parts[1])
            currency = parts[2]
            
            # نمایش پیام در حال محاسبه
            await query.edit_message_text(
                f"⏳ در حال محاسبه مجدد {amount} {currency} به تومان..."
            )
            
            # تبدیل به تومان
            result = await convert_to_toman(amount, currency)
            
            if result:
                toman_amount, currency_name, usd_rate = result
                
                # فرمت کردن نتیجه
                if toman_amount >= 1000000:
                    formatted_amount = f"{toman_amount/1000000:.2f} میلیون تومان"
                elif toman_amount >= 1000:
                    formatted_amount = f"{toman_amount/1000:.2f} هزار تومان"
                else:
                    formatted_amount = f"{toman_amount:.2f} تومان"
                
                # ایجاد پیام نتیجه
                result_text = f"""
💰 **محاسبه قیمت (بروزرسانی شده)**

📊 **مقدار**: {amount:,.2f} {currency_name}
💵 **قیمت**: {formatted_amount}

📈 **نرخ فعلی**: 1 {currency} = {usd_rate:,.4f} USD
🔄 **آخرین بروزرسانی**: {asyncio.get_event_loop().time():.0f}
                """
                
                # دکمه‌های کنترلی
                keyboard = [
                    [InlineKeyboardButton("🔄 محاسبه مجدد", callback_data=f"recalc:{amount}:{currency}")],
                    [InlineKeyboardButton("📊 نمودار قیمت", callback_data=f"chart:{currency}")],
                    [InlineKeyboardButton("🔔 تنظیم هشدار", callback_data=f"alert:{currency}")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await query.edit_message_text(result_text, reply_markup=reply_markup)
    
    elif data.startswith("chart:"):
        # نمایش نمودار
        currency = data.split(":")[1]
        await query.edit_message_text(
            f"📊 نمودار قیمت {currency} در حال آماده‌سازی است..."
        )
    
    elif data.startswith("alert:"):
        # تنظیم هشدار
        currency = data.split(":")[1]
        await query.edit_message_text(
            f"🔔 تنظیم هشدار برای {currency} در حال آماده‌سازی است..."
        )

async def send_calculator_ready_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """ارسال پیام آمادگی ماشین حساب"""
    welcome_text = """
🧮 **ماشین حساب ارز آماده است!**

💡 **نحوه استفاده:**
• برای محاسبه قیمت، پیام خود را به این صورت بنویسید:
  `10 تتر` یا `5 بیتکوین` یا `100 دلار`

📊 **ارزهای پشتیبانی شده:**
• کریپتو: بیتکوین، اتریوم، تتر، تون، ترون
• فیات: دلار، یورو، پوند، ین، درهم، لیر
• فلزات: طلا، نقره

🔄 **مثال‌ها:**
• `1 تتر` → قیمت 1 تتر به تومان
• `10 بیتکوین` → قیمت 10 بیتکوین به تومان
• `100 دلار` → قیمت 100 دلار به تومان

⚡ **ویژگی‌ها:**
• قیمت‌های لحظه‌ای
• تبدیل خودکار به تومان
• بروزرسانی خودکار نرخ‌ها
    """
    
    keyboard = [
        [InlineKeyboardButton("📊 لیست ارزها", callback_data="currency_list")],
        [InlineKeyboardButton("❓ راهنما", callback_data="calculator_help")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(welcome_text, reply_markup=reply_markup)

async def handle_calculator_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """نمایش راهنمای ماشین حساب"""
    query = update.callback_query
    await query.answer()
    
    help_text = """
❓ **راهنمای ماشین حساب**

📝 **فرمت درخواست:**
• `مقدار + نام ارز`
• مثال: `10 تتر`، `5 بیتکوین`، `100 دلار`

🔢 **مثال‌های کامل:**
• `1 تتر` → 1 تتر = X تومان
• `10 بیتکوین` → 10 بیتکوین = X تومان  
• `100 دلار` → 100 دلار = X تومان
• `50 یورو` → 50 یورو = X تومان
• `2 طلا` → 2 اونس طلا = X تومان

⚡ **نکات مهم:**
• از اعداد اعشاری استفاده کنید: `1.5 تتر`
• نام ارزها به فارسی یا انگلیسی قابل قبول است
• قیمت‌ها به صورت لحظه‌ای بروزرسانی می‌شوند
• نتیجه به تومان نمایش داده می‌شود

🔄 **دکمه‌های کنترلی:**
• 🔄 محاسبه مجدد: بروزرسانی قیمت
• 📊 نمودار: نمایش نمودار قیمت
• 🔔 هشدار: تنظیم هشدار قیمت
    """
    
    keyboard = [
        [InlineKeyboardButton("🔙 بازگشت", callback_data="back_to_calculator")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(help_text, reply_markup=reply_markup)

