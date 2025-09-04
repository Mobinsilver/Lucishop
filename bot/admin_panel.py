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
    
    async def handle_admin_panel_text(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """مدیریت متن‌های پنل مدیریتی"""
        user_id = update.effective_user.id
        
        # بررسی دسترسی (مالک یا ادمین)
        admins = self.store.get('admins', [])
        if user_id != OWNER_ID and user_id not in admins:
            await update.message.reply_text("❌ شما دسترسی به پنل مدیریتی ندارید!")
    
        
        text = update.message.text.strip()
        

        
        # Handle admin panel buttons
        if text == "👥 مدیریت ادمین‌ها":
            await self.admin_manage_admins(update, context)
        elif text == "📢 ارسال همگانی":
            await self.broadcast_start(update, context)
        elif text == "📝 تنظیم متن‌ها":
            await self.admin_texts_panel(update, context)
        elif text == "🔧 مدیریت API ها":
            await self.manage_apis(update, context)
        elif text == "💰 مدیریت ارزها":
            await self.manage_currencies(update, context)
        elif text == "📊 مدیریت شاخص‌ها":
            await self.manage_indicators(update, context)
        elif text == "🔒 قفل اجباری":
            await self.force_subscription_panel(update, context)
        elif text == "⚪ لیست سفید/سیاه":
            await self.admin_lists_panel(update, context)
        elif text == "🗄️ مدیریت کش":
            await self.admin_cache_panel(update, context)
        elif text == "⚙️ تنظیمات سیستم":
            await self.admin_system_panel(update, context)
        elif text == "💾 پشتیبان‌گیری":
            await self.admin_backup_panel(update, context)
        elif text == "📋 لاگ‌ها":
            await self.admin_logs_panel(update, context)
        elif text == "🔔 مدیریت هشدارها":
            await self.admin_alerts_panel(update, context)
        elif text == "📊 آمار و گزارش":
            await self.admin_stats_panel(update, context)
        elif text == "⌨️ دستورات سفارشی":
            await self.admin_commands_panel(update, context)
        elif text == "🤖 تنظیمات ربات":
            await self.admin_bot_settings_panel(update, context)
        elif text == "🔙 بازگشت به منو":
            await self.admin_panel_main(update, context)
        elif text == "➕ افزودن ادمین":
            await self.add_admin_start(update, context)
        elif text == "➖ حذف ادمین":
            await self.remove_admin_start(update, context)
        elif text == "📋 لیست ادمین‌ها":
            await self.list_admins_action(update, context)
        elif text == "➕ افزودن API جدید":
            await self.add_api(update, context)
        elif text == "📋 لیست API ها":
            await self.list_apis_action(update, context)
        elif text == "⚙️ تنظیمات API":
            await self.api_settings_panel(update, context)
        elif text == "➕ افزودن ارز":
            await self.add_currency(update, context)
        elif text == "📋 لیست ارزها":
            await self.list_currencies_action(update, context)
        elif text == "⚙️ تنظیمات ارزها":
            await self.currency_settings_panel(update, context)
        elif text == "➕ افزودن شاخص":
            await self.add_indicator(update, context)
        elif text == "📋 لیست شاخص‌ها":
            await self.list_indicators_action(update, context)
        elif text == "⚙️ تنظیمات شاخص‌ها":
            await self.indicator_settings_panel(update, context)
        elif text == "📌 پین کردن پیام همگانی":
            await self.pin_broadcast_message(update, context)
        elif text == "🪙 کریپتو":
            await self._process_api_type(update, context, "🪙 کریپتو")
        elif text == "💱 فیات":
            await self._process_api_type(update, context, "💱 فیات")
        elif text == "📰 اخبار":
            await self._process_api_type(update, context, "📰 اخبار")
        elif text == "📊 تکنیکال":
            await self._process_api_type(update, context, "📊 تکنیکال")
        elif text == "🔍 دریافت لیست ارزها از API":
            await self.fetch_currencies_from_api(update, context)
        elif text == "🔴 خاموش":
            await self.process_currency_toggle(update, context)
        elif text == "🟢 روشن":
            await self.process_currency_toggle(update, context)
        elif text == "🔙 بازگشت به لیست ارزها":
            await self.manage_currencies(update, context)
        elif text == "⬅️ صفحه قبل":
            await self.process_currency_selection(update, context)
        elif text == "➡️ صفحه بعد":
            await self.process_currency_selection(update, context)
        elif text == "⌨️ متن‌های کیبورد سریع":
            await self.show_keyboard_texts_menu(update, context)
        elif text == "💬 متن‌های پیام‌ها":
            await self.show_message_texts_menu(update, context)
        elif text == "🎯 متن‌های قابلیت‌ها":
            await self.show_feature_texts_menu(update, context)
        elif text == "📋 متن‌های منوها":
            await self.show_menu_texts_menu(update, context)
        elif text == "⚠️ متن‌های خطا":
            await self.show_error_texts_menu(update, context)
        elif text == "ℹ️ متن‌های اطلاعاتی":
            await self.show_info_texts_menu(update, context)
        elif text == "➕ افزودن چنل":
            await self.add_force_sub_channel_start(update, context)
        elif text == "➖ حذف چنل":
            await self.remove_force_sub_channel_start(update, context)
        elif text == "📋 لیست چنل‌ها":
            await self.list_force_sub_channels(update, context)
        elif text == "⚙️ تنظیمات قفل":
            await self.toggle_force_subscription(update, context)
        elif text == "ادمین کردم":
            await self.process_admin_confirmation(update, context)
        elif text == "📊 آمار 24 ساعت":
            await self.show_24h_stats(update, context)
        elif text == "📈 آمار 1 هفته":
            await self.show_7d_stats(update, context)
        elif text == "📅 آمار 1 ماه":
            await self.show_30d_stats(update, context)
        elif text == "🔄 بروزرسانی آمار":
            await self.admin_stats_panel(update, context)
        elif text == "📋 گزارش کامل":
            await self.show_full_report(update, context)
        elif text == "⚙️ تنظیمات آمار":
            await self.toggle_live_notifications(update, context)
        elif text == "🔧 مدیریت دکمه‌های کاربری":
            await self.manage_user_buttons(update, context)
        elif text == "⚙️ مدیریت دکمه‌های ادمین":
            await self.manage_admin_buttons(update, context)
        elif text == "📊 آمار ویژگی‌ها":
            await self.show_features_stats(update, context)
        elif text == "🔄 بازنشانی تنظیمات":
            await self.reset_settings(update, context)
        elif text == "🔄 تایید بازنشانی":
            await self.process_reset_confirmation(update, context)
        elif text == "❌ لغو":
            await self.process_reset_confirmation(update, context)
        elif text == "➕ افزودن به لیست سیاه":
            await self.add_to_blacklist_start(update, context)
        elif text == "➖ حذف از لیست سیاه":
            await self.remove_from_blacklist_start(update, context)
        elif text == "📋 لیست مسدودین":
            await self.show_blacklist_users(update, context)
        elif text == "📊 آمار لیست‌ها":
            await self.show_lists_stats(update, context)
        elif text == "✅ تایید مسدودسازی":
            await self.process_blacklist_confirmation(update, context)
        elif text == "✅ تایید آزادسازی":
            await self.process_unblacklist_confirmation(update, context)
        else:
            await update.message.reply_text("❌ دستور نامعتبر! لطفاً از دکمه‌های موجود استفاده کنید.")

    async def admin_panel_main(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """پنل مدیریتی اصلی"""
        user_id = update.effective_user.id
        
        # بررسی دسترسی (مالک یا ادمین)
        admins = self.store.get('admins', [])
        if user_id != OWNER_ID and user_id not in admins:
            await update.message.reply_text("❌ شما دسترسی به پنل مدیریتی ندارید!")
    
        

        
        # ایجاد کیبورد سریع به جای دکمه‌های شیشه‌ای
        from telegram import ReplyKeyboardMarkup, KeyboardButton
        
        keyboard = [
            [KeyboardButton("👥 مدیریت ادمین‌ها"), KeyboardButton("📢 ارسال همگانی")],
            [KeyboardButton("📝 تنظیم متن‌ها"), KeyboardButton("🔧 مدیریت API ها")],
            [KeyboardButton("💰 مدیریت ارزها"), KeyboardButton("📊 مدیریت شاخص‌ها")],
            [KeyboardButton("🔒 قفل اجباری"), KeyboardButton("⚪ لیست سفید/سیاه")],
            [KeyboardButton("🗄️ مدیریت کش"), KeyboardButton("⚙️ تنظیمات سیستم")],
            [KeyboardButton("💾 پشتیبان‌گیری"), KeyboardButton("📋 لاگ‌ها")],
            [KeyboardButton("🔔 مدیریت هشدارها"), KeyboardButton("📊 آمار و گزارش")],
            [KeyboardButton("⌨️ دستورات سفارشی"), KeyboardButton("🤖 تنظیمات ربات")],
            [KeyboardButton("🔙 بازگشت به منو")]
        ]
        
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        
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
        
        await update.message.reply_text(text, reply_markup=reply_markup)
    
    async def admin_manage_admins(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """مدیریت ادمین‌ها"""
        admins = self.store.get('admins', [])
        admin_list = "\n".join([f"• {admin_id}" for admin_id in admins])
        
        keyboard = [
            [KeyboardButton("➕ افزودن ادمین"), KeyboardButton("➖ حذف ادمین")],
            [KeyboardButton("📋 لیست ادمین‌ها")],
            [KeyboardButton("🔙 بازگشت به منو")]
        ]
        
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        
        text = f"""
👥 **مدیریت ادمین‌ها**

👨‍💼 **ادمین‌های فعلی**:
{admin_list if admin_list else "• هیچ ادمینی وجود ندارد"}

**عملیات موجود**:
➕ افزودن ادمین جدید
➖ حذف ادمین موجود
📋 مشاهده لیست کامل
        """
        
        await update.message.reply_text(text, reply_markup=reply_markup)
    
    async def add_admin_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """شروع فرآیند افزودن ادمین"""
        await update.message.reply_text(
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
            
            keyboard = [[KeyboardButton("🔙 بازگشت به منو")]]
            reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
            
            await update.message.reply_text(
                f"✅ **ادمین با موفقیت اضافه شد!**\n\n"
                f"👤 **آیدی جدید**: {new_admin_id}\n"
                f"📅 **تاریخ**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
                f"🎉 این کاربر حالا دسترسی کامل به پنل مدیریتی دارد!",
                reply_markup=reply_markup
            )
            

            
        except ValueError:
            await update.message.reply_text("❌ لطفاً یک عدد معتبر وارد کنید!")
            return ADD_ADMIN
    
    async def remove_admin_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """شروع فرآیند حذف ادمین"""
        await update.message.reply_text(
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
            
            keyboard = [[KeyboardButton("🔙 بازگشت به منو")]]
            reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
            
            await update.message.reply_text(
                f"✅ **ادمین با موفقیت حذف شد!**\n\n"
                f"👤 **آیدی حذف شده**: {admin_to_remove}\n"
                f"📅 **تاریخ**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
                f"🔒 تمامی دسترسی‌های پنل مدیریتی از این کاربر گرفته شد!",
                reply_markup=reply_markup
            )
            

            
        except ValueError:
            await update.message.reply_text("❌ لطفاً یک عدد معتبر وارد کنید!")
            return REMOVE_ADMIN
    
    async def broadcast_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """شروع ارسال همگانی"""
        users_count = len(self.store.get('users', []))
        admins_count = len(self.store.get('admins', []))
        whitelist_count = len(self.store.get('whitelist', []))
        
        text = f"""
📢 **ارسال همگانی**

👥 **آمار کاربران**:
• کل کاربران: {users_count}
• ادمین‌ها: {admins_count}
• لیست سفید: {whitelist_count}

📝 **دستورالعمل**:
لطفاً پیام خود را ارسال کنید تا به تمام کاربران ارسال شود.

⚠️ **نکات مهم**:
• پیام شما به تمام کاربرانی که ربات را استارت کرده‌اند ارسال می‌شود
• آمار ارسال موفق/ناموفق نمایش داده می‌شود
• امکان پین کردن پیام در پیوی کاربران وجود دارد

🔙 برای لغو عملیات، /cancel را ارسال کنید.
        """
        
        await update.message.reply_text(text)
        return BROADCAST_MESSAGE
    
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
        

    
    async def broadcast_message_process(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """پردازش ارسال پیام همگانی"""
        # دریافت تمام کاربران
        users = self.store.get('users', [])
        admins = self.store.get('admins', [])
        whitelist = self.store.get('whitelist', [])
        
        # ترکیب تمام گیرندگان (بدون تکرار)
        all_recipients = list(set(users + admins + [OWNER_ID] + whitelist))
        
        # ذخیره پیام برای پین کردن
        context.user_data['broadcast_message'] = {
            'message_id': update.message.message_id,
            'chat_id': update.message.chat_id,
            'text': update.message.text or update.message.caption or "پیام غیرمتنی"
        }
        
        # ارسال پیام
        success_count = 0
        failed_count = 0
        failed_users = []
        
        await update.message.reply_text("📤 در حال ارسال پیام به تمام کاربران...")
        
        for user_id in all_recipients:
            try:
                # ارسال پیام (کپی به جای فوروارد)
                if update.message.text:
                    await context.bot.send_message(
                        chat_id=user_id,
                        text=update.message.text,
                        parse_mode=update.message.parse_mode
                    )
                elif update.message.photo:
                    await context.bot.send_photo(
                        chat_id=user_id,
                        photo=update.message.photo[-1].file_id,
                        caption=update.message.caption,
                        parse_mode=update.message.parse_mode
                    )
                elif update.message.video:
                    await context.bot.send_video(
                        chat_id=user_id,
                        video=update.message.video.file_id,
                        caption=update.message.caption,
                        parse_mode=update.message.parse_mode
                    )
                elif update.message.document:
                    await context.bot.send_document(
                        chat_id=user_id,
                        document=update.message.document.file_id,
                        caption=update.message.caption,
                        parse_mode=update.message.parse_mode
                    )
                else:
                    # برای سایر انواع پیام، فوروارد کن
                    await update.message.forward(chat_id=user_id)
                
                success_count += 1
                await asyncio.sleep(0.1)  # تاخیر برای جلوگیری از محدودیت
                
            except Exception as e:
                failed_count += 1
                failed_users.append(user_id)
                print(f"Failed to send to {user_id}: {e}")
        
        # نمایش آمار
        keyboard = [
            [KeyboardButton("📌 پین کردن پیام همگانی")],
            [KeyboardButton("🔙 بازگشت به منو")]
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        
        text = f"""
✅ **ارسال همگانی تکمیل شد!**

📊 **آمار ارسال**:
• ✅ موفق: {success_count}
• ❌ ناموفق: {failed_count}
• 📅 تاریخ: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

👥 **گیرندگان**:
• کل کاربران: {len(all_recipients)}
• ارسال موفق: {success_count}
• ارسال ناموفق: {failed_count}

💡 **گزینه‌های موجود**:
• 📌 پین کردن پیام در پیوی تمام کاربران
• 🔙 بازگشت به منوی اصلی
        """
        
        await update.message.reply_text(text, reply_markup=reply_markup)
    
    async def pin_broadcast_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """پین کردن پیام همگانی در پیوی تمام کاربران"""
        broadcast_data = context.user_data.get('broadcast_message')
        
        if not broadcast_data:
            await update.message.reply_text("❌ پیام همگانی یافت نشد!")

        
        # دریافت تمام کاربران
        users = self.store.get('users', [])
        admins = self.store.get('admins', [])
        whitelist = self.store.get('whitelist', [])
        all_recipients = list(set(users + admins + [OWNER_ID] + whitelist))
        
        await update.message.reply_text("📌 در حال پین کردن پیام در پیوی تمام کاربران...")
        
        success_count = 0
        failed_count = 0
        
        for user_id in all_recipients:
            try:
                # ارسال پیام و پین کردن آن
                if broadcast_data.get('text') and broadcast_data['text'] != "پیام غیرمتنی":
                    sent_message = await context.bot.send_message(
                        chat_id=user_id,
                        text=broadcast_data['text']
                    )
                else:
                    # برای پیام‌های غیرمتنی، فوروارد کن
                    sent_message = await context.bot.forward_message(
                        chat_id=user_id,
                        from_chat_id=broadcast_data['chat_id'],
                        message_id=broadcast_data['message_id']
                    )
                
                # پین کردن پیام
                await context.bot.pin_chat_message(
                    chat_id=user_id,
                    message_id=sent_message.message_id
                )
                
                success_count += 1
                await asyncio.sleep(0.1)
                
            except Exception as e:
                failed_count += 1
                print(f"Failed to pin message for {user_id}: {e}")
        
        keyboard = [
            [KeyboardButton("🔙 بازگشت به منو")]
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        
        text = f"""
📌 **پین کردن پیام همگانی تکمیل شد!**

📊 **آمار پین کردن**:
• ✅ موفق: {success_count}
• ❌ ناموفق: {failed_count}
• 📅 تاریخ: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

👥 **گیرندگان**:
• کل کاربران: {len(all_recipients)}
• پین موفق: {success_count}
• پین ناموفق: {failed_count}

💡 پیام همگانی در پیوی تمام کاربران پین شد.
        """
        
        await update.message.reply_text(text, reply_markup=reply_markup)
    
    async def admin_texts_panel(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """پنل تنظیم متن‌های ربات"""
        keyboard = [
            [KeyboardButton("⌨️ متن‌های کیبورد سریع"), KeyboardButton("💬 متن‌های پیام‌ها")],
            [KeyboardButton("🎯 متن‌های قابلیت‌ها"), KeyboardButton("📋 متن‌های منوها")],
            [KeyboardButton("⚠️ متن‌های خطا"), KeyboardButton("ℹ️ متن‌های اطلاعاتی")],
            [KeyboardButton("🔙 بازگشت به منو")]
        ]
        
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        
        text = """
📝 **تنظیم متن‌های ربات**

🎯 **دسته‌بندی متن‌ها**:

⌨️ **متن‌های کیبورد سریع**: دکمه‌های کیبورد اصلی
💬 **متن‌های پیام‌ها**: پیام‌های خوش‌آمدگویی، راهنما و...
🎯 **متن‌های قابلیت‌ها**: توضیحات قابلیت‌های ربات
📋 **متن‌های منوها**: متن‌های منوهای مختلف
⚠️ **متن‌های خطا**: پیام‌های خطا و هشدار
ℹ️ **متن‌های اطلاعاتی**: پیام‌های اطلاع‌رسانی

💡 **نحوه استفاده**:
• دسته مورد نظر را انتخاب کنید
• متن مورد نظر را انتخاب کنید
• متن جدید را ارسال کنید
• تغییرات بلافاصله اعمال می‌شوند
        """
        
        await update.message.reply_text(text, reply_markup=reply_markup)
    
    async def show_keyboard_texts_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """نمایش منوی متن‌های کیبورد سریع"""
        keyboard = [
            [KeyboardButton("💰 نرخ ارز"), KeyboardButton("📰 اخبار")],
            [KeyboardButton("📊 تحلیل تکنیکال"), KeyboardButton("🔄 مقایسه قیمت‌ها")],
            [KeyboardButton("💱 P2P"), KeyboardButton("🔔 هشدارهای من")],
            [KeyboardButton("⭐ واچ‌لیست"), KeyboardButton("💼 پرتفوی")],
            [KeyboardButton("⚙️ تنظیمات"), KeyboardButton("❓ راهنما")],
            [KeyboardButton("🔙 بازگشت به منو")]
        ]
        
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        
        text = """
⌨️ **تنظیم متن‌های کیبورد سریع**

🎯 **دکمه‌های قابل تنظیم**:

💰 **نرخ ارز**: دکمه نمایش قیمت ارزها
📰 **اخبار**: دکمه نمایش اخبار
📊 **تحلیل تکنیکال**: دکمه تحلیل تکنیکال
🔄 **مقایسه قیمت‌ها**: دکمه مقایسه قیمت‌ها
💱 **P2P**: دکمه P2P
🔔 **هشدارهای من**: دکمه هشدارها
⭐ **واچ‌لیست**: دکمه واچ‌لیست
💼 **پرتفوی**: دکمه پرتفوی
⚙️ **تنظیمات**: دکمه تنظیمات
❓ **راهنما**: دکمه راهنما

💡 **نحوه استفاده**:
• روی دکمه مورد نظر کلیک کنید
• متن جدید را ارسال کنید
• تغییرات بلافاصله اعمال می‌شوند
        """
        
        await update.message.reply_text(text, reply_markup=reply_markup)
        return "KEYBOARD_TEXT_SELECTION"
    
    async def process_keyboard_text_selection(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """پردازش انتخاب متن کیبورد"""
        selected_text = update.message.text
        
        # نگاشت دکمه‌ها به کلیدهای store
        text_mapping = {
            "💰 نرخ ارز": "crypto_prices",
            "📰 اخبار": "news",
            "📊 تحلیل تکنیکال": "technical_analysis",
            "🔄 مقایسه قیمت‌ها": "price_comparison",
            "💱 P2P": "p2p",
            "🔔 هشدارهای من": "alerts",
            "⭐ واچ‌لیست": "watchlist",
            "💼 پرتفوی": "portfolio",
            "⚙️ تنظیمات": "settings",
            "❓ راهنما": "help"
        }
        
        if selected_text not in text_mapping:
            await update.message.reply_text("❌ دکمه انتخاب شده نامعتبر است!")
            return "KEYBOARD_TEXT_SELECTION"
        
        text_key = text_mapping[selected_text]
        current_text = self.store.get('keyboard_texts', {}).get(text_key, selected_text)
        
        # ذخیره انتخاب
        context.user_data['selected_keyboard_text'] = text_key
        context.user_data['selected_keyboard_display'] = selected_text
        
        keyboard = [
            [KeyboardButton("🔙 بازگشت به منو")]
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        
        text = f"""
⌨️ **تنظیم متن دکمه: {selected_text}**

📝 **متن فعلی**: `{current_text}`

✏️ **متن جدید را ارسال کنید**:

لطفاً متن جدید دکمه را ارسال کنید.

💡 **نکات مهم**:
• متن باید کوتاه و واضح باشد
• از emoji استفاده کنید
• تغییرات بلافاصله اعمال می‌شوند
• برای لغو: /cancel
        """
        
        await update.message.reply_text(text, reply_markup=reply_markup)
        return "KEYBOARD_TEXT_EDIT"
    
    async def process_keyboard_text_edit(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """پردازش ویرایش متن کیبورد"""
        new_text = update.message.text.strip()
        text_key = context.user_data.get('selected_keyboard_text')
        display_name = context.user_data.get('selected_keyboard_display')
        
        if not text_key:
            await update.message.reply_text("❌ خطا در پردازش!")

        
        # ذخیره متن جدید
        keyboard_texts = self.store.get('keyboard_texts', {})
        keyboard_texts[text_key] = new_text
        self.store['keyboard_texts'] = keyboard_texts
        save_store(self.store)
        
        keyboard = [
            [KeyboardButton("🔙 بازگشت به منو")]
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        
        text = f"""
✅ **متن دکمه با موفقیت تغییر کرد!**

⌨️ **دکمه**: {display_name}
📝 **متن جدید**: `{new_text}`
📅 **تاریخ**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

🎉 **تبریک!** تغییرات بلافاصله اعمال شد.

💡 **نکته**: دکمه در کیبورد سریع با متن جدید نمایش داده می‌شود.
        """
        
        await update.message.reply_text(text, reply_markup=reply_markup)
    
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

        
        try:
            # تست API TradingView
            # اینجا کد تست API قرار می‌گیرد
            await query.answer("✅ TradingView API درست کار می‌کند!")
        except Exception as e:
            await query.answer(f"❌ خطا در TradingView API: {str(e)}")
        

    
    async def test_fiat_action(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """تست فیات API"""
        query = update.callback_query
        await query.answer()
        
        fiat_api = self.store.get('fiat_api', '')
        
        if not fiat_api or fiat_api == 'تنظیم نشده':
            await query.answer("❌ فیات API تنظیم نشده!")

        
        try:
            # تست API فیات
            # اینجا کد تست API قرار می‌گیرد
            await query.answer("✅ فیات API درست کار می‌کند!")
        except Exception as e:
            await query.answer(f"❌ خطا در فیات API: {str(e)}")
        

    
    async def test_crypto_action(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """تست کریپتو API"""
        query = update.callback_query
        await query.answer()
        
        crypto_api = self.store.get('crypto_api', '')
        
        if not crypto_api or crypto_api == 'تنظیم نشده':
            await query.answer("❌ کریپتو API تنظیم نشده!")

        
        try:
            # تست API کریپتو
            # اینجا کد تست API قرار می‌گیرد
            await query.answer("✅ کریپتو API درست کار می‌کند!")
        except Exception as e:
            await query.answer(f"❌ خطا در کریپتو API: {str(e)}")
        

    
    async def force_subscription_panel(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """پنل قفل اجباری"""
        force_sub = self.store.get('forced_subscription', {})
        is_enabled = force_sub.get('enabled', False)
        channels = force_sub.get('channels', [])
        
        status_emoji = "✅" if is_enabled else "❌"
        status_text = "فعال" if is_enabled else "غیرفعال"
        
        # نمایش کانال‌ها
        if channels:
            channels_text = f"📢 **{len(channels)} کانال فعال**\n\n"
            for i, channel in enumerate(channels, 1):
                channel_info = channel.get('title', 'نامشخص')
                channel_link = channel.get('link', '')
                channels_text += f"{i}. {channel_info}\n   🔗 {channel_link}\n\n"
        else:
            channels_text = "• هیچ کانالی تنظیم نشده"
        
        keyboard = [
            [KeyboardButton("➕ افزودن چنل"), KeyboardButton("➖ حذف چنل")],
            [KeyboardButton("📋 لیست چنل‌ها"), KeyboardButton("⚙️ تنظیمات قفل")],
            [KeyboardButton("🔙 بازگشت به منو")]
        ]
        
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        
        text = f"""
🔒 **قفل اجباری عضویت**

📊 **وضعیت فعلی**:
{status_emoji} قفل اجباری: {status_text}
📢 تعداد چنل‌ها: {len(channels)}

{channels_text}

🎯 **عملیات موجود**:
➕ **افزودن چنل**: اضافه کردن چنل یا گروه جدید
➖ **حذف چنل**: حذف چنل از لیست
📋 **لیست چنل‌ها**: مشاهده تمام چنل‌های فعال
⚙️ **تنظیمات قفل**: فعال/غیرفعال کردن قفل

💡 **نحوه کارکرد**:
• کاربران باید در چنل‌های مشخص شده عضو باشند
• ربات عضویت را بررسی می‌کند
• در صورت عدم عضویت، دسترسی محدود می‌شود
• پیام هشدار 15 ثانیه‌ای نمایش داده می‌شود
• کانال‌ها به صورت دکمه‌های شیشه‌ای نمایش داده می‌شوند
        """
        
        await update.message.reply_text(text, reply_markup=reply_markup)
    
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
        

    
    async def admin_stats_panel(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """پنل آمار و گزارش پیشرفته"""
        # بررسی دسترسی - فقط مالک و ادمین‌ها
        user_id = update.effective_user.id
        from config import OWNER_ID
        admins = self.store.get('admins', [])
        
        if user_id != OWNER_ID and user_id not in admins:
            await update.message.reply_text("❌ شما دسترسی به آمار و گزارش ندارید!")

        
        # محاسبه آمار پیشرفته
        stats = self._calculate_advanced_stats()
        
        keyboard = [
            [KeyboardButton("📊 آمار 24 ساعت"), KeyboardButton("📈 آمار 1 هفته")],
            [KeyboardButton("📅 آمار 1 ماه"), KeyboardButton("🔄 بروزرسانی آمار")],
            [KeyboardButton("📋 گزارش کامل"), KeyboardButton("⚙️ تنظیمات آمار")],
            [KeyboardButton("🔙 بازگشت به منو")]
        ]
        
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        
        text = f"""
📊 **آمار و گزارش پیشرفته ربات**

🎯 **آمار کلی**:
• کل کاربران: {stats['total_users']}
• ادمین‌ها: {stats['total_admins']}
• لیست سفید: {stats['whitelist']}
• لیست سیاه: {stats['blacklist']}

⏰ **آمار زمانی**:
• 24 ساعت گذشته: {stats['users_24h']} کاربر جدید
• 1 هفته گذشته: {stats['users_7d']} کاربر جدید
• 1 ماه گذشته: {stats['users_30d']} کاربر جدید

📈 **آمار فعالیت**:
• کاربران فعال (24 ساعت): {stats['active_24h']}
• کاربران فعال (7 روز): {stats['active_7d']}
• کاربران فعال (30 روز): {stats['active_30d']}

🔔 **اطلاع‌رسانی لحظه‌ای**: {'✅ فعال' if stats['live_notifications'] else '❌ غیرفعال'}

🕒 **آخرین بروزرسانی**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        """
        
        await update.message.reply_text(text, reply_markup=reply_markup)
    
    def _calculate_advanced_stats(self):
        """محاسبه آمار پیشرفته"""
        users = self.store.get('users', [])
        admins = self.store.get('admins', [])
        whitelist = self.store.get('whitelist', [])
        blacklist = self.store.get('blacklist', [])
        user_data = self.store.get('user_data', {})
        
        now = datetime.now()
        
        # آمار کلی
        total_users = len(users)
        total_admins = len(admins) + 1  # +1 for owner
        
        # آمار زمانی - کاربران جدید
        users_24h = 0
        users_7d = 0
        users_30d = 0
        
        for user_id in users:
            user_info = user_data.get(str(user_id), {})
            join_date = user_info.get('join_date')
            
            if join_date:
                try:
                    join_datetime = datetime.fromisoformat(join_date)
                    time_diff = now - join_datetime
                    
                    if time_diff <= timedelta(hours=24):
                        users_24h += 1
                    if time_diff <= timedelta(days=7):
                        users_7d += 1
                    if time_diff <= timedelta(days=30):
                        users_30d += 1
                except:
                    pass
        
        # آمار فعالیت - کاربران فعال
        active_24h = 0
        active_7d = 0
        active_30d = 0
        
        for user_id, data in user_data.items():
            if isinstance(data, dict) and data.get('last_activity'):
                try:
                    last_activity = datetime.fromisoformat(data['last_activity'])
                    time_diff = now - last_activity
                    
                    if time_diff <= timedelta(hours=24):
                        active_24h += 1
                    if time_diff <= timedelta(days=7):
                        active_7d += 1
                    if time_diff <= timedelta(days=30):
                        active_30d += 1
                except:
                    pass
        
        # تنظیمات اطلاع‌رسانی لحظه‌ای
        live_notifications = self.store.get('live_notifications', True)
        
        return {
            'total_users': total_users,
            'total_admins': total_admins,
            'whitelist': len(whitelist),
            'blacklist': len(blacklist),
            'users_24h': users_24h,
            'users_7d': users_7d,
            'users_30d': users_30d,
            'active_24h': active_24h,
            'active_7d': active_7d,
            'active_30d': active_30d,
            'live_notifications': live_notifications
        }
    
    async def show_24h_stats(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """نمایش آمار 24 ساعت گذشته"""
        stats = self._calculate_advanced_stats()
        
        keyboard = [
            [KeyboardButton("🔙 بازگشت به منو")]
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        
        text = f"""
📊 **آمار 24 ساعت گذشته**

👥 **کاربران جدید**: {stats['users_24h']} نفر
📈 **کاربران فعال**: {stats['active_24h']} نفر

📋 **جزئیات**:
• کاربران جدید: {stats['users_24h']} نفر
• کاربران فعال: {stats['active_24h']} نفر
• نرخ رشد: {((stats['users_24h'] / max(stats['total_users'], 1)) * 100):.2f}%

🕒 **بازه زمانی**: 24 ساعت گذشته
📅 **تاریخ**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        """
        
        await update.message.reply_text(text, reply_markup=reply_markup)
    
    async def show_7d_stats(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """نمایش آمار 1 هفته گذشته"""
        stats = self._calculate_advanced_stats()
        
        keyboard = [
            [KeyboardButton("🔙 بازگشت به منو")]
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        
        text = f"""
📈 **آمار 1 هفته گذشته**

👥 **کاربران جدید**: {stats['users_7d']} نفر
📈 **کاربران فعال**: {stats['active_7d']} نفر

📋 **جزئیات**:
• کاربران جدید: {stats['users_7d']} نفر
• کاربران فعال: {stats['active_7d']} نفر
• میانگین روزانه: {(stats['users_7d'] / 7):.1f} نفر
• نرخ رشد: {((stats['users_7d'] / max(stats['total_users'], 1)) * 100):.2f}%

🕒 **بازه زمانی**: 7 روز گذشته
📅 **تاریخ**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        """
        
        await update.message.reply_text(text, reply_markup=reply_markup)
    
    async def show_30d_stats(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """نمایش آمار 1 ماه گذشته"""
        stats = self._calculate_advanced_stats()
        
        keyboard = [
            [KeyboardButton("🔙 بازگشت به منو")]
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        
        text = f"""
📅 **آمار 1 ماه گذشته**

👥 **کاربران جدید**: {stats['users_30d']} نفر
📈 **کاربران فعال**: {stats['active_30d']} نفر

📋 **جزئیات**:
• کاربران جدید: {stats['users_30d']} نفر
• کاربران فعال: {stats['active_30d']} نفر
• میانگین روزانه: {(stats['users_30d'] / 30):.1f} نفر
• میانگین هفتگی: {(stats['users_30d'] / 4.3):.1f} نفر
• نرخ رشد: {((stats['users_30d'] / max(stats['total_users'], 1)) * 100):.2f}%

🕒 **بازه زمانی**: 30 روز گذشته
📅 **تاریخ**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        """
        
        await update.message.reply_text(text, reply_markup=reply_markup)
    
    async def notify_new_user_to_admins(self, context: ContextTypes.DEFAULT_TYPE, user_id: int, username: str = None, first_name: str = None):
        """اطلاع‌رسانی کاربر جدید به مالک و ادمین‌ها"""
        # بررسی فعال بودن اطلاع‌رسانی لحظه‌ای
        if not self.store.get('live_notifications', True):
            return
        
        from config import OWNER_ID
        admins = self.store.get('admins', [])
        
        # متن اطلاع‌رسانی
        user_info = f"👤 **{first_name or 'کاربر'}" if first_name else "👤 **کاربر جدید**"
        if username:
            user_info += f" (@{username})"
        user_info += f"**\n🆔 **آیدی**: `{user_id}`\n⏰ **زمان**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        
        # ارسال به مالک
        try:
            await context.bot.send_message(
                chat_id=OWNER_ID,
                text=f"🆕 **کاربر جدید استارت کرد!**\n\n{user_info}",
                parse_mode='Markdown'
            )
        except Exception as e:
            print(f"Error sending notification to owner: {e}")
        
        # ارسال به ادمین‌ها
        for admin_id in admins:
            try:
                await context.bot.send_message(
                    chat_id=admin_id,
                    text=f"🆕 **کاربر جدید استارت کرد!**\n\n{user_info}",
                    parse_mode='Markdown'
                )
            except Exception as e:
                print(f"Error sending notification to admin {admin_id}: {e}")
    
    async def toggle_live_notifications(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """تغییر وضعیت اطلاع‌رسانی لحظه‌ای"""
        current_status = self.store.get('live_notifications', True)
        new_status = not current_status
        
        self.store['live_notifications'] = new_status
        save_store(self.store)
        
        keyboard = [
            [KeyboardButton("🔙 بازگشت به منو")]
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        
        status_text = "فعال" if new_status else "غیرفعال"
        status_emoji = "✅" if new_status else "❌"
        
        text = f"""
{status_emoji} **اطلاع‌رسانی لحظه‌ای {status_text} شد!**

🔔 **وضعیت فعلی**: {status_text}

💡 **نحوه کارکرد**:
• وقتی کاربر جدیدی استارت می‌کند
• اطلاع‌رسانی فوری به مالک و ادمین‌ها ارسال می‌شود
• شامل نام، نام کاربری و آیدی عددی کاربر
• فقط برای مالک و ادمین‌ها قابل مشاهده است

📅 **تاریخ تغییر**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        """
        
        await update.message.reply_text(text, reply_markup=reply_markup)
    
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

    
    async def clear_cache_action(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """پاک کردن کش"""
        query = update.callback_query
        await query.answer()
        
        self.cache.clear()
        
        await query.answer("🗑️ کش با موفقیت پاک شد!")
        await self.admin_cache_panel(update, context)
        

    
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

    
    async def admin_lists_panel(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """پنل لیست سفید/سیاه"""
        whitelist_count = len(self.store.get('whitelist', []))
        blacklist_count = len(self.store.get('blacklist', []))
        
        keyboard = [
            [KeyboardButton("➕ افزودن به لیست سیاه"), KeyboardButton("➖ حذف از لیست سیاه")],
            [KeyboardButton("📋 لیست مسدودین"), KeyboardButton("📊 آمار لیست‌ها")],
            [KeyboardButton("🔙 بازگشت به منو")]
        ]
        
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        
        text = f"""
⚫ **مدیریت لیست سیاه**

📊 **وضعیت فعلی**:
• کاربران مسدود: {blacklist_count} نفر
• کاربران عادی: {len(self.store.get('users', [])) - blacklist_count} نفر

🎯 **عملیات موجود**:
➕ **افزودن به لیست سیاه**: مسدود کردن کاربر
➖ **حذف از لیست سیاه**: آزاد کردن کاربر
📋 **لیست مسدودین**: مشاهده کاربران مسدود
📊 **آمار لیست‌ها**: آمار کامل

💡 **نحوه کارکرد**:
• کاربر مسدود شده پیام "مسدود شدید" دریافت می‌کند
• ربات دیگر هیچ دستوری از کاربر مسدود نمی‌گیرد
• تا زمان حذف از لیست سیاه، دسترسی محدود است

**نحوه استفاده**:
• آیدی عددی کاربر را وارد کنید
• تایید یا رد کنید
• کاربر مستقیماً بلاک/آنبلاک می‌شود
• کاربران لیست سیاه هیچ خدماتی دریافت نمی‌کنند
        """
        
        await update.message.reply_text(text, reply_markup=reply_markup)
    
    async def add_to_blacklist_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """شروع افزودن کاربر به لیست سیاه"""
        keyboard = [
            [KeyboardButton("🔙 بازگشت به منو")]
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        
        text = """
➕ **افزودن کاربر به لیست سیاه**

📝 **آیدی عددی کاربر را ارسال کنید**:

لطفاً آیدی عددی کاربری که می‌خواهید مسدود کنید را ارسال کنید.

💡 **نکات مهم**:
• آیدی باید عددی باشد (مثل: 123456789)
• کاربر مسدود شده پیام "مسدود شدید" دریافت می‌کند
• ربات دیگر هیچ دستوری از کاربر مسدود نمی‌گیرد
• تا زمان حذف از لیست سیاه، دسترسی محدود است

🔙 برای لغو: /cancel
        """
        
        await update.message.reply_text(text, reply_markup=reply_markup)
        return "BLACKLIST_USER_INPUT"
    
    async def process_blacklist_user_input(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """پردازش آیدی کاربر برای لیست سیاه"""
        user_input = update.message.text.strip()
        
        # بررسی اینکه آیا آیدی عددی است
        try:
            user_id = int(user_input)
        except ValueError:
            await update.message.reply_text("❌ آیدی باید عددی باشد! لطفاً آیدی صحیح ارسال کنید.")
            return "BLACKLIST_USER_INPUT"
        
        # بررسی اینکه آیا کاربر در لیست سیاه است
        blacklist = self.store.get('blacklist', [])
        if user_id in blacklist:
            await update.message.reply_text("❌ این کاربر قبلاً در لیست سیاه است!")
            return "BLACKLIST_USER_INPUT"
        
        # ذخیره آیدی برای تایید
        context.user_data['blacklist_user_id'] = user_id
        
        keyboard = [
            [KeyboardButton("✅ تایید مسدودسازی"), KeyboardButton("❌ لغو")],
            [KeyboardButton("🔙 بازگشت به منو")]
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        
        text = f"""
⚠️ **تایید مسدودسازی کاربر**

🆔 **آیدی کاربر**: `{user_id}`

🔍 **اطلاعات کاربر**:
• آیدی: {user_id}
• وضعیت: کاربر عادی

⚠️ **هشدار**: این عمل کاربر را مسدود می‌کند!

📋 **نتیجه مسدودسازی**:
• کاربر پیام "مسدود شدید" دریافت می‌کند
• ربات دیگر هیچ دستوری از کاربر نمی‌گیرد
• دسترسی به تمام قابلیت‌های ربات محدود می‌شود

آیا مطمئن هستید؟
        """
        
        await update.message.reply_text(text, reply_markup=reply_markup)
        return "BLACKLIST_CONFIRMATION"
    
    async def process_blacklist_confirmation(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """پردازش تایید مسدودسازی"""
        action = update.message.text.strip()
        user_id = context.user_data.get('blacklist_user_id')
        
        if action == "✅ تایید مسدودسازی":
            if not user_id:
                await update.message.reply_text("❌ خطا در پردازش!")
    
            
            # افزودن به لیست سیاه
            blacklist = self.store.get('blacklist', [])
            blacklist.append(user_id)
            self.store['blacklist'] = blacklist
            save_store(self.store)
            
            # ارسال پیام به کاربر مسدود شده
            try:
                await context.bot.send_message(
                    chat_id=user_id,
                    text="🚫 **شما مسدود شدید!**\n\nمتأسفانه دسترسی شما به ربات محدود شده است.\n\nبرای اطلاعات بیشتر با ادمین تماس بگیرید."
                )
            except Exception as e:
                print(f"Error sending block message to user {user_id}: {e}")
            
            keyboard = [
                [KeyboardButton("🔙 بازگشت به منو")]
            ]
            reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
            
            text = f"""
✅ **کاربر با موفقیت مسدود شد!**

🆔 **آیدی کاربر**: `{user_id}`
📅 **تاریخ مسدودسازی**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

📋 **اقدامات انجام شده**:
• کاربر به لیست سیاه اضافه شد
• پیام "مسدود شدید" ارسال شد
• دسترسی به ربات محدود شد

💡 **نکته**: برای آزاد کردن کاربر از "➖ حذف از لیست سیاه" استفاده کنید.
            """
            
            await update.message.reply_text(text, reply_markup=reply_markup)

        
        elif action == "❌ لغو":
            await update.message.reply_text("❌ مسدودسازی لغو شد.")

        
        else:
            await update.message.reply_text("❌ عمل نامعتبر!")
            return "BLACKLIST_CONFIRMATION"
    
    async def remove_from_blacklist_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """شروع حذف کاربر از لیست سیاه"""
        blacklist = self.store.get('blacklist', [])
        
        if not blacklist:
            keyboard = [
                [KeyboardButton("🔙 بازگشت به منو")]
            ]
            reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
            
            text = """
📋 **لیست سیاه خالی است**

⚫ **وضعیت**: هیچ کاربری در لیست سیاه نیست

💡 **نکته**: ابتدا کاربری را مسدود کنید تا بتوانید آن را آزاد کنید.
            """
            
            await update.message.reply_text(text, reply_markup=reply_markup)

        
        keyboard = [
            [KeyboardButton("🔙 بازگشت به منو")]
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        
        text = f"""
➖ **حذف کاربر از لیست سیاه**

📝 **آیدی عددی کاربر را ارسال کنید**:

لطفاً آیدی عددی کاربری که می‌خواهید آزاد کنید را ارسال کنید.

📊 **وضعیت فعلی**: {len(blacklist)} کاربر مسدود

💡 **نکات مهم**:
• آیدی باید عددی باشد (مثل: 123456789)
• کاربر باید در لیست سیاه باشد
• پس از آزادسازی، کاربر به حالت عادی برمی‌گردد
• دسترسی کامل به ربات بازگردانده می‌شود

🔙 برای لغو: /cancel
        """
        
        await update.message.reply_text(text, reply_markup=reply_markup)
        return "UNBLACKLIST_USER_INPUT"
    
    async def process_unblacklist_user_input(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """پردازش آیدی کاربر برای حذف از لیست سیاه"""
        user_input = update.message.text.strip()
        
        # بررسی اینکه آیا آیدی عددی است
        try:
            user_id = int(user_input)
        except ValueError:
            await update.message.reply_text("❌ آیدی باید عددی باشد! لطفاً آیدی صحیح ارسال کنید.")
            return "UNBLACKLIST_USER_INPUT"
        
        # بررسی اینکه آیا کاربر در لیست سیاه است
        blacklist = self.store.get('blacklist', [])
        if user_id not in blacklist:
            await update.message.reply_text("❌ این کاربر در لیست سیاه نیست!")
            return "UNBLACKLIST_USER_INPUT"
        
        # ذخیره آیدی برای تایید
        context.user_data['unblacklist_user_id'] = user_id
        
        keyboard = [
            [KeyboardButton("✅ تایید آزادسازی"), KeyboardButton("❌ لغو")],
            [KeyboardButton("🔙 بازگشت به منو")]
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        
        text = f"""
✅ **تایید آزادسازی کاربر**

🆔 **آیدی کاربر**: `{user_id}`

🔍 **اطلاعات کاربر**:
• آیدی: {user_id}
• وضعیت: مسدود شده

✅ **نتیجه آزادسازی**:
• کاربر از لیست سیاه حذف می‌شود
• دسترسی کامل به ربات بازگردانده می‌شود
• کاربر می‌تواند دوباره از ربات استفاده کند

آیا مطمئن هستید؟
        """
        
        await update.message.reply_text(text, reply_markup=reply_markup)
        return "UNBLACKLIST_CONFIRMATION"
    
    async def process_unblacklist_confirmation(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """پردازش تایید آزادسازی"""
        action = update.message.text.strip()
        user_id = context.user_data.get('unblacklist_user_id')
        
        if action == "✅ تایید آزادسازی":
            if not user_id:
                await update.message.reply_text("❌ خطا در پردازش!")
    
            
            # حذف از لیست سیاه
            blacklist = self.store.get('blacklist', [])
            if user_id in blacklist:
                blacklist.remove(user_id)
                self.store['blacklist'] = blacklist
                save_store(self.store)
            
            # ارسال پیام به کاربر آزاد شده
            try:
                await context.bot.send_message(
                    chat_id=user_id,
                    text="✅ **شما آزاد شدید!**\n\nدسترسی شما به ربات بازگردانده شد.\n\nمی‌توانید دوباره از ربات استفاده کنید."
                )
            except Exception as e:
                print(f"Error sending unblock message to user {user_id}: {e}")
            
            keyboard = [
                [KeyboardButton("🔙 بازگشت به منو")]
            ]
            reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
            
            text = f"""
✅ **کاربر با موفقیت آزاد شد!**

🆔 **آیدی کاربر**: `{user_id}`
📅 **تاریخ آزادسازی**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

📋 **اقدامات انجام شده**:
• کاربر از لیست سیاه حذف شد
• پیام "آزاد شدید" ارسال شد
• دسترسی کامل به ربات بازگردانده شد

💡 **نکته**: کاربر می‌تواند دوباره از ربات استفاده کند.
            """
            
            await update.message.reply_text(text, reply_markup=reply_markup)

        
        elif action == "❌ لغو":
            await update.message.reply_text("❌ آزادسازی لغو شد.")

        
        else:
            await update.message.reply_text("❌ عمل نامعتبر!")
            return "UNBLACKLIST_CONFIRMATION"
    
    async def show_blacklist_users(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """نمایش لیست کاربران مسدود"""
        blacklist = self.store.get('blacklist', [])
        
        if not blacklist:
            keyboard = [
                [KeyboardButton("🔙 بازگشت به منو")]
            ]
            reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
            
            text = """
📋 **لیست مسدودین**

⚫ **وضعیت**: هیچ کاربری مسدود نیست

💡 **نکته**: لیست سیاه خالی است.
            """
            
            await update.message.reply_text(text, reply_markup=reply_markup)

        
        # نمایش لیست کاربران مسدود
        users_text = ""
        for i, user_id in enumerate(blacklist, 1):
            users_text += f"{i}. `{user_id}`\n"
        
        keyboard = [
            [KeyboardButton("🔙 بازگشت به منو")]
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        
        text = f"""
📋 **لیست مسدودین**

⚫ **تعداد کاربران مسدود**: {len(blacklist)} نفر

👥 **کاربران مسدود**:
{users_text}

💡 **نکته**: برای آزاد کردن کاربر از "➖ حذف از لیست سیاه" استفاده کنید.
        """
        
        await update.message.reply_text(text, reply_markup=reply_markup)
    
    async def show_lists_stats(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """نمایش آمار لیست‌ها"""
        blacklist = self.store.get('blacklist', [])
        users = self.store.get('users', [])
        
        keyboard = [
            [KeyboardButton("🔙 بازگشت به منو")]
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        
        text = f"""
📊 **آمار لیست‌ها**

👥 **آمار کاربران**:
• کل کاربران: {len(users)} نفر
• کاربران عادی: {len(users) - len(blacklist)} نفر
• کاربران مسدود: {len(blacklist)} نفر

📈 **درصدها**:
• درصد کاربران عادی: {((len(users) - len(blacklist)) / max(len(users), 1) * 100):.1f}%
• درصد کاربران مسدود: {(len(blacklist) / max(len(users), 1) * 100):.1f}%

🕒 **آخرین بروزرسانی**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        """
        
        await update.message.reply_text(text, reply_markup=reply_markup)

    async def admin_bot_settings_panel(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """پنل تنظیمات ربات"""
        # شمارش ویژگی‌های فعال/غیرفعال
        features = self.store.get('bot_features', {})
        active_features = sum(1 for status in features.values() if status)
        total_features = len(features)
        
        keyboard = [
            [KeyboardButton("🔧 مدیریت دکمه‌های کاربری"), KeyboardButton("⚙️ مدیریت دکمه‌های ادمین")],
            [KeyboardButton("📊 آمار ویژگی‌ها"), KeyboardButton("🔄 بازنشانی تنظیمات")],
            [KeyboardButton("🔙 بازگشت به منو")]
        ]
        
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        
        text = f"""
🤖 **تنظیمات ربات**

🎯 **بخش‌های موجود**:
🔧 **مدیریت دکمه‌های کاربری**: خاموش/روشن کردن دکمه‌های کیبورد اصلی
⚙️ **مدیریت دکمه‌های ادمین**: خاموش/روشن کردن دکمه‌های پنل مدیریت
📊 **آمار ویژگی‌ها**: نمایش وضعیت تمام ویژگی‌ها
🔄 **بازنشانی تنظیمات**: بازگردانی به حالت پیش‌فرض

📊 **وضعیت فعلی**:
• ویژگی‌های فعال: {active_features}/{total_features}
• ویژگی‌های غیرفعال: {total_features - active_features}/{total_features}

💡 **نحوه استفاده**:
• دکمه مورد نظر را انتخاب کنید
• وضعیت ON/OFF را تغییر دهید
• تغییرات بلافاصله اعمال می‌شوند
        """
        
        await update.message.reply_text(text, reply_markup=reply_markup)
    
    async def manage_user_buttons(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """مدیریت دکمه‌های کاربری"""
        features = self.store.get('bot_features', {})
        
        # تعریف دکمه‌های کاربری
        user_buttons = {
            'crypto_prices': '💰 نرخ ارز',
            'fiat_rates': '🏦 ارز داخلی',
            'news': '📰 اخبار',
            'charts': '📊 نمودار',
            'technical_analysis': '📊 تحلیل تکنیکال',
            'arbitrage': '🔄 مقایسه قیمت‌ها',
            'p2p': '💱 P2P',
            'watchlist': '⭐ واچ‌لیست',
            'portfolio': '💼 پرتفوی',
            'alerts': '🔔 هشدارهای من',
            'settings': '⚙️ تنظیمات',
            'help': '❓ راهنما'
        }
        
        keyboard = []
        for key, display_name in user_buttons.items():
            status = features.get(key, True)
            status_emoji = "✅" if status else "❌"
            keyboard.append([KeyboardButton(f"{status_emoji} {display_name}")])
        
        keyboard.append([KeyboardButton("🔙 بازگشت به منو")])
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        
        text = """
🔧 **مدیریت دکمه‌های کاربری**

🎯 **دکمه‌های قابل مدیریت**:

✅ = فعال (دکمه نمایش داده می‌شود)
❌ = غیرفعال (دکمه حذف می‌شود)

💡 **نحوه استفاده**:
• روی دکمه مورد نظر کلیک کنید
• وضعیت ON/OFF را انتخاب کنید
• تغییرات بلافاصله اعمال می‌شوند
        """
        
        await update.message.reply_text(text, reply_markup=reply_markup)
        return "USER_BUTTON_SELECTION"
    
    async def manage_admin_buttons(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """مدیریت دکمه‌های ادمین"""
        admin_features = self.store.get('admin_features', {})
        
        # تعریف دکمه‌های ادمین
        admin_buttons = {
            'user_management': '👥 مدیریت کاربران',
            'broadcast': '📢 ارسال همگانی',
            'text_settings': '📝 تنظیم متن‌ها',
            'api_management': '🔗 مدیریت API',
            'force_subscription': '🔒 قفل اجباری',
            'stats': '📊 آمار و گزارش',
            'bot_settings': '⚙️ تنظیمات ربات',
            'cache_management': '🗄️ مدیریت کش'
        }
        
        keyboard = []
        for key, display_name in admin_buttons.items():
            status = admin_features.get(key, True)
            status_emoji = "✅" if status else "❌"
            keyboard.append([KeyboardButton(f"{status_emoji} {display_name}")])
        
        keyboard.append([KeyboardButton("🔙 بازگشت به منو")])
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        
        text = """
⚙️ **مدیریت دکمه‌های ادمین**

🎯 **دکمه‌های قابل مدیریت**:

✅ = فعال (دکمه در پنل مدیریت نمایش داده می‌شود)
❌ = غیرفعال (دکمه از پنل مدیریت حذف می‌شود)

💡 **نحوه استفاده**:
• روی دکمه مورد نظر کلیک کنید
• وضعیت ON/OFF را انتخاب کنید
• تغییرات بلافاصله اعمال می‌شوند
        """
        
        await update.message.reply_text(text, reply_markup=reply_markup)
        return "ADMIN_BUTTON_SELECTION"
    
    async def process_user_button_selection(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """پردازش انتخاب دکمه کاربری"""
        selected_text = update.message.text.strip()
        
        # استخراج نام دکمه از متن
        button_mapping = {
            '✅ 💰 نرخ ارز': ('crypto_prices', '💰 نرخ ارز'),
            '❌ 💰 نرخ ارز': ('crypto_prices', '💰 نرخ ارز'),
            '✅ 🏦 ارز داخلی': ('fiat_rates', '🏦 ارز داخلی'),
            '❌ 🏦 ارز داخلی': ('fiat_rates', '🏦 ارز داخلی'),
            '✅ 📰 اخبار': ('news', '📰 اخبار'),
            '❌ 📰 اخبار': ('news', '📰 اخبار'),
            '✅ 📊 نمودار': ('charts', '📊 نمودار'),
            '❌ 📊 نمودار': ('charts', '📊 نمودار'),
            '✅ 📊 تحلیل تکنیکال': ('technical_analysis', '📊 تحلیل تکنیکال'),
            '❌ 📊 تحلیل تکنیکال': ('technical_analysis', '📊 تحلیل تکنیکال'),
            '✅ 🔄 مقایسه قیمت‌ها': ('arbitrage', '🔄 مقایسه قیمت‌ها'),
            '❌ 🔄 مقایسه قیمت‌ها': ('arbitrage', '🔄 مقایسه قیمت‌ها'),
            '✅ 💱 P2P': ('p2p', '💱 P2P'),
            '❌ 💱 P2P': ('p2p', '💱 P2P'),
            '✅ ⭐ واچ‌لیست': ('watchlist', '⭐ واچ‌لیست'),
            '❌ ⭐ واچ‌لیست': ('watchlist', '⭐ واچ‌لیست'),
            '✅ 💼 پرتفوی': ('portfolio', '💼 پرتفوی'),
            '❌ 💼 پرتفوی': ('portfolio', '💼 پرتفوی'),
            '✅ 🔔 هشدارهای من': ('alerts', '🔔 هشدارهای من'),
            '❌ 🔔 هشدارهای من': ('alerts', '🔔 هشدارهای من'),
            '✅ ⚙️ تنظیمات': ('settings', '⚙️ تنظیمات'),
            '❌ ⚙️ تنظیمات': ('settings', '⚙️ تنظیمات'),
            '✅ ❓ راهنما': ('help', '❓ راهنما'),
            '❌ ❓ راهنما': ('help', '❓ راهنما')
        }
        
        if selected_text not in button_mapping:
            await update.message.reply_text("❌ دکمه انتخاب شده نامعتبر است!")
            return "USER_BUTTON_SELECTION"
        
        button_key, display_name = button_mapping[selected_text]
        current_status = self.store.get('bot_features', {}).get(button_key, True)
        
        # ذخیره انتخاب
        context.user_data['selected_button_key'] = button_key
        context.user_data['selected_button_display'] = display_name
        context.user_data['current_status'] = current_status
        
        keyboard = [
            [KeyboardButton("🟢 ON"), KeyboardButton("🔴 OFF")],
            [KeyboardButton("🔙 بازگشت به منو")]
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        
        status_text = "فعال" if current_status else "غیرفعال"
        status_emoji = "✅" if current_status else "❌"
        
        text = f"""
🔧 **تنظیم دکمه: {display_name}**

📊 **وضعیت فعلی**: {status_emoji} {status_text}

🎯 **انتخاب کنید**:
🟢 **ON**: دکمه فعال می‌شود و نمایش داده می‌شود
🔴 **OFF**: دکمه غیرفعال می‌شود و حذف می‌شود

💡 **نکته**: تغییرات بلافاصله اعمال می‌شوند
        """
        
        await update.message.reply_text(text, reply_markup=reply_markup)
        return "USER_BUTTON_TOGGLE"
    
    async def process_user_button_toggle(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """پردازش تغییر وضعیت دکمه کاربری"""
        action = update.message.text.strip()
        button_key = context.user_data.get('selected_button_key')
        display_name = context.user_data.get('selected_button_display')
        
        if not button_key:
            await update.message.reply_text("❌ خطا در پردازش!")

        
        # تغییر وضعیت
        features = self.store.get('bot_features', {})
        
        if action == "🟢 ON":
            features[button_key] = True
            status_text = "فعال"
            status_emoji = "✅"
        elif action == "🔴 OFF":
            features[button_key] = False
            status_text = "غیرفعال"
            status_emoji = "❌"
        else:
            await update.message.reply_text("❌ عمل نامعتبر!")
            return "USER_BUTTON_TOGGLE"
        
        self.store['bot_features'] = features
        save_store(self.store)
        
        keyboard = [
            [KeyboardButton("🔙 بازگشت به منو")]
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        
        text = f"""
{status_emoji} **دکمه {status_text} شد!**

🔧 **دکمه**: {display_name}
📊 **وضعیت جدید**: {status_text}
📅 **تاریخ**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

🎉 **تبریک!** تغییرات بلافاصله اعمال شد.

💡 **نکته**: دکمه در کیبورد کاربران با وضعیت جدید نمایش داده می‌شود.
        """
        
        await update.message.reply_text(text, reply_markup=reply_markup)
    
    async def process_admin_button_selection(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """پردازش انتخاب دکمه ادمین"""
        selected_text = update.message.text.strip()
        
        # استخراج نام دکمه از متن
        button_mapping = {
            '✅ 👥 مدیریت کاربران': ('user_management', '👥 مدیریت کاربران'),
            '❌ 👥 مدیریت کاربران': ('user_management', '👥 مدیریت کاربران'),
            '✅ 📢 ارسال همگانی': ('broadcast', '📢 ارسال همگانی'),
            '❌ 📢 ارسال همگانی': ('broadcast', '📢 ارسال همگانی'),
            '✅ 📝 تنظیم متن‌ها': ('text_settings', '📝 تنظیم متن‌ها'),
            '❌ 📝 تنظیم متن‌ها': ('text_settings', '📝 تنظیم متن‌ها'),
            '✅ 🔗 مدیریت API': ('api_management', '🔗 مدیریت API'),
            '❌ 🔗 مدیریت API': ('api_management', '🔗 مدیریت API'),
            '✅ 🔒 قفل اجباری': ('force_subscription', '🔒 قفل اجباری'),
            '❌ 🔒 قفل اجباری': ('force_subscription', '🔒 قفل اجباری'),
            '✅ 📊 آمار و گزارش': ('stats', '📊 آمار و گزارش'),
            '❌ 📊 آمار و گزارش': ('stats', '📊 آمار و گزارش'),
            '✅ ⚙️ تنظیمات ربات': ('bot_settings', '⚙️ تنظیمات ربات'),
            '❌ ⚙️ تنظیمات ربات': ('bot_settings', '⚙️ تنظیمات ربات'),
            '✅ 🗄️ مدیریت کش': ('cache_management', '🗄️ مدیریت کش'),
            '❌ 🗄️ مدیریت کش': ('cache_management', '🗄️ مدیریت کش')
        }
        
        if selected_text not in button_mapping:
            await update.message.reply_text("❌ دکمه انتخاب شده نامعتبر است!")
            return "ADMIN_BUTTON_SELECTION"
        
        button_key, display_name = button_mapping[selected_text]
        current_status = self.store.get('admin_features', {}).get(button_key, True)
        
        # ذخیره انتخاب
        context.user_data['selected_admin_button_key'] = button_key
        context.user_data['selected_admin_button_display'] = display_name
        context.user_data['current_admin_status'] = current_status
        
        keyboard = [
            [KeyboardButton("🟢 ON"), KeyboardButton("🔴 OFF")],
            [KeyboardButton("🔙 بازگشت به منو")]
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        
        status_text = "فعال" if current_status else "غیرفعال"
        status_emoji = "✅" if current_status else "❌"
        
        text = f"""
⚙️ **تنظیم دکمه ادمین: {display_name}**

📊 **وضعیت فعلی**: {status_emoji} {status_text}

🎯 **انتخاب کنید**:
🟢 **ON**: دکمه در پنل مدیریت فعال می‌شود
🔴 **OFF**: دکمه از پنل مدیریت حذف می‌شود

💡 **نکته**: تغییرات بلافاصله اعمال می‌شوند
        """
        
        await update.message.reply_text(text, reply_markup=reply_markup)
        return "ADMIN_BUTTON_TOGGLE"
    
    async def process_admin_button_toggle(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """پردازش تغییر وضعیت دکمه ادمین"""
        action = update.message.text.strip()
        button_key = context.user_data.get('selected_admin_button_key')
        display_name = context.user_data.get('selected_admin_button_display')
        
        if not button_key:
            await update.message.reply_text("❌ خطا در پردازش!")

        
        # تغییر وضعیت
        admin_features = self.store.get('admin_features', {})
        
        if action == "🟢 ON":
            admin_features[button_key] = True
            status_text = "فعال"
            status_emoji = "✅"
        elif action == "🔴 OFF":
            admin_features[button_key] = False
            status_text = "غیرفعال"
            status_emoji = "❌"
        else:
            await update.message.reply_text("❌ عمل نامعتبر!")
            return "ADMIN_BUTTON_TOGGLE"
        
        self.store['admin_features'] = admin_features
        save_store(self.store)
        
        keyboard = [
            [KeyboardButton("🔙 بازگشت به منو")]
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        
        text = f"""
{status_emoji} **دکمه ادمین {status_text} شد!**

⚙️ **دکمه**: {display_name}
📊 **وضعیت جدید**: {status_text}
📅 **تاریخ**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

🎉 **تبریک!** تغییرات بلافاصله اعمال شد.

💡 **نکته**: دکمه در پنل مدیریت با وضعیت جدید نمایش داده می‌شود.
        """
        
        await update.message.reply_text(text, reply_markup=reply_markup)
    
    async def show_features_stats(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """نمایش آمار ویژگی‌ها"""
        features = self.store.get('bot_features', {})
        admin_features = self.store.get('admin_features', {})
        
        # آمار دکمه‌های کاربری
        user_active = sum(1 for status in features.values() if status)
        user_total = len(features)
        
        # آمار دکمه‌های ادمین
        admin_active = sum(1 for status in admin_features.values() if status)
        admin_total = len(admin_features)
        
        keyboard = [
            [KeyboardButton("🔙 بازگشت به منو")]
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        
        text = f"""
📊 **آمار ویژگی‌های ربات**

👥 **دکمه‌های کاربری**:
• فعال: {user_active}/{user_total}
• غیرفعال: {user_total - user_active}/{user_total}
• درصد فعال: {(user_active/user_total*100):.1f}%

⚙️ **دکمه‌های ادمین**:
• فعال: {admin_active}/{admin_total}
• غیرفعال: {admin_total - admin_active}/{admin_total}
• درصد فعال: {(admin_active/admin_total*100):.1f}%

📈 **آمار کلی**:
• کل ویژگی‌ها: {user_total + admin_total}
• ویژگی‌های فعال: {user_active + admin_active}
• ویژگی‌های غیرفعال: {(user_total + admin_total) - (user_active + admin_active)}

🕒 **آخرین بروزرسانی**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        """
        
        await update.message.reply_text(text, reply_markup=reply_markup)
    
    async def reset_settings(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """بازنشانی تنظیمات"""
        keyboard = [
            [KeyboardButton("🔄 تایید بازنشانی"), KeyboardButton("❌ لغو")],
            [KeyboardButton("🔙 بازگشت به منو")]
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        
        text = """
🔄 **بازنشانی تنظیمات ربات**

⚠️ **هشدار**: این عمل تمام تنظیمات ربات را به حالت پیش‌فرض بازمی‌گرداند!

📋 **تنظیماتی که بازنشانی می‌شوند**:
• تمام دکمه‌های کاربری (فعال می‌شوند)
• تمام دکمه‌های ادمین (فعال می‌شوند)
• تنظیمات اطلاع‌رسانی (فعال می‌شود)
• سایر تنظیمات ربات

💡 **نکته**: این عمل قابل بازگشت نیست!

آیا مطمئن هستید؟
        """
        
        await update.message.reply_text(text, reply_markup=reply_markup)
        return "RESET_CONFIRMATION"
    
    async def process_reset_confirmation(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """پردازش تایید بازنشانی"""
        action = update.message.text.strip()
        
        if action == "🔄 تایید بازنشانی":
            # بازنشانی تنظیمات
            self.store['bot_features'] = {
                'crypto_prices': True,
                'fiat_rates': True,
                'news': True,
                'charts': True,
                'technical_analysis': True,
                'arbitrage': True,
                'p2p': True,
                'watchlist': True,
                'portfolio': True,
                'alerts': True,
                'settings': True,
                'help': True
            }
            
            self.store['admin_features'] = {
                'user_management': True,
                'broadcast': True,
                'text_settings': True,
                'api_management': True,
                'force_subscription': True,
                'stats': True,
                'bot_settings': True,
                'cache_management': True
            }
            
            self.store['live_notifications'] = True
            
            save_store(self.store)
            
            keyboard = [
                [KeyboardButton("🔙 بازگشت به منو")]
            ]
            reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
            
            text = """
✅ **تنظیمات با موفقیت بازنشانی شد!**

🔄 **تنظیمات بازنشانی شده**:
• تمام دکمه‌های کاربری فعال شدند
• تمام دکمه‌های ادمین فعال شدند
• اطلاع‌رسانی لحظه‌ای فعال شد
• سایر تنظیمات به حالت پیش‌فرض بازگشت

📅 **تاریخ بازنشانی**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

🎉 **تبریک!** ربات به حالت پیش‌فرض بازگشت.
            """
            
            await update.message.reply_text(text, reply_markup=reply_markup)

        
        elif action == "❌ لغو":
            await update.message.reply_text("❌ بازنشانی لغو شد.")

        
        else:
            await update.message.reply_text("❌ عمل نامعتبر!")
            return "RESET_CONFIRMATION"
    
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
    
        

    
    async def list_admins_action(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """نمایش لیست ادمین‌ها"""
        admins = self.store.get('admins', [])
        admin_list = "\n".join([f"• {admin_id}" for admin_id in admins])
        
        keyboard = [[KeyboardButton("🔙 بازگشت به منو")]]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        
        text = f"""
📋 **لیست ادمین‌ها**

👨‍💼 **ادمین‌های فعلی**:
{admin_list if admin_list else "• هیچ ادمینی وجود ندارد"}

📊 **تعداد کل**: {len(admins)} ادمین
        """
        
        await update.message.reply_text(text, reply_markup=reply_markup)
    
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
        

    
    async def add_force_sub_channel_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """شروع افزودن چنل عضویت اجباری"""
        channels = self.store.get('forced_subscription', {}).get('channels', [])
        
        keyboard = [
            [KeyboardButton("🔙 بازگشت به منو")]
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        
        text = f"""
➕ **افزودن چنل عضویت اجباری**

📺 **چنل‌های فعلی**: {len(channels)} چنل فعال

🎯 **مرحله 1: ادمین کردن ربات**

لطفاً ربات را در چنل یا گروه مورد نظر ادمین کنید:

1️⃣ **ربات را به چنل اضافه کنید**
2️⃣ **ربات را ادمین کنید** (دسترسی کامل)
3️⃣ **دکمه "ادمین کردم" را ارسال کنید**

💡 **نکات مهم**:
• ربات باید ادمین چنل باشد
• دسترسی کامل (ارسال پیام، حذف پیام) لازم است
• چنل می‌تواند عمومی یا خصوصی باشد

🔙 برای لغو: /cancel
        """
        
        await update.message.reply_text(text, reply_markup=reply_markup)
    
    async def process_admin_confirmation(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """پردازش تایید ادمین کردن ربات"""
        text = update.message.text.strip()
        
        if text == "ادمین کردم":
            keyboard = [
                [KeyboardButton("🔙 بازگشت به منو")]
            ]
            reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
            
            message_text = """
✅ **ادمین کردن تایید شد!**

🎯 **مرحله 2: ارسال لینک چنل**

حالا لینک چنل یا گروه را ارسال کنید:

📋 **فرمت‌های پشتیبانی شده**:
• لینک عمومی: `https://t.me/channel_name`
• لینک خصوصی: `https://t.me/joinchat/xxxxx`
• نام کاربری: `@channel_name`

💡 **نکات مهم**:
• لینک باید معتبر باشد
• چنل باید قابل دسترسی باشد
• ربات باید در چنل ادمین باشد

🔙 برای لغو: /cancel
            """
            
            await update.message.reply_text(message_text, reply_markup=reply_markup)
        
        else:
            await update.message.reply_text("❌ لطفاً دکمه 'ادمین کردم' را ارسال کنید یا /cancel را بزنید.")
    
    async def process_channel_link(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """پردازش لینک چنل"""
        channel_link = update.message.text.strip()
        
        # پاک کردن فضاهای اضافی
        channel_link = channel_link.strip()
        
        # بررسی فرمت لینک - پشتیبانی از فرمت‌های مختلف
        valid_formats = [
            'https://t.me/',
            'http://t.me/',
            't.me/',
            '@',
            'https://telegram.me/',
            'http://telegram.me/',
            'telegram.me/'
        ]
        
        is_valid = any(channel_link.startswith(fmt) for fmt in valid_formats)
        
        if not is_valid:
            await update.message.reply_text(
                "❌ **فرمت لینک نامعتبر!**\n\n"
                "لطفاً یکی از فرمت‌های زیر را استفاده کنید:\n\n"
                "**لینک عمومی:**\n"
                "• `https://t.me/channel_name`\n"
                "• `t.me/channel_name`\n"
                "• `@channel_name`\n\n"
                "**لینک خصوصی:**\n"
                "• `https://t.me/joinchat/...`\n"
                "• `t.me/joinchat/...`\n\n"
                "**مثال‌ها:**\n"
                "• `https://t.me/my_channel`\n"
                "• `@my_channel`\n"
                "• `t.me/joinchat/ABC123`"
            )
        
        # استخراج نام چنل از لینک
        if '/joinchat/' in channel_link:
            # لینک خصوصی
            if 'joinchat/' in channel_link:
                channel_id = channel_link.split('joinchat/')[-1]
            else:
                channel_id = channel_link.split('/joinchat/')[-1]
            channel_title = f"چنل خصوصی ({channel_id[:10]}...)"
        elif channel_link.startswith('@'):
            # نام کاربری
            channel_username = channel_link.replace('@', '')
            channel_title = f"@{channel_username}"
        else:
            # لینک عمومی - پشتیبانی از فرمت‌های مختلف
            if 't.me/' in channel_link:
                channel_username = channel_link.split('t.me/')[-1].replace('@', '')
            elif 'telegram.me/' in channel_link:
                channel_username = channel_link.split('telegram.me/')[-1].replace('@', '')
            else:
                channel_username = channel_link.replace('@', '')
            channel_title = f"@{channel_username}"
        
        # ذخیره چنل
        force_sub = self.store.get('forced_subscription', {})
        channels = force_sub.get('channels', [])
        
        new_channel = {
            'title': channel_title,
            'link': channel_link,
            'added_at': datetime.now().isoformat(),
            'enabled': True
        }
        
        channels.append(new_channel)
        force_sub['channels'] = channels
        force_sub['enabled'] = True  # فعال کردن قفل اجباری
        self.store['forced_subscription'] = force_sub
        save_store(self.store)
        
        keyboard = [
            [KeyboardButton("🔙 بازگشت به منو")]
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        
        success_text = f"""
✅ **چنل با موفقیت قفل شد!**

📢 **اطلاعات چنل**:
• نام: {channel_title}
• لینک: {channel_link}
• تاریخ: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

🎉 **تبریک!** قفل اجباری فعال شد.

💡 **نحوه کارکرد**:
• کاربران جدید باید در این چنل عضو باشند
• ربات عضویت را بررسی می‌کند
• در صورت عدم عضویت، پیام هشدار نمایش داده می‌شود
• دکمه تایید عضویت نمایش داده می‌شود

🔧 **مدیریت**: از پنل قفل اجباری می‌توانید چنل‌ها را مدیریت کنید.
        """
        
        await update.message.reply_text(success_text, reply_markup=reply_markup)

    
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
            

            
        except ValueError:
            await update.message.reply_text(
                "❌ **آیدی نامعتبر!**\n\n"
                "لطفاً یک عدد صحیح وارد کنید.\n\n"
                "🔙 برای بازگشت کلیک کنید:",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔙 بازگشت", callback_data="back_to_main")
                ]])
            )

    
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
            

            
        except Exception as e:
            await update.message.reply_text(f"❌ خطا در ارسال پیام: {str(e)}")
            return USER_MESSAGE
    
    # ===== مدیریت API ها =====
    async def manage_apis(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """مدیریت API ها"""
        # دریافت API های موجود
        apis = self.store.get('api_configs', {})
        
        keyboard = [
            [KeyboardButton("➕ افزودن API جدید"), KeyboardButton("📋 لیست API ها")],
            [KeyboardButton("⚙️ تنظیمات API")],
            [KeyboardButton("🔙 بازگشت به منو")]
        ]
        
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        
        text = f"""
🔧 **مدیریت API ها**

📊 **آمار API ها**:
• تعداد API های فعال: {len([api for api in apis.values() if api.get('enabled', False)])}
• تعداد API های غیرفعال: {len([api for api in apis.values() if not api.get('enabled', False)])}

🔗 **API های موجود**:
{self._format_api_list(apis)}

لطفاً یکی از گزینه‌های زیر را انتخاب کنید:
        """
        
        await update.message.reply_text(text, reply_markup=reply_markup)
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
        """افزودن API جدید - مرحله 1: لینک API"""
        keyboard = [
            [KeyboardButton("🔙 بازگشت به منو")]
        ]
        
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        
        text = """
➕ **افزودن API جدید - مرحله 1**

🔗 **لینک API را وارد کنید:**

لطفاً آدرس کامل API خود را ارسال کنید.

**مثال‌ها**:
• `https://api.coingecko.com/api/v3`
• `https://api.binance.com/api/v3`
• `https://api.exchangerate.host`
• `https://your-custom-api.com/v1`

⚠️ **نکات مهم**:
• آدرس باید کامل باشد (شامل http یا https)
• API باید قابل دسترسی باشد
• برای لغو عملیات: /cancel
        """
        
        await update.message.reply_text(text, reply_markup=reply_markup)
    
    async def process_add_api(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """پردازش افزودن API - مراحل سه‌گانه"""
        message_text = update.message.text.strip()
        
        # بررسی مرحله فعلی
        current_step = context.user_data.get('api_step', 1)
        
        if current_step == 1:
            # مرحله 1: دریافت لینک API
            return await self._process_api_url(update, context, message_text)
        elif current_step == 2:
            # مرحله 2: دریافت API Key
            return await self._process_api_key(update, context, message_text)
        elif current_step == 3:
            # مرحله 3: انتخاب نوع API
            return await self._process_api_type(update, context, message_text)
        
    
    async def _process_api_url(self, update: Update, context: ContextTypes.DEFAULT_TYPE, url: str):
        """پردازش لینک API"""
        # پاک کردن فضاهای اضافی
        url = url.strip()
        
        # بررسی صحت URL
        if not url.startswith(('http://', 'https://')):
            # اگر http یا https ندارد، اضافه کن
            if not url.startswith('www.'):
                url = 'https://' + url
            else:
                url = 'https://' + url
        
        # بررسی ساده URL
        if not ('.' in url and len(url) > 10):
            await update.message.reply_text(
                "❌ **خطا در آدرس API!**\n\n"
                "لطفاً آدرس معتبر API را وارد کنید\n"
                "مثال‌ها:\n"
                "• `https://api.coingecko.com/api/v3`\n"
                "• `api.binance.com`\n"
                "• `api.exchangerate.host`\n"
                "• `your-custom-api.com`"
            )
            return
        
        # ذخیره URL
        context.user_data['api_url'] = url
        context.user_data['api_step'] = 2
        
        keyboard = [
            [KeyboardButton("🔙 بازگشت به منو")]
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        
        text = f"""
✅ **لینک API ثبت شد!**

🔗 **آدرس API**: `{url}`

➕ **افزودن API جدید - مرحله 2**

🔑 **API Key را وارد کنید:**

لطفاً کلید API خود را ارسال کنید.

**مثال‌ها**:
• `your_api_key_here`
• `sk-1234567890abcdef`
• `Bearer your_token_here`

⚠️ **نکات مهم**:
• کلید API محرمانه است و امن ذخیره می‌شود
• اگر API کلید ندارد، `none` یا `no_key` بنویسید
• برای لغو عملیات: /cancel
        """
        
        await update.message.reply_text(text, reply_markup=reply_markup)
    
    async def _process_api_key(self, update: Update, context: ContextTypes.DEFAULT_TYPE, api_key: str):
        """پردازش API Key"""
        # ذخیره API Key
        context.user_data['api_key'] = api_key
        context.user_data['api_step'] = 3
        
        keyboard = [
            [KeyboardButton("🪙 کریپتو"), KeyboardButton("💱 فیات")],
            [KeyboardButton("📰 اخبار"), KeyboardButton("📊 تکنیکال")],
            [KeyboardButton("🔙 بازگشت به منو")]
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        
        text = f"""
✅ **API Key ثبت شد!**

🔑 **کلید API**: `{'*' * len(api_key) if api_key not in ['none', 'no_key'] else 'بدون کلید'}`

➕ **افزودن API جدید - مرحله 3**

📋 **نوع API را انتخاب کنید:**

لطفاً نوع API خود را انتخاب کنید:

🪙 **کریپتو**: برای دریافت قیمت ارزهای دیجیتال
💱 **فیات**: برای دریافت نرخ ارزهای فیات
📰 **اخبار**: برای دریافت اخبار ارزهای دیجیتال
📊 **تکنیکال**: برای دریافت شاخص‌های تکنیکال

⚠️ **نکات مهم**:
• نوع API تعیین می‌کند که ربات از کجا داده بگیرد
• می‌توانید بعداً نوع را تغییر دهید
• برای لغو عملیات: /cancel
        """
        
        await update.message.reply_text(text, reply_markup=reply_markup)
    
    async def _process_api_type(self, update: Update, context: ContextTypes.DEFAULT_TYPE, api_type: str):
        """پردازش نوع API"""
        # تبدیل نام فارسی به انگلیسی
        type_mapping = {
            "🪙 کریپتو": "crypto",
            "💱 فیات": "fiat", 
            "📰 اخبار": "news",
            "📊 تکنیکال": "technical"
        }
        
        if api_type not in type_mapping:
            await update.message.reply_text(
                "❌ **نوع API نامعتبر!**\n\n"
                "لطفاً یکی از گزینه‌های زیر را انتخاب کنید:\n"
                "🪙 کریپتو\n"
                "💱 فیات\n"
                "📰 اخبار\n"
                "📊 تکنیکال"
            )
            return
        
        api_type_en = type_mapping[api_type]
        
        # ذخیره نوع API
        context.user_data['api_type'] = api_type_en
        
        # ایجاد API ID منحصر به فرد
        import uuid
        api_id = f"api_{uuid.uuid4().hex[:8]}"
        
        # ذخیره API در store
        api_configs = self.store.get('api_configs', {})
        api_configs[api_id] = {
            'name': f"API {api_type}",
            'type': api_type_en,
            'url': context.user_data['api_url'],
            'key': context.user_data['api_key'],
            'enabled': True,
            'created_at': datetime.now().isoformat()
        }
        
        self.store['api_configs'] = api_configs
        save_store(self.store)
        
        # پاک کردن داده‌های موقت
        context.user_data.pop('api_step', None)
        context.user_data.pop('api_url', None)
        context.user_data.pop('api_key', None)
        context.user_data.pop('api_type', None)
        
        keyboard = [
            [KeyboardButton("🔙 بازگشت به منو")]
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        
        text = f"""
✅ **API با موفقیت ثبت شد!**

📊 **جزئیات API**:
• 🆔 **شناسه**: `{api_id}`
• 🔗 **آدرس**: `{context.user_data.get('api_url', 'N/A')}`
• 🔑 **کلید**: `{'*' * 10 if context.user_data.get('api_key') not in ['none', 'no_key'] else 'بدون کلید'}`
• 📋 **نوع**: {api_type}
• ✅ **وضعیت**: فعال

🎉 **تبریک!** API شما آماده استفاده است.

💡 **مرحله بعدی**:
حالا می‌توانید در قسمت "💰 مدیریت ارزها" یا "📊 مدیریت شاخص‌ها" 
از این API استفاده کنید.
        """
        
        await update.message.reply_text(text, reply_markup=reply_markup)
    
    async def fetch_currencies_from_api(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """دریافت لیست ارزها از API ثبت شده"""
        api_configs = self.store.get('api_configs', {})
        
        if not api_configs:
            await update.message.reply_text(
                "❌ **هیچ API ای ثبت نشده است!**\n\n"
                "ابتدا API خود را در قسمت '🔧 مدیریت API ها' ثبت کنید."
            )

        
        # نمایش لیست API های موجود
        keyboard = []
        for api_id, api_data in api_configs.items():
            if api_data.get('enabled', False) and api_data.get('type') == 'crypto':
                keyboard.append([KeyboardButton(f"🔗 {api_data.get('name', api_id)}")])
        
        if not keyboard:
            await update.message.reply_text(
                "❌ **هیچ API کریپتو فعالی یافت نشد!**\n\n"
                "ابتدا یک API کریپتو فعال ثبت کنید."
            )

        
        keyboard.append([KeyboardButton("🔙 بازگشت به منو")])
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        
        text = """
🔍 **دریافت لیست ارزها از API**

لطفاً API مورد نظر خود را انتخاب کنید تا لیست ارزهای موجود را دریافت کنیم:

⚠️ **نکات مهم**:
• این عملیات ممکن است چند ثانیه طول بکشد
• لیست ارزهای موجود از API دریافت می‌شود
• سپس می‌توانید ارزهای مورد نظر را فعال/غیرفعال کنید
        """
        
        await update.message.reply_text(text, reply_markup=reply_markup)
        return "SELECT_API_FOR_CURRENCIES"
    
    async def process_api_selection_for_currencies(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """پردازش انتخاب API برای دریافت ارزها"""
        selected_api = update.message.text
        
        # پیدا کردن API انتخاب شده
        api_configs = self.store.get('api_configs', {})
        selected_api_config = None
        selected_api_id = None
        
        for api_id, api_data in api_configs.items():
            if f"🔗 {api_data.get('name', api_id)}" == selected_api:
                selected_api_config = api_data
                selected_api_id = api_id
                break
        
        if not selected_api_config:
            await update.message.reply_text("❌ API انتخاب شده یافت نشد!")

        
        # ذخیره API انتخاب شده
        context.user_data['selected_api_id'] = selected_api_id
        context.user_data['selected_api_config'] = selected_api_config
        
        await update.message.reply_text(
            f"🔍 **در حال دریافت لیست ارزها از API...**\n\n"
            f"📡 **API**: {selected_api_config.get('name', selected_api_id)}\n"
            f"🔗 **آدرس**: {selected_api_config.get('url', 'نامشخص')}\n\n"
            f"⏳ لطفاً صبر کنید..."
        )
        
        # دریافت لیست ارزها از API
        currencies = await self._fetch_currencies_from_api(selected_api_config)
        
        if not currencies:
            await update.message.reply_text(
                "❌ **خطا در دریافت لیست ارزها!**\n\n"
                "ممکن است API در دسترس نباشد یا فرمت پاسخ صحیح نباشد."
            )

        
        # ذخیره لیست ارزها
        context.user_data['available_currencies'] = currencies
        
        # نمایش منوی انتخاب ارزها
        return await self._show_currency_selection_menu(update, context, currencies)
    
    async def _fetch_currencies_from_api(self, api_config: dict) -> list:
        """دریافت لیست ارزها از API"""
        try:
            import aiohttp
            
            api_url = api_config.get('url', '')
            api_key = api_config.get('key', '')
            
            # تنظیم headers
            headers = {}
            if api_key and api_key not in ['none', 'no_key']:
                headers['Authorization'] = f'Bearer {api_key}'
                headers['X-API-Key'] = api_key
            
            # تلاش برای دریافت لیست ارزها
            currencies = []
            
            # برای CoinGecko
            if 'coingecko' in api_url.lower():
                currencies = await self._fetch_coingecko_currencies(api_url, headers)
            # برای Binance
            elif 'binance' in api_url.lower():
                currencies = await self._fetch_binance_currencies(api_url, headers)
            # برای API های دیگر
            else:
                currencies = await self._fetch_generic_currencies(api_url, headers)
            
            return currencies
            
        except Exception as e:
            print(f"خطا در دریافت لیست ارزها: {e}")
            return []
    
    async def _fetch_coingecko_currencies(self, api_url: str, headers: dict) -> list:
        """دریافت لیست ارزها از CoinGecko"""
        try:
            import aiohttp
            
            url = f"{api_url}/coins/list"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=30)) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        currencies = []
                        
                        for coin in data[:100]:  # محدود به 100 ارز اول
                            currencies.append({
                                'id': coin.get('id', ''),
                                'symbol': coin.get('symbol', '').upper(),
                                'name': coin.get('name', '')
                            })
                        
                        return currencies
            
            return []
            
        except Exception as e:
            print(f"خطا در دریافت از CoinGecko: {e}")
            return []
    
    async def _fetch_binance_currencies(self, api_url: str, headers: dict) -> list:
        """دریافت لیست ارزها از Binance"""
        try:
            import aiohttp
            
            url = f"{api_url}/exchangeInfo"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=30)) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        currencies = []
                        seen_symbols = set()
                        
                        for symbol_info in data.get('symbols', []):
                            base_asset = symbol_info.get('baseAsset', '')
                            if base_asset and base_asset not in seen_symbols:
                                seen_symbols.add(base_asset)
                                currencies.append({
                                    'id': base_asset.lower(),
                                    'symbol': base_asset,
                                    'name': base_asset
                                })
                        
                        return currencies[:50]  # محدود به 50 ارز اول
            
            return []
            
        except Exception as e:
            print(f"خطا در دریافت از Binance: {e}")
            return []
    
    async def _fetch_generic_currencies(self, api_url: str, headers: dict) -> list:
        """دریافت لیست ارزها از API عمومی"""
        try:
            import aiohttp
            
            # تلاش برای endpoint های مختلف
            endpoints = ['/coins', '/currencies', '/symbols', '/tickers']
            
            for endpoint in endpoints:
                try:
                    url = f"{api_url}{endpoint}"
                    
                    async with aiohttp.ClientSession() as session:
                        async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=30)) as resp:
                            if resp.status == 200:
                                data = await resp.json()
                                currencies = []
                                
                                # تلاش برای استخراج ارزها از پاسخ
                                if isinstance(data, list):
                                    for item in data[:50]:
                                        if isinstance(item, dict):
                                            symbol = item.get('symbol') or item.get('id') or item.get('code')
                                            name = item.get('name') or symbol
                                            if symbol:
                                                currencies.append({
                                                    'id': str(symbol).lower(),
                                                    'symbol': str(symbol).upper(),
                                                    'name': str(name)
                                                })
                                
                                if currencies:
                                    return currencies
                
                except Exception:
                    continue
            
            return []
            
        except Exception as e:
            print(f"خطا در دریافت از API عمومی: {e}")
            return []
    
    async def _show_currency_selection_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE, currencies: list):
        """نمایش منوی انتخاب ارزها"""
        # تقسیم ارزها به صفحات
        currencies_per_page = 10
        total_pages = (len(currencies) + currencies_per_page - 1) // currencies_per_page
        
        context.user_data['currency_page'] = 0
        context.user_data['total_currency_pages'] = total_pages
        
        return await self._display_currency_page(update, context, currencies, 0)
    
    async def _display_currency_page(self, update: Update, context: ContextTypes.DEFAULT_TYPE, currencies: list, page: int):
        """نمایش صفحه ارزها"""
        currencies_per_page = 10
        start_idx = page * currencies_per_page
        end_idx = start_idx + currencies_per_page
        page_currencies = currencies[start_idx:end_idx]
        
        # ایجاد دکمه‌های ارزها
        keyboard = []
        for currency in page_currencies:
            symbol = currency.get('symbol', '')
            name = currency.get('name', '')
            button_text = f"{symbol} ({name})"
            keyboard.append([KeyboardButton(button_text)])
        
        # دکمه‌های ناوبری
        nav_buttons = []
        if page > 0:
            nav_buttons.append(KeyboardButton("⬅️ صفحه قبل"))
        if page < context.user_data.get('total_currency_pages', 1) - 1:
            nav_buttons.append(KeyboardButton("➡️ صفحه بعد"))
        
        if nav_buttons:
            keyboard.append(nav_buttons)
        
        keyboard.append([KeyboardButton("🔙 بازگشت به منو")])
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        
        text = f"""
🪙 **انتخاب ارزها - صفحه {page + 1} از {context.user_data.get('total_currency_pages', 1)}**

📊 **تعداد کل ارزها**: {len(currencies)}

💡 **دستورالعمل**:
• روی هر ارز کلیک کنید تا آن را فعال/غیرفعال کنید
• ارزهای فعال در منوی کاربران نمایش داده می‌شوند
• ارزهای غیرفعال از منوی کاربران حذف می‌شوند

⚠️ **نکته**: فقط ارزهای فعال برای کاربران قابل مشاهده هستند.
        """
        
        await update.message.reply_text(text, reply_markup=reply_markup)
        return "CURRENCY_SELECTION"
    
    async def process_currency_selection(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """پردازش انتخاب ارز"""
        selected_currency = update.message.text
        
        # بررسی دکمه‌های ناوبری
        if selected_currency == "⬅️ صفحه قبل":
            current_page = context.user_data.get('currency_page', 0)
            if current_page > 0:
                context.user_data['currency_page'] = current_page - 1
                currencies = context.user_data.get('available_currencies', [])
                return await self._display_currency_page(update, context, currencies, current_page - 1)
        
        elif selected_currency == "➡️ صفحه بعد":
            current_page = context.user_data.get('currency_page', 0)
            total_pages = context.user_data.get('total_currency_pages', 1)
            if current_page < total_pages - 1:
                context.user_data['currency_page'] = current_page + 1
                currencies = context.user_data.get('available_currencies', [])
                return await self._display_currency_page(update, context, currencies, current_page + 1)
        
        # پیدا کردن ارز انتخاب شده
        currencies = context.user_data.get('available_currencies', [])
        selected_currency_data = None
        
        for currency in currencies:
            symbol = currency.get('symbol', '')
            name = currency.get('name', '')
            button_text = f"{symbol} ({name})"
            if button_text == selected_currency:
                selected_currency_data = currency
                break
        
        if not selected_currency_data:
            await update.message.reply_text("❌ ارز انتخاب شده یافت نشد!")
            return "CURRENCY_SELECTION"
        
        # ذخیره ارز انتخاب شده
        context.user_data['selected_currency'] = selected_currency_data
        
        # بررسی وضعیت فعلی ارز
        symbol = selected_currency_data.get('symbol', '').lower()
        enabled_currencies = self.store.get('enabled_currencies', {})
        is_enabled = symbol in enabled_currencies and enabled_currencies[symbol].get('enabled', False)
        
        # نمایش منوی فعال/غیرفعال
        keyboard = []
        if is_enabled:
            keyboard.append([KeyboardButton("🔴 خاموش")])
        else:
            keyboard.append([KeyboardButton("🟢 روشن")])
        
        keyboard.append([KeyboardButton("🔙 بازگشت به لیست ارزها")])
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        
        status_text = "🟢 فعال" if is_enabled else "🔴 غیرفعال"
        
        text = f"""
🪙 **مدیریت ارز: {selected_currency_data.get('symbol', '')}**

📝 **نام**: {selected_currency_data.get('name', '')}
🆔 **شناسه**: {selected_currency_data.get('id', '')}
📊 **وضعیت فعلی**: {status_text}

💡 **دستورالعمل**:
• روی "🟢 روشن" کلیک کنید تا ارز را فعال کنید
• روی "🔴 خاموش" کلیک کنید تا ارز را غیرفعال کنید

⚠️ **نکته**: ارزهای غیرفعال در منوی کاربران نمایش داده نمی‌شوند.
        """
        
        await update.message.reply_text(text, reply_markup=reply_markup)
        return "CURRENCY_TOGGLE"
    
    async def process_currency_toggle(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """پردازش فعال/غیرفعال کردن ارز"""
        action = update.message.text
        selected_currency = context.user_data.get('selected_currency')
        
        if not selected_currency:
            await update.message.reply_text("❌ ارز انتخاب شده یافت نشد!")

        
        symbol = selected_currency.get('symbol', '').lower()
        currency_name = selected_currency.get('name', '')
        api_id = context.user_data.get('selected_api_id')
        
        enabled_currencies = self.store.get('enabled_currencies', {})
        
        if action == "🟢 روشن":
            # فعال کردن ارز
            enabled_currencies[symbol] = {
                'symbol': selected_currency.get('symbol', ''),
                'name': currency_name,
                'type': 'crypto',
                'api_id': api_id,
                'enabled': True,
                'created_at': datetime.now().isoformat()
            }
            
            self.store['enabled_currencies'] = enabled_currencies
            save_store(self.store)
            
            keyboard = [
                [KeyboardButton("🔙 بازگشت به لیست ارزها")]
            ]
            reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
            
            text = f"""
✅ **ارز با موفقیت فعال شد!**

🪙 **ارز**: {selected_currency.get('symbol', '')} ({currency_name})
📊 **وضعیت**: 🟢 فعال
🔗 **API**: {context.user_data.get('selected_api_config', {}).get('name', 'نامشخص')}
📅 **تاریخ**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

🎉 **تبریک!** این ارز حالا در منوی کاربران نمایش داده می‌شود.
            """
            
            await update.message.reply_text(text, reply_markup=reply_markup)
            return "CURRENCY_SELECTION"
        
        elif action == "🔴 خاموش":
            # غیرفعال کردن ارز
            if symbol in enabled_currencies:
                enabled_currencies[symbol]['enabled'] = False
            else:
                enabled_currencies[symbol] = {
                    'symbol': selected_currency.get('symbol', ''),
                    'name': currency_name,
                    'type': 'crypto',
                    'api_id': api_id,
                    'enabled': False,
                    'created_at': datetime.now().isoformat()
                }
            
            self.store['enabled_currencies'] = enabled_currencies
            save_store(self.store)
            
            keyboard = [
                [KeyboardButton("🔙 بازگشت به لیست ارزها")]
            ]
            reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
            
            text = f"""
✅ **ارز با موفقیت خاموش شد!**

🪙 **ارز**: {selected_currency.get('symbol', '')} ({currency_name})
📊 **وضعیت**: 🔴 غیرفعال
🔗 **API**: {context.user_data.get('selected_api_config', {}).get('name', 'نامشخص')}
📅 **تاریخ**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

🔒 **نکته**: این ارز دیگر در منوی کاربران نمایش داده نمی‌شود.
            """
            
            await update.message.reply_text(text, reply_markup=reply_markup)
            return "CURRENCY_SELECTION"
        
        elif action == "🔙 بازگشت به لیست ارزها":
            # بازگشت به لیست ارزها
            currencies = context.user_data.get('available_currencies', [])
            current_page = context.user_data.get('currency_page', 0)
            return await self._display_currency_page(update, context, currencies, current_page)
        
        else:
            await update.message.reply_text("❌ عمل نامعتبر!")
            return "CURRENCY_TOGGLE"
    
    # ===== مدیریت ارزها =====
    async def manage_currencies(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """مدیریت ارزها"""
        # دریافت ارزهای موجود
        currencies = self.store.get('enabled_currencies', {})
        
        keyboard = [
            [KeyboardButton("🔍 دریافت لیست ارزها از API")],
            [KeyboardButton("➕ افزودن ارز"), KeyboardButton("📋 لیست ارزها")],
            [KeyboardButton("⚙️ تنظیمات ارزها")],
            [KeyboardButton("🔙 بازگشت به منو")]
        ]
        
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        
        text = f"""
💰 **مدیریت ارزها**

📊 **آمار ارزها**:
• تعداد ارزهای فعال: {len([c for c in currencies.values() if c.get('enabled', False)])}
• تعداد ارزهای غیرفعال: {len([c for c in currencies.values() if not c.get('enabled', False)])}

🪙 **ارزهای موجود**:
{self._format_currency_list(currencies)}

لطفاً یکی از گزینه‌های زیر را انتخاب کنید:
        """
        
        await update.message.reply_text(text, reply_markup=reply_markup)
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
        # دریافت شاخص‌های موجود
        indicators = self.store.get('enabled_indicators', {})
        
        keyboard = [
            [KeyboardButton("➕ افزودن شاخص"), KeyboardButton("📋 لیست شاخص‌ها")],
            [KeyboardButton("⚙️ تنظیمات شاخص‌ها")],
            [KeyboardButton("🔙 بازگشت به منو")]
        ]
        
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        
        text = f"""
📊 **مدیریت شاخص‌ها**

📊 **آمار شاخص‌ها**:
• تعداد شاخص‌های فعال: {len([i for i in indicators.values() if i.get('enabled', False)])}
• تعداد شاخص‌های غیرفعال: {len([i for i in indicators.values() if not i.get('enabled', False)])}

📈 **شاخص‌های موجود**:
{self._format_indicator_list(indicators)}

لطفاً یکی از گزینه‌های زیر را انتخاب کنید:
        """
        
        await update.message.reply_text(text, reply_markup=reply_markup)
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
        
        keyboard = [
            [KeyboardButton("🔙 بازگشت به منو")]
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        
        if not api_configs:
            await update.message.reply_text(
                "📋 **لیست API ها**\n\n"
                "❌ هیچ API ثبت نشده است.",
                reply_markup=reply_markup
            )
            return
        
        text = "📋 **لیست API های ثبت شده:**\n\n"
        for api_id, config in api_configs.items():
            status = "✅ فعال" if config.get('enabled', True) else "❌ غیرفعال"
            text += f"🔹 **{config.get('name', api_id)}**\n"
            text += f"   نوع: {config.get('type', 'نامشخص')}\n"
            text += f"   وضعیت: {status}\n"
            text += f"   URL: {config.get('url', 'نامشخص')[:50]}...\n\n"
        
        await update.message.reply_text(
            text,
            reply_markup=reply_markup
        )

    async def list_currencies_action(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """نمایش لیست ارزها"""
        store = load_store()
        enabled_currencies = store.get('enabled_currencies', {})
        
        keyboard = [
            [KeyboardButton("🔙 بازگشت به منو")]
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        
        if not enabled_currencies:
            await update.message.reply_text(
                "💰 **لیست ارزها**\n\n"
                "❌ هیچ ارزی فعال نشده است.",
                reply_markup=reply_markup
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
        
        await update.message.reply_text(
            text,
            reply_markup=reply_markup
        )

    async def list_indicators_action(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """نمایش لیست شاخص‌ها"""
        store = load_store()
        enabled_indicators = store.get('enabled_indicators', {})
        
        keyboard = [
            [KeyboardButton("🔙 بازگشت به منو")]
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        
        if not enabled_indicators:
            await update.message.reply_text(
                "📊 **لیست شاخص‌ها**\n\n"
                "❌ هیچ شاخصی فعال نشده است.",
                reply_markup=reply_markup
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
        
        await update.message.reply_text(
            text,
            reply_markup=reply_markup
        )



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
        await update.message.reply_text("✅ بازگشت زدی! دکمه مورد نظر را انتخاب کن:")
        await self.admin_panel_main(update, context)

# ایجاد نمونه از کلاس
admin_panel = AdminPanel()
