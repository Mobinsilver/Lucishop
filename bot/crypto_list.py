import asyncio
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from price_service import get_crypto_price_with_provider
from history import fetch_history_prices
from store import load_store, get_user_data, save_store
from cache import TTLCache
from fiat_service import get_fiat_rate_with_provider

# لیست ارزهای پشتیبانی شده
SUPPORTED_CRYPTOS = [
    {"symbol": "BTC", "name": "Bitcoin", "emoji": "₿"},
    {"symbol": "ETH", "name": "Ethereum", "emoji": "Ξ"},
    {"symbol": "BNB", "name": "Binance Coin", "emoji": "🟡"},
    {"symbol": "SOL", "name": "Solana", "emoji": "☀️"},
    {"symbol": "XRP", "name": "Ripple", "emoji": "💎"},
    {"symbol": "ADA", "name": "Cardano", "emoji": "🔷"},
    {"symbol": "DOGE", "name": "Dogecoin", "emoji": "🐕"},
    {"symbol": "TON", "name": "Toncoin", "emoji": "💎"},
    {"symbol": "TRX", "name": "TRON", "emoji": "⚡"},
    {"symbol": "LTC", "name": "Litecoin", "emoji": "Ł"},
    {"symbol": "DOT", "name": "Polkadot", "emoji": "🔴"},
    {"symbol": "MATIC", "name": "Polygon", "emoji": "🟣"},
    {"symbol": "AVAX", "name": "Avalanche", "emoji": "❄️"},
    {"symbol": "LINK", "name": "Chainlink", "emoji": "🔗"},
    {"symbol": "UNI", "name": "Uniswap", "emoji": "🦄"},
    {"symbol": "ATOM", "name": "Cosmos", "emoji": "⚛️"},
    {"symbol": "ETC", "name": "Ethereum Classic", "emoji": "🔶"},
    {"symbol": "XLM", "name": "Stellar", "emoji": "⭐"},
    {"symbol": "BCH", "name": "Bitcoin Cash", "emoji": "💰"},
    {"symbol": "FIL", "name": "Filecoin", "emoji": "📁"},
    {"symbol": "NEAR", "name": "NEAR Protocol", "emoji": "🌐"},
    {"symbol": "ALGO", "name": "Algorand", "emoji": "🔵"},
    {"symbol": "VET", "name": "VeChain", "emoji": "🔷"},
    {"symbol": "ICP", "name": "Internet Computer", "emoji": "🌐"},
    {"symbol": "FTM", "name": "Fantom", "emoji": "👻"},
    {"symbol": "MANA", "name": "Decentraland", "emoji": "🏠"},
    {"symbol": "SAND", "name": "The Sandbox", "emoji": "🏖️"},
    {"symbol": "AXS", "name": "Axie Infinity", "emoji": "🎮"},
    {"symbol": "GALA", "name": "Gala", "emoji": "🎵"},
    {"symbol": "CHZ", "name": "Chiliz", "emoji": "⚽"},
    {"symbol": "ENJ", "name": "Enjin Coin", "emoji": "⚔️"},
    {"symbol": "THETA", "name": "Theta Network", "emoji": "🎬"},
    {"symbol": "EOS", "name": "EOS", "emoji": "🟢"},
    {"symbol": "AAVE", "name": "Aave", "emoji": "🦘"},
    {"symbol": "COMP", "name": "Compound", "emoji": "🏦"},
    {"symbol": "MKR", "name": "Maker", "emoji": "🏭"},
    {"symbol": "SNX", "name": "Synthetix", "emoji": "📊"},
    {"symbol": "CRV", "name": "Curve DAO", "emoji": "📈"},
    {"symbol": "YFI", "name": "yearn.finance", "emoji": "🏛️"},
    {"symbol": "SUSHI", "name": "SushiSwap", "emoji": "🍣"},
    {"symbol": "1INCH", "name": "1inch", "emoji": "🔧"},
    {"symbol": "ZEC", "name": "Zcash", "emoji": "🛡️"},
    {"symbol": "XMR", "name": "Monero", "emoji": "🔒"},
    {"symbol": "DASH", "name": "Dash", "emoji": "💎"},
    {"symbol": "NEO", "name": "NEO", "emoji": "🟢"},
    {"symbol": "QTUM", "name": "Qtum", "emoji": "🔷"},
    {"symbol": "IOTA", "name": "IOTA", "emoji": "📡"},
    {"symbol": "XTZ", "name": "Tezos", "emoji": "🟣"},
    {"symbol": "HBAR", "name": "Hedera", "emoji": "🌿"},
    {"symbol": "GRT", "name": "The Graph", "emoji": "📊"},
    {"symbol": "BAT", "name": "Basic Attention Token", "emoji": "🦇"},
    {"symbol": "HOT", "name": "Holo", "emoji": "🔥"},
    {"symbol": "ZIL", "name": "Zilliqa", "emoji": "⚡"},
    {"symbol": "WAVES", "name": "Waves", "emoji": "🌊"},
    {"symbol": "RVN", "name": "Ravencoin", "emoji": "🦅"},
    {"symbol": "NANO", "name": "Nano", "emoji": "⚡"},
    {"symbol": "BTT", "name": "BitTorrent", "emoji": "🌊"},
    {"symbol": "WIN", "name": "WINk", "emoji": "🎰"},
    {"symbol": "CAKE", "name": "PancakeSwap", "emoji": "🥞"},
    {"symbol": "BAKE", "name": "BakeryToken", "emoji": "🍞"},
    {"symbol": "AUTO", "name": "CUBE", "emoji": "🚗"},
    {"symbol": "ALPHA", "name": "Alpha Finance", "emoji": "🅰️"},
    {"symbol": "BEL", "name": "Bella Protocol", "emoji": "🔔"},
    {"symbol": "CTSI", "name": "Cartesi", "emoji": "🧮"},
    {"symbol": "DEGO", "name": "Dego Finance", "emoji": "🏗️"},
    {"symbol": "DODO", "name": "DODO", "emoji": "🦤"},
    {"symbol": "DUSK", "name": "Dusk Network", "emoji": "🌆"},
    {"symbol": "EGLD", "name": "MultiversX", "emoji": "⭐"},
    {"symbol": "FLOW", "name": "Flow", "emoji": "🌊"},
    {"symbol": "HIVE", "name": "Hive", "emoji": "🐝"},
    {"symbol": "ICX", "name": "ICON", "emoji": "🔗"},
    {"symbol": "KAVA", "name": "Kava", "emoji": "🏛️"},
    {"symbol": "KSM", "name": "Kusama", "emoji": "🟡"},
    {"symbol": "LRC", "name": "Loopring", "emoji": "🔄"},
    {"symbol": "OMG", "name": "OMG Network", "emoji": "🟣"},
    {"symbol": "ONT", "name": "Ontology", "emoji": "🟢"},
    {"symbol": "PAXG", "name": "PAX Gold", "emoji": "🥇"},
    {"symbol": "REN", "name": "Ren", "emoji": "🔗"},
    {"symbol": "RSR", "name": "Reserve Rights", "emoji": "🛡️"},
    {"symbol": "SKL", "name": "SKALE", "emoji": "⚡"},
    {"symbol": "STORJ", "name": "Storj", "emoji": "💾"},
    {"symbol": "SXP", "name": "SXP", "emoji": "💳"},
    {"symbol": "TFUEL", "name": "Theta Fuel", "emoji": "⛽"},
    {"symbol": "TOMO", "name": "TomoChain", "emoji": "🍅"},
    {"symbol": "WRX", "name": "WazirX", "emoji": "🔄"},
    {"symbol": "ZRX", "name": "0x", "emoji": "🔄"},
    {"symbol": "ANKR", "name": "Ankr", "emoji": "🔗"},
    {"symbol": "AR", "name": "Arweave", "emoji": "📚"},
    {"symbol": "BICO", "name": "Biconomy", "emoji": "🔧"},
    {"symbol": "BLZ", "name": "Blizzard", "emoji": "❄️"},
    {"symbol": "BOND", "name": "BarnBridge", "emoji": "🌉"},
    {"symbol": "C98", "name": "Coin98", "emoji": "🪙"},
    {"symbol": "CELO", "name": "Celo", "emoji": "📱"},
    {"symbol": "CHR", "name": "Chromia", "emoji": "🎨"},
    {"symbol": "CKB", "name": "Nervos Network", "emoji": "🧠"},
    {"symbol": "CLV", "name": "Clover Finance", "emoji": "🍀"},
    {"symbol": "COCOS", "name": "Cocos-BCX", "emoji": "🎮"},
    {"symbol": "COS", "name": "Contentos", "emoji": "📹"},
    {"symbol": "CTXC", "name": "Cortex", "emoji": "🧠"},
    {"symbol": "CVP", "name": "PowerPool", "emoji": "⚡"},
    {"symbol": "DATA", "name": "Streamr", "emoji": "📊"},
    {"symbol": "DGB", "name": "DigiByte", "emoji": "💎"},
    {"symbol": "DYDX", "name": "dYdX", "emoji": "📈"},
    {"symbol": "ELF", "name": "aelf", "emoji": "🧝"},
    {"symbol": "ERN", "name": "Ethernity", "emoji": "🎨"},
    {"symbol": "FET", "name": "Fetch.ai", "emoji": "🤖"},
    {"symbol": "FORTH", "name": "Ampleforth", "emoji": "🔄"},
    {"symbol": "FRONT", "name": "Frontier", "emoji": "🚀"},
    {"symbol": "FTT", "name": "FTX Token", "emoji": "🏦"},
    {"symbol": "FXS", "name": "Frax Share", "emoji": "🏛️"},
    {"symbol": "GTC", "name": "Gitcoin", "emoji": "🐙"},
    {"symbol": "HARD", "name": "Kava Lend", "emoji": "🏦"},
    {"symbol": "HBTC", "name": "Huobi BTC", "emoji": "₿"},
    {"symbol": "HIVE", "name": "Hive", "emoji": "🐝"},
    {"symbol": "HNT", "name": "Helium", "emoji": "📡"},
    {"symbol": "HOT", "name": "Holo", "emoji": "🔥"},
    {"symbol": "ICP", "name": "Internet Computer", "emoji": "🌐"},
    {"symbol": "IDEX", "name": "IDEX", "emoji": "🔄"},
    {"symbol": "ILV", "name": "Illuvium", "emoji": "🎮"},
    {"symbol": "IMX", "name": "Immutable X", "emoji": "⚡"},
    {"symbol": "INJ", "name": "Injective", "emoji": "💉"},
    {"symbol": "IOTX", "name": "IoTeX", "emoji": "📱"},
    {"symbol": "JASMY", "name": "JasmyCoin", "emoji": "🔐"},
    {"symbol": "KEEP", "name": "Keep Network", "emoji": "🔒"},
    {"symbol": "KLAY", "name": "Klaytn", "emoji": "🟢"},
    {"symbol": "KNC", "name": "Kyber Network", "emoji": "🔄"},
    {"symbol": "LDO", "name": "Lido DAO", "emoji": "🏛️"},
    {"symbol": "LINA", "name": "Linear", "emoji": "📈"},
    {"symbol": "LIT", "name": "Litentry", "emoji": "🆔"},
    {"symbol": "LPT", "name": "Livepeer", "emoji": "📹"},
    {"symbol": "LQTY", "name": "Liquity", "emoji": "🏦"},
    {"symbol": "LTO", "name": "LTO Network", "emoji": "🔗"},
    {"symbol": "LUNA", "name": "Terra", "emoji": "🌙"},
    {"symbol": "MASK", "name": "Mask Network", "emoji": "🎭"},
    {"symbol": "MBOX", "name": "MOBOX", "emoji": "📦"},
    {"symbol": "MC", "name": "Merit Circle", "emoji": "🎯"},
    {"symbol": "MINA", "name": "Mina", "emoji": "📱"},
    {"symbol": "MIR", "name": "Mirror Protocol", "emoji": "🪞"},
    {"symbol": "MLN", "name": "Enzyme", "emoji": "🧬"},
    {"symbol": "MOVR", "name": "Moonriver", "emoji": "🌙"},
    {"symbol": "MTL", "name": "Metal", "emoji": "🥇"},
    {"symbol": "MULTI", "name": "Multichain", "emoji": "🌉"},
    {"symbol": "NMR", "name": "Numeraire", "emoji": "🧮"},
    {"symbol": "OCEAN", "name": "Ocean Protocol", "emoji": "🌊"},
    {"symbol": "OGN", "name": "Origin Protocol", "emoji": "🎨"},
    {"symbol": "OM", "name": "MANTRA DAO", "emoji": "🕉️"},
    {"symbol": "ONE", "name": "Harmony", "emoji": "🎵"},
    {"symbol": "ONG", "name": "Ontology Gas", "emoji": "⛽"},
    {"symbol": "OP", "name": "Optimism", "emoji": "⚡"},
    {"symbol": "ORBS", "name": "Orbs", "emoji": "🔮"},
    {"symbol": "ORN", "name": "Orion Protocol", "emoji": "🦅"},
    {"symbol": "OXT", "name": "Orchid", "emoji": "🌸"},
    {"symbol": "PAX", "name": "Paxos Standard", "emoji": "💵"},
    {"symbol": "PEOPLE", "name": "ConstitutionDAO", "emoji": "👥"},
    {"symbol": "PERP", "name": "Perpetual Protocol", "emoji": "📊"},
    {"symbol": "POLS", "name": "Polkastarter", "emoji": "🚀"},
    {"symbol": "POLY", "name": "Polymath", "emoji": "📜"},
    {"symbol": "POND", "name": "Marlin", "emoji": "🐟"},
    {"symbol": "POWR", "name": "Power Ledger", "emoji": "⚡"},
    {"symbol": "PRO", "name": "Propy", "emoji": "🏠"},
    {"symbol": "PUNDIX", "name": "Pundi X", "emoji": "🏪"},
    {"symbol": "PYR", "name": "Vulcan Forged", "emoji": "🔥"},
    {"symbol": "QI", "name": "BENQI", "emoji": "🦄"},
    {"symbol": "QNT", "name": "Quant", "emoji": "🔗"},
    {"symbol": "QUICK", "name": "QuickSwap", "emoji": "⚡"},
    {"symbol": "RAD", "name": "Radicle", "emoji": "🌱"},
    {"symbol": "RARE", "name": "SuperRare", "emoji": "🎨"},
    {"symbol": "RAY", "name": "Raydium", "emoji": "☀️"},
    {"symbol": "REEF", "name": "Reef", "emoji": "🪸"},
    {"symbol": "REN", "name": "Ren", "emoji": "🔗"},
    {"symbol": "REQ", "name": "Request", "emoji": "📋"},
    {"symbol": "RLC", "name": "iExec RLC", "emoji": "☁️"},
    {"symbol": "ROSE", "name": "Oasis Network", "emoji": "🌹"},
    {"symbol": "RSR", "name": "Reserve Rights", "emoji": "🛡️"},
    {"symbol": "RUNE", "name": "THORChain", "emoji": "⚡"},
    {"symbol": "SAND", "name": "The Sandbox", "emoji": "🏖️"},
    {"symbol": "SCRT", "name": "Secret", "emoji": "🔒"},
    {"symbol": "SHIB", "name": "Shiba Inu", "emoji": "🐕"},
    {"symbol": "SLP", "name": "Smooth Love Potion", "emoji": "💕"},
    {"symbol": "SNT", "name": "Status", "emoji": "📱"},
    {"symbol": "SPELL", "name": "Spell Token", "emoji": "🧙"},
    {"symbol": "SRM", "name": "Serum", "emoji": "💉"},
    {"symbol": "STPT", "name": "Standard Tokenization", "emoji": "📜"},
    {"symbol": "STRAX", "name": "Stratis", "emoji": "🔗"},
    {"symbol": "SUPER", "name": "SuperFarm", "emoji": "🚜"},
    {"symbol": "SUSHI", "name": "SushiSwap", "emoji": "🍣"},
    {"symbol": "SWRV", "name": "Swerve", "emoji": "🔄"},
    {"symbol": "SXP", "name": "SXP", "emoji": "💳"},
    {"symbol": "SYN", "name": "Synapse", "emoji": "🧠"},
    {"symbol": "TFUEL", "name": "Theta Fuel", "emoji": "⛽"},
    {"symbol": "TLM", "name": "Alien Worlds", "emoji": "👽"},
    {"symbol": "TOMO", "name": "TomoChain", "emoji": "🍅"},
    {"symbol": "TRB", "name": "Tellor", "emoji": "📊"},
    {"symbol": "TRIBE", "name": "Tribe", "emoji": "🏛️"},
    {"symbol": "TRU", "name": "TrueFi", "emoji": "✅"},
    {"symbol": "TVK", "name": "Terra Virtua", "emoji": "🎮"},
    {"symbol": "UMA", "name": "UMA", "emoji": "🛡️"},
    {"symbol": "UNFI", "name": "Unifi Protocol DAO", "emoji": "🔄"},
    {"symbol": "USDC", "name": "USD Coin", "emoji": "💵"},
    {"symbol": "USDT", "name": "Tether", "emoji": "💵"},
    {"symbol": "UTK", "name": "Utrust", "emoji": "💳"},
    {"symbol": "VET", "name": "VeChain", "emoji": "🔷"},
    {"symbol": "VGX", "name": "Voyager Token", "emoji": "🚀"},
    {"symbol": "VTHO", "name": "VeThor Token", "emoji": "⚡"},
    {"symbol": "WAVES", "name": "Waves", "emoji": "🌊"},
    {"symbol": "WAXP", "name": "WAX", "emoji": "🕯️"},
    {"symbol": "WBTC", "name": "Wrapped Bitcoin", "emoji": "₿"},
    {"symbol": "WETH", "name": "Wrapped Ether", "emoji": "Ξ"},
    {"symbol": "WOO", "name": "WOO Network", "emoji": "🦉"},
    {"symbol": "WRX", "name": "WazirX", "emoji": "🔄"},
    {"symbol": "XEC", "name": "eCash", "emoji": "💵"},
    {"symbol": "XEM", "name": "NEM", "emoji": "💎"},
    {"symbol": "XLM", "name": "Stellar", "emoji": "⭐"},
    {"symbol": "XRP", "name": "Ripple", "emoji": "💎"},
    {"symbol": "XTZ", "name": "Tezos", "emoji": "🟣"},
    {"symbol": "XVG", "name": "Verge", "emoji": "🌙"},
    {"symbol": "YFI", "name": "yearn.finance", "emoji": "🏛️"},
    {"symbol": "YGG", "name": "Yield Guild Games", "emoji": "🎮"},
    {"symbol": "ZEC", "name": "Zcash", "emoji": "🛡️"},
    {"symbol": "ZEN", "name": "Horizen", "emoji": "🧘"},
    {"symbol": "ZIL", "name": "Zilliqa", "emoji": "⚡"},
    {"symbol": "ZRX", "name": "0x", "emoji": "🔄"}
]

