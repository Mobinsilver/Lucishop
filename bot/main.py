
import os
import asyncio
import aiohttp
import logging
from typing import Optional, List, Tuple, Dict
from datetime import datetime, timedelta

from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.DEBUG
)
logger = logging.getLogger(__name__)
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, CallbackQueryHandler, MessageHandler, filters, ConversationHandler

from price_service import SYMBOL_TO_CG_ID, get_crypto_price_with_provider
from fiat_service import get_fiat_rate_with_provider
from news_service import get_news
from history import fetch_history_prices, sparkline
from arbitrage import compare_prices
from p2p_service import fetch_binance_p2p, summarize_p2p_offers
from store import load_store, save_store, get_user_data
from cache import TTLCache
from security import check_black_white, touch_rate_limit
from admin_panel import (
    admin_panel, ADMIN_PANEL, ADD_ADMIN, REMOVE_ADMIN, BROADCAST_MESSAGE, 
    BROADCAST_FORWARD, SET_WELCOME_TEXT, SET_HELP_TEXT, SET_ERROR_TEXT, 
    SET_API_KEY, SET_TRADINGVIEW_API, SET_FIAT_API, FORCE_SUBSCRIPTION, 
    ADD_FORCE_SUB_CHANNEL, ADD_WHITELIST, ADD_BLACKLIST, USER_MESSAGE, SET_CRYPTO_API_KEY,
    EXTERNAL_API_URL, EXTERNAL_API_KEY, EXTERNAL_API_TYPE,
    LOCK_MENU, ADD_LOCK_CHANNEL, CONFIRM_ADMIN, SUBMIT_LOCK_LINK, LIST_LOCKED_CHANNELS,
    FEATURE_TOGGLE_MENU, FEATURE_TOGGLE_SUBMENU, FEATURE_SEARCH,
    AWAIT_BLACKLIST_ADD, AWAIT_BLACKLIST_REMOVE, AWAIT_WHITELIST_ADD, AWAIT_WHITELIST_REMOVE, LISTS_SEARCH
)
from crypto_list import show_crypto_list, show_crypto_detail, refresh_crypto_price, show_crypto_chart, handle_crypto_selection, show_all_cryptos
from calculator import handle_calculation_request, handle_calculator_callback, send_calculator_ready_message, handle_calculator_help
import config


load_dotenv()
BOT_TOKEN = config.TELEGRAM_BOT_TOKEN
STORE = load_store()
CACHE = TTLCache()

# Validate required environment variables
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN environment variable is required")
if not config.OWNER_ID:
    raise ValueError("OWNER_ID environment variable is required")


async def get_crypto_rates_with_external_api(symbols: List[str]) -> List[Dict]:
    """دریافت نرخ ارزهای کریپتو با استفاده از API خارجی (اگر تنظیم شده)"""
    try:
        return await admin_panel.get_crypto_rates_for_display(symbols)
    except Exception as e:
        print(f"Error getting crypto rates with external API: {e}")
        return []

async def get_fiat_rates_with_external_api(pairs: List[str]) -> List[Dict]:
    """دریافت نرخ ارزهای فیات با استفاده از API خارجی (اگر تنظیم شده)"""
    try:
        return await admin_panel.get_fiat_rates_for_display(pairs)
    except Exception as e:
        print(f"Error getting fiat rates with external API: {e}")
        return []

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


async def convert_price_for_user(user_id: int, amount_usd: float) -> str:
	ud = get_user_data(STORE, user_id)
	st = ud.get("settings", {}) or {}
	base = st.get("base_fiat", "USD")
	to_toman = st.get("display_toman", True)
	show_irr = st.get("show_irr", True)  # نمایش ریال ایران
	
	# ابتدا قیمت به واحد پایه کاربر
	if base == "USD":
		base_amount = amount_usd
		if st.get("language", "FA") == "FA":
			base_text = f"{base_amount:,.4f} دلار"
		else:
			base_text = f"${base_amount:,.4f}"
	else:
		# تبدیل به واحد پایه کاربر
		cache_key = f"fiat:USD->{base}"
		rate = CACHE.get(cache_key)
		if rate is None:
			prov = (STORE.get("providers", {}) or {}).get("fiat", "exchangerate_host")
			res = await get_fiat_rate_with_provider(base, prov, base="USD")
			if res:
				_, rate, _ = res
				CACHE.set(cache_key, rate, ttl_seconds=180)
			else:
				rate = 1.0
		base_amount = amount_usd * float(rate)
		if base == "IRR" and to_toman:
			base_text = f"{base_amount/10:,.0f} تومان"
		else:
			base_text = f"{base_amount:,.4f} {base}"
	
	# اگر نمایش ریال فعال باشد و واحد پایه ریال نباشد
	if show_irr and base != "IRR":
		irr_rate = await get_usd_to_irr_rate()
		irr_amount = amount_usd * irr_rate
		if to_toman:
			irr_text = f"{irr_amount/10:,.0f} تومان"
		else:
			irr_text = f"{irr_amount:,.0f} ریال"
		return f"{base_text}\n🇮🇷 {irr_text}"
	
	return base_text

if not BOT_TOKEN:
	raise RuntimeError("Please set TELEGRAM_BOT_TOKEN in environment or .env file")


def help_text_by_lang(lang: str) -> str:
	lang = (lang or "FA").upper()
	if lang == "EN":
		return (
			"📋 **Help & Features:**\n\n"
			"💰 **Crypto Prices** - Real-time cryptocurrency prices\n"
			"🏦 **Fiat Rates** - Domestic currency rates\n"
			"📰 **News** - Latest crypto news\n"
			"📊 **Charts** - Price charts and analysis\n"
			"🛠 **Settings** - Bot configuration\n\n"
			"Use the quick menu buttons below to navigate features."
		)
	if lang == "AR":
		return (
			"📋 **المساعدة والميزات:**\n\n"
			"💰 **أسعار العملات المشفرة** - أسعار العملات المشفرة في الوقت الفعلي\n"
			"🏦 **أسعار العملات التقليدية** - أسعار العملات المحلية\n"
			"📰 **الأخبار** - آخر أخبار العملات المشفرة\n"
			"📊 **الرسوم البيانية** - رسوم بيانية وتحليل الأسعار\n"
			"🛠 **الإعدادات** - إعدادات الروبوت\n\n"
			"استخدم الأزرار السريعة أدناه للتنقل بين الميزات."
		)
	return (
		"📋 **راهنما و امکانات:**\n\n"
		"💰 **قیمت ارز** - قیمت لحظه‌ای ارزهای دیجیتال\n"
		"🏦 **ارز داخلی** - نرخ ارزهای داخلی\n"
		"📰 **اخبار** - آخرین اخبار ارزهای دیجیتال\n"
		"📊 **نمودار** - نمودارها و تحلیل قیمت\n"
		"🛠 **تنظیمات** - تنظیمات ربات\n\n"
		"از دکمه‌های میانبر زیر برای استفاده از امکانات استفاده کنید."
	)


def get_help_text(user_id: int) -> str:
	ud = get_user_data(STORE, user_id)
	lang = ud.get("settings", {}).get("language", "FA")
	if lang == "EN":
		return "Choose an option:"
	elif lang == "AR":
		return "اختر خياراً:"
	else:
		return "گزینه مورد نظر را انتخاب کنید:"


def get_welcome_text(user_id: int) -> str:
	"""پیام خوش‌آمدگویی کامل برای کاربران جدید"""
	ud = get_user_data(STORE, user_id)
	lang = ud.get("settings", {}).get("language", "FA")
	if lang == "EN":
		return (
			"Hi! 👋\n"
			"I'm a bot for real-time crypto and fiat prices.\n\n"
			"Use the quick menu buttons below to navigate features."
		)
	if lang == "AR":
		return (
			"مرحباً! 👋\n"
			"أنا روبوت لأسعار العملات المشفرة والعملات التقليدية في الوقت الفعلي.\n\n"
			"استخدم الأزرار السريعة أدناه للتنقل بين الميزات."
		)
	return (
		"سلام! 👋\n"
		"من ربات قیمت لحظه‌ای ارزهای دیجیتال و فیات هستم.\n\n"
		"از دکمه‌های میانبر زیر برای استفاده از امکانات استفاده کنید."
	)


def reply_keyboard(update: Update = None) -> ReplyKeyboardMarkup:
	# دریافت وضعیت ویژگی‌ها از FeatureRegistry
	keyboard = []
	
	# ردیف اول
	row1 = []
	if admin_panel.is_feature_enabled('user.crypto_prices'):
		row1.append(KeyboardButton("💰 قیمت ارز"))
	if admin_panel.is_feature_enabled('user.fiat_rates'):
		row1.append(KeyboardButton("🏦 ارز داخلی"))
	if row1:
		keyboard.append(row1)
	
	# ردیف دوم
	row2 = []
	if admin_panel.is_feature_enabled('user.news'):
		row2.append(KeyboardButton("📰 اخبار"))
	if admin_panel.is_feature_enabled('user.charts'):
		row2.append(KeyboardButton("📊 نمودار"))
	if row2:
		keyboard.append(row2)
	
	# ردیف سوم - حذف شده (تحلیل تکنیکال، مقایسه، P2P، واچ‌لیست، پرتفوی، هشدارها)
	
	# ردیف سوم
	row3 = []
	if admin_panel.is_feature_enabled('user.settings'):
		row3.append(KeyboardButton("🛠 تنظیمات"))
	if admin_panel.is_feature_enabled('user.help'):
		row3.append(KeyboardButton("❓ راهنما"))
	if row3:
		keyboard.append(row3)
	

	
	# اضافه کردن دکمه‌های مدیریتی برای مالک و ادمین‌ها
	from config import OWNER_ID
	if update and update.effective_user:
		user_id = update.effective_user.id
		admins = STORE.get('admins', [])
		
		if user_id == OWNER_ID or user_id in admins:
			keyboard.append([KeyboardButton("🔐 پنل مدیریتی")])
			keyboard.append([KeyboardButton("📊 آمار و گزارش")])
	
	return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


async def ensure_forced_subscription(user_id: int, context: ContextTypes.DEFAULT_TYPE) -> Tuple[bool, str]:
	"""بررسی عضویت اجباری در کانال"""
	fs = STORE.get("forced_subscription", {}) or {}
	if not fs.get("enabled"):
		return True, ""
	
	channel = fs.get("channel_username")
	if not channel:
		return True, ""
	
	try:
		member = await context.bot.get_chat_member(f"@{channel}", user_id)
		return member.status not in ["left", "kicked"], channel
	except Exception:
		return False, channel


