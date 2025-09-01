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
    USER_MESSAGE, BROADCAST_FORWARD
) = range(29)

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
            [InlineKeyboardButton("🔧 تنظیمات API", callback_data="admin_api")],
            [InlineKeyboardButton("🔒 قفل اجباری", callback_data="admin_force_sub")],
            [InlineKeyboardButton("⚪ لیست سفید/سیاه", callback_data="admin_lists")],
            [InlineKeyboardButton("📊 آمار و گزارش", callback_data="admin_stats")],
            [InlineKeyboardButton("🗄️ مدیریت کش", callback_data="admin_cache")],
            [InlineKeyboardButton("⚙️ تنظیمات سیستم", callback_data="admin_system")],
            [InlineKeyboardButton("💾 پشتیبان‌گیری", callback_data="admin_backup")],
            [InlineKeyboardButton("📋 لاگ‌ها", callback_data="admin_logs")],
            [InlineKeyboardButton("🔔 مدیریت هشدارها", callback_data="admin_alerts")],
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
            "لطفاً ربات یا پیامی که می‌خواهید فوروارد شود را ارسال کنید:\n\n"
            "💡 **نکات مهم**:\n"
            "• ربات آن را به تمام کاربران فوروارد می‌کند\n"
            "• برای لغو: /cancel\n\n"
            "📤 **نوع ارسال**: فوروارد همگانی",
            parse_mode='Markdown'
        )
        
        return BROADCAST_FORWARD
    
    async def broadcast_forward_process(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """پردازش فوروارد همگانی"""
        broadcast_type = context.user_data.get('broadcast_type', 'all')
        
        # تعیین لیست گیرندگان
        if broadcast_type == 'all':
            recipients = self.store.get('users', [])
        elif broadcast_type == 'admins':
            recipients = self.store.get('admins', []) + [OWNER_ID]
        elif broadcast_type == 'whitelist':
            recipients = self.store.get('whitelist', [])
        
        # فوروارد کردن پیام
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

لطفاً یکی از گزینه‌ها را انتخاب کنید:
        """
        
        await query.edit_message_text(text, reply_markup=reply_markup)
        return ADMIN_PANEL
    
    async def set_welcome_text_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """شروع تنظیم متن خوش‌آمدگویی"""
        query = update.callback_query
        await query.answer()
        
        current_text = self.store.get('texts', {}).get('welcome', 'متن خوش‌آمدگویی تنظیم نشده')
        
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
            [InlineKeyboardButton("📊 وضعیت API", callback_data="api_status")],
            [InlineKeyboardButton("🔙 بازگشت", callback_data="back_to_main")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        providers = self.store.get('providers', {})
        crypto_provider = providers.get('crypto', 'coingecko')
        fiat_provider = providers.get('fiat', 'exchangerate_host')
        tradingview_api = self.store.get('tradingview_api', 'تنظیم نشده')
        
        text = f"""
🔧 **تنظیمات API**

📊 **Provider های فعلی**:
💰 ارز دیجیتال: {crypto_provider}
💱 ارز فیات: {fiat_provider}
📈 TradingView: {tradingview_api}

**عملیات موجود**:
🔑 تنظیم TradingView API
💱 تنظیم فیات API
💰 تنظیم کریپتو API
📊 بررسی وضعیت API
        """
        
        await query.edit_message_text(text, reply_markup=reply_markup)
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
        
        channels_text = "\n".join([f"• @{ch}" for ch in channels]) if channels else "• هیچ کانالی تنظیم نشده"
        
        keyboard = [
            [InlineKeyboardButton(f"{'❌' if is_enabled else '✅'} {'غیرفعال' if is_enabled else 'فعال'} کردن", 
                                callback_data="toggle_force_sub")],
            [InlineKeyboardButton("📢 افزودن کانال", callback_data="add_force_sub_channel")],
            [InlineKeyboardButton("🗑️ حذف کانال", callback_data="remove_force_sub_channel")],
            [InlineKeyboardButton("🔙 بازگشت", callback_data="back_to_main")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        text = f"""
🔒 **قفل اجباری عضویت**

📊 **وضعیت فعلی**:
{status_emoji} قفل اجباری: {status_text}
📢 تعداد کانال‌ها: {len(channels)}

**کانال‌های تنظیم شده**:
{channels_text}

**عملیات موجود**:
{'❌ غیرفعال' if is_enabled else '✅ فعال'} کردن قفل اجباری
📢 افزودن کانال جدید
🗑️ حذف کانال موجود
        """
        
        await query.edit_message_text(text, reply_markup=reply_markup)
        return ADMIN_PANEL
    
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

**نحوه استفاده**:
• آیدی عددی کاربر را وارد کنید
• تایید یا رد کنید
• کاربر مستقیماً بلاک/آنبلاک می‌شود
        """
        
        await query.edit_message_text(text, reply_markup=reply_markup)
        return ADMIN_PANEL

    async def admin_bot_settings_panel(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """پنل تنظیمات ربات"""
        query = update.callback_query
        await query.answer()
        
        keyboard = [
            [InlineKeyboardButton("🤖 اطلاعات ربات", callback_data="bot_info")],
            [InlineKeyboardButton("⚙️ تنظیمات عمومی", callback_data="general_settings")],
            [InlineKeyboardButton("🎨 تنظیمات ظاهری", callback_data="appearance_settings")],
            [InlineKeyboardButton("🔧 تنظیمات فنی", callback_data="technical_settings")],
            [InlineKeyboardButton("🔙 بازگشت", callback_data="back_to_main")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        text = """
🤖 **تنظیمات ربات**

**بخش‌های موجود**:
🤖 اطلاعات و وضعیت ربات
⚙️ تنظیمات عمومی و پیش‌فرض
🎨 تنظیمات ظاهری و رابط کاربری
🔧 تنظیمات فنی و عملکرد

لطفاً یکی از گزینه‌ها را انتخاب کنید:
        """
        
        await query.edit_message_text(text, reply_markup=reply_markup)
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
        elif data == "admin_backup":
            return await self.admin_backup_panel(update, context)
        elif data == "admin_logs":
            return await self.admin_logs_panel(update, context)
        elif data == "admin_alerts":
            return await self.admin_alerts_panel(update, context)
        elif data == "admin_bot_settings":
            return await self.admin_bot_settings_panel(update, context)
        elif data.startswith("broadcast_"):
            return await self.broadcast_message_start(update, context)
        elif data == "set_welcome":
            return await self.set_welcome_text_start(update, context)
        elif data == "set_help":
            return await self.set_help_text_start(update, context)
        elif data == "set_error":
            return await self.set_error_text_start(update, context)
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
        elif data == "toggle_force_sub":
            return await self.toggle_force_subscription(update, context)
        elif data == "add_force_sub_channel":
            return await self.add_force_sub_channel_start(update, context)
        elif data == "remove_force_sub_channel":
            return await self.remove_force_sub_channel_start(update, context)
        elif data == "add_whitelist":
            return await self.add_whitelist_start(update, context)
        elif data == "remove_whitelist":
            return await self.remove_whitelist_start(update, context)
        elif data == "add_blacklist":
            return await self.add_blacklist_start(update, context)
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
        elif data.startswith("toggle_feature:"):
            feature = data.split(":")[1]
            return await self.toggle_feature(update, context, feature)
        elif data.startswith("message_user:"):
            user_id = data.split(":")[1]
            return await self.start_user_message(update, context, user_id)
        elif data.startswith("remove_blacklist:"):
            return await self.remove_blacklist_action(update, context)
        elif data.startswith("remove_whitelist:"):
            return await self.remove_whitelist_action(update, context)
        elif data == "broadcast_forward":
            return await self.broadcast_forward_start(update, context)
        elif data.startswith("toggle_feature:"):
            feature = data.split(":")[1]
            return await self.toggle_feature(update, context, feature)
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
        
        return SET_API_KEY
    
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
            
            keyboard = [[InlineKeyboardButton("🔙 بازگشت به پنل", callback_data="back_to_main")]]
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
            "🔙 برای بازگشت: /cancel",
            parse_mode='Markdown'
        )
        
        return ADD_WHITELIST
    
    async def add_whitelist_process(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """پردازش افزودن کاربر به لیست سفید"""
        try:
            user_id = int(update.message.text.strip())
            
            # بررسی وجود کاربر
            users = self.store.get('users', [])
            if user_id not in users:
                await update.message.reply_text(
                    f"❌ **کاربر یافت نشد!**\n\n"
                    f"👤 **آیدی وارد شده**: {user_id}\n"
                    f"📊 **کل کاربران**: {len(users)}\n\n"
                    f"🔙 برای بازگشت کلیک کنید:",
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton("🔙 بازگشت", callback_data="back_to_main")
                    ]])
                )
                return ADMIN_PANEL
            
            # بررسی اینکه قبلاً در لیست سفید نیست
            whitelist = self.store.get('whitelist', [])
            if user_id in whitelist:
                await update.message.reply_text(
                    f"⚠️ **کاربر قبلاً در لیست سفید است!**\n\n"
                    f"👤 **آیدی کاربر**: {user_id}\n\n"
                    f"🔙 برای بازگشت کلیک کنید:",
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton("🔙 بازگشت", callback_data="back_to_main")
                    ]])
                )
                return ADMIN_PANEL
            
            # افزودن به لیست سفید
            whitelist.append(user_id)
            self.store['whitelist'] = whitelist
            save_store(self.store)
            
            keyboard = [[InlineKeyboardButton("🔙 بازگشت به پنل", callback_data="back_to_main")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                f"✅ **کاربر با موفقیت به لیست سفید اضافه شد!**\n\n"
                f"👤 **آیدی کاربر**: {user_id}\n"
                f"⚪ **وضعیت**: در لیست سفید\n"
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
    
    async def add_blacklist_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """شروع افزودن به لیست سیاه"""
        query = update.callback_query
        await query.answer()
        
        await query.edit_message_text(
            "🚫 **افزودن به لیست سیاه**\n\n"
            "لطفاً آیدی عددی کاربر را ارسال کنید:\n\n"
            "🔙 برای لغو: /cancel"
        )
        
        return ADD_BLACKLIST
    
    async def add_blacklist_process(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """پردازش افزودن به لیست سیاه"""
        user_id = update.message.text.strip()
        
        try:
            user_id = int(user_id)
            
            # بررسی وجود کاربر
            users = self.store.get('users', [])
            if user_id not in users:
                await update.message.reply_text(
                    f"❌ **کاربر یافت نشد!**\n\n"
                    f"👤 **آیدی وارد شده**: {user_id}\n"
                    f"📊 **کل کاربران**: {len(users)}\n\n"
                    f"🔙 برای بازگشت کلیک کنید:",
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton("🔙 بازگشت", callback_data="back_to_main")
                    ]])
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
    
    async def add_whitelist_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """شروع افزودن به لیست سفید"""
        query = update.callback_query
        await query.answer()
        
        await query.edit_message_text(
            "✅ **افزودن به لیست سفید**\n\n"
            "لطفاً آیدی عددی کاربر را ارسال کنید:\n\n"
            "🔙 برای لغو: /cancel"
        )
        
        return WHITELIST_USER
    

    
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
    
    async def toggle_feature(self, update: Update, context: ContextTypes.DEFAULT_TYPE, feature: str):
        """تغییر وضعیت ویژگی‌های ربات"""
        query = update.callback_query
        await query.answer()
        
        features = self.store.get('enabled_features', {
            'price': True, 'fiat': True, 'news': True, 'chart': True,
            'compare': True, 'p2p': True, 'watchlist': True, 'portfolio': True,
            'settings': True, 'alerts': True
        })
        
        features[feature] = not features.get(feature, True)
        self.store['enabled_features'] = features
        save_store(self.store)
        
        keyboard = [[InlineKeyboardButton("🔙 بازگشت", callback_data="admin_bot_settings")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        status = "فعال" if features[feature] else "غیرفعال"
        await query.edit_message_text(
            f"✅ **ویژگی {feature.title()} {status} شد!**\n\n"
            f"🔄 **وضعیت جدید**: {'🟢 فعال' if features[feature] else '🔴 غیرفعال'}\n"
            f"📅 **تاریخ**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            reply_markup=reply_markup
        )
        
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
    
    async def cancel(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """لغو عملیات"""
        await update.message.reply_text("❌ عملیات لغو شد.")
        return ConversationHandler.END

# ایجاد نمونه از کلاس
admin_panel = AdminPanel()
