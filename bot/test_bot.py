#!/usr/bin/env python3
"""
🧪 تست ربات Crypto Navasan Bot
این فایل برای تست عملکرد ربات استفاده می‌شود
"""

import asyncio
import sys
import os
from datetime import datetime

# اضافه کردن مسیر پروژه
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

async def test_imports():
    """تست import کردن ماژول‌ها"""
    print("🔍 تست Import ها...")
    
    try:
        import main
        print("✅ main.py import شد")
    except Exception as e:
        print(f"❌ خطا در import main.py: {e}")
        return False
    
    try:
        import config
        print("✅ config.py import شد")
    except Exception as e:
        print(f"❌ خطا در import config.py: {e}")
        return False
    
    try:
        from price_service import get_crypto_price_with_provider
        print("✅ price_service.py import شد")
    except Exception as e:
        print(f"❌ خطا در import price_service.py: {e}")
        return False
    
    try:
        from fiat_service import get_fiat_rate_with_provider
        print("✅ fiat_service.py import شد")
    except Exception as e:
        print(f"❌ خطا در import fiat_service.py: {e}")
        return False
    
    try:
        from news_service import get_news
        print("✅ news_service.py import شد")
    except Exception as e:
        print(f"❌ خطا در import news_service.py: {e}")
        return False
    
    try:
        from admin_panel import admin_panel
        print("✅ admin_panel.py import شد")
    except Exception as e:
        print(f"❌ خطا در import admin_panel.py: {e}")
        return False
    
    return True

async def test_config():
    """تست تنظیمات"""
    print("\n🔧 تست تنظیمات...")
    
    try:
        import config
        
        # تست توکن ربات
        if config.TELEGRAM_BOT_TOKEN:
            print(f"✅ توکن ربات: {config.TELEGRAM_BOT_TOKEN[:20]}...")
        else:
            print("❌ توکن ربات تنظیم نشده")
            return False
        
        # تست آیدی مالک
        if config.OWNER_ID:
            print(f"✅ آیدی مالک: {config.OWNER_ID}")
        else:
            print("❌ آیدی مالک تنظیم نشده")
            return False
        
        # تست یوزرنیم ربات
        if config.BOT_USERNAME:
            print(f"✅ یوزرنیم ربات: {config.BOT_USERNAME}")
        else:
            print("❌ یوزرنیم ربات تنظیم نشده")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ خطا در تست تنظیمات: {e}")
        return False

async def test_services():
    """تست سرویس‌ها"""
    print("\n🌐 تست سرویس‌ها...")
    
    try:
        from price_service import get_crypto_price_with_provider
        
        # تست دریافت قیمت BTC
        print("🔍 تست دریافت قیمت BTC...")
        result = await get_crypto_price_with_provider("btc", "coingecko")
        if result:
            symbol, price, change = result
            print(f"✅ قیمت {symbol}: ${price:,.2f} ({change:+.2f}% if change else 'نامشخص')")
        else:
            print("❌ خطا در دریافت قیمت BTC")
            return False
        
        # تست دریافت قیمت ETH
        print("🔍 تست دریافت قیمت ETH...")
        result = await get_crypto_price_with_provider("eth", "coingecko")
        if result:
            symbol, price, change = result
            print(f"✅ قیمت {symbol}: ${price:,.2f} ({change:+.2f}% if change else 'نامشخص')")
        else:
            print("❌ خطا در دریافت قیمت ETH")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ خطا در تست سرویس‌ها: {e}")
        return False

async def test_fiat_service():
    """تست سرویس ارزهای فیات"""
    print("\n💱 تست سرویس ارزهای فیات...")
    
    try:
        from fiat_service import get_fiat_rate_with_provider
        
        # تست دریافت نرخ EUR
        print("🔍 تست دریافت نرخ EUR...")
        result = await get_fiat_rate_with_provider("EUR", "exchangerate_host", "USD")
        if result:
            code, rate, base = result
            print(f"✅ نرخ {code}/{base}: {rate:.4f}")
        else:
            print("❌ خطا در دریافت نرخ EUR")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ خطا در تست سرویس فیات: {e}")
        return False

