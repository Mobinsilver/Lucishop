#!/usr/bin/env python3
"""
Comprehensive test script for Crypto Navasan Bot
Tests all major functionality before Railway deployment
"""

import os
import sys
import asyncio
from datetime import datetime

# Set environment variables for testing
os.environ["BOT_TOKEN"] = "8308884100:AAEfcSUiiBKV-YIUZs8PUaV6Ik9Gh-3nvZE"
os.environ["OWNER_ID"] = "5803428693"
os.environ["BOT_USERNAME"] = "Crypto_navasan_bot"

def test_imports():
    """Test that all modules can be imported without errors"""
    print("🔍 Testing imports...")
    
    try:
        import main
        print("✅ main.py imported successfully")
    except Exception as e:
        print(f"❌ Failed to import main.py: {e}")
        return False
    
    try:
        import admin_panel
        print("✅ admin_panel.py imported successfully")
    except Exception as e:
        print(f"❌ Failed to import admin_panel.py: {e}")
        return False
    
    try:
        import config
        print("✅ config.py imported successfully")
    except Exception as e:
        print(f"❌ Failed to import config.py: {e}")
        return False
    
    try:
        import store
        print("✅ store.py imported successfully")
    except Exception as e:
        print(f"❌ Failed to import store.py: {e}")
        return False
    
    try:
        import cache
        print("✅ cache.py imported successfully")
    except Exception as e:
        print(f"❌ Failed to import cache.py: {e}")
        return False
    
    try:
        import security
        print("✅ security.py imported successfully")
    except Exception as e:
        print(f"❌ Failed to import security.py: {e}")
        return False
    
    return True

def test_config():
    """Test configuration loading"""
    print("\n🔍 Testing configuration...")
    
    try:
        import config
        
        # Test required environment variables
        if not config.TELEGRAM_BOT_TOKEN:
            print("❌ BOT_TOKEN not set")
            return False
        else:
            print("✅ BOT_TOKEN loaded")
        
        if not config.OWNER_ID:
            print("❌ OWNER_ID not set")
            return False
        else:
            print(f"✅ OWNER_ID loaded: {config.OWNER_ID}")
        
        if not config.BOT_USERNAME:
            print("❌ BOT_USERNAME not set")
            return False
        else:
            print(f"✅ BOT_USERNAME loaded: {config.BOT_USERNAME}")
        
        return True
        
    except Exception as e:
        print(f"❌ Configuration test failed: {e}")
        return False

def test_build_app():
    """Test that build_app function works"""
    print("\n🔍 Testing build_app function...")
    
    try:
        import main
        app = main.build_app()
        
        if app is None:
            print("❌ build_app returned None")
            return False
        
        print("✅ build_app function works")
        return True
        
    except Exception as e:
        print(f"❌ build_app test failed: {e}")
        return False

def test_admin_panel():
    """Test admin panel functionality"""
    print("\n🔍 Testing admin panel...")
    
    try:
        import admin_panel
        
        # Test admin panel instantiation
        panel = admin_panel.AdminPanel()
        
        if panel is None:
            print("❌ AdminPanel instantiation failed")
            return False
        
        print("✅ AdminPanel instantiated successfully")
        
        # Test admin panel methods exist
        if not hasattr(panel, 'handle_admin_panel_text'):
            print("❌ handle_admin_panel_text method missing")
            return False
        
        if not hasattr(panel, 'admin_panel_main'):
            print("❌ admin_panel_main method missing")
            return False
        
        if not hasattr(panel, 'handle_callback'):
            print("❌ handle_callback method missing")
            return False
        
        print("✅ Admin panel methods exist")
        return True
        
    except Exception as e:
        print(f"❌ Admin panel test failed: {e}")
        return False

def test_conversation_states():
    """Test conversation states are properly defined"""
    print("\n🔍 Testing conversation states...")
    
    try:
        import admin_panel
        
        # Check that all required states are defined
        required_states = [
            'ADMIN_PANEL', 'ADD_ADMIN', 'REMOVE_ADMIN', 'BROADCAST_MESSAGE',
            'SET_WELCOME_TEXT', 'SET_HELP_TEXT', 'SET_ERROR_TEXT', 'SET_API_KEY',
            'FORCE_SUBSCRIPTION', 'ADD_WHITELIST', 'ADD_BLACKLIST', 'USER_MESSAGE'
        ]
        
        for state in required_states:
            if not hasattr(admin_panel, state):
                print(f"❌ Missing state: {state}")
                return False
        
        print("✅ All conversation states defined")
        return True
        
    except Exception as e:
        print(f"❌ Conversation states test failed: {e}")
        return False

def test_requirements():
    """Test that all required packages are available"""
    print("\n🔍 Testing requirements...")
    
    required_packages = [
        'telegram',
        'aiohttp',
        'dotenv',
        'pytz',
        'feedparser',
        'numpy',
        'requests',
        'httpx'
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package)
            print(f"✅ {package} available")
        except ImportError:
            print(f"❌ {package} missing")
            missing_packages.append(package)
    
    if missing_packages:
        print(f"❌ Missing packages: {missing_packages}")
        return False
    
    return True

def main():
    """Run all tests"""
    print("🚀 Starting comprehensive bot test...")
    print(f"⏰ Test started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    tests = [
        test_imports,
        test_config,
        test_build_app,
        test_admin_panel,
        test_conversation_states,
        test_requirements
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        try:
            if test():
                passed += 1
            else:
                print(f"❌ Test failed: {test.__name__}")
        except Exception as e:
            print(f"❌ Test error in {test.__name__}: {e}")
    
    print("\n" + "=" * 60)
    print(f"📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Bot is ready for deployment.")
        return True
    else:
        print("❌ Some tests failed. Please fix issues before deployment.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
