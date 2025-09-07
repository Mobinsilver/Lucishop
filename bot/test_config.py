#!/usr/bin/env python3
"""
تست متغیرهای محیطی برای Railway
"""

import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_env_vars():
    """تست متغیرهای محیطی"""
    print("🔍 بررسی متغیرهای محیطی...")
    
    # متغیرهای ضروری
    required_vars = {
        "BOT_TOKEN": "توکن ربات",
        "OWNER_ID": "شناسه مالک",
        "BOT_USERNAME": "نام کاربری ربات"
    }
    
    # متغیرهای API
    api_vars = {
        "TABDEAL_API_URL": "آدرس API Tabdeal",
        "TABDEAL_API_KEY": "کلید API Tabdeal",
        "TABDEAL_API_SECRET": "رمز API Tabdeal",
        "BRS_API_URL": "آدرس API BRS",
        "BRS_API_KEY": "کلید API BRS"
    }
    
    print("\n📋 متغیرهای ضروری:")
    for var, desc in required_vars.items():
        value = os.getenv(var)
        if value:
            if var == "OWNER_ID":
                try:
                    int(value)
                    print(f"✅ {var}: {value} ({desc})")
                except ValueError:
                    print(f"❌ {var}: {value} - باید عدد باشد!")
            else:
                print(f"✅ {var}: {value[:20]}... ({desc})")
        else:
            print(f"❌ {var}: تعریف نشده ({desc})")
    
    print("\n🔌 متغیرهای API:")
    for var, desc in api_vars.items():
        value = os.getenv(var)
        if value:
            print(f"✅ {var}: {value[:30]}... ({desc})")
        else:
            print(f"❌ {var}: تعریف نشده ({desc})")
    
    print("\n🌍 متغیرهای محیط:")
    env_vars = {
        "ENVIRONMENT": "محیط",
        "DEBUG": "حالت دیباگ",
        "LOG_LEVEL": "سطح لاگ",
        "PORT": "پورت"
    }
    
    for var, desc in env_vars.items():
        value = os.getenv(var, "تعریف نشده")
        print(f"ℹ️  {var}: {value} ({desc})")

if __name__ == "__main__":
    test_env_vars()
