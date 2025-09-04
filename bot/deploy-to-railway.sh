#!/bin/bash

# 🚀 Railway Deployment Script
# This script helps you deploy your Telegram bot to Railway

echo "🚀 Railway Deployment Script"
echo "=============================="

# Check if git is initialized
if [ ! -d ".git" ]; then
    echo "❌ Git repository not initialized. Please run:"
    echo "   git init"
    echo "   git add ."
    echo "   git commit -m 'Initial commit'"
    exit 1
fi

# Check if Railway CLI is installed
if ! command -v railway &> /dev/null; then
    echo "❌ Railway CLI not installed. Please install it:"
    echo "   npm install -g @railway/cli"
    exit 1
fi

# Check if user is logged in to Railway
if ! railway whoami &> /dev/null; then
    echo "❌ Not logged in to Railway. Please login:"
    echo "   railway login"
    exit 1
fi

echo "✅ Git repository found"
echo "✅ Railway CLI installed"
echo "✅ Logged in to Railway"

# Check if required files exist
required_files=("main.py" "admin_panel.py" "requirements.txt" "railway_start.py" "railway.json" "Procfile" "runtime.txt")

for file in "${required_files[@]}"; do
    if [ ! -f "$file" ]; then
        echo "❌ Required file missing: $file"
        exit 1
    fi
done

echo "✅ All required files present"

# Check if environment variables are set
echo ""
echo "🔧 Environment Variables Check:"
echo "================================"

if [ -z "$BOT_TOKEN" ]; then
    echo "❌ BOT_TOKEN not set"
    echo "   Please set: railway variables set BOT_TOKEN=your_bot_token"
else
    echo "✅ BOT_TOKEN is set"
fi

if [ -z "$OWNER_ID" ]; then
    echo "❌ OWNER_ID not set"
    echo "   Please set: railway variables set OWNER_ID=your_user_id"
else
    echo "✅ OWNER_ID is set"
fi

if [ -z "$ADMIN_ID" ]; then
    echo "❌ ADMIN_ID not set"
    echo "   Please set: railway variables set ADMIN_ID=your_admin_id"
else
    echo "✅ ADMIN_ID is set"
fi

echo ""
echo "🚀 Deploying to Railway..."
echo "=========================="

# Deploy to Railway
railway up

if [ $? -eq 0 ]; then
    echo ""
    echo "🎉 Deployment successful!"
    echo "========================="
    echo "Your bot should now be running on Railway."
    echo ""
    echo "📋 Next steps:"
    echo "1. Check Railway dashboard for deployment status"
    echo "2. Test your bot with /start command"
    echo "3. Test admin features with /admin command"
    echo "4. Monitor logs in Railway dashboard"
    echo ""
    echo "🔗 Railway Dashboard: https://railway.app/dashboard"
else
    echo ""
    echo "❌ Deployment failed!"
    echo "===================="
    echo "Please check the error messages above and try again."
    echo "Common issues:"
    echo "- Missing environment variables"
    echo "- Build errors in requirements.txt"
    echo "- Network connectivity issues"
fi
