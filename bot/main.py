import os
import asyncio
from typing import Optional, List, Tuple

from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, CallbackQueryHandler, MessageHandler, filters
from flask import Flask, request, jsonify
import config

from price_service import get_price_by_symbol, format_price_message, SYMBOL_TO_CG_ID, get_crypto_price_with_provider
from fiat_service import get_fiat_rate, format_fiat_message, FIAT_CODES, get_fiat_rate_with_provider
from news_service import get_news
from history import fetch_history_prices, sparkline
from arbitrage import compare_prices
from p2p_service import fetch_binance_p2p, summarize_p2p_offers
from store import load_store, save_store, is_admin, get_user_data
from cache import TTLCache
from security import check_black_white, touch_rate_limit, start_captcha, verify_captcha
from ta import sma, rsi, macd, simple_support_resistance


load_dotenv()
BOT_TOKEN = config.TELEGRAM_BOT_TOKEN
STORE = load_store()
CACHE = TTLCache()

# Flask app for webhook
app = Flask(__name__)


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
			"أنا روبوت لأسعار العملات الرقمية والfiat بالوقت الحقيقي.\n\n"
			"استخدم أزرار القائمة السريعة أدناه للوصول إلى الميزات."
		)
	# FA default
	return (
		"سلام! 👋\n"
		"من ربات قیمت لحظه‌ای ارزهای دیجیتال و ارزهای فیات هستم.\n\n"
		"برای استفاده از امکانات، از دکمه‌های منوی پایین استفاده کنید."
	)


def get_help_text(user_id: int) -> str:
	ud = get_user_data(STORE, user_id)
	lng = (ud.get("settings", {}) or {}).get("language", "FA")
	return help_text_by_lang(lng)

MENU_CRYPTO = "📊 لیست قیمت ارز دیجیتال"
MENU_FIAT = "💱 قیمت ارزهای فیات"
MENU_ADMIN = "⚙️ مدیریت"
MENU_WATCHLIST = "⭐ واچ‌لیست"
MENU_PORTFOLIO = "📚 پرتفوی"
MENU_ALERTS = "⏰ هشدارها"
MENU_NEWS = "📰 اخبار"
MENU_CHART = "📈 چارت"
MENU_SETTINGS = "🛠 تنظیمات"
MENU_ARB = "🔁 آربیتراژ"
MENU_P2P = "🤝 P2P"
MENU_SIGNALS = "📐 سیگنال‌ها"


def reply_keyboard() -> ReplyKeyboardMarkup:
	keyboard = [
		[KeyboardButton(MENU_CRYPTO), KeyboardButton(MENU_FIAT)],
		[KeyboardButton(MENU_WATCHLIST), KeyboardButton(MENU_PORTFOLIO)],
		[KeyboardButton(MENU_ALERTS), KeyboardButton(MENU_CHART)],
		[KeyboardButton(MENU_NEWS), KeyboardButton(MENU_SETTINGS)],
		[KeyboardButton(MENU_ARB), KeyboardButton(MENU_P2P)],
		[KeyboardButton(MENU_SIGNALS)],
		[KeyboardButton(MENU_ADMIN)],
	]
	return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)


def build_admin_inline() -> InlineKeyboardMarkup:
	buttons: List[List[InlineKeyboardButton]] = []
	buttons.append([
		InlineKeyboardButton(text="🔌 تنظیم پراوایدرها", callback_data="ADMIN:SET_PROVIDER"),
	])
	return InlineKeyboardMarkup(buttons)


def admin_providers_text() -> str:
	prov = STORE.get("providers", {}) or {}
	crypto_p = prov.get("crypto", "coingecko")
	fiat_p = prov.get("fiat", "exchangerate_host")
	return (
		"تنظیمات پراوایدرها:\n"
		f"کریپتو: {crypto_p}\n"
		f"فیات: {fiat_p}\n"
		"یکی را برای تغییر انتخاب کنید:"
	)


def build_admin_providers_inline() -> InlineKeyboardMarkup:
	buttons: List[List[InlineKeyboardButton]] = []
	# Crypto providers
	buttons.append([
		InlineKeyboardButton(text="Coingecko", callback_data="ADMIN:PROV_CRYPTO_COINGECKO"),
		InlineKeyboardButton(text="Binance", callback_data="ADMIN:PROV_CRYPTO_BINANCE"),
	])
	# Fiat providers
	buttons.append([
		InlineKeyboardButton(text="ExchangerateHost", callback_data="ADMIN:PROV_FIAT_EXCHANGERATE_HOST"),
		InlineKeyboardButton(text="Frankfurter", callback_data="ADMIN:PROV_FIAT_FRANKFURTER"),
	])
	buttons.append([
		InlineKeyboardButton(text="⬅️ بازگشت", callback_data="ADMIN:BACK"),
	])
	return InlineKeyboardMarkup(buttons)