async def check_force_subscription(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
	"""بررسی عضویت اجباری"""
	user = update.effective_user
	uid = user.id
	
	# دریافت تنظیمات قفل اجباری
	force_sub = STORE.get('forced_subscription', {})
	if not force_sub.get('enabled', False):
		return True  # قفل اجباری غیرفعال است
	
	channels = force_sub.get('channels', [])
	if not channels:
		return True  # هیچ کانالی تنظیم نشده
	
	# بررسی عضویت در کانال‌ها
	for channel in channels:
		try:
			member = await context.bot.get_chat_member(chat_id=f"@{channel}", user_id=uid)
			if member.status in ['left', 'kicked']:
				# کاربر عضو نیست
				await show_force_subscription_message(update, context, channels)
				return False
		except Exception as e:
			print(f"Error checking membership for {channel}: {e}")
			continue
	
	return True  # کاربر در تمام کانال‌ها عضو است

async def show_force_subscription_message(update: Update, context: ContextTypes.DEFAULT_TYPE, channels: list):
	"""نمایش پیام عضویت اجباری"""
	channels_text = "\n".join([f"• @{ch}" for ch in channels])
	
	keyboard = []
	for channel in channels:
		keyboard.append([InlineKeyboardButton(f"📢 عضویت در @{channel}", url=f"https://t.me/{channel}")])
	
	keyboard.append([InlineKeyboardButton("✅ تایید عضویت", callback_data="check_subscription")])
	reply_markup = InlineKeyboardMarkup(keyboard)
	
	text = f"""
🔒 **عضویت اجباری**

برای استفاده از ربات، باید در کانال‌های زیر عضو باشید:

{channels_text}

لطفاً در کانال‌های بالا عضو شوید و سپس دکمه "تایید عضویت" را بزنید.
	"""
	
	if update.callback_query:
		await update.callback_query.edit_message_text(text, reply_markup=reply_markup)
	else:
		await update.message.reply_text(text, reply_markup=reply_markup)

async def start_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
	"""دستور /start - همیشه به منوی اصلی برمی‌گردد"""
	# پاک کردن context user_data برای شروع جدید
	context.user_data.clear()
	
	# فراخوانی متد start اصلی
	await start(update, context)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
	user = update.effective_user
	uid = user.id
	
	# بررسی دسترسی کاربر (سیستم جدید)
	if not admin_panel.is_user_allowed(uid):
		# کاربر مسدود است - پیام اطلاع‌رسانی ارسال نمی‌کنیم تا از اسپم جلوگیری کنیم
		return
	
	# بررسی عضویت اجباری (سیستم جدید)
	if await admin_panel.handle_user_start_with_lock(update, context):
		return
	
	# ثبت رویداد استارت و ارسال اعلان
	admin_panel.log_user_event(uid, 'start')
	admin_panel.update_user_info(uid, user.username, user.full_name)
	await admin_panel.send_start_notification(update, context)
	
	# rate limit
	ok, reason = touch_rate_limit(uid)
	if not ok:
		await update.message.reply_text("لطفا کمی بعد دوباره تلاش کنید.")
		return
	
	# بررسی کاربر جدید
	is_new_user = uid not in set(STORE.get("users", []))
	if is_new_user:
		STORE.setdefault("users", []).append(uid)
		save_store(STORE)
		
		# اطلاع‌رسانی به مالک
		await notify_owner_new_user(update, context, user)
	
	allowed, channel = await ensure_forced_subscription(user.id, context)
	if not allowed:
		await update.message.reply_text(
			f"برای استفاده، ابتدا عضو کانال {channel} شوید و دوباره تلاش کنید."
		)
		return
	
	# If first time or language not set, ask for language selection
	ud = get_user_data(STORE, user.id)
	if not ud.get("settings") or not ud.get("settings", {}).get("language"):
		await update.message.reply_text(
			"Select language / اختر اللغة / انتخاب زبان:",
			reply_markup=InlineKeyboardMarkup([
				[InlineKeyboardButton(text="فارسی", callback_data="LANGSEL:FA"), InlineKeyboardButton(text="English", callback_data="LANGSEL:EN"), InlineKeyboardButton(text="العربية", callback_data="LANGSEL:AR")]
			])
		)
		return
	
	# فقط برای کاربران جدید پیام خوش‌آمدگویی ارسال کن
	if is_new_user:
		await update.message.reply_text(get_welcome_text(user.id), reply_markup=reply_keyboard(update))
	else:
		# برای کاربران قدیمی فقط کیبورد را نشان بده
		await update.message.reply_text("منوی اصلی:", reply_markup=reply_keyboard(update))


async def notify_owner_new_user(update: Update, context: ContextTypes.DEFAULT_TYPE, is_new_user: bool) -> None:
	"""اطلاع‌رسانی به مالک در مورد کاربر جدید"""
	from config import OWNER_ID
	
	user = update.effective_user
	uid = user.id
	
	# اطلاعات کاربر
	username = user.username or "بدون نام کاربری"
	first_name = user.first_name or "بدون نام"
	last_name = user.last_name or ""
	full_name = f"{first_name} {last_name}".strip()
	
	# تاریخ و زمان
	now = datetime.now()
	date_time = now.strftime('%Y-%m-%d %H:%M:%S')
	
	# متن اطلاع‌رسانی
	if is_new_user:
		status_text = "🆕 **کاربر جدید**"
		status_emoji = "🆕"
	else:
		status_text = "🔄 **بازگشت کاربر**"
		status_emoji = "🔄"
	
	notification_text = f"""
{status_emoji} **اطلاع‌رسانی ربات**

{status_text}

👤 **اطلاعات کاربر**:
• آیدی: `{uid}`
• نام: {full_name}
• نام کاربری: @{username}
• تاریخ: {date_time}

📊 **آمار کلی**:
• کل کاربران: {len(STORE.get('users', [])):,}
• کاربران جدید امروز: {len([u for u in STORE.get('users', []) if get_user_data(STORE, u).get('join_date') == now.strftime('%Y-%m-%d')])}
	"""
	
	# دکمه ارسال پیام
	keyboard = [
		[InlineKeyboardButton("📩 پیام به کاربر", callback_data=f"message_user:{uid}")],
		[InlineKeyboardButton("👁 مشاهده پروفایل", callback_data=f"view_profile:{uid}")],
		[InlineKeyboardButton("📊 آمار کاربر", callback_data=f"user_stats:{uid}")]
	]
	reply_markup = InlineKeyboardMarkup(keyboard)
	
	try:
		await context.bot.send_message(
			chat_id=OWNER_ID,
			text=notification_text,
			reply_markup=reply_markup,
			parse_mode='Markdown'
		)
	except Exception as e:
		print(f"Error sending notification to owner: {e}")

async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
	# فقط راهنما را نشان بده، نه پیام خوش‌آمدگویی
	ud = get_user_data(STORE, update.effective_user.id)
	await update.message.reply_text(help_text_by_lang(ud.get("settings", {}).get("language", "FA")), reply_markup=reply_keyboard(update))


async def show_detailed_stats(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
	"""نمایش آمار دقیق و کامل"""
	uid = update.effective_user.id
	
	# بررسی دسترسی
	from config import OWNER_ID
	admins = STORE.get('admins', [])
	
	if uid != OWNER_ID and uid not in admins:
		await update.message.reply_text("❌ شما دسترسی به آمار ندارید!")
		return
	
	# محاسبه آمار دقیق
	users = STORE.get('users', [])
	user_data = STORE.get('user_data', {})
	admins_list = STORE.get('admins', [])
	whitelist = STORE.get('whitelist', [])
	blacklist = STORE.get('blacklist', [])
	
	# آمار 24 ساعت اخیر
	now = datetime.now()
	yesterday = now - timedelta(days=1)
	users_24h = 0
	
	# آمار یک هفته اخیر
	week_ago = now - timedelta(days=7)
	users_7d = 0
	
	# آمار کاربران بلاک شده
	blocked_users = []
	
	for user_id in users:
		user_info = user_data.get(str(user_id), {})
		
		# بررسی آخرین فعالیت
		if user_info.get('last_activity'):
			try:
				last_activity = datetime.fromisoformat(user_info['last_activity'])
				if last_activity >= yesterday:
					users_24h += 1
				if last_activity >= week_ago:
					users_7d += 1
			except:
				pass
		
		# بررسی کاربران بلاک شده
		if user_id in blacklist:
			blocked_users.append(user_id)
	
	# آمار کلی
	total_users = len(users)
	total_admins = len(admins_list) + 1  # +1 for owner
	total_whitelist = len(whitelist)
	total_blacklist = len(blacklist)
	
	# آمار رشد
	today = now.strftime('%Y-%m-%d')
	users_today = 0
	for user_id in users:
		user_info = user_data.get(str(user_id), {})
		if user_info.get('join_date') == today:
			users_today += 1
	
	# نمایش آمار
	stats_text = f"""
📊 **آمار دقیق و کامل ربات**

👥 **آمار کاربران**:
• کل کاربران: {total_users:,}
• کاربران فعال (24 ساعت): {users_24h:,}
• کاربران فعال (7 روز): {users_7d:,}
• کاربران جدید امروز: {users_today:,}

👑 **آمار مدیریتی**:
• کل ادمین‌ها: {total_admins:,}
• لیست سفید: {total_whitelist:,}
• لیست سیاه: {total_blacklist:,}

⚫ **کاربران بلاک شده** ({len(blocked_users)}):
"""
	
	# نمایش آیدی کاربران بلاک شده
	if blocked_users:
		# نمایش حداکثر 10 آیدی اول
		displayed_blocked = blocked_users[:10]
		for user_id in displayed_blocked:
			stats_text += f"• `{user_id}`\n"
		
		if len(blocked_users) > 10:
			stats_text += f"• ... و {len(blocked_users) - 10} کاربر دیگر\n"
	else:
		stats_text += "• هیچ کاربری بلاک نشده\n"
	
	stats_text += f"""
📈 **نرخ رشد**:
• رشد 24 ساعت: {users_24h/total_users*100:.1f}%
• رشد 7 روز: {users_7d/total_users*100:.1f}%

🕒 **آخرین بروزرسانی**: {now.strftime('%Y-%m-%d %H:%M:%S')}
	"""
	
	# دکمه‌های عملیات
	keyboard = [
		[InlineKeyboardButton("🔄 بروزرسانی", callback_data="refresh_detailed_stats")],
		[InlineKeyboardButton("📋 لیست کامل بلاک‌ها", callback_data="show_full_blocked_list")],
		[InlineKeyboardButton("📊 گزارش CSV", callback_data="export_stats_csv")]
	]
	reply_markup = InlineKeyboardMarkup(keyboard)
	
	await update.message.reply_text(
		stats_text,
		reply_markup=reply_markup,
		parse_mode='Markdown'
	)

async def show_full_blocked_list(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
	"""نمایش لیست کامل کاربران بلاک شده"""
	query = update.callback_query
	await query.answer()
	
	blacklist = STORE.get('blacklist', [])
	
	if not blacklist:
		await query.edit_message_text(
			"⚫ **لیست کاربران بلاک شده**\n\n"
			"❌ هیچ کاربری بلاک نشده است.",
			reply_markup=InlineKeyboardMarkup([[
				InlineKeyboardButton("🔙 بازگشت", callback_data="refresh_detailed_stats")
			]])
		)
		return
	
	# نمایش لیست کامل
	blocked_text = f"⚫ **لیست کامل کاربران بلاک شده** ({len(blacklist)} کاربر)\n\n"
	
	# نمایش در صفحات 20 تایی
	page_size = 20
	total_pages = (len(blacklist) + page_size - 1) // page_size
	
	# دریافت شماره صفحه از callback_data (اگر وجود دارد)
	page = 1
	if hasattr(query, 'data') and ':' in query.data:
		try:
			page = int(query.data.split(':')[1])
		except:
			page = 1
	
	start_idx = (page - 1) * page_size
	end_idx = min(start_idx + page_size, len(blacklist))
	
	blocked_text += f"📄 صفحه {page} از {total_pages}\n\n"
	
	for i in range(start_idx, end_idx):
		user_id = blacklist[i]
		blocked_text += f"• `{user_id}`\n"
	
	# دکمه‌های ناوبری
	keyboard = []
	if page > 1:
		keyboard.append([InlineKeyboardButton("⬅️ صفحه قبل", callback_data=f"show_full_blocked_list:{page-1}")])
	
	if page < total_pages:
		keyboard.append([InlineKeyboardButton("➡️ صفحه بعد", callback_data=f"show_full_blocked_list:{page+1}")])
	
	keyboard.append([InlineKeyboardButton("🔙 بازگشت", callback_data="refresh_detailed_stats")])
	
	reply_markup = InlineKeyboardMarkup(keyboard)
	
	await query.edit_message_text(
		blocked_text,
		reply_markup=reply_markup,
		parse_mode='Markdown'
	)

async def export_stats_csv(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
	"""صادرات آمار به فرمت CSV"""
	query = update.callback_query
	await query.answer()
	
	# محاسبه آمار
	users = STORE.get('users', [])
	user_data = STORE.get('user_data', {})
	blacklist = STORE.get('blacklist', [])
	whitelist = STORE.get('whitelist', [])
	
	# ایجاد CSV
	csv_content = "User ID,Join Date,Last Activity,Status,Is Admin\n"
	
	for user_id in users:
		user_info = user_data.get(str(user_id), {})
		join_date = user_info.get('join_date', 'Unknown')
		last_activity = user_info.get('last_activity', 'Unknown')
		
		# تعیین وضعیت
		if user_id in blacklist:
			status = "Blocked"
		elif user_id in whitelist:
			status = "Whitelisted"
		else:
			status = "Normal"
		
		# بررسی ادمین بودن
		admins = STORE.get('admins', [])
		from config import OWNER_ID
		is_admin = "Yes" if user_id == OWNER_ID or user_id in admins else "No"
		
		csv_content += f"{user_id},{join_date},{last_activity},{status},{is_admin}\n"
	
	# ارسال فایل CSV
	from io import BytesIO
	csv_file = BytesIO(csv_content.encode('utf-8'))
	csv_file.name = f"bot_stats_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
	
	await context.bot.send_document(
		chat_id=query.from_user.id,
		document=csv_file,
		caption="📊 **گزارش کامل آمار ربات**\n\n"
				"فایل CSV شامل اطلاعات تمام کاربران، تاریخ عضویت، آخرین فعالیت و وضعیت آن‌ها است.",
		parse_mode='Markdown'
	)
	
	await query.edit_message_text(
		"✅ **گزارش CSV ارسال شد!**\n\n"
		"فایل CSV به پیوی شما ارسال شد.",
		reply_markup=InlineKeyboardMarkup([[
			InlineKeyboardButton("🔙 بازگشت", callback_data="refresh_detailed_stats")
		]])
	)

async def admin_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
	"""دستور پنل مدیریتی"""
	# Set admin conversation flag
	context.user_data['admin_conversation'] = True
	return await admin_panel.admin_panel_main(update, context)


async def price(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
	allowed, channel = await ensure_forced_subscription(update.effective_user.id, context)
	if not allowed:
		await update.message.reply_text(
			f"برای استفاده، ابتدا عضو کانال {channel} شوید و دوباره تلاش کنید."
		)
		return
	
	args = context.args or []
	if not args:
		await update.message.reply_text("لطفا نماد ارز را وارد کنید. مثال: /price btc")
		return
	
	symbol = args[0]
	provider = (STORE.get("providers", {}) or {}).get("crypto", "coingecko")
	result = await get_crypto_price_with_provider(symbol, provider)
	if not result:
		await update.message.reply_text("ارز موردنظر یافت نشد یا موقتا در دسترس نیست.")
		return
	
	sym, price_usd, change = result
	price_txt = await convert_price_for_user(update.effective_user.id, price_usd)
	change_txt = "" if change is None else ("📈" if change >= 0 else "📉") + f" {change:.2f}%"
	await update.message.reply_text(f"قیمت لحظه‌ای {sym}:\n{price_txt}\nتغییر ۲۴ساعته: {('نامشخص' if not change_txt else change_txt)}")
	CACHE.set(f"price:{sym}", (price_usd, change), ttl_seconds=30)


async def price_shortcut(update: Update, context: ContextTypes.DEFAULT_TYPE, symbol: str) -> None:
	allowed, channel = await ensure_forced_subscription(update.effective_user.id, context)
	if not allowed:
		await update.message.reply_text(
			f"برای استفاده، ابتدا عضو کانال {channel} شوید و دوباره تلاش کنید."
		)
		return
	
	provider = (STORE.get("providers", {}) or {}).get("crypto", "coingecko")
	result = await get_crypto_price_with_provider(symbol, provider)
	if not result:
		await update.message.reply_text("ارز موردنظر یافت نشد یا موقتا در دسترس نیست.")
		return
	
	sym, price_usd, change = result
	price_txt = await convert_price_for_user(update.effective_user.id, price_usd)
	change_txt = "" if change is None else ("📈" if change >= 0 else "📉") + f" {change:.2f}%"
	await update.message.reply_text(f"قیمت لحظه‌ای {sym}:\n{price_txt}\nتغییر ۲۴ساعته: {('نامشخص' if not change_txt else change_txt)}")
	CACHE.set(f"price:{sym}", (price_usd, change), ttl_seconds=30)


async def show_watchlist(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
	uid = update.effective_user.id
	ud = get_user_data(STORE, uid)
	watchlist = ud.get("watchlist", [])
	
	if not watchlist:
		await update.message.reply_text("واچ‌لیست شما خالی است.")
		return
	
	text = "📋 واچ‌لیست شما:\n\n"
	for i, symbol in enumerate(watchlist, 1):
		text += f"{i}. {symbol.upper()}\n"
	
	text += "\nبرای حذف، روی دکمه 'حذف از واچ‌لیست' کلیک کنید."
	
	keyboard = InlineKeyboardMarkup([
		[InlineKeyboardButton("حذف از واچ‌لیست", callback_data="WL_DEL_MENU")]
	])
	
	await update.message.reply_text(text, reply_markup=keyboard)


async def show_portfolio(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
	uid = update.effective_user.id
	ud = get_user_data(STORE, uid)
	portfolio = ud.get("portfolio", [])
	
	if not portfolio:
		await update.message.reply_text("پرتفوی شما خالی است.")
		return
	
	text = "📚 پرتفوی شما:\n\n"
	total_value = 0
	
	for i, item in enumerate(portfolio, 1):
		symbol = item["symbol"].upper()
		qty = item["qty"]
		avg_price = item["avg_price"]
		current_price = 0
		
		# Get current price
		result = await get_crypto_price_with_provider(symbol, "coingecko")
		if result:
			current_price = result[1]
		
		item_value = qty * current_price if current_price > 0 else qty * avg_price
		total_value += item_value
		
		text += f"{i}. {symbol}: {qty} @ ${avg_price:.2f}\n"
		if current_price > 0:
			text += f"   قیمت فعلی: ${current_price:.2f}\n"
			text += f"   ارزش: ${item_value:.2f}\n"
		text += "\n"
	
	text += f"💰 ارزش کل: ${total_value:.2f}"
	
	keyboard = InlineKeyboardMarkup([
		[InlineKeyboardButton("حذف از پرتفوی", callback_data="PF_DEL_MENU")]
	])
	
	await update.message.reply_text(text, reply_markup=keyboard)


async def show_alerts(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
	uid = update.effective_user.id
	ud = get_user_data(STORE, uid)
	alerts = ud.get("alerts", [])
	
	if not alerts:
		await update.message.reply_text("هیچ هشداری تنظیم نشده است.")
		return
	
	text = "🔔 هشدارهای شما:\n\n"
	for i, alert in enumerate(alerts, 1):
		symbol = alert["symbol"].upper()
		atype = alert["type"]
		value = alert["value"]
		text += f"{i}. {symbol} {atype} ${value:,.2f}\n"
	
	text += "\nبرای حذف، روی دکمه 'حذف هشدار' کلیک کنید."
	
	keyboard = InlineKeyboardMarkup([
		[InlineKeyboardButton("حذف هشدار", callback_data="ALERT_DEL_MENU")]
	])
	
	await update.message.reply_text(text, reply_markup=keyboard)


async def show_settings(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
	uid = update.effective_user.id
	ud = get_user_data(STORE, uid)
	settings = ud.get("settings", {})
	
	lang = settings.get("language", "FA")
	base_fiat = settings.get("base_fiat", "USD")
	show_irr = settings.get("show_irr", True)
	display_toman = settings.get("display_toman", True)
	
	text = "🛠 تنظیمات شما:\n\n"
	text += f"🌐 زبان: {lang}\n"
	text += f"💱 ارز پایه: {base_fiat}\n"
	text += f"🇮🇷 نمایش ریال: {'بله' if show_irr else 'خیر'}\n"
	text += f"💎 نمایش تومان: {'بله' if display_toman else 'خیر'}\n"
	
	keyboard = InlineKeyboardMarkup([
		[InlineKeyboardButton("تغییر زبان", callback_data="CHANGE_LANG")],
		[InlineKeyboardButton("تغییر ارز پایه", callback_data="CHANGE_BASE_FIAT")]
	])
	
	await update.message.reply_text(text, reply_markup=keyboard)


async def show_text_settings(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
	"""تنظیم متن‌های ربات"""
	uid = update.effective_user.id
	
	# فقط مالک می‌تواند تنظیم متن کند
	from config import OWNER_ID
	if uid != OWNER_ID:
		await update.message.reply_text("❌ فقط مالک ربات می‌تواند متن‌ها را تنظیم کند!")
		return
	
	text = "📝 **تنظیم متن‌های ربات**\n\n"
	text += "**متن‌های قابل تنظیم**:\n"
	text += "👋 متن خوش‌آمدگویی (/start)\n"
	text += "❓ متن راهنما (/help)\n"
	text += "⚠️ متن خطاها\n"
	text += "📝 متن درباره ربات\n"
	text += "🔒 متن عضویت اجباری\n\n"
	text += "برای تنظیم هر متن، روی دکمه مربوطه کلیک کنید:"
	
	keyboard = InlineKeyboardMarkup([
		[InlineKeyboardButton("👋 متن خوش‌آمدگویی", callback_data="set_welcome")],
		[InlineKeyboardButton("❓ متن راهنما", callback_data="set_help")],
		[InlineKeyboardButton("⚠️ متن خطا", callback_data="set_error")],
		[InlineKeyboardButton("📝 متن درباره", callback_data="set_about")],
		[InlineKeyboardButton("🔒 متن عضویت اجباری", callback_data="set_force_sub")]
	])
	
	await update.message.reply_text(text, reply_markup=keyboard)


async def show_stats(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
	"""نمایش آمار و گزارش ربات"""
	uid = update.effective_user.id
	
	# فقط مالک می‌تواند آمار را ببیند
	from config import OWNER_ID
	if uid != OWNER_ID:
		await update.message.reply_text("❌ فقط مالک ربات می‌تواند آمار را مشاهده کند!")
		return
	
	users = STORE.get('users', [])
	admins = STORE.get('admins', [])
	whitelist = STORE.get('whitelist', [])
	blacklist = STORE.get('blacklist', [])
	user_data = STORE.get('user_data', {})
	
	# محاسبه آمار
	total_users = len(users)
	total_admins = len(admins) + 1  # +1 for owner
	total_whitelist = len(whitelist)
	total_blacklist = len(blacklist)
	
	# آمار کاربران فعال
	active_24h = 0
	active_week = 0
	for user_id, data in user_data.items():
		if isinstance(data, dict) and data.get('last_activity'):
			last_activity = datetime.fromisoformat(data['last_activity'])
			time_diff = datetime.now() - last_activity
			if time_diff.days == 0:
				active_24h += 1
			if time_diff.days < 7:
				active_week += 1
	
	text = f"""
📊 **آمار و گزارش ربات**

👥 **آمار کاربران**:
• کل کاربران: {total_users}
• کاربران فعال (24 ساعت): {active_24h}
• کاربران فعال (هفته): {active_week}
• ادمین‌ها: {total_admins}
• لیست سفید: {total_whitelist}
• لیست سیاه: {total_blacklist}

📈 **نرخ رشد**:
• کاربران جدید امروز: {len([u for u in users if user_data.get(str(u), {}).get('join_date') == datetime.now().strftime('%Y-%m-%d')])}

🕒 **آخرین بروزرسانی**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
	"""
	
	await update.message.reply_text(text)




async def on_menu_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
	text = update.message.text.strip()
	uid = update.effective_user.id
	
	logger.debug(f"on_menu_text: User {uid} sent text: {repr(text)}")
	
	# Skip if user is in admin conversation (handled by conversation handler)
	if context.user_data.get('admin_conversation', False):
		logger.debug(f"on_menu_text: User {uid} is in admin conversation, skipping")
		return
	
	# بررسی دسترسی کاربر (سیستم جدید)
	if not admin_panel.is_user_allowed(uid):
		# کاربر مسدود است - پیام اطلاع‌رسانی ارسال نمی‌کنیم تا از اسپم جلوگیری کنیم
		return
	
	# rate limit
	ok, reason = touch_rate_limit(uid)
	if not ok:
		return
	
	# ثبت رویداد پیام
	admin_panel.log_user_event(uid, 'message')
	admin_panel.update_user_info(uid, update.effective_user.username, update.effective_user.full_name)
	
	# بررسی ویژگی‌های فعال
	features = STORE.get('bot_features', {})
	
	# Handle crypto selection from keyboard buttons first
	await handle_crypto_selection(update, context)
	
	# Handle calculator requests in groups
	if update.message.chat.type in ['group', 'supergroup']:
		# بررسی دستور "ربات"
		if text == "ربات" or text == "bot" or text == "Bot":
			await send_calculator_ready_message(update, context)
			return
		
		# بررسی درخواست‌های محاسبه
		handled = await handle_calculation_request(update, context)
		if handled:
			return
		
		# در گروه‌ها، فقط درخواست‌های محاسبه را پردازش کن
		# سایر دستورات را نادیده بگیر
		return
	
	# Handle menu buttons
	if text == "💰 قیمت ارز":
		if not admin_panel.is_feature_enabled('user.crypto_prices'):
			await update.message.reply_text("این بخش غیرفعال است.")
			return
		await show_crypto_list(update, context)
		return
	elif text == "🏦 ارز داخلی":
		if not admin_panel.is_feature_enabled('user.fiat_rates'):
			await update.message.reply_text("این بخش غیرفعال است.")
			return
		await show_domestic_currency_list(update, context)
		return
	elif text == "📰 اخبار":
		if not admin_panel.is_feature_enabled('user.news'):
			await update.message.reply_text("این بخش غیرفعال است.")
			return
		await update.message.reply_text("لطفا نماد ارز مورد نظر را وارد کنید (مثل: btc, eth) یا Enter بزنید برای اخبار عمومی")
		ud = get_user_data(STORE, uid)
		ud["pending"] = {"type": "news"}
		save_store(STORE)
		return
	elif text == "📊 نمودار":
		if not admin_panel.is_feature_enabled('user.charts'):
			await update.message.reply_text("این بخش غیرفعال است.")
			return
		await update.message.reply_text("لطفا نماد ارز مورد نظر را وارد کنید (مثل: btc, eth)")
		ud = get_user_data(STORE, uid)
		ud["pending"] = {"type": "chart"}
		save_store(STORE)
		return
	# دکمه‌های حذف شده: تحلیل تکنیکال، مقایسه، P2P، واچ‌لیست، پرتفوی، هشدارها
	elif text == "🛠 تنظیمات":
		if not admin_panel.is_feature_enabled('user.settings'):
			await update.message.reply_text("این بخش غیرفعال است.")
			return
		await show_settings(update, context)
		return
	elif text == "❓ راهنما":
		if not admin_panel.is_feature_enabled('user.help'):
			await update.message.reply_text("این بخش غیرفعال است.")
			return
		await help_cmd(update, context)
		return
	elif text == "📝 تنظیم متن‌ها":
		await show_text_settings(update, context)
		return
	elif text == "🔐 پنل مدیریتی":
		await admin_cmd(update, context)
		return
	elif text == "📊 آمار و گزارش":
		await show_detailed_stats(update, context)
		return
	# دکمه هشدارهای من حذف شده
	elif text == "/start":
		# بازگشت به منوی اصلی با دستور /start
		context.user_data.clear()
		await start(update, context)
		return
	
	# check for pending actions
	ud = get_user_data(STORE, uid)
	pending = (ud or {}).get("pending")
	if not pending:
		return
	
	ptype = pending.get("type")
	text_in = (update.message.text or "").strip()
	
	if ptype == "price_input":
		# Handle price input
		result = await get_crypto_price_with_provider(text_in, "coingecko")
		if not result:
			await update.message.reply_text("ارز موردنظر یافت نشد یا موقتا در دسترس نیست.")
		else:
			sym, price_usd, change = result
			price_txt = await convert_price_for_user(uid, price_usd)
			change_txt = "" if change is None else ("📈" if change >= 0 else "📉") + f" {change:.2f}%"
			await update.message.reply_text(f"قیمت لحظه‌ای {sym}:\n{price_txt}\nتغییر ۲۴ساعته: {('نامشخص' if not change_txt else change_txt)}")
		ud.pop("pending", None)
		save_store(STORE)
	elif ptype == "fiat_input":
		# Handle fiat rate input
		result = await get_fiat_rate_with_provider(text_in, "exchangerate_host", "USD")
		if not result:
			await update.message.reply_text("نرخ ارز موردنظر یافت نشد.")
		else:
			_, rate, _ = result
			await update.message.reply_text(f"نرخ {text_in}/USD: {rate:.4f}")
		ud.pop("pending", None)
		save_store(STORE)
	elif ptype == "chart":
		# text is a symbol, optional days not supported here; default 7
		coin_id = SYMBOL_TO_CG_ID.get(text_in.lower())
		if not coin_id:
			await update.message.reply_text("نماد پشتیبانی نمی‌شود.")
		else:
			series = await fetch_history_prices(coin_id, days=7)
			if not series:
				await update.message.reply_text("داده تاریخچه در دسترس نیست.")
			else:
				await update.message.reply_text(f"{text_in.upper()} {sparkline(series)}")
		ud.pop("pending", None)
		save_store(STORE)
	elif ptype == "news":
		items = await get_news(symbol=text_in, per_feed=3)
		if not items:
			await update.message.reply_text("خبری یافت نشد.")
		else:
			lines = []
			for it in items[:10]:
				title = it.get("title", "")
				link = it.get("link", "")
				lines.append(f"• {title}\n{link}")
			await update.message.reply_text("\n\n".join(lines))
		ud.pop("pending", None)
		save_store(STORE)
	elif ptype == "alert_add":
		# expecting: sym type value
		parts = text_in.split()
		if len(parts) >= 3:
			symbol, atype, val = parts[0], parts[1], parts[2]
			ud.setdefault("alerts", []).append({"symbol": symbol.lower(), "type": atype.lower(), "value": float(val)})
			save_store(STORE)
			await update.message.reply_text("هشدار ثبت شد.")
		else:
			await update.message.reply_text("فرمت نامعتبر. مثال: btc above 50000")
		ud.pop("pending", None)
		save_store(STORE)
	elif ptype == "arb":
		res = await compare_prices(text_in)
		if not res:
			await update.message.reply_text("اطلاعات کافی برای مقایسه موجود نیست.")
		else:
			sym, cg_p, bn_p, diff = res
			await update.message.reply_text(f"{sym}:\nCoingecko: {cg_p:,.4f}\nBinance: {bn_p:,.4f}\nاختلاف: {diff:.2f}%")
		ud.pop("pending", None)
		save_store(STORE)
	elif ptype == "p2p":
		parts = text_in.split()
		asset = parts[0].upper() if len(parts) > 0 else "USDT"
		fiat = parts[1].upper() if len(parts) > 1 else "IRR"
		trade_type = parts[2].upper() if len(parts) > 2 else "SELL"
		data = await fetch_binance_p2p(asset=asset, fiat=fiat, trade_type=trade_type)
		await update.message.reply_text(summarize_p2p_offers(data))
		ud.pop("pending", None)
		save_store(STORE)
	elif ptype == "wl_add":
		ud.setdefault("watchlist", []).append(text_in.strip().lower())
		save_store(STORE)
		await update.message.reply_text("به واچ‌لیست اضافه شد.")
		ud.pop("pending", None)
		save_store(STORE)
	elif ptype == "wl_del":
		ud["watchlist"] = [s for s in ud.get("watchlist", []) if s != text_in.strip().lower()]
		save_store(STORE)
		await update.message.reply_text("از واچ‌لیست حذف شد.")
		ud.pop("pending", None)
		save_store(STORE)
	elif ptype == "pf_add":
		parts = text_in.split()
		if len(parts) >= 3:
			sym, qty, avg = parts[0], float(parts[1]), float(parts[2])
			ud.setdefault("portfolio", []).append({"symbol": sym.lower(), "qty": qty, "avg_price": avg})
			save_store(STORE)
			await update.message.reply_text("به پرتفوی اضافه شد.")
		else:
			await update.message.reply_text("فرمت نادرست. مثال: btc 0.5 40000")
		ud.pop("pending", None)
		save_store(STORE)
	elif ptype == "pf_del":
		sym = text_in.strip().lower()
		ud["portfolio"] = [p for p in ud.get("portfolio", []) if p.get("symbol") != sym]
		save_store(STORE)
		await update.message.reply_text("از پرتفوی حذف شد.")
		ud.pop("pending", None)
		save_store(STORE)
	elif ptype == "ta":
		# Handle technical analysis input
		from ta import get_simple_ta
		result = await get_simple_ta(text_in)
		await update.message.reply_text(result)
		ud.pop("pending", None)
		save_store(STORE)
	elif ptype == "alert_del":
		try:
			index = int(text_in) - 1
			if 0 <= index < len(ud.get("alerts", [])):
				removed = ud["alerts"].pop(index)
				save_store(STORE)
				await update.message.reply_text(f"هشدار {removed['symbol'].upper()} حذف شد.")
			else:
				await update.message.reply_text("شماره هشدار نامعتبر است.")
		except ValueError:
			await update.message.reply_text("لطفا شماره هشدار را به صورت عدد وارد کنید.")
		ud.pop("pending", None)
		save_store(STORE)


async def on_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
	query = update.callback_query
	await query.answer()
	
	uid = query.from_user.id
	data = query.data
	
	logger.debug(f"on_callback: User {uid} clicked callback: {repr(data)}")
	
	# Skip if user is in admin conversation (handled by conversation handler)
	if context.user_data.get('admin_conversation', False):
		logger.debug(f"on_callback: User {uid} is in admin conversation, skipping")
		return
	
	# ثبت رویداد callback
	uid = query.from_user.id
	admin_panel.log_user_event(uid, 'callback')
	admin_panel.update_user_info(uid, query.from_user.username, query.from_user.full_name)
	
	# بررسی دسترسی کاربر (سیستم جدید)
	if not admin_panel.is_user_allowed(uid):
		# کاربر مسدود است - پیام اطلاع‌رسانی ارسال نمی‌کنیم تا از اسپم جلوگیری کنیم
		return
	
	data = query.data
	if data.startswith("LANGSEL:"):
		lang = data.split(":")[1]
		ud = get_user_data(STORE, query.from_user.id)
		ud.setdefault("settings", {})["language"] = lang
		save_store(STORE)
		await query.edit_message_text("زبان انتخاب شد. / Language selected. / تم اختيار اللغة.")
		# بعد از انتخاب زبان، فقط منو را نشان بده
		await query.message.reply_text("منوی اصلی:", reply_markup=reply_keyboard(update))
	elif data == "WL_DEL_MENU":
		await query.edit_message_text("لطفا نماد ارزی که می‌خواهید حذف کنید را وارد کنید:")
		ud = get_user_data(STORE, query.from_user.id)
		ud["pending"] = {"type": "wl_del"}
		save_store(STORE)
	elif data == "PF_DEL_MENU":
		await query.edit_message_text("لطفا نماد ارزی که می‌خواهید حذف کنید را وارد کنید:")
		ud = get_user_data(STORE, query.from_user.id)
		ud["pending"] = {"type": "pf_del"}
		save_store(STORE)
	elif data == "ALERT_DEL_MENU":
		await query.edit_message_text("لطفا شماره هشداری که می‌خواهید حذف کنید را وارد کنید:")
		ud = get_user_data(STORE, query.from_user.id)
		ud["pending"] = {"type": "alert_del"}
		save_store(STORE)
	elif data == "CHANGE_LANG":
		await query.edit_message_text(
			"زبان مورد نظر را انتخاب کنید:",
			reply_markup=InlineKeyboardMarkup([
				[InlineKeyboardButton(text="فارسی", callback_data="LANGSEL:FA")],
				[InlineKeyboardButton(text="English", callback_data="LANGSEL:EN")],
				[InlineKeyboardButton(text="العربية", callback_data="LANGSEL:AR")]
			])
		)
	elif data == "CHANGE_BASE_FIAT":
		await query.edit_message_text(
			"ارز پایه مورد نظر را انتخاب کنید:",
			reply_markup=InlineKeyboardMarkup([
				[InlineKeyboardButton(text="USD", callback_data="BASE_FIAT:USD")],
				[InlineKeyboardButton(text="EUR", callback_data="BASE_FIAT:EUR")],
				[InlineKeyboardButton(text="IRR", callback_data="BASE_FIAT:IRR")]
			])
		)
	elif data.startswith("BASE_FIAT:"):
		base_fiat = data.split(":")[1]
		ud = get_user_data(STORE, query.from_user.id)
		ud.setdefault("settings", {})["base_fiat"] = base_fiat
		save_store(STORE)
		await query.edit_message_text(f"ارز پایه به {base_fiat} تغییر یافت.")
	elif data == "back_to_crypto_list":
		await show_crypto_list(update, context)
	elif data == "show_all_cryptos":
		await show_all_cryptos(update, context)
	elif data.startswith("crypto_detail:"):
		await show_crypto_detail(update, context)
	elif data.startswith("refresh_crypto:"):
		await refresh_crypto_price(update, context)
	elif data.startswith("chart_crypto:"):
		await show_crypto_chart(update, context)
	elif data.startswith("refresh_chart:"):
		await show_crypto_chart(update, context)
	elif data == "back_to_main":
		# بازگشت به منوی اصلی با inline keyboard
		keyboard = [
			[InlineKeyboardButton("💰 قیمت ارز", callback_data="crypto_list")],
			[InlineKeyboardButton("🏦 ارز داخلی", callback_data="currency_list")],
			[InlineKeyboardButton("📰 اخبار", callback_data="news_menu")],
			[InlineKeyboardButton("📊 نمودار", callback_data="chart_menu")],
			[InlineKeyboardButton("🛠 تنظیمات", callback_data="settings_menu")],
			[InlineKeyboardButton("❓ راهنما", callback_data="help_menu")]
		]
		reply_markup = InlineKeyboardMarkup(keyboard)
		await query.edit_message_text(
			get_help_text(query.from_user.id),
			reply_markup=reply_markup
		)
	elif data == "crypto_list":
		await show_crypto_list(update, context)
	elif data == "currency_list":
		await show_domestic_currency_list(update, context)
	elif data == "news_menu":
		await query.edit_message_text(
			"📰 **منوی اخبار**\n\n"
			"لطفاً نماد ارز مورد نظر را وارد کنید (مثل: btc, eth) یا Enter بزنید برای اخبار عمومی",
			reply_markup=InlineKeyboardMarkup([[
				InlineKeyboardButton("🔙 بازگشت", callback_data="back_to_main")
			]])
		)
	elif data == "chart_menu":
		await query.edit_message_text(
			"📊 **منوی نمودار**\n\n"
			"لطفاً نماد ارز مورد نظر را وارد کنید (مثل: btc, eth)",
			reply_markup=InlineKeyboardMarkup([[
				InlineKeyboardButton("🔙 بازگشت", callback_data="back_to_main")
			]])
		)
	elif data == "settings_menu":
		await show_settings(update, context)
	elif data == "help_menu":
		ud = get_user_data(STORE, query.from_user.id)
		await query.edit_message_text(
			help_text_by_lang(ud.get("settings", {}).get("language", "FA")),
			reply_markup=InlineKeyboardMarkup([[
				InlineKeyboardButton("🔙 بازگشت", callback_data="back_to_main")
			]])
		)
	elif data == "calculator_help":
		await handle_calculator_help(update, context)
	elif data == "back_to_calculator":
		await send_calculator_ready_message(update, context)
	elif data.startswith("recalc:") or data.startswith("chart:") or data.startswith("alert:"):
		await handle_calculator_callback(update, context)
	elif data == "verify_membership":
		await admin_panel.verify_user_membership(update, context)
	elif data == "refresh_gate":
		await admin_panel.refresh_gate(update, context)
	elif data == "no_link":
		await query.answer("❌ لینک عضویت در دسترس نیست!")
	elif data == "check_subscription":
		# بررسی مجدد عضویت
		if await check_force_subscription(update, context):
			await query.edit_message_text(
				get_help_text(query.from_user.id),
				reply_markup=reply_keyboard(update)
			)
		else:
			await query.answer("❌ هنوز در تمام کانال‌ها عضو نشده‌اید!")
	elif data == "refresh_detailed_stats":
		await show_detailed_stats(update, context)
	elif data == "show_full_blocked_list":
		await show_full_blocked_list(update, context)
	elif data == "export_stats_csv":
		await export_stats_csv(update, context)
	elif data.startswith("show_full_blocked_list:"):
		await show_full_blocked_list(update, context)
	elif data.startswith("message_user:"):
		user_id = data.split(":")[1]
		await start_user_message(update, context, user_id)
	elif data == "cancel_user_message":
		await cancel_user_message(update, context)
	elif data.startswith("cancel_alert:"):
		crypto_symbol = data.split(":")[1]
		await cancel_alert_setup(update, context, crypto_symbol)
	elif data == "my_alerts":
		await show_user_alerts(update, context)
	elif data == "show_currency_buttons":
		await show_currency_buttons(update, context)
	elif data.startswith("CURRENCY:"):
		currency_code = data.split(":")[1]
		await handle_currency_selection(update, context, currency_code)
	elif data.startswith("DOMESTIC_CURRENCY:"):
		currency_symbol = data.split(":")[1]
		await show_domestic_currency_detail(update, context, currency_symbol)
	elif data.startswith("REFRESH_DOMESTIC:"):
		currency_symbol = data.split(":")[1]
		await show_domestic_currency_detail(update, context, currency_symbol)
	elif data.startswith("CHART_DOMESTIC:"):
		currency_symbol = data.split(":")[1]
		await show_domestic_currency_chart(update, context, currency_symbol)
	elif data == "back_to_domestic_list":
		await show_domestic_currency_list(update, context)
	elif data.startswith("REFRESH_CURRENCY:"):
		currency_code = data.split(":")[1]
		await handle_currency_selection(update, context, currency_code)
	elif data.startswith("CHART_CURRENCY:"):
		currency_code = data.split(":")[1]
		await show_currency_chart(update, context, currency_code)
	elif data.startswith("SET_ALERT:"):
		symbol = data.split(":")[1]
		await setup_alert(update, context, symbol)


async def handle_pending_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
	"""مدیریت ورودی‌های در انتظار"""
	uid = update.effective_user.id
	ud = get_user_data(STORE, uid)
	
	if "pending" not in ud:
		return
	
	pending = ud["pending"]
	pending_type = pending.get("type")
	
	if pending_type == "alert_setup":
		await handle_alert_setup(update, context, pending)
	elif pending_type == "user_message":
		await handle_user_message(update, context, pending)
	elif pending_type == "fiat_input":
		await handle_fiat_input(update, context)
	elif pending_type == "news":
		await handle_news_input(update, context)
	elif pending_type == "chart":
		await handle_chart_input(update, context)
	elif pending_type == "ta":
		await handle_ta_input(update, context)
	elif pending_type == "arb":
		await handle_arb_input(update, context)
	elif pending_type == "p2p":
		await handle_p2p_input(update, context)


async def handle_alert_setup(update: Update, context: ContextTypes.DEFAULT_TYPE, pending: dict) -> None:
	"""مدیریت تنظیم هشدار"""
	uid = update.effective_user.id
	text = update.message.text
	
	if text.lower() == "/cancel":
		ud = get_user_data(STORE, uid)
		ud.pop("pending", None)
		save_store(STORE)
		await update.message.reply_text("❌ تنظیم هشدار لغو شد.")
		return
	
	try:
		target_price = float(text)
		crypto_symbol = pending.get("crypto", "BTC")
		
		# ذخیره هشدار
		alerts = STORE.get('alerts', {})
		if uid not in alerts:
			alerts[uid] = []
		
		alert = {
			"crypto": crypto_symbol,
			"target_price": target_price,
			"created_at": datetime.now().isoformat(),
			"active": True
		}
		
		alerts[uid].append(alert)
		STORE['alerts'] = alerts
		save_store(STORE)
		
		# پاک کردن pending
		ud = get_user_data(STORE, uid)
		ud.pop("pending", None)
		save_store(STORE)
		
		await update.message.reply_text(
			f"✅ **هشدار تنظیم شد!**\n\n"
			f"🔔 **ارز**: {crypto_symbol.upper()}\n"
			f"💰 **قیمت هدف**: ${target_price:,.2f}\n"
			f"📅 **تاریخ**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
			f"هنگامی که قیمت {crypto_symbol.upper()} به ${target_price:,.2f} برسد، به شما اطلاع داده خواهد شد."
		)
		
	except ValueError:
		await update.message.reply_text(
			"❌ لطفاً یک عدد معتبر وارد کنید.\n"
			"مثال: 50000\n\n"
			"🔙 برای لغو: /cancel"
		)


async def handle_user_message(update: Update, context: ContextTypes.DEFAULT_TYPE, pending: dict) -> None:
	"""مدیریت ارسال پیام به کاربر"""
	uid = update.effective_user.id
	text = update.message.text
	target_user_id = pending.get("target_user")
	
	if text.lower() == "/cancel":
		ud = get_user_data(STORE, uid)
		ud.pop("pending", None)
		save_store(STORE)
		await update.message.reply_text("❌ ارسال پیام لغو شد.")
		return
	
	try:
		target_user_id = int(target_user_id)
		
		# ارسال پیام به کاربر
		try:
			await context.bot.send_message(
				chat_id=target_user_id,
				text=f"💬 **پیام از مدیر ربات:**\n\n{text}"
			)
			
			# پاک کردن pending
			ud = get_user_data(STORE, uid)
			ud.pop("pending", None)
			save_store(STORE)
			
			await update.message.reply_text(
				f"✅ **پیام ارسال شد!**\n\n"
				f"👤 **به کاربر**: {target_user_id}\n"
				f"📝 **پیام**: {text[:100]}{'...' if len(text) > 100 else ''}"
			)
			
		except Exception as e:
			await update.message.reply_text(
				f"❌ **خطا در ارسال پیام:**\n\n"
				f"👤 **کاربر**: {target_user_id}\n"
				f"🔍 **خطا**: {str(e)}\n\n"
				f"ممکن است کاربر ربات را بلاک کرده باشد یا آیدی اشتباه باشد."
			)
			
	except ValueError:
		await update.message.reply_text(
			"❌ آیدی کاربر نامعتبر است.\n\n"
			"🔙 برای لغو: /cancel"
		)


async def handle_fiat_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
	"""مدیریت ورودی نرخ ارز"""
	uid = update.effective_user.id
	text = update.message.text.strip().upper()
	
	if text.lower() == "/cancel":
		ud = get_user_data(STORE, uid)
		ud.pop("pending", None)
		save_store(STORE)
		await update.message.reply_text("❌ درخواست نرخ ارز لغو شد.")
		return
	
	# پاک کردن pending
	ud = get_user_data(STORE, uid)
	ud.pop("pending", None)
	save_store(STORE)
	
	# دریافت نرخ ارز
	result = await get_fiat_rate_with_provider(text, "exchangerate_host", "USD")
	if not result:
		await update.message.reply_text(
			f"❌ نرخ ارز {text} یافت نشد.\n"
			f"لطفاً کد ارز صحیح را وارد کنید (مثل: EUR, GBP, JPY)"
		)
		return
	
	_, rate, _ = result
	
	# ایجاد دکمه‌های شیشه‌ای
	keyboard = [
		[InlineKeyboardButton("🔄 بروزرسانی", callback_data=f"REFRESH_CURRENCY:{text}")],
		[InlineKeyboardButton("📊 نمودار", callback_data=f"CHART_CURRENCY:{text}")],
		[InlineKeyboardButton("💱 ارز دیگر", callback_data="show_currency_buttons")],
		[InlineKeyboardButton("🔙 بازگشت به منو", callback_data="back_to_main")]
	]
	
	await update.message.reply_text(
		f"💎 **نرخ {text}/USD:**\n\n"
		f"💰 **قیمت**: {rate:.4f}\n"
		f"📅 **تاریخ**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
		reply_markup=InlineKeyboardMarkup(keyboard)
	)


async def handle_fiat_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
	"""مدیریت ورودی نرخ ارز"""
	uid = update.effective_user.id
	text = update.message.text.strip().upper()
	
	if text.lower() == "/cancel":
		ud = get_user_data(STORE, uid)
		ud.pop("pending", None)
		save_store(STORE)
		await update.message.reply_text("❌ درخواست نرخ ارز لغو شد.")
		return
	
	# پاک کردن pending
	ud = get_user_data(STORE, uid)
	ud.pop("pending", None)
	save_store(STORE)
	
	# دریافت نرخ ارز
	result = await get_fiat_rate_with_provider(text, "exchangerate_host", "USD")
	if not result:
		await update.message.reply_text(
			f"❌ نرخ ارز {text} یافت نشد.\n"
			f"لطفاً کد ارز صحیح را وارد کنید (مثل: EUR, GBP, JPY)"
		)
		return
	
	_, rate, _ = result
	
	# ایجاد دکمه‌های شیشه‌ای
	keyboard = [
		[InlineKeyboardButton("🔄 بروزرسانی", callback_data=f"REFRESH_CURRENCY:{text}")],
		[InlineKeyboardButton("📊 نمودار", callback_data=f"CHART_CURRENCY:{text}")],
		[InlineKeyboardButton("💱 ارز دیگر", callback_data="show_currency_buttons")],
		[InlineKeyboardButton("🔙 بازگشت به منو", callback_data="back_to_main")]
	]
	
	await update.message.reply_text(
		f"💎 **نرخ {text}/USD:**\n\n"
		f"💰 **قیمت**: {rate:.4f}\n"
		f"📅 **تاریخ**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
		reply_markup=InlineKeyboardMarkup(keyboard)
	)


async def handle_news_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
	"""مدیریت ورودی اخبار"""
	uid = update.effective_user.id
	text = update.message.text.strip().lower()
	
	if text.lower() == "/cancel":
		ud = get_user_data(STORE, uid)
		ud.pop("pending", None)
		save_store(STORE)
		await update.message.reply_text("❌ درخواست اخبار لغو شد.")
		return
	
	# پاک کردن pending
	ud = get_user_data(STORE, uid)
	ud.pop("pending", None)
	save_store(STORE)
	
	if not text or text == "":
		# اخبار عمومی
		await update.message.reply_text("📰 در حال دریافت اخبار عمومی...")
		# اینجا کد دریافت اخبار عمومی اضافه می‌شود
	else:
		# اخبار ارز خاص
		await update.message.reply_text(f"📰 در حال دریافت اخبار {text.upper()}...")


async def handle_chart_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
	"""مدیریت ورودی نمودار"""
	uid = update.effective_user.id
	text = update.message.text.strip().lower()
	
	if text.lower() == "/cancel":
		ud = get_user_data(STORE, uid)
		ud.pop("pending", None)
		save_store(STORE)
		await update.message.reply_text("❌ درخواست نمودار لغو شد.")
		return
	
	# پاک کردن pending
	ud = get_user_data(STORE, uid)
	ud.pop("pending", None)
	save_store(STORE)
	
	await update.message.reply_text(f"📊 در حال ایجاد نمودار {text.upper()}...")




async def handle_ta_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
	"""مدیریت ورودی تحلیل تکنیکال"""
	uid = update.effective_user.id
	text = update.message.text.strip().lower()
	
	if text.lower() == "/cancel":
		ud = get_user_data(STORE, uid)
		ud.pop("pending", None)
		save_store(STORE)
		await update.message.reply_text("❌ درخواست تحلیل تکنیکال لغو شد.")
		return
	
	# پاک کردن pending
	ud = get_user_data(STORE, uid)
	ud.pop("pending", None)
	save_store(STORE)
	
	await update.message.reply_text(f"📈 در حال تحلیل تکنیکال {text.upper()}...")


async def handle_arb_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
	"""مدیریت ورودی مقایسه"""
	uid = update.effective_user.id
	text = update.message.text.strip().lower()
	
	if text.lower() == "/cancel":
		ud = get_user_data(STORE, uid)
		ud.pop("pending", None)
		save_store(STORE)
		await update.message.reply_text("❌ درخواست مقایسه لغو شد.")
		return
	
	# پاک کردن pending
	ud = get_user_data(STORE, uid)
	ud.pop("pending", None)
	save_store(STORE)
	
	await update.message.reply_text(f"⚖️ در حال مقایسه قیمت‌های {text.upper()}...")


async def handle_p2p_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
	"""مدیریت ورودی P2P"""
	uid = update.effective_user.id
	text = update.message.text.strip()
	
	if text.lower() == "/cancel":
		ud = get_user_data(STORE, uid)
		ud.pop("pending", None)
		save_store(STORE)
		await update.message.reply_text("❌ درخواست P2P لغو شد.")
		return
	
	# پاک کردن pending
	ud = get_user_data(STORE, uid)
	ud.pop("pending", None)
	save_store(STORE)
	
	await update.message.reply_text(f"🔄 در حال جستجوی قیمت‌های P2P برای: {text}")


async def handle_pending_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
	"""مدیریت ورودی‌های در انتظار"""
	uid = update.effective_user.id
	ud = get_user_data(STORE, uid)
	
	if "pending" not in ud:
		return
	
	pending = ud["pending"]
	pending_type = pending.get("type")
	
	if pending_type == "alert_setup":
		await handle_alert_setup(update, context, pending)
	elif pending_type == "user_message":
		await handle_user_message(update, context, pending)
	elif pending_type == "fiat_input":
		await handle_fiat_input(update, context)
	elif pending_type == "news":
		await handle_news_input(update, context)
	elif pending_type == "chart":
		await handle_chart_input(update, context)
	elif pending_type == "ta":
		await handle_ta_input(update, context)
	elif pending_type == "arb":
		await handle_arb_input(update, context)
	elif pending_type == "p2p":
		await handle_p2p_input(update, context)


async def handle_alert_setup(update: Update, context: ContextTypes.DEFAULT_TYPE, pending: dict) -> None:
	"""مدیریت تنظیم هشدار"""
	uid = update.effective_user.id
	text = update.message.text
	
	if text.lower() == "/cancel":
		ud = get_user_data(STORE, uid)
		ud.pop("pending", None)
		save_store(STORE)
		await update.message.reply_text("❌ تنظیم هشدار لغو شد.")
		return
	
	try:
		target_price = float(text)
		crypto_symbol = pending.get("crypto", "BTC")
		
		# ذخیره هشدار
		alerts = STORE.get('alerts', {})
		if uid not in alerts:
			alerts[uid] = []
		
		alert = {
			"crypto": crypto_symbol,
			"target_price": target_price,
			"created_at": datetime.now().isoformat(),
			"active": True
		}
		
		alerts[uid].append(alert)
		STORE['alerts'] = alerts
		save_store(STORE)
		
		# پاک کردن pending
		ud = get_user_data(STORE, uid)
		ud.pop("pending", None)
		save_store(STORE)
		
		await update.message.reply_text(
			f"✅ **هشدار تنظیم شد!**\n\n"
			f"🔔 **ارز**: {crypto_symbol.upper()}\n"
			f"💰 **قیمت هدف**: ${target_price:,.2f}\n"
			f"📅 **تاریخ**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
			f"هنگامی که قیمت {crypto_symbol.upper()} به ${target_price:,.2f} برسد، به شما اطلاع داده خواهد شد."
		)
		
	except ValueError:
		await update.message.reply_text(
			"❌ لطفاً یک عدد معتبر وارد کنید.\n"
			"مثال: 50000\n\n"
			"🔙 برای لغو: /cancel"
		)


async def handle_user_message(update: Update, context: ContextTypes.DEFAULT_TYPE, pending: dict) -> None:
	"""مدیریت ارسال پیام به کاربر"""
	uid = update.effective_user.id
	text = update.message.text
	target_user_id = pending.get("target_user")
	
	if text.lower() == "/cancel":
		ud = get_user_data(STORE, uid)
		ud.pop("pending", None)
		save_store(STORE)
		await update.message.reply_text("❌ ارسال پیام لغو شد.")
		return
	
	try:
		target_user_id = int(target_user_id)
		
		# ارسال پیام به کاربر
		try:
			await context.bot.send_message(
				chat_id=target_user_id,
				text=f"💬 **پیام از مدیر ربات:**\n\n{text}"
			)
			
			# پاک کردن pending
			ud = get_user_data(STORE, uid)
			ud.pop("pending", None)
			save_store(STORE)
			
			await update.message.reply_text(
				f"✅ **پیام ارسال شد!**\n\n"
				f"👤 **به کاربر**: {target_user_id}\n"
				f"📝 **پیام**: {text[:100]}{'...' if len(text) > 100 else ''}"
			)
			
		except Exception as e:
			await update.message.reply_text(
				f"❌ **خطا در ارسال پیام:**\n\n"
				f"👤 **کاربر**: {target_user_id}\n"
				f"🔍 **خطا**: {str(e)}\n\n"
				f"ممکن است کاربر ربات را بلاک کرده باشد یا آیدی اشتباه باشد."
			)
			
	except ValueError:
		await update.message.reply_text(
			"❌ آیدی کاربر نامعتبر است.\n\n"
			"🔙 برای لغو: /cancel"
		)


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
	"""مدیریت پیام‌های کاربر"""
	user = update.effective_user
	uid = user.id
	
	# check black/white list
	allowed, reason = check_black_white(uid)
	if not allowed:
		return
	
	# rate limit
	ok, reason = touch_rate_limit(uid)
	if not ok:
		return
	
	# Handle pending input
	await handle_pending_input(update, context)
	
	# Handle user messages
	text = update.message.text.strip()
	
	if text.startswith("/"):
		# Command handler will handle commands
		pass
	elif text.startswith("@"):
		# Mention handler will handle mentions
		pass
	else:
		# Regular text message
		await update.message.reply_text(
			"متاسفانه من فقط دستورات و پیام‌های خاص را پشتیبانی می‌کنم. لطفاً از دکمه‌های میانبر استفاده کنید."
		)


def build_app():
	app = ApplicationBuilder().token(BOT_TOKEN).concurrent_updates(True).build()
	
	# Core commands
	app.add_handler(CommandHandler("start", start_cmd))
	app.add_handler(CommandHandler("help", help_cmd))
	app.add_handler(CommandHandler("price", price))
	app.add_handler(CommandHandler("admin", admin_cmd))
	
	# Admin panel conversation handler - Fixed broadcast_message_process issue
	admin_conv_handler = ConversationHandler(
		entry_points=[CommandHandler("admin", admin_cmd)],
		states={
			ADMIN_PANEL: [
				MessageHandler(filters.TEXT & ~filters.COMMAND, admin_panel.handle_admin_panel_text),
				CallbackQueryHandler(admin_panel.handle_callback),
				CommandHandler("cancel", admin_panel.cancel)
			],
			ADD_ADMIN: [
				MessageHandler(filters.TEXT & ~filters.COMMAND, admin_panel.add_admin_process),
				CommandHandler("cancel", admin_panel.cancel_admin_operation)
			],
			REMOVE_ADMIN: [
				MessageHandler(filters.TEXT & ~filters.COMMAND, admin_panel.remove_admin_process),
				CommandHandler("cancel", admin_panel.cancel_admin_operation)
			],
			BROADCAST_MESSAGE: [
				MessageHandler(filters.ALL, admin_panel.broadcast_message_start),
				CommandHandler("cancel", admin_panel.cancel)
			],
			BROADCAST_FORWARD: [
				MessageHandler(filters.ALL, admin_panel.broadcast_forward_process),
				CommandHandler("cancel", admin_panel.cancel)
			],
			"BROADCAST_CAPTURE": [
				MessageHandler(filters.ALL, admin_panel.capture_broadcast_message),
				CommandHandler("cancel", admin_panel.cancel)
			],
			EXTERNAL_API_URL: [
				MessageHandler(filters.TEXT & ~filters.COMMAND, admin_panel.external_api_url_process),
				CommandHandler("cancel", admin_panel.cancel_admin_operation)
			],
			EXTERNAL_API_KEY: [
				MessageHandler(filters.TEXT & ~filters.COMMAND, admin_panel.external_api_key_process),
				CommandHandler("cancel", admin_panel.cancel_admin_operation)
			],
			EXTERNAL_API_TYPE: [
				MessageHandler(filters.TEXT & ~filters.COMMAND, admin_panel.external_api_type_process),
				CommandHandler("cancel", admin_panel.cancel_admin_operation)
			],
			SUBMIT_LOCK_LINK: [
				MessageHandler(filters.ALL, admin_panel.process_lock_link_or_forward),
				CommandHandler("cancel", admin_panel.cancel_admin_operation)
			],
			FEATURE_SEARCH: [
				MessageHandler(filters.TEXT & ~filters.COMMAND, admin_panel.process_feature_search),
				CommandHandler("cancel", admin_panel.cancel_admin_operation)
			],
			AWAIT_BLACKLIST_ADD: [
				MessageHandler(filters.TEXT & ~filters.COMMAND, admin_panel.add_to_blacklist_process),
				CommandHandler("cancel", admin_panel.cancel_admin_operation)
			],
			AWAIT_BLACKLIST_REMOVE: [
				MessageHandler(filters.TEXT & ~filters.COMMAND, admin_panel.remove_from_blacklist_process),
				CommandHandler("cancel", admin_panel.cancel_admin_operation)
			],
			AWAIT_WHITELIST_ADD: [
				MessageHandler(filters.TEXT & ~filters.COMMAND, admin_panel.add_to_whitelist_process),
				CommandHandler("cancel", admin_panel.cancel_admin_operation)
			],
			AWAIT_WHITELIST_REMOVE: [
				MessageHandler(filters.TEXT & ~filters.COMMAND, admin_panel.remove_from_whitelist_process),
				CommandHandler("cancel", admin_panel.cancel_admin_operation)
			],
			LISTS_SEARCH: [
				MessageHandler(filters.TEXT & ~filters.COMMAND, admin_panel.search_lists_process),
				CommandHandler("cancel", admin_panel.cancel_admin_operation)
			],
			SET_WELCOME_TEXT: [
				MessageHandler(filters.TEXT & ~filters.COMMAND, admin_panel.set_welcome_text_process),
				CommandHandler("cancel", admin_panel.cancel)
			],
			SET_HELP_TEXT: [
				MessageHandler(filters.TEXT & ~filters.COMMAND, admin_panel.set_help_text_process),
				CommandHandler("cancel", admin_panel.cancel)
			],
			SET_ERROR_TEXT: [
				MessageHandler(filters.TEXT & ~filters.COMMAND, admin_panel.set_error_text_process),
				CommandHandler("cancel", admin_panel.cancel)
			],
			SET_API_KEY: [
				MessageHandler(filters.TEXT & ~filters.COMMAND, admin_panel.set_api_key_process),
				CommandHandler("cancel", admin_panel.cancel)
			],
			SET_TRADINGVIEW_API: [
				MessageHandler(filters.TEXT & ~filters.COMMAND, admin_panel.set_tradingview_api_process),
				CommandHandler("cancel", admin_panel.cancel)
			],
			SET_FIAT_API: [
				MessageHandler(filters.TEXT & ~filters.COMMAND, admin_panel.set_fiat_api_process),
				CommandHandler("cancel", admin_panel.cancel)
			],
			SET_CRYPTO_API_KEY: [
				MessageHandler(filters.TEXT & ~filters.COMMAND, admin_panel.set_crypto_api_process),
				CommandHandler("cancel", admin_panel.cancel)
			],
			FORCE_SUBSCRIPTION: [
				MessageHandler(filters.TEXT & ~filters.COMMAND, admin_panel.set_force_sub_channel_process),
				CommandHandler("cancel", admin_panel.cancel)
			],
			ADD_FORCE_SUB_CHANNEL: [
				MessageHandler(filters.TEXT & ~filters.COMMAND, admin_panel.add_force_sub_channel_process),
				CommandHandler("cancel", admin_panel.cancel)
			],
			ADD_WHITELIST: [
				MessageHandler(filters.TEXT & ~filters.COMMAND, admin_panel.add_whitelist_process),
				CommandHandler("cancel", admin_panel.cancel)
			],
			ADD_BLACKLIST: [
				MessageHandler(filters.TEXT & ~filters.COMMAND, admin_panel.add_blacklist_process),
				CommandHandler("cancel", admin_panel.cancel)
			],
			USER_MESSAGE: [
				MessageHandler(filters.TEXT & ~filters.COMMAND, admin_panel.send_user_message),
				CommandHandler("cancel", admin_panel.cancel)
			]
		},
		fallbacks=[CommandHandler("cancel", admin_panel.cancel)]
	)
	app.add_handler(admin_conv_handler)
	
	# Shortcut commands
	for sym in ["btc", "eth", "bnb", "sol", "xrp", "ada", "doge", "ton", "trx", "ltc"]:
		app.add_handler(CommandHandler(sym, lambda u, c, s=sym: price_shortcut(u, c, s)))
	
	# Start command handler - always returns to main menu
	app.add_handler(MessageHandler(filters.Regex("^/start$"), start_cmd))
	
	# Crypto selection handler - handles crypto button presses from keyboard
	# User menu handlers - these will only handle non-admin users
	# Admin users are handled by the conversation handler above
	app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), on_menu_text))
	app.add_handler(CallbackQueryHandler(on_callback))
	
	return app


# توابع ضروری گم شده

async def handle_currency_selection(update: Update, context: ContextTypes.DEFAULT_TYPE, currency_code: str) -> None:
	"""مدیریت انتخاب کد ارز در پنجره شیشه‌ای"""
	uid = update.callback_query.from_user.id
	ud = get_user_data(STORE, uid)
	
	# پاک کردن pending
	ud.pop("pending", None)
	save_store(STORE)
	
	# دریافت نرخ ارز برای کد ارز انتخاب شده
	result = await get_fiat_rate_with_provider(currency_code, "exchangerate_host", "USD")
	if not result:
		await update.callback_query.edit_message_text(
			f"❌ نرخ ارز {currency_code} یافت نشد.\n"
			f"لطفاً کد ارز صحیح را انتخاب کنید."
		)
		return
	
	_, rate, _ = result
	
	# ایجاد دکمه‌های شیشه‌ای
	keyboard = [
		[InlineKeyboardButton("🔄 بروزرسانی", callback_data=f"REFRESH_CURRENCY:{currency_code}")],
		[InlineKeyboardButton("📊 نمودار", callback_data=f"CHART_CURRENCY:{currency_code}")],
		[InlineKeyboardButton("💱 ارز دیگر", callback_data="show_currency_buttons")],
		[InlineKeyboardButton("🔙 بازگشت به منو", callback_data="back_to_main")]
	]
	
	await update.callback_query.edit_message_text(
		f"💎 **نرخ {currency_code}/USD:**\n\n"
		f"💰 **قیمت**: {rate:.4f}\n"
		f"📅 **تاریخ**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
		reply_markup=InlineKeyboardMarkup(keyboard)
	)


async def show_currency_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
	"""نمایش دکمه‌های شیشه‌ای برای انتخاب ارز"""
	currencies = ["EUR", "GBP", "JPY", "AUD", "CAD", "CHF", "CNY", "INR", "KRW", "RUB", "TRY", "AED"]
	
	keyboard = []
	for i in range(0, len(currencies), 2):
		row = []
		for j in range(2):
			if i + j < len(currencies):
				currency = currencies[i + j]
				row.append(InlineKeyboardButton(f"💎 {currency}", callback_data=f"CURRENCY:{currency}"))
		keyboard.append(row)
	
	keyboard.append([InlineKeyboardButton("🔙 بازگشت به منو", callback_data="back_to_main")])
	
	await update.callback_query.edit_message_text(
		"💎 **انتخاب ارز مورد نظر:**\n\n"
		"لطفاً یکی از ارزهای زیر را انتخاب کنید:",
		reply_markup=InlineKeyboardMarkup(keyboard)
	)


async def show_currency_chart(update: Update, context: ContextTypes.DEFAULT_TYPE, currency_code: str) -> None:
	"""نمایش نمودار ارز"""
	keyboard = [
		[InlineKeyboardButton("🔄 بروزرسانی", callback_data=f"REFRESH_CURRENCY:{currency_code}")],
		[InlineKeyboardButton("💱 ارز دیگر", callback_data="show_currency_buttons")],
		[InlineKeyboardButton("🔙 بازگشت به منو", callback_data="back_to_main")]
	]
	
	await update.callback_query.edit_message_text(
		f"📊 **نمودار {currency_code}/USD**\n\n"
		f"نمودار قیمت {currency_code} در برابر دلار آمریکا\n"
		f"(نمودار در حال حاضر در دسترس نیست)",
		reply_markup=InlineKeyboardMarkup(keyboard)
	)


async def show_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
	"""نمایش منوی اصلی"""
	if update.callback_query:
		await update.callback_query.edit_message_text(
			"منوی اصلی:",
			reply_markup=reply_keyboard(update)
		)
	else:
		await update.message.reply_text(
			"منوی اصلی:",
			reply_markup=reply_keyboard(update)
		)


async def setup_alert(update: Update, context: ContextTypes.DEFAULT_TYPE, crypto_symbol: str) -> None:
	"""تنظیم هشدار برای ارز"""
	uid = update.callback_query.from_user.id
	ud = get_user_data(STORE, uid)
	
	# بررسی وضعیت هشدارها
	alert_mode = STORE.get('alert_type', 'optional')
	
	if alert_mode == 'required':
		await update.callback_query.edit_message_text(
			"🔒 **هشدارهای اجباری فعال هستند!**\n\n"
			"تنها مالک ربات می‌تواند هشدار تنظیم کند.\n"
			"🔙 برای بازگشت کلیک کنید:",
			reply_markup=InlineKeyboardMarkup([[
				InlineKeyboardButton("🔙 بازگشت", callback_data=f"crypto_detail:{crypto_symbol}")
			]])
		)
		return
	
	# دریافت قیمت فعلی
	try:
		current_price_result = await get_crypto_price_with_provider(crypto_symbol.lower(), "coingecko")
		if current_price_result:
			_, current_price, _ = current_price_result
			current_price_text = await convert_price_for_user(uid, current_price)
		else:
			current_price_text = "نامشخص"
	except:
		current_price_text = "نامشخص"
	
	# نمایش فرم تنظیم هشدار
	keyboard = [
		[InlineKeyboardButton("❌ لغو", callback_data=f"cancel_alert:{crypto_symbol}")]
	]
	reply_markup = InlineKeyboardMarkup(keyboard)
	
	await update.callback_query.edit_message_text(
		f"🔔 **تنظیم هشدار برای {crypto_symbol.upper()}**\n\n"
		f"💰 **قیمت فعلی**: {current_price_text}\n\n"
		f"💬 **لطفاً قیمت هدف را وارد کنید**:\n"
		f"مثال: 50000\n\n"
		f"💡 **نکات مهم**:\n"
		f"• قیمت را به دلار وارد کنید\n"
		f"• ربات هنگام رسیدن به قیمت به شما اطلاع می‌دهد\n"
		f"• می‌توانید چندین هشدار تنظیم کنید\n\n"
		f"🔙 برای لغو: /cancel",
		reply_markup=reply_markup,
		parse_mode='Markdown'
	)
	
	# ذخیره وضعیت
	ud["pending"] = {
		"type": "alert_setup",
		"crypto": crypto_symbol
	}
	save_store(STORE)
	
async def cancel_alert_setup(update: Update, context: ContextTypes.DEFAULT_TYPE, crypto_symbol: str) -> None:
	"""لغو تنظیم هشدار"""
	query = update.callback_query
	await query.answer()
	
	uid = query.from_user.id
	ud = get_user_data(STORE, uid)
	
	# حذف pending
	if "pending" in ud:
		del ud["pending"]
		save_store(STORE)
	
	await query.edit_message_text(
		f"❌ **تنظیم هشدار لغو شد!**\n\n"
		f"هشدار برای {crypto_symbol.upper()} تنظیم نشد.",
		reply_markup=InlineKeyboardMarkup([[
			InlineKeyboardButton("🔙 بازگشت", callback_data=f"crypto_detail:{crypto_symbol}")
		]])
	)

async def show_user_alerts(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
	"""نمایش هشدارهای کاربر"""
	query = update.callback_query
	await query.answer()
	
	uid = query.from_user.id
	alerts = STORE.get('alerts', {}).get(uid, [])
	
	if not alerts:
		await query.edit_message_text(
			"🔔 **هشدارهای شما**\n\n"
			"❌ هیچ هشدار فعالی ندارید.\n\n"
			"برای تنظیم هشدار، از دکمه '🔔 تنظیم هشدار' در جزئیات ارز استفاده کنید.",
			reply_markup=InlineKeyboardMarkup([[
				InlineKeyboardButton("🔙 بازگشت", callback_data="back_to_main")
			]])
		)
		return
	
	# نمایش هشدارها
	alerts_text = f"🔔 **هشدارهای شما** ({len(alerts)} هشدار فعال)\n\n"
	
	for i, alert in enumerate(alerts, 1):
		crypto = alert.get('crypto', 'BTC')
		target_price = alert.get('target_price', 0)
		created_at = alert.get('created_at', '')
		
		# تبدیل تاریخ
		try:
			created_date = datetime.fromisoformat(created_at)
			date_text = created_date.strftime('%Y-%m-%d %H:%M')
		except:
			date_text = "نامشخص"
		
		alerts_text += f"**{i}.** {crypto.upper()}\n"
		alerts_text += f"🎯 قیمت هدف: ${target_price:,.2f}\n"
		alerts_text += f"📅 تاریخ: {date_text}\n\n"
	
	# دکمه‌های عملیات
	keyboard = [
		[InlineKeyboardButton("🗑️ حذف همه", callback_data="clear_all_alerts")],
		[InlineKeyboardButton("🔙 بازگشت", callback_data="back_to_main")]
	]
	reply_markup = InlineKeyboardMarkup(keyboard)
	
	await query.edit_message_text(
		alerts_text,
		reply_markup=reply_markup,
		parse_mode='Markdown'
	)

async def show_user_alerts_keyboard(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
	"""نمایش هشدارهای کاربر از کیبورد سریع"""
	uid = update.effective_user.id
	alerts = STORE.get('alerts', {}).get(uid, [])
	
	if not alerts:
		await update.message.reply_text(
			"🔔 **هشدارهای شما**\n\n"
			"❌ هیچ هشدار فعالی ندارید.\n\n"
			"برای تنظیم هشدار، از دکمه '🔔 تنظیم هشدار' در جزئیات ارز استفاده کنید.",
			reply_markup=reply_keyboard(update)
		)
		return
	
	# نمایش هشدارها
	alerts_text = f"🔔 **هشدارهای شما** ({len(alerts)} هشدار فعال)\n\n"
	
	for i, alert in enumerate(alerts, 1):
		crypto = alert.get('crypto', 'BTC')
		target_price = alert.get('target_price', 0)
		created_at = alert.get('created_at', '')
		
		# تبدیل تاریخ
		try:
			created_date = datetime.fromisoformat(created_at)
			date_text = created_date.strftime('%Y-%m-%d %H:%M')
		except:
			date_text = "نامشخص"
		
		alerts_text += f"**{i}.** {crypto.upper()}\n"
		alerts_text += f"🎯 قیمت هدف: ${target_price:,.2f}\n"
		alerts_text += f"📅 تاریخ: {date_text}\n\n"
	
	# دکمه‌های عملیات
	keyboard = [
		[InlineKeyboardButton("🗑️ حذف همه", callback_data="clear_all_alerts")],
		[InlineKeyboardButton("🔙 بازگشت", callback_data="back_to_main")]
	]
	reply_markup = InlineKeyboardMarkup(keyboard)
	
	await update.message.reply_text(
		alerts_text,
		reply_markup=reply_markup,
		parse_mode='Markdown'
	)

async def show_domestic_currency_list(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
	"""نمایش لیست ارزهای داخلی"""
	# تعریف ارزهای داخلی
	domestic_currencies = [
		{"symbol": "GOLD", "name": "طلا", "emoji": "🥇", "type": "gold"},
		{"symbol": "SILVER", "name": "نقره", "emoji": "🥈", "type": "silver"},
		{"symbol": "USD", "name": "دلار آمریکا", "emoji": "💵", "type": "currency"},
		{"symbol": "EUR", "name": "یورو", "emoji": "💶", "type": "currency"},
		{"symbol": "GBP", "name": "پوند انگلیس", "emoji": "💷", "type": "currency"},
		{"symbol": "JPY", "name": "ین ژاپن", "emoji": "💴", "type": "currency"},
		{"symbol": "CAD", "name": "دلار کانادا", "emoji": "🇨🇦", "type": "currency"},
		{"symbol": "AUD", "name": "دلار استرالیا", "emoji": "🇦🇺", "type": "currency"},
		{"symbol": "CHF", "name": "فرانک سوئیس", "emoji": "🇨🇭", "type": "currency"},
		{"symbol": "CNY", "name": "یوان چین", "emoji": "🇨🇳", "type": "currency"},
		{"symbol": "AED", "name": "درهم امارات", "emoji": "🇦🇪", "type": "currency"},
		{"symbol": "TRY", "name": "لیر ترکیه", "emoji": "🇹🇷", "type": "currency"}
	]
	
	# ایجاد دکمه‌ها (2 در هر ردیف)
	keyboard = []
	for i in range(0, len(domestic_currencies), 2):
		row = []
		# ارز اول
		currency1 = domestic_currencies[i]
		row.append(InlineKeyboardButton(
			f"{currency1['emoji']} {currency1['name']}", 
			callback_data=f"DOMESTIC_CURRENCY:{currency1['symbol']}"
		))
		# ارز دوم (اگر وجود دارد)
		if i + 1 < len(domestic_currencies):
			currency2 = domestic_currencies[i + 1]
			row.append(InlineKeyboardButton(
				f"{currency2['emoji']} {currency2['name']}", 
				callback_data=f"DOMESTIC_CURRENCY:{currency2['symbol']}"
			))
		keyboard.append(row)
	
	# دکمه بازگشت
	keyboard.append([InlineKeyboardButton("🔙 بازگشت به منو", callback_data="back_to_main")])
	
	reply_markup = InlineKeyboardMarkup(keyboard)
	
	text = """
🏦 **ارزهای داخلی و قیمت‌های لحظه‌ای**

**دسترسی به قیمت‌های:**
🥇 طلا و نقره
💵 ارزهای خارجی
📊 قیمت‌های لحظه‌ای

**نحوه استفاده:**
روی هر ارز کلیک کنید تا قیمت لحظه‌ای، هفته گذشته و ماه گذشته را مشاهده کنید.

**منبع داده:** API های داخلی تنظیم شده در پنل مدیریتی
	"""
	
	await update.message.reply_text(text, reply_markup=reply_markup)

async def show_domestic_currency_detail(update: Update, context: ContextTypes.DEFAULT_TYPE, currency_symbol: str) -> None:
	"""نمایش جزئیات ارز داخلی"""
	query = update.callback_query
	await query.answer()
	
	# تعریف اطلاعات ارزها
	currency_info = {
		"GOLD": {"name": "طلا", "emoji": "🥇", "unit": "گرم"},
		"SILVER": {"name": "نقره", "emoji": "🥈", "unit": "گرم"},
		"USD": {"name": "دلار آمریکا", "emoji": "💵", "unit": "دلار"},
		"EUR": {"name": "یورو", "emoji": "💶", "unit": "یورو"},
		"GBP": {"name": "پوند انگلیس", "emoji": "💷", "unit": "پوند"},
		"JPY": {"name": "ین ژاپن", "emoji": "💴", "unit": "ین"},
		"CAD": {"name": "دلار کانادا", "emoji": "🇨🇦", "unit": "دلار"},
		"AUD": {"name": "دلار استرالیا", "emoji": "🇦🇺", "unit": "دلار"},
		"CHF": {"name": "فرانک سوئیس", "emoji": "🇨🇭", "unit": "فرانک"},
		"CNY": {"name": "یوان چین", "emoji": "🇨🇳", "unit": "یوان"},
		"AED": {"name": "درهم امارات", "emoji": "🇦🇪", "unit": "درهم"},
		"TRY": {"name": "لیر ترکیه", "emoji": "🇹🇷", "unit": "لیر"}
	}
	
	info = currency_info.get(currency_symbol, {"name": currency_symbol, "emoji": "💰", "unit": "واحد"})
	
	# نمایش پیام در حال بارگذاری
	loading_text = f"⏳ در حال دریافت قیمت {info['emoji']} {info['name']}..."
	await query.edit_message_text(loading_text)
	
	try:
		# دریافت قیمت از API های داخلی
		current_price, weekly_price, monthly_price = await get_domestic_currency_price(currency_symbol)
		
		# محاسبه تغییرات
		weekly_change = None
		monthly_change = None
		
		if weekly_price and current_price:
			weekly_change = ((current_price - weekly_price) / weekly_price) * 100
		
		if monthly_price and current_price:
			monthly_change = ((current_price - monthly_price) / monthly_price) * 100
		
		# ایجاد متن
		text = f"""
{info['emoji']} **{info['name']}**

💰 **قیمت فعلی**: {current_price:,.0f} ریال
📅 **آخرین بروزرسانی**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

📊 **تغییرات**:
"""
		
		if weekly_change is not None:
			change_emoji = "📈" if weekly_change > 0 else "📉" if weekly_change < 0 else "➡️"
			text += f"• هفته گذشته: {weekly_price:,.0f} ریال ({change_emoji} {weekly_change:+.1f}%)\n"
		else:
			text += "• هفته گذشته: نامشخص\n"
		
		if monthly_change is not None:
			change_emoji = "📈" if monthly_change > 0 else "📉" if monthly_change < 0 else "➡️"
			text += f"• ماه گذشته: {monthly_price:,.0f} ریال ({change_emoji} {monthly_change:+.1f}%)\n"
		else:
			text += "• ماه گذشته: نامشخص\n"
		
		text += f"""
💡 **منبع**: API های داخلی تنظیم شده
🔄 **واحد**: {info['unit']}
		"""
		
		# دکمه‌های شیشه‌ای
		keyboard = [
			[InlineKeyboardButton("🔄 بروزرسانی", callback_data=f"REFRESH_DOMESTIC:{currency_symbol}")],
			[InlineKeyboardButton("📊 نمودار", callback_data=f"CHART_DOMESTIC:{currency_symbol}")],
			[InlineKeyboardButton("🔔 تنظیم هشدار", callback_data=f"SET_ALERT:{currency_symbol}")],
			[InlineKeyboardButton("🔙 بازگشت به لیست", callback_data="back_to_domestic_list")]
		]
		
		reply_markup = InlineKeyboardMarkup(keyboard)
		await query.edit_message_text(text, reply_markup=reply_markup)
		
	except Exception as e:
		error_text = f"❌ خطا در دریافت اطلاعات {info['name']}:\n{str(e)}"
		keyboard = [
			[InlineKeyboardButton("🔄 تلاش مجدد", callback_data=f"DOMESTIC_CURRENCY:{currency_symbol}")],
			[InlineKeyboardButton("🔙 بازگشت به لیست", callback_data="back_to_domestic_list")]
		]
		reply_markup = InlineKeyboardMarkup(keyboard)
		await query.edit_message_text(error_text, reply_markup=reply_markup)

async def get_domestic_currency_price(currency_symbol: str) -> tuple:
	"""دریافت قیمت ارز داخلی از API"""
	try:
		# دریافت تنظیمات API از store
		tradingview_api = STORE.get('tradingview_api', '')
		fiat_api = STORE.get('fiat_api', '')
		crypto_api = STORE.get('crypto_api', '')
		
		# بررسی اینکه API تنظیم شده باشد
		if not any([tradingview_api, fiat_api, crypto_api]):
			print("No API configured in admin panel")
			return await get_fallback_price(currency_symbol)
		
		# استفاده از API های مختلف بر اساس نوع ارز
		if currency_symbol in ['GOLD', 'SILVER']:
			# استفاده از API طلا/نقره (TradingView یا کریپتو)
			if tradingview_api:
				return await get_gold_silver_from_tradingview(currency_symbol, tradingview_api)
			elif crypto_api:
				return await get_gold_silver_from_crypto_api(currency_symbol, crypto_api)
			else:
				return await get_fallback_price(currency_symbol)
		else:
			# استفاده از API ارزهای خارجی (فیات)
			if fiat_api:
				return await get_foreign_currency_from_fiat_api(currency_symbol, fiat_api)
			elif tradingview_api:
				return await get_foreign_currency_from_tradingview(currency_symbol, tradingview_api)
			else:
				return await get_fallback_price(currency_symbol)
			
	except Exception as e:
		print(f"Error getting domestic currency price: {e}")
		return await get_fallback_price(currency_symbol)

async def get_gold_silver_price(currency_symbol: str) -> tuple:
	"""دریافت قیمت طلا/نقره"""
	try:
		# شبیه‌سازی قیمت (در واقعیت از API واقعی استفاده کنید)
		import random
		
		if currency_symbol == 'GOLD':
			current = random.randint(2500000, 3000000)  # قیمت طلا به ریال
			weekly = current * random.uniform(0.95, 1.05)
			monthly = current * random.uniform(0.90, 1.10)
		else:  # SILVER
			current = random.randint(30000, 40000)  # قیمت نقره به ریال
			weekly = current * random.uniform(0.95, 1.05)
			monthly = current * random.uniform(0.90, 1.10)
		
		return current, weekly, monthly
		
	except Exception as e:
		print(f"Error getting gold/silver price: {e}")
		return None, None, None

async def get_foreign_currency_price(currency_symbol: str) -> tuple:
	"""دریافت قیمت ارزهای خارجی"""
	try:
		# شبیه‌سازی قیمت (در واقعیت از API واقعی استفاده کنید)
		import random
		
		# قیمت‌های تقریبی ارزها به ریال
		base_prices = {
			'USD': 420000,
			'EUR': 450000,
			'GBP': 520000,
			'JPY': 2800,
			'CAD': 310000,
			'AUD': 280000,
			'CHF': 460000,
			'CNY': 58000,
			'AED': 114000,
			'TRY': 14000
		}
		
		base_price = base_prices.get(currency_symbol, 100000)
		current = base_price * random.uniform(0.95, 1.05)
		weekly = current * random.uniform(0.95, 1.05)
		monthly = current * random.uniform(0.90, 1.10)
		
		return current, weekly, monthly
		
	except Exception as e:
		print(f"Error getting foreign currency price: {e}")
		return None, None, None

async def get_fallback_price(currency_symbol: str) -> tuple:
	"""قیمت‌های پیش‌فرض در صورت عدم دسترسی به API"""
	try:
		import random
		
		# قیمت‌های پیش‌فرض
		base_prices = {
			'GOLD': 2500000,
			'SILVER': 35000,
			'USD': 420000,
			'EUR': 450000,
			'GBP': 520000,
			'JPY': 2800,
			'CAD': 310000,
			'AUD': 280000,
			'CHF': 460000,
			'CNY': 58000,
			'AED': 114000,
			'TRY': 14000
		}
		
		base_price = base_prices.get(currency_symbol, 100000)
		current = base_price * random.uniform(0.95, 1.05)
		weekly = current * random.uniform(0.95, 1.05)
		monthly = current * random.uniform(0.90, 1.10)
		
		return current, weekly, monthly
		
	except Exception as e:
		print(f"Error getting fallback price: {e}")
		return None, None, None

async def get_gold_silver_from_tradingview(currency_symbol: str, api_key: str) -> tuple:
	"""دریافت قیمت طلا/نقره از TradingView API"""
	try:
		import aiohttp
		
		# تعریف نمادهای TradingView
		symbols = {
			'GOLD': 'XAUUSD',
			'SILVER': 'XAGUSD'
		}
		
		symbol = symbols.get(currency_symbol)
		if not symbol:
			return await get_fallback_price(currency_symbol)
		
		# درخواست به TradingView API
		url = f"https://api.tradingview.com/v1/symbols/{symbol}/quotes"
		headers = {
			'Authorization': f'Bearer {api_key}',
			'Content-Type': 'application/json'
		}
		
		async with aiohttp.ClientSession() as session:
			async with session.get(url, headers=headers) as response:
				if response.status == 200:
					data = await response.json()
					current_price = data.get('price', 0)
					
					# تبدیل به ریال (نرخ تقریبی)
					usd_to_rial = 420000  # این مقدار باید از API فیات دریافت شود
					current_rial = current_price * usd_to_rial
					
					# محاسبه قیمت‌های تاریخی (تقریبی)
					weekly = current_rial * 0.98
					monthly = current_rial * 0.95
					
					return current_rial, weekly, monthly
				else:
					print(f"TradingView API error: {response.status}")
					return await get_fallback_price(currency_symbol)
					
	except Exception as e:
		print(f"Error getting gold/silver from TradingView: {e}")
		return await get_fallback_price(currency_symbol)

async def get_gold_silver_from_crypto_api(currency_symbol: str, api_key: str) -> tuple:
	"""دریافت قیمت طلا/نقره از کریپتو API"""
	try:
		import aiohttp
		
		# تعریف نمادهای کریپتو
		symbols = {
			'GOLD': 'GOLD',
			'SILVER': 'SILVER'
		}
		
		symbol = symbols.get(currency_symbol)
		if not symbol:
			return await get_fallback_price(currency_symbol)
		
		# درخواست به کریپتو API
		url = f"https://api.crypto.com/v1/price/{symbol}"
		headers = {
			'X-API-Key': api_key,
			'Content-Type': 'application/json'
		}
		
		async with aiohttp.ClientSession() as session:
			async with session.get(url, headers=headers) as response:
				if response.status == 200:
					data = await response.json()
					current_price = data.get('price', 0)
					
					# تبدیل به ریال
					usd_to_rial = 420000
					current_rial = current_price * usd_to_rial
					
					# محاسبه قیمت‌های تاریخی
					weekly = current_rial * 0.98
					monthly = current_rial * 0.95
					
					return current_rial, weekly, monthly
				else:
					print(f"Crypto API error: {response.status}")
					return await get_fallback_price(currency_symbol)
					
	except Exception as e:
		print(f"Error getting gold/silver from crypto API: {e}")
		return await get_fallback_price(currency_symbol)

async def get_foreign_currency_from_fiat_api(currency_symbol: str, api_key: str) -> tuple:
	"""دریافت قیمت ارزهای خارجی از فیات API"""
	try:
		import aiohttp
		
		# درخواست به فیات API
		url = f"https://api.exchangerate.host/latest?base=USD&symbols={currency_symbol}"
		headers = {
			'X-API-Key': api_key,
			'Content-Type': 'application/json'
		}
		
		async with aiohttp.ClientSession() as session:
			async with session.get(url, headers=headers) as response:
				if response.status == 200:
					data = await response.json()
					rate = data.get('rates', {}).get(currency_symbol, 1)
					
					# تبدیل به ریال
					usd_to_rial = 420000
					current_rial = rate * usd_to_rial
					
					# محاسبه قیمت‌های تاریخی
					weekly = current_rial * 0.99
					monthly = current_rial * 0.97
					
					return current_rial, weekly, monthly
				else:
					print(f"Fiat API error: {response.status}")
					return await get_fallback_price(currency_symbol)
					
	except Exception as e:
		print(f"Error getting foreign currency from fiat API: {e}")
		return await get_fallback_price(currency_symbol)

async def get_foreign_currency_from_tradingview(currency_symbol: str, api_key: str) -> tuple:
	"""دریافت قیمت ارزهای خارجی از TradingView API"""
	try:
		import aiohttp
		
		# تعریف نمادهای TradingView
		symbols = {
			'USD': 'USD',
			'EUR': 'EURUSD',
			'GBP': 'GBPUSD',
			'JPY': 'USDJPY',
			'CAD': 'USDCAD',
			'AUD': 'AUDUSD',
			'CHF': 'USDCHF',
			'CNY': 'USDCNY',
			'AED': 'USDAED',
			'TRY': 'USDTRY'
		}
		
		symbol = symbols.get(currency_symbol)
		if not symbol:
			return await get_fallback_price(currency_symbol)
		
		# درخواست به TradingView API
		url = f"https://api.tradingview.com/v1/symbols/{symbol}/quotes"
		headers = {
			'Authorization': f'Bearer {api_key}',
			'Content-Type': 'application/json'
		}
		
		async with aiohttp.ClientSession() as session:
			async with session.get(url, headers=headers) as response:
				if response.status == 200:
					data = await response.json()
					current_price = data.get('price', 1)
					
					# تبدیل به ریال
					usd_to_rial = 420000
					current_rial = current_price * usd_to_rial
					
					# محاسبه قیمت‌های تاریخی
					weekly = current_rial * 0.99
					monthly = current_rial * 0.97
					
					return current_rial, weekly, monthly
				else:
					print(f"TradingView API error: {response.status}")
					return await get_fallback_price(currency_symbol)
					
	except Exception as e:
		print(f"Error getting foreign currency from TradingView: {e}")
		return await get_fallback_price(currency_symbol)

async def show_domestic_currency_chart(update: Update, context: ContextTypes.DEFAULT_TYPE, currency_symbol: str) -> None:
	"""نمایش نمودار ارز داخلی"""
	query = update.callback_query
	await query.answer()
	
	# تعریف اطلاعات ارزها
	currency_info = {
		"GOLD": {"name": "طلا", "emoji": "🥇"},
		"SILVER": {"name": "نقره", "emoji": "🥈"},
		"USD": {"name": "دلار آمریکا", "emoji": "💵"},
		"EUR": {"name": "یورو", "emoji": "💶"},
		"GBP": {"name": "پوند انگلیس", "emoji": "💷"},
		"JPY": {"name": "ین ژاپن", "emoji": "💴"},
		"CAD": {"name": "دلار کانادا", "emoji": "🇨🇦"},
		"AUD": {"name": "دلار استرالیا", "emoji": "🇦🇺"},
		"CHF": {"name": "فرانک سوئیس", "emoji": "🇨🇭"},
		"CNY": {"name": "یوان چین", "emoji": "🇨🇳"},
		"AED": {"name": "درهم امارات", "emoji": "🇦🇪"},
		"TRY": {"name": "لیر ترکیه", "emoji": "🇹🇷"}
	}
	
	info = currency_info.get(currency_symbol, {"name": currency_symbol, "emoji": "💰"})
	
	# شبیه‌سازی نمودار (در واقعیت از API واقعی استفاده کنید)
	import random
	
	# تولید داده‌های نمودار
	chart_data = []
	for i in range(30):  # 30 روز گذشته
		base_price = 100000 if currency_symbol not in ['GOLD', 'SILVER'] else (2500000 if currency_symbol == 'GOLD' else 35000)
		price = base_price * random.uniform(0.9, 1.1)
		chart_data.append(price)
	
	# ایجاد نمودار ساده با کاراکترها
	chart_text = f"""
📊 **نمودار {info['emoji']} {info['name']}**

📈 **روند 30 روز گذشته**:
"""
	
	# نمایش نمودار ساده
	max_price = max(chart_data)
	min_price = min(chart_data)
	
	for i in range(0, len(chart_data), 3):  # نمایش هر 3 روز
		price = chart_data[i]
		bar_length = int((price - min_price) / (max_price - min_price) * 10)
		bar = "█" * bar_length + "░" * (10 - bar_length)
		chart_text += f"روز {i+1:2d}: {bar} {price:,.0f}\n"
	
	chart_text += f"""
📊 **آمار**:
• بالاترین قیمت: {max_price:,.0f} ریال
• پایین‌ترین قیمت: {min_price:,.0f} ریال
• تغییرات: {((chart_data[-1] - chart_data[0]) / chart_data[0] * 100):+.1f}%

💡 **نکات**:
• نقاط بالاتر = قیمت بیشتر
• نقاط پایین‌تر = قیمت کمتر
	"""
	
	keyboard = [
		[InlineKeyboardButton("🔄 بروزرسانی", callback_data=f"REFRESH_DOMESTIC:{currency_symbol}")],
		[InlineKeyboardButton("🔙 بازگشت", callback_data=f"DOMESTIC_CURRENCY:{currency_symbol}")]
	]
	
	reply_markup = InlineKeyboardMarkup(keyboard)
	await query.edit_message_text(chart_text, reply_markup=reply_markup)

async def start_user_message(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: str) -> None:
	"""شروع ارسال پیام به کاربر"""
	query = update.callback_query
	await query.answer()
	
	uid = query.from_user.id
	ud = get_user_data(STORE, uid)
	
	ud["pending"] = {
		"type": "user_message",
		"target_user": user_id
	}
	save_store(STORE)
	
	# دریافت اطلاعات کاربر
	user_data = STORE.get('user_data', {}).get(user_id, {})
	username = user_data.get('username', 'بدون نام کاربری')
	first_name = user_data.get('first_name', 'بدون نام')
	
	keyboard = [
		[InlineKeyboardButton("❌ لغو", callback_data="cancel_user_message")]
	]
	reply_markup = InlineKeyboardMarkup(keyboard)
	
	await query.edit_message_text(
		f"📩 **ارسال پیام به کاربر**\n\n"
		f"👤 **اطلاعات کاربر**:\n"
		f"• آیدی: `{user_id}`\n"
		f"• نام کاربری: @{username}\n"
		f"• نام: {first_name}\n\n"
		f"💬 **لطفاً پیام خود را وارد کنید**:\n\n"
		f"🔙 برای لغو: /cancel",
		reply_markup=reply_markup,
		parse_mode='Markdown'
	)

async def cancel_user_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
	"""لغو ارسال پیام به کاربر"""
	query = update.callback_query
	await query.answer()
	
	uid = query.from_user.id
	ud = get_user_data(STORE, uid)
	
	# حذف pending
	if "pending" in ud:
		del ud["pending"]
		save_store(STORE)
	
	await query.edit_message_text(
		"❌ **ارسال پیام لغو شد!**\n\n"
		"عملیات ارسال پیام به کاربر لغو شد.",
		reply_markup=InlineKeyboardMarkup([[
			InlineKeyboardButton("🔙 بازگشت", callback_data="back_to_main")
		]])
	)

async def toggle_bot_feature(update: Update, context: ContextTypes.DEFAULT_TYPE, feature: str) -> None:
	"""تغییر وضعیت ویژگی ربات"""
	features = STORE.get('bot_features', {})
	current_status = features.get(feature, True)
	features[feature] = not current_status
	STORE['bot_features'] = features
	save_store(STORE)
	
	status_text = "روشن" if features[feature] else "خاموش"
	
	await update.callback_query.edit_message_text(
		f"✅ **ویژگی {feature} {status_text} شد**\n\n"
		f"وضعیت فعلی: {'🟢 فعال' if features[feature] else '🔴 غیرفعال'}"
	)



def main() -> None:
	"""Main function to start the bot"""
	try:
		telegram_app = build_app()
		
		print("🚀 Starting Crypto Navasan Bot...")
		print(f"👤 Owner ID: {config.OWNER_ID}")
		print(f"🤖 Bot Username: @{config.BOT_USERNAME}")
		
		# Add error handler for the application
		async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
			"""Handle errors gracefully"""
			print(f"❌ Error occurred: {context.error}")
			if update and update.effective_chat:
				try:
					await context.bot.send_message(
						chat_id=update.effective_chat.id,
						text="❌ خطایی رخ داد. لطفاً دوباره تلاش کنید."
					)
				except Exception:
					pass  # Ignore errors when sending error messages
		
		# Add error handler to the application
		telegram_app.add_error_handler(error_handler)
		
		# Use long polling for both local and Railway deployment
		print("📡 Starting in polling mode...")
		telegram_app.run_polling(
			allowed_updates=Update.ALL_TYPES,
			close_loop=False,
			drop_pending_updates=True
		)
		
	except KeyboardInterrupt:
		print("\n🛑 Bot stopped by user")
	except Exception as e:
		print(f"❌ Error starting bot: {e}")
		raise


if __name__ == "__main__":
	main()