#!/bin/bash

# 🤖 Bot Setup Script for Crypto_navasan_bot
# This script helps you set up your bot with the correct configuration

echo "🤖 Setting up Crypto_navasan_bot"
echo "================================="

# Bot Information
BOT_TOKEN="8308884100:AAEfcSUiiBKV-YIUZs8PUaV6Ik9Gh-3nvZE"
OWNER_ID="5803428693"
ADMIN_ID="5803428693"
BOT_USERNAME="Crypto_navasan_bot"

echo "📋 Bot Information:"
echo "  Bot Token: ${BOT_TOKEN:0:20}..."
echo "  Owner ID: $OWNER_ID"
echo "  Admin ID: $ADMIN_ID"
echo "  Bot Username: $BOT_USERNAME"
echo ""

# Check if Railway CLI is installed
if command -v railway &> /dev/null; then
    echo "✅ Railway CLI is installed"
    
    # Check if user is logged in
    if railway whoami &> /dev/null; then
        echo "✅ Logged in to Railway"
        
        # Set environment variables
        echo "🔧 Setting environment variables..."
        railway variables set BOT_TOKEN="$BOT_TOKEN"
        railway variables set OWNER_ID="$OWNER_ID"
        railway variables set ADMIN_ID="$ADMIN_ID"
        railway variables set BOT_USERNAME="$BOT_USERNAME"
        railway variables set PORT="3000"
        railway variables set ENVIRONMENT="production"
        railway variables set LOG_LEVEL="INFO"
        
        echo "✅ Environment variables set successfully"
        
        # Deploy
        echo "🚀 Deploying to Railway..."
        railway up
        
        if [ $? -eq 0 ]; then
            echo ""
            echo "🎉 Bot deployed successfully!"
            echo "============================="
            echo "Your bot is now running on Railway."
            echo "Test it by sending /start to @$BOT_USERNAME"
            echo ""
            echo "📋 Next steps:"
            echo "1. Test your bot with /start command"
            echo "2. Test admin features with /admin command"
            echo "3. Check Railway dashboard for logs"
            echo "4. Monitor performance and usage"
        else
            echo "❌ Deployment failed. Check Railway logs for details."
        fi
    else
        echo "❌ Not logged in to Railway. Please run: railway login"
    fi
else
    echo "❌ Railway CLI not installed. Please install it:"
    echo "   npm install -g @railway/cli"
    echo "   Then run: railway login"
fi

echo ""
echo "📚 For manual setup, see RAILWAY-DEPLOYMENT-GUIDE.md"
