# 🚀 Railway Deployment Guide

## 📋 **Prerequisites**

- [ ] Railway account (free at [railway.app](https://railway.app))
- [ ] Telegram Bot Token from [@BotFather](https://t.me/BotFather)
- [ ] Your Telegram User ID
- [ ] Git repository with your bot code

## 🎯 **Step-by-Step Deployment**

### **Step 1: Prepare Your Repository**

1. **Clone your repository:**
   ```bash
   git clone https://github.com/yourusername/your-bot-repo.git
   cd your-bot-repo
   ```

2. **Verify all files are present:**
   ```
   ├── main.py
   ├── admin_panel.py
   ├── config.py
   ├── requirements.txt
   ├── railway_start.py
   ├── railway.json
   ├── Procfile
   ├── runtime.txt
   └── RAILWAY-ENVIRONMENT-VARIABLES.md
   ```

### **Step 2: Create Railway Project**

1. **Go to Railway Dashboard:**
   - Visit [railway.app](https://railway.app)
   - Sign in with GitHub

2. **Create New Project:**
   - Click "New Project"
   - Select "Deploy from GitHub repo"
   - Choose your bot repository
   - Click "Deploy"

### **Step 3: Configure Environment Variables**

1. **Go to Variables Tab:**
   - Click on your deployed service
   - Go to "Variables" tab

2. **Add Required Variables:**
   ```bash
   BOT_TOKEN=8308884100:AAEfcSUiiBKV-YIUZs8PUaV6Ik9Gh-3nvZE
   OWNER_ID=5803428693
   ADMIN_ID=5803428693
   BOT_USERNAME=Crypto_navasan_bot
   ```

3. **Add Optional Variables (if needed):**
   ```bash
   TRADINGVIEW_API_KEY=your_tradingview_key
   FIAT_API_KEY=your_fiat_key
   CRYPTO_API_KEY=your_crypto_key
   LOG_LEVEL=INFO
   BOT_ENV=production
   ```

### **Step 4: Deploy and Test**

1. **Deploy:**
   - Railway will automatically deploy when you push to your repository
   - Or click "Deploy" button in Railway dashboard

2. **Check Logs:**
   - Go to "Deployments" tab
   - Click on latest deployment
   - Check logs for any errors

3. **Test Your Bot:**
   - Send `/start` to your bot
   - Test admin commands with `/admin`
   - Verify all features work correctly

## 🔧 **Configuration Options**

### **Webhook vs Polling**

#### **Polling Mode (Default):**
- No additional configuration needed
- Bot polls Telegram servers for updates
- Good for development and testing

#### **Webhook Mode (Recommended for Production):**
1. **Set Webhook URL:**
   ```bash
   WEBHOOK_URL=https://your-app-name.railway.app/webhook
   ```

2. **Benefits:**
   - Faster response times
   - More efficient for high-traffic bots
   - Better for production use

### **Custom Domain (Optional)**

1. **Add Custom Domain:**
   - Go to Railway dashboard
   - Click "Settings"
   - Go to "Domains" tab
   - Add your custom domain

2. **Update Webhook URL:**
   ```bash
   WEBHOOK_URL=https://yourdomain.com/webhook
   ```

## 📊 **Monitoring and Logs**

### **View Logs:**
1. Go to Railway dashboard
2. Click on your service
3. Go to "Deployments" tab
4. Click on latest deployment
5. View real-time logs

### **Monitor Performance:**
- Railway provides built-in metrics
- Monitor CPU, memory, and network usage
- Set up alerts for critical issues

## 🔄 **Updates and Maintenance**

### **Deploy Updates:**
1. **Push to Repository:**
   ```bash
   git add .
   git commit -m "Update bot features"
   git push origin main
   ```

2. **Railway Auto-Deploy:**
   - Railway automatically detects changes
   - Builds and deploys new version
   - Zero-downtime deployment

### **Rollback:**
1. Go to Railway dashboard
2. Click "Deployments" tab
3. Find previous working deployment
4. Click "Redeploy"

## 🚨 **Troubleshooting**

### **Common Issues:**

#### **Bot Not Responding:**
- Check if `BOT_TOKEN` is correct
- Verify bot is not blocked by users
- Check Railway logs for errors

#### **Admin Commands Not Working:**
- Verify `OWNER_ID` and `ADMIN_ID` are set correctly
- Check if user IDs are numeric
- Test with `/admin` command

#### **API Errors:**
- Check if API keys are set correctly
- Verify API endpoints are accessible
- Check rate limits and quotas

#### **Deployment Failures:**
- Check `requirements.txt` for missing dependencies
- Verify Python version in `runtime.txt`
- Check Railway logs for build errors

### **Debug Mode:**
```bash
# Set debug mode
LOG_LEVEL=DEBUG
BOT_ENV=development
```

## 💰 **Pricing and Limits**

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

## 🔐 **Security Best Practices**

### **Environment Variables:**
- Never commit secrets to Git
- Use Railway environment variables for all sensitive data
- Regularly rotate API keys

### **Bot Security:**
- Use strong, unique bot tokens
- Regularly update dependencies
- Monitor bot usage and logs

### **Access Control:**
- Limit admin access to trusted users
- Use blacklist/whitelist features
- Monitor admin actions

## 📞 **Support and Resources**

### **Railway Support:**
- [Railway Documentation](https://docs.railway.app)
- [Railway Discord](https://discord.gg/railway)
- [Railway GitHub](https://github.com/railwayapp)

### **Bot Support:**
- Check bot logs for errors
- Test all features after deployment
- Monitor user feedback

## 🎉 **Success Checklist**

- [ ] Bot deployed successfully on Railway
- [ ] All environment variables set correctly
- [ ] Bot responds to `/start` command
- [ ] Admin panel accessible with `/admin`
- [ ] All features working correctly
- [ ] Logs showing no errors
- [ ] Performance monitoring active

## 🔄 **Next Steps**

1. **Set up monitoring alerts**
2. **Configure custom domain (optional)**
3. **Set up automated backups**
4. **Monitor usage and performance**
5. **Regular updates and maintenance**

---

**🎯 Your Telegram bot is now successfully deployed on Railway!**

For any issues or questions, check the troubleshooting section or contact support.
