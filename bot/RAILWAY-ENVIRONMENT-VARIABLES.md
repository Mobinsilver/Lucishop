# 🚀 Railway Environment Variables

## 📋 **Required Environment Variables**

### **Core Bot Configuration**
```bash
# Bot Token (Required)
BOT_TOKEN=8308884100:AAEfcSUiiBKV-YIUZs8PUaV6Ik9Gh-3nvZE

# Owner ID (Required) - Your Telegram User ID
OWNER_ID=5803428693

# Admin ID (Required) - Initial Admin User ID
ADMIN_ID=5803428693

# Bot Username (Optional)
BOT_USERNAME=Crypto_navasan_bot
```

### **Railway Configuration**
```bash
# Railway automatically sets these, but you can override:
PORT=3000
RAILWAY_ENVIRONMENT=production
RAILWAY_DEPLOYMENT_ID=your_deployment_id
```

### **Webhook Configuration (Optional)**
```bash
# If you want to use webhook instead of polling:
WEBHOOK_URL=https://your-app-name.railway.app/webhook
```

## 🔧 **Optional Environment Variables**

### **API Keys (Optional)**
```bash
# TradingView API Key
TRADINGVIEW_API_KEY=your_tradingview_api_key

# Fiat Exchange API Key
FIAT_API_KEY=your_fiat_api_key

# Crypto API Key
CRYPTO_API_KEY=your_crypto_api_key
```

### **Database Configuration (Optional)**
```bash
# If you want to use external database:
DATABASE_URL=postgresql://user:password@host:port/database
```

### **Logging Configuration (Optional)**
```bash
# Log level (DEBUG, INFO, WARNING, ERROR)
LOG_LEVEL=INFO

# Bot environment (development, production)
BOT_ENV=production
```

### **Cache Configuration (Optional)**
```bash
# Cache TTL in seconds
CACHE_TTL=300

# Maximum cache size
CACHE_MAX_SIZE=1000
```

## 🎯 **How to Set Environment Variables in Railway**

### **Method 1: Railway Dashboard**
1. Go to your Railway project dashboard
2. Click on your service
3. Go to "Variables" tab
4. Add each environment variable with its value
5. Click "Save"

### **Method 2: Railway CLI**
```bash
# Install Railway CLI
npm install -g @railway/cli

# Login to Railway
railway login

# Set environment variables
railway variables set BOT_TOKEN=your_bot_token
railway variables set OWNER_ID=123456789
railway variables set ADMIN_ID=123456789

# Deploy
railway up
```

### **Method 3: Railway.json (Not Recommended for Secrets)**
```json
{
  "deploy": {
    "env": {
      "BOT_ENV": "production",
      "LOG_LEVEL": "INFO"
    }
  }
}
```

## 🔐 **Security Best Practices**

### **Never Commit These to Git:**
- `BOT_TOKEN`
- `TRADINGVIEW_API_KEY`
- `FIAT_API_KEY`
- `CRYPTO_API_KEY`
- `DATABASE_URL`

### **Use Railway Secrets:**
- All sensitive data should be set as Railway environment variables
- Railway automatically encrypts environment variables
- Never put secrets in your code or configuration files

## 📊 **Environment Variable Priority**

1. **Railway Environment Variables** (Highest Priority)
2. **Railway.json configuration**
3. **Default values in code** (Lowest Priority)

## 🚨 **Troubleshooting**

### **Common Issues:**

#### **Bot Not Starting:**
- Check if `BOT_TOKEN` is set correctly
- Verify `OWNER_ID` and `ADMIN_ID` are numeric
- Check Railway logs for error messages

#### **Webhook Issues:**
- Ensure `WEBHOOK_URL` is set correctly
- Check if the URL is accessible from outside
- Verify SSL certificate is valid

#### **API Issues:**
- Check if API keys are set correctly
- Verify API endpoints are accessible
- Check rate limits and quotas

## 📝 **Example Complete Configuration**

```bash
# Core Bot
BOT_TOKEN=8308884100:AAEfcSUiiBKV-YIUZs8PUaV6Ik9Gh-3nvZE
OWNER_ID=5803428693
ADMIN_ID=5803428693
BOT_USERNAME=Crypto_navasan_bot

# Railway
PORT=3000
RAILWAY_ENVIRONMENT=production

# Optional APIs
TRADINGVIEW_API_KEY=your_tradingview_key
FIAT_API_KEY=your_fiat_key
CRYPTO_API_KEY=your_crypto_key

# Configuration
LOG_LEVEL=INFO
BOT_ENV=production
CACHE_TTL=300
```

## 🔄 **Updating Environment Variables**

### **To Update Variables:**
1. Go to Railway dashboard
2. Navigate to Variables tab
3. Edit the variable value
4. Click "Save"
5. Railway will automatically restart your service

### **To Add New Variables:**
1. Go to Railway dashboard
2. Navigate to Variables tab
3. Click "Add Variable"
4. Enter variable name and value
5. Click "Save"

## 📞 **Support**

If you encounter any issues with environment variables:
1. Check Railway logs for error messages
2. Verify all required variables are set
3. Check variable names for typos
4. Ensure values are properly formatted
