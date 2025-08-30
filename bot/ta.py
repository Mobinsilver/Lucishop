from typing import List, Dict


def sma(values: List[float], period: int) -> List[float]:
	if period <= 1 or period > len(values):
		return [sum(values) / len(values)] * len(values)
	out = []
	for i in range(len(values)):
		start = max(0, i - period + 1)
		window = values[start:i + 1]
		out.append(sum(window) / len(window))
	return out


def rsi(values: List[float], period: int = 14) -> List[float]:
	if len(values) < period + 1:
		return [50.0] * len(values)
	gains, losses = [], []
	for i in range(1, len(values)):
		delta = values[i] - values[i - 1]
		gains.append(max(0.0, delta))
		losses.append(max(0.0, -delta))
	avg_gain = sum(gains[:period]) / period
	avg_loss = sum(losses[:period]) / period
	rsis = [50.0] * period
	for i in range(period, len(values) - 1):
		avg_gain = (avg_gain * (period - 1) + gains[i]) / period
		avg_loss = (avg_loss * (period - 1) + losses[i]) / period
		rs = (avg_gain / avg_loss) if avg_loss != 0 else 0
		rsis.append(100 - (100 / (1 + rs)))
	# align length
	while len(rsis) < len(values):
		rsis.append(rsis[-1])
	return rsis


def macd(values: List[float], fast: int = 12, slow: int = 26, signal: int = 9) -> Dict[str, List[float]]:
	def ema(vals: List[float], p: int) -> List[float]:
		k = 2 / (p + 1)
		out = [vals[0]]
		for v in vals[1:]:
			out.append(v * k + out[-1] * (1 - k))
		return out
	if len(values) < slow + signal:
		line = [0.0] * len(values)
		return {"macd": line, "signal": line, "hist": [0.0] * len(values)}
	fast_ema = ema(values, fast)
	slow_ema = ema(values, slow)
	macd_line = [f - s for f, s in zip(fast_ema, slow_ema)]
	signal_line = ema(macd_line, signal)
	hist = [m - s for m, s in zip(macd_line, signal_line)]
	return {"macd": macd_line, "signal": signal_line, "hist": hist}


def simple_support_resistance(values: List[float]) -> Dict[str, float]:
	if not values:
		return {"support": 0.0, "resistance": 0.0}
	return {"support": min(values), "resistance": max(values)}



