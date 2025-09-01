
import os
import asyncio
from typing import Optional, List, Tuple
from datetime import datetime

from dotenv import load_dotenv
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
    ADD_FORCE_SUB_CHANNEL, ADD_WHITELIST, ADD_BLACKLIST, USER_MESSAGE
)
from crypto_list import show_crypto_list, show_crypto_detail, refresh_crypto_price, show_crypto_chart
import config


load_dotenv()
BOT_TOKEN = config.TELEGRAM_BOT_TOKEN
STORE = load_store()
CACHE = TTLCache()


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


def get_help_text(user_id: int) -> str:
	ud = get_user_data(STORE, user_id)
	lang = ud.get("settings", {}).get("language", "FA")
	if lang == "EN":
		return "Choose an option:"
	elif lang == "AR":
		return "اختر خياراً:"
	else:
		return "گزینه مورد نظر را انتخاب کنید:"


def reply_keyboard(update: Update = None) -> ReplyKeyboardMarkup:
	keyboard = [
		[KeyboardButton("💰 قیمت ارز"), KeyboardButton("💱 نرخ ارز")],
		[KeyboardButton("📰 اخبار"), KeyboardButton("📊 نمودار")],
		[KeyboardButton("📈 تحلیل تکنیکال"), KeyboardButton("⚖️ مقایسه")],
		[KeyboardButton("🔄 P2P"), KeyboardButton("👁 واچ‌لیست")],
		[KeyboardButton("📚 پرتفوی"), KeyboardButton("🔔 هشدارها")],
		[KeyboardButton("🛠 تنظیمات"), KeyboardButton("❓ راهنما")],
		[KeyboardButton("📝 تنظیم متن‌ها")],
		[KeyboardButton("📊 آمار و گزارش")]
	]
	
	# اضافه کردن دکمه پنل مدیریتی برای مالک
	from config import OWNER_ID
	if update and update.effective_user and update.effective_user.id == OWNER_ID:
		keyboard.append([KeyboardButton("🔐 پنل مدیریتی")])
	
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


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
	user = update.effective_user
	uid = user.id
	
	# check black/white list
	allowed, reason = check_black_white(uid)
	if not allowed:
		if reason == "blacklisted":
			await update.message.reply_text("دسترسی شما مسدود شده است.")
		else:
			await update.message.reply_text("دسترسی شما محدود است.")
		return
	
	# rate limit
	ok, reason = touch_rate_limit(uid)
	if not ok:
		await update.message.reply_text("لطفا کمی بعد دوباره تلاش کنید.")
		return
	
	if uid not in set(STORE.get("users", [])):
		STORE.setdefault("users", []).append(uid)
		save_store(STORE)
	
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
	
	await update.message.reply_text(get_help_text(user.id), reply_markup=reply_keyboard(update))
	await update.message.reply_text(help_text_by_lang(ud.get("settings", {}).get("language", "FA")))


async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
	await update.message.reply_text(get_help_text(update.effective_user.id), reply_markup=reply_keyboard(update))

async def admin_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
	"""دستور پنل مدیریتی"""
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


