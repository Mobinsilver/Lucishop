import asyncio
from typing import Dict, Optional, Tuple
import aiohttp
from store import load_store

COINGECKO_API = "https://api.coingecko.com/api/v3"
BINANCE_API = "https://api.binance.com/api/v3"

# Minimal symbol->id mapping; extend as needed
SYMBOL_TO_CG_ID: Dict[str, str] = {
	"btc": "bitcoin",
	"eth": "ethereum",
	"bnb": "binancecoin",
	"sol": "solana",
	"xrp": "ripple",
	"ada": "cardano",
	"doge": "dogecoin",
	"ton": "the-open-network",
	"trx": "tron",
	"ltc": "litecoin",
	"dot": "polkadot",
	"matic": "matic-network",
	"link": "chainlink",
	"avax": "avalanche-2",
}


async def fetch_json(session: aiohttp.ClientSession, url: str, params: Optional[Dict[str, str]] = None) -> dict:
	async with session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=10)) as resp:
		resp.raise_for_status()
		return await resp.json()


async def get_price_by_cgid(coin_id: str) -> Optional[Tuple[float, Optional[float]]]:
	"""Return (usd_price, usd_24h_change) or None if not found."""
	url = f"{COINGECKO_API}/simple/price"
	params = {
		"ids": coin_id,
		"vs_currencies": "usd",
		"include_24hr_change": "true",
	}
	async with aiohttp.ClientSession() as session:
		try:
			data = await fetch_json(session, url, params)
			info = data.get(coin_id)
			if not info:
				return None
			price = float(info.get("usd"))
			change = info.get("usd_24h_change")
			return price, (float(change) if change is not None else None)
		except Exception:
			return None


async def get_price_by_symbol(symbol: str) -> Optional[Tuple[str, float, Optional[float]]]:
	"""Lookup by common ticker symbol; returns (symbol, price, change)."""
	sym = symbol.strip().lower()
	coin_id = SYMBOL_TO_CG_ID.get(sym)
	if not coin_id:
		return None
	result = await get_price_by_cgid(coin_id)
	if result is None:
		return None
	price, change = result
	return sym.upper(), price, change


async def get_price_by_symbol_binance(symbol: str) -> Optional[Tuple[str, float, Optional[float]]]:
	"""Binance spot price for symbolUSDT, change via 24hr ticker."""
	sym = symbol.strip().upper()
	pair = f"{sym}USDT"
	try:
		async with aiohttp.ClientSession() as session:
			# price
			async with session.get(f"{BINANCE_API}/ticker/price", params={"symbol": pair}, timeout=aiohttp.ClientTimeout(total=10)) as r:
				r.raise_for_status()
				p = await r.json()
				price = float(p.get("price"))
			# change
			async with session.get(f"{BINANCE_API}/ticker/24hr", params={"symbol": pair}, timeout=aiohttp.ClientTimeout(total=10)) as r2:
				r2.raise_for_status()
				j = await r2.json()
				change = float(j.get("priceChangePercent")) if j.get("priceChangePercent") is not None else None
			return sym, price, change
	except Exception:
		return None


async def get_crypto_price_with_provider(symbol: str, provider: str) -> Optional[Tuple[str, float, Optional[float]]]:
	"""Get crypto price with specified provider. Returns (symbol, price, 24h_change) or None."""
	symbol = symbol.lower()
	
	# بررسی اینکه آیا ارز در لیست فعال است یا نه
	store = load_store()
	enabled_currencies = store.get('enabled_currencies', {})
	
	if symbol not in enabled_currencies:
		# اگر ارز در لیست فعال نیست، از API های پیش‌فرض استفاده کن
		provider_key = (provider or "").lower()
		if provider_key == "binance":
			res = await get_price_by_symbol_binance(symbol)
			if res:
				return res
		return await get_price_by_symbol(symbol)
	
	currency_data = enabled_currencies[symbol]
	if not currency_data.get('enabled', False):
		return None
	
	# استفاده از API ثبت شده
	api_id = currency_data.get('api')
	if api_id:
		api_configs = store.get('api_configs', {})
		api_config = api_configs.get(api_id)
		
		if api_config and api_config.get('enabled', False):
			# استفاده از API سفارشی
			result = await get_price_from_custom_api(symbol, api_config)
			if result:
				return result
	
	# استفاده از API های پیش‌فرض
	provider_key = (provider or "").lower()
	if provider_key == "binance":
		res = await get_price_by_symbol_binance(symbol)
		if res:
			return res
		# fallback to coingecko if binance fails
	return await get_price_by_symbol(symbol)

