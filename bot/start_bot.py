#!/usr/bin/env python3
"""
Simple bot startup script for Railway
This script avoids all async/await issues
"""

import os
import sys
import logging
from pathlib import Path

# Add current directory to Python path
sys.path.insert(0, str(Path(__file__).parent))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

def main():
    """Main entry point"""
    logger.info("🚀 Starting Crypto Navasan Bot...")
    
    # Set environment variables if not set
    os.environ.setdefault('BOT_TOKEN', '8308884100:AAEfcSUiiBKV-YIUZs8PUaV6Ik9Gh-3nvZE')
    os.environ.setdefault('OWNER_ID', '5803428693')
    os.environ.setdefault('ADMIN_ID', '5803428693')
    os.environ.setdefault('BOT_USERNAME', 'Crypto_navasan_bot')
    os.environ.setdefault('PORT', '3000')
    os.environ.setdefault('ENVIRONMENT', 'production')
    os.environ.setdefault('LOG_LEVEL', 'INFO')
    
    logger.info("✅ Environment variables set")
    logger.info("🤖 Starting Telegram Bot...")
    
    try:
        # Import and run the bot
        from main import main as bot_main
        bot_main()
    except KeyboardInterrupt:
        logger.info("🛑 Bot stopped by user")
    except Exception as e:
        logger.error(f"❌ Bot crashed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