def settings_text(user_id: int) -> str:
	ud = get_user_data(STORE, user_id)
	st = ud.get("settings", {}) or {}
	base = st.get("base_fiat", "USD")
	ui = st.get("ui_mode", "compact")
	lng = st.get("language", "FA")
	to_toman = st.get("display_toman", True)
	show_irr = st.get("show_irr", True)
	return (
		"تنظیمات کاربر:\n"
		f"واحد پایه: {base}\n"
		f"نمایش: {('فشرده' if ui=='compact' else 'گرافیکی')}\n"
		f"زبان: {lng}\n"
		f"نمایش تومان: {'بله' if to_toman else 'خیر'}\n"
		f"نمایش ریال ایران: {'بله' if show_irr else 'خیر'}"
	)


def build_settings_inline(user_id: int) -> InlineKeyboardMarkup:
	ud = get_user_data(STORE, user_id)
	st = ud.get("settings", {}) or {}
	base = st.get("base_fiat", "USD")
	ui = st.get("ui_mode", "compact")
	lng = st.get("language", "FA")
	show_irr = st.get("show_irr", True)
	buttons: List[List[InlineKeyboardButton]] = []
	buttons.append([
		InlineKeyboardButton(text=f"واحد پایه: {base}", callback_data="SET:BASE"),
	])
	buttons.append([
		InlineKeyboardButton(text=f"نمایش: {'فشرده' if ui=='compact' else 'گرافیکی'}", callback_data="SET:UI"),
	])
	buttons.append([
		InlineKeyboardButton(text=f"زبان: {lng}", callback_data="SET:LANG"),
	])
	buttons.append([
		InlineKeyboardButton(text="نمایش تومان: تغییر", callback_data="SET:TOMAN"),
	])
	buttons.append([
		InlineKeyboardButton(text=f"نمایش ریال ایران: {'بله' if show_irr else 'خیر'}", callback_data="SET:IRR"),
	])
	return InlineKeyboardMarkup(buttons)


async def ensure_forced_subscription(user_id: int, context: ContextTypes.DEFAULT_TYPE) -> Tuple[bool, Optional[str]]:
	fs = STORE.get("forced_subscription", {}) or {}
	if not fs.get("enabled") or not fs.get("channel_username"):
		return True, None
	channel_username = fs.get("channel_username")
	try:
		member = await context.bot.get_chat_member(chat_id=channel_username, user_id=user_id)
		status = getattr(member, "status", None)
		if status in ("member", "creator", "administrator"):
			return True, None
		else:
			return False, channel_username
	except Exception:
		# If check fails, block access until user joins
		return False, channel_username


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
	user = update.effective_user
	if user:
		uid = user.id
		# blacklist/whitelist
		ok, reason = check_black_white(uid)
		if not ok:
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
		# captcha if not passed
		ud = get_user_data(STORE, uid)
		if not ud.get("captcha", {}).get("passed"):
			q = start_captcha(uid)
			if q != "passed":
				await update.message.reply_text(f"برای ادامه، مقدار {q} را ارسال کنید.")
				ud["pending"] = {"type": "captcha"}
				save_store(STORE)
				return
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
	await update.message.reply_text(get_help_text(user.id), reply_markup=reply_keyboard())
	await update.message.reply_text(help_text_by_lang(ud.get("settings", {}).get("language", "FA")))


async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
	await update.message.reply_text(get_help_text(update.effective_user.id), reply_markup=reply_keyboard())


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


def build_crypto_inline() -> InlineKeyboardMarkup:
	buttons: List[List[InlineKeyboardButton]] = []
	row: List[InlineKeyboardButton] = []
	for sym in sorted(SYMBOL_TO_CG_ID.keys()):
		row.append(InlineKeyboardButton(text=sym.upper(), callback_data=f"CRYPTO:{sym}"))
		if len(row) == 4:
			buttons.append(row)
			row = []
	if row:
		buttons.append(row)
	return InlineKeyboardMarkup(buttons)


def build_fiat_inline() -> InlineKeyboardMarkup:
	buttons: List[List[InlineKeyboardButton]] = []
	row: List[InlineKeyboardButton] = []
	for code in FIAT_CODES:
		row.append(InlineKeyboardButton(text=code, callback_data=f"FIAT:{code}"))
		if len(row) == 4:
			buttons.append(row)
			row = []
	if row:
		buttons.append(row)
	return InlineKeyboardMarkup(buttons)


