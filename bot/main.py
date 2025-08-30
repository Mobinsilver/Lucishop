import os
import asyncio
from typing import Optional, List, Tuple

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
from admin_panel import admin_panel
from crypto_list import show_crypto_list, show_crypto_detail, refresh_crypto_price, show_crypto_chart
import config

# Admin panel states
ADMIN_PANEL, ADD_ADMIN, BROADCAST_MESSAGE, SET_WELCOME_TEXT = range(4)


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
		[KeyboardButton("🛠 تنظیمات"), KeyboardButton("❓ راهنما")]
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
			BROADCAST_MESSAGE: [
				MessageHandler(filters.ALL, admin_panel.broadcast_message_process),
				CommandHandler("cancel", admin_panel.cancel)
			],
			SET_WELCOME_TEXT: [
				MessageHandler(filters.TEXT & ~filters.COMMAND, admin_panel.set_welcome_text_process),
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