# ایجاد instance از cache و store
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

async def show_crypto_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """نمایش لیست ارزها با دکمه‌های شیشه‌ای"""
    keyboard = []
    row = []
    
    for i, crypto in enumerate(SUPPORTED_CRYPTOS):
        # ایجاد دکمه شیشه‌ای برای هر ارز
        button_text = f"{crypto['emoji']} {crypto['symbol']}"
        callback_data = f"crypto_detail:{crypto['symbol'].lower()}"
        
        row.append(InlineKeyboardButton(button_text, callback_data=callback_data))
        
        # هر 3 دکمه در یک ردیف
        if len(row) == 3:
            keyboard.append(row)
            row = []
    
    # اضافه کردن ردیف آخر اگر کامل نباشد
    if row:
        keyboard.append(row)
    
    # دکمه بازگشت
    keyboard.append([InlineKeyboardButton("🔙 بازگشت به منو", callback_data="back_to_main")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    text = """
💰 **لیست ارزهای دیجیتال**

لطفاً ارز مورد نظر خود را انتخاب کنید:

💡 **نکات**:
• روی هر ارز کلیک کنید تا قیمت کامل را ببینید
• قیمت‌های لحظه‌ای، هفتگی و ماهانه نمایش داده می‌شود
• از دکمه بازگشت برای بازگشت به منو استفاده کنید
    """
    
    if update.callback_query:
        await update.callback_query.edit_message_text(text, reply_markup=reply_markup)
    else:
        await update.message.reply_text(text, reply_markup=reply_markup)

async def show_crypto_detail(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """نمایش جزئیات کامل قیمت ارز"""
    query = update.callback_query
    await query.answer()
    
    # استخراج نماد ارز از callback data
    symbol = query.data.split(":")[1].upper()
    
    # پیدا کردن اطلاعات ارز
    crypto_info = None
    for crypto in SUPPORTED_CRYPTOS:
        if crypto['symbol'].upper() == symbol:
            crypto_info = crypto
            break
    
    if not crypto_info:
        await query.edit_message_text("❌ ارز مورد نظر یافت نشد!")
        return
    
    # نمایش پیام در حال بارگذاری
    loading_text = f"⏳ در حال دریافت قیمت {crypto_info['emoji']} {crypto_info['name']}..."
    await query.edit_message_text(loading_text)
    
    try:
        # دریافت قیمت لحظه‌ای
        current_price_result = await get_crypto_price_with_provider(symbol.lower(), "coingecko")
        
        if not current_price_result:
            await query.edit_message_text(f"❌ خطا در دریافت قیمت {symbol}")
            return
        
        _, current_price, current_change = current_price_result
        
        # دریافت قیمت‌های تاریخی
        weekly_price = None
        monthly_price = None
        
        # تلاش برای دریافت قیمت هفتگی (7 روز پیش)
        try:
            from price_service import SYMBOL_TO_CG_ID
            coin_id = SYMBOL_TO_CG_ID.get(symbol.lower())
            if coin_id:
                weekly_series = await fetch_history_prices(coin_id, days=7)
                if weekly_series and len(weekly_series) > 0:
                    weekly_price = weekly_series[0]  # قیمت 7 روز پیش
        except Exception:
            pass
        
        # تلاش برای دریافت قیمت ماهانه (30 روز پیش)
        try:
            if coin_id:
                monthly_series = await fetch_history_prices(coin_id, days=30)
                if monthly_series and len(monthly_series) > 0:
                    monthly_price = monthly_series[0]  # قیمت 30 روز پیش
        except Exception:
            pass
        
        # تبدیل قیمت برای کاربر
        user_id = query.from_user.id
        current_price_text = await convert_price_for_user(user_id, current_price)
        
        # محاسبه تغییرات
        weekly_change = None
        monthly_change = None
        
        if weekly_price:
            weekly_change = ((current_price - weekly_price) / weekly_price) * 100
            weekly_price_text = await convert_price_for_user(user_id, weekly_price)
        else:
            weekly_price_text = "نامشخص"
        
        if monthly_price:
            monthly_change = ((current_price - monthly_price) / monthly_price) * 100
            monthly_price_text = await convert_price_for_user(user_id, monthly_price)
        else:
            monthly_price_text = "نامشخص"
        
        # ایجاد متن کامل
        text = f"""
{crypto_info['emoji']} **{crypto_info['name']} ({symbol})**

💰 **قیمت لحظه‌ای**:
{current_price_text}
📈 تغییر 24 ساعته: {('📈' if current_change >= 0 else '📉') + f" {current_change:.2f}%" if current_change is not None else "نامشخص"}

📊 **قیمت هفتگی** (7 روز پیش):
{weekly_price_text}
📈 تغییر هفتگی: {('📈' if weekly_change >= 0 else '📉') + f" {weekly_change:.2f}%" if weekly_change is not None else "نامشخص"}

📈 **قیمت ماهانه** (30 روز پیش):
{monthly_price_text}
📈 تغییر ماهانه: {('📈' if monthly_change >= 0 else '📉') + f" {monthly_change:.2f}%" if monthly_change is not None else "نامشخص"}

🕒 **آخرین بروزرسانی**: {asyncio.get_event_loop().time():.0f}
        """
        
        # دکمه‌های شیشه‌ای
        keyboard = [
            [InlineKeyboardButton("🔄 بروزرسانی", callback_data=f"refresh_crypto:{symbol.lower()}")],
            [InlineKeyboardButton("📊 نمودار", callback_data=f"chart_crypto:{symbol.lower()}")],
            [InlineKeyboardButton("🔔 تنظیم هشدار", callback_data=f"SET_ALERT:{symbol.lower()}")],
            [InlineKeyboardButton("🔙 بازگشت به لیست", callback_data="back_to_crypto_list")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(text, reply_markup=reply_markup)
        
    except Exception as e:
        error_text = f"❌ خطا در دریافت اطلاعات {symbol}:\n{str(e)}"
        keyboard = [
            [InlineKeyboardButton("🔔 تنظیم هشدار", callback_data=f"SET_ALERT:{symbol}")],
            [InlineKeyboardButton("🔙 بازگشت به لیست", callback_data="back_to_crypto_list")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(error_text, reply_markup=reply_markup)

async def refresh_crypto_price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """بروزرسانی قیمت ارز"""
    query = update.callback_query
    await query.answer()
    
    # استخراج نماد ارز از callback data
    symbol = query.data.split(":")[1].upper()
    
    # نمایش پیام در حال بروزرسانی
    loading_text = f"🔄 در حال بروزرسانی قیمت {symbol}..."
    await query.edit_message_text(loading_text)
    
    # پاک کردن کش برای این ارز
    cache_key = f"price:{symbol.lower()}"
    CACHE.delete(cache_key)
    
    # نمایش مجدد جزئیات
    await show_crypto_detail(update, context)

async def show_crypto_chart(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """نمایش نمودار ارز"""
    query = update.callback_query
    await query.answer()
    
    # استخراج نماد ارز از callback data
    symbol = query.data.split(":")[1].upper()
    
    # نمایش پیام در حال بارگذاری
    loading_text = f"📊 در حال ایجاد نمودار {symbol}..."
    await query.edit_message_text(loading_text)
    
    try:
        from history import sparkline
        from price_service import SYMBOL_TO_CG_ID
        
        coin_id = SYMBOL_TO_CG_ID.get(symbol.lower())
        if not coin_id:
            await query.edit_message_text(f"❌ نمودار برای {symbol} در دسترس نیست")
            return
        
        # دریافت داده‌های نمودار
        series = await fetch_history_prices(coin_id, days=7)
        if not series:
            await query.edit_message_text(f"❌ داده‌های نمودار برای {symbol} در دسترس نیست")
            return
        
        # ایجاد نمودار
        chart = sparkline(series)
        
        text = f"""
📊 **نمودار {symbol} (7 روز گذشته)**

{chart}

📈 **نکات نمودار**:
• نمودار تغییرات قیمت در 7 روز گذشته را نشان می‌دهد
• نقاط بالاتر = قیمت بیشتر
• نقاط پایین‌تر = قیمت کمتر
        """
        
        keyboard = [
            [InlineKeyboardButton("🔄 بروزرسانی", callback_data=f"refresh_chart:{symbol.lower()}")],
            [InlineKeyboardButton("🔙 بازگشت", callback_data=f"crypto_detail:{symbol.lower()}")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(text, reply_markup=reply_markup)
        
    except Exception as e:
        error_text = f"❌ خطا در ایجاد نمودار {symbol}:\n{str(e)}"
        keyboard = [[InlineKeyboardButton("🔙 بازگشت", callback_data=f"crypto_detail:{symbol.lower()}")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(error_text, reply_markup=reply_markup)