async def on_menu_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
	# security checks
	ok, reason = check_black_white(update.effective_user.id)
	if not ok:
		return
	ok, reason = touch_rate_limit(update.effective_user.id)
	if not ok:
		await update.message.reply_text("لطفا کمی بعد دوباره تلاش کنید.")
		return
	allowed, channel = await ensure_forced_subscription(update.effective_user.id, context)
	if not allowed:
		await update.message.reply_text(
			f"برای استفاده، ابتدا عضو کانال {channel} شوید و دوباره تلاش کنید."
		)
		return
	text = (update.message.text or "").strip()
	if text == MENU_CRYPTO:
		await update.message.reply_text("یکی از ارزهای دیجیتال را انتخاب کنید:", reply_markup=build_crypto_inline())
	elif text == MENU_FIAT:
		await update.message.reply_text("یکی از ارزهای فیات را انتخاب کنید:", reply_markup=build_fiat_inline())
	elif text == MENU_WATCHLIST:
		await update.message.reply_text(
			"واچ‌لیست:",
			reply_markup=InlineKeyboardMarkup([
				[InlineKeyboardButton(text="➕ افزودن", callback_data="WL:ADD"), InlineKeyboardButton(text="➖ حذف", callback_data="WL:DEL")],
				[InlineKeyboardButton(text="📋 نمایش", callback_data="WL:SHOW")],
			])
		)
	elif text == MENU_PORTFOLIO:
		await update.message.reply_text(
			"پرتفوی:",
			reply_markup=InlineKeyboardMarkup([
				[InlineKeyboardButton(text="➕ افزودن", callback_data="PF:ADD"), InlineKeyboardButton(text="➖ حذف", callback_data="PF:DEL")],
				[InlineKeyboardButton(text="📊 نمایش", callback_data="PF:SHOW")],
			])
		)
	elif text == MENU_ALERTS:
		await update.message.reply_text(
			"مدیریت هشدارها:",
			reply_markup=InlineKeyboardMarkup([
				[InlineKeyboardButton(text="➕ افزودن هشدار", callback_data="ALERTS:ADD")],
				[InlineKeyboardButton(text="📋 لیست هشدارها", callback_data="ALERTS:LIST")],
			])
		)
	elif text == MENU_CHART:
		await update.message.reply_text(
			"نمایش چارت مینی: نماد را وارد کنید (مثال: btc)",
		)
		ud = get_user_data(STORE, update.effective_user.id)
		ud["pending"] = {"type": "chart"}
		save_store(STORE)
	elif text == MENU_ARB:
		await update.message.reply_text("نماد را برای مقایسه قیمت بین صرافی‌ها ارسال کنید (مثال: btc)")
		ud = get_user_data(STORE, update.effective_user.id)
		ud["pending"] = {"type": "arb"}
		save_store(STORE)
	elif text == MENU_P2P:
		await update.message.reply_text("دریافت نرخ‌های P2P بایننس: به صورت 'USDT IRR SELL' یا خالی برای پیش‌فرض ارسال کنید")
		ud = get_user_data(STORE, update.effective_user.id)
		ud["pending"] = {"type": "p2p"}
		save_store(STORE)
	elif text == MENU_NEWS:
		await update.message.reply_text(
			"اخبار: اگر نماد خاصی مدنظر دارید ارسال کنید (مثال: btc). در غیر این صورت آخرین اخبار نمایش داده می‌شود.")
		ud = get_user_data(STORE, update.effective_user.id)
		ud["pending"] = {"type": "news"}
		save_store(STORE)
	elif text == MENU_SIGNALS:
		await update.message.reply_text("نماد را ارسال کنید تا سیگنال‌های آموزشی (MA/RSI/MACD و S/R) محاسبه شود.")
		ud = get_user_data(STORE, update.effective_user.id)
		ud["pending"] = {"type": "signals"}
		save_store(STORE)
	elif text == MENU_SETTINGS:
		uid = update.effective_user.id
		await update.message.reply_text(
			settings_text(uid),
			reply_markup=build_settings_inline(uid)
		)
	elif text == MENU_ADMIN:
		if not is_admin(update.effective_user.id, STORE):
			await update.message.reply_text("دسترسی ندارید.")
			return
		await update.message.reply_text("پنل مدیریت:", reply_markup=build_admin_inline())
	else:
		# check for pending actions
		ud = get_user_data(STORE, update.effective_user.id)
		pending = (ud or {}).get("pending")
		if not pending:
			return
		ptype = pending.get("type")
		text_in = (update.message.text or "").strip()
		# captcha first
		if ptype == "captcha":
			if verify_captcha(update.effective_user.id, text_in):
				ud.pop("pending", None)
				save_store(STORE)
				await start(update, context)
			else:
				await update.message.reply_text("نادرست بود، دوباره تلاش کنید.")
			return
		if ptype == "chart":
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
		elif ptype == "signals":
			# compute indicators on recent history (7 or 14 days)
			coin_id = SYMBOL_TO_CG_ID.get(text_in.lower())
			if not coin_id:
				await update.message.reply_text("نماد پشتیبانی نمی‌شود.")
				ud.pop("pending", None)
				save_store(STORE)
				return
			series = await fetch_history_prices(coin_id, days=14)
			if not series:
				await update.message.reply_text("داده کافی در دسترس نیست.")
				ud.pop("pending", None)
				save_store(STORE)
				return
			sma7 = sma(series, 7)[-1]
			rsi14 = rsi(series, 14)[-1]
			macd_obj = macd(series)
			macd_v = macd_obj["macd"][-1]
			sig_v = macd_obj["signal"][-1]
			hist_v = macd_obj["hist"][-1]
			sr = simple_support_resistance(series)
			last = series[-1]
			msg = (
				f"سیگنال‌های آموزشی برای {text_in.upper()}\n"
				f"قیمت فعلی: {last:,.4f} USD\n"
				f"SMA(7): {sma7:,.4f}\n"
				f"RSI(14): {rsi14:.2f}\n"
				f"MACD: {macd_v:.4f} | Signal: {sig_v:.4f} | Hist: {hist_v:.4f}\n"
				f"حمایت: {sr['support']:,.4f} | مقاومت: {sr['resistance']:,.4f}"
			)
			await update.message.reply_text(msg)
			ud.pop("pending", None)
			save_store(STORE)
		else:
			return