async def get_price_from_custom_api(symbol: str, api_config: dict) -> Optional[Tuple[str, float, Optional[float]]]:
	"""دریافت قیمت از API سفارشی"""
	try:
		api_type = api_config.get('type', 'crypto')
		api_key = api_config.get('key', '')
		api_url = api_config.get('url', '')
		
		if api_type == 'crypto':
			if 'coingecko' in api_url.lower():
				return await get_price_from_coingecko_api(symbol, api_key, api_url)
			elif 'binance' in api_url.lower():
				return await get_price_from_binance_api(symbol, api_key, api_url)
			else:
				# API سفارشی دیگر
				return await get_price_from_generic_api(symbol, api_config)
		
		return None
		
	except Exception as e:
		print(f"خطا در دریافت قیمت از API سفارشی: {e}")
		return None

async def get_price_from_coingecko_api(symbol: str, api_key: str, api_url: str) -> Optional[Tuple[str, float, Optional[float]]]:
	"""دریافت قیمت از CoinGecko API سفارشی"""
	try:
		coin_id = SYMBOL_TO_CG_ID.get(symbol.lower())
		if not coin_id:
			return None
		
		url = f"{api_url}/simple/price"
		params = {
			"ids": coin_id,
			"vs_currencies": "usd",
			"include_24hr_change": "true",
		}
		
		if api_key:
			params["x_cg_demo_api_key"] = api_key
		
		async with aiohttp.ClientSession() as session:
			async with session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=10)) as resp:
				if resp.status == 200:
					data = await resp.json()
					info = data.get(coin_id)
					if info:
						price = float(info.get("usd", 0))
						change = info.get("usd_24h_change")
						change = float(change) if change is not None else None
						return symbol.upper(), price, change
		
		return None
		
	except Exception as e:
		print(f"خطا در دریافت قیمت از CoinGecko API: {e}")
		return None

async def get_price_from_binance_api(symbol: str, api_key: str, api_url: str) -> Optional[Tuple[str, float, Optional[float]]]:
	"""دریافت قیمت از Binance API سفارشی"""
	try:
		symbol = symbol.upper() + "USDT"
		url = f"{api_url}/ticker/24hr"
		params = {"symbol": symbol}
		
		headers = {}
		if api_key:
			headers["X-MBX-APIKEY"] = api_key
		
		async with aiohttp.ClientSession() as session:
			async with session.get(url, params=params, headers=headers, timeout=aiohttp.ClientTimeout(total=10)) as resp:
				if resp.status == 200:
					data = await resp.json()
					price = float(data.get("lastPrice", 0))
					change = float(data.get("priceChangePercent", 0))
					return symbol.replace("USDT", ""), price, change
		
		return None
		
	except Exception as e:
		print(f"خطا در دریافت قیمت از Binance API: {e}")
		return None

async def get_price_from_generic_api(symbol: str, api_config: dict) -> Optional[Tuple[str, float, Optional[float]]]:
	"""دریافت قیمت از API عمومی"""
	try:
		api_url = api_config.get('url', '')
		api_key = api_config.get('key', '')
		
		# ساخت URL با پارامترها
		url = f"{api_url}/price/{symbol.upper()}"
		
		headers = {}
		if api_key:
			headers["Authorization"] = f"Bearer {api_key}"
			headers["X-API-Key"] = api_key
		
		async with aiohttp.ClientSession() as session:
			async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=10)) as resp:
				if resp.status == 200:
					data = await resp.json()
					
					# تلاش برای استخراج قیمت از پاسخ
					price = None
					change = None
					
					if isinstance(data, dict):
						price = data.get("price") or data.get("last") or data.get("close")
						change = data.get("change_24h") or data.get("change_percent") or data.get("change")
					
					if price:
						price = float(price)
						change = float(change) if change is not None else None
						return symbol.upper(), price, change
		
		return None
		
	except Exception as e:
		print(f"خطا در دریافت قیمت از API عمومی: {e}")
		return None

def format_price_message(symbol: str, price: float, change_24h: Optional[float]) -> str:
	arrow = "" if change_24h is None else ("📈" if change_24h >= 0 else "📉")
	change_txt = "نامشخص" if change_24h is None else f"{change_24h:.2f}% {arrow}"
	return (
		f"قیمت لحظه‌ای {symbol}:\n"
		f"💵 {price:,.4f} دلار\n"
		f"تغییر ۲۴ساعته: {change_txt}"
	)


if __name__ == "__main__":
	# Quick manual test
	async def _test():
		for sym in ["btc", "eth", "sol", "xrp"]:
			print("Testing", sym)
			res = await get_price_by_symbol(sym)
			print(res)
	asyncio.run(_test())
