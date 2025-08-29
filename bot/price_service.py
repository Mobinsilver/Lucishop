import asyncio
from typing import Dict, Optional, Tuple

import httpx

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


async def fetch_json(client: httpx.AsyncClient, url: str, params: Optional[Dict[str, str]] = None) -> dict:
	r = await client.get(url, params=params)
	r.raise_for_status()
	return r.json()


async def get_price_by_cgid(coin_id: str) -> Optional[Tuple[float, Optional[float]]]:
	"""Return (usd_price, usd_24h_change) or None if not found."""
	url = f"{COINGECKO_API}/simple/price"
	params = {
		"ids": coin_id,
		"vs_currencies": "usd",
		"include_24hr_change": "true",
	}
	async with httpx.AsyncClient(timeout=10.0) as client:
		try:
			data = await fetch_json(client, url, params)
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
		async with httpx.AsyncClient(timeout=10.0) as client:
			p_resp = await client.get(f"{BINANCE_API}/ticker/price", params={"symbol": pair})
			p_resp.raise_for_status()
			p = p_resp.json()
			price = float(p.get("price"))
			c_resp = await client.get(f"{BINANCE_API}/ticker/24hr", params={"symbol": pair})
			c_resp.raise_for_status()
			j = c_resp.json()
			change = float(j.get("priceChangePercent")) if j.get("priceChangePercent") is not None else None
			return sym, price, change
	except Exception:
		return None


async def get_crypto_price_with_provider(symbol: str, provider: str) -> Optional[Tuple[str, float, Optional[float]]]:
	provider_key = (provider or "").lower()
	if provider_key == "binance":
		res = await get_price_by_symbol_binance(symbol)
		if res:
			return res
		# fallback to coingecko if binance fails
	return await get_price_by_symbol(symbol)


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
