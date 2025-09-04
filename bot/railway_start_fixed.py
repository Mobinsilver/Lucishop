#!/usr/bin/env python3
"""
Fixed Railway startup script for Telegram Bot
This script properly handles async/await issues
"""

import os
import sys
import asyncio
import logging
from pathlib import Path

# Add current directory to Python path
sys.path.insert(0, str(Path(__file__).parent))

# Configure logging for Railway
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

def check_environment_variables():
    """Check if all required environment variables are set"""
    required_vars = [
        'BOT_TOKEN',
        'OWNER_ID',
        'ADMIN_ID'
    ]
    
    missing_vars = []
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        logger.error(f"Missing required environment variables: {', '.join(missing_vars)}")
        logger.error("Please set these variables in Railway dashboard")
        return False
    
    logger.info("✅ All required environment variables are set")
    return True

def setup_railway_config():
    """Setup Railway-specific configurations"""
    # Set Railway-specific environment variables
    os.environ.setdefault('RAILWAY_ENVIRONMENT', 'production')
    os.environ.setdefault('RAILWAY_DEPLOYMENT_ID', os.getenv('RAILWAY_DEPLOYMENT_ID', 'unknown'))
    
    # Configure bot for Railway
    os.environ.setdefault('BOT_ENV', 'production')
    os.environ.setdefault('LOG_LEVEL', 'INFO')
    
    logger.info("🚀 Railway configuration setup complete")

async def start_bot_async():
    """Start the Telegram bot asynchronously"""
    try:
        # Import and start the bot
        from main import main
        
        logger.info("🤖 Starting Telegram Bot on Railway...")
        await main()
        
    except Exception as e:
        logger.error(f"❌ Failed to start bot: {e}")
        raise

def main():
    """Main entry point for Railway"""
    logger.info("🚀 Railway Bot Startup Script (Fixed)")
    
    # Check environment variables
    if not check_environment_variables():
        sys.exit(1)
    
    # Setup Railway configuration
    setup_railway_config()
    
    # Start the bot
    try:
        asyncio.run(start_bot_async())
    except KeyboardInterrupt:
        logger.info("🛑 Bot stopped by user")
    except Exception as e:
        logger.error(f"❌ Bot crashed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
