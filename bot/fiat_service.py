import asyncio
from typing import Dict, Optional, Tuple

import aiohttp
from config import BRS_API_URL, BRS_API_KEY

EXR_API = "https://api.exchangerate.host/latest"
FRANKFURTER_API = "https://api.frankfurter.app/latest"

# Base currency USD by default
DEFAULT_BASE = "USD"

# Common fiat codes to expose in inline menu
FIAT_CODES = [
	"USD", "EUR", "GBP", "CHF", "JPY", "CNY", "AED", "TRY", "CAD", "AUD",
	"SEK", "NOK", "DKK", "RUB", "INR", "PKR", "AFN", "IRR", "QAR", "OMR",
]


async def fetch_fiat_rates(base: str = DEFAULT_BASE) -> Optional[Dict[str, float]]:
	params = {"base": base}
	async with aiohttp.ClientSession() as session:
		try:
			async with session.get(EXR_API, params=params, timeout=aiohttp.ClientTimeout(total=10)) as resp:
				resp.raise_for_status()
				data = await resp.json()
				rates = data.get("rates")
				if not isinstance(rates, dict):
					return None
				return {k: float(v) for k, v in rates.items()}
		except Exception:
			return None


async def fetch_fiat_rates_frankfurter(base: str = DEFAULT_BASE) -> Optional[Dict[str, float]]:
	params = {"from": base}
	async with aiohttp.ClientSession() as session:
		try:
			async with session.get(FRANKFURTER_API, params=params, timeout=aiohttp.ClientTimeout(total=10)) as resp:
				resp.raise_for_status()
				data = await resp.json()
				rates = data.get("rates")
				if not isinstance(rates, dict):
					return None
				return {k: float(v) for k, v in rates.items()}
		except Exception:
			return None


async def get_fiat_rate(symbol: str, base: str = DEFAULT_BASE) -> Optional[Tuple[str, float, str]]:
	"""Return (code, rate, base) where rate is 1 base -> X code."""
	code = symbol.strip().upper()
	rates = await fetch_fiat_rates(base=base)
	if not rates or code not in rates:
		return None
	return code, float(rates[code]), base


async def get_fiat_rate_with_provider(symbol: str, provider: str, base: str = DEFAULT_BASE) -> Optional[Tuple[str, float, str]]:
	prov = (provider or "").lower()
	
	# اولویت: BRS > Frankfurter > ExchangeRate
	if prov == "brs":
		result = await get_brs_fiat_rate(symbol)
		if result:
			code, rate = result
			return code, rate, base
	elif prov == "frankfurter":
		rates = await fetch_fiat_rates_frankfurter(base=base)
		code = symbol.strip().upper()
		if not rates or code not in rates:
			return None
		return code, float(rates[code]), base
	
	# Fallback به BRS اگر provider مشخص نشده
	if not prov or prov == "exchangerate":
		result = await get_brs_fiat_rate(symbol)
		if result:
			code, rate = result
			return code, rate, base
	
	# آخرین fallback به ExchangeRate
	return await get_fiat_rate(symbol, base=base)


def format_fiat_message(code: str, rate: float, base: str) -> str:
	return (
		f"نرخ {code} نسبت به {base}:\n"
		f"1 {base} = {rate:,.4f} {code}"
	)


async def get_brs_fiat_rate(symbol: str) -> Optional[Tuple[str, float]]:
	"""دریافت نرخ ارز از API BRS"""
	try:
		headers = {
			'Authorization': f'Bearer {BRS_API_KEY}',
			'Content-Type': 'application/json'
		}
		
		url = f"{BRS_API_URL}/fiat/rate"
		params = {'symbol': symbol.upper()}
		
		async with aiohttp.ClientSession() as session:
			async with session.get(url, headers=headers, params=params, timeout=aiohttp.ClientTimeout(total=10)) as resp:
				if resp.status == 200:
					data = await resp.json()
					if data.get('success') and 'data' in data:
						rate_data = data['data']
						rate = float(rate_data.get('rate', 0))
						return symbol.upper(), rate
		return None
	except Exception as e:
		print(f"خطا در دریافت نرخ ارز از BRS: {e}")
		return None


if __name__ == "__main__":
	async def _test():
		print(await get_fiat_rate("EUR"))
	asyncio.run(_test())
