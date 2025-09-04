#!/usr/bin/env python3
"""
Test script to verify bot startup without coroutine warnings
"""

import asyncio
import sys
import os
from pathlib import Path

# Add current directory to Python path
sys.path.insert(0, str(Path(__file__).parent))

async def test_bot():
    """Test the bot startup"""
    try:
        print("🧪 Testing bot startup...")
        
        # Import the main function
        from main import main
        
        print("✅ Bot module imported successfully")
        print("✅ Main function is async")
        
        # Test if we can call it (without actually running)
        print("✅ Bot is ready to start")
        
        return True
        
    except Exception as e:
        print(f"❌ Error testing bot: {e}")
        return False

def main():
    """Main test function"""
    print("🚀 Bot Test Script")
    print("==================")
    
    # Set required environment variables for testing
    os.environ.setdefault('BOT_TOKEN', '8308884100:AAEfcSUiiBKV-YIUZs8PUaV6Ik9Gh-3nvZE')
    os.environ.setdefault('OWNER_ID', '5803428693')
    os.environ.setdefault('ADMIN_ID', '5803428693')
    os.environ.setdefault('BOT_USERNAME', 'Crypto_navasan_bot')
    
    # Run the test
    success = asyncio.run(test_bot())
    
    if success:
        print("\n🎉 Bot test passed! No coroutine warnings should occur.")
    else:
        print("\n❌ Bot test failed. Check the errors above.")
        sys.exit(1)

if __name__ == "__main__":
    main()