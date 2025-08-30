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
    VIEW_LOGS, MANAGE_ALERTS, CUSTOM_COMMANDS, BOT_SETTINGS
) = range(19)

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
➖ حذف ادمین
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
    
    async def broadcast_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """شروع ارسال همگانی"""
        query = update.callback_query
        await query.answer()
        
        keyboard = [
            [InlineKeyboardButton("📢 ارسال به همه", callback_data="broadcast_all")],
            [InlineKeyboardButton("👥 ارسال به ادمین‌ها", callback_data="broadcast_admins")],
            [InlineKeyboardButton("⚪ ارسال به لیست سفید", callback_data="broadcast_whitelist")],
            [InlineKeyboardButton("🔙 بازگشت", callback_data="back_to_main")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        users_count = len(self.store.get('users', []))
        admins_count = len(self.store.get('admins', []))
        whitelist_count = len(self.store.get('whitelist', []))
        
        text = f"""
📢 **ارسال همگانی**

📊 **آمار کاربران**:
👥 کل کاربران: {users_count}
👨‍💼 ادمین‌ها: {admins_count}
⚪ لیست سفید: {whitelist_count}

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
    
    async def broadcast_message_process(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """پردازش ارسال پیام همگانی"""
        broadcast_type = context.user_data.get('broadcast_type', 'all')
        
        # تعیین لیست گیرندگان
        if broadcast_type == 'all':
            recipients = self.store.get('users', [])
        elif broadcast_type == 'admins':
            recipients = self.store.get('admins', []) + [OWNER_ID]
        elif broadcast_type == 'whitelist':
            recipients = self.store.get('whitelist', [])
        
        # ارسال پیام
        success_count = 0
        failed_count = 0
        
        await update.message.reply_text("📤 در حال ارسال پیام...")
        
        for user_id in recipients:
            try:
                if update.message.text:
                    await context.bot.send_message(
                        chat_id=user_id,
                        text=update.message.text,
                        parse_mode='Markdown'
                    )
                elif update.message.photo:
                    await context.bot.send_photo(
                        chat_id=user_id,
                        photo=update.message.photo[-1].file_id,
                        caption=update.message.caption
                    )
                elif update.message.video:
                    await context.bot.send_video(
                        chat_id=user_id,
                        video=update.message.video.file_id,
                        caption=update.message.caption
                    )
                elif update.message.document:
                    await context.bot.send_document(
                        chat_id=user_id,
                        document=update.message.document.file_id,
                        caption=update.message.caption
                    )
                
                success_count += 1
                await asyncio.sleep(0.1)  # تاخیر برای جلوگیری از محدودیت
                
            except Exception as e:
                failed_count += 1
                print(f"Failed to send to {user_id}: {e}")
        
        keyboard = [[InlineKeyboardButton("🔙 بازگشت به پنل", callback_data="back_to_main")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            f"✅ **ارسال همگانی تکمیل شد!**\n\n"
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
            [InlineKeyboardButton("🔑 تنظیم API Key", callback_data="set_api_key")],
            [InlineKeyboardButton("🔄 تغییر Provider", callback_data="change_provider")],
            [InlineKeyboardButton("📊 وضعیت API", callback_data="api_status")],
            [InlineKeyboardButton("🔙 بازگشت", callback_data="back_to_main")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        providers = self.store.get('providers', {})
        crypto_provider = providers.get('crypto', 'coingecko')
        fiat_provider = providers.get('fiat', 'exchangerate_host')
        
        text = f"""
🔧 **تنظیمات API**

📊 **Provider های فعلی**:
💰 ارز دیجیتال: {crypto_provider}
💱 ارز فیات: {fiat_provider}

**عملیات موجود**:
🔑 تنظیم API Key جدید
🔄 تغییر Provider
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
        channel = force_sub.get('channel_username', 'تنظیم نشده')
        
        status_emoji = "✅" if is_enabled else "❌"
        status_text = "فعال" if is_enabled else "غیرفعال"
        
        keyboard = [
            [InlineKeyboardButton(f"{'❌' if is_enabled else '✅'} {'غیرفعال' if is_enabled else 'فعال'} کردن", 
                                callback_data="toggle_force_sub")],
            [InlineKeyboardButton("📢 تنظیم کانال", callback_data="set_force_sub_channel")],
            [InlineKeyboardButton("🔙 بازگشت", callback_data="back_to_main")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        text = f"""
🔒 **قفل اجباری عضویت**

📊 **وضعیت فعلی**:
{status_emoji} قفل اجباری: {status_text}
📢 کانال: @{channel}

**عملیات موجود**:
{'❌ غیرفعال' if is_enabled else '✅ فعال'} کردن قفل اجباری
📢 تنظیم کانال اجباری
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
            [InlineKeyboardButton("➖ حذف از لیست سفید", callback_data="remove_whitelist")],
            [InlineKeyboardButton("⚫ افزودن به لیست سیاه", callback_data="add_blacklist")],
            [InlineKeyboardButton("⚪ حذف از لیست سیاه", callback_data="remove_blacklist")],
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
➖ حذف کاربر از لیست سفید
⚫ افزودن کاربر به لیست سیاه
⚪ حذف کاربر از لیست سیاه
📋 مشاهده لیست کامل
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
        elif data == "admin_commands":
            return await self.admin_commands_panel(update, context)
        elif data == "admin_bot_settings":
            return await self.admin_bot_settings_panel(update, context)
        elif data.startswith("broadcast_"):
            return await self.broadcast_message_start(update, context)
        elif data == "set_welcome":
            return await self.set_welcome_text_start(update, context)
        elif data == "toggle_force_sub":
            return await self.toggle_force_subscription(update, context)
        elif data == "clear_cache":
            return await self.clear_cache_action(update, context)
        elif data == "create_backup":
            return await self.create_backup_action(update, context)
        elif data == "admin_exit":
            await query.edit_message_text("👋 پنل مدیریتی بسته شد.")
            return ConversationHandler.END
        
        return ADMIN_PANEL
    
    async def cancel(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """لغو عملیات"""
        await update.message.reply_text("❌ عملیات لغو شد.")
        return ConversationHandler.END

# ایجاد نمونه از کلاس
admin_panel = AdminPanel()