async def test_news_service():
    """تست سرویس اخبار"""
    print("\n📰 تست سرویس اخبار...")
    
    try:
        from news_service import get_news
        
        # تست دریافت اخبار
        print("🔍 تست دریافت اخبار...")
        news = await get_news(per_feed=2)
        if news:
            print(f"✅ {len(news)} خبر دریافت شد")
            for i, item in enumerate(news[:3], 1):
                title = item.get("title", "")[:50]
                print(f"   {i}. {title}...")
        else:
            print("❌ خطا در دریافت اخبار")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ خطا در تست سرویس اخبار: {e}")
        return False

async def test_store():
    """تست سیستم ذخیره‌سازی"""
    print("\n💾 تست سیستم ذخیره‌سازی...")
    
    try:
        from store import load_store, save_store
        
        # تست بارگذاری store
        print("🔍 تست بارگذاری store...")
        store = load_store()
        if store:
            print("✅ store بارگذاری شد")
            print(f"   مالک: {store.get('owner_id')}")
            print(f"   ادمین‌ها: {len(store.get('admins', []))}")
            print(f"   کاربران: {len(store.get('users', []))}")
        else:
            print("❌ خطا در بارگذاری store")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ خطا در تست store: {e}")
        return False

async def test_cache():
    """تست سیستم کش"""
    print("\n🗄️ تست سیستم کش...")
    
    try:
        from cache import TTLCache
        
        # تست کش
        print("🔍 تست سیستم کش...")
        cache = TTLCache()
        
        # اضافه کردن آیتم
        cache.set("test_key", "test_value", 60)
        
        # دریافت آیتم
        value = cache.get("test_key")
        if value == "test_value":
            print("✅ سیستم کش کار می‌کند")
        else:
            print("❌ خطا در سیستم کش")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ خطا در تست کش: {e}")
        return False

async def test_security():
    """تست سیستم امنیتی"""
    print("\n🛡️ تست سیستم امنیتی...")
    
    try:
        from security import check_black_white, touch_rate_limit
        
        # تست بررسی لیست سیاه/سفید
        print("🔍 تست بررسی لیست سیاه/سفید...")
        allowed, reason = check_black_white(123456789)
        if allowed:
            print("✅ سیستم لیست سیاه/سفید کار می‌کند")
        else:
            print(f"⚠️ کاربر در لیست سیاه/سفید: {reason}")
        
        # تست rate limiting
        print("🔍 تست rate limiting...")
        ok, reason = touch_rate_limit(123456789)
        if ok:
            print("✅ سیستم rate limiting کار می‌کند")
        else:
            print(f"⚠️ Rate limit: {reason}")
        
        return True
        
    except Exception as e:
        print(f"❌ خطا در تست امنیت: {e}")
        return False

async def main():
    """تابع اصلی تست"""
    print("🤖 تست ربات Crypto Navasan Bot")
    print("=" * 50)
    print(f"📅 تاریخ: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    tests = [
        ("Import ها", test_imports),
        ("تنظیمات", test_config),
        ("سرویس قیمت", test_services),
        ("سرویس فیات", test_fiat_service),
        ("سرویس اخبار", test_news_service),
        ("سیستم ذخیره‌سازی", test_store),
        ("سیستم کش", test_cache),
        ("سیستم امنیتی", test_security),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        try:
            result = await test_func()
            if result:
                passed += 1
            else:
                print(f"❌ تست {test_name} ناموفق")
        except Exception as e:
            print(f"❌ خطا در تست {test_name}: {e}")
    
    print("\n" + "=" * 50)
    print(f"📊 نتیجه نهایی: {passed}/{total} تست موفق")
    
    if passed == total:
        print("🎉 تمام تست‌ها موفق بود! ربات آماده است.")
        return True
    else:
        print("⚠️ برخی تست‌ها ناموفق بود. لطفاً مشکلات را بررسی کنید.")
        return False

if __name__ == "__main__":
    try:
        result = asyncio.run(main())
        sys.exit(0 if result else 1)
    except KeyboardInterrupt:
        print("\n⏹️ تست متوقف شد.")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ خطای غیرمنتظره: {e}")
        sys.exit(1)