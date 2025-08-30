import os
import asyncio
from typing import Optional, List, Tuple

from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, CallbackQueryHandler, MessageHandler, filters
from flask import Flask, request, jsonify

from price_service import get_price_by_symbol, format_price_message, SYMBOL_TO_CG_ID, get_crypto_price_with_provider
from fiat_service import get_fiat_rate, format_fiat_message, FIAT_CODES, get_fiat_rate_with_provider
from news_service import get_news
from history import fetch_history_prices, sparkline
from arbitrage import compare_prices
from p2p_service import fetch_binance_p2p, summarize_p2p_offers
from store import load_store, save_store, is_admin, get_user_data
from cache import TTLCache
from security import check_black_white, touch_rate_limit
from ta import sma, rsi, macd, simple_support_resistance
import config


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


def reply_keyboard() -> ReplyKeyboardMarkup:
	return ReplyKeyboardMarkup([
		[KeyboardButton("💰 قیمت ارز"), KeyboardButton("💱 نرخ ارز")],
		[KeyboardButton("📰 اخبار"), KeyboardButton("📊 نمودار")],
		[KeyboardButton("⚖️ مقایسه"), KeyboardButton("🔄 P2P")],
		[KeyboardButton("👁 واچ‌لیست"), KeyboardButton("📚 پرتفوی")],
		[KeyboardButton("🔔 هشدارها"), KeyboardButton("🛠 تنظیمات")],
		[KeyboardButton("❓ راهنما")]
	], resize_keyboard=True)


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
	
	# check for pending actions
	ud = get_user_data(STORE, uid)
	pending = (ud or {}).get("pending")
	if not pending:
		return
	
	ptype = pending.get("type")
	text_in = (update.message.text or "").strip()
	
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
	
	return app


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
		telegram_app.run_polling(allowed_updates=Update.ALL_TYPES, close_loop=False)
	
	# Start Flask app for health check
	if webhook_url:
		app.run(host='0.0.0.0', port=port)


if __name__ == "__main__":
	main()
