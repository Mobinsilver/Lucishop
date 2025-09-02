import httpx
from typing import List, Dict

BINANCE_P2P_API = "https://p2p.binance.com/bapi/c2c/v2/friendly/c2c/adv/search"


async def fetch_binance_p2p(asset: str = "USDT", fiat: str = "IRR", trade_type: str = "SELL", rows: int = 5) -> List[Dict]:
	payload = {
		"asset": asset,
		"fiat": fiat,
		"page": 1,
		"rows": rows,
		"tradeType": trade_type,
	}
	headers = {
		"Content-Type": "application/json",
	}
	try:
		async with httpx.AsyncClient(timeout=10.0) as client:
			r = await client.post(BINANCE_P2P_API, json=payload, headers=headers)
			r.raise_for_status()
			j = r.json()
			return j.get("data", [])
	except Exception:
		return []


def summarize_p2p_offers(data: List[Dict]) -> str:
	if not data:
		return "اطلاعات در دسترس نیست."
	lines = []
	for d in data[:5]:
		adv = d.get("adv", {})
		price = adv.get("price")
		minSingleTransAmount = adv.get("minSingleTransAmount")
		maxSingleTransAmount = adv.get("dynamicMaxSingleTransAmount") or adv.get("maxSingleTransAmount")
		lines.append(f"قیمت: {price} | حداقل: {minSingleTransAmount} | حداکثر: {maxSingleTransAmount}")
	return "\n".join(lines)

