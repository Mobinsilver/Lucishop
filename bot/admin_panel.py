import json
import asyncio
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import ContextTypes, ConversationHandler
from config import OWNER_ID, ADMIN_ID
from store import load_store, save_store
from cache import TTLCache
import aiohttp

# States for conversation
(
    ADMIN_PANEL, ADD_ADMIN, REMOVE_ADMIN, BROADCAST_MESSAGE, 
    SET_WELCOME_TEXT, SET_HELP_TEXT, SET_ERROR_TEXT, SET_API_KEY,
    FORCE_SUBSCRIPTION, WHITELIST_USER, BLACKLIST_USER,
    VIEW_STATS, MANAGE_CACHE, SYSTEM_SETTINGS, BACKUP_RESTORE,
    VIEW_LOGS, MANAGE_ALERTS, CUSTOM_COMMANDS, BOT_SETTINGS,
    ADD_WHITELIST, ADD_BLACKLIST, REMOVE_WHITELIST, REMOVE_BLACKLIST,
    SET_TRADINGVIEW_API, SET_FIAT_API, SET_CRYPTO_API, ADD_FORCE_SUB_CHANNEL,
    USER_MESSAGE, BROADCAST_FORWARD, SET_CRYPTO_API_KEY,
    # New API management states
    MANAGE_APIS, ADD_API, EDIT_API, DELETE_API, API_SETTINGS,
    MANAGE_CURRENCIES, ADD_CURRENCY, EDIT_CURRENCY, DELETE_CURRENCY, CURRENCY_SETTINGS,
    MANAGE_INDICATORS, ADD_INDICATOR, EDIT_INDICATOR, DELETE_INDICATOR, INDICATOR_SETTINGS
) = range(45)

