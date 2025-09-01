#!/usr/bin/env python3
"""
Test script for the Telegram bot
Run this script to test core functionality before deployment
"""

import asyncio
import sys
import os

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from price_service import get_crypto_price_with_provider, SYMBOL_TO_CG_ID
from fiat_service import get_fiat_rate_with_provider
from news_service import get_news
from history import fetch_history_prices, sparkline
from arbitrage import compare_prices
from p2p_service import fetch_binance_p2p, summarize_p2p_offers
from ta import get_technical_analysis
from store import load_store, save_store, get_user_data
from cache import TTLCache


async def test_price_service():
    """Test price service functionality"""
    print("🔍 Testing Price Service...")
    
    # Test basic price lookup
    result = await get_crypto_price_with_provider("btc", "coingecko")
    if result:
        symbol, price, change = result
        print(f"✅ BTC Price: ${price:,.2f} ({change:+.2f}%)")
    else:
        print("❌ Failed to get BTC price")
        return False
    
    # Test symbol mapping
    print(f"✅ Supported symbols: {len(SYMBOL_TO_CG_ID)}")
    
    return True


async def test_fiat_service():
    """Test fiat service functionality"""
    print("\n🔍 Testing Fiat Service...")
    
    result = await get_fiat_rate_with_provider("EUR", "exchangerate_host", "USD")
    if result:
        code, rate, base = result
        print(f"✅ EUR/USD Rate: {rate:.4f}")
    else:
        print("❌ Failed to get EUR rate")
        return False
    
    return True


async def test_news_service():
    """Test news service functionality"""
    print("\n🔍 Testing News Service...")
    
    news = await get_news(per_feed=2)
    if news:
        print(f"✅ Got {len(news)} news items")
        for item in news[:2]:
            print(f"   📰 {item.get('title', 'No title')[:50]}...")
    else:
        print("❌ Failed to get news")
        return False
    
    return True


async def test_history_service():
    """Test history service functionality"""
    print("\n🔍 Testing History Service...")
    
    # Test with BTC
    coin_id = SYMBOL_TO_CG_ID.get("btc")
    if coin_id:
        series = await fetch_history_prices(coin_id, days=7)
        if series:
            spark = sparkline(series)
            print(f"✅ BTC Sparkline: {spark}")
        else:
            print("❌ Failed to get BTC history")
            return False
    else:
        print("❌ BTC not found in symbol mapping")
        return False
    
    return True


async def test_arbitrage_service():
    """Test arbitrage service functionality"""
    print("\n🔍 Testing Arbitrage Service...")
    
    result = await compare_prices("btc")
    if result:
        sym, cg_p, bn_p, diff = result
        print(f"✅ BTC Comparison:")
        print(f"   CoinGecko: ${cg_p:,.2f}")
        print(f"   Binance: ${bn_p:,.2f}")
        print(f"   Difference: {diff:.2f}%")
    else:
        print("❌ Failed to compare prices")
        return False
    
    return True


async def test_p2p_service():
    """Test P2P service functionality"""
    print("\n🔍 Testing P2P Service...")
    
    data = await fetch_binance_p2p(asset="USDT", fiat="IRR", trade_type="SELL")
    if data:
        summary = summarize_p2p_offers(data)
        print(f"✅ P2P Data: {len(data)} offers")
        print(f"   Summary: {summary[:100]}...")
    else:
        print("❌ Failed to get P2P data")
        return False
    
    return True


async def test_technical_analysis():
    """Test technical analysis functionality"""
    print("\n🔍 Testing Technical Analysis...")
    
    ta_data = await get_technical_analysis("btc", days=30)
    if ta_data:
        print(f"✅ Technical Analysis for {ta_data['symbol']}:")
        print(f"   Current Price: ${ta_data['current_price']:,.2f}")
        print(f"   RSI: {ta_data['rsi']:.1f}" if ta_data['rsi'] else "   RSI: N/A")
        print(f"   Support: ${ta_data['support']:,.2f}")
        print(f"   Resistance: ${ta_data['resistance']:,.2f}")
    else:
        print("❌ Failed to get technical analysis")
        return False
    
    return True


async def test_store_service():
    """Test store service functionality"""
    print("\n🔍 Testing Store Service...")
    
    # Test store loading
    store = load_store()
    if store:
        print("✅ Store loaded successfully")
        
        # Test user data
        test_user_id = 123456789
        user_data = get_user_data(store, test_user_id)
        if user_data:
            print("✅ User data created successfully")
            
            # Test saving
            try:
                save_store(store)
                print("✅ Store saved successfully")
            except Exception as e:
                print(f"❌ Failed to save store: {e}")
                return False
        else:
            print("❌ Failed to create user data")
            return False
    else:
        print("❌ Failed to load store")
        return False
    
    return True


async def test_cache_service():
    """Test cache service functionality"""
    print("\n🔍 Testing Cache Service...")
    
    cache = TTLCache()
    
    # Test setting and getting
    cache.set("test_key", "test_value", ttl_seconds=10)
    value = cache.get("test_key")
    
    if value == "test_value":
        print("✅ Cache set/get working")
    else:
        print("❌ Cache set/get failed")
        return False
    
    # Test TTL
    cache.set("expire_key", "expire_value", ttl_seconds=1)
    await asyncio.sleep(2)
    expired_value = cache.get("expire_key")
    
    if expired_value is None:
        print("✅ Cache TTL working")
    else:
        print("❌ Cache TTL failed")
        return False
    
    return True


async def main():
    """Run all tests"""
    print("🚀 Starting Bot Tests...\n")
    
    tests = [
        ("Price Service", test_price_service),
        ("Fiat Service", test_fiat_service),
        ("News Service", test_news_service),
        ("History Service", test_history_service),
        ("Arbitrage Service", test_arbitrage_service),
        ("P2P Service", test_p2p_service),
        ("Technical Analysis", test_technical_analysis),
        ("Store Service", test_store_service),
        ("Cache Service", test_cache_service),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        try:
            if await test_func():
                passed += 1
            else:
                print(f"❌ {test_name} test failed")
        except Exception as e:
            print(f"❌ {test_name} test error: {e}")
    
    print(f"\n📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Bot is ready for deployment.")
        return True
    else:
        print("⚠️  Some tests failed. Please fix issues before deployment.")
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)

