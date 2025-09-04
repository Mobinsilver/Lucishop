from typing import Optional, Tuple

from price_service import get_price_by_symbol as cg_price, get_price_by_symbol_binance as bin_price


async def compare_prices(symbol: str) -> Optional[Tuple[str, float, float, float]]:
	"""Return (SYM, coingecko_price, binance_price, diff_pct) or None."""
	sym = symbol.strip().upper()
	cg = await cg_price(sym)
	bn = await bin_price(sym)
	if not cg and not bn:
		return None
	cg_p = cg[1] if cg else None
	bn_p = bn[1] if bn else None
	if cg_p is None and bn_p is None:
		return None
	# if one missing, set to 0 for diff calc and handle accordingly
	if cg_p is None:
		return sym, 0.0, float(bn_p), 0.0
	if bn_p is None:
		return sym, float(cg_p), 0.0, 0.0
	diff_pct = ((bn_p - cg_p) / cg_p) * 100.0 if cg_p else 0.0
	return sym, float(cg_p), float(bn_p), float(diff_pct)