async def show_text_settings(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
	"""تنظیم متن‌های ربات"""
	uid = update.effective_user.id
	
	# فقط مالک می‌تواند متن‌ها را تنظیم کند
	from config import OWNER_ID
	if uid != OWNER_ID:
		await update.message.reply_text("❌ فقط مالک ربات می‌تواند متن‌ها را تنظیم کند!")
		return
	
	keyboard = [
		[InlineKeyboardButton("👋 متن خوش‌آمدگویی", callback_data="set_welcome")],
		[InlineKeyboardButton("❓ متن راهنما", callback_data="set_help")],
		[InlineKeyboardButton("⚠️ متن خطا", callback_data="set_error")],
		[InlineKeyboardButton("📝 متن درباره", callback_data="set_about")],
		[InlineKeyboardButton("🔒 متن عضویت اجباری", callback_data="set_force_sub")],
		[InlineKeyboardButton("🔙 بازگشت به منو", callback_data="back_to_main")]
	]
	
	reply_markup = InlineKeyboardMarkup(keyboard)
	
	text = """
📝 **تنظیم متن‌های ربات**

**متن‌های قابل تنظیم**:
👋 متن خوش‌آمدگویی (/start)
❓ متن راهنما (/help)
⚠️ متن خطاها
📝 متن درباره ربات
🔒 متن عضویت اجباری

لطفاً یکی از گزینه‌ها را انتخاب کنید:
	"""
	
	await update.message.reply_text(text, reply_markup=reply_markup)


async def on_menu_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
	text = update.message.text.strip()
	uid = update.effective_user.id
	
	# check black/white list
	allowed, reason = check_black_white(uid)
	if not allowed:
		return
	
	# rate limit
	ok, reason = touch_rate_limit(uid)
	if not ok:
		return
	
	# Handle menu buttons
	if text == "💰 قیمت ارز":
		await show_crypto_list(update, context)
		return
	elif text == "💱 نرخ ارز":
		await update.message.reply_text("لطفا کد ارز مورد نظر را وارد کنید (مثل: EUR, GBP, JPY)")
		ud = get_user_data(STORE, uid)
		ud["pending"] = {"type": "fiat_input"}
		save_store(STORE)
		return
	elif text == "📰 اخبار":
		await update.message.reply_text("لطفا نماد ارز مورد نظر را وارد کنید (مثل: btc, eth) یا Enter بزنید برای اخبار عمومی")
		ud = get_user_data(STORE, uid)
		ud["pending"] = {"type": "news"}
		save_store(STORE)
		return
	elif text == "📊 نمودار":
		await update.message.reply_text("لطفا نماد ارز مورد نظر را وارد کنید (مثل: btc, eth)")
		ud = get_user_data(STORE, uid)
		ud["pending"] = {"type": "chart"}
		save_store(STORE)
		return
	elif text == "📈 تحلیل تکنیکال":
		await update.message.reply_text("لطفا نماد ارز مورد نظر را وارد کنید (مثل: btc, eth)")
		ud = get_user_data(STORE, uid)
		ud["pending"] = {"type": "ta"}
		save_store(STORE)
		return
	elif text == "⚖️ مقایسه":
		await update.message.reply_text("لطفا نماد ارز مورد نظر را وارد کنید (مثل: btc, eth)")
		ud = get_user_data(STORE, uid)
		ud["pending"] = {"type": "arb"}
		save_store(STORE)
		return
	elif text == "🔄 P2P":
		await update.message.reply_text("لطفا اطلاعات P2P را وارد کنید (مثل: USDT IRR SELL)")
		ud = get_user_data(STORE, uid)
		ud["pending"] = {"type": "p2p"}
		save_store(STORE)
		return
	elif text == "👁 واچ‌لیست":
		await show_watchlist(update, context)
		return
	elif text == "📚 پرتفوی":
		await show_portfolio(update, context)
		return
	elif text == "🔔 هشدارها":
		await show_alerts(update, context)
		return
	elif text == "🛠 تنظیمات":
		await show_settings(update, context)
		return
	elif text == "❓ راهنما":
		await help_cmd(update, context)
		return
	elif text == "📝 تنظیم متن‌ها":
		await show_text_settings(update, context)
		return
	elif text == "📊 آمار و گزارش":
		await show_stats(update, context)
		return
	elif text == "🔐 پنل مدیریتی":
		await admin_cmd(update, context)
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
	
	data = query.data
	if data.startswith("LANGSEL:"):
		lang = data.split(":")[1]
		ud = get_user_data(STORE, query.from_user.id)
		ud.setdefault("settings", {})["language"] = lang
		save_store(STORE)
		await query.edit_message_text("زبان انتخاب شد. / Language selected. / تم اختيار اللغة.")
		await start(update, context)
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
	elif data.startswith("crypto_detail:"):
		await show_crypto_detail(update, context)
	elif data.startswith("refresh_crypto:"):
		await refresh_crypto_price(update, context)
	elif data.startswith("chart_crypto:"):
		await show_crypto_chart(update, context)
	elif data.startswith("refresh_chart:"):
		await show_crypto_chart(update, context)
	elif data == "back_to_main":
		await query.edit_message_text(
			get_help_text(query.from_user.id),
			reply_markup=reply_keyboard(update)
		)
	elif data == "show_currency_buttons":
		await show_currency_buttons(update, context)
	elif data.startswith("CURRENCY:"):
		currency_code = data.split(":")[1]
		await handle_currency_selection(update, context, currency_code)
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
	app.add_handler(CommandHandler("start", start))
	app.add_handler(CommandHandler("help", help_cmd))
	app.add_handler(CommandHandler("price", price))
	app.add_handler(CommandHandler("admin", admin_cmd))
	
	# Admin panel conversation handler
	admin_conv_handler = ConversationHandler(
		entry_points=[CommandHandler("admin", admin_cmd)],
		states={
			ADMIN_PANEL: [
				CallbackQueryHandler(admin_panel.handle_callback),
				CommandHandler("cancel", admin_panel.cancel)
			],
			ADD_ADMIN: [
				MessageHandler(filters.TEXT & ~filters.COMMAND, admin_panel.add_admin_process),
				CommandHandler("cancel", admin_panel.cancel)
			],
			REMOVE_ADMIN: [
				MessageHandler(filters.TEXT & ~filters.COMMAND, admin_panel.remove_admin_process),
				CommandHandler("cancel", admin_panel.cancel)
			],
			BROADCAST_MESSAGE: [
				MessageHandler(filters.ALL, admin_panel.broadcast_message_process),
				CommandHandler("cancel", admin_panel.cancel)
			],
			BROADCAST_FORWARD: [
				MessageHandler(filters.ALL, admin_panel.broadcast_forward_process),
				CommandHandler("cancel", admin_panel.cancel)
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
	
	# Menus
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
	await update.callback_query.edit_message_text(
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
	
	# نمایش فرم تنظیم هشدار
	await update.callback_query.edit_message_text(
		f"🔔 **تنظیم هشدار برای {crypto_symbol.upper()}**\n\n"
		f"لطفاً قیمت هدف را بر حسب دلار وارد کنید:\n"
		f"مثال: 50000\n\n"
		f"💡 **نکات مهم**:\n"
		f"• قیمت را به دلار وارد کنید\n"
		f"• ربات هنگام رسیدن به قیمت به شما اطلاع می‌دهد\n"
		f"• برای لغو: /cancel",
		parse_mode='Markdown'
	)
	
	# ذخیره وضعیت
	ud["pending"] = {
		"type": "alert_setup",
		"crypto": crypto_symbol
	}
	save_store(STORE)


async def start_user_message(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: str) -> None:
	"""شروع ارسال پیام به کاربر"""
	uid = update.callback_query.from_user.id
	ud = get_user_data(STORE, uid)
	
	ud["pending"] = {
		"type": "user_message",
		"target_user": user_id
	}
	save_store(STORE)
	
	await update.callback_query.edit_message_text(
		f"📩 **ارسال پیام به کاربر {user_id}**\n\n"
		f"لطفاً پیام خود را وارد کنید:\n\n"
		f"🔙 برای لغو: /cancel"
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
	telegram_app = build_app()
	
	print("Bot is running...")
	
	# Check if running on Railway (production) or locally
	port = config.PORT
	webhook_url = config.WEBHOOK_URL
	
	if webhook_url:
		# Production mode with webhook
		print(f"Starting webhook on port {port}")
		telegram_app.run_webhook(
			listen="0.0.0.0",
			port=port,
			webhook_url=webhook_url,
			allowed_updates=Update.ALL_TYPES
		)
	else:
		# Local development mode with polling
		print("Starting in polling mode... Press Ctrl+C to stop")
		telegram_app.run_polling(allowed_updates=Update.ALL_TYPES, close_loop=False)


if __name__ == "__main__":
	main()