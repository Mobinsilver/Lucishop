# 🤖 Telegram Bot - Railway Deployment

## 🚀 **Quick Start**

### **1. Deploy to Railway (One-Click)**
[![Deploy on Railway](https://railway.app/button.svg)](https://railway.app/template/deploy)

### **2. Manual Deployment**
```bash
# Clone repository
git clone https://github.com/yourusername/your-bot-repo.git
cd your-bot-repo

# Install Railway CLI
npm install -g @railway/cli

# Login to Railway
railway login

# Deploy
railway up
```

## 📋 **Required Environment Variables**

Set these in Railway dashboard → Variables tab:

```bash
# Core Bot Configuration
BOT_TOKEN=8308884100:AAEfcSUiiBKV-YIUZs8PUaV6Ik9Gh-3nvZE
OWNER_ID=5803428693
ADMIN_ID=5803428693
BOT_USERNAME=Crypto_navasan_bot

# Optional APIs
TRADINGVIEW_API_KEY=your_tradingview_key
FIAT_API_KEY=your_fiat_key
CRYPTO_API_KEY=your_crypto_key
```

## 🎯 **Features**

### **Admin Panel Features:**
- ✅ **Broadcast to All** - Send messages to all users
- ✅ **Admin Management** - Add/remove admins
- ✅ **External API Configuration** - Configure custom APIs
- ✅ **Mandatory Join** - Force users to join channels
- ✅ **Analytics & Stats** - User statistics and reports
- ✅ **Feature Toggles** - Enable/disable bot features
- ✅ **Blacklist/Whitelist** - User access control
- ✅ **Text Settings** - Customize bot messages

### **User Features:**
- ✅ **Crypto Prices** - Real-time cryptocurrency prices
- ✅ **Fiat Rates** - Exchange rates for fiat currencies
- ✅ **News Feed** - Latest cryptocurrency news
- ✅ **Technical Analysis** - Trading indicators and charts
- ✅ **Price Comparison** - Compare prices across exchanges
- ✅ **P2P Trading** - Binance P2P market data
- ✅ **Watchlist** - Track favorite cryptocurrencies
- ✅ **Portfolio** - Manage your crypto portfolio
- ✅ **Alerts** - Price and news alerts

## 🔧 **Configuration**

### **Environment Variables:**
- `BOT_TOKEN` - Your Telegram bot token (required)
- `OWNER_ID` - Your Telegram user ID (required)
- `ADMIN_ID` - Initial admin user ID (required)
- `TRADINGVIEW_API_KEY` - TradingView API key (optional)
- `FIAT_API_KEY` - Fiat exchange API key (optional)
- `CRYPTO_API_KEY` - Cryptocurrency API key (optional)
- `LOG_LEVEL` - Logging level (default: INFO)
- `BOT_ENV` - Bot environment (default: production)

### **Railway Configuration:**
- **Port**: 3000 (automatically set)
- **Python Version**: 3.11.0
- **Start Command**: `python railway_start.py`
- **Restart Policy**: ON_FAILURE with 10 retries

## 📊 **Monitoring**

### **Railway Dashboard:**
- View deployment status
- Monitor resource usage
- Check logs and errors
- Manage environment variables

### **Bot Logs:**
- Real-time logging
- Error tracking
- Performance monitoring
- User activity logs

## 🔄 **Updates**

### **Automatic Updates:**
Railway automatically deploys when you push to your repository:

```bash
git add .
git commit -m "Update bot features"
git push origin main
```

### **Manual Updates:**
```bash
railway up
```

## 🚨 **Troubleshooting**

### **Common Issues:**

#### **Bot Not Responding:**
- Check if `BOT_TOKEN` is correct
- Verify bot is not blocked
- Check Railway logs for errors

#### **Admin Commands Not Working:**
- Verify `OWNER_ID` and `ADMIN_ID` are set
- Check if user IDs are numeric
- Test with `/admin` command

#### **API Errors:**
- Check if API keys are set correctly
- Verify API endpoints are accessible
- Check rate limits and quotas

### **Debug Mode:**
```bash
LOG_LEVEL=DEBUG
BOT_ENV=development
```

## 📞 **Support**

### **Railway Support:**
- [Railway Documentation](https://docs.railway.app)
- [Railway Discord](https://discord.gg/railway)
- [Railway GitHub](https://github.com/railwayapp)

### **Bot Support:**
- Check bot logs for errors
- Test all features after deployment
- Monitor user feedback

## 🔐 **Security**

### **Best Practices:**
- Use strong, unique bot tokens
- Regularly update dependencies
- Monitor bot usage and logs
- Limit admin access to trusted users

### **Environment Variables:**
- Never commit secrets to Git
- Use Railway environment variables
- Regularly rotate API keys

## 💰 **Pricing**

### **Railway Free Tier:**
- $5 credit per month
- 500 hours of usage
- 1GB RAM
- 1GB storage

### **Railway Pro:**
- $5 per month per service
- Unlimited usage
- 8GB RAM
- 100GB storage

## 🎉 **Success Checklist**

- [ ] Bot deployed successfully on Railway
- [ ] All environment variables set correctly
- [ ] Bot responds to `/start` command
- [ ] Admin panel accessible with `/admin`
- [ ] All features working correctly
- [ ] Logs showing no errors
- [ ] Performance monitoring active

---

**🎯 Your Telegram bot is now ready for Railway deployment!**

For detailed deployment instructions, see [RAILWAY-DEPLOYMENT-GUIDE.md](RAILWAY-DEPLOYMENT-GUIDE.md)