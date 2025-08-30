#!/bin/bash

echo "Starting Telegram Bot on Railway..."

# Check if environment variables are set
if [ -z "$TELEGRAM_BOT_TOKEN" ]; then
    echo "ERROR: TELEGRAM_BOT_TOKEN is not set!"
    exit 1
fi

echo "Bot token is configured"
echo "Starting bot..."

# Run the bot
python main.py