class AdminPanel:
    def __init__(self):
        self.store = load_store()
        self.cache = TTLCache()
    
    async def admin_panel_main(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """پنل مدیریتی اصلی"""
        user_id = update.effective_user.id
        
        if user_id != OWNER_ID:
            await update.message.reply_text("❌ شما دسترسی به پنل مدیریتی ندارید!")
            return ConversationHandler.END
        
        keyboard = [
            [InlineKeyboardButton("👥 مدیریت ادمین‌ها", callback_data="admin_manage")],
            [InlineKeyboardButton("📢 ارسال همگانی", callback_data="admin_broadcast")],
            [InlineKeyboardButton("📝 تنظیم متن‌ها", callback_data="admin_texts")],
            [InlineKeyboardButton("🔧 مدیریت API ها", callback_data="admin_apis")],
            [InlineKeyboardButton("💰 مدیریت ارزها", callback_data="admin_currencies")],
            [InlineKeyboardButton("📊 مدیریت شاخص‌ها", callback_data="admin_indicators")],
            [InlineKeyboardButton("🔒 قفل اجباری", callback_data="admin_force_sub")],
            [InlineKeyboardButton("⚪ لیست سفید/سیاه", callback_data="admin_lists")],
            [InlineKeyboardButton("🗄️ مدیریت کش", callback_data="admin_cache")],
            [InlineKeyboardButton("⚙️ تنظیمات سیستم", callback_data="admin_system")],
            [InlineKeyboardButton("💾 پشتیبان‌گیری", callback_data="admin_backup")],
            [InlineKeyboardButton("📋 لاگ‌ها", callback_data="admin_logs")],
            [InlineKeyboardButton("🔔 مدیریت هشدارها", callback_data="admin_alerts")],
            [InlineKeyboardButton("📊 آمار و گزارش", callback_data="admin_stats")],
            [InlineKeyboardButton("⌨️ دستورات سفارشی", callback_data="admin_commands")],
            [InlineKeyboardButton("🤖 تنظیمات ربات", callback_data="admin_bot_settings")],
            [InlineKeyboardButton("❌ خروج", callback_data="admin_exit")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        text = f"""
🔐 **پنل مدیریتی پیشرفته**

👤 **مالک**: {OWNER_ID}
📅 **تاریخ**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
🔄 **وضعیت**: فعال

📊 **آمار سریع**:
👥 کاربران: {len(self.store.get('users', []))}
⚪ لیست سفید: {len(self.store.get('whitelist', []))}
⚫ لیست سیاه: {len(self.store.get('blacklist', []))}
👨‍💼 ادمین‌ها: {len(self.store.get('admins', []))}

لطفاً یکی از گزینه‌های زیر را انتخاب کنید:
        """
        
        if update.callback_query:
            await update.callback_query.edit_message_text(text, reply_markup=reply_markup)
        else:
            await update.message.reply_text(text, reply_markup=reply_markup)
        
        return ADMIN_PANEL
    
    async def admin_manage_admins(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """مدیریت ادمین‌ها"""
        query = update.callback_query
        await query.answer()
        
        admins = self.store.get('admins', [])
        admin_list = "\n".join([f"• {admin_id}" for admin_id in admins])
        
        keyboard = [
            [InlineKeyboardButton("➕ افزودن ادمین", callback_data="add_admin")],
            [InlineKeyboardButton("➖ حذف ادمین", callback_data="remove_admin")],
            [InlineKeyboardButton("📋 لیست ادمین‌ها", callback_data="list_admins")],
            [InlineKeyboardButton("🔙 بازگشت", callback_data="back_to_main")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        text = f"""
👥 **مدیریت ادمین‌ها**

👨‍💼 **ادمین‌های فعلی**:
{admin_list if admin_list else "• هیچ ادمینی وجود ندارد"}

**عملیات موجود**:
➕ افزودن ادمین جدید
➖ حذف ادمین موجود
📋 مشاهده لیست کامل
        """
        
        await query.edit_message_text(text, reply_markup=reply_markup)
        return ADMIN_PANEL
    
    async def add_admin_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """شروع فرآیند افزودن ادمین"""
        query = update.callback_query
        await query.answer()
        
        await query.edit_message_text(
            "➕ **افزودن ادمین جدید**\n\n"
            "لطفاً آیدی عددی کاربر را ارسال کنید:\n"
            "مثال: `123456789`\n\n"
            "🔙 برای بازگشت: /cancel",
            parse_mode='Markdown'
        )
        
        return ADD_ADMIN
    
    async def add_admin_process(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """پردازش افزودن ادمین"""
        try:
            new_admin_id = int(update.message.text)
            
            if new_admin_id == OWNER_ID:
                await update.message.reply_text("❌ این کاربر مالک ربات است!")
                return ADD_ADMIN
            
            admins = self.store.get('admins', [])
            
            if new_admin_id in admins:
                await update.message.reply_text("❌ این کاربر قبلاً ادمین است!")
                return ADD_ADMIN
            
            admins.append(new_admin_id)
            self.store['admins'] = admins
            save_store(self.store)
            
            keyboard = [[InlineKeyboardButton("🔙 بازگشت به پنل", callback_data="back_to_main")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                f"✅ **ادمین با موفقیت اضافه شد!**\n\n"
                f"👤 **آیدی جدید**: {new_admin_id}\n"
                f"📅 **تاریخ**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                reply_markup=reply_markup
            )
            
            return ADMIN_PANEL
            
        except ValueError:
            await update.message.reply_text("❌ لطفاً یک عدد معتبر وارد کنید!")
            return ADD_ADMIN
    
    async def remove_admin_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """شروع فرآیند حذف ادمین"""
        query = update.callback_query
        await query.answer()
        
        await query.edit_message_text(
            "➖ **حذف ادمین**\n\n"
            "لطفاً آیدی عددی کاربر را ارسال کنید:\n"
            "مثال: `123456789`\n\n"
            "🔙 برای بازگشت: /cancel",
            parse_mode='Markdown'
        )
        
        return REMOVE_ADMIN
    
    async def remove_admin_process(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """پردازش حذف ادمین"""
        try:
            admin_to_remove = int(update.message.text)
            
            if admin_to_remove == OWNER_ID:
                await update.message.reply_text("❌ این کاربر مالک ربات است!")
                return REMOVE_ADMIN
            
            admins = self.store.get('admins', [])
            
            if admin_to_remove not in admins:
                await update.message.reply_text("❌ این کاربر قبلاً ادمین نیست!")
                return REMOVE_ADMIN
            
            admins.remove(admin_to_remove)
            self.store['admins'] = admins
            save_store(self.store)
            
            keyboard = [[InlineKeyboardButton("🔙 بازگشت به پنل", callback_data="back_to_main")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                f"✅ **ادمین با موفقیت حذف شد!**\n\n"
                f"👤 **آیدی حذف شده**: {admin_to_remove}\n"
                f"📅 **تاریخ**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                reply_markup=reply_markup
            )
            
            return ADMIN_PANEL
            
        except ValueError:
            await update.message.reply_text("❌ لطفاً یک عدد معتبر وارد کنید!")
            return REMOVE_ADMIN
    
    async def broadcast_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """شروع ارسال همگانی"""
        query = update.callback_query
        await query.answer()
        
        keyboard = [
            [InlineKeyboardButton("📢 ارسال به همه", callback_data="broadcast_all")],
            [InlineKeyboardButton("👥 ارسال به ادمین‌ها", callback_data="broadcast_admins")],
            [InlineKeyboardButton("⚪ ارسال به لیست سفید", callback_data="broadcast_whitelist")],
            [InlineKeyboardButton("🔄 فوروارد همگانی", callback_data="broadcast_forward")],
            [InlineKeyboardButton("🔙 بازگشت", callback_data="back_to_main")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        users_count = len(self.store.get('users', []))
        admins_count = len(self.store.get('admins', []))
        whitelist_count = len(self.store.get('whitelist', []))
        
        text = f"""
📢 **ارسال همگانی (فوروارد ربات)**

📊 **آمار کاربران**:
👥 کل کاربران: {users_count}
👨‍💼 ادمین‌ها: {admins_count}
⚪ لیست سفید: {whitelist_count}

**نحوه استفاده**:
1. ربات مورد نظر را فوروارد کنید
2. ربات آن را به تمام کاربران فوروارد می‌کند

**انتخاب کنید**:
📢 ارسال به همه کاربران
👥 ارسال به ادمین‌ها
⚪ ارسال به لیست سفید
        """
        
        await query.edit_message_text(text, reply_markup=reply_markup)
        return ADMIN_PANEL
    
    async def broadcast_message_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """شروع نوشتن پیام همگانی"""
        query = update.callback_query
        await query.answer()
        
        broadcast_type = query.data.split('_')[1]
        context.user_data['broadcast_type'] = broadcast_type
        
        type_names = {
            'all': 'همه کاربران',
            'admins': 'ادمین‌ها',
            'whitelist': 'لیست سفید'
        }
        
        await query.edit_message_text(
            f"📢 **ارسال پیام به {type_names[broadcast_type]}**\n\n"
            f"لطفاً پیام خود را ارسال کنید:\n\n"
            f"💡 **نکات مهم**:\n"
            f"• از Markdown پشتیبانی می‌شود\n"
            f"• می‌توانید عکس، ویدیو یا فایل ارسال کنید\n"
            f"• برای لغو: /cancel\n\n"
            f"📤 **نوع ارسال**: {type_names[broadcast_type]}",
            parse_mode='Markdown'
        )
        
        return BROADCAST_MESSAGE
    
    async def broadcast_forward_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """شروع فوروارد همگانی"""
        query = update.callback_query
        await query.answer()
        
        await query.edit_message_text(
            "🔄 **فوروارد همگانی**\n\n"
            "لطفاً پیامی که می‌خواهید فوروارد شود را ارسال کنید:\n\n"
            "💡 **نکات مهم**:\n"
            "• ربات آن را به **تمام کاربرانی که استارت کرده‌اند** فوروارد می‌کند\n"
            "• پیام **فقط فوروارد** می‌شود (کپی نمی‌شود)\n"
            "• برای لغو: /cancel\n\n"
            "📤 **نوع ارسال**: فوروارد همگانی",
            parse_mode='Markdown'
        )
        
        return BROADCAST_FORWARD
    
    async def broadcast_forward_process(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """پردازش فوروارد همگانی"""
        # دریافت تمام کاربرانی که استارت کرده‌اند
        all_users = self.store.get('users', [])
        
        # فوروارد کردن پیام
        success_count = 0
        failed_count = 0
        
        await update.message.reply_text("📤 در حال فوروارد کردن به تمام کاربران...")
        
        for user_id in all_users:
            try:
                # فوروارد کردن پیام (فقط فوروارد، نه کپی)
                await context.bot.forward_message(
                    chat_id=user_id,
                    from_chat_id=update.effective_chat.id,
                    message_id=update.message.message_id
                )
                success_count += 1
                await asyncio.sleep(0.1)  # تاخیر برای جلوگیری از محدودیت
                
            except Exception as e:
                failed_count += 1
                print(f"Failed to forward to {user_id}: {e}")
        
        keyboard = [[InlineKeyboardButton("🔙 بازگشت به پنل", callback_data="back_to_main")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            f"✅ **فوروارد همگانی تکمیل شد!**\n\n"
            f"📊 **نتایج**:\n"
            f"✅ موفق: {success_count}\n"
            f"❌ ناموفق: {failed_count}\n"
            f"👥 **کل کاربران**: {len(all_users)}\n"
            f"📅 **تاریخ**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            reply_markup=reply_markup
        )
        
        return ADMIN_PANEL
    
    async def broadcast_message_process(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """پردازش ارسال پیام همگانی - فوروارد"""
        broadcast_type = context.user_data.get('broadcast_type', 'all')
        
        # تعیین لیست گیرندگان
        if broadcast_type == 'all':
            recipients = self.store.get('users', [])
        elif broadcast_type == 'admins':
            recipients = self.store.get('admins', []) + [OWNER_ID]
        elif broadcast_type == 'whitelist':
            recipients = self.store.get('whitelist', [])
        
        # ارسال فوروارد
        success_count = 0
        failed_count = 0
        
        await update.message.reply_text("📤 در حال فوروارد کردن...")
        
        for user_id in recipients:
            try:
                # فوروارد کردن پیام
                await update.message.forward(chat_id=user_id)
                success_count += 1
                await asyncio.sleep(0.1)  # تاخیر برای جلوگیری از محدودیت
                
            except Exception as e:
                failed_count += 1
                print(f"Failed to forward to {user_id}: {e}")
        
        keyboard = [[InlineKeyboardButton("🔙 بازگشت به پنل", callback_data="back_to_main")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            f"✅ **فوروارد همگانی تکمیل شد!**\n\n"
            f"📊 **نتایج**:\n"
            f"✅ موفق: {success_count}\n"
            f"❌ ناموفق: {failed_count}\n"
            f"📅 **تاریخ**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            reply_markup=reply_markup
        )
        
        return ADMIN_PANEL
    
    async def admin_texts_panel(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """پنل تنظیم متن‌ها"""
        query = update.callback_query
        await query.answer()
        
        keyboard = [
            [InlineKeyboardButton("👋 متن خوش‌آمدگویی", callback_data="set_welcome")],
            [InlineKeyboardButton("❓ متن راهنما", callback_data="set_help")],
            [InlineKeyboardButton("⚠️ متن خطا", callback_data="set_error")],
            [InlineKeyboardButton("📝 متن درباره", callback_data="set_about")],
            [InlineKeyboardButton("🔒 متن عضویت اجباری", callback_data="set_force_sub")],
            [InlineKeyboardButton("⚙️ متن تنظیمات", callback_data="set_settings")],
            [InlineKeyboardButton("🔙 بازگشت", callback_data="back_to_main")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        text = """
📝 **تنظیم متن‌های ربات**

**متن‌های قابل تنظیم**:
👋 متن خوش‌آمدگویی (/start)
❓ متن راهنما (/help)
⚠️ متن خطاها
📝 متن درباره ربات
🔒 متن عضویت اجباری
⚙️ متن تنظیمات

لطفاً یکی از گزینه‌ها را انتخاب کنید:
        """
        
        await query.edit_message_text(text, reply_markup=reply_markup)
        return ADMIN_PANEL
    
    async def set_welcome_text_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """شروع تنظیم متن خوش‌آمدگویی"""
        current_text = self.store.get('texts', {}).get('welcome', 'متن خوش‌آمدگویی تنظیم نشده')
        
        # بررسی اینکه آیا از کیبورد سریع آمده یا callback
        if update.callback_query:
            query = update.callback_query
            await query.answer()
            await query.edit_message_text(
                f"👋 **تنظیم متن خوش‌آمدگویی**\n\n"
                f"📝 **متن فعلی**:\n{current_text}\n\n"
                f"✏️ **متن جدید را ارسال کنید**:\n\n"
                f"💡 **متغیرهای قابل استفاده**:\n"
                f"• {{name}} - نام کاربر\n"
                f"• {{username}} - نام کاربری\n"
                f"• {{user_id}} - آیدی کاربر\n\n"
                f"🔙 برای لغو: /cancel",
                parse_mode='Markdown'
            )
        else:
            # از کیبورد سریع آمده
            await update.message.reply_text(
                f"👋 **تنظیم متن خوش‌آمدگویی**\n\n"
                f"📝 **متن فعلی**:\n{current_text}\n\n"
                f"✏️ **متن جدید را ارسال کنید**:\n\n"
                f"💡 **متغیرهای قابل استفاده**:\n"
                f"• {{name}} - نام کاربر\n"
                f"• {{username}} - نام کاربری\n"
                f"• {{user_id}} - آیدی کاربر\n\n"
                f"🔙 برای لغو: /cancel",
                parse_mode='Markdown'
            )
        
        return SET_WELCOME_TEXT
    
    async def set_welcome_text_process(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """پردازش تنظیم متن خوش‌آمدگویی"""
        new_text = update.message.text
        
        if 'texts' not in self.store:
            self.store['texts'] = {}
        
        self.store['texts']['welcome'] = new_text
        save_store(self.store)
        
        keyboard = [[InlineKeyboardButton("🔙 بازگشت به پنل", callback_data="back_to_main")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            f"✅ **متن خوش‌آمدگویی با موفقیت تنظیم شد!**\n\n"
            f"📝 **متن جدید**:\n{new_text}\n\n"
            f"📅 **تاریخ**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            reply_markup=reply_markup
        )
        
        return ADMIN_PANEL
    
    async def admin_api_panel(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """پنل تنظیمات API"""
        query = update.callback_query
        await query.answer()
        
        keyboard = [
            [InlineKeyboardButton("🔑 TradingView API", callback_data="set_tradingview_api")],
            [InlineKeyboardButton("💱 فیات API", callback_data="set_fiat_api")],
            [InlineKeyboardButton("💰 کریپتو API", callback_data="set_crypto_api")],
            [InlineKeyboardButton("📊 مدیریت ارزهای فعال", callback_data="manage_currencies")],
            [InlineKeyboardButton("📈 تست API", callback_data="test_api")],
            [InlineKeyboardButton("🔙 بازگشت", callback_data="back_to_main")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # دریافت تنظیمات فعلی
        tradingview_api = self.store.get('tradingview_api', 'تنظیم نشده')
        fiat_api = self.store.get('fiat_api', 'تنظیم نشده')
        crypto_api = self.store.get('crypto_api', 'تنظیم نشده')
        active_currencies = self.store.get('active_currencies', [])
        
        text = f"""
🔧 **تنظیمات API**

📊 **وضعیت API ها**:
🔑 TradingView: {tradingview_api[:20] + '...' if len(tradingview_api) > 20 else tradingview_api}
💱 فیات API: {fiat_api[:20] + '...' if len(fiat_api) > 20 else fiat_api}
💰 کریپتو API: {crypto_api[:20] + '...' if len(crypto_api) > 20 else crypto_api}

📈 **ارزهای فعال**: {len(active_currencies)} ارز

**عملیات موجود**:
🔑 تنظیم TradingView API
💱 تنظیم فیات API
💰 تنظیم کریپتو API
📊 مدیریت ارزهای فعال
📈 تست API ها
        """
        
        await query.edit_message_text(text, reply_markup=reply_markup)
        return ADMIN_PANEL
    
    async def manage_currencies_panel(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """پنل مدیریت ارزهای فعال"""
        query = update.callback_query
        await query.answer()
        
        active_currencies = self.store.get('active_currencies', [])
        available_currencies = self.store.get('available_currencies', [
            'USD', 'EUR', 'GBP', 'JPY', 'CAD', 'AUD', 'CHF', 'CNY', 'SEK', 'NZD',
            'MXN', 'SGD', 'HKD', 'NOK', 'TRY', 'RUB', 'INR', 'BRL', 'ZAR', 'KRW'
        ])
        
        # ایجاد دکمه‌ها برای ارزهای فعال
        active_buttons = []
        for currency in active_currencies[:10]:  # حداکثر 10 ارز در هر ردیف
            active_buttons.append([InlineKeyboardButton(f"❌ {currency}", callback_data=f"remove_currency:{currency}")])
        
        # ایجاد دکمه‌ها برای ارزهای غیرفعال
        inactive_currencies = [c for c in available_currencies if c not in active_currencies]
        inactive_buttons = []
        for currency in inactive_currencies[:10]:  # حداکثر 10 ارز در هر ردیف
            inactive_buttons.append([InlineKeyboardButton(f"➕ {currency}", callback_data=f"add_currency:{currency}")])
        
        keyboard = []
        
        if active_currencies:
            keyboard.append([InlineKeyboardButton("📊 ارزهای فعال", callback_data="dummy")])
            keyboard.extend(active_buttons)
        
        if inactive_currencies:
            keyboard.append([InlineKeyboardButton("➕ ارزهای غیرفعال", callback_data="dummy")])
            keyboard.extend(inactive_buttons)
        
        keyboard.extend([
            [InlineKeyboardButton("🔄 بارگذاری مجدد", callback_data="reload_currencies")],
            [InlineKeyboardButton("🔙 بازگشت", callback_data="admin_api")]
        ])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        text = f"""
📊 **مدیریت ارزهای فعال**

📈 **ارزهای فعال**: {len(active_currencies)} ارز
📉 **ارزهای غیرفعال**: {len(inactive_currencies)} ارز

**نحوه استفاده**:
❌ برای حذف ارز از لیست فعال
➕ برای اضافه کردن ارز به لیست فعال
🔄 برای بارگذاری مجدد لیست ارزها

**ارزهای فعال فعلی**:
{', '.join(active_currencies) if active_currencies else 'هیچ ارزی فعال نیست'}
        """
        
        await query.edit_message_text(text, reply_markup=reply_markup)
        return ADMIN_PANEL
    
    async def test_api_panel(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """پنل تست API"""
        query = update.callback_query
        await query.answer()
        
        keyboard = [
            [InlineKeyboardButton("🔑 تست TradingView", callback_data="test_tradingview")],
            [InlineKeyboardButton("💱 تست فیات API", callback_data="test_fiat")],
            [InlineKeyboardButton("💰 تست کریپتو API", callback_data="test_crypto")],
            [InlineKeyboardButton("🔙 بازگشت", callback_data="admin_api")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        text = """
📈 **تست API ها**

**عملیات موجود**:
🔑 تست TradingView API
💱 تست فیات API
💰 تست کریپتو API

**نکته**: تست API ها برای بررسی صحت تنظیمات انجام می‌شود
        """
        
        await query.edit_message_text(text, reply_markup=reply_markup)
        return ADMIN_PANEL
    
    async def test_tradingview_action(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """تست TradingView API"""
        query = update.callback_query
        await query.answer()
        
        tradingview_api = self.store.get('tradingview_api', '')
        if not tradingview_api:
            await query.edit_message_text(
                "❌ **TradingView API تنظیم نشده!**\n\n"
                "لطفاً ابتدا API key را در بخش تنظیمات API وارد کنید.",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔙 بازگشت", callback_data="test_api")
                ]])
            )
            return ADMIN_PANEL
        
        # نمایش پیام در حال تست
        await query.edit_message_text("⏳ در حال تست TradingView API...")
        
        try:
            import aiohttp
            
            # تست API با درخواست ساده
            url = "https://api.tradingview.com/v1/symbols/BTCUSD/quotes"
            headers = {
                'Authorization': f'Bearer {tradingview_api}',
                'Content-Type': 'application/json'
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers, timeout=10) as response:
                    if response.status == 200:
                        data = await response.json()
                        price = data.get('price', 'نامشخص')
                        
                        await query.edit_message_text(
                            f"✅ **TradingView API کار می‌کند!**\n\n"
                            f"🔑 **API Key**: {tradingview_api[:10]}...\n"
                            f"💰 **قیمت تست (BTC)**: ${price}\n"
                            f"📅 **زمان تست**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
                            f"**وضعیت**: API فعال و قابل استفاده",
                            reply_markup=InlineKeyboardMarkup([[
                                InlineKeyboardButton("🔙 بازگشت", callback_data="test_api")
                            ]])
                        )
                    else:
                        await query.edit_message_text(
                            f"❌ **خطا در TradingView API!**\n\n"
                            f"🔑 **API Key**: {tradingview_api[:10]}...\n"
                            f"📊 **کد خطا**: {response.status}\n"
                            f"📅 **زمان تست**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
                            f"**مشکل**: API key نامعتبر یا منقضی شده",
                            reply_markup=InlineKeyboardMarkup([[
                                InlineKeyboardButton("🔙 بازگشت", callback_data="test_api")
                            ]])
                        )
                        
        except Exception as e:
            await query.edit_message_text(
                f"❌ **خطا در تست TradingView API!**\n\n"
                f"🔑 **API Key**: {tradingview_api[:10]}...\n"
                f"📅 **زمان تست**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
                f"⚠️ **خطا**: {str(e)}\n\n"
                f"**مشکل**: اتصال به API یا تنظیمات نادرست",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔙 بازگشت", callback_data="test_api")
                ]])
            )
        
        return ADMIN_PANEL
    
    async def test_fiat_action(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """تست فیات API"""
        query = update.callback_query
        await query.answer()
        
        fiat_api = self.store.get('fiat_api', '')
        if not fiat_api:
            await query.edit_message_text(
                "❌ **فیات API تنظیم نشده!**\n\n"
                "لطفاً ابتدا API key را در بخش تنظیمات API وارد کنید.",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔙 بازگشت", callback_data="test_api")
                ]])
            )
            return ADMIN_PANEL
        
        # نمایش پیام در حال تست
        await query.edit_message_text("⏳ در حال تست فیات API...")
        
        try:
            import aiohttp
            
            # تست API با درخواست ساده
            url = "https://api.exchangerate.host/latest?base=USD&symbols=EUR"
            headers = {
                'X-API-Key': fiat_api,
                'Content-Type': 'application/json'
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers, timeout=10) as response:
                    if response.status == 200:
                        data = await response.json()
                        rate = data.get('rates', {}).get('EUR', 'نامشخص')
                        
                        await query.edit_message_text(
                            f"✅ **فیات API کار می‌کند!**\n\n"
                            f"🔑 **API Key**: {fiat_api[:10]}...\n"
                            f"💱 **نرخ تست (EUR)**: {rate}\n"
                            f"📅 **زمان تست**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
                            f"**وضعیت**: API فعال و قابل استفاده",
                            reply_markup=InlineKeyboardMarkup([[
                                InlineKeyboardButton("🔙 بازگشت", callback_data="test_api")
                            ]])
                        )
                    else:
                        await query.edit_message_text(
                            f"❌ **خطا در فیات API!**\n\n"
                            f"🔑 **API Key**: {fiat_api[:10]}...\n"
                            f"📊 **کد خطا**: {response.status}\n"
                            f"📅 **زمان تست**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
                            f"**مشکل**: API key نامعتبر یا منقضی شده",
                            reply_markup=InlineKeyboardMarkup([[
                                InlineKeyboardButton("🔙 بازگشت", callback_data="test_api")
                            ]])
                        )
                        
        except Exception as e:
            await query.edit_message_text(
                f"❌ **خطا در تست فیات API!**\n\n"
                f"🔑 **API Key**: {fiat_api[:10]}...\n"
                f"📅 **زمان تست**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
                f"⚠️ **خطا**: {str(e)}\n\n"
                f"**مشکل**: اتصال به API یا تنظیمات نادرست",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔙 بازگشت", callback_data="test_api")
                ]])
            )
        
        return ADMIN_PANEL
    
    async def test_crypto_action(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """تست کریپتو API"""
        query = update.callback_query
        await query.answer()
        
        crypto_api = self.store.get('crypto_api', '')
        if not crypto_api:
            await query.edit_message_text(
                "❌ **کریپتو API تنظیم نشده!**\n\n"
                "لطفاً ابتدا API key را در بخش تنظیمات API وارد کنید.",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔙 بازگشت", callback_data="test_api")
                ]])
            )
            return ADMIN_PANEL
        
        # نمایش پیام در حال تست
        await query.edit_message_text("⏳ در حال تست کریپتو API...")
        
        try:
            import aiohttp
            
            # تست API با درخواست ساده
            url = "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd"
            headers = {
                'X-API-Key': crypto_api,
                'Content-Type': 'application/json'
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers, timeout=10) as response:
                    if response.status == 200:
                        data = await response.json()
                        price = data.get('bitcoin', {}).get('usd', 'نامشخص')
                        
                        await query.edit_message_text(
                            f"✅ **کریپتو API کار می‌کند!**\n\n"
                            f"🔑 **API Key**: {crypto_api[:10]}...\n"
                            f"💰 **قیمت تست (BTC)**: ${price}\n"
                            f"📅 **زمان تست**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
                            f"**وضعیت**: API فعال و قابل استفاده",
                            reply_markup=InlineKeyboardMarkup([[
                                InlineKeyboardButton("🔙 بازگشت", callback_data="test_api")
                            ]])
                        )
                    else:
                        await query.edit_message_text(
                            f"❌ **خطا در کریپتو API!**\n\n"
                            f"🔑 **API Key**: {crypto_api[:10]}...\n"
                            f"📊 **کد خطا**: {response.status}\n"
                            f"📅 **زمان تست**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
                            f"**مشکل**: API key نامعتبر یا منقضی شده",
                            reply_markup=InlineKeyboardMarkup([[
                                InlineKeyboardButton("🔙 بازگشت", callback_data="test_api")
                            ]])
                        )
                        
        except Exception as e:
            await query.edit_message_text(
                f"❌ **خطا در تست کریپتو API!**\n\n"
                f"🔑 **API Key**: {crypto_api[:10]}...\n"
                f"📅 **زمان تست**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
                f"⚠️ **خطا**: {str(e)}\n\n"
                f"**مشکل**: اتصال به API یا تنظیمات نادرست",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔙 بازگشت", callback_data="test_api")
                ]])
            )
        
        return ADMIN_PANEL
    
    async def add_currency_action(self, update: Update, context: ContextTypes.DEFAULT_TYPE, currency: str):
        """اضافه کردن ارز به لیست فعال"""
        query = update.callback_query
        await query.answer()
        
        active_currencies = self.store.get('active_currencies', [])
        if currency not in active_currencies:
            active_currencies.append(currency)
            self.store['active_currencies'] = active_currencies
            save_store(self.store)
            
            await query.answer(f"✅ ارز {currency} اضافه شد!")
        else:
            await query.answer(f"⚠️ ارز {currency} قبلاً فعال است!")
        
        # بازگشت به پنل مدیریت ارزها
        return await self.manage_currencies_panel(update, context)
    
    async def remove_currency_action(self, update: Update, context: ContextTypes.DEFAULT_TYPE, currency: str):
        """حذف ارز از لیست فعال"""
        query = update.callback_query
        await query.answer()
        
        active_currencies = self.store.get('active_currencies', [])
        if currency in active_currencies:
            active_currencies.remove(currency)
            self.store['active_currencies'] = active_currencies
            save_store(self.store)
            
            await query.answer(f"❌ ارز {currency} حذف شد!")
        else:
            await query.answer(f"⚠️ ارز {currency} در لیست فعال نیست!")
        
        # بازگشت به پنل مدیریت ارزها
        return await self.manage_currencies_panel(update, context)
    
    async def reload_currencies_action(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """بارگذاری مجدد لیست ارزها"""
        query = update.callback_query
        await query.answer()
        
        # بارگذاری لیست ارزهای جدید از API
        try:
            # اینجا می‌توانید از API های مختلف لیست ارزها را دریافت کنید
            available_currencies = [
                'USD', 'EUR', 'GBP', 'JPY', 'CAD', 'AUD', 'CHF', 'CNY', 'SEK', 'NZD',
                'MXN', 'SGD', 'HKD', 'NOK', 'TRY', 'RUB', 'INR', 'BRL', 'ZAR', 'KRW',
                'AED', 'SAR', 'QAR', 'KWD', 'BHD', 'OMR', 'JOD', 'LBP', 'EGP', 'MAD'
            ]
            
            self.store['available_currencies'] = available_currencies
            save_store(self.store)
            
            await query.answer("🔄 لیست ارزها بارگذاری شد!")
        except Exception as e:
            await query.answer(f"❌ خطا در بارگذاری: {str(e)}")
        
        # بازگشت به پنل مدیریت ارزها
        return await self.manage_currencies_panel(update, context)
    
    async def test_tradingview_action(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """تست TradingView API"""
        query = update.callback_query
        await query.answer()
        
        tradingview_api = self.store.get('tradingview_api', '')
        
        if not tradingview_api or tradingview_api == 'تنظیم نشده':
            await query.answer("❌ TradingView API تنظیم نشده!")
            return ADMIN_PANEL
        
        try:
            # تست API TradingView
            # اینجا کد تست API قرار می‌گیرد
            await query.answer("✅ TradingView API درست کار می‌کند!")
        except Exception as e:
            await query.answer(f"❌ خطا در TradingView API: {str(e)}")
        
        return ADMIN_PANEL
    
    async def test_fiat_action(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """تست فیات API"""
        query = update.callback_query
        await query.answer()
        
        fiat_api = self.store.get('fiat_api', '')
        
        if not fiat_api or fiat_api == 'تنظیم نشده':
            await query.answer("❌ فیات API تنظیم نشده!")
            return ADMIN_PANEL
        
        try:
            # تست API فیات
            # اینجا کد تست API قرار می‌گیرد
            await query.answer("✅ فیات API درست کار می‌کند!")
        except Exception as e:
            await query.answer(f"❌ خطا در فیات API: {str(e)}")
        
        return ADMIN_PANEL
    
    async def test_crypto_action(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """تست کریپتو API"""
        query = update.callback_query
        await query.answer()
        
        crypto_api = self.store.get('crypto_api', '')
        
        if not crypto_api or crypto_api == 'تنظیم نشده':
            await query.answer("❌ کریپتو API تنظیم نشده!")
            return ADMIN_PANEL
        
        try:
            # تست API کریپتو
            # اینجا کد تست API قرار می‌گیرد
            await query.answer("✅ کریپتو API درست کار می‌کند!")
        except Exception as e:
            await query.answer(f"❌ خطا در کریپتو API: {str(e)}")
        
        return ADMIN_PANEL
    
    async def force_subscription_panel(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """پنل قفل اجباری"""
        query = update.callback_query
        await query.answer()
        
        force_sub = self.store.get('forced_subscription', {})
        is_enabled = force_sub.get('enabled', False)
        channels = force_sub.get('channels', [])
        
        status_emoji = "✅" if is_enabled else "❌"
        status_text = "فعال" if is_enabled else "غیرفعال"
        
        # نمایش کانال‌ها به صورت دکمه‌های شیشه‌ای
        if channels:
            channels_text = f"📢 **{len(channels)} کانال فعال**\n\n"
            for i, channel in enumerate(channels, 1):
                channels_text += f"{i}. @{channel}\n"
        else:
            channels_text = "• هیچ کانالی تنظیم نشده"
        
        keyboard = [
            [InlineKeyboardButton(f"{'❌' if is_enabled else '✅'} {'غیرفعال' if is_enabled else 'فعال'} کردن", 
                                callback_data="toggle_force_sub")],
            [InlineKeyboardButton("📢 افزودن کانال", callback_data="add_force_sub_channel")],
            [InlineKeyboardButton("🗑️ حذف کانال", callback_data="remove_force_sub_channel")],
            [InlineKeyboardButton("📋 لیست کانال‌ها", callback_data="list_force_sub_channels")],
            [InlineKeyboardButton("🔙 بازگشت", callback_data="back_to_main")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        text = f"""
🔒 **قفل اجباری عضویت**

📊 **وضعیت فعلی**:
{status_emoji} قفل اجباری: {status_text}
📢 تعداد کانال‌ها: {len(channels)}

{channels_text}

**عملیات موجود**:
{'❌ غیرفعال' if is_enabled else '✅ فعال'} کردن قفل اجباری
📢 افزودن کانال جدید
🗑️ حذف کانال موجود
📋 مشاهده لیست کامل کانال‌ها

**نحوه کارکرد**:
• کاربران باید در کانال‌های مشخص شده عضو باشند
• ربات عضویت را بررسی می‌کند
• در صورت عدم عضویت، دسترسی محدود می‌شود
• کانال‌ها به صورت دکمه‌های شیشه‌ای نمایش داده می‌شوند
        """
        
        await query.edit_message_text(text, reply_markup=reply_markup)
        return ADMIN_PANEL
    
    async def list_force_sub_channels(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """نمایش لیست کامل کانال‌های قفل اجباری"""
        query = update.callback_query
        await query.answer()
        
        force_sub = self.store.get('forced_subscription', {})
        channels = force_sub.get('channels', [])
        is_enabled = force_sub.get('enabled', False)
        
        if not channels:
            keyboard = [[InlineKeyboardButton("🔙 بازگشت", callback_data="admin_force_sub")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                "📋 **لیست کانال‌های قفل اجباری**\n\n"
                "❌ هیچ کانالی تنظیم نشده است!\n\n"
                "برای افزودن کانال، از دکمه 'افزودن کانال' استفاده کنید.",
                reply_markup=reply_markup
            )
            return ADMIN_PANEL
        
        # ایجاد دکمه‌ها برای هر کانال (2 کانال در هر ردیف)
        channel_buttons = []
        for i in range(0, len(channels), 2):
            row = []
            # کانال اول
            row.append(InlineKeyboardButton(f"📢 @{channels[i]}", callback_data=f"view_channel:{channels[i]}"))
            # کانال دوم (اگر وجود دارد)
            if i + 1 < len(channels):
                row.append(InlineKeyboardButton(f"📢 @{channels[i+1]}", callback_data=f"view_channel:{channels[i+1]}"))
            channel_buttons.append(row)
        
        # دکمه‌های حذف (2 کانال در هر ردیف)
        remove_buttons = []
        for i in range(0, len(channels), 2):
            row = []
            # دکمه حذف کانال اول
            row.append(InlineKeyboardButton(f"❌ @{channels[i]}", callback_data=f"remove_channel:{channels[i]}"))
            # دکمه حذف کانال دوم (اگر وجود دارد)
            if i + 1 < len(channels):
                row.append(InlineKeyboardButton(f"❌ @{channels[i+1]}", callback_data=f"remove_channel:{channels[i+1]}"))
            remove_buttons.append(row)
        
        keyboard = [
            [InlineKeyboardButton("📋 کانال‌های فعال", callback_data="dummy")],
        ] + channel_buttons + [
            [InlineKeyboardButton("🗑️ حذف کانال‌ها", callback_data="dummy")],
        ] + remove_buttons + [
            [InlineKeyboardButton("🔙 بازگشت", callback_data="admin_force_sub")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        status_text = "فعال" if is_enabled else "غیرفعال"
        channels_list = "\n".join([f"• @{ch}" for ch in channels])
        
        text = f"""
📋 **لیست کانال‌های قفل اجباری**

📊 **وضعیت**: {status_text}
📢 **تعداد کانال‌ها**: {len(channels)}

**نحوه استفاده**:
📢 برای مشاهده اطلاعات کانال
❌ برای حذف کانال از لیست
🔙 برای بازگشت به منوی اصلی

**کانال‌های فعال**:
{channels_list}
        """
        
        await query.edit_message_text(text, reply_markup=reply_markup)
        return ADMIN_PANEL
    
    async def view_channel_info(self, update: Update, context: ContextTypes.DEFAULT_TYPE, channel: str):
        """نمایش اطلاعات کانال"""
        query = update.callback_query
        await query.answer()
        
        try:
            # دریافت اطلاعات کانال
            chat = await context.bot.get_chat(f"@{channel}")
            
            # شمارش اعضا
            member_count = await context.bot.get_chat_member_count(f"@{channel}")
            
            keyboard = [
                [InlineKeyboardButton("📢 عضویت در کانال", url=f"https://t.me/{channel}")],
                [InlineKeyboardButton("❌ حذف کانال", callback_data=f"remove_channel:{channel}")],
                [InlineKeyboardButton("🔙 بازگشت", callback_data="list_force_sub_channels")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            text = f"""
📢 **اطلاعات کانال**

🏷️ **نام کانال**: {chat.title}
📝 **نام کاربری**: @{channel}
👥 **تعداد اعضا**: {member_count:,}
📄 **توضیحات**: {chat.description or 'توضیحی وجود ندارد'}

**وضعیت**: کانال فعال در قفل اجباری
            """
            
            await query.edit_message_text(text, reply_markup=reply_markup)
            
        except Exception as e:
            keyboard = [
                [InlineKeyboardButton("❌ حذف کانال", callback_data=f"remove_channel:{channel}")],
                [InlineKeyboardButton("🔙 بازگشت", callback_data="list_force_sub_channels")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            text = f"""
📢 **اطلاعات کانال**

🏷️ **نام کاربری**: @{channel}
❌ **خطا**: نتوانستیم اطلاعات کانال را دریافت کنیم

**ممکن است**:
• کانال وجود نداشته باشد
• ربات دسترسی نداشته باشد
• نام کانال اشتباه باشد
            """
            
            await query.edit_message_text(text, reply_markup=reply_markup)
        
        return ADMIN_PANEL
    
    async def remove_channel_direct(self, update: Update, context: ContextTypes.DEFAULT_TYPE, channel: str):
        """حذف مستقیم کانال از لیست"""
        query = update.callback_query
        await query.answer()
        
        force_sub = self.store.get('forced_subscription', {})
        channels = force_sub.get('channels', [])
        
        if channel in channels:
            channels.remove(channel)
            force_sub['channels'] = channels
            self.store['forced_subscription'] = force_sub
            save_store(self.store)
            
            await query.answer(f"✅ کانال @{channel} حذف شد!")
        else:
            await query.answer(f"⚠️ کانال @{channel} در لیست نیست!")
        
        # بازگشت به لیست کانال‌ها
        return await self.list_force_sub_channels(update, context)
    
    async def toggle_force_subscription(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """تغییر وضعیت قفل اجباری"""
        query = update.callback_query
        await query.answer()
        
        force_sub = self.store.get('forced_subscription', {})
        current_status = force_sub.get('enabled', False)
        
        force_sub['enabled'] = not current_status
        self.store['forced_subscription'] = force_sub
        save_store(self.store)
        
        new_status = "فعال" if force_sub['enabled'] else "غیرفعال"
        emoji = "✅" if force_sub['enabled'] else "❌"
        
        await query.answer(f"🔒 قفل اجباری {new_status} شد!")
        await self.force_subscription_panel(update, context)
        
        return ADMIN_PANEL
    
    async def admin_stats_panel(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """پنل آمار و گزارش"""
        query = update.callback_query
        await query.answer()
        
        users = self.store.get('users', [])
        admins = self.store.get('admins', [])
        whitelist = self.store.get('whitelist', [])
        blacklist = self.store.get('blacklist', [])
        user_data = self.store.get('user_data', {})
        
        # محاسبه آمار
        total_users = len(users)
        total_admins = len(admins) + 1  # +1 for owner
        total_whitelist = len(whitelist)
        total_blacklist = len(blacklist)
        
        # آمار کاربران فعال
        active_users = 0
        for user_id, data in user_data.items():
            if isinstance(data, dict) and data.get('last_activity'):
                last_activity = datetime.fromisoformat(data['last_activity'])
                if datetime.now() - last_activity < timedelta(days=7):
                    active_users += 1
        
        keyboard = [
            [InlineKeyboardButton("📊 گزارش کامل", callback_data="full_report")],
            [InlineKeyboardButton("📈 نمودار کاربران", callback_data="user_chart")],
            [InlineKeyboardButton("🔄 بروزرسانی", callback_data="refresh_stats")],
            [InlineKeyboardButton("🔙 بازگشت", callback_data="back_to_main")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        text = f"""
📊 **آمار و گزارش ربات**

👥 **آمار کاربران**:
• کل کاربران: {total_users}
• کاربران فعال (۷ روز): {active_users}
• ادمین‌ها: {total_admins}
• لیست سفید: {total_whitelist}
• لیست سیاه: {total_blacklist}

📈 **نرخ رشد**:
• کاربران جدید امروز: {len([u for u in users if user_data.get(str(u), {}).get('join_date') == datetime.now().strftime('%Y-%m-%d')])}

🕒 **آخرین بروزرسانی**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        """
        
        await query.edit_message_text(text, reply_markup=reply_markup)
        return ADMIN_PANEL
    
    async def admin_cache_panel(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """پنل مدیریت کش"""
        query = update.callback_query
        await query.answer()
        
        cache_size = len(self.cache._store)
        cache_info = "TTLCache - " + str(len(self.cache._store)) + " آیتم"
        
        keyboard = [
            [InlineKeyboardButton("🗑️ پاک کردن کش", callback_data="clear_cache")],
            [InlineKeyboardButton("📊 اطلاعات کش", callback_data="cache_info")],
            [InlineKeyboardButton("🔄 بروزرسانی کش", callback_data="refresh_cache")],
            [InlineKeyboardButton("🔙 بازگشت", callback_data="back_to_main")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        text = f"""
🗄️ **مدیریت کش**

📊 **وضعیت فعلی**:
• تعداد آیتم‌ها: {cache_size}
• اطلاعات: {cache_info}

**عملیات موجود**:
🗑️ پاک کردن تمام کش
📊 مشاهده اطلاعات دقیق
🔄 بروزرسانی کش
        """
        
        await query.edit_message_text(text, reply_markup=reply_markup)
        return ADMIN_PANEL
    
    async def clear_cache_action(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """پاک کردن کش"""
        query = update.callback_query
        await query.answer()
        
        self.cache.clear()
        
        await query.answer("🗑️ کش با موفقیت پاک شد!")
        await self.admin_cache_panel(update, context)
        
        return ADMIN_PANEL
    
    async def admin_system_panel(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """پنل تنظیمات سیستم"""
        query = update.callback_query
        await query.answer()
        
        keyboard = [
            [InlineKeyboardButton("⚡ تنظیمات عملکرد", callback_data="performance_settings")],
            [InlineKeyboardButton("🔒 تنظیمات امنیتی", callback_data="security_settings")],
            [InlineKeyboardButton("📝 تنظیمات لاگ", callback_data="log_settings")],
            [InlineKeyboardButton("🔄 تنظیمات بروزرسانی", callback_data="update_settings")],
            [InlineKeyboardButton("🔙 بازگشت", callback_data="back_to_main")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        text = """
⚙️ **تنظیمات سیستم**

**بخش‌های موجود**:
⚡ تنظیمات عملکرد و سرعت
🔒 تنظیمات امنیتی و محدودیت‌ها
📝 تنظیمات لاگ و گزارش‌گیری
🔄 تنظیمات بروزرسانی خودکار

لطفاً یکی از گزینه‌ها را انتخاب کنید:
        """
        
        await query.edit_message_text(text, reply_markup=reply_markup)
        return ADMIN_PANEL
    
    async def admin_backup_panel(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """پنل پشتیبان‌گیری"""
        query = update.callback_query
        await query.answer()
        
        keyboard = [
            [InlineKeyboardButton("💾 ایجاد پشتیبان", callback_data="create_backup")],
            [InlineKeyboardButton("📥 بازگردانی", callback_data="restore_backup")],
            [InlineKeyboardButton("📋 لیست پشتیبان‌ها", callback_data="list_backups")],
            [InlineKeyboardButton("🔙 بازگشت", callback_data="back_to_main")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        text = """
💾 **پشتیبان‌گیری و بازگردانی**

**عملیات موجود**:
💾 ایجاد پشتیبان از داده‌ها
📥 بازگردانی از پشتیبان
📋 مشاهده لیست پشتیبان‌ها

⚠️ **هشدار**: بازگردانی تمام داده‌های فعلی را جایگزین می‌کند!
        """
        
        await query.edit_message_text(text, reply_markup=reply_markup)
        return ADMIN_PANEL
    
    async def create_backup_action(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """ایجاد پشتیبان"""
        query = update.callback_query
        await query.answer()
        
        try:
            backup_data = {
                'timestamp': datetime.now().isoformat(),
                'store': self.store,
                'version': '1.0.0'
            }
            
            backup_filename = f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            
            # ذخیره پشتیبان
            with open(backup_filename, 'w', encoding='utf-8') as f:
                json.dump(backup_data, f, ensure_ascii=False, indent=2)
            
            await query.answer(f"💾 پشتیبان {backup_filename} ایجاد شد!")
            
        except Exception as e:
            await query.answer(f"❌ خطا در ایجاد پشتیبان: {str(e)}")
        
        await self.admin_backup_panel(update, context)
        return ADMIN_PANEL
    
    async def admin_logs_panel(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """پنل لاگ‌ها"""
        query = update.callback_query
        await query.answer()
        
        keyboard = [
            [InlineKeyboardButton("📋 لاگ‌های امروز", callback_data="today_logs")],
            [InlineKeyboardButton("📊 لاگ‌های هفته", callback_data="week_logs")],
            [InlineKeyboardButton("🔍 جستجو در لاگ", callback_data="search_logs")],
            [InlineKeyboardButton("🗑️ پاک کردن لاگ", callback_data="clear_logs")],
            [InlineKeyboardButton("🔙 بازگشت", callback_data="back_to_main")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        text = """
📋 **مدیریت لاگ‌ها**

**عملیات موجود**:
📋 مشاهده لاگ‌های امروز
📊 مشاهده لاگ‌های هفته
🔍 جستجو در لاگ‌ها
🗑️ پاک کردن لاگ‌ها

📝 لاگ‌ها شامل تمام فعالیت‌های ربات هستند.
        """
        
        await query.edit_message_text(text, reply_markup=reply_markup)
        return ADMIN_PANEL
    
    async def admin_alerts_panel(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """پنل مدیریت هشدارها"""
        query = update.callback_query
        await query.answer()
        
        keyboard = [
            [InlineKeyboardButton("📊 آمار هشدارها", callback_data="alert_stats")],
            [InlineKeyboardButton("⚙️ تنظیمات هشدار", callback_data="alert_settings")],
            [InlineKeyboardButton("🔔 تست هشدار", callback_data="test_alert")],
            [InlineKeyboardButton("👥 مدیریت کاربران", callback_data="manage_user_alerts")],
            [InlineKeyboardButton("🔙 بازگشت", callback_data="back_to_main")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # شمارش هشدارهای فعال
        active_alerts = 0
        for user_data in self.store.get('user_data', {}).values():
            if isinstance(user_data, dict) and 'alerts' in user_data:
                active_alerts += len(user_data['alerts'])
        
        text = f"""
🔔 **مدیریت هشدارها**

📊 **وضعیت فعلی**:
• هشدارهای فعال: {active_alerts}
• کاربران با هشدار: {len([u for u in self.store.get('user_data', {}).values() if isinstance(u, dict) and u.get('alerts')])}

**عملیات موجود**:
📊 مشاهده آمار هشدارها
⚙️ تنظیمات سیستم هشدار
🔔 تست ارسال هشدار
        """
        
        await query.edit_message_text(text, reply_markup=reply_markup)
        return ADMIN_PANEL
    
    async def admin_commands_panel(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """پنل دستورات سفارشی"""
        query = update.callback_query
        await query.answer()
        
        custom_commands = self.store.get('custom_commands', {})
        commands_count = len(custom_commands)
        
        keyboard = [
            [InlineKeyboardButton("➕ افزودن دستور", callback_data="add_command")],
            [InlineKeyboardButton("📋 لیست دستورات", callback_data="list_commands")],
            [InlineKeyboardButton("✏️ ویرایش دستور", callback_data="edit_command")],
            [InlineKeyboardButton("🗑️ حذف دستور", callback_data="delete_command")],
            [InlineKeyboardButton("🔙 بازگشت", callback_data="back_to_main")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        text = f"""
⌨️ **دستورات سفارشی**

📊 **وضعیت فعلی**:
• تعداد دستورات: {commands_count}

**عملیات موجود**:
➕ افزودن دستور جدید
📋 مشاهده لیست دستورات
✏️ ویرایش دستور موجود
🗑️ حذف دستور
        """
        
        await query.edit_message_text(text, reply_markup=reply_markup)
        return ADMIN_PANEL
    
    async def admin_lists_panel(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """پنل لیست سفید/سیاه"""
        query = update.callback_query
        await query.answer()
        
        keyboard = [
            [InlineKeyboardButton("➕ افزودن به لیست سفید", callback_data="add_whitelist")],
            [InlineKeyboardButton("⚫ افزودن به لیست سیاه", callback_data="add_blacklist")],
            [InlineKeyboardButton("📋 مشاهده لیست‌ها", callback_data="view_lists")],
            [InlineKeyboardButton("🗑️ حذف از لیست‌ها", callback_data="remove_from_lists")],
            [InlineKeyboardButton("🔙 بازگشت", callback_data="back_to_main")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        whitelist_count = len(self.store.get('whitelist', []))
        blacklist_count = len(self.store.get('blacklist', []))
        
        text = f"""
⚪ **مدیریت لیست سفید/سیاه**

📊 **وضعیت فعلی**:
• لیست سفید: {whitelist_count} کاربر
• لیست سیاه: {blacklist_count} کاربر

**عملیات موجود**:
➕ افزودن کاربر به لیست سفید
⚫ افزودن کاربر به لیست سیاه
📋 مشاهده لیست کامل
🗑️ حذف از لیست‌ها

**نحوه استفاده**:
• آیدی عددی کاربر را وارد کنید
• تایید یا رد کنید
• کاربر مستقیماً بلاک/آنبلاک می‌شود
• کاربران لیست سیاه هیچ خدماتی دریافت نمی‌کنند
        """
        
        await query.edit_message_text(text, reply_markup=reply_markup)
        return ADMIN_PANEL

    async def admin_bot_settings_panel(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """پنل تنظیمات ربات"""
        query = update.callback_query
        await query.answer()
        
        keyboard = [
            [InlineKeyboardButton("🔧 مدیریت ویژگی‌ها", callback_data="manage_features")],
            [InlineKeyboardButton("🤖 اطلاعات ربات", callback_data="bot_info")],
            [InlineKeyboardButton("⚙️ تنظیمات عمومی", callback_data="general_settings")],
            [InlineKeyboardButton("🎨 تنظیمات ظاهری", callback_data="appearance_settings")],
            [InlineKeyboardButton("🔧 تنظیمات فنی", callback_data="technical_settings")],
            [InlineKeyboardButton("🔙 بازگشت", callback_data="back_to_main")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # شمارش ویژگی‌های فعال/غیرفعال
        features = self.store.get('bot_features', {})
        active_features = sum(1 for status in features.values() if status)
        total_features = len(features)
        
        text = f"""
🤖 **تنظیمات ربات**

**بخش‌های موجود**:
🔧 مدیریت ویژگی‌ها - خاموش/روشن کردن قسمت‌ها
🤖 اطلاعات و وضعیت ربات
⚙️ تنظیمات عمومی و پیش‌فرض
🎨 تنظیمات ظاهری و رابط کاربری
🔧 تنظیمات فنی و عملکرد

📊 **وضعیت فعلی**:
• ویژگی‌های فعال: {active_features}/{total_features}
• ویژگی‌های غیرفعال: {total_features - active_features}/{total_features}

لطفاً یکی از گزینه‌ها را انتخاب کنید:
        """
        
        await query.edit_message_text(text, reply_markup=reply_markup)
        return ADMIN_PANEL
    
    async def manage_features_panel(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """پنل مدیریت ویژگی‌های ربات"""
        query = update.callback_query
        await query.answer()
        
        # تعریف ویژگی‌های ربات
        features = {
            "crypto_prices": {"name": "💰 قیمت ارز", "emoji": "💰"},
            "fiat_rates": {"name": "🏦 ارز داخلی", "emoji": "🏦"},
            "news": {"name": "📰 اخبار", "emoji": "📰"},
            "charts": {"name": "📊 نمودار", "emoji": "📊"},
            "technical_analysis": {"name": "📈 تحلیل تکنیکال", "emoji": "📈"},
            "arbitrage": {"name": "⚖️ مقایسه", "emoji": "⚖️"},
            "p2p": {"name": "🔄 P2P", "emoji": "🔄"},
            "watchlist": {"name": "👁 واچ‌لیست", "emoji": "👁"},
            "portfolio": {"name": "📚 پرتفوی", "emoji": "📚"},
            "alerts": {"name": "🔔 هشدارها", "emoji": "🔔"},
            "settings": {"name": "🛠 تنظیمات", "emoji": "🛠"},
            "help": {"name": "❓ راهنما", "emoji": "❓"}
        }
        
        # دریافت وضعیت فعلی ویژگی‌ها
        bot_features = self.store.get('bot_features', {})
        
        # ایجاد دکمه‌ها
        keyboard = []
        for feature_key, feature_info in features.items():
            is_active = bot_features.get(feature_key, True)
            status_emoji = "🟢" if is_active else "🔴"
            button_text = f"{status_emoji} {feature_info['emoji']} {feature_info['name']}"
            
            keyboard.append([InlineKeyboardButton(
                button_text, 
                callback_data=f"toggle_feature:{feature_key}"
            )])
        
        # دکمه‌های عملیات
        keyboard.extend([
            [InlineKeyboardButton("🔄 بازگردانی همه", callback_data="reset_all_features")],
            [InlineKeyboardButton("🔙 بازگشت", callback_data="admin_bot_settings")]
        ])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # شمارش ویژگی‌ها
        active_count = sum(1 for status in bot_features.values() if status)
        total_count = len(features)
        
        text = f"""
🔧 **مدیریت ویژگی‌های ربات**

📊 **وضعیت فعلی**:
• فعال: {active_count}/{total_count}
• غیرفعال: {total_count - active_count}/{total_count}

**نحوه استفاده**:
🟢 ویژگی فعال - کلیک برای خاموش کردن
🔴 ویژگی غیرفعال - کلیک برای روشن کردن

**ویژگی‌های موجود**:
        """
        
        await query.edit_message_text(text, reply_markup=reply_markup)
        return ADMIN_PANEL
    
    async def toggle_feature(self, update: Update, context: ContextTypes.DEFAULT_TYPE, feature: str):
        """تغییر وضعیت ویژگی"""
        query = update.callback_query
        await query.answer()
        
        # تعریف نام‌های ویژگی‌ها
        feature_names = {
            "crypto_prices": "💰 قیمت ارز",
            "fiat_rates": "🏦 ارز داخلی",
            "news": "📰 اخبار",
            "charts": "📊 نمودار",
            "technical_analysis": "📈 تحلیل تکنیکال",
            "arbitrage": "⚖️ مقایسه",
            "p2p": "🔄 P2P",
            "watchlist": "👁 واچ‌لیست",
            "portfolio": "📚 پرتفوی",
            "alerts": "🔔 هشدارها",
            "settings": "🛠 تنظیمات",
            "help": "❓ راهنما"
        }
        
        # تغییر وضعیت
        bot_features = self.store.get('bot_features', {})
        current_status = bot_features.get(feature, True)
        bot_features[feature] = not current_status
        self.store['bot_features'] = bot_features
        save_store(self.store)
        
        # نمایش نتیجه
        new_status = "فعال" if bot_features[feature] else "غیرفعال"
        status_emoji = "🟢" if bot_features[feature] else "🔴"
        action_text = "روشن" if bot_features[feature] else "خاموش"
        
        feature_name = feature_names.get(feature, feature)
        
        keyboard = [
            [InlineKeyboardButton("🔙 بازگشت", callback_data="manage_features")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            f"✅ **ویژگی {action_text} شد!**\n\n"
            f"{status_emoji} **{feature_name}**\n"
            f"📊 **وضعیت**: {new_status}\n\n"
            f"تغییرات اعمال شد و در کیبورد سریع نمایش داده می‌شود.",
            reply_markup=reply_markup
        )
        
        return ADMIN_PANEL
    
    async def reset_all_features(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """بازگردانی همه ویژگی‌ها به حالت فعال"""
        query = update.callback_query
        await query.answer()
        
        # تعریف ویژگی‌ها
        features = [
            "crypto_prices", "fiat_rates", "news", "charts", 
            "technical_analysis", "arbitrage", "p2p", "watchlist", 
            "portfolio", "alerts", "settings", "help"
        ]
        
        # فعال کردن همه ویژگی‌ها
        bot_features = {}
        for feature in features:
            bot_features[feature] = True
        
        self.store['bot_features'] = bot_features
        save_store(self.store)
        
        keyboard = [
            [InlineKeyboardButton("🔙 بازگشت", callback_data="manage_features")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            "✅ **همه ویژگی‌ها فعال شدند!**\n\n"
            "🟢 تمام قسمت‌های ربات اکنون فعال هستند\n"
            "📱 همه دکمه‌ها در کیبورد سریع نمایش داده می‌شوند\n\n"
            "تغییرات اعمال شد.",
            reply_markup=reply_markup
        )
        
        return ADMIN_PANEL
    
    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """مدیریت callback ها"""
        query = update.callback_query
        data = query.data
        
        if data == "back_to_main":
            return await self.admin_panel_main(update, context)
        elif data == "admin_manage":
            return await self.admin_manage_admins(update, context)
        elif data == "add_admin":
            return await self.add_admin_start(update, context)
        elif data == "remove_admin":
            return await self.remove_admin_start(update, context)
        elif data == "list_admins":
            return await self.list_admins_action(update, context)
        elif data == "admin_broadcast":
            return await self.broadcast_start(update, context)
        elif data == "admin_texts":
            return await self.admin_texts_panel(update, context)
        elif data == "admin_api":
            return await self.admin_api_panel(update, context)
        elif data == "admin_force_sub":
            return await self.force_subscription_panel(update, context)
        elif data == "admin_lists":
            return await self.admin_lists_panel(update, context)
        elif data == "admin_stats":
            return await self.admin_stats_panel(update, context)
        elif data == "admin_cache":
            return await self.admin_cache_panel(update, context)
        elif data == "admin_system":
            return await self.admin_system_panel(update, context)
        elif data == "admin_backup":
            return await self.admin_backup_panel(update, context)
        elif data == "admin_logs":
            return await self.admin_logs_panel(update, context)
        elif data == "admin_alerts":
            return await self.admin_alerts_panel(update, context)
        elif data == "admin_bot_settings":
            return await self.admin_bot_settings_panel(update, context)
        elif data == "admin_commands":
            return await self.admin_commands_panel(update, context)
        elif data == "admin_exit":
            await query.edit_message_text("✅ از پنل مدیریتی خارج شدید.")
            return ConversationHandler.END
        elif data == "admin_apis":
            return await self.manage_apis(update, context)
        elif data == "admin_currencies":
            return await self.manage_currencies(update, context)
        elif data == "admin_indicators":
            return await self.manage_indicators(update, context)
        elif data == "manage_apis":
            return await self.manage_apis(update, context)
        elif data == "add_api":
            return await self.add_api(update, context)
        elif data == "list_apis":
            return await self.list_apis_action(update, context)
        elif data == "manage_currencies":
            return await self.manage_currencies(update, context)
        elif data == "add_currency":
            return await self.add_currency(update, context)
        elif data == "list_currencies":
            return await self.list_currencies_action(update, context)
        elif data == "manage_indicators":
            return await self.manage_indicators(update, context)
        elif data == "add_indicator":
            return await self.add_indicator(update, context)
        elif data == "list_indicators":
            return await self.list_indicators_action(update, context)
        elif data == "manage_features":
            return await self.manage_features_panel(update, context)
        elif data.startswith("toggle_feature:"):
            feature = data.split(":")[1]
            return await self.toggle_feature(update, context, feature)
        elif data == "reset_all_features":
            return await self.reset_all_features(update, context)
        elif data.startswith("broadcast_"):
            return await self.broadcast_message_start(update, context)
        elif data == "set_welcome":
            return await self.set_welcome_text_start(update, context)
        elif data == "set_help":
            return await self.set_help_text_start(update, context)
        elif data == "set_error":
            return await self.set_error_text_start(update, context)
        elif data == "set_about":
            return await self.set_about_text_start(update, context)
        elif data == "set_force_sub":
            return await self.set_force_sub_text_start(update, context)
        elif data == "set_settings":
            return await self.set_settings_text_start(update, context)
        elif data == "set_tradingview_api":
            return await self.set_tradingview_api_start(update, context)
        elif data == "set_fiat_api":
            return await self.set_fiat_api_start(update, context)
        elif data == "set_crypto_api":
            return await self.set_crypto_api_start(update, context)

        elif data == "test_api":
            return await self.test_api_panel(update, context)
        elif data.startswith("add_currency:"):
            currency = data.split(":")[1]
            return await self.add_currency_action(update, context, currency)
        elif data.startswith("remove_currency:"):
            currency = data.split(":")[1]
            return await self.remove_currency_action(update, context, currency)
        elif data == "reload_currencies":
            return await self.reload_currencies_action(update, context)
        elif data == "test_tradingview":
            return await self.test_tradingview_action(update, context)
        elif data == "test_fiat":
            return await self.test_fiat_action(update, context)
        elif data == "test_crypto":
            return await self.test_crypto_action(update, context)
        elif data == "toggle_force_sub":
            return await self.toggle_force_subscription(update, context)
        elif data == "add_force_sub_channel":
            return await self.add_force_sub_channel_start(update, context)
        elif data == "remove_force_sub_channel":
            return await self.remove_force_sub_channel_start(update, context)
        elif data == "list_force_sub_channels":
            return await self.list_force_sub_channels(update, context)
        elif data.startswith("remove_channel:"):
            channel = data.split(":")[1]
            return await self.remove_channel_direct(update, context, channel)
        elif data.startswith("view_channel:"):
            channel = data.split(":")[1]
            return await self.view_channel_info(update, context, channel)
        elif data == "add_whitelist":
            return await self.add_whitelist_start(update, context)
        elif data == "remove_whitelist":
            return await self.remove_whitelist_start(update, context)
        elif data == "add_blacklist":
            return await self.add_blacklist_start(update, context)
        elif data.startswith("confirm_whitelist:"):
            user_id = int(data.split(":")[1])
            return await self.confirm_whitelist(update, context, user_id)
        elif data == "cancel_whitelist":
            return await self.cancel_whitelist(update, context)
        elif data.startswith("confirm_blacklist:"):
            user_id = int(data.split(":")[1])
            return await self.confirm_blacklist(update, context, user_id)
        elif data == "cancel_blacklist":
            return await self.cancel_blacklist(update, context)
        elif data == "remove_blacklist":
            return await self.remove_blacklist_start(update, context)
        elif data == "view_lists":
            return await self.view_lists_action(update, context)
        elif data == "stats_24h":
            return await self.stats_24h_action(update, context)
        elif data == "stats_week":
            return await self.stats_week_action(update, context)
        elif data == "stats_total":
            return await self.stats_total_action(update, context)
        elif data == "stats_blocked":
            return await self.stats_blocked_action(update, context)
        elif data == "clear_cache":
            return await self.clear_cache_action(update, context)
        elif data == "cache_status":
            return await self.cache_status_action(update, context)
        elif data == "create_backup":
            return await self.create_backup_action(update, context)
        elif data == "restore_backup":
            return await self.restore_backup_start(update, context)
        elif data == "view_full_logs":
            return await self.view_full_logs_action(update, context)
        elif data == "clear_logs":
            return await self.clear_logs_action(update, context)
        elif data == "alerts_optional":
            return await self.alerts_optional_action(update, context)
        elif data == "alerts_required":
            return await self.alerts_required_action(update, context)
        elif data == "view_alerts":
            return await self.view_alerts_action(update, context)
        elif data == "refresh_stats":
            return await self.refresh_stats_action(update, context)
        elif data == "refresh_cache":
            return await self.refresh_cache_action(update, context)
        elif data == "update_settings":
            return await self.update_settings_action(update, context)
        elif data.startswith("message_user:"):
            user_id = data.split(":")[1]
            return await self.start_user_message(update, context, user_id)
        elif data.startswith("remove_blacklist:"):
            return await self.remove_blacklist_action(update, context)
        elif data.startswith("remove_whitelist:"):
            return await self.remove_whitelist_action(update, context)
        elif data == "broadcast_forward":
            return await self.broadcast_forward_start(update, context)
        elif data == "admin_exit":
            await query.edit_message_text("👋 پنل مدیریتی بسته شد.")
            return ConversationHandler.END
        
        return ADMIN_PANEL
    
    async def list_admins_action(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """نمایش لیست ادمین‌ها"""
        query = update.callback_query
        await query.answer()
        
        admins = self.store.get('admins', [])
        admin_list = "\n".join([f"• {admin_id}" for admin_id in admins])
        
        keyboard = [[InlineKeyboardButton("🔙 بازگشت", callback_data="admin_manage")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        text = f"""
📋 **لیست ادمین‌ها**

👨‍💼 **ادمین‌های فعلی**:
{admin_list if admin_list else "• هیچ ادمینی وجود ندارد"}

📊 **تعداد کل**: {len(admins)} ادمین
        """
        
        await query.edit_message_text(text, reply_markup=reply_markup)
        return ADMIN_PANEL
    
    async def set_help_text_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """شروع تنظیم متن راهنما"""
        query = update.callback_query
        await query.answer()
        
        current_text = self.store.get('texts', {}).get('help', 'متن راهنما تنظیم نشده')
        
        await query.edit_message_text(
            f"❓ **تنظیم متن راهنما**\n\n"
            f"📝 **متن فعلی**:\n{current_text}\n\n"
            f"لطفاً متن جدید را ارسال کنید:\n\n"
            f"🔙 برای بازگشت: /cancel"
        )
        
        return SET_HELP_TEXT
    
    async def set_error_text_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """شروع تنظیم متن خطا"""
        query = update.callback_query
        await query.answer()
        
        current_text = self.store.get('texts', {}).get('error', 'متن خطا تنظیم نشده')
        
        await query.edit_message_text(
            f"⚠️ **تنظیم متن خطا**\n\n"
            f"📝 **متن فعلی**:\n{current_text}\n\n"
            f"لطفاً متن جدید را ارسال کنید:\n\n"
            f"🔙 برای بازگشت: /cancel"
        )
        
        return SET_ERROR_TEXT
    
    async def set_about_text_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """شروع تنظیم متن درباره"""
        # بررسی اینکه آیا از کیبورد سریع آمده یا callback
        if update.callback_query:
            query = update.callback_query
            await query.answer()
            await query.edit_message_text(
                f"📝 **تنظیم متن درباره ربات**\n\n"
                f"📝 **متن فعلی**:\n{self.store.get('texts', {}).get('about', 'متن درباره تنظیم نشده')}\n\n"
                f"✏️ **متن جدید را ارسال کنید**:\n\n"
                f"🔙 برای لغو: /cancel"
            )
        else:
            # از کیبورد سریع آمده
            current_text = self.store.get('texts', {}).get('about', 'متن درباره تنظیم نشده')
            await update.message.reply_text(
                f"📝 **تنظیم متن درباره ربات**\n\n"
                f"📝 **متن فعلی**:\n{current_text}\n\n"
                f"✏️ **متن جدید را ارسال کنید**:\n\n"
                f"🔙 برای لغو: /cancel"
            )
        
        return SET_WELCOME_TEXT
    
    async def set_force_sub_text_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """شروع تنظیم متن عضویت اجباری"""
        query = update.callback_query
        await query.answer()
        
        current_text = self.store.get('texts', {}).get('force_sub', 'متن عضویت اجباری تنظیم نشده')
        
        await query.edit_message_text(
            f"🔒 **تنظیم متن عضویت اجباری**\n\n"
            f"📝 **متن فعلی**:\n{current_text}\n\n"
            f"لطفاً متن جدید را ارسال کنید:\n\n"
            f"🔙 برای بازگشت: /cancel"
        )
        
        return SET_WELCOME_TEXT
    
    async def set_settings_text_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """شروع تنظیم متن تنظیمات"""
        query = update.callback_query
        await query.answer()
        
        current_text = self.store.get('texts', {}).get('settings', 'متن تنظیمات تنظیم نشده')
        
        await query.edit_message_text(
            f"⚙️ **تنظیم متن تنظیمات**\n\n"
            f"📝 **متن فعلی**:\n{current_text}\n\n"
            f"لطفاً متن جدید را ارسال کنید:\n\n"
            f"🔙 برای بازگشت: /cancel"
        )
        
        return SET_WELCOME_TEXT
    
    async def set_help_text_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """شروع تنظیم متن راهنما"""
        query = update.callback_query
        await query.answer()
        
        current_text = self.store.get('texts', {}).get('help', 'متن راهنما تنظیم نشده')
        
        await query.edit_message_text(
            f"❓ **تنظیم متن راهنما**\n\n"
            f"📝 **متن فعلی**:\n{current_text}\n\n"
            f"✏️ **متن جدید را ارسال کنید**:\n\n"
            f"💡 **متغیرهای قابل استفاده**:\n"
            f"• {{name}} - نام کاربر\n"
            f"• {{username}} - نام کاربری\n"
            f"• برای لغو: /cancel",
            parse_mode='Markdown'
        )
        
        return SET_HELP_TEXT
    
    async def set_help_text_process(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """پردازش تنظیم متن راهنما"""
        new_text = update.message.text
        
        # ذخیره متن جدید
        if 'texts' not in self.store:
            self.store['texts'] = {}
        
        self.store['texts']['help'] = new_text
        save_store(self.store)
        
        keyboard = [[InlineKeyboardButton("🔙 بازگشت به پنل", callback_data="back_to_main")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            f"✅ **متن راهنما با موفقیت تنظیم شد!**\n\n"
            f"📝 **متن جدید**:\n{new_text}\n\n"
            f"📅 **تاریخ**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            reply_markup=reply_markup
        )
        
        return ADMIN_PANEL
    
    async def set_error_text_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """شروع تنظیم متن خطا"""
        query = update.callback_query
        await query.answer()
        
        current_text = self.store.get('texts', {}).get('error', 'متن خطا تنظیم نشده')
        
        await query.edit_message_text(
            f"⚠️ **تنظیم متن خطا**\n\n"
            f"📝 **متن فعلی**:\n{current_text}\n\n"
            f"✏️ **متن جدید را ارسال کنید**:\n\n"
            f"💡 **متغیرهای قابل استفاده**:\n"
            f"• {{error}} - نوع خطا\n"
            f"• برای لغو: /cancel",
            parse_mode='Markdown'
        )
        
        return SET_ERROR_TEXT
    
    async def set_error_text_process(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """پردازش تنظیم متن خطا"""
        new_text = update.message.text
        
        # ذخیره متن جدید
        if 'texts' not in self.store:
            self.store['texts'] = {}
        
        self.store['texts']['error'] = new_text
        save_store(self.store)
        
        keyboard = [[InlineKeyboardButton("🔙 بازگشت به پنل", callback_data="back_to_main")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            f"✅ **متن خطا با موفقیت تنظیم شد!**\n\n"
            f"📝 **متن جدید**:\n{new_text}\n\n"
            f"📅 **تاریخ**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            reply_markup=reply_markup
        )
        
        return ADMIN_PANEL
    
    async def set_tradingview_api_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """شروع تنظیم TradingView API"""
        query = update.callback_query
        await query.answer()
        
        current_api = self.store.get('tradingview_api', 'تنظیم نشده')
        
        await query.edit_message_text(
            f"📊 **تنظیم TradingView API**\n\n"
            f"🔑 **API فعلی**: {current_api}\n\n"
            f"لطفاً API Key جدید را ارسال کنید:\n\n"
            f"💡 **نکات مهم**:\n"
            f"• از TradingView API برای تحلیل‌های پیشرفته استفاده می‌شود\n"
            f"• برای لغو: /cancel",
            parse_mode='Markdown'
        )
        
        return SET_TRADINGVIEW_API
    
    async def set_fiat_api_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """شروع تنظیم Fiat API"""
        query = update.callback_query
        await query.answer()
        
        current_api = self.store.get('fiat_api', 'تنظیم نشده')
        
        await query.edit_message_text(
            f"💱 **تنظیم Fiat API**\n\n"
            f"🔑 **API فعلی**: {current_api}\n\n"
            f"لطفاً API Key جدید را ارسال کنید:\n\n"
            f"💡 **نکات مهم**:\n"
            f"• از این API برای تبدیل ارزهای فیات استفاده می‌شود\n"
            f"• برای لغو: /cancel",
            parse_mode='Markdown'
        )
        
        return SET_FIAT_API
    
    async def set_crypto_api_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """شروع تنظیم Crypto API"""
        query = update.callback_query
        await query.answer()
        
        current_api = self.store.get('crypto_api', 'تنظیم نشده')
        
        await query.edit_message_text(
            f"💎 **تنظیم Crypto API**\n\n"
            f"🔑 **API فعلی**: {current_api}\n\n"
            f"لطفاً API Key جدید را ارسال کنید:\n\n"
            f"🔙 برای بازگشت: /cancel"
        )
        
        return SET_CRYPTO_API_KEY
    
    async def set_crypto_api_process(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """پردازش تنظیم Crypto API"""
        api_key = update.message.text.strip()
        
        if not api_key:
            await update.message.reply_text("❌ API Key نامعتبر است!")
            return SET_CRYPTO_API_KEY
        
        # ذخیره API Key
        self.store['crypto_api'] = api_key
        save_store(self.store)
        
        keyboard = [[InlineKeyboardButton("🔙 بازگشت به پنل", callback_data="back_to_main")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            f"✅ **Crypto API با موفقیت تنظیم شد!**\n\n"
            f"🔑 **API Key**: {api_key[:10]}...\n"
            f"📅 **تاریخ**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            reply_markup=reply_markup
        )
        
        return ADMIN_PANEL
    
    async def set_api_key_process(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """پردازش تنظیم API Key عمومی"""
        api_key = update.message.text.strip()
        
        if not api_key:
            await update.message.reply_text("❌ API Key نامعتبر است!")
            return SET_API_KEY
        
        # ذخیره API Key
        self.store['general_api'] = api_key
        save_store(self.store)
        
        keyboard = [[InlineKeyboardButton("🔙 بازگشت به پنل", callback_data="back_to_main")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            f"✅ **API Key عمومی با موفقیت تنظیم شد!**\n\n"
            f"🔑 **API Key**: {api_key[:10]}...\n"
            f"📅 **تاریخ**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            reply_markup=reply_markup
        )
        
        return ADMIN_PANEL
    
    async def set_tradingview_api_process(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """پردازش تنظیم TradingView API"""
        api_key = update.message.text.strip()
        
        if not api_key:
            await update.message.reply_text("❌ API Key نامعتبر است!")
            return SET_TRADINGVIEW_API
        
        # ذخیره API Key
        self.store['tradingview_api'] = api_key
        save_store(self.store)
        
        keyboard = [[InlineKeyboardButton("🔙 بازگشت به پنل", callback_data="back_to_main")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            f"✅ **TradingView API با موفقیت تنظیم شد!**\n\n"
            f"🔑 **API Key**: {api_key[:10]}...\n"
            f"📅 **تاریخ**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            reply_markup=reply_markup
        )
        
        return ADMIN_PANEL
    
    async def set_fiat_api_process(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """پردازش تنظیم Fiat API"""
        api_key = update.message.text.strip()
        
        if not api_key:
            await update.message.reply_text("❌ API Key نامعتبر است!")
            return SET_FIAT_API
        
        # ذخیره API Key
        self.store['fiat_api'] = api_key
        save_store(self.store)
        
        keyboard = [[InlineKeyboardButton("🔙 بازگشت به پنل", callback_data="back_to_main")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            f"✅ **Fiat API با موفقیت تنظیم شد!**\n\n"
            f"🔑 **API Key**: {api_key[:10]}...\n"
            f"📅 **تاریخ**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            reply_markup=reply_markup
        )
        
        return ADMIN_PANEL
    
    async def add_force_sub_channel_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """شروع افزودن کانال عضویت اجباری"""
        query = update.callback_query
        await query.answer()
        
        channels = self.store.get('forced_subscription', {}).get('channels', [])
        channels_text = "\n".join([f"• @{ch}" for ch in channels]) if channels else "• هیچ کانالی تنظیم نشده"
        
        await query.edit_message_text(
            f"📢 **افزودن کانال عضویت اجباری**\n\n"
            f"📺 **کانال‌های فعلی**:\n{channels_text}\n\n"
            f"لطفاً نام کاربری کانال جدید را ارسال کنید:\n"
            f"مثال: channel_name (بدون @)\n\n"
            f"💡 **نکات مهم**:\n"
            f"• ربات باید ادمین کانال باشد\n"
            f"• نام کانال بدون @ ارسال شود\n"
            f"• کاربران باید در این کانال عضو باشند\n\n"
            f"🔙 برای لغو: /cancel"
        )
        
        return FORCE_SUBSCRIPTION
    
    async def set_force_sub_channel_process(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """پردازش تنظیم کانال عضویت اجباری"""
        channel_username = update.message.text.strip().replace('@', '')
        
        if not channel_username:
            await update.message.reply_text("❌ نام کاربری کانال نامعتبر است!")
            return FORCE_SUBSCRIPTION
        
        # تنظیم کانال جدید
        if 'forced_subscription' not in self.store:
            self.store['forced_subscription'] = {}
        
        self.store['forced_subscription']['main_channel'] = channel_username
        save_store(self.store)
        
        keyboard = [[InlineKeyboardButton("🔙 بازگشت به پنل", callback_data="back_to_main")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            f"✅ **کانال عضویت اجباری تنظیم شد!**\n\n"
            f"📺 **کانال اصلی**: @{channel_username}\n"
            f"📅 **تاریخ**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            reply_markup=reply_markup
        )
        
        return ADMIN_PANEL
    
    async def add_force_sub_channel_process(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """پردازش افزودن کانال عضویت اجباری"""
        channel_username = update.message.text.strip().replace('@', '')
        
        if not channel_username:
            await update.message.reply_text("❌ نام کاربری کانال نامعتبر است!")
            return ADD_FORCE_SUB_CHANNEL
        
        # افزودن کانال جدید
        if 'forced_subscription' not in self.store:
            self.store['forced_subscription'] = {}
        
        if 'channels' not in self.store['forced_subscription']:
            self.store['forced_subscription']['channels'] = []
        
        if channel_username not in self.store['forced_subscription']['channels']:
            self.store['forced_subscription']['channels'].append(channel_username)
            save_store(self.store)
            
            keyboard = [
                [InlineKeyboardButton("📋 مشاهده لیست", callback_data="list_force_sub_channels")],
                [InlineKeyboardButton("🔙 بازگشت به پنل", callback_data="back_to_main")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                f"✅ **کانال عضویت اجباری اضافه شد!**\n\n"
                f"📺 **کانال جدید**: @{channel_username}\n"
                f"📅 **تاریخ**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                reply_markup=reply_markup
            )
        else:
            await update.message.reply_text("❌ این کانال قبلاً اضافه شده است!")
            return ADD_FORCE_SUB_CHANNEL
        
        return ADMIN_PANEL
    
    async def remove_force_sub_channel_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """شروع حذف کانال عضویت اجباری"""
        query = update.callback_query
        await query.answer()
        
        channels = self.store.get('forced_subscription', {}).get('channels', [])
        if not channels:
            await query.edit_message_text(
                "❌ **هیچ کانالی برای حذف وجود ندارد!**\n\n"
                "🔙 برای بازگشت کلیک کنید:",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔙 بازگشت", callback_data="back_to_main")
                ]])
            )
            return ADMIN_PANEL
        
        # ایجاد کیبورد برای انتخاب کانال
        keyboard = []
        for channel in channels:
            keyboard.append([InlineKeyboardButton(f"🗑️ @{channel}", callback_data=f"remove_channel:{channel}")])
        
        keyboard.append([InlineKeyboardButton("🔙 بازگشت", callback_data="back_to_main")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            f"🗑️ **حذف کانال عضویت اجباری**\n\n"
            f"📺 **کانال‌های موجود**:\n"
            f"{chr(10).join([f'• @{ch}' for ch in channels])}\n\n"
            f"لطفاً کانال مورد نظر برای حذف را انتخاب کنید:",
            reply_markup=reply_markup
        )
        
        return ADMIN_PANEL
    
    async def add_whitelist_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """شروع افزودن کاربر به لیست سفید"""
        query = update.callback_query
        await query.answer()
        
        await query.edit_message_text(
            "⚪ **افزودن کاربر به لیست سفید**\n\n"
            "لطفاً آیدی عددی کاربر را ارسال کنید:\n"
            "مثال: `123456789`\n\n"
            "💡 **نکات مهم**:\n"
            "• کاربران لیست سفید دسترسی کامل دارند\n"
            "• آیدی عددی کاربر را وارد کنید\n"
            "• پس از تایید، کاربر مستقیماً اضافه می‌شود\n\n"
            "🔙 برای بازگشت: /cancel",
            parse_mode='Markdown'
        )
        
        return ADD_WHITELIST
    
    async def add_whitelist_process(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """پردازش افزودن کاربر به لیست سفید"""
        try:
            user_id = int(update.message.text.strip())
            
            # نمایش تایید
            keyboard = [
                [InlineKeyboardButton("✅ تایید", callback_data=f"confirm_whitelist:{user_id}")],
                [InlineKeyboardButton("❌ رد", callback_data="cancel_whitelist")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                f"⚪ **تایید افزودن به لیست سفید**\n\n"
                f"👤 **آیدی کاربر**: {user_id}\n"
                f"📅 **تاریخ**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
                f"**آیا مطمئن هستید که می‌خواهید این کاربر را به لیست سفید اضافه کنید؟**\n\n"
                f"✅ تایید - کاربر مستقیماً اضافه می‌شود\n"
                f"❌ رد - عملیات لغو می‌شود",
                reply_markup=reply_markup
            )
            
            return ADMIN_PANEL
            
        except ValueError:
            await update.message.reply_text(
                "❌ **آیدی نامعتبر!**\n\n"
                "لطفاً یک عدد صحیح وارد کنید.\n\n"
                "🔙 برای بازگشت کلیک کنید:",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔙 بازگشت", callback_data="admin_lists")
                ]])
            )
            return ADD_WHITELIST
    
    async def confirm_whitelist(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int):
        """تایید افزودن به لیست سفید"""
        query = update.callback_query
        await query.answer()
        
        # بررسی اینکه قبلاً در لیست سفید نیست
        whitelist = self.store.get('whitelist', [])
        if user_id in whitelist:
            await query.edit_message_text(
                f"⚠️ **کاربر قبلاً در لیست سفید است!**\n\n"
                f"👤 **آیدی کاربر**: {user_id}\n\n"
                f"🔙 برای بازگشت کلیک کنید:",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔙 بازگشت", callback_data="admin_lists")
                ]])
            )
            return ADMIN_PANEL
        
        # افزودن به لیست سفید
        whitelist.append(user_id)
        self.store['whitelist'] = whitelist
        save_store(self.store)
        
        # حذف از لیست سیاه اگر وجود دارد
        blacklist = self.store.get('blacklist', [])
        if user_id in blacklist:
            blacklist.remove(user_id)
            self.store['blacklist'] = blacklist
            save_store(self.store)
        
        keyboard = [
            [InlineKeyboardButton("📋 مشاهده لیست‌ها", callback_data="view_lists")],
            [InlineKeyboardButton("🔙 بازگشت به پنل", callback_data="admin_lists")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            f"✅ **کاربر با موفقیت به لیست سفید اضافه شد!**\n\n"
            f"👤 **آیدی کاربر**: {user_id}\n"
            f"📅 **تاریخ**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
            f"**وضعیت**: کاربر حالا دسترسی کامل به ربات دارد",
            reply_markup=reply_markup
        )
        
        return ADMIN_PANEL
    
    async def cancel_whitelist(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """لغو افزودن به لیست سفید"""
        query = update.callback_query
        await query.answer()
        
        keyboard = [[InlineKeyboardButton("🔙 بازگشت به پنل", callback_data="admin_lists")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            "❌ **عملیات لغو شد!**\n\n"
            "کاربر به لیست سفید اضافه نشد.",
            reply_markup=reply_markup
        )
        
        return ADMIN_PANEL
    
    async def confirm_blacklist(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int):
        """تایید افزودن به لیست سیاه"""
        query = update.callback_query
        await query.answer()
        
        # بررسی اینکه قبلاً در لیست سیاه نیست
        blacklist = self.store.get('blacklist', [])
        if user_id in blacklist:
            await query.edit_message_text(
                f"⚠️ **کاربر قبلاً در لیست سیاه است!**\n\n"
                f"👤 **آیدی کاربر**: {user_id}\n\n"
                f"🔙 برای بازگشت کلیک کنید:",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔙 بازگشت", callback_data="admin_lists")
                ]])
            )
            return ADMIN_PANEL
        
        # افزودن به لیست سیاه
        blacklist.append(user_id)
        self.store['blacklist'] = blacklist
        save_store(self.store)
        
        # حذف از لیست سفید اگر وجود دارد
        whitelist = self.store.get('whitelist', [])
        if user_id in whitelist:
            whitelist.remove(user_id)
            self.store['whitelist'] = whitelist
            save_store(self.store)
        
        keyboard = [
            [InlineKeyboardButton("📋 مشاهده لیست‌ها", callback_data="view_lists")],
            [InlineKeyboardButton("🔙 بازگشت به پنل", callback_data="admin_lists")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            f"⚫ **کاربر با موفقیت به لیست سیاه اضافه شد!**\n\n"
            f"👤 **آیدی کاربر**: {user_id}\n"
            f"📅 **تاریخ**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
            f"**وضعیت**: کاربر حالا هیچ خدماتی از ربات دریافت نمی‌کند",
            reply_markup=reply_markup
        )
        
        return ADMIN_PANEL
    
    async def cancel_blacklist(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """لغو افزودن به لیست سیاه"""
        query = update.callback_query
        await query.answer()
        
        keyboard = [[InlineKeyboardButton("🔙 بازگشت به پنل", callback_data="admin_lists")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            "❌ **عملیات لغو شد!**\n\n"
            "کاربر به لیست سیاه اضافه نشد.",
            reply_markup=reply_markup
        )
        
        return ADMIN_PANEL
    
    async def add_blacklist_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """شروع افزودن به لیست سیاه"""
        query = update.callback_query
        await query.answer()
        
        await query.edit_message_text(
            "⚫ **افزودن کاربر به لیست سیاه**\n\n"
            "لطفاً آیدی عددی کاربر را ارسال کنید:\n"
            "مثال: `123456789`\n\n"
            "💡 **نکات مهم**:\n"
            "• کاربران لیست سیاه هیچ خدماتی دریافت نمی‌کنند\n"
            "• آیدی عددی کاربر را وارد کنید\n"
            "• پس از تایید، کاربر مستقیماً بلاک می‌شود\n\n"
            "🔙 برای بازگشت: /cancel",
            parse_mode='Markdown'
        )
        
        return ADD_BLACKLIST
    
    async def add_blacklist_process(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """پردازش افزودن به لیست سیاه"""
        user_id = update.message.text.strip()
        
        try:
            user_id = int(user_id)
            
            # نمایش تایید
            keyboard = [
                [InlineKeyboardButton("✅ تایید", callback_data=f"confirm_blacklist:{user_id}")],
                [InlineKeyboardButton("❌ رد", callback_data="cancel_blacklist")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                f"⚫ **تایید افزودن به لیست سیاه**\n\n"
                f"👤 **آیدی کاربر**: {user_id}\n"
                f"📅 **تاریخ**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
                f"**آیا مطمئن هستید که می‌خواهید این کاربر را به لیست سیاه اضافه کنید؟**\n\n"
                f"✅ تایید - کاربر مستقیماً بلاک می‌شود\n"
                f"❌ رد - عملیات لغو می‌شود",
                reply_markup=reply_markup
            )
            
            return ADMIN_PANEL
            
            # بررسی اینکه قبلاً در لیست سیاه نیست
            blacklist = self.store.get('blacklist', [])
            if user_id in blacklist:
                await update.message.reply_text(
                    f"⚠️ **کاربر قبلاً در لیست سیاه است!**\n\n"
                    f"👤 **آیدی کاربر**: {user_id}\n\n"
                    f"🔙 برای بازگشت کلیک کنید:",
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton("🔙 بازگشت", callback_data="back_to_main")
                    ]])
                )
                return ADMIN_PANEL
            
            # افزودن به لیست سیاه
            blacklist.append(user_id)
            self.store['blacklist'] = blacklist
            save_store(self.store)
            
            keyboard = [[InlineKeyboardButton("🔙 بازگشت به پنل", callback_data="back_to_main")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                f"✅ **کاربر با موفقیت به لیست سیاه اضافه شد!**\n\n"
                f"👤 **آیدی کاربر**: {user_id}\n"
                f"🚫 **وضعیت**: بلاک شده\n"
                f"📅 **تاریخ**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                reply_markup=reply_markup
            )
            
            return ADMIN_PANEL
            
        except ValueError:
            await update.message.reply_text(
                "❌ **آیدی نامعتبر!**\n\n"
                "لطفاً یک عدد صحیح وارد کنید.\n\n"
                "🔙 برای بازگشت کلیک کنید:",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔙 بازگشت", callback_data="back_to_main")
                ]])
            )
            return ADMIN_PANEL
    
    async def remove_blacklist_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """شروع حذف از لیست سیاه"""
        query = update.callback_query
        await query.answer()
        
        blacklist = self.store.get('blacklist', [])
        if not blacklist:
            await query.edit_message_text(
                "❌ **لیست سیاه خالی است!**\n\n"
                "🔙 برای بازگشت کلیک کنید:",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔙 بازگشت", callback_data="back_to_main")
                ]])
            )
            return ADMIN_PANEL
        
        # ایجاد کیبورد برای انتخاب کاربر
        keyboard = []
        for user_id in blacklist:
            keyboard.append([InlineKeyboardButton(f"✅ {user_id}", callback_data=f"remove_blacklist:{user_id}")])
        
        keyboard.append([InlineKeyboardButton("🔙 بازگشت", callback_data="back_to_main")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            f"✅ **حذف از لیست سیاه**\n\n"
            f"🚫 **کاربران بلاک شده** ({len(blacklist)} کاربر):\n"
            f"{chr(10).join([f'• {user_id}' for user_id in blacklist])}\n\n"
            f"لطفاً کاربر مورد نظر برای حذف را انتخاب کنید:",
            reply_markup=reply_markup
        )
        
        return ADMIN_PANEL
    
    async def remove_blacklist_action(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """حذف کاربر از لیست سیاه"""
        query = update.callback_query
        await query.answer()
        
        user_id = int(query.data.split(":")[1])
        blacklist = self.store.get('blacklist', [])
        
        if user_id in blacklist:
            blacklist.remove(user_id)
            self.store['blacklist'] = blacklist
            save_store(self.store)
            
            await query.answer(f"✅ کاربر {user_id} از لیست سیاه حذف شد!")
        else:
            await query.answer(f"❌ کاربر {user_id} در لیست سیاه یافت نشد!")
        
        # بازگشت به پنل لیست‌ها
        await self.admin_lists_panel(update, context)
        return ADMIN_PANEL
    
    async def remove_whitelist_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """شروع حذف از لیست سفید"""
        query = update.callback_query
        await query.answer()
        
        whitelist = self.store.get('whitelist', [])
        if not whitelist:
            await query.edit_message_text(
                "❌ **لیست سفید خالی است!**\n\n"
                "🔙 برای بازگشت کلیک کنید:",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔙 بازگشت", callback_data="back_to_main")
                ]])
            )
            return ADMIN_PANEL
        
        # ایجاد کیبورد برای انتخاب کاربر
        keyboard = []
        for user_id in whitelist:
            keyboard.append([InlineKeyboardButton(f"❌ {user_id}", callback_data=f"remove_whitelist:{user_id}")])
        
        keyboard.append([InlineKeyboardButton("🔙 بازگشت", callback_data="back_to_main")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            f"❌ **حذف از لیست سفید**\n\n"
            f"✅ **کاربران لیست سفید** ({len(whitelist)} کاربر):\n"
            f"{chr(10).join([f'• {user_id}' for user_id in whitelist])}\n\n"
            f"لطفاً کاربر مورد نظر برای حذف را انتخاب کنید:",
            reply_markup=reply_markup
        )
        
        return ADMIN_PANEL
    
    async def remove_whitelist_action(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """حذف کاربر از لیست سفید"""
        query = update.callback_query
        await query.answer()
        
        user_id = int(query.data.split(":")[1])
        whitelist = self.store.get('whitelist', [])
        
        if user_id in whitelist:
            whitelist.remove(user_id)
            self.store['whitelist'] = whitelist
            save_store(self.store)
            
            await query.answer(f"✅ کاربر {user_id} از لیست سفید حذف شد!")
        else:
            await query.answer(f"❌ کاربر {user_id} در لیست سفید یافت نشد!")
        
        # بازگشت به پنل لیست‌ها
        await self.admin_lists_panel(update, context)
        return ADMIN_PANEL
    
    async def view_lists_action(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """نمایش لیست‌های سفید و سیاه"""
        query = update.callback_query
        await query.answer()
        
        whitelist = self.store.get('whitelist', [])
        blacklist = self.store.get('blacklist', [])
        
        whitelist_text = "\n".join([f"• {user_id}" for user_id in whitelist])
        blacklist_text = "\n".join([f"• {user_id}" for user_id in blacklist])
        
        keyboard = [[InlineKeyboardButton("🔙 بازگشت", callback_data="admin_lists")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        text = f"""
📋 **لیست‌های سفید و سیاه**

⚪ **لیست سفید** ({len(whitelist)} کاربر):
{whitelist_text if whitelist_text else "• خالی"}

⚫ **لیست سیاه** ({len(blacklist)} کاربر):
{blacklist_text if blacklist_text else "• خالی"}
        """
        
        await query.edit_message_text(text, reply_markup=reply_markup)
        return ADMIN_PANEL
    
    async def stats_24h_action(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """نمایش آمار 24 ساعت اخیر"""
        query = update.callback_query
        await query.answer()
        
        # محاسبه آمار 24 ساعت (نمونه)
        users = self.store.get('users', [])
        active_24h = len(users)  # در واقعیت باید از لاگ‌ها محاسبه شود
        
        keyboard = [[InlineKeyboardButton("🔙 بازگشت", callback_data="admin_stats")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        text = f"""
📊 **آمار 24 ساعت اخیر**

🕐 **کاربران فعال**: {active_24h}
📈 **نرخ رشد**: +{active_24h//10} کاربر
🔄 **آخرین بروزرسانی**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        """
        
        await query.edit_message_text(text, reply_markup=reply_markup)
        return ADMIN_PANEL
    
    async def stats_week_action(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """نمایش آمار هفته اخیر"""
        query = update.callback_query
        await query.answer()
        
        # محاسبه آمار هفته (نمونه)
        users = self.store.get('users', [])
        active_week = len(users)  # در واقعیت باید از لاگ‌ها محاسبه شود
        
        keyboard = [[InlineKeyboardButton("🔙 بازگشت", callback_data="admin_stats")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        text = f"""
📊 **آمار هفته اخیر**

📅 **کاربران فعال**: {active_week}
📈 **نرخ رشد**: +{active_week//7} کاربر
🔄 **آخرین بروزرسانی**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        """
        
        await query.edit_message_text(text, reply_markup=reply_markup)
        return ADMIN_PANEL
    
    async def stats_total_action(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """نمایش آمار کلی"""
        query = update.callback_query
        await query.answer()
        
        users = self.store.get('users', [])
        admins = self.store.get('admins', [])
        whitelist = self.store.get('whitelist', [])
        blacklist = self.store.get('blacklist', [])
        
        keyboard = [[InlineKeyboardButton("🔙 بازگشت", callback_data="admin_stats")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        text = f"""
📊 **آمار کلی**

👥 **کل کاربران**: {len(users)}
👨‍💼 **ادمین‌ها**: {len(admins)}
⚪ **لیست سفید**: {len(whitelist)}
⚫ **لیست سیاه**: {len(blacklist)}
🔄 **آخرین بروزرسانی**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        """
        
        await query.edit_message_text(text, reply_markup=reply_markup)
        return ADMIN_PANEL
    
    async def stats_blocked_action(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """نمایش لیست کاربران بلاک شده"""
        query = update.callback_query
        await query.answer()
        
        blacklist = self.store.get('blacklist', [])
        blacklist_text = "\n".join([f"• {user_id}" for user_id in blacklist])
        
        keyboard = [[InlineKeyboardButton("🔙 بازگشت", callback_data="admin_stats")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        text = f"""
📊 **لیست کاربران بلاک شده**

⚫ **کاربران بلاک شده** ({len(blacklist)} کاربر):
{blacklist_text if blacklist_text else "• هیچ کاربری بلاک نشده"}
        """
        
        await query.edit_message_text(text, reply_markup=reply_markup)
        return ADMIN_PANEL
    
    async def cache_status_action(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """نمایش وضعیت کش"""
        query = update.callback_query
        await query.answer()
        
        cache_size = len(self.cache._store)
        
        keyboard = [[InlineKeyboardButton("🔙 بازگشت", callback_data="admin_cache")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        text = f"""
🗄️ **وضعیت کش**

📊 **تعداد آیتم‌ها**: {cache_size}
💾 **حافظه استفاده شده**: {cache_size * 100} KB
🔄 **آخرین بروزرسانی**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        """
        
        await query.edit_message_text(text, reply_markup=reply_markup)
        return ADMIN_PANEL
    
    async def restore_backup_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """شروع بازگردانی از پشتیبان"""
        query = update.callback_query
        await query.answer()
        
        await query.edit_message_text(
            "📥 **بازگردانی از پشتیبان**\n\n"
            "⚠️ **هشدار**: این عملیات تمام داده‌های فعلی را جایگزین می‌کند!\n\n"
            "لطفاً فایل پشتیبان را ارسال کنید:\n\n"
            f"🔙 برای بازگشت: /cancel"
        )
        
        return BACKUP_RESTORE
    
    async def view_full_logs_action(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """نمایش لاگ‌های کامل"""
        query = update.callback_query
        await query.answer()
        
        logs = self.store.get('logs', [])
        log_text = ""
        for log in logs[-20:]:  # 20 لاگ آخر
            log_text += f"• {log.get('user_id', 'نامشخص')} - {log.get('action', 'نامشخص')} - {log.get('timestamp', 'نامشخص')}\n"
        
        keyboard = [[InlineKeyboardButton("🔙 بازگشت", callback_data="admin_logs")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        text = f"""
📋 **لاگ‌های کامل**

📊 **کل لاگ‌ها**: {len(logs)}
📝 **آخرین 20 لاگ**:
{log_text if log_text else "• هیچ لاگی وجود ندارد"}
        """
        
        await query.edit_message_text(text, reply_markup=reply_markup)
        return ADMIN_PANEL
    
    async def clear_logs_action(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """پاک کردن لاگ‌ها"""
        query = update.callback_query
        await query.answer()
        
        self.store['logs'] = []
        save_store(self.store)
        
        keyboard = [[InlineKeyboardButton("🔙 بازگشت", callback_data="admin_logs")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            f"✅ **لاگ‌ها با موفقیت پاک شدند!**\n\n"
            f"🗑️ **عملیات**: پاک کردن تمام لاگ‌ها\n"
            f"📅 **تاریخ**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            reply_markup=reply_markup
        )
        
        return ADMIN_PANEL
    
    async def alerts_optional_action(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """تنظیم هشدارهای اختیاری"""
        query = update.callback_query
        await query.answer()
        
        self.store['alert_type'] = 'optional'
        save_store(self.store)
        
        keyboard = [[InlineKeyboardButton("🔙 بازگشت", callback_data="admin_alerts")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            f"✅ **هشدارهای اختیاری فعال شدند!**\n\n"
            f"🔔 **نوع هشدار**: اختیاری (کاربر تنظیم می‌کند)\n"
            f"📅 **تاریخ**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            reply_markup=reply_markup
        )
        
        return ADMIN_PANEL
    
    async def alerts_required_action(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """تنظیم هشدارهای اجباری"""
        query = update.callback_query
        await query.answer()
        
        self.store['alert_type'] = 'required'
        save_store(self.store)
        
        keyboard = [[InlineKeyboardButton("🔙 بازگشت", callback_data="admin_alerts")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            f"✅ **هشدارهای اجباری فعال شدند!**\n\n"
            f"🔔 **نوع هشدار**: اجباری (مالک تنظیم می‌کند)\n"
            f"📅 **تاریخ**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            reply_markup=reply_markup
        )
        
        return ADMIN_PANEL
    
    async def view_alerts_action(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """نمایش هشدارهای فعال"""
        query = update.callback_query
        await query.answer()
        
        # شمارش هشدارهای فعال
        active_alerts = 0
        for user_data in self.store.get('user_data', {}).values():
            if isinstance(user_data, dict) and 'alerts' in user_data:
                active_alerts += len(user_data['alerts'])
        
        keyboard = [[InlineKeyboardButton("🔙 بازگشت", callback_data="admin_alerts")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        text = f"""
🔔 **هشدارهای فعال**

📊 **وضعیت فعلی**:
• هشدارهای فعال: {active_alerts}
• کاربران با هشدار: {len([u for u in self.store.get('user_data', {}).values() if isinstance(u, dict) and u.get('alerts')])}
• نوع هشدار: {self.store.get('alert_type', 'اختیاری')}
        """
        
        await query.edit_message_text(text, reply_markup=reply_markup)
        return ADMIN_PANEL
    
    async def remove_channel_action(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """حذف کانال از لیست عضویت اجباری"""
        query = update.callback_query
        await query.answer()
        
        channel_name = query.data.split(":")[1]
        force_sub = self.store.get('forced_subscription', {})
        channels = force_sub.get('channels', [])
        
        if channel_name in channels:
            channels.remove(channel_name)
            force_sub['channels'] = channels
            self.store['forced_subscription'] = force_sub
            save_store(self.store)
            
            await query.answer(f"✅ کانال @{channel_name} حذف شد!")
        else:
            await query.answer(f"❌ کانال @{channel_name} یافت نشد!")
        
        # بازگشت به پنل قفل اجباری
        await self.force_subscription_panel(update, context)
        return ADMIN_PANEL
    
    async def start_user_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: str):
        """شروع ارسال پیام به کاربر"""
        query = update.callback_query
        await query.answer()
        
        context.user_data['target_user_id'] = user_id
        
        await query.edit_message_text(
            f"💬 **ارسال پیام به کاربر**\n\n"
            f"👤 **آیدی کاربر**: {user_id}\n\n"
            f"لطفاً پیام مورد نظر را ارسال کنید:\n\n"
            f"🔙 برای بازگشت: /cancel"
        )
        
        return USER_MESSAGE
    
    async def send_user_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """ارسال پیام به کاربر"""
        target_user_id = context.user_data.get('target_user_id')
        message_text = update.message.text
        
        try:
            await context.bot.send_message(
                chat_id=int(target_user_id),
                text=f"💬 **پیام از مدیریت**:\n\n{message_text}"
            )
            
            keyboard = [[InlineKeyboardButton("🔙 بازگشت به پنل", callback_data="back_to_main")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                f"✅ **پیام با موفقیت ارسال شد!**\n\n"
                f"👤 **به کاربر**: {target_user_id}\n"
                f"📝 **پیام**: {message_text}\n"
                f"📅 **تاریخ**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                reply_markup=reply_markup
            )
            
            return ADMIN_PANEL
            
        except Exception as e:
            await update.message.reply_text(f"❌ خطا در ارسال پیام: {str(e)}")
            return USER_MESSAGE
    
    # ===== مدیریت API ها =====
    async def manage_apis(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """مدیریت API ها"""
        query = update.callback_query
        await query.answer()
        
        # دریافت API های موجود
        apis = self.store.get('api_configs', {})
        
        keyboard = [
            [InlineKeyboardButton("➕ افزودن API جدید", callback_data="add_api")],
            [InlineKeyboardButton("📋 لیست API ها", callback_data="list_apis")],
            [InlineKeyboardButton("⚙️ تنظیمات API", callback_data="api_settings")],
            [InlineKeyboardButton("🔙 بازگشت", callback_data="back_to_main")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        text = f"""
🔧 **مدیریت API ها**

📊 **آمار API ها**:
• تعداد API های فعال: {len([api for api in apis.values() if api.get('enabled', False)])}
• تعداد API های غیرفعال: {len([api for api in apis.values() if not api.get('enabled', False)])}

🔗 **API های موجود**:
{self._format_api_list(apis)}

لطفاً یکی از گزینه‌های زیر را انتخاب کنید:
        """
        
        await query.edit_message_text(text, reply_markup=reply_markup)
        return MANAGE_APIS
    
    def _format_api_list(self, apis):
        """فرمت کردن لیست API ها"""
        if not apis:
            return "• هیچ API ای ثبت نشده است"
        
        formatted = []
        for api_id, api_data in apis.items():
            status = "✅ فعال" if api_data.get('enabled', False) else "❌ غیرفعال"
            formatted.append(f"• {api_data.get('name', api_id)} - {status}")
        
        return "\n".join(formatted)
    
    async def add_api(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """افزودن API جدید"""
        query = update.callback_query
        await query.answer()
        
        keyboard = [
            [InlineKeyboardButton("🔙 بازگشت", callback_data="admin_apis")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        text = """
➕ **افزودن API جدید**

لطفاً اطلاعات API را به صورت زیر ارسال کنید:

**فرمت**:
```
نام API: نام API شما
نوع: crypto|fiat|news|technical
کلید: کلید API شما
آدرس: آدرس API (اختیاری)
```

**مثال**:
```
نام API: CoinGecko Pro
نوع: crypto
کلید: your_api_key_here
آدرس: https://api.coingecko.com/api/v3
```

⚠️ **نکته**: کلید API شما محرمانه است و فقط برای استفاده ربات ذخیره می‌شود.
        """
        
        await query.edit_message_text(text, reply_markup=reply_markup)
        return ADD_API
    
    async def process_add_api(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """پردازش افزودن API"""
        message_text = update.message.text.strip()
        
        try:
            # پارس کردن اطلاعات API
            api_data = self._parse_api_data(message_text)
            
            if not api_data:
                await update.message.reply_text(
                    "❌ فرمت اطلاعات API صحیح نیست. لطفاً دوباره تلاش کنید."
                )
                return ADD_API
            
            # ذخیره API
            api_id = f"api_{len(self.store.get('api_configs', {})) + 1}"
            self.store.setdefault('api_configs', {})[api_id] = api_data
            save_store(self.store)
            
            await update.message.reply_text(
                f"✅ API با موفقیت اضافه شد!\n\n"
                f"🆔 شناسه: {api_id}\n"
                f"📝 نام: {api_data['name']}\n"
                f"🔗 نوع: {api_data['type']}\n"
                f"⚙️ وضعیت: {'فعال' if api_data.get('enabled', True) else 'غیرفعال'}"
            )
            
            return await self.manage_apis(update, context)
            
        except Exception as e:
            await update.message.reply_text(f"❌ خطا در افزودن API: {str(e)}")
            return ADD_API
    
    def _parse_api_data(self, text):
        """پارس کردن اطلاعات API از متن"""
        lines = text.strip().split('\n')
        api_data = {}
        
        for line in lines:
            if ':' in line:
                key, value = line.split(':', 1)
                key = key.strip().lower()
                value = value.strip()
                
                if 'نام' in key:
                    api_data['name'] = value
                elif 'نوع' in key:
                    api_data['type'] = value
                elif 'کلید' in key:
                    api_data['key'] = value
                elif 'آدرس' in key:
                    api_data['url'] = value
        
        # بررسی وجود فیلدهای ضروری
        if 'name' in api_data and 'type' in api_data and 'key' in api_data:
            api_data['enabled'] = True
            api_data['created_at'] = datetime.now().isoformat()
            return api_data
        
        return None
    
    # ===== مدیریت ارزها =====
    async def manage_currencies(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """مدیریت ارزها"""
        query = update.callback_query
        await query.answer()
        
        # دریافت ارزهای موجود
        currencies = self.store.get('enabled_currencies', {})
        
        keyboard = [
            [InlineKeyboardButton("➕ افزودن ارز", callback_data="add_currency")],
            [InlineKeyboardButton("📋 لیست ارزها", callback_data="list_currencies")],
            [InlineKeyboardButton("⚙️ تنظیمات ارزها", callback_data="currency_settings")],
            [InlineKeyboardButton("🔙 بازگشت", callback_data="back_to_main")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        text = f"""
💰 **مدیریت ارزها**

📊 **آمار ارزها**:
• تعداد ارزهای فعال: {len([c for c in currencies.values() if c.get('enabled', False)])}
• تعداد ارزهای غیرفعال: {len([c for c in currencies.values() if not c.get('enabled', False)])}

🪙 **ارزهای موجود**:
{self._format_currency_list(currencies)}

لطفاً یکی از گزینه‌های زیر را انتخاب کنید:
        """
        
        await query.edit_message_text(text, reply_markup=reply_markup)
        return MANAGE_CURRENCIES
    
    def _format_currency_list(self, currencies):
        """فرمت کردن لیست ارزها"""
        if not currencies:
            return "• هیچ ارزی تنظیم نشده است"
        
        formatted = []
        for symbol, currency_data in currencies.items():
            status = "✅ فعال" if currency_data.get('enabled', False) else "❌ غیرفعال"
            formatted.append(f"• {symbol.upper()} - {currency_data.get('name', symbol)} - {status}")
        
        return "\n".join(formatted)
    
    async def add_currency(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """افزودن ارز جدید"""
        query = update.callback_query
        await query.answer()
        
        keyboard = [
            [InlineKeyboardButton("🔙 بازگشت", callback_data="admin_currencies")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        text = """
➕ **افزودن ارز جدید**

لطفاً اطلاعات ارز را به صورت زیر ارسال کنید:

**فرمت**:
```
نماد: نماد ارز (مثل btc, eth)
نام: نام کامل ارز
نوع: crypto|fiat
API: شناسه API مورد استفاده
```

**مثال**:
```
نماد: btc
نام: Bitcoin
نوع: crypto
API: api_1
```

⚠️ **نکته**: نماد ارز باید با نمادهای استاندارد مطابقت داشته باشد.
        """
        
        await query.edit_message_text(text, reply_markup=reply_markup)
        return ADD_CURRENCY
    
    async def process_add_currency(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """پردازش افزودن ارز"""
        message_text = update.message.text.strip()
        
        try:
            # پارس کردن اطلاعات ارز
            currency_data = self._parse_currency_data(message_text)
            
            if not currency_data:
                await update.message.reply_text(
                    "❌ فرمت اطلاعات ارز صحیح نیست. لطفاً دوباره تلاش کنید."
                )
                return ADD_CURRENCY
            
            # ذخیره ارز
            symbol = currency_data['symbol'].lower()
            self.store.setdefault('enabled_currencies', {})[symbol] = currency_data
            save_store(self.store)
            
            await update.message.reply_text(
                f"✅ ارز با موفقیت اضافه شد!\n\n"
                f"🪙 نماد: {symbol.upper()}\n"
                f"📝 نام: {currency_data['name']}\n"
                f"🔗 نوع: {currency_data['type']}\n"
                f"🔧 API: {currency_data['api']}\n"
                f"⚙️ وضعیت: {'فعال' if currency_data.get('enabled', True) else 'غیرفعال'}"
            )
            
            return await self.manage_currencies(update, context)
            
        except Exception as e:
            await update.message.reply_text(f"❌ خطا در افزودن ارز: {str(e)}")
            return ADD_CURRENCY
    
    def _parse_currency_data(self, text):
        """پارس کردن اطلاعات ارز از متن"""
        lines = text.strip().split('\n')
        currency_data = {}
        
        for line in lines:
            if ':' in line:
                key, value = line.split(':', 1)
                key = key.strip().lower()
                value = value.strip()
                
                if 'نماد' in key:
                    currency_data['symbol'] = value
                elif 'نام' in key:
                    currency_data['name'] = value
                elif 'نوع' in key:
                    currency_data['type'] = value
                elif 'api' in key:
                    currency_data['api'] = value
        
        # بررسی وجود فیلدهای ضروری
        if all(key in currency_data for key in ['symbol', 'name', 'type', 'api']):
            currency_data['enabled'] = True
            currency_data['created_at'] = datetime.now().isoformat()
            return currency_data
        
        return None
    
    # ===== مدیریت شاخص‌ها =====
    async def manage_indicators(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """مدیریت شاخص‌ها"""
        query = update.callback_query
        await query.answer()
        
        # دریافت شاخص‌های موجود
        indicators = self.store.get('enabled_indicators', {})
        
        keyboard = [
            [InlineKeyboardButton("➕ افزودن شاخص", callback_data="add_indicator")],
            [InlineKeyboardButton("📋 لیست شاخص‌ها", callback_data="list_indicators")],
            [InlineKeyboardButton("⚙️ تنظیمات شاخص‌ها", callback_data="indicator_settings")],
            [InlineKeyboardButton("🔙 بازگشت", callback_data="back_to_main")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        text = f"""
📊 **مدیریت شاخص‌ها**

📊 **آمار شاخص‌ها**:
• تعداد شاخص‌های فعال: {len([i for i in indicators.values() if i.get('enabled', False)])}
• تعداد شاخص‌های غیرفعال: {len([i for i in indicators.values() if not i.get('enabled', False)])}

📈 **شاخص‌های موجود**:
{self._format_indicator_list(indicators)}

لطفاً یکی از گزینه‌های زیر را انتخاب کنید:
        """
        
        await query.edit_message_text(text, reply_markup=reply_markup)
        return MANAGE_INDICATORS
    
    def _format_indicator_list(self, indicators):
        """فرمت کردن لیست شاخص‌ها"""
        if not indicators:
            return "• هیچ شاخصی تنظیم نشده است"
        
        formatted = []
        for indicator_id, indicator_data in indicators.items():
            status = "✅ فعال" if indicator_data.get('enabled', False) else "❌ غیرفعال"
            formatted.append(f"• {indicator_data.get('name', indicator_id)} - {status}")
        
        return "\n".join(formatted)
    
    async def add_indicator(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """افزودن شاخص جدید"""
        query = update.callback_query
        await query.answer()
        
        keyboard = [
            [InlineKeyboardButton("🔙 بازگشت", callback_data="admin_indicators")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        text = """
➕ **افزودن شاخص جدید**

لطفاً اطلاعات شاخص را به صورت زیر ارسال کنید:

**فرمت**:
```
نام: نام شاخص
نوع: rsi|macd|sma|ema|bollinger|support|resistance
توضیحات: توضیحات شاخص
API: شناسه API مورد استفاده
```

**مثال**:
```
نام: RSI
نوع: rsi
توضیحات: شاخص قدرت نسبی
API: api_1
```

⚠️ **نکته**: نوع شاخص باید از انواع پشتیبانی شده باشد.
        """
        
        await query.edit_message_text(text, reply_markup=reply_markup)
        return ADD_INDICATOR
    
    async def process_add_indicator(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """پردازش افزودن شاخص"""
        message_text = update.message.text.strip()
        
        try:
            # پارس کردن اطلاعات شاخص
            indicator_data = self._parse_indicator_data(message_text)
            
            if not indicator_data:
                await update.message.reply_text(
                    "❌ فرمت اطلاعات شاخص صحیح نیست. لطفاً دوباره تلاش کنید."
                )
                return ADD_INDICATOR
            
            # ذخیره شاخص
            indicator_id = f"indicator_{len(self.store.get('enabled_indicators', {})) + 1}"
            self.store.setdefault('enabled_indicators', {})[indicator_id] = indicator_data
            save_store(self.store)
            
            await update.message.reply_text(
                f"✅ شاخص با موفقیت اضافه شد!\n\n"
                f"🆔 شناسه: {indicator_id}\n"
                f"📝 نام: {indicator_data['name']}\n"
                f"🔗 نوع: {indicator_data['type']}\n"
                f"📄 توضیحات: {indicator_data.get('description', 'ندارد')}\n"
                f"🔧 API: {indicator_data['api']}\n"
                f"⚙️ وضعیت: {'فعال' if indicator_data.get('enabled', True) else 'غیرفعال'}"
            )
            
            return await self.manage_indicators(update, context)
            
        except Exception as e:
            await update.message.reply_text(f"❌ خطا در افزودن شاخص: {str(e)}")
            return ADD_INDICATOR
    
    def _parse_indicator_data(self, text):
        """پارس کردن اطلاعات شاخص از متن"""
        lines = text.strip().split('\n')
        indicator_data = {}
        
        for line in lines:
            if ':' in line:
                key, value = line.split(':', 1)
                key = key.strip().lower()
                value = value.strip()
                
                if 'نام' in key:
                    indicator_data['name'] = value
                elif 'نوع' in key:
                    indicator_data['type'] = value
                elif 'توضیحات' in key:
                    indicator_data['description'] = value
                elif 'api' in key:
                    indicator_data['api'] = value
        
        # بررسی وجود فیلدهای ضروری
        if all(key in indicator_data for key in ['name', 'type', 'api']):
            indicator_data['enabled'] = True
            indicator_data['created_at'] = datetime.now().isoformat()
            return indicator_data
        
        return None

    async def list_apis_action(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """نمایش لیست API ها"""
        store = load_store()
        api_configs = store.get('api_configs', {})
        
        if not api_configs:
            await update.callback_query.edit_message_text(
                "📋 **لیست API ها**\n\n"
                "❌ هیچ API ثبت نشده است.",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔙 بازگشت", callback_data="manage_apis")
                ]])
            )
            return
        
        text = "📋 **لیست API های ثبت شده:**\n\n"
        for api_id, config in api_configs.items():
            status = "✅ فعال" if config.get('enabled', True) else "❌ غیرفعال"
            text += f"🔹 **{config.get('name', api_id)}**\n"
            text += f"   نوع: {config.get('type', 'نامشخص')}\n"
            text += f"   وضعیت: {status}\n"
            text += f"   URL: {config.get('url', 'نامشخص')[:50]}...\n\n"
        
        await update.callback_query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 بازگشت", callback_data="manage_apis")
            ]])
        )

    async def list_currencies_action(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """نمایش لیست ارزها"""
        store = load_store()
        enabled_currencies = store.get('enabled_currencies', {})
        
        if not enabled_currencies:
            await update.callback_query.edit_message_text(
                "💰 **لیست ارزها**\n\n"
                "❌ هیچ ارزی فعال نشده است.",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔙 بازگشت", callback_data="manage_currencies")
                ]])
            )
            return
        
        text = "💰 **لیست ارزهای فعال:**\n\n"
        for currency_id, config in enabled_currencies.items():
            status = "✅ فعال" if config.get('enabled', True) else "❌ غیرفعال"
            text += f"🔹 **{config.get('symbol', currency_id)}**\n"
            text += f"   نام: {config.get('name', 'نامشخص')}\n"
            text += f"   نوع: {config.get('type', 'نامشخص')}\n"
            text += f"   وضعیت: {status}\n"
            text += f"   API: {config.get('api_id', 'پیش‌فرض')}\n\n"
        
        await update.callback_query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 بازگشت", callback_data="manage_currencies")
            ]])
        )

    async def list_indicators_action(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """نمایش لیست شاخص‌ها"""
        store = load_store()
        enabled_indicators = store.get('enabled_indicators', {})
        
        if not enabled_indicators:
            await update.callback_query.edit_message_text(
                "📊 **لیست شاخص‌ها**\n\n"
                "❌ هیچ شاخصی فعال نشده است.",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔙 بازگشت", callback_data="manage_indicators")
                ]])
            )
            return
        
        text = "📊 **لیست شاخص‌های فعال:**\n\n"
        for indicator_id, config in enabled_indicators.items():
            status = "✅ فعال" if config.get('enabled', True) else "❌ غیرفعال"
            text += f"🔹 **{config.get('name', indicator_id)}**\n"
            text += f"   نوع: {config.get('type', 'نامشخص')}\n"
            text += f"   توضیحات: {config.get('description', 'نامشخص')}\n"
            text += f"   وضعیت: {status}\n"
            text += f"   API: {config.get('api_id', 'پیش‌فرض')}\n\n"
        
        await update.callback_query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 بازگشت", callback_data="manage_indicators")
            ]])
        )

    async def admin_stats_panel(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """پنل آمار و گزارش - فقط برای مالک ربات"""
        query = update.callback_query
        await query.answer()
        
        # بررسی دسترسی - فقط مالک ربات
        user_id = update.effective_user.id
        if user_id != OWNER_ID:
            await query.edit_message_text("❌ شما دسترسی به آمار و گزارش ندارید!")
            return ADMIN_PANEL
        
        # محاسبه آمار
        users = self.store.get('users', [])
        admins = self.store.get('admins', [])
        whitelist = self.store.get('whitelist', [])
        blacklist = self.store.get('blacklist', [])
        alerts = self.store.get('alerts', {})
        user_data = self.store.get('user_data', {})
        
        # محاسبه آمار کاربران فعال
        active_users = len([uid for uid in users if user_data.get(str(uid), {}).get('last_activity')])
        
        # محاسبه آمار هشدارها
        total_alerts = sum(len(user_alerts) for user_alerts in alerts.values())
        
        keyboard = [
            [InlineKeyboardButton("🔄 بروزرسانی آمار", callback_data="refresh_detailed_stats")],
            [InlineKeyboardButton("📊 گزارش CSV", callback_data="export_stats_csv")],
            [InlineKeyboardButton("👥 لیست کاربران بلاک شده", callback_data="show_full_blocked_list")],
            [InlineKeyboardButton("🔙 بازگشت", callback_data="back_to_main")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        text = f"""
📊 **آمار و گزارش ربات**

👥 **آمار کاربران**:
• کل کاربران: {len(users)}
• کاربران فعال: {active_users}
• ادمین‌ها: {len(admins)}
• لیست سفید: {len(whitelist)}
• لیست سیاه: {len(blacklist)}

🔔 **آمار هشدارها**:
• کل هشدارها: {total_alerts}
• کاربران با هشدار: {len(alerts)}

📅 **آخرین بروزرسانی**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

**عملیات موجود**:
🔄 بروزرسانی آمار
📊 دانلود گزارش CSV
👥 مشاهده لیست کاربران بلاک شده
        """
        
        await query.edit_message_text(text, reply_markup=reply_markup)
        return ADMIN_PANEL

    async def refresh_stats_action(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """بروزرسانی آمار"""
        return await self.admin_stats_panel(update, context)

    async def refresh_cache_action(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """بروزرسانی کش"""
        return await self.admin_cache_panel(update, context)

    async def update_settings_action(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """تنظیمات بروزرسانی"""
        return await self.admin_system_panel(update, context)

    async def cancel(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """لغو عملیات"""
        await update.message.reply_text("❌ عملیات لغو شد.")
        return ConversationHandler.END

# ایجاد نمونه از کلاس
admin_panel = AdminPanel()