# --- Watchlist & Portfolio ---

async def show_watchlist(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
	ud = get_user_data(STORE, update.effective_user.id)
	wl = ud.get("watchlist", [])
	if not wl:
		text = "واچ‌لیست خالی است. با /watch_add <symbol> اضافه کنید."
		if update.callback_query:
			await update.callback_query.edit_message_text(text)
		else:
			await update.message.reply_text(text)
		return
	lines = ["⭐ واچ‌لیست:"]
	provider = (STORE.get("providers", {}) or {}).get("crypto", "coingecko")
	for sym in wl[:30]:
		cached = CACHE.get(f"price:{sym.upper()}")
		if cached:
			price_usd, change = cached
			price_txt = await convert_price_for_user(update.effective_user.id, price_usd)
			lines.append(f"{sym.upper()}: {price_txt}")
			continue
		res = await get_crypto_price_with_provider(sym, provider)
		if not res:
			lines.append(f"{sym.upper()}: -")
			continue
		_, p, ch = res
		CACHE.set(f"price:{sym.upper()}", (p, ch), ttl_seconds=30)
		price_txt = await convert_price_for_user(update.effective_user.id, p)
		lines.append(f"{sym.upper()}: {price_txt}")
	text = "\n".join(lines)
	if update.callback_query:
		await update.callback_query.edit_message_text(text)
	else:
		await update.message.reply_text(text)


async def show_portfolio(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
	ud = get_user_data(STORE, update.effective_user.id)
	pf = ud.get("portfolio", [])
	if not pf:
		text = "پرتفوی خالی است. با /pf_add <symbol> <qty> <avg_price_usd> اضافه کنید."
		if update.callback_query:
			await update.callback_query.edit_message_text(text)
		else:
			await update.message.reply_text(text)
		return
	provider = (STORE.get("providers", {}) or {}).get("crypto", "coingecko")
	lines = ["📚 پرتفوی:"]
	total_value = 0.0
	total_cost = 0.0
	for pos in pf:
		sym = pos.get("symbol", "").upper()
		qty = float(pos.get("qty", 0))
		avg_price = float(pos.get("avg_price", 0))
		price_data = CACHE.get(f"price:{sym}")
		if not price_data:
			res = await get_crypto_price_with_provider(sym, provider)
			if res:
				_, price_usd, ch = res
				CACHE.set(f"price:{sym}", (price_usd, ch), ttl_seconds=30)
				price_data = (price_usd, ch)
		price_usd = price_data[0] if price_data else 0.0
		value = qty * price_usd
		cost = qty * avg_price
		pnl = value - cost
		total_value += value
		total_cost += cost
		price_txt = await convert_price_for_user(update.effective_user.id, price_usd)
		val_txt = await convert_price_for_user(update.effective_user.id, value)
		cost_txt = await convert_price_for_user(update.effective_user.id, cost)
		pnl_txt = await convert_price_for_user(update.effective_user.id, pnl)
		lines.append(f"{sym} | مقدار: {qty:g} | خرید (USD): {avg_price:,.4f} | قیمت: {price_txt} | ارزش: {val_txt} | PnL: {pnl_txt}")
	lines.append("—" * 10)
	lines.append(f"ارزش کل: {(await convert_price_for_user(update.effective_user.id, total_value))} | هزینه کل: {(await convert_price_for_user(update.effective_user.id, total_cost))} | PnL کل: {(await convert_price_for_user(update.effective_user.id, total_value - total_cost))}")
	text = "\n".join(lines)
	if update.callback_query:
		await update.callback_query.edit_message_text(text)
	else:
		await update.message.reply_text(text)


async def watch_add(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
	args = context.args or []
	if not args:
		await update.message.reply_text("استفاده: /watch_add <symbol>")
		return
	ud = get_user_data(STORE, update.effective_user.id)
	sym = args[0].strip().lower()
	if sym not in ud.setdefault("watchlist", []):
		ud["watchlist"].append(sym)
		save_store(STORE)
	await update.message.reply_text("به واچ‌لیست اضافه شد.")


async def watch_del(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
	args = context.args or []
	if not args:
		await update.message.reply_text("استفاده: /watch_del <symbol>")
		return
	ud = get_user_data(STORE, update.effective_user.id)
	sym = args[0].strip().lower()
	ud["watchlist"] = [s for s in ud.get("watchlist", []) if s != sym]
	save_store(STORE)
	await update.message.reply_text("از واچ‌لیست حذف شد.")


async def watch_list_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
	await show_watchlist(update, context)


async def pf_add(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
	args = context.args or []
	if len(args) < 3:
		await update.message.reply_text("استفاده: /pf_add <symbol> <qty> <avg_price_usd>")
		return
	ud = get_user_data(STORE, update.effective_user.id)
	sym = args[0].strip().lower()
	qty = float(args[1])
	avg = float(args[2])
	ud.setdefault("portfolio", []).append({"symbol": sym, "qty": qty, "avg_price": avg})
	save_store(STORE)
	await update.message.reply_text("به پرتفوی اضافه شد.")


async def pf_del(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
	args = context.args or []
	if len(args) < 1:
		await update.message.reply_text("استفاده: /pf_del <symbol>")
		return
	ud = get_user_data(STORE, update.effective_user.id)
	sym = args[0].strip().lower()
	ud["portfolio"] = [p for p in ud.get("portfolio", []) if p.get("symbol") != sym]
	save_store(STORE)
	await update.message.reply_text("از پرتفوی حذف شد.")


async def pf_show_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
	await show_portfolio(update, context)


# --- Alerts ---

async def alert_add(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
	args = context.args or []
	if len(args) < 3:
		await update.message.reply_text("استفاده: /alert_add <symbol> <type: above|below|pct> <value>")
		return
	ud = get_user_data(STORE, update.effective_user.id)
	symbol = args[0].strip().lower()
	atype = args[1].strip().lower()
	value = float(args[2])
	ud.setdefault("alerts", []).append({"symbol": symbol, "type": atype, "value": value})
	save_store(STORE)
	await update.message.reply_text("هشدار ثبت شد.")


async def alert_list(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
	ud = get_user_data(STORE, update.effective_user.id)
	al = ud.get("alerts", [])
	if not al:
		await update.message.reply_text("هشداری ثبت نشده است.")
		return
	lines = ["⏰ هشدارها:"]
	for a in al:
		lines.append(f"{a['symbol'].upper()} {a['type']} {a['value']}")
	await update.message.reply_text("\n".join(lines))


async def alert_del(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
	args = context.args or []
	if len(args) < 2:
		await update.message.reply_text("استفاده: /alert_del <symbol> <index>")
		return
	ud = get_user_data(STORE, update.effective_user.id)
	sym = args[0].strip().lower()
	idx = int(args[1])
	alerts = [a for a in ud.get("alerts", []) if a.get("symbol") == sym]
	if not alerts or idx < 0 or idx >= len(alerts):
		await update.message.reply_text("مورد یافت نشد.")
		return
	# remove idx-th for that symbol
	count = -1
	new_list = []
	for a in ud.get("alerts", []):
		if a.get("symbol") == sym:
			count += 1
			if count == idx:
				continue
		new_list.append(a)
	ud["alerts"] = new_list
	save_store(STORE)
	await update.message.reply_text("حذف شد.")


# background alert checker (polling loop)
async def alert_checker(app):
	while True:
		try:
			provider = (STORE.get("providers", {}) or {}).get("crypto", "coingecko")
			user_data = STORE.get("user_data", {}) or {}
			for uid_str, ud in list(user_data.items()):
				uid = int(uid_str)
				for a in list(ud.get("alerts", [])):
					sym = a.get("symbol")
					atype = a.get("type")
					val = float(a.get("value"))
					res = await get_crypto_price_with_provider(sym, provider)
					if not res:
						continue
					_, price_usd, change = res
					trigger = False
					if atype == "above" and price_usd >= val:
						trigger = True
					elif atype == "below" and price_usd <= val:
						trigger = True
					elif atype == "pct" and change is not None and abs(change) >= val:
						trigger = True
					if trigger:
						try:
							await app.bot.send_message(chat_id=uid, text=f"⏰ هشدار {sym.upper()} فعال شد: {atype} {val}")
						except Exception:
							pass
		except Exception:
			pass
		await asyncio.sleep(20)


async def on_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
	query = update.callback_query
	if not query:
		return
	await query.answer()
	data = query.data or ""
	if data.startswith("CRYPTO:"):
		symbol = data.split(":", 1)[1]
		provider = (STORE.get("providers", {}) or {}).get("crypto", "coingecko")
		res = await get_crypto_price_with_provider(symbol, provider)
		if not res:
			await query.edit_message_text("خطا در دریافت قیمت.")
			return
		sym, price_usd, change = res
		price_txt = await convert_price_for_user(update.effective_user.id, price_usd)
		change_txt = "" if change is None else ("📈" if change >= 0 else "📉") + f" {change:.2f}%"
		message = f"قیمت لحظه‌ای {sym}:\n{price_txt}\nتغییر ۲۴ساعته: {('نامشخص' if not change_txt else change_txt)}"
		await query.edit_message_text(message, reply_markup=build_crypto_inline())
	elif data.startswith("FIAT:"):
		code = data.split(":", 1)[1]
		prov = (STORE.get("providers", {}) or {}).get("fiat", "exchangerate_host")
		res = await get_fiat_rate_with_provider(code, prov)
		if not res:
			await query.edit_message_text("نرخ یافت نشد.")
			return
		c, rate, base = res
		await query.edit_message_text(format_fiat_message(c, rate, base), reply_markup=build_fiat_inline())
	elif data.startswith("ADMIN:"):
		key = data.split(":", 1)[1]
		if not is_admin(update.effective_user.id, STORE):
			await query.answer("دسترسی ندارید.", show_alert=True)
			return
		if key == "SET_PROVIDER":
			await query.edit_message_text(
				text=admin_providers_text(), reply_markup=build_admin_providers_inline()
			)
		elif key.startswith("PROV_CRYPTO_"):
			prov = key.replace("PROV_CRYPTO_", "").lower()
			STORE.setdefault("providers", {})["crypto"] = prov
			save_store(STORE)
			await query.edit_message_text(
				text=admin_providers_text(), reply_markup=build_admin_providers_inline()
			)
		elif key.startswith("PROV_FIAT_"):
			prov = key.replace("PROV_FIAT_", "").lower()
			STORE.setdefault("providers", {})["fiat"] = prov
			save_store(STORE)
			await query.edit_message_text(
				text=admin_providers_text(), reply_markup=build_admin_providers_inline()
			)
		elif key == "BACK":
			await query.edit_message_text("پنل مدیریت:", reply_markup=build_admin_inline())
	elif data.startswith("SET:"):
		action = data.split(":", 1)[1]
		uid = update.effective_user.id
		ud = get_user_data(STORE, uid)
		st = ud.setdefault("settings", {})
		if action == "BASE":
			# toggle USD -> EUR -> IRR
			base = st.get("base_fiat", "USD")
			nexts = {"USD": "EUR", "EUR": "IRR", "IRR": "USD"}
			st["base_fiat"] = nexts.get(base, "USD")
		elif action == "UI":
			st["ui_mode"] = "rich" if st.get("ui_mode", "compact") == "compact" else "compact"
		elif action == "LANG":
			# cycle FA -> EN -> AR -> FA
			lang = st.get("language", "FA").upper()
			next_lang = {"FA": "EN", "EN": "AR", "AR": "FA"}.get(lang, "FA")
			st["language"] = next_lang
		elif action == "TOMAN":
			st["display_toman"] = not bool(st.get("display_toman", True))
		elif action == "IRR":
			st["show_irr"] = not bool(st.get("show_irr", True))
		save_store(STORE)
		await query.edit_message_text(settings_text(uid), reply_markup=build_settings_inline(uid))
	elif data.startswith("LANGSEL:"):
		lang = data.split(":", 1)[1].upper()
		uid = update.effective_user.id
		ud = get_user_data(STORE, uid)
		ud.setdefault("settings", {})["language"] = lang
		save_store(STORE)
		await query.edit_message_text(help_text_by_lang(lang))
		# then show main help with keyboard
		await context.bot.send_message(chat_id=uid, text=get_help_text(uid), reply_markup=reply_keyboard())
	elif data.startswith("ALERTS:"):
		action = data.split(":", 1)[1]
		if action == "ADD":
			await query.edit_message_text("نماد و نوع و مقدار را ارسال کنید به‌صورت: btc above 50000 | btc below 45000 | btc pct 5")
			ud = get_user_data(STORE, update.effective_user.id)
			ud["pending"] = {"type": "alert_add"}
			save_store(STORE)
		elif action == "LIST":
			# show user alerts
			ud = get_user_data(STORE, update.effective_user.id)
			al = ud.get("alerts", [])
			if not al:
				await query.edit_message_text("هشداری ثبت نشده است.")
				return
			lines = ["⏰ هشدارها:"]
			for idx, a in enumerate(al):
				lines.append(f"{idx}) {a['symbol'].upper()} {a['type']} {a['value']}")
			await query.edit_message_text("\n".join(lines))
	elif data.startswith("WL:"):
		a = data.split(":", 1)[1]
		ud = get_user_data(STORE, update.effective_user.id)
		if a == "ADD":
			await query.edit_message_text("نماد را ارسال کنید (مثال: btc)")
			ud["pending"] = {"type": "wl_add"}
			save_store(STORE)
		elif a == "DEL":
			await query.edit_message_text("نماد را برای حذف ارسال کنید (مثال: btc)")
			ud["pending"] = {"type": "wl_del"}
			save_store(STORE)
		elif a == "SHOW":
			await show_watchlist(update, context)
	elif data.startswith("PF:"):
		a = data.split(":", 1)[1]
		ud = get_user_data(STORE, update.effective_user.id)
		if a == "ADD":
			await query.edit_message_text("برای افزودن موقعیت، به صورت: btc 0.5 40000 ارسال کنید")
			ud["pending"] = {"type": "pf_add"}
			save_store(STORE)
		elif a == "DEL":
			await query.edit_message_text("نماد موقعیت برای حذف (مثال: btc)")
			ud["pending"] = {"type": "pf_del"}
			save_store(STORE)
		elif a == "SHOW":
			await show_portfolio(update, context)


# --- Admin and settings ---

async def set_owner(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
	user = update.effective_user
	if STORE.get("owner_id") and user.id != STORE.get("owner_id"):
		await update.message.reply_text("تنها مالک فعلی می‌تواند مالک را تغییر دهد.")
		return
	args = context.args or []
	if not args:
		STORE["owner_id"] = user.id
		save_store(STORE)
		await update.message.reply_text("شما به عنوان مالک ثبت شدید.")
		return
	try:
		STORE["owner_id"] = int(args[0])
		save_store(STORE)
		await update.message.reply_text("مالک بروزرسانی شد.")
	except Exception:
		await update.message.reply_text("ورودی نامعتبر.")


async def add_admin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
	if not is_admin(update.effective_user.id, STORE):
		await update.message.reply_text("دسترسی ندارید.")
		return
	args = context.args or []
	if not args:
		await update.message.reply_text("استفاده: /addadmin <user_id>")
		return
	try:
		uid = int(args[0])
		admins = set(STORE.get("admins", []))
		admins.add(uid)
		STORE["admins"] = list(admins)
		save_store(STORE)
		await update.message.reply_text("ادمین اضافه شد.")
	except Exception:
		await update.message.reply_text("نامعتبر.")


async def del_admin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
	if not is_admin(update.effective_user.id, STORE):
		await update.message.reply_text("دسترسی ندارید.")
		return
	args = context.args or []
	if not args:
		await update.message.reply_text("استفاده: /deladmin <user_id>")
		return
	try:
		uid = int(args[0])
		admins = set(STORE.get("admins", []))
		admins.discard(uid)
		STORE["admins"] = list(admins)
		save_store(STORE)
		await update.message.reply_text("ادمین حذف شد.")
	except Exception:
		await update.message.reply_text("نامعتبر.")


async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
	if not is_admin(update.effective_user.id, STORE):
		await update.message.reply_text("دسترسی ندارید.")
		return
	text = " ".join(context.args or [])
	if not text:
		await update.message.reply_text("استفاده: /broadcast <متن>")
		return
	count = 0
	errs = 0
	for uid in list(set(STORE.get("users", []))):
		try:
			await context.bot.send_message(chat_id=uid, text=text)
			count += 1
		except Exception:
			errs += 1
	await update.message.reply_text(f"ارسال شد. موفق: {count}، خطا: {errs}")


async def forcesub(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
	if not is_admin(update.effective_user.id, STORE):
		await update.message.reply_text("دسترسی ندارید.")
		return
	args = context.args or []
	if not args:
		fs = STORE.get("forced_subscription", {}) or {}
		status = "روشن" if fs.get("enabled") else "خاموش"
		ch = fs.get("channel_username") or "-"
		await update.message.reply_text(f"وضعیت قفل: {status}\nکانال: {ch}\nاستفاده: /forcesub on @channel | /forcesub off")
		return
	mode = args[0].lower()
	if mode == "on" and len(args) >= 2:
		STORE["forced_subscription"] = {"enabled": True, "channel_username": args[1]}
		save_store(STORE)
		await update.message.reply_text("قفل اجباری فعال شد.")
	elif mode == "off":
		STORE["forced_subscription"] = {"enabled": False, "channel_username": None}
		save_store(STORE)
		await update.message.reply_text("قفل اجباری غیرفعال شد.")
	else:
		await update.message.reply_text("استفاده: /forcesub on @channel | /forcesub off")


def build_app():
	app = ApplicationBuilder().token(BOT_TOKEN).concurrent_updates(True).build()
	# Core commands
	app.add_handler(CommandHandler("start", start))
	app.add_handler(CommandHandler("help", help_cmd))
	app.add_handler(CommandHandler("price", price))
	# Shortcut commands
	for sym in ["btc", "eth", "bnb", "sol", "xrp", "ada", "doge", "ton", "trx", "ltc"]:
		app.add_handler(CommandHandler(sym, lambda u, c, s=sym: price_shortcut(u, c, s)))
	# Menus
	app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), on_menu_text))
	app.add_handler(CallbackQueryHandler(on_callback))
	# Admin
	app.add_handler(CommandHandler("setowner", set_owner))
	app.add_handler(CommandHandler("addadmin", add_admin))
	app.add_handler(CommandHandler("deladmin", del_admin))
	app.add_handler(CommandHandler("broadcast", broadcast))
	app.add_handler(CommandHandler("forcesub", forcesub))
	# Watchlist & portfolio commands
	app.add_handler(CommandHandler("watch_add", watch_add))
	app.add_handler(CommandHandler("watch_del", watch_del))
	app.add_handler(CommandHandler("watch_list", watch_list_cmd))
	app.add_handler(CommandHandler("pf_add", pf_add))
	app.add_handler(CommandHandler("pf_del", pf_del))
	app.add_handler(CommandHandler("pf", pf_show_cmd))
	# Alerts, news, chart
	app.add_handler(CommandHandler("alert_add", alert_add))
	app.add_handler(CommandHandler("alert_list", alert_list))
	app.add_handler(CommandHandler("alert_del", alert_del))
	app.add_handler(CommandHandler("news", news_cmd))
	app.add_handler(CommandHandler("chart", chart_cmd))
	return app


async def chart_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
	args = context.args or []
	if not args:
		await update.message.reply_text("استفاده: /chart <symbol> [days=7]")
		return
	sym = args[0].strip().lower()
	days = int(args[1]) if len(args) > 1 else 7
	coin_id = SYMBOL_TO_CG_ID.get(sym)
	if not coin_id:
		await update.message.reply_text("نماد پشتیبانی نمی‌شود.")
		return
	series = await fetch_history_prices(coin_id, days=days)
	if not series:
		await update.message.reply_text("داده تاریخچه در دسترس نیست.")
		return
	await update.message.reply_text(f"{sym.upper()} {sparkline(series)}")


async def news_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
	args = context.args or []
	sym = args[0] if args else None
	items = await get_news(symbol=sym, per_feed=3)
	if not items:
		await update.message.reply_text("خبری یافت نشد.")
		return
	lines = []
	for it in items[:10]:
		title = it.get("title", "")
		link = it.get("link", "")
		lines.append(f"• {title}\n{link}")
	await update.message.reply_text("\n\n".join(lines))


# Flask routes
@app.route('/health')
def health_check():
	return jsonify({"status": "healthy", "bot": "running"})

@app.route('/webhook', methods=['POST'])
def webhook():
	update = Update.de_json(request.get_json(), bot)
	asyncio.create_task(process_update(update))
	return jsonify({"status": "ok"})

async def process_update(update):
	await bot.process_update(update)

def main() -> None:
	telegram_app = build_app()
	global bot
	bot = telegram_app.bot
	
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
		# start background alert checker
		asyncio.get_event_loop().create_task(alert_checker(telegram_app))
		telegram_app.run_polling(allowed_updates=Update.ALL_TYPES, close_loop=False)
	
	# Start Flask app for health check
	if webhook_url:
		app.run(host='0.0.0.0', port=port)


if __name__ == "__main__":
	main()
