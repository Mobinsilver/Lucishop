#!/bin/bash

echo "🚀 Starting Crypto Navasan Bot..."

# Check if environment variables are set
if [ -z "$TELEGRAM_BOT_TOKEN" ]; then
    echo "❌ Error: TELEGRAM_BOT_TOKEN is not set"
    exit 1
fi

if [ -z "$OWNER_ID" ]; then
    echo "❌ Error: OWNER_ID is not set"
    exit 1
fi

echo "✅ Environment variables loaded successfully"
echo "🤖 Bot Token: ${TELEGRAM_BOT_TOKEN:0:20}..."
echo "👑 Owner ID: $OWNER_ID"
echo "🌍 Environment: ${ENVIRONMENT:-production}"

# Start the bot
echo "🚀 Starting bot..."
python main.py
