import aiohttp
from typing import List, Optional

COINGECKO_API = "https://api.coingecko.com/api/v3"


async def fetch_history_prices(coin_id: str, days: int = 7) -> Optional[List[float]]:
	url = f"{COINGECKO_API}/coins/{coin_id}/market_chart"
	params = {"vs_currency": "usd", "days": str(days)}
	try:
		async with aiohttp.ClientSession() as session:
			async with session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=10)) as r:
				r.raise_for_status()
				j = await r.json()
				prices = j.get("prices") or []
				return [float(p[1]) for p in prices]
	except Exception:
		return None


SPARK_CHARS = "▁▂▃▄▅▆▇█"


def sparkline(values: List[float]) -> str:
	if not values:
		return ""
	mn = min(values)
	mx = max(values)
	if mx == mn:
		return "".join([SPARK_CHARS[0] for _ in values])
	rng = mx - mn
	out = []
	for v in values:
		i = int((v - mn) / rng * (len(SPARK_CHARS) - 1))
		out.append(SPARK_CHARS[i])
	return "".join(out)


