import asyncio
from typing import Dict, Optional, Tuple

import aiohttp

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
	if prov == "frankfurter":
		rates = await fetch_fiat_rates_frankfurter(base=base)
		code = symbol.strip().upper()
		if not rates or code not in rates:
			return None
		return code, float(rates[code]), base
	# default exchangerate_host
	return await get_fiat_rate(symbol, base=base)


def format_fiat_message(code: str, rate: float, base: str) -> str:
	return (
		f"نرخ {code} نسبت به {base}:\n"
		f"1 {base} = {rate:,.4f} {code}"
	)


if __name__ == "__main__":
	async def _test():
		print(await get_fiat_rate("EUR"))
	asyncio.run(_test())
