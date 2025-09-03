import numpy as np
from typing import List, Optional, Tuple, Dict
import aiohttp
from price_service import SYMBOL_TO_CG_ID

COINGECKO_API = "https://api.coingecko.com/api/v3"


async def fetch_ohlcv_data(coin_id: str, days: int = 30) -> Optional[List[Dict]]:
    """Fetch OHLCV data from CoinGecko"""
    url = f"{COINGECKO_API}/coins/{coin_id}/ohlc"
    params = {"vs_currency": "usd", "days": str(days)}
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=10)) as r:
                r.raise_for_status()
                data = await r.json()
                return data
    except Exception:
        return None


def calculate_sma(prices: List[float], period: int) -> List[float]:
    """Calculate Simple Moving Average"""
    if len(prices) < period:
        return []
    
    sma = []
    for i in range(period - 1, len(prices)):
        sma.append(sum(prices[i - period + 1:i + 1]) / period)
    return sma


def calculate_ema(prices: List[float], period: int) -> List[float]:
    """Calculate Exponential Moving Average"""
    if len(prices) < period:
        return []
    
    ema = [prices[0]]
    multiplier = 2 / (period + 1)
    
    for i in range(1, len(prices)):
        ema.append((prices[i] * multiplier) + (ema[i-1] * (1 - multiplier)))
    
    return ema


def calculate_rsi(prices: List[float], period: int = 14) -> List[float]:
    """Calculate Relative Strength Index"""
    if len(prices) < period + 1:
        return []
    
    deltas = [prices[i] - prices[i-1] for i in range(1, len(prices))]
    gains = [delta if delta > 0 else 0 for delta in deltas]
    losses = [-delta if delta < 0 else 0 for delta in deltas]
    
    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period
    
    rsi = []
    for i in range(period, len(prices)):
        if avg_loss == 0:
            rsi.append(100)
        else:
            rs = avg_gain / avg_loss
            rsi_value = 100 - (100 / (1 + rs))
            rsi.append(rsi_value)
        
        # Update averages
        if i < len(prices) - 1:
            avg_gain = (avg_gain * (period - 1) + gains[i]) / period
            avg_loss = (avg_loss * (period - 1) + losses[i]) / period
    
    return rsi


def calculate_macd(prices: List[float], fast: int = 12, slow: int = 26, signal: int = 9) -> Tuple[List[float], List[float], List[float]]:
    """Calculate MACD (Moving Average Convergence Divergence)"""
    if len(prices) < slow:
        return [], [], []
    
    ema_fast = calculate_ema(prices, fast)
    ema_slow = calculate_ema(prices, slow)
    
    # MACD line
    macd_line = []
    for i in range(len(ema_slow)):
        if i < len(ema_fast) - (slow - fast):
            macd_line.append(ema_fast[i + (slow - fast)] - ema_slow[i])
    
    if len(macd_line) < signal:
        return macd_line, [], []
    
    # Signal line
    signal_line = calculate_ema(macd_line, signal)
    
    # Histogram
    histogram = []
    for i in range(len(signal_line)):
        if i < len(macd_line):
            histogram.append(macd_line[i] - signal_line[i])
    
    return macd_line, signal_line, histogram


def calculate_bollinger_bands(prices: List[float], period: int = 20, std_dev: float = 2) -> Tuple[List[float], List[float], List[float]]:
    """Calculate Bollinger Bands"""
    if len(prices) < period:
        return [], [], []
    
    sma = calculate_sma(prices, period)
    upper_band = []
    lower_band = []
    
    for i in range(len(sma)):
        start_idx = i
        end_idx = start_idx + period
        if end_idx > len(prices):
            break
        
        window = prices[start_idx:end_idx]
        std = np.std(window)
        
        upper_band.append(sma[i] + (std_dev * std))
        lower_band.append(sma[i] - (std_dev * std))
    
    return sma, upper_band, lower_band


def get_support_resistance(prices: List[float], window: int = 20) -> Tuple[float, float]:
    """Calculate support and resistance levels"""
    if len(prices) < window:
        return min(prices), max(prices)
    
    recent_prices = prices[-window:]
    return min(recent_prices), max(recent_prices)


