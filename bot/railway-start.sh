#!/bin/bash

echo "🚀 Starting Telegram Bot on Railway..."

# Check if environment variables are set
if [ -z "$TELEGRAM_BOT_TOKEN" ]; then
    echo "❌ ERROR: TELEGRAM_BOT_TOKEN is not set!"
    echo "Please set the TELEGRAM_BOT_TOKEN environment variable in Railway."
    exit 1
fi

echo "✅ Bot token is configured"
echo "🌐 Environment: $ENVIRONMENT"
echo "🔧 Debug mode: $DEBUG"
echo "📡 Port: $PORT"
echo "👤 Owner ID: $OWNER_ID"
echo "👨‍💼 Admin ID: $ADMIN_ID"

# Create store.json if it doesn't exist
if [ ! -f "store.json" ]; then
    echo "📁 Creating initial store.json..."
    echo '{"owner_id": 5803428693, "admins": [6041119040], "whitelist": [], "blacklist": [], "forced_subscription": {"enabled": false, "channel_username": null}, "providers": {"crypto": "coingecko", "fiat": "exchangerate_host"}, "users": [], "user_data": {}, "points": {}}' > store.json
fi

# Check if all required files exist
echo "🔍 Checking required files..."
required_files=("main.py" "config.py" "requirements.txt" "store.json")
for file in "${required_files[@]}"; do
    if [ -f "$file" ]; then
        echo "✅ $file exists"
    else
        echo "❌ ERROR: $file is missing!"
        exit 1
    fi
done

echo "🤖 Starting bot..."

# Run the bot with error handling
exec python main.py