async def get_technical_analysis(symbol: str, days: int = 30) -> Optional[Dict]:
    """Get comprehensive technical analysis for a symbol"""
    coin_id = SYMBOL_TO_CG_ID.get(symbol.lower())
    if not coin_id:
        return None
    
    ohlcv_data = await fetch_ohlcv_data(coin_id, days)
    if not ohlcv_data:
        return None
    
    # Extract closing prices
    prices = [float(candle[4]) for candle in ohlcv_data]  # Close price is at index 4
    
    if len(prices) < 20:
        return None
    
    # Calculate indicators
    sma_20 = calculate_sma(prices, 20)
    sma_50 = calculate_sma(prices, 50)
    ema_12 = calculate_ema(prices, 12)
    ema_26 = calculate_ema(prices, 26)
    rsi = calculate_rsi(prices, 14)
    macd_line, signal_line, histogram = calculate_macd(prices)
    bb_middle, bb_upper, bb_lower = calculate_bollinger_bands(prices)
    support, resistance = get_support_resistance(prices)
    
    # Current values
    current_price = prices[-1]
    current_rsi = rsi[-1] if rsi else None
    current_macd = macd_line[-1] if macd_line else None
    current_signal = signal_line[-1] if signal_line else None
    
    # Generate signals
    signals = []
    
    # RSI signals
    if current_rsi:
        if current_rsi > 70:
            signals.append("RSI: Overbought (>70)")
        elif current_rsi < 30:
            signals.append("RSI: Oversold (<30)")
    
    # MACD signals
    if current_macd and current_signal:
        if current_macd > current_signal:
            signals.append("MACD: Bullish (above signal)")
        else:
            signals.append("MACD: Bearish (below signal)")
    
    # Moving average signals
    if sma_20 and sma_50:
        if current_price > sma_20[-1] and sma_20[-1] > sma_50[-1]:
            signals.append("MA: Bullish trend")
        elif current_price < sma_20[-1] and sma_20[-1] < sma_50[-1]:
            signals.append("MA: Bearish trend")
    
    # Bollinger Bands signals
    if bb_upper and bb_lower:
        if current_price > bb_upper[-1]:
            signals.append("BB: Price above upper band")
        elif current_price < bb_lower[-1]:
            signals.append("BB: Price below lower band")
    
    return {
        "symbol": symbol.upper(),
        "current_price": current_price,
        "support": support,
        "resistance": resistance,
        "rsi": current_rsi,
        "macd": current_macd,
        "macd_signal": current_signal,
        "sma_20": sma_20[-1] if sma_20 else None,
        "sma_50": sma_50[-1] if sma_50 else None,
        "ema_12": ema_12[-1] if ema_12 else None,
        "ema_26": ema_26[-1] if ema_26 else None,
        "bb_upper": bb_upper[-1] if bb_upper else None,
        "bb_lower": bb_lower[-1] if bb_lower else None,
        "signals": signals,
        "price_change_24h": ((current_price - prices[-2]) / prices[-2] * 100) if len(prices) > 1 else 0
    }


def format_ta_message(ta_data: Dict) -> str:
    """Format technical analysis data into a readable message"""
    if not ta_data:
        return "تحلیل تکنیکال در دسترس نیست."
    
    msg = f"📊 تحلیل تکنیکال {ta_data['symbol']}\n\n"
    msg += f"💰 قیمت فعلی: ${ta_data['current_price']:,.2f}\n"
    msg += f"📈 تغییر ۲۴ساعته: {ta_data['price_change_24h']:+.2f}%\n\n"
    
    if ta_data['rsi']:
        msg += f"📊 RSI: {ta_data['rsi']:.1f}\n"
    
    if ta_data['macd']:
        msg += f"📈 MACD: {ta_data['macd']:.4f}\n"
    
    if ta_data['sma_20']:
        msg += f"📉 SMA(20): ${ta_data['sma_20']:,.2f}\n"
    
    if ta_data['sma_50']:
        msg += f"📉 SMA(50): ${ta_data['sma_50']:,.2f}\n"
    
    msg += f"\n🛡️ حمایت: ${ta_data['support']:,.2f}\n"
    msg += f"🎯 مقاومت: ${ta_data['resistance']:,.2f}\n"
    
    if ta_data['signals']:
        msg += "\n🔔 سیگنال‌ها:\n"
        for signal in ta_data['signals']:
            msg += f"• {signal}\n"
    
    return msg


async def get_simple_ta(symbol: str) -> str:
    """Get simple technical analysis for quick overview"""
    ta_data = await get_technical_analysis(symbol, days=30)
    return format_ta_message(ta_data)



