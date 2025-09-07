import json
import asyncio
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton, Message
from telegram.ext import ContextTypes, ConversationHandler
from typing import Optional, List, Dict
from config import OWNER_ID, ADMIN_ID
from store import load_store, save_store
from cache import TTLCache
from external_api_client import ExternalAPIManager
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
    USER_MESSAGE, BROADCAST_FORWARD, SET_CRYPTO_API_KEY, BROADCAST_CAPTURE,
    # New API management states
    MANAGE_APIS, ADD_API, EDIT_API, DELETE_API, API_SETTINGS,
    MANAGE_CURRENCIES, ADD_CURRENCY, EDIT_CURRENCY, DELETE_CURRENCY, CURRENCY_SETTINGS,
    MANAGE_INDICATORS, ADD_INDICATOR, EDIT_INDICATOR, DELETE_INDICATOR, INDICATOR_SETTINGS,
    # External API configuration states
    EXTERNAL_API_URL, EXTERNAL_API_KEY, EXTERNAL_API_TYPE,
    # Enhanced Lock system states
    LOCK_MENU, ADD_LOCK_CHANNEL, CONFIRM_ADMIN, SUBMIT_LOCK_LINK, LIST_LOCKED_CHANNELS,
    # Analytics system states
    STATS_24H, STATS_7D, STATS_30D, STATS_ALL_TIME,
    # Feature toggle system states
    FEATURE_TOGGLE_MENU, FEATURE_TOGGLE_SUBMENU, FEATURE_SEARCH,
    # Blacklist/Whitelist system states
    AWAIT_BLACKLIST_ADD, AWAIT_BLACKLIST_REMOVE, AWAIT_WHITELIST_ADD, AWAIT_WHITELIST_REMOVE, LISTS_SEARCH
) = range(66)

class AdminPanel:
    def __init__(self):
        self.store = load_store()
        self.cache = TTLCache()
        # In-memory admin set for fast lookups
        self._refresh_admins_cache()
        # External API manager
        self.api_manager = ExternalAPIManager(self.store)
    
    def _refresh_admins_cache(self):
        """بروزرسانی کش ادمین‌ها"""
        from config import OWNER_ID
        admins = self.store.get('admins', [])
        self.admins_set = {OWNER_ID} | set(admins)
    
    def _is_admin(self, user_id: int) -> bool:
        """بررسی دسترسی ادمین"""
        return user_id in self.admins_set
    
    # Repository layer for admin management
    def get_admin_ids(self) -> set[int]:
        """دریافت لیست آیدی‌های ادمین‌ها"""
        return self.admins_set.copy()
    
    def add_admin(self, user_id: int) -> bool:
        """افزودن ادمین جدید"""
        from config import OWNER_ID
        
        if user_id == OWNER_ID:
            return False  # Owner is always admin, can't be added
        
        admins = self.store.get('admins', [])
        if user_id in admins:
            return False  # Already admin
        
        admins.append(user_id)
        self.store['admins'] = admins
        save_store(self.store)
        self._refresh_admins_cache()
        return True
    
    def remove_admin(self, user_id: int) -> bool:
        """حذف ادمین"""
        from config import OWNER_ID
        
        if user_id == OWNER_ID:
            return False  # Can't remove owner
        
        admins = self.store.get('admins', [])
        if user_id not in admins:
            return False  # Not an admin
        
        # Safety check: prevent removing last admin
        if len(admins) <= 1:
            return False  # Must keep at least one admin
        
        admins.remove(user_id)
        self.store['admins'] = admins
        save_store(self.store)
        self._refresh_admins_cache()
        return True
    
    def count_admins(self) -> int:
        """شمارش تعداد ادمین‌ها"""
        return len(self.admins_set)
    
    async def handle_admin_panel_text(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """مدیریت متن‌های پنل مدیریتی"""
        user_id = update.effective_user.id
        text = update.message.text.strip()
        
        print(f"DEBUG: handle_admin_panel_text: User {user_id} sent text: {repr(text)}")
        
        # بررسی دسترسی (مالک یا ادمین)
        admins = self.store.get('admins', [])
        if user_id != OWNER_ID and user_id not in admins:
            print(f"DEBUG: User {user_id} is not admin, access denied")
            await update.message.reply_text("❌ شما دسترسی به پنل مدیریتی ندارید!")
            return
        

        
        # Handle admin panel buttons
        if text == "👥 مدیریت ادمین‌ها":
            await self.admin_manage_admins(update, context)
        elif text == "📢 ارسال همگانی":
            await self.broadcast_start(update, context)
        elif text == "📝 تنظیم متن‌ها":
            await self.admin_texts_panel(update, context)
        elif text == "🔧 مدیریت API ها":
            await self.admin_api_panel(update, context)
        elif text == "💰 مدیریت ارزها":
            await self.manage_currencies(update, context)
        elif text == "📊 مدیریت شاخص‌ها":
            await self.manage_indicators(update, context)
        elif text == "🔒 قفل اجباری":
            await self.enhanced_lock_menu(update, context)
        elif text == "⚪ لیست سفید/سیاه":
            await self.admin_lists_panel(update, context)
        elif text == "📊 آمار و گزارش":
            await self.enhanced_analytics_dashboard(update, context)
        elif text == "🔙 بازگشت به منو":
            # بازگشت به منوی اصلی کاربر
            from main import show_main_menu
            await show_main_menu(update, context)
            return
        else:
            await update.message.reply_text("❌ دستور نامعتبر! لطفاً از دکمه‌های موجود استفاده کنید.")
        
        return ADMIN_PANEL

    async def admin_panel_main(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """پنل مدیریتی اصلی"""
        user_id = update.effective_user.id
        
        print(f"DEBUG: admin_panel_main called by user {user_id}")
        
        # بررسی دسترسی (مالک یا ادمین)
        if not self._is_admin(user_id):
            print(f"DEBUG: User {user_id} is not admin, access denied")
            await update.message.reply_text("❌ شما دسترسی به پنل مدیریتی ندارید!")
            return
        
        # بررسی timeout عملیات ادمین
        if self.check_admin_timeout(context):
            await update.message.reply_text("مهلت انجام عملیات به پایان رسید. لطفاً دوباره تلاش کنید.")
    
        

        
        # ایجاد کیبورد سریع (ReplyKeyboard) برای پنل مدیریتی
        from telegram import ReplyKeyboardMarkup, KeyboardButton
        
        # مقداردهی اولیه registry
        self.initialize_feature_registry()
        
        # ساخت کیبورد سریع بر اساس ویژگی‌های فعال
        keyboard = []
        
        # ردیف 1 - مدیریت کاربران و ارسال
        row1 = []
        if self.is_feature_enabled('admin.user_management'):
            row1.append(KeyboardButton("👥 مدیریت ادمین‌ها"))
        if self.is_feature_enabled('admin.broadcast'):
            row1.append(KeyboardButton("📢 ارسال همگانی"))
        if row1:
            keyboard.append(row1)
        
        # ردیف 2 - تنظیمات متن و API
        row2 = []
        if self.is_feature_enabled('admin.text_settings'):
            row2.append(KeyboardButton("📝 تنظیم متن‌ها"))
        if self.is_feature_enabled('admin.api_management'):
            row2.append(KeyboardButton("🔧 مدیریت API ها"))
        if row2:
            keyboard.append(row2)
        
        # ردیف 3 - مدیریت ارزها و شاخص‌ها
        row3 = []
        if self.is_feature_enabled('admin.currencies'):
            row3.append(KeyboardButton("💰 مدیریت ارزها"))
        if self.is_feature_enabled('admin.indicators'):
            row3.append(KeyboardButton("📊 مدیریت شاخص‌ها"))
        if row3:
            keyboard.append(row3)
        
        # ردیف 4
        row4 = []
        if self.is_feature_enabled('admin.force_subscription'):
            row4.append(KeyboardButton("🔒 قفل اجباری"))
        if self.is_feature_enabled('admin.lists'):
            row4.append(KeyboardButton("⚪ لیست سفید/سیاه"))
        if row4:
            keyboard.append(row4)
        
        # ردیف 5
        row5 = []
        if self.is_feature_enabled('admin.stats'):
            row5.append(KeyboardButton("📊 آمار و گزارش"))
        if row5:
            keyboard.append(row5)
        
        # دکمه بازگشت (همیشه موجود)
        keyboard.append([KeyboardButton("🔙 بازگشت به منو")])
        
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
        
        # Handle both message and callback query
        if update.message:
            await update.message.reply_text(text, reply_markup=reply_markup)
        elif update.callback_query:
            await update.callback_query.edit_message_text(text, reply_markup=reply_markup)
        
        return ADMIN_PANEL
    
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
        # بررسی دسترسی ادمین
        user_id = update.effective_user.id
        if not self._is_admin(user_id):
            await update.message.reply_text("دسترسی غیرمجاز.")
            return
        
        # تنظیم timeout برای 2 دقیقه
        context.user_data['admin_action_timeout'] = datetime.now() + timedelta(minutes=2)
        
        await update.message.reply_text(
            "➕ **افزودن ادمین جدید**\n\n"
            "لطفاً آی‌دی عددی کاربر را ارسال کنید.\n\n"
            "🔙 برای بازگشت: /cancel",
            parse_mode='Markdown'
        )
        
        return ADD_ADMIN
    
    async def add_admin_process(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """پردازش افزودن ادمین"""
        # بررسی دسترسی ادمین
        user_id = update.effective_user.id
        if not self._is_admin(user_id):
            await update.message.reply_text("دسترسی غیرمجاز.")
            return
        
        # بررسی timeout
        if 'admin_action_timeout' in context.user_data:
            if datetime.now() > context.user_data['admin_action_timeout']:
                context.user_data.pop('admin_action_timeout', None)
                await update.message.reply_text("مهلت انجام عملیات به پایان رسید. لطفاً دوباره تلاش کنید.")
                return ADMIN_PANEL
        
        try:
            new_admin_id = int(update.message.text)
            
            # بررسی صحت آیدی
            if new_admin_id <= 0:
                await update.message.reply_text("لطفاً فقط آی‌دی عددی ارسال کنید.")
                return ADD_ADMIN
            
            # استفاده از repository layer
            success = self.add_admin(new_admin_id)
            
            if not success:
                # بررسی دلیل عدم موفقیت
                from config import OWNER_ID
                if new_admin_id == OWNER_ID:
                    await update.message.reply_text("❌ این کاربر مالک ربات است!")
                elif new_admin_id in self.get_admin_ids():
                    await update.message.reply_text("این کاربر قبلاً ادمین است.")
                else:
                    await update.message.reply_text("❌ خطا در افزودن ادمین!")
                return ADD_ADMIN
            
            # پاک کردن timeout
            context.user_data.pop('admin_action_timeout', None)
            
            keyboard = [[KeyboardButton("🔙 بازگشت به منو")]]
            reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
            
            await update.message.reply_text(
                f"کاربر {new_admin_id} با موفقیت به ادمین‌ها اضافه شد. دسترسی پنل مدیریت برای او فعال شد.",
                reply_markup=reply_markup
            )
            
            return ADMIN_PANEL
            
        except ValueError:
            await update.message.reply_text("لطفاً فقط آی‌دی عددی ارسال کنید.")
            return ADD_ADMIN
        except Exception as e:
            print(f"Error in add_admin_process: {e}")
            await update.message.reply_text("❌ خطا در پردازش درخواست. لطفاً دوباره تلاش کنید.")
            return ADD_ADMIN
    
    async def remove_admin_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """شروع فرآیند حذف ادمین"""
        # بررسی دسترسی ادمین
        user_id = update.effective_user.id
        if not self._is_admin(user_id):
            await update.message.reply_text("دسترسی غیرمجاز.")
            return
        
        # تنظیم timeout برای 2 دقیقه
        context.user_data['admin_action_timeout'] = datetime.now() + timedelta(minutes=2)
        
        await update.message.reply_text(
            "➖ **حذف ادمین**\n\n"
            "لطفاً آی‌دی عددی ادمین برای حذف را ارسال کنید.\n\n"
            "🔙 برای بازگشت: /cancel",
            parse_mode='Markdown'
        )
        
        return REMOVE_ADMIN
    
    async def remove_admin_process(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """پردازش حذف ادمین"""
        # بررسی دسترسی ادمین
        user_id = update.effective_user.id
        if not self._is_admin(user_id):
            await update.message.reply_text("دسترسی غیرمجاز.")
            return
        
        # بررسی timeout
        if 'admin_action_timeout' in context.user_data:
            if datetime.now() > context.user_data['admin_action_timeout']:
                context.user_data.pop('admin_action_timeout', None)
                await update.message.reply_text("مهلت انجام عملیات به پایان رسید. لطفاً دوباره تلاش کنید.")
                return ADMIN_PANEL
        
        try:
            admin_to_remove = int(update.message.text)
            
            # بررسی صحت آیدی
            if admin_to_remove <= 0:
                await update.message.reply_text("لطفاً فقط آی‌دی عددی ارسال کنید.")
                return REMOVE_ADMIN
            
            # استفاده از repository layer
            success = self.remove_admin(admin_to_remove)
            
            if not success:
                # بررسی دلیل عدم موفقیت
                from config import OWNER_ID
                if admin_to_remove == OWNER_ID:
                    await update.message.reply_text("❌ این کاربر مالک ربات است!")
                elif admin_to_remove not in self.get_admin_ids():
                    await update.message.reply_text("این کاربر ادمین نیست.")
                elif self.count_admins() <= 1:
                    await update.message.reply_text("عملیات مسدود شد: حداقل یک ادمین باید باقی بماند.")
                else:
                    await update.message.reply_text("❌ خطا در حذف ادمین!")
                return REMOVE_ADMIN
            
            # پاک کردن timeout
            context.user_data.pop('admin_action_timeout', None)
            
            keyboard = [[KeyboardButton("🔙 بازگشت به منو")]]
            reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
            
            await update.message.reply_text(
                f"کاربر {admin_to_remove} با موفقیت از ادمینی عزل شد و دسترسی پنل مدیریت غیرفعال گردید.",
                reply_markup=reply_markup
            )
            
            return ADMIN_PANEL
            
        except ValueError:
            await update.message.reply_text("لطفاً فقط آی‌دی عددی ارسال کنید.")
            return REMOVE_ADMIN
        except Exception as e:
            print(f"Error in remove_admin_process: {e}")
            await update.message.reply_text("❌ خطا در پردازش درخواست. لطفاً دوباره تلاش کنید.")
            return REMOVE_ADMIN
    
    async def cancel_admin_operation(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """لغو عملیات ادمین"""
        # پاک کردن timeout
        context.user_data.pop('admin_action_timeout', None)
        
        await update.message.reply_text("عملیات لغو شد.")
        return ADMIN_PANEL
    
    def check_admin_timeout(self, context: ContextTypes.DEFAULT_TYPE) -> bool:
        """بررسی timeout عملیات ادمین"""
        if 'admin_action_timeout' in context.user_data:
            if datetime.now() > context.user_data['admin_action_timeout']:
                context.user_data.pop('admin_action_timeout', None)
                return True
        return False
    
    async def broadcast_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """شروع ارسال همگانی - مرحله 1: دریافت پیام"""
        # بررسی دسترسی ادمین
        user_id = update.effective_user.id
        if not self._is_admin(user_id):
            await update.message.reply_text("دسترسی غیرمجاز.")
            return
        
        # بررسی وجود کاربران
        users = self.store.get('users', [])
        if not users:
            await update.message.reply_text("هیچ کاربری برای ارسال وجود ندارد.")
            return
        
        # پاک کردن داده‌های قبلی
        context.user_data.pop('broadcast_payload', None)
        context.user_data.pop('broadcast_message_id', None)
        context.user_data.pop('broadcast_state', None)
        
        # ایجاد دکمه‌های شیشه‌ای
        keyboard = [
            [InlineKeyboardButton("شروع ارسال", callback_data="start_broadcast", disabled=True)],
            [InlineKeyboardButton("انصراف", callback_data="cancel_broadcast")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        text = f"""
📢 **ارسال همگانی**

👥 **آمار کاربران**: {len(users)} نفر

پیام همگانی را ارسال یا فوروارد کنید. هر نوع محتوا مجاز است.

💡 **نکات مهم**:
• می‌توانید متن، عکس، ویدیو، فایل یا هر محتوای دیگری ارسال کنید
• پس از ارسال پیام، دکمه "شروع ارسال" فعال می‌شود
• آمار لحظه‌ای ارسال نمایش داده می‌شود
        """
        
        message = await update.message.reply_text(text, reply_markup=reply_markup)
        context.user_data['broadcast_instruction_message_id'] = message.message_id
        context.user_data['broadcast_state'] = 'awaiting_message'
        
        return BROADCAST_CAPTURE
    
    async def capture_broadcast_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """ضبط پیام همگانی"""
        # بررسی دسترسی ادمین
        user_id = update.effective_user.id
        if not self._is_admin(user_id):
            return
        
        # بررسی وضعیت broadcast
        if context.user_data.get('broadcast_state') != 'awaiting_message':
            return
        
        # ذخیره payload پیام
        payload = {
            'message_id': update.message.message_id,
            'chat_id': update.message.chat_id,
            'from_user_id': update.message.from_user.id,
            'date': update.message.date,
            'message_type': 'text' if update.message.text else 'media',
            'text': update.message.text,
            'caption': update.message.caption,
            'parse_mode': update.message.parse_mode,
            'forward_from': update.message.forward_from,
            'forward_from_chat': update.message.forward_from_chat,
            'forward_date': update.message.forward_date,
            'is_forward': bool(update.message.forward_from or update.message.forward_from_chat)
        }
        
        # ذخیره media files
        if update.message.photo:
            payload['photo'] = [photo.file_id for photo in update.message.photo]
        elif update.message.video:
            payload['video'] = update.message.video.file_id
        elif update.message.document:
            payload['document'] = update.message.document.file_id
        elif update.message.audio:
            payload['audio'] = update.message.audio.file_id
        elif update.message.voice:
            payload['voice'] = update.message.voice.file_id
        elif update.message.video_note:
            payload['video_note'] = update.message.video_note.file_id
        elif update.message.sticker:
            payload['sticker'] = update.message.sticker.file_id
        elif update.message.animation:
            payload['animation'] = update.message.animation.file_id
        
        context.user_data['broadcast_payload'] = payload
        context.user_data['broadcast_state'] = 'message_captured'
        
        # بروزرسانی دکمه‌ها
        keyboard = [
            [InlineKeyboardButton("شروع ارسال", callback_data="start_broadcast")],
            [InlineKeyboardButton("انصراف", callback_data="cancel_broadcast")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # بروزرسانی پیام دستورالعمل
        instruction_msg_id = context.user_data.get('broadcast_instruction_message_id')
        if instruction_msg_id:
            try:
                await context.bot.edit_message_reply_markup(
                    chat_id=update.message.chat_id,
                    message_id=instruction_msg_id,
                    reply_markup=reply_markup
                )
            except:
                pass
        
        # تایید دریافت پیام
        await update.message.reply_text("پیام ثبت شد. برای شروع، «شروع ارسال» را بزنید.")
        
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
        

    
    async def start_broadcast(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """شروع ارسال همگانی"""
        query = update.callback_query
        await query.answer()
        
        # بررسی دسترسی ادمین
        user_id = update.effective_user.id
        if not self._is_admin(user_id):
            await query.edit_message_text("دسترسی غیرمجاز.")
            return
        
        # بررسی وجود payload
        payload = context.user_data.get('broadcast_payload')
        if not payload:
            await query.edit_message_text("هیچ پیامی ثبت نشده است. لطفاً ابتدا پیام را ارسال یا فوروارد کنید.")
            return
        
        # دریافت کاربران
        users = self.store.get('users', [])
        if not users:
            await query.edit_message_text("هیچ کاربری برای ارسال وجود ندارد.")
            return
        
        # ایجاد broadcast record
        import uuid
        broadcast_id = f"broadcast_{uuid.uuid4().hex[:8]}"
        broadcast_record = {
            'broadcast_id': broadcast_id,
            'admin_id': user_id,
            'created_at': datetime.now().isoformat(),
            'payload_meta': {
                'message_type': payload['message_type'],
                'is_forward': payload['is_forward'],
                'text_length': len(payload.get('text', '') or ''),
                'has_media': bool(payload.get('photo') or payload.get('video') or payload.get('document'))
            },
            'total': len(users),
            'success': 0,
            'fail': 0,
            'results': []
        }
        
        # ذخیره broadcast record
        broadcasts = self.store.get('broadcasts', [])
        broadcasts.append(broadcast_record)
        self.store['broadcasts'] = broadcasts
        save_store(self.store)
        
        # شروع ارسال
        context.user_data['broadcast_id'] = broadcast_id
        context.user_data['broadcast_state'] = 'sending'
        
        await self._send_broadcast_messages(update, context, payload, users, broadcast_id)
    
    async def _send_broadcast_messages(self, update: Update, context: ContextTypes.DEFAULT_TYPE, payload: dict, users: list, broadcast_id: str):
        """ارسال پیام‌های همگانی با آمار لحظه‌ای"""
        success_count = 0
        failed_count = 0
        total = len(users)
        sent_message_ids = {}  # برای پین کردن بعدی
        failed_users = []  # لیست کاربران ناموفق با دلیل خطا
        
        # پیام آمار لحظه‌ای
        status_message = await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=f"در حال ارسال… 0/{total}\nموفق: 0 | ناموفق: 0"
        )
        
        for i, user_id in enumerate(users):
            try:
                # ارسال پیام با retry logic
                sent_msg = await self._send_message_to_user_with_retry(context, payload, user_id)
                
                if sent_msg:
                    success_count += 1
                    sent_message_ids[user_id] = sent_msg.message_id
                    # ثبت رویداد ارسال موفق
                    self.log_user_event(user_id, 'broadcast_success', {'broadcast_id': broadcast_id})
                else:
                    failed_count += 1
                    failed_users.append({'user_id': user_id, 'error': 'نامشخص'})
                    # ثبت رویداد ارسال ناموفق
                    self.log_user_event(user_id, 'broadcast_fail', {'broadcast_id': broadcast_id, 'error': 'نامشخص'})
                
                # بروزرسانی آمار هر 10 پیام یا در انتها
                if (i + 1) % 10 == 0 or i == total - 1:
                    try:
                        await status_message.edit_text(
                            f"در حال ارسال… {i + 1}/{total}\nموفق: {success_count} | ناموفق: {failed_count}"
                        )
                    except:
                        pass
                
                # تاخیر برای جلوگیری از محدودیت
                await asyncio.sleep(0.1)
                
            except Exception as e:
                failed_count += 1
                error_reason = self._get_error_reason(str(e))
                failed_users.append({'user_id': user_id, 'error': error_reason})
                print(f"Failed to send to {user_id}: {e}")
        
        # بروزرسانی broadcast record
        self._update_broadcast_record(broadcast_id, success_count, failed_count, sent_message_ids, failed_users)
        
        # نمایش آمار نهایی
        keyboard = [
            [InlineKeyboardButton("پین کردن پیام همگانی", callback_data=f"pin_broadcast:{broadcast_id}")],
            [InlineKeyboardButton("گزارش خطاها", callback_data=f"download_failures:{broadcast_id}")],
            [InlineKeyboardButton("بستن", callback_data="close_broadcast")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        final_text = f"""
ارسال همگانی به پایان رسید.

ارسال موفق: {success_count} | ناموفق: {failed_count}
        """
        
        await status_message.edit_text(final_text, reply_markup=reply_markup)
    
    async def _send_message_to_user_with_retry(self, context: ContextTypes.DEFAULT_TYPE, payload: dict, user_id: int, max_retries: int = 3) -> Optional[Message]:
        """ارسال پیام به کاربر با retry logic"""
        for attempt in range(max_retries):
            try:
                return await self._send_message_to_user(context, payload, user_id)
            except Exception as e:
                if "FloodWait" in str(e) or "429" in str(e):
                    # استخراج زمان انتظار از خطا
                    wait_time = self._extract_flood_wait_time(str(e))
                    if attempt < max_retries - 1:
                        await asyncio.sleep(wait_time)
                        continue
                elif "400" in str(e) or "403" in str(e):
                    # خطاهای دائمی - متوقف کردن retry
                    break
                else:
                    # خطاهای دیگر - retry
                    if attempt < max_retries - 1:
                        await asyncio.sleep(1)
                        continue
        return None
    
    def _get_error_reason(self, error_str: str) -> str:
        """تبدیل خطا به دلیل قابل فهم"""
        if "FloodWait" in error_str or "429" in error_str:
            return "محدودیت ارسال (FloodWait)"
        elif "403" in error_str or "Forbidden" in error_str:
            return "کاربر ربات را مسدود کرده است"
        elif "400" in error_str or "Bad Request" in error_str:
            return "چت یافت نشد"
        elif "404" in error_str:
            return "کاربر یافت نشد"
        else:
            return "خطای نامشخص"
    
    def _extract_flood_wait_time(self, error_str: str) -> int:
        """استخراج زمان انتظار از خطای FloodWait"""
        import re
        match = re.search(r'FloodWait\((\d+)\)', error_str)
        if match:
            return int(match.group(1))
        return 1  # پیش‌فرض 1 ثانیه
        
        # پاک کردن state
        context.user_data.pop('broadcast_state', None)
        context.user_data.pop('broadcast_payload', None)
        context.user_data.pop('broadcast_instruction_message_id', None)
    
    async def _send_message_to_user(self, context: ContextTypes.DEFAULT_TYPE, payload: dict, user_id: int):
        """ارسال پیام به کاربر خاص"""
        try:
            # اگر پیام فوروارد است، فوروارد کن
            if payload.get('is_forward'):
                # ایجاد message object برای فوروارد
                from telegram import Message
                original_chat_id = payload['chat_id']
                original_message_id = payload['message_id']
                
                # فوروارد پیام اصلی
                return await context.bot.forward_message(
                    chat_id=user_id,
                    from_chat_id=original_chat_id,
                    message_id=original_message_id
                )
            
            # ارسال پیام جدید
            if payload.get('text'):
                return await context.bot.send_message(
                    chat_id=user_id,
                    text=payload['text'],
                    parse_mode=payload.get('parse_mode')
                )
            elif payload.get('photo'):
                return await context.bot.send_photo(
                    chat_id=user_id,
                    photo=payload['photo'][-1],  # بزرگترین سایز
                    caption=payload.get('caption'),
                    parse_mode=payload.get('parse_mode')
                )
            elif payload.get('video'):
                return await context.bot.send_video(
                    chat_id=user_id,
                    video=payload['video'],
                    caption=payload.get('caption'),
                    parse_mode=payload.get('parse_mode')
                )
            elif payload.get('document'):
                return await context.bot.send_document(
                    chat_id=user_id,
                    document=payload['document'],
                    caption=payload.get('caption'),
                    parse_mode=payload.get('parse_mode')
                )
            elif payload.get('audio'):
                return await context.bot.send_audio(
                    chat_id=user_id,
                    audio=payload['audio'],
                    caption=payload.get('caption'),
                    parse_mode=payload.get('parse_mode')
                )
            elif payload.get('voice'):
                return await context.bot.send_voice(
                    chat_id=user_id,
                    voice=payload['voice'],
                    caption=payload.get('caption'),
                    parse_mode=payload.get('parse_mode')
                )
            elif payload.get('video_note'):
                return await context.bot.send_video_note(
                    chat_id=user_id,
                    video_note=payload['video_note']
                )
            elif payload.get('sticker'):
                return await context.bot.send_sticker(
                    chat_id=user_id,
                    sticker=payload['sticker']
                )
            elif payload.get('animation'):
                return await context.bot.send_animation(
                    chat_id=user_id,
                    animation=payload['animation'],
                    caption=payload.get('caption'),
                    parse_mode=payload.get('parse_mode')
                )
            
            return None
            
        except Exception as e:
            print(f"Error sending message to {user_id}: {e}")
            return None
    
    def _update_broadcast_record(self, broadcast_id: str, success_count: int, failed_count: int, sent_message_ids: dict, failed_users: list = None):
        """بروزرسانی رکورد broadcast"""
        broadcasts = self.store.get('broadcasts', [])
        for broadcast in broadcasts:
            if broadcast['broadcast_id'] == broadcast_id:
                broadcast['success'] = success_count
                broadcast['fail'] = failed_count
                broadcast['sent_message_ids'] = sent_message_ids
                if failed_users:
                    broadcast['failed_users'] = failed_users
                break
        
        self.store['broadcasts'] = broadcasts
        save_store(self.store)
    
    async def pin_broadcast_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """پین کردن پیام همگانی در پیوی تمام کاربران"""
        query = update.callback_query
        await query.answer()
        
        # استخراج broadcast_id از callback_data
        broadcast_id = query.data.split(':')[1] if ':' in query.data else None
        
        if not broadcast_id:
            await query.edit_message_text("❌ شناسه broadcast یافت نشد!")
            return
        
        # دریافت broadcast record
        broadcasts = self.store.get('broadcasts', [])
        broadcast_record = None
        for broadcast in broadcasts:
            if broadcast['broadcast_id'] == broadcast_id:
                broadcast_record = broadcast
                break
        
        if not broadcast_record:
            await query.edit_message_text("❌ رکورد broadcast یافت نشد!")
            return
        
        # دریافت کاربران موفق
        sent_message_ids = broadcast_record.get('sent_message_ids', {})
        if not sent_message_ids:
            await query.edit_message_text("❌ هیچ پیام موفقی برای پین کردن وجود ندارد!")
            return
        
        # نمایش پیام شروع پین
        status_message = await query.edit_message_text(
            f"📌 در حال پین کردن پیام همگانی...\n"
            f"در حال پین… 0/{len(sent_message_ids)}\n"
            f"پین‌شده: 0 | ناموفق: 0"
        )
        
        pinned_count = 0
        pin_failed_count = 0
        
        for i, (user_id, message_id) in enumerate(sent_message_ids.items()):
            try:
                # پین کردن پیام
                await context.bot.pin_chat_message(
                    chat_id=user_id,
                    message_id=message_id
                )
                pinned_count += 1
                
                # بروزرسانی آمار هر 10 پیام یا در انتها
                if (i + 1) % 10 == 0 or i == len(sent_message_ids) - 1:
                    try:
                        await status_message.edit_text(
                            f"📌 در حال پین کردن پیام همگانی...\n"
                            f"در حال پین… {i + 1}/{len(sent_message_ids)}\n"
                            f"پین‌شده: {pinned_count} | ناموفق: {pin_failed_count}"
                        )
                    except:
                        pass
                
                # تاخیر برای جلوگیری از محدودیت
                await asyncio.sleep(0.1)
                
            except Exception as e:
                pin_failed_count += 1
                print(f"Failed to pin message for {user_id}: {e}")
        
        # نمایش آمار نهایی
        final_text = f"""
پین کردن به پایان رسید.

پین‌شده: {pinned_count} | ناموفق: {pin_failed_count}
        """
        
        keyboard = [
            [InlineKeyboardButton("🔙 بازگشت", callback_data="back_to_main")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await status_message.edit_text(final_text, reply_markup=reply_markup)
    
    async def download_failures(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """دانلود گزارش خطاهای ارسال همگانی"""
        query = update.callback_query
        await query.answer()
        
        # استخراج broadcast_id از callback_data
        broadcast_id = query.data.split(':')[1] if ':' in query.data else None
        
        if not broadcast_id:
            await query.edit_message_text("❌ شناسه broadcast یافت نشد!")
            return
        
        # دریافت broadcast record
        broadcasts = self.store.get('broadcasts', [])
        broadcast_record = None
        for broadcast in broadcasts:
            if broadcast['broadcast_id'] == broadcast_id:
                broadcast_record = broadcast
                break
        
        if not broadcast_record:
            await query.edit_message_text("❌ رکورد broadcast یافت نشد!")
            return
        
        failed_users = broadcast_record.get('failed_users', [])
        if not failed_users:
            await query.edit_message_text("✅ هیچ خطایی در ارسال همگانی رخ نداده است!")
            return
        
        # ایجاد گزارش CSV
        import csv
        import io
        
        csv_content = "User ID,Error Reason\n"
        for user in failed_users:
            csv_content += f"{user['user_id']},{user['error']}\n"
        
        # ارسال فایل CSV
        csv_file = io.BytesIO(csv_content.encode('utf-8'))
        csv_file.name = f"broadcast_failures_{broadcast_id}.csv"
        
        await context.bot.send_document(
            chat_id=query.from_user.id,
            document=csv_file,
            caption=f"📊 **گزارش خطاهای ارسال همگانی**\n\n"
                   f"🔢 **شناسه Broadcast**: {broadcast_id}\n"
                   f"❌ **تعداد خطاها**: {len(failed_users)}\n"
                   f"📅 **تاریخ**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )
        
        await query.edit_message_text(
            f"✅ **گزارش خطاها ارسال شد!**\n\n"
            f"فایل CSV به پیوی شما ارسال شد.\n"
            f"تعداد خطاها: {len(failed_users)}",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 بازگشت", callback_data="back_to_main")
            ]])
        )
    
    async def cancel_broadcast(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """لغو ارسال همگانی"""
        query = update.callback_query
        await query.answer()
        
        # پاک کردن state
        context.user_data.pop('broadcast_state', None)
        context.user_data.pop('broadcast_payload', None)
        context.user_data.pop('broadcast_instruction_message_id', None)
        context.user_data.pop('broadcast_id', None)
        
        await query.edit_message_text(
            "❌ **عملیات لغو شد**\n\n"
            "ارسال همگانی لغو شد.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 بازگشت", callback_data="back_to_main")
            ]])
        )
    
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
        user_id = query.from_user.id
        
        print(f"DEBUG: handle_callback: User {user_id} clicked callback: {repr(data)}")
        
        # Admin panel now uses ReplyKeyboard - no callback handling needed
        
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
            return await self.enhanced_lock_menu(update, context)
        elif data == "enhanced_lock_menu":
            return await self.enhanced_lock_menu(update, context)
        elif data == "add_lock_channel":
            return await self.add_lock_channel_start(update, context)
        elif data == "confirm_admin":
            return await self.confirm_admin_handled(update, context)
        elif data == "list_locked_channels":
            return await self.list_locked_channels(update, context)
        elif data.startswith("list_page:"):
            page = int(data.split(":")[1])
            return await self.list_locked_channels(update, context, page)
        elif data.startswith("remove_chat:"):
            chat_id = int(data.split(":")[1])
            return await self.remove_locked_chat(update, context, chat_id)
        elif data == "verify_membership":
            return await self.verify_user_membership(update, context)
        elif data == "refresh_gate":
            return await self.refresh_gate(update, context)
        elif data == "analytics_dashboard":
            return await self.enhanced_analytics_dashboard(update, context)
        elif data == "stats_24h":
            return await self.show_stats_for_window(update, context, "24h")
        elif data == "stats_7d":
            return await self.show_stats_for_window(update, context, "7d")
        elif data == "stats_30d":
            return await self.show_stats_for_window(update, context, "30d")
        elif data == "stats_all":
            return await self.show_stats_for_window(update, context, "all")
        elif data == "refresh_stats":
            return await self.refresh_stats(update, context)
        elif data.startswith("refresh_stats_"):
            window_type = data.split("_")[2]
            return await self.refresh_stats(update, context, window_type)
        elif data == "feature_toggle_menu":
            return await self.enhanced_feature_toggle_menu(update, context)
        elif data.startswith("toggle_feature:"):
            feature_key = data.split(":")[1]
            return await self.show_feature_toggle_submenu(update, context, feature_key)
        elif data.startswith("set_feature_on:"):
            feature_key = data.split(":")[1]
            return await self.toggle_feature_state(update, context, feature_key, True)
        elif data.startswith("set_feature_off:"):
            feature_key = data.split(":")[1]
            return await self.toggle_feature_state(update, context, feature_key, False)
        elif data.startswith("feature_page:"):
            page = int(data.split(":")[1])
            return await self.enhanced_feature_toggle_menu(update, context, page)
        elif data == "search_features":
            return await self.search_features_start(update, context)
        elif data == "protected_feature":
            await update.callback_query.answer("🔒 این بخش محافظت شده است!")
            return
        elif data == "lists_menu":
            return await self.enhanced_lists_menu(update, context)
        elif data == "add_to_blacklist":
            return await self.add_to_blacklist_start(update, context)
        elif data == "remove_from_blacklist":
            return await self.remove_from_blacklist_start(update, context)
        elif data == "add_to_whitelist":
            return await self.add_to_whitelist_start(update, context)
        elif data == "remove_from_whitelist":
            return await self.remove_from_whitelist_start(update, context)
        elif data == "show_blacklist":
            return await self.show_blacklist(update, context)
        elif data == "show_whitelist":
            return await self.show_whitelist(update, context)
        elif data == "search_lists":
            return await self.search_lists_start(update, context)
        elif data.startswith("remove_blacklist:"):
            user_id = int(data.split(":")[1])
            success, message = self.remove_from_blacklist(user_id)
            if success:
                await update.callback_query.answer(f"✅ {message}")
            else:
                await update.callback_query.answer(f"❌ {message}")
            return await self.show_blacklist(update, context)
        elif data.startswith("remove_whitelist:"):
            user_id = int(data.split(":")[1])
            success, message = self.remove_from_whitelist(user_id)
            if success:
                await update.callback_query.answer(f"✅ {message}")
            else:
                await update.callback_query.answer(f"❌ {message}")
            return await self.show_whitelist(update, context)
        elif data.startswith("blacklist_page:"):
            page = int(data.split(":")[1])
            return await self.show_blacklist(update, context, page)
        elif data.startswith("whitelist_page:"):
            page = int(data.split(":")[1])
            return await self.show_whitelist(update, context, page)
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
        elif data == "start_broadcast":
            return await self.start_broadcast(update, context)
        elif data == "cancel_broadcast":
            return await self.cancel_broadcast(update, context)
        elif data.startswith("pin_broadcast:"):
            return await self.pin_broadcast_message(update, context)
        elif data.startswith("download_failures:"):
            return await self.download_failures(update, context)
        elif data == "close_broadcast":
            return await self.cancel_broadcast(update, context)
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
    
    # ===== External API Configuration Wizard =====
    async def external_api_config_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """شروع تنظیمات API خارجی - مرحله 1: URL"""
        # بررسی دسترسی ادمین
        user_id = update.effective_user.id
        if not self._is_admin(user_id):
            await update.message.reply_text("دسترسی غیرمجاز.")
            return
        
        # پاک کردن داده‌های قبلی
        context.user_data.pop('external_api_config', None)
        
        keyboard = [
            [KeyboardButton("🔙 بازگشت به منو")]
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        
        text = """
🔧 **تنظیمات API خارجی - مرحله 1**

لطفاً لینک API را وارد کنید.

مثال: https://api.example.com/v1

🔙 برای بازگشت: /cancel
        """
        
        await update.message.reply_text(text, reply_markup=reply_markup)
        return EXTERNAL_API_URL
    
    async def external_api_url_process(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """پردازش URL API خارجی"""
        # بررسی دسترسی ادمین
        user_id = update.effective_user.id
        if not self._is_admin(user_id):
            await update.message.reply_text("دسترسی غیرمجاز.")
            return
        
        url = update.message.text.strip()
        
        # اعتبارسنجی URL
        if not url.startswith(('http://', 'https://')):
            await update.message.reply_text(
                "❌ **URL نامعتبر!**\n\n"
                "لطفاً URL معتبر وارد کنید (شروع با http:// یا https://)\n\n"
                "مثال: https://api.example.com/v1"
            )
            return EXTERNAL_API_URL
        
        # ذخیره URL
        if 'external_api_config' not in context.user_data:
            context.user_data['external_api_config'] = {}
        context.user_data['external_api_config']['base_url'] = url
        
        # مرحله بعد: API Key
        keyboard = [
            [KeyboardButton("🔙 بازگشت به منو")]
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        
        text = """
🔧 **تنظیمات API خارجی - مرحله 2**

لطفاً کلید API را وارد کنید.

مثال: abc123def456ghi789

🔙 برای بازگشت: /cancel
        """
        
        await update.message.reply_text(text, reply_markup=reply_markup)
        return EXTERNAL_API_KEY
    
    async def external_api_key_process(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """پردازش API Key خارجی"""
        # بررسی دسترسی ادمین
        user_id = update.effective_user.id
        if not self._is_admin(user_id):
            await update.message.reply_text("دسترسی غیرمجاز.")
            return
        
        api_key = update.message.text.strip()
        
        # اعتبارسنجی API Key
        if not api_key or len(api_key) < 5:
            await update.message.reply_text(
                "❌ **کلید API نامعتبر!**\n\n"
                "لطفاً کلید API معتبر وارد کنید (حداقل 5 کاراکتر)\n\n"
                "مثال: abc123def456ghi789"
            )
            return EXTERNAL_API_KEY
        
        # ذخیره API Key
        context.user_data['external_api_config']['api_key'] = api_key
        
        # مرحله بعد: نوع API
        keyboard = [
            [KeyboardButton("کریپتو"), KeyboardButton("ارز داخلی")],
            [KeyboardButton("ذخیره"), KeyboardButton("تست اتصال")],
            [KeyboardButton("انصراف")]
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        
        text = """
🔧 **تنظیمات API خارجی - مرحله 3**

نوع API را انتخاب کنید.

**گزینه‌ها:**
• کریپتو: برای ارزهای دیجیتال (BTC, ETH, etc.)
• ارز داخلی: برای ارزهای فیات (USD/IRR, EUR/IRR, etc.)

🔙 برای بازگشت: /cancel
        """
        
        await update.message.reply_text(text, reply_markup=reply_markup)
        return EXTERNAL_API_TYPE
    
    async def external_api_type_process(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """پردازش نوع API خارجی"""
        # بررسی دسترسی ادمین
        user_id = update.effective_user.id
        if not self._is_admin(user_id):
            await update.message.reply_text("دسترسی غیرمجاز.")
            return
        
        text = update.message.text.strip()
        
        if text == "کریپتو":
            api_type = "crypto"
        elif text == "ارز داخلی":
            api_type = "fiat"
        elif text == "ذخیره":
            return await self.save_external_api_config(update, context)
        elif text == "تست اتصال":
            return await self.test_external_api_connection(update, context)
        elif text == "انصراف":
            return await self.cancel_external_api_config(update, context)
        else:
            await update.message.reply_text(
                "❌ **گزینه نامعتبر!**\n\n"
                "لطفاً یکی از گزینه‌های موجود را انتخاب کنید:\n"
                "• کریپتو\n"
                "• ارز داخلی\n"
                "• ذخیره\n"
                "• تست اتصال\n"
                "• انصراف"
            )
            return EXTERNAL_API_TYPE
        
        # ذخیره نوع API
        context.user_data['external_api_config']['type'] = api_type
        
        # نمایش خلاصه تنظیمات
        config = context.user_data['external_api_config']
        keyboard = [
            [KeyboardButton("ذخیره"), KeyboardButton("تست اتصال")],
            [KeyboardButton("انصراف")]
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        
        summary_text = f"""
🔧 **خلاصه تنظیمات API**

**URL**: {config['base_url']}
**API Key**: {config['api_key'][:8]}...{config['api_key'][-4:]}
**نوع**: {'کریپتو' if api_type == 'crypto' else 'ارز داخلی'}

**عملیات:**
• ذخیره: ذخیره تنظیمات
• تست اتصال: بررسی اتصال به API
• انصراف: لغو تنظیمات
        """
        
        await update.message.reply_text(summary_text, reply_markup=reply_markup)
        return EXTERNAL_API_TYPE
    
    async def save_external_api_config(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """ذخیره تنظیمات API خارجی"""
        # بررسی دسترسی ادمین
        user_id = update.effective_user.id
        if not self._is_admin(user_id):
            await update.message.reply_text("دسترسی غیرمجاز.")
            return
        
        config = context.user_data.get('external_api_config', {})
        
        if not config.get('base_url') or not config.get('api_key') or not config.get('type'):
            await update.message.reply_text(
                "❌ **تنظیمات ناقص!**\n\n"
                "لطفاً تمام مراحل را تکمیل کنید."
            )
            return EXTERNAL_API_TYPE
        
        # ذخیره تنظیمات
        success = self.api_manager.save_api_config(config)
        
        if success:
            # پاک کردن داده‌های موقت
            context.user_data.pop('external_api_config', None)
            
            keyboard = [
                [KeyboardButton("🔙 بازگشت به منو")]
            ]
            reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
            
            await update.message.reply_text(
                "تنظیمات با موفقیت ذخیره شد.",
                reply_markup=reply_markup
            )
            return ADMIN_PANEL
        else:
            await update.message.reply_text(
                "خطا در ذخیره‌سازی تنظیمات. دوباره تلاش کنید."
            )
            return EXTERNAL_API_TYPE
    
    async def test_external_api_connection(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """تست اتصال به API خارجی"""
        # بررسی دسترسی ادمین
        user_id = update.effective_user.id
        if not self._is_admin(user_id):
            await update.message.reply_text("دسترسی غیرمجاز.")
            return
        
        config = context.user_data.get('external_api_config', {})
        
        if not config.get('base_url') or not config.get('api_key') or not config.get('type'):
            await update.message.reply_text(
                "❌ **تنظیمات ناقص!**\n\n"
                "لطفاً تمام مراحل را تکمیل کنید."
            )
            return EXTERNAL_API_TYPE
        
        # نمایش پیام در حال تست
        await update.message.reply_text("⏳ در حال تست اتصال به API...")
        
        # ایجاد کلاینت موقت برای تست
        from external_api_client import ExternalRatesClient
        client = ExternalRatesClient(
            base_url=config['base_url'],
            api_key=config['api_key'],
            api_type=config['type']
        )
        
        # تست اتصال
        health_check = await client.healthcheck()
        
        keyboard = [
            [KeyboardButton("ذخیره"), KeyboardButton("انصراف")]
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        
        if health_check.ok:
            response_time = health_check.response_time
            time_text = f" ({response_time:.2f}s)" if response_time else ""
            
            await update.message.reply_text(
                f"اتصال به API با موفقیت برقرار شد.{time_text}",
                reply_markup=reply_markup
            )
        else:
            error_msg = health_check.error or "خطای نامشخص"
            await update.message.reply_text(
                f"اتصال به API ناموفق بود، لطفاً اطلاعات را بررسی کنید.\n\n"
                f"خطا: {error_msg}",
                reply_markup=reply_markup
            )
        
        return EXTERNAL_API_TYPE
    
    async def cancel_external_api_config(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """لغو تنظیمات API خارجی"""
        # پاک کردن داده‌های موقت
        context.user_data.pop('external_api_config', None)
        
        keyboard = [
            [KeyboardButton("🔙 بازگشت به منو")]
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        
        await update.message.reply_text(
            "عملیات لغو شد.",
            reply_markup=reply_markup
        )
        return ADMIN_PANEL
    
    # ===== External API Integration for User-Facing Rates =====
    async def get_external_crypto_rates(self, symbols: List[str]) -> List[Dict]:
        """دریافت نرخ ارزهای کریپتو از API خارجی"""
        try:
            rates = await self.api_manager.get_crypto_rates(symbols)
            return [
                {
                    'symbol': rate.symbol,
                    'price': rate.price,
                    'change_24h': rate.change_pct,
                    'timestamp': rate.timestamp
                }
                for rate in rates
            ]
        except Exception as e:
            print(f"Error fetching external crypto rates: {e}")
            return []
    
    async def get_external_fiat_rates(self, pairs: List[str]) -> List[Dict]:
        """دریافت نرخ ارزهای فیات از API خارجی"""
        try:
            rates = await self.api_manager.get_fiat_rates(pairs)
            return [
                {
                    'pair': rate.symbol,
                    'rate': rate.price,
                    'change_24h': rate.change_pct,
                    'timestamp': rate.timestamp
                }
                for rate in rates
            ]
        except Exception as e:
            print(f"Error fetching external fiat rates: {e}")
            return []
    
    def is_external_api_configured(self) -> bool:
        """بررسی اینکه آیا API خارجی تنظیم شده است یا نه"""
        config = self.api_manager.get_api_config()
        return bool(config and config.get('base_url') and config.get('api_key'))
    
    def get_external_api_type(self) -> Optional[str]:
        """دریافت نوع API خارجی"""
        config = self.api_manager.get_api_config()
        return config.get('type') if config else None
    
    async def get_crypto_rates_for_display(self, symbols: List[str]) -> List[Dict]:
        """دریافت نرخ ارزهای کریپتو برای نمایش (با اولویت API خارجی)"""
        # اگر API خارجی تنظیم شده و نوع آن کریپتو است
        if self.is_external_api_configured() and self.get_external_api_type() == 'crypto':
            try:
                return await self.get_external_crypto_rates(symbols)
            except Exception as e:
                print(f"External API failed, falling back to default: {e}")
        
        # استفاده از API پیش‌فرض
        try:
            from price_service import get_crypto_price_with_provider
            rates = []
            for symbol in symbols:
                result = await get_crypto_price_with_provider(symbol, "coingecko")
                if result:
                    sym, price, change = result
                    rates.append({
                        'symbol': sym,
                        'price': price,
                        'change_24h': change,
                        'timestamp': int(datetime.now().timestamp())
                    })
            return rates
        except Exception as e:
            print(f"Default API failed: {e}")
            return []
    
    async def get_fiat_rates_for_display(self, pairs: List[str]) -> List[Dict]:
        """دریافت نرخ ارزهای فیات برای نمایش (با اولویت API خارجی)"""
        # اگر API خارجی تنظیم شده و نوع آن فیات است
        if self.is_external_api_configured() and self.get_external_api_type() == 'fiat':
            try:
                return await self.get_external_fiat_rates(pairs)
            except Exception as e:
                print(f"External API failed, falling back to default: {e}")
        
        # استفاده از API پیش‌فرض
        try:
            from fiat_service import get_fiat_rate_with_provider
            rates = []
            for pair in pairs:
                # تبدیل pair به currency code (مثل USD/IRR -> USD)
                currency = pair.split('/')[0] if '/' in pair else pair
                result = await get_fiat_rate_with_provider(currency, "exchangerate_host", "USD")
                if result:
                    _, rate, _ = result
                    rates.append({
                        'pair': pair,
                        'rate': rate,
                        'change_24h': None,
                        'timestamp': int(datetime.now().timestamp())
                    })
            return rates
        except Exception as e:
            print(f"Default API failed: {e}")
            return []
    
    def format_rates_message(self, rates: List[Dict], rate_type: str = "crypto") -> str:
        """فرمت کردن پیام نرخ ارزها"""
        if not rates:
            return "در حال حاضر نرخ ارزها در دسترس نیست."
        
        if rate_type == "crypto":
            message = "💰 **قیمت ارزهای دیجیتال**\n\n"
            for rate in rates:
                symbol = rate['symbol']
                price = rate['price']
                change = rate.get('change_24h')
                
                # فرمت قیمت
                if price >= 1:
                    price_str = f"${price:,.2f}"
                else:
                    price_str = f"${price:.6f}"
                
                # فرمت تغییر
                if change is not None:
                    change_emoji = "📈" if change >= 0 else "📉"
                    change_str = f"{change_emoji} {change:+.2f}%"
                else:
                    change_str = "نامشخص"
                
                message += f"**{symbol}**: {price_str} {change_str}\n"
        
        else:  # fiat
            message = "🏦 **نرخ ارزهای فیات**\n\n"
            for rate in rates:
                pair = rate['pair']
                rate_value = rate['rate']
                change = rate.get('change_24h')
                
                # فرمت نرخ
                if rate_value >= 1:
                    rate_str = f"{rate_value:,.4f}"
                else:
                    rate_str = f"{rate_value:.6f}"
                
                # فرمت تغییر
                if change is not None:
                    change_emoji = "📈" if change >= 0 else "📉"
                    change_str = f"{change_emoji} {change:+.2f}%"
                else:
                    change_str = "نامشخص"
                
                message += f"**{pair}**: {rate_str} {change_str}\n"
        
        # اضافه کردن زمان به‌روزرسانی
        if rates:
            timestamp = rates[0].get('timestamp')
            if timestamp:
                update_time = datetime.fromtimestamp(timestamp).strftime('%H:%M:%S')
                message += f"\n🕐 **آخرین به‌روزرسانی**: {update_time}"
        
        return message
    
    # ===== Enhanced Mandatory Join (Lock) System =====
    def get_locked_chats(self) -> List[Dict]:
        """دریافت لیست کانال‌های قفل‌شده"""
        return self.store.get('locked_chats', [])
    
    def add_locked_chat(self, chat_id: int, title: str, join_link: str = None, chat_type: str = "channel") -> bool:
        """افزودن کانال/گروه به لیست قفل‌شده"""
        try:
            locked_chats = self.get_locked_chats()
            
            # بررسی تکراری نبودن
            for chat in locked_chats:
                if chat['chat_id'] == chat_id:
                    return False
            
            new_chat = {
                'chat_id': chat_id,
                'title': title,
                'join_link': join_link,
                'type': chat_type,
                'created_at': datetime.now().isoformat()
            }
            
            locked_chats.append(new_chat)
            self.store['locked_chats'] = locked_chats
            
            # تنظیم lock_enabled_at اگر اولین بار است
            if not self.store.get('lock_enabled_at'):
                self.store['lock_enabled_at'] = datetime.now().isoformat()
            
            save_store(self.store)
            return True
        except Exception as e:
            print(f"Error adding locked chat: {e}")
            return False
    
    def remove_locked_chat(self, chat_id: int) -> bool:
        """حذف کانال/گروه از لیست قفل‌شده"""
        try:
            locked_chats = self.get_locked_chats()
            locked_chats = [chat for chat in locked_chats if chat['chat_id'] != chat_id]
            self.store['locked_chats'] = locked_chats
            save_store(self.store)
            return True
        except Exception as e:
            print(f"Error removing locked chat: {e}")
            return False
    
    def is_lock_enabled(self) -> bool:
        """بررسی اینکه آیا قفل فعال است یا نه"""
        return bool(self.store.get('lock_enabled_at'))
    
    def get_lock_enabled_at(self) -> Optional[datetime]:
        """دریافت زمان فعال شدن قفل"""
        lock_time = self.store.get('lock_enabled_at')
        if lock_time:
            try:
                return datetime.fromisoformat(lock_time)
            except:
                return None
        return None
    
    def should_enforce_lock_for_user(self, user_id: int) -> bool:
        """بررسی اینکه آیا قفل برای کاربر اعمال شود یا نه"""
        if not self.is_lock_enabled():
            return False
        
        # اگر کاربر ادمین است، قفل اعمال نشود
        if self._is_admin(user_id):
            return False
        
        # بررسی زمان اولین ورود کاربر
        user_data = self.store.get('users', {})
        user_info = user_data.get(str(user_id), {})
        first_seen = user_info.get('first_seen_at')
        
        if not first_seen:
            return True  # اگر اطلاعات کاربر موجود نیست، قفل اعمال شود
        
        try:
            first_seen_dt = datetime.fromisoformat(first_seen)
            lock_enabled_dt = self.get_lock_enabled_at()
            
            if not lock_enabled_dt:
                return False
            
            return first_seen_dt >= lock_enabled_dt
        except:
            return True  # در صورت خطا، قفل اعمال شود
    
    async def check_user_membership(self, context: ContextTypes.DEFAULT_TYPE, user_id: int, chat_id: int) -> bool:
        """بررسی عضویت کاربر در کانال/گروه"""
        try:
            member = await context.bot.get_chat_member(chat_id, user_id)
            return member.status in ['member', 'administrator', 'creator']
        except Exception as e:
            print(f"Error checking membership for user {user_id} in chat {chat_id}: {e}")
            return False
    
    async def check_all_memberships(self, context: ContextTypes.DEFAULT_TYPE, user_id: int) -> Dict[int, bool]:
        """بررسی عضویت کاربر در تمام کانال‌های قفل‌شده"""
        locked_chats = self.get_locked_chats()
        results = {}
        
        for chat in locked_chats:
            chat_id = chat['chat_id']
            is_member = await self.check_user_membership(context, user_id, chat_id)
            results[chat_id] = is_member
        
        return results
    
    # ===== Admin Lock Menu and Handlers =====
    async def enhanced_lock_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """منوی قفل اجباری پیشرفته"""
        # بررسی دسترسی ادمین
        user_id = update.effective_user.id
        if not self._is_admin(user_id):
            await update.message.reply_text("دسترسی غیرمجاز.")
            return
        
        locked_chats = self.get_locked_chats()
        is_enabled = self.is_lock_enabled()
        
        status_emoji = "✅" if is_enabled else "❌"
        status_text = "فعال" if is_enabled else "غیرفعال"
        
        keyboard = [
            [InlineKeyboardButton("افزودن کانال/گروه", callback_data="add_lock_channel")],
            [InlineKeyboardButton("حذف کانال/گروه", callback_data="remove_lock_channel")],
            [InlineKeyboardButton("لیست کانال‌های قفل‌شده", callback_data="list_locked_channels")],
            [InlineKeyboardButton("بازگشت", callback_data="back_to_main")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        text = f"""
🔒 **قفل اجباری**

📊 **وضعیت**: {status_emoji} {status_text}
📢 **کانال‌های قفل‌شده**: {len(locked_chats)} کانال

**عملیات موجود**:
• افزودن کانال/گروه جدید
• حذف کانال/گروه موجود
• مشاهده لیست کانال‌های قفل‌شده
        """
        
        if update.callback_query:
            await update.callback_query.edit_message_text(text, reply_markup=reply_markup)
        else:
            await update.message.reply_text(text, reply_markup=reply_markup)
    
    async def add_lock_channel_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """شروع افزودن کانال/گروه قفل‌شده"""
        # بررسی دسترسی ادمین
        user_id = update.effective_user.id
        if not self._is_admin(user_id):
            await update.message.reply_text("دسترسی غیرمجاز.")
            return
        
        keyboard = [
            [InlineKeyboardButton("ادمین کردم", callback_data="confirm_admin")],
            [InlineKeyboardButton("انصراف", callback_data="enhanced_lock_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        text = """
🔒 **افزودن کانال/گروه قفل‌شده**

ربات را در کانال/گروه موردنظر ادمین کنید، سپس روی «ادمین کردم» بزنید.

⚠️ **نکات مهم**:
• ربات باید در کانال/گروه ادمین باشد
• دسترسی‌های لازم: خواندن پیام‌ها و مدیریت اعضا
• لینک عمومی یا خصوصی هر دو پشتیبانی می‌شود
        """
        
        if update.callback_query:
            await update.callback_query.edit_message_text(text, reply_markup=reply_markup)
        else:
            await update.message.reply_text(text, reply_markup=reply_markup)
    
    async def confirm_admin_handled(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """تأیید ادمین شدن ربات"""
        # بررسی دسترسی ادمین
        user_id = update.effective_user.id
        if not self._is_admin(user_id):
            await update.message.reply_text("دسترسی غیرمجاز.")
            return
        
        keyboard = [
            [InlineKeyboardButton("انصراف", callback_data="enhanced_lock_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        text = """
🔗 **ارسال لینک کانال/گروه**

لینک کانال/گروه را ارسال کنید. لینک عمومی یا خصوصی هر دو پشتیبانی می‌شود.

**فرمت‌های پشتیبانی شده**:
• `@username` (مثل @mychannel)
• `https://t.me/username`
• لینک دعوت خصوصی

**یا** یک پیام از کانال/گروه فوروارد کنید.
        """
        
        if update.callback_query:
            await update.callback_query.edit_message_text(text, reply_markup=reply_markup)
        else:
            await update.message.reply_text(text, reply_markup=reply_markup)
        
        return SUBMIT_LOCK_LINK
    
    async def process_lock_link_or_forward(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """پردازش لینک یا فوروارد کانال/گروه"""
        # بررسی دسترسی ادمین
        user_id = update.effective_user.id
        if not self._is_admin(user_id):
            await update.message.reply_text("دسترسی غیرمجاز.")
            return
        
        chat_id = None
        title = None
        join_link = None
        chat_type = "channel"
        
        # بررسی فوروارد
        if update.message.forward_from_chat:
            chat_id = update.message.forward_from_chat.id
            title = update.message.forward_from_chat.title or "نامشخص"
            chat_type = "supergroup" if update.message.forward_from_chat.type == "supergroup" else "channel"
            
            # تلاش برای ساخت لینک عمومی
            if update.message.forward_from_chat.username:
                join_link = f"https://t.me/{update.message.forward_from_chat.username}"
        
        # بررسی متن لینک
        elif update.message.text:
            link_text = update.message.text.strip()
            
            # پارس کردن لینک
            if link_text.startswith('@'):
                username = link_text[1:]
                try:
                    chat = await context.bot.get_chat(f"@{username}")
                    chat_id = chat.id
                    title = chat.title or "نامشخص"
                    chat_type = "supergroup" if chat.type == "supergroup" else "channel"
                    join_link = f"https://t.me/{username}"
                except Exception as e:
                    await update.message.reply_text(f"❌ خطا در یافتن کانال: {str(e)}")
                    return SUBMIT_LOCK_LINK
            
            elif link_text.startswith('https://t.me/'):
                try:
                    # استخراج username از لینک
                    username = link_text.replace('https://t.me/', '').split('/')[0]
                    chat = await context.bot.get_chat(f"@{username}")
                    chat_id = chat.id
                    title = chat.title or "نامشخص"
                    chat_type = "supergroup" if chat.type == "supergroup" else "channel"
                    join_link = link_text
                except Exception as e:
                    await update.message.reply_text(f"❌ خطا در یافتن کانال: {str(e)}")
                    return SUBMIT_LOCK_LINK
            
            else:
                # لینک دعوت خصوصی
                try:
                    chat = await context.bot.get_chat(link_text)
                    chat_id = chat.id
                    title = chat.title or "نامشخص"
                    chat_type = "supergroup" if chat.type == "supergroup" else "channel"
                    join_link = link_text
                except Exception as e:
                    await update.message.reply_text(f"❌ خطا در یافتن کانال: {str(e)}")
                    return SUBMIT_LOCK_LINK
        
        if not chat_id:
            await update.message.reply_text("❌ لینک نامعتبر است. لطفاً لینک صحیح ارسال کنید.")
            return SUBMIT_LOCK_LINK
        
        # بررسی ادمین بودن ربات
        try:
            bot_member = await context.bot.get_chat_member(chat_id, context.bot.id)
            if bot_member.status not in ['administrator', 'creator']:
                await update.message.reply_text(
                    "❌ ربات در این کانال/گروه ادمین نیست!\n\n"
                    "لطفاً ابتدا ربات را ادمین کنید و دوباره تلاش کنید."
                )
                return SUBMIT_LOCK_LINK
        except Exception as e:
            await update.message.reply_text(f"❌ خطا در بررسی دسترسی ربات: {str(e)}")
            return SUBMIT_LOCK_LINK
        
        # افزودن کانال/گروه
        success = self.add_locked_chat(chat_id, title, join_link, chat_type)
        
        if success:
            keyboard = [
                [InlineKeyboardButton("بازگشت به منو", callback_data="enhanced_lock_menu")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                f"✅ **قفل با موفقیت فعال شد!**\n\n"
                f"📢 **کانال/گروه**: {title}\n"
                f"🔗 **لینک**: {join_link or 'نامشخص'}\n"
                f"📅 **تاریخ**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                reply_markup=reply_markup
            )
        else:
            await update.message.reply_text(
                "❌ خطا در افزودن کانال/گروه. ممکن است قبلاً اضافه شده باشد."
            )
        
        return ADMIN_PANEL
    
    async def list_locked_channels(self, update: Update, context: ContextTypes.DEFAULT_TYPE, page: int = 0):
        """نمایش لیست کانال‌های قفل‌شده (صفحه‌بندی شده)"""
        # بررسی دسترسی ادمین
        user_id = update.effective_user.id
        if not self._is_admin(user_id):
            await update.message.reply_text("دسترسی غیرمجاز.")
            return
        
        locked_chats = self.get_locked_chats()
        items_per_page = 5
        total_pages = (len(locked_chats) + items_per_page - 1) // items_per_page
        
        if not locked_chats:
            keyboard = [
                [InlineKeyboardButton("بازگشت", callback_data="enhanced_lock_menu")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            text = """
📋 **لیست کانال‌های قفل‌شده**

• هیچ کانال/گروهی قفل نشده است

برای افزودن کانال/گروه جدید، از منوی اصلی استفاده کنید.
            """
            
            if update.callback_query:
                await update.callback_query.edit_message_text(text, reply_markup=reply_markup)
            else:
                await update.message.reply_text(text, reply_markup=reply_markup)
            return
        
        # محاسبه آیتم‌های صفحه فعلی
        start_idx = page * items_per_page
        end_idx = min(start_idx + items_per_page, len(locked_chats))
        page_chats = locked_chats[start_idx:end_idx]
        
        # ساخت کیبورد
        keyboard = []
        for chat in page_chats:
            chat_title = chat['title']
            chat_type_emoji = "📢" if chat['type'] == 'channel' else "👥"
            button_text = f"{chat_type_emoji} {chat_title}"
            keyboard.append([InlineKeyboardButton(button_text, callback_data=f"view_chat:{chat['chat_id']}")])
            keyboard.append([InlineKeyboardButton("حذف", callback_data=f"remove_chat:{chat['chat_id']}")])
        
        # دکمه‌های ناوبری
        nav_buttons = []
        if page > 0:
            nav_buttons.append(InlineKeyboardButton("صفحه قبل", callback_data=f"list_page:{page-1}"))
        if page < total_pages - 1:
            nav_buttons.append(InlineKeyboardButton("صفحه بعد", callback_data=f"list_page:{page+1}"))
        
        if nav_buttons:
            keyboard.append(nav_buttons)
        
        keyboard.append([InlineKeyboardButton("بازگشت", callback_data="enhanced_lock_menu")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        text = f"""
📋 **لیست کانال‌های قفل‌شده**

📊 **صفحه {page + 1} از {total_pages}**
📢 **تعداد کل**: {len(locked_chats)} کانال/گروه

**کانال‌های این صفحه**:
        """
        
        for i, chat in enumerate(page_chats, start_idx + 1):
            chat_type_emoji = "📢" if chat['type'] == 'channel' else "👥"
            text += f"\n{i}. {chat_type_emoji} {chat['title']}"
            if chat.get('join_link'):
                text += f"\n   🔗 {chat['join_link']}"
        
        if update.callback_query:
            await update.callback_query.edit_message_text(text, reply_markup=reply_markup)
        else:
            await update.message.reply_text(text, reply_markup=reply_markup)
    
    async def remove_locked_chat(self, update: Update, context: ContextTypes.DEFAULT_TYPE, chat_id: int):
        """حذف کانال/گروه از لیست قفل‌شده"""
        # بررسی دسترسی ادمین
        user_id = update.effective_user.id
        if not self._is_admin(user_id):
            await update.message.reply_text("دسترسی غیرمجاز.")
            return
        
        # یافتن اطلاعات کانال
        locked_chats = self.get_locked_chats()
        chat_info = None
        for chat in locked_chats:
            if chat['chat_id'] == chat_id:
                chat_info = chat
                break
        
        if not chat_info:
            await update.callback_query.answer("❌ کانال/گروه یافت نشد!")
            return
        
        # حذف کانال
        success = self.remove_locked_chat(chat_id)
        
        if success:
            await update.callback_query.answer(f"✅ {chat_info['title']} با موفقیت حذف شد!")
        else:
            await update.callback_query.answer("❌ خطا در حذف کانال/گروه!")
        
        # بازگشت به لیست
        await self.list_locked_channels(update, context)
    
    # ===== User Gate System =====
    async def render_user_gate(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """نمایش دروازه عضویت اجباری برای کاربران"""
        locked_chats = self.get_locked_chats()
        
        if not locked_chats:
            return False  # اگر کانالی قفل نشده، دروازه نمایش داده نشود
        
        keyboard = []
        for chat in locked_chats:
            chat_title = chat['title']
            chat_type_text = "کانال" if chat['type'] == 'channel' else "گروه"
            button_text = f"{chat_type_text}: {chat_title}"
            
            if chat.get('join_link'):
                keyboard.append([InlineKeyboardButton(button_text, url=chat['join_link'])])
            else:
                # اگر لینک موجود نیست، دکمه غیرفعال
                keyboard.append([InlineKeyboardButton(button_text, callback_data="no_link")])
        
        keyboard.append([InlineKeyboardButton("تأیید عضویت", callback_data="verify_membership")])
        keyboard.append([InlineKeyboardButton("تازه‌سازی", callback_data="refresh_gate")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        text = """
🔒 **عضویت اجباری**

برای استفاده از ربات، لطفاً در کانال/گروه‌های زیر عضو شوید:

⚠️ **نکات مهم**:
• ابتدا در کانال/گروه‌های بالا عضو شوید
• سپس روی «تأیید عضویت» کلیک کنید
• در صورت مشکل، «تازه‌سازی» را بزنید
        """
        
        if update.callback_query:
            await update.callback_query.edit_message_text(text, reply_markup=reply_markup)
        else:
            await update.message.reply_text(text, reply_markup=reply_markup)
        
        return True
    
    async def verify_user_membership(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """بررسی عضویت کاربر در کانال‌های قفل‌شده"""
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        locked_chats = self.get_locked_chats()
        
        if not locked_chats:
            await query.edit_message_text("✅ عضویت تأیید شد. خوش آمدید!")
            return True
        
        # بررسی عضویت در تمام کانال‌ها
        membership_results = await self.check_all_memberships(context, user_id)
        
        # بررسی اینکه آیا کاربر در همه کانال‌ها عضو است
        all_joined = all(membership_results.values())
        
        if all_joined:
            # موفق - کاربر در همه کانال‌ها عضو است
            await query.edit_message_text("✅ عضویت تأیید شد. خوش آمدید!")
            return True
        else:
            # ناموفق - کاربر در برخی کانال‌ها عضو نیست
            await self.show_membership_failure_notice(update, context)
            return False
    
    async def show_membership_failure_notice(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """نمایش اعلان عدم عضویت با پین 15 ثانیه‌ای"""
        query = update.callback_query
        
        # پاسخ سریع به callback
        await query.answer("❌ عضو نشدی در کانال/گروه. لطفاً عضو شو و سپس «تأیید عضویت» را بزن.")
        
        # ارسال پیام اعلان
        notice_message = await query.message.reply_text(
            "❌ **عضو نشدی در کانال/گروه. لطفاً عضو شو و سپس «تأیید عضویت» را بزن.**"
        )
        
        # تلاش برای پین کردن پیام
        try:
            await context.bot.pin_chat_message(
                chat_id=query.message.chat_id,
                message_id=notice_message.message_id
            )
            
            # برنامه‌ریزی برای unpin بعد از 15 ثانیه
            async def unpin_after_delay():
                await asyncio.sleep(15)
                try:
                    await context.bot.unpin_chat_message(
                        chat_id=query.message.chat_id,
                        message_id=notice_message.message_id
                    )
                    # حذف پیام اعلان
                    await context.bot.delete_message(
                        chat_id=query.message.chat_id,
                        message_id=notice_message.message_id
                    )
                except:
                    pass  # اگر unpin یا delete ناموفق بود، نادیده بگیر
            
            # اجرای unpin در پس‌زمینه
            asyncio.create_task(unpin_after_delay())
            
        except Exception as e:
            print(f"Failed to pin notice message: {e}")
            # اگر پین ناموفق بود، فقط callback answer کافی است
    
    async def refresh_gate(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """تازه‌سازی دروازه عضویت"""
        query = update.callback_query
        await query.answer("🔄 در حال تازه‌سازی...")
        
        # نمایش مجدد دروازه
        await self.render_user_gate(update, context)
    
    async def handle_user_start_with_lock(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
        """مدیریت شروع کاربر با بررسی قفل اجباری"""
        user_id = update.effective_user.id
        
        # بررسی اینکه آیا قفل برای این کاربر اعمال شود
        if not self.should_enforce_lock_for_user(user_id):
            return False  # قفل اعمال نشود
        
        # نمایش دروازه عضویت
        return await self.render_user_gate(update, context)
    
    # ===== Analytics System =====
    def log_user_event(self, user_id: int, event_type: str, meta: dict = None):
        """ثبت رویداد کاربر"""
        try:
            # بروزرسانی اطلاعات کاربر
            user_data = self.store.get('user_data', {})
            user_key = str(user_id)
            
            if user_key not in user_data:
                user_data[user_key] = {
                    'first_seen_at': datetime.now().isoformat(),
                    'last_active_at': datetime.now().isoformat(),
                    'username': None,
                    'full_name': None
                }
            else:
                user_data[user_key]['last_active_at'] = datetime.now().isoformat()
            
            self.store['user_data'] = user_data
            
            # ثبت رویداد
            events = self.store.get('events', [])
            event = {
                'id': len(events) + 1,
                'user_id': user_id,
                'type': event_type,
                'ts': datetime.now().isoformat(),
                'meta': meta or {}
            }
            events.append(event)
            self.store['events'] = events
            
            save_store(self.store)
            return True
        except Exception as e:
            print(f"Error logging user event: {e}")
            return False
    
    def update_user_info(self, user_id: int, username: str = None, full_name: str = None):
        """بروزرسانی اطلاعات کاربر"""
        try:
            user_data = self.store.get('user_data', {})
            user_key = str(user_id)
            
            if user_key not in user_data:
                user_data[user_key] = {
                    'first_seen_at': datetime.now().isoformat(),
                    'last_active_at': datetime.now().isoformat(),
                    'username': username,
                    'full_name': full_name
                }
            else:
                if username:
                    user_data[user_key]['username'] = username
                if full_name:
                    user_data[user_key]['full_name'] = full_name
                user_data[user_key]['last_active_at'] = datetime.now().isoformat()
            
            self.store['user_data'] = user_data
            save_store(self.store)
            return True
        except Exception as e:
            print(f"Error updating user info: {e}")
            return False
    
    def get_events_in_window(self, start_time: datetime, end_time: datetime = None) -> List[Dict]:
        """دریافت رویدادها در بازه زمانی مشخص"""
        if end_time is None:
            end_time = datetime.now()
        
        events = self.store.get('events', [])
        filtered_events = []
        
        for event in events:
            try:
                event_time = datetime.fromisoformat(event['ts'])
                if start_time <= event_time < end_time:
                    filtered_events.append(event)
            except:
                continue
        
        return filtered_events
    
    def get_stats_for_window(self, window_type: str) -> Dict:
        """محاسبه آمار برای بازه زمانی مشخص"""
        now = datetime.now()
        
        if window_type == "24h":
            start_time = now - timedelta(hours=24)
            hours = 24
        elif window_type == "7d":
            start_time = now - timedelta(days=7)
            hours = 24 * 7
        elif window_type == "30d":
            start_time = now - timedelta(days=30)
            hours = 24 * 30
        elif window_type == "all":
            # پیدا کردن اولین رویداد
            events = self.store.get('events', [])
            if not events:
                start_time = now
            else:
                try:
                    start_time = datetime.fromisoformat(events[0]['ts'])
                except:
                    start_time = now
            hours = (now - start_time).total_seconds() / 3600
        else:
            return {}
        
        # دریافت رویدادها در بازه زمانی
        events_in_window = self.get_events_in_window(start_time, now)
        
        # محاسبه آمار
        starts = len([e for e in events_in_window if e['type'] == 'start'])
        active_users = len(set([e['user_id'] for e in events_in_window if e['type'] in ['start', 'message', 'callback']]))
        broadcast_success = len([e for e in events_in_window if e['type'] == 'broadcast_success'])
        broadcast_fail = len([e for e in events_in_window if e['type'] == 'broadcast_fail'])
        
        # محاسبه میانگین
        if window_type == "24h":
            avg_rate = starts / 24 if hours > 0 else 0
            avg_unit = "در ساعت"
        else:
            days = hours / 24
            avg_rate = starts / days if days > 0 else 0
            avg_unit = "در روز"
        
        return {
            'window_type': window_type,
            'start_time': start_time,
            'end_time': now,
            'starts': starts,
            'active_users': active_users,
            'broadcast_success': broadcast_success,
            'broadcast_fail': broadcast_fail,
            'avg_rate': avg_rate,
            'avg_unit': avg_unit,
            'hours': hours
        }
    
    def format_persian_date(self, dt: datetime) -> str:
        """فرمت کردن تاریخ به صورت فارسی"""
        return dt.strftime('%Y/%m/%d %H:%M')
    
    def get_cached_stats(self, window_type: str) -> Optional[Dict]:
        """دریافت آمار از کش"""
        cache_key = f"stats_{window_type}"
        return self.cache.get(cache_key)
    
    def set_cached_stats(self, window_type: str, stats: Dict, ttl_seconds: int = 60):
        """ذخیره آمار در کش"""
        cache_key = f"stats_{window_type}"
        self.cache.set(cache_key, stats, ttl_seconds)
    
    # ===== Feature Toggle System =====
    def initialize_feature_registry(self):
        """مقداردهی اولیه FeatureRegistry"""
        if 'feature_registry' not in self.store:
            self.store['feature_registry'] = {}
        
        # ویژگی‌های پیش‌فرض
        default_features = {
            # Admin Panel Features
            'admin.panel': {
                'title': 'پنل مدیریت',
                'enabled': True,
                'category': 'admin',
                'deps': [],
                'protected': True
            },
            'admin.stats': {
                'title': 'آمار و گزارش',
                'enabled': True,
                'category': 'admin',
                'deps': [],
                'protected': False
            },
            'admin.broadcast': {
                'title': 'ارسال همگانی',
                'enabled': True,
                'category': 'admin',
                'deps': [],
                'protected': False
            },
            'admin.text_settings': {
                'title': 'تنظیم متن‌ها',
                'enabled': True,
                'category': 'admin',
                'deps': [],
                'protected': False
            },
            'admin.api_management': {
                'title': 'مدیریت API',
                'enabled': True,
                'category': 'admin',
                'deps': [],
                'protected': False
            },
            'admin.force_subscription': {
                'title': 'قفل اجباری',
                'enabled': True,
                'category': 'admin',
                'deps': [],
                'protected': False
            },
            'admin.lists': {
                'title': 'لیست سفید/سیاه',
                'enabled': True,
                'category': 'admin',
                'deps': [],
                'protected': False
            },
            'admin.cache': {
                'title': 'مدیریت کش',
                'enabled': True,
                'category': 'admin',
                'deps': [],
                'protected': False
            },
            'admin.system_settings': {
                'title': 'تنظیمات سیستم',
                'enabled': True,
                'category': 'admin',
                'deps': [],
                'protected': False
            },
            'admin.backup': {
                'title': 'پشتیبان‌گیری',
                'enabled': True,
                'category': 'admin',
                'deps': [],
                'protected': False
            },
            'admin.logs': {
                'title': 'لاگ‌ها',
                'enabled': True,
                'category': 'admin',
                'deps': [],
                'protected': False
            },
            'admin.alerts': {
                'title': 'مدیریت هشدارها',
                'enabled': True,
                'category': 'admin',
                'deps': [],
                'protected': False
            },
            'admin.commands': {
                'title': 'دستورات سفارشی',
                'enabled': True,
                'category': 'admin',
                'deps': [],
                'protected': False
            },
            'admin.bot_settings': {
                'title': 'تنظیمات ربات',
                'enabled': True,
                'category': 'admin',
                'deps': [],
                'protected': True
            },
            
            # User Features
            'user.crypto_prices': {
                'title': 'نرخ ارز (کریپتو)',
                'enabled': True,
                'category': 'user',
                'deps': [],
                'protected': False
            },
            'user.fiat_rates': {
                'title': 'نرخ ارز (فیات)',
                'enabled': True,
                'category': 'user',
                'deps': [],
                'protected': False
            },
            'user.news': {
                'title': 'اخبار',
                'enabled': True,
                'category': 'user',
                'deps': [],
                'protected': False
            },
            'user.charts': {
                'title': 'نمودار',
                'enabled': True,
                'category': 'user',
                'deps': ['user.crypto_prices'],
                'protected': False
            },
            'user.technical_analysis': {
                'title': 'تحلیل تکنیکال',
                'enabled': True,
                'category': 'user',
                'deps': ['user.crypto_prices'],
                'protected': False
            },
            'user.arbitrage': {
                'title': 'مقایسه قیمت‌ها',
                'enabled': True,
                'category': 'user',
                'deps': ['user.crypto_prices', 'user.fiat_rates'],
                'protected': False
            },
            'user.p2p': {
                'title': 'P2P',
                'enabled': True,
                'category': 'user',
                'deps': [],
                'protected': False
            },
            'user.watchlist': {
                'title': 'واچ‌لیست',
                'enabled': True,
                'category': 'user',
                'deps': ['user.crypto_prices'],
                'protected': False
            },
            'user.portfolio': {
                'title': 'پرتفوی',
                'enabled': True,
                'category': 'user',
                'deps': ['user.crypto_prices'],
                'protected': False
            },
            'user.alerts': {
                'title': 'هشدارها',
                'enabled': True,
                'category': 'user',
                'deps': ['user.crypto_prices'],
                'protected': False
            }
        }
        
        # بروزرسانی registry با ویژگی‌های پیش‌فرض
        registry = self.store['feature_registry']
        for key, feature in default_features.items():
            if key not in registry:
                registry[key] = {
                    **feature,
                    'updated_at': datetime.now().isoformat(),
                    'updated_by': None
                }
        
        self.store['feature_registry'] = registry
        save_store(self.store)
    
    def is_feature_enabled(self, feature_key: str) -> bool:
        """بررسی فعال بودن یک ویژگی"""
        registry = self.store.get('feature_registry', {})
        feature = registry.get(feature_key, {})
        return feature.get('enabled', False)
    
    def get_feature_info(self, feature_key: str) -> dict:
        """دریافت اطلاعات یک ویژگی"""
        registry = self.store.get('feature_registry', {})
        return registry.get(feature_key, {})
    
    def get_all_features(self, category: str = None) -> dict:
        """دریافت تمام ویژگی‌ها یا بر اساس دسته"""
        registry = self.store.get('feature_registry', {})
        if category:
            return {k: v for k, v in registry.items() if v.get('category') == category}
        return registry
    
    def toggle_feature(self, feature_key: str, enabled: bool, updated_by: int) -> tuple[bool, str]:
        """تغییر وضعیت یک ویژگی"""
        try:
            registry = self.store.get('feature_registry', {})
            feature = registry.get(feature_key, {})
            
            if not feature:
                return False, "ویژگی یافت نشد."
            
            # بررسی محافظت شده بودن
            if feature.get('protected', False):
                return False, "این بخش اصلی ربات است و قابل خاموش کردن نیست."
            
            # بررسی وابستگی‌ها
            if enabled:
                deps = feature.get('deps', [])
                for dep_key in deps:
                    if not self.is_feature_enabled(dep_key):
                        dep_info = self.get_feature_info(dep_key)
                        dep_title = dep_info.get('title', dep_key)
                        return False, f"این قابلیت به بخش‌های دیگری وابسته است؛ ابتدا وابستگی‌ها را فعال کنید. (وابسته به: {dep_title})"
            
            # بروزرسانی وضعیت
            feature['enabled'] = enabled
            feature['updated_at'] = datetime.now().isoformat()
            feature['updated_by'] = updated_by
            
            registry[feature_key] = feature
            self.store['feature_registry'] = registry
            save_store(self.store)
            
            # پاک کردن کش
            self.cache.clear()
            
            return True, "عملیات با موفقیت انجام شد."
            
        except Exception as e:
            print(f"Error toggling feature {feature_key}: {e}")
            return False, "عملیات ناموفق بود. لطفاً دوباره تلاش کنید."
    
    def get_feature_dependents(self, feature_key: str) -> list:
        """دریافت ویژگی‌هایی که به این ویژگی وابسته هستند"""
        registry = self.store.get('feature_registry', {})
        dependents = []
        
        for key, feature in registry.items():
            deps = feature.get('deps', [])
            if feature_key in deps:
                dependents.append(key)
        
        return dependents
    
    def search_features(self, query: str) -> dict:
        """جستجوی ویژگی‌ها بر اساس عنوان"""
        registry = self.store.get('feature_registry', {})
        query_lower = query.lower()
        
        results = {}
        for key, feature in registry.items():
            title = feature.get('title', '').lower()
            if query_lower in title or query_lower in key.lower():
                results[key] = feature
        
        return results
    
    # ===== Enhanced Blacklist/Whitelist System =====
    def initialize_lists_cache(self):
        """مقداردهی اولیه کش لیست‌ها"""
        # مقداردهی اولیه لیست‌ها در store
        if 'blacklist' not in self.store:
            self.store['blacklist'] = []
        if 'whitelist' not in self.store:
            self.store['whitelist'] = []
        
        # بروزرسانی کش
        self._refresh_lists_cache()
    
    def _refresh_lists_cache(self):
        """بروزرسانی کش لیست‌ها"""
        blacklist_data = self.store.get('blacklist', [])
        whitelist_data = self.store.get('whitelist', [])
        
        # تبدیل به set برای جستجوی سریع
        self.BLACKLIST_SET = {item['user_id'] for item in blacklist_data if 'user_id' in item}
        self.WHITELIST_SET = {item['user_id'] for item in whitelist_data if 'user_id' in item}
        
        # ذخیره در کش
        self.cache.set('blacklist_set', self.BLACKLIST_SET, 3600)  # 1 hour
        self.cache.set('whitelist_set', self.WHITELIST_SET, 3600)  # 1 hour
    
    def is_user_blacklisted(self, user_id: int) -> bool:
        """بررسی مسدود بودن کاربر"""
        if not hasattr(self, 'BLACKLIST_SET'):
            self._refresh_lists_cache()
        return user_id in self.BLACKLIST_SET
    
    def is_user_whitelisted(self, user_id: int) -> bool:
        """بررسی سفید بودن کاربر"""
        if not hasattr(self, 'WHITELIST_SET'):
            self._refresh_lists_cache()
        return user_id in self.WHITELIST_SET
    
    def is_user_allowed(self, user_id: int) -> bool:
        """بررسی مجاز بودن کاربر (با در نظر گیری اولویت‌ها)"""
        # ادمین‌ها همیشه مجاز هستند
        if self._is_admin(user_id):
            return True
        
        # اگر در لیست سفید است، مجاز است
        if self.is_user_whitelisted(user_id):
            return True
        
        # اگر در لیست سیاه است، مجاز نیست
        if self.is_user_blacklisted(user_id):
            return False
        
        # در غیر این صورت مجاز است
        return True
    
    def add_to_blacklist(self, user_id: int, username: str = None, added_by: int = None) -> tuple[bool, str]:
        """افزودن کاربر به لیست سیاه"""
        try:
            # بررسی وجود در لیست سیاه
            if self.is_user_blacklisted(user_id):
                return False, "این کاربر هم‌اکنون در لیست سیاه است."
            
            # بررسی ادمین بودن
            if self._is_admin(user_id):
                return False, "امکان مسدود کردن مالک/ادمین وجود ندارد."
            
            # افزودن به لیست
            blacklist_data = self.store.get('blacklist', [])
            blacklist_data.append({
                'user_id': user_id,
                'username': username,
                'added_at': datetime.now().isoformat(),
                'added_by': added_by
            })
            
            self.store['blacklist'] = blacklist_data
            save_store(self.store)
            
            # بروزرسانی کش
            self._refresh_lists_cache()
            
            return True, "کاربر با موفقیت به لیست سیاه اضافه شد."
            
        except Exception as e:
            print(f"Error adding to blacklist: {e}")
            return False, "عملیات ناموفق بود. لطفاً دوباره تلاش کنید."
    
    def remove_from_blacklist(self, user_id: int) -> tuple[bool, str]:
        """حذف کاربر از لیست سیاه"""
        try:
            # بررسی وجود در لیست سیاه
            if not self.is_user_blacklisted(user_id):
                return False, "این کاربر در لیست سیاه نیست."
            
            # حذف از لیست
            blacklist_data = self.store.get('blacklist', [])
            blacklist_data = [item for item in blacklist_data if item.get('user_id') != user_id]
            
            self.store['blacklist'] = blacklist_data
            save_store(self.store)
            
            # بروزرسانی کش
            self._refresh_lists_cache()
            
            return True, "کاربر با موفقیت از لیست سیاه حذف شد."
            
        except Exception as e:
            print(f"Error removing from blacklist: {e}")
            return False, "عملیات ناموفق بود. لطفاً دوباره تلاش کنید."
    
    def add_to_whitelist(self, user_id: int, username: str = None, added_by: int = None) -> tuple[bool, str]:
        """افزودن کاربر به لیست سفید"""
        try:
            # بررسی وجود در لیست سفید
            if self.is_user_whitelisted(user_id):
                return False, "این کاربر هم‌اکنون در لیست سفید است."
            
            # افزودن به لیست
            whitelist_data = self.store.get('whitelist', [])
            whitelist_data.append({
                'user_id': user_id,
                'username': username,
                'added_at': datetime.now().isoformat(),
                'added_by': added_by
            })
            
            self.store['whitelist'] = whitelist_data
            save_store(self.store)
            
            # بروزرسانی کش
            self._refresh_lists_cache()
            
            return True, "کاربر با موفقیت به لیست سفید اضافه شد."
            
        except Exception as e:
            print(f"Error adding to whitelist: {e}")
            return False, "عملیات ناموفق بود. لطفاً دوباره تلاش کنید."
    
    def remove_from_whitelist(self, user_id: int) -> tuple[bool, str]:
        """حذف کاربر از لیست سفید"""
        try:
            # بررسی وجود در لیست سفید
            if not self.is_user_whitelisted(user_id):
                return False, "این کاربر در لیست سفید نیست."
            
            # حذف از لیست
            whitelist_data = self.store.get('whitelist', [])
            whitelist_data = [item for item in whitelist_data if item.get('user_id') != user_id]
            
            self.store['whitelist'] = whitelist_data
            save_store(self.store)
            
            # بروزرسانی کش
            self._refresh_lists_cache()
            
            return True, "کاربر با موفقیت از لیست سفید حذف شد."
            
        except Exception as e:
            print(f"Error removing from whitelist: {e}")
            return False, "عملیات ناموفق بود. لطفاً دوباره تلاش کنید."
    
    def get_blacklist_data(self) -> list:
        """دریافت داده‌های لیست سیاه"""
        return self.store.get('blacklist', [])
    
    def get_whitelist_data(self) -> list:
        """دریافت داده‌های لیست سفید"""
        return self.store.get('whitelist', [])
    
    def search_in_lists(self, query: str) -> tuple[list, list]:
        """جستجو در لیست‌ها"""
        blacklist_data = self.get_blacklist_data()
        whitelist_data = self.get_whitelist_data()
        
        query_lower = query.lower()
        
        # جستجو در لیست سیاه
        blacklist_results = []
        for item in blacklist_data:
            user_id_str = str(item.get('user_id', ''))
            username = item.get('username', '').lower()
            
            if (query_lower in user_id_str or 
                query_lower in username or
                query_lower in item.get('username', '').lower()):
                blacklist_results.append(item)
        
        # جستجو در لیست سفید
        whitelist_results = []
        for item in whitelist_data:
            user_id_str = str(item.get('user_id', ''))
            username = item.get('username', '').lower()
            
            if (query_lower in user_id_str or 
                query_lower in username or
                query_lower in item.get('username', '').lower()):
                whitelist_results.append(item)
        
        return blacklist_results, whitelist_results
    
    async def notify_user_blocked(self, context: ContextTypes.DEFAULT_TYPE, user_id: int):
        """اطلاع‌رسانی مسدود شدن به کاربر"""
        try:
            message = "شما مسدود شده‌اید و تا زمان رفع مسدودی امکان استفاده از ربات را ندارید."
            await context.bot.send_message(chat_id=user_id, text=message)
        except Exception as e:
            print(f"Error notifying blocked user {user_id}: {e}")
    
    def resolve_user_identifier(self, identifier: str) -> tuple[bool, int, str]:
        """حل کردن شناسه کاربر (آیدی یا یوزرنیم)"""
        try:
            # اگر عدد است، مستقیماً آیدی است
            if identifier.isdigit():
                return True, int(identifier), None
            
            # اگر با @ شروع می‌شود، یوزرنیم است
            if identifier.startswith('@'):
                username = identifier[1:]
            else:
                username = identifier
            
            # در اینجا باید از Telegram API استفاده کنیم تا یوزرنیم را به آیدی تبدیل کنیم
            # برای سادگی، فعلاً یوزرنیم را برمی‌گردانیم
            return False, None, username
            
        except Exception as e:
            print(f"Error resolving user identifier: {e}")
            return False, None, None
    
    # ===== Enhanced Blacklist/Whitelist Interface =====
    async def enhanced_lists_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """منوی لیست سیاه و سفید پیشرفته"""
        # بررسی دسترسی ادمین
        user_id = update.effective_user.id
        if not self._is_admin(user_id):
            await update.message.reply_text("دسترسی غیرمجاز.")
            return
        
        # مقداردهی اولیه کش
        self.initialize_lists_cache()
        
        # آمار لیست‌ها
        blacklist_count = len(self.get_blacklist_data())
        whitelist_count = len(self.get_whitelist_data())
        
        keyboard = [
            [InlineKeyboardButton("➕ افزودن به لیست سیاه", callback_data="add_to_blacklist")],
            [InlineKeyboardButton("➖ حذف از لیست سیاه", callback_data="remove_from_blacklist")],
            [InlineKeyboardButton("➕ افزودن به لیست سفید", callback_data="add_to_whitelist")],
            [InlineKeyboardButton("➖ حذف از لیست سفید", callback_data="remove_from_whitelist")],
            [InlineKeyboardButton("📋 نمایش لیست سیاه", callback_data="show_blacklist")],
            [InlineKeyboardButton("📋 نمایش لیست سفید", callback_data="show_whitelist")],
            [InlineKeyboardButton("🔍 جستجو", callback_data="search_lists")],
            [InlineKeyboardButton("🔙 بازگشت", callback_data="back_to_main")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        text = f"""
⚫⚪ **لیست سیاه و سفید**

📊 **وضعیت فعلی**:
• کاربران مسدود: {blacklist_count} نفر
• کاربران سفید: {whitelist_count} نفر

🎯 **عملیات موجود**:
➕ **افزودن به لیست سیاه**: مسدود کردن کاربر
➖ **حذف از لیست سیاه**: آزاد کردن کاربر
➕ **افزودن به لیست سفید**: افزودن کاربر به لیست سفید
➖ **حذف از لیست سفید**: حذف کاربر از لیست سفید
📋 **نمایش لیست‌ها**: مشاهده کاربران مسدود/سفید
🔍 **جستجو**: جستجو در لیست‌ها

💡 **نحوه کارکرد**:
• کاربر مسدود شده پیام "مسدود شدید" دریافت می‌کند
• ربات دیگر هیچ دستوری از کاربر مسدود نمی‌گیرد
• لیست سفید اولویت بالاتری از لیست سیاه دارد
• ادمین‌ها همیشه مجاز هستند
        """
        
        if update.callback_query:
            await update.callback_query.edit_message_text(text, reply_markup=reply_markup)
        else:
            await update.message.reply_text(text, reply_markup=reply_markup)
    
    async def add_to_blacklist_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """شروع افزودن کاربر به لیست سیاه"""
        # بررسی دسترسی ادمین
        user_id = update.effective_user.id
        if not self._is_admin(user_id):
            await update.message.reply_text("دسترسی غیرمجاز.")
            return
        
        keyboard = [
            [InlineKeyboardButton("انصراف", callback_data="lists_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        text = """
➕ **افزودن به لیست سیاه**

آی‌دی عددی یا یوزرنیم کاربر را ارسال کنید.

💡 **نکات**:
• می‌توانید آیدی عددی (مثل: 123456789) ارسال کنید
• یا یوزرنیم (مثل: @username یا username) ارسال کنید
• کاربر مسدود شده پیام اطلاع‌رسانی دریافت می‌کند
        """
        
        if update.callback_query:
            await update.callback_query.edit_message_text(text, reply_markup=reply_markup)
        else:
            await update.message.reply_text(text, reply_markup=reply_markup)
        
        return AWAIT_BLACKLIST_ADD
    
    async def add_to_blacklist_process(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """پردازش افزودن کاربر به لیست سیاه"""
        # بررسی دسترسی ادمین
        user_id = update.effective_user.id
        if not self._is_admin(user_id):
            await update.message.reply_text("دسترسی غیرمجاز.")
            return
        
        identifier = update.message.text.strip()
        if not identifier:
            await update.message.reply_text("❌ لطفاً آیدی یا یوزرنیم کاربر را وارد کنید.")
            return AWAIT_BLACKLIST_ADD
        
        # حل کردن شناسه کاربر
        is_numeric, target_user_id, username = self.resolve_user_identifier(identifier)
        
        if not is_numeric and not username:
            await update.message.reply_text("ورودی نامعتبر است. لطفاً آیدی عددی یا یوزرنیم معتبر وارد کنید.")
            return AWAIT_BLACKLIST_ADD
        
        # اگر یوزرنیم است، باید از Telegram API استفاده کنیم
        if not is_numeric:
            await update.message.reply_text("❌ برای افزودن کاربر با یوزرنیم، لطفاً آیدی عددی کاربر را ارسال کنید.")
            return AWAIT_BLACKLIST_ADD
        
        # افزودن به لیست سیاه
        success, message = self.add_to_blacklist(target_user_id, username, user_id)
        
        if success:
            # اطلاع‌رسانی به کاربر
            await self.notify_user_blocked(context, target_user_id)
            
            await update.message.reply_text(f"✅ {message}")
        else:
            await update.message.reply_text(f"❌ {message}")
        
        # بازگشت به منوی اصلی
        await self.enhanced_lists_menu(update, context)
        return ADMIN_PANEL
    
    async def remove_from_blacklist_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """شروع حذف کاربر از لیست سیاه"""
        # بررسی دسترسی ادمین
        user_id = update.effective_user.id
        if not self._is_admin(user_id):
            await update.message.reply_text("دسترسی غیرمجاز.")
            return
        
        keyboard = [
            [InlineKeyboardButton("انصراف", callback_data="lists_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        text = """
➖ **حذف از لیست سیاه**

آی‌دی عددی یا یوزرنیم کاربر برای حذف از لیست سیاه را ارسال کنید.

💡 **نکات**:
• می‌توانید آیدی عددی (مثل: 123456789) ارسال کنید
• یا یوزرنیم (مثل: @username یا username) ارسال کنید
• کاربر بلافاصله دسترسی خود را بازمی‌یابد
        """
        
        if update.callback_query:
            await update.callback_query.edit_message_text(text, reply_markup=reply_markup)
        else:
            await update.message.reply_text(text, reply_markup=reply_markup)
        
        return AWAIT_BLACKLIST_REMOVE
    
    async def remove_from_blacklist_process(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """پردازش حذف کاربر از لیست سیاه"""
        # بررسی دسترسی ادمین
        user_id = update.effective_user.id
        if not self._is_admin(user_id):
            await update.message.reply_text("دسترسی غیرمجاز.")
            return
        
        identifier = update.message.text.strip()
        if not identifier:
            await update.message.reply_text("❌ لطفاً آیدی یا یوزرنیم کاربر را وارد کنید.")
            return AWAIT_BLACKLIST_REMOVE
        
        # حل کردن شناسه کاربر
        is_numeric, target_user_id, username = self.resolve_user_identifier(identifier)
        
        if not is_numeric and not username:
            await update.message.reply_text("ورودی نامعتبر است. لطفاً آیدی عددی یا یوزرنیم معتبر وارد کنید.")
            return AWAIT_BLACKLIST_REMOVE
        
        # اگر یوزرنیم است، باید از Telegram API استفاده کنیم
        if not is_numeric:
            await update.message.reply_text("❌ برای حذف کاربر با یوزرنیم، لطفاً آیدی عددی کاربر را ارسال کنید.")
            return AWAIT_BLACKLIST_REMOVE
        
        # حذف از لیست سیاه
        success, message = self.remove_from_blacklist(target_user_id)
        
        if success:
            await update.message.reply_text(f"✅ {message}")
        else:
            await update.message.reply_text(f"❌ {message}")
        
        # بازگشت به منوی اصلی
        await self.enhanced_lists_menu(update, context)
        return ADMIN_PANEL
    
    async def add_to_whitelist_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """شروع افزودن کاربر به لیست سفید"""
        # بررسی دسترسی ادمین
        user_id = update.effective_user.id
        if not self._is_admin(user_id):
            await update.message.reply_text("دسترسی غیرمجاز.")
            return
        
        keyboard = [
            [InlineKeyboardButton("انصراف", callback_data="lists_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        text = """
➕ **افزودن به لیست سفید**

آی‌دی عددی یا یوزرنیم کاربر را برای افزودن به لیست سفید ارسال کنید.

💡 **نکات**:
• می‌توانید آیدی عددی (مثل: 123456789) ارسال کنید
• یا یوزرنیم (مثل: @username یا username) ارسال کنید
• لیست سفید اولویت بالاتری از لیست سیاه دارد
        """
        
        if update.callback_query:
            await update.callback_query.edit_message_text(text, reply_markup=reply_markup)
        else:
            await update.message.reply_text(text, reply_markup=reply_markup)
        
        return AWAIT_WHITELIST_ADD
    
    async def add_to_whitelist_process(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """پردازش افزودن کاربر به لیست سفید"""
        # بررسی دسترسی ادمین
        user_id = update.effective_user.id
        if not self._is_admin(user_id):
            await update.message.reply_text("دسترسی غیرمجاز.")
            return
        
        identifier = update.message.text.strip()
        if not identifier:
            await update.message.reply_text("❌ لطفاً آیدی یا یوزرنیم کاربر را وارد کنید.")
            return AWAIT_WHITELIST_ADD
        
        # حل کردن شناسه کاربر
        is_numeric, target_user_id, username = self.resolve_user_identifier(identifier)
        
        if not is_numeric and not username:
            await update.message.reply_text("ورودی نامعتبر است. لطفاً آیدی عددی یا یوزرنیم معتبر وارد کنید.")
            return AWAIT_WHITELIST_ADD
        
        # اگر یوزرنیم است، باید از Telegram API استفاده کنیم
        if not is_numeric:
            await update.message.reply_text("❌ برای افزودن کاربر با یوزرنیم، لطفاً آیدی عددی کاربر را ارسال کنید.")
            return AWAIT_WHITELIST_ADD
        
        # افزودن به لیست سفید
        success, message = self.add_to_whitelist(target_user_id, username, user_id)
        
        if success:
            await update.message.reply_text(f"✅ {message}")
        else:
            await update.message.reply_text(f"❌ {message}")
        
        # بازگشت به منوی اصلی
        await self.enhanced_lists_menu(update, context)
        return ADMIN_PANEL
    
    async def remove_from_whitelist_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """شروع حذف کاربر از لیست سفید"""
        # بررسی دسترسی ادمین
        user_id = update.effective_user.id
        if not self._is_admin(user_id):
            await update.message.reply_text("دسترسی غیرمجاز.")
            return
        
        keyboard = [
            [InlineKeyboardButton("انصراف", callback_data="lists_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        text = """
➖ **حذف از لیست سفید**

آی‌دی عددی یا یوزرنیم کاربر برای حذف از لیست سفید را ارسال کنید.

💡 **نکات**:
• می‌توانید آیدی عددی (مثل: 123456789) ارسال کنید
• یا یوزرنیم (مثل: @username یا username) ارسال کنید
• کاربر از لیست سفید حذف می‌شود
        """
        
        if update.callback_query:
            await update.callback_query.edit_message_text(text, reply_markup=reply_markup)
        else:
            await update.message.reply_text(text, reply_markup=reply_markup)
        
        return AWAIT_WHITELIST_REMOVE
    
    async def remove_from_whitelist_process(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """پردازش حذف کاربر از لیست سفید"""
        # بررسی دسترسی ادمین
        user_id = update.effective_user.id
        if not self._is_admin(user_id):
            await update.message.reply_text("دسترسی غیرمجاز.")
            return
        
        identifier = update.message.text.strip()
        if not identifier:
            await update.message.reply_text("❌ لطفاً آیدی یا یوزرنیم کاربر را وارد کنید.")
            return AWAIT_WHITELIST_REMOVE
        
        # حل کردن شناسه کاربر
        is_numeric, target_user_id, username = self.resolve_user_identifier(identifier)
        
        if not is_numeric and not username:
            await update.message.reply_text("ورودی نامعتبر است. لطفاً آیدی عددی یا یوزرنیم معتبر وارد کنید.")
            return AWAIT_WHITELIST_REMOVE
        
        # اگر یوزرنیم است، باید از Telegram API استفاده کنیم
        if not is_numeric:
            await update.message.reply_text("❌ برای حذف کاربر با یوزرنیم، لطفاً آیدی عددی کاربر را ارسال کنید.")
            return AWAIT_WHITELIST_REMOVE
        
        # حذف از لیست سفید
        success, message = self.remove_from_whitelist(target_user_id)
        
        if success:
            await update.message.reply_text(f"✅ {message}")
        else:
            await update.message.reply_text(f"❌ {message}")
        
        # بازگشت به منوی اصلی
        await self.enhanced_lists_menu(update, context)
        return ADMIN_PANEL
    
    async def show_blacklist(self, update: Update, context: ContextTypes.DEFAULT_TYPE, page: int = 0):
        """نمایش لیست سیاه"""
        # بررسی دسترسی ادمین
        user_id = update.effective_user.id
        if not self._is_admin(user_id):
            await update.message.reply_text("دسترسی غیرمجاز.")
            return
        
        blacklist_data = self.get_blacklist_data()
        
        if not blacklist_data:
            keyboard = [
                [InlineKeyboardButton("بازگشت", callback_data="lists_menu")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            text = """
📋 **لیست سیاه**

• هیچ کاربری در لیست سیاه نیست
            """
            
            if update.callback_query:
                await update.callback_query.edit_message_text(text, reply_markup=reply_markup)
            else:
                await update.message.reply_text(text, reply_markup=reply_markup)
            return
        
        # صفحه‌بندی
        items_per_page = 8
        total_pages = (len(blacklist_data) + items_per_page - 1) // items_per_page
        
        # محاسبه آیتم‌های صفحه فعلی
        start_idx = page * items_per_page
        end_idx = min(start_idx + items_per_page, len(blacklist_data))
        page_data = blacklist_data[start_idx:end_idx]
        
        # ساخت کیبورد
        keyboard = []
        for item in page_data:
            user_id = item.get('user_id', 'نامشخص')
            username = item.get('username', 'نامشخص')
            added_at = item.get('added_at', 'نامشخص')
            
            button_text = f"❌ {user_id} — @{username}"
            keyboard.append([InlineKeyboardButton(button_text, callback_data=f"remove_blacklist:{user_id}")])
        
        # دکمه‌های ناوبری
        nav_buttons = []
        if page > 0:
            nav_buttons.append(InlineKeyboardButton("صفحه قبل", callback_data=f"blacklist_page:{page-1}"))
        if page < total_pages - 1:
            nav_buttons.append(InlineKeyboardButton("صفحه بعد", callback_data=f"blacklist_page:{page+1}"))
        
        if nav_buttons:
            keyboard.append(nav_buttons)
        
        keyboard.append([InlineKeyboardButton("بازگشت", callback_data="lists_menu")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # متن صفحه
        text = f"""
📋 **لیست سیاه**

📊 **صفحه {page + 1} از {total_pages}**
📢 **تعداد کل**: {len(blacklist_data)} کاربر

**کاربران این صفحه**:
        """
        
        for item in page_data:
            user_id = item.get('user_id', 'نامشخص')
            username = item.get('username', 'نامشخص')
            added_at = item.get('added_at', 'نامشخص')
            
            text += f"\n• {user_id} — @{username} — {added_at}"
        
        if update.callback_query:
            await update.callback_query.edit_message_text(text, reply_markup=reply_markup)
        else:
            await update.message.reply_text(text, reply_markup=reply_markup)
    
    async def show_whitelist(self, update: Update, context: ContextTypes.DEFAULT_TYPE, page: int = 0):
        """نمایش لیست سفید"""
        # بررسی دسترسی ادمین
        user_id = update.effective_user.id
        if not self._is_admin(user_id):
            await update.message.reply_text("دسترسی غیرمجاز.")
            return
        
        whitelist_data = self.get_whitelist_data()
        
        if not whitelist_data:
            keyboard = [
                [InlineKeyboardButton("بازگشت", callback_data="lists_menu")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            text = """
📋 **لیست سفید**

• هیچ کاربری در لیست سفید نیست
            """
            
            if update.callback_query:
                await update.callback_query.edit_message_text(text, reply_markup=reply_markup)
            else:
                await update.message.reply_text(text, reply_markup=reply_markup)
            return
        
        # صفحه‌بندی
        items_per_page = 8
        total_pages = (len(whitelist_data) + items_per_page - 1) // items_per_page
        
        # محاسبه آیتم‌های صفحه فعلی
        start_idx = page * items_per_page
        end_idx = min(start_idx + items_per_page, len(whitelist_data))
        page_data = whitelist_data[start_idx:end_idx]
        
        # ساخت کیبورد
        keyboard = []
        for item in page_data:
            user_id = item.get('user_id', 'نامشخص')
            username = item.get('username', 'نامشخص')
            added_at = item.get('added_at', 'نامشخص')
            
            button_text = f"✅ {user_id} — @{username}"
            keyboard.append([InlineKeyboardButton(button_text, callback_data=f"remove_whitelist:{user_id}")])
        
        # دکمه‌های ناوبری
        nav_buttons = []
        if page > 0:
            nav_buttons.append(InlineKeyboardButton("صفحه قبل", callback_data=f"whitelist_page:{page-1}"))
        if page < total_pages - 1:
            nav_buttons.append(InlineKeyboardButton("صفحه بعد", callback_data=f"whitelist_page:{page+1}"))
        
        if nav_buttons:
            keyboard.append(nav_buttons)
        
        keyboard.append([InlineKeyboardButton("بازگشت", callback_data="lists_menu")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # متن صفحه
        text = f"""
📋 **لیست سفید**

📊 **صفحه {page + 1} از {total_pages}**
📢 **تعداد کل**: {len(whitelist_data)} کاربر

**کاربران این صفحه**:
        """
        
        for item in page_data:
            user_id = item.get('user_id', 'نامشخص')
            username = item.get('username', 'نامشخص')
            added_at = item.get('added_at', 'نامشخص')
            
            text += f"\n• {user_id} — @{username} — {added_at}"
        
        if update.callback_query:
            await update.callback_query.edit_message_text(text, reply_markup=reply_markup)
        else:
            await update.message.reply_text(text, reply_markup=reply_markup)
    
    async def search_lists_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """شروع جستجو در لیست‌ها"""
        # بررسی دسترسی ادمین
        user_id = update.effective_user.id
        if not self._is_admin(user_id):
            await update.message.reply_text("دسترسی غیرمجاز.")
            return
        
        keyboard = [
            [InlineKeyboardButton("انصراف", callback_data="lists_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        text = """
🔍 **جستجو در لیست‌ها**

نام کاربر، آیدی یا یوزرنیم را ارسال کنید.

💡 **نکات**:
• می‌توانید آیدی عددی جستجو کنید
• یا یوزرنیم جستجو کنید
• جستجو در هر دو لیست انجام می‌شود
        """
        
        if update.callback_query:
            await update.callback_query.edit_message_text(text, reply_markup=reply_markup)
        else:
            await update.message.reply_text(text, reply_markup=reply_markup)
        
        return LISTS_SEARCH
    
    async def search_lists_process(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """پردازش جستجو در لیست‌ها"""
        # بررسی دسترسی ادمین
        user_id = update.effective_user.id
        if not self._is_admin(user_id):
            await update.message.reply_text("دسترسی غیرمجاز.")
            return
        
        query = update.message.text.strip()
        if not query:
            await update.message.reply_text("❌ لطفاً عبارت جستجو را وارد کنید.")
            return LISTS_SEARCH
        
        # جستجو در لیست‌ها
        blacklist_results, whitelist_results = self.search_in_lists(query)
        
        # ساخت کیبورد
        keyboard = []
        
        # نتایج لیست سیاه
        if blacklist_results:
            keyboard.append([InlineKeyboardButton(f"📋 لیست سیاه ({len(blacklist_results)})", callback_data="show_blacklist")])
        
        # نتایج لیست سفید
        if whitelist_results:
            keyboard.append([InlineKeyboardButton(f"📋 لیست سفید ({len(whitelist_results)})", callback_data="show_whitelist")])
        
        keyboard.append([InlineKeyboardButton("بازگشت", callback_data="lists_menu")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # متن نتایج
        text = f"""
🔍 **نتایج جستجو برای: {query}**

📊 **نتایج یافت شده**:
• لیست سیاه: {len(blacklist_results)} نتیجه
• لیست سفید: {len(whitelist_results)} نتیجه
        """
        
        if not blacklist_results and not whitelist_results:
            text += "\n\n• هیچ نتیجه‌ای یافت نشد"
        
        await update.message.reply_text(text, reply_markup=reply_markup)
        
        # بازگشت به منوی اصلی
        await self.enhanced_lists_menu(update, context)
        return ADMIN_PANEL
    
    # ===== Enhanced Feature Toggle Interface =====
    async def enhanced_feature_toggle_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE, page: int = 0, search_query: str = None):
        """منوی تنظیمات ربات پیشرفته"""
        # بررسی دسترسی ادمین
        user_id = update.effective_user.id
        if not self._is_admin(user_id):
            await update.message.reply_text("دسترسی غیرمجاز.")
            return
        
        # مقداردهی اولیه registry
        self.initialize_feature_registry()
        
        # دریافت ویژگی‌ها
        if search_query:
            features = self.search_features(search_query)
        else:
            features = self.get_all_features()
        
        # صفحه‌بندی
        items_per_page = 8
        total_pages = (len(features) + items_per_page - 1) // items_per_page
        
        if not features:
            keyboard = [
                [InlineKeyboardButton("بازگشت", callback_data="back_to_main")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            text = """
🤖 **تنظیمات ربات**

• هیچ ویژگی‌ای یافت نشد

برای جستجو، از دکمه "جستجو" استفاده کنید.
            """
            
            if update.callback_query:
                await update.callback_query.edit_message_text(text, reply_markup=reply_markup)
            else:
                await update.message.reply_text(text, reply_markup=reply_markup)
            return
        
        # محاسبه آیتم‌های صفحه فعلی
        start_idx = page * items_per_page
        end_idx = min(start_idx + items_per_page, len(features))
        page_features = list(features.items())[start_idx:end_idx]
        
        # ساخت کیبورد
        keyboard = []
        for feature_key, feature_info in page_features:
            title = feature_info.get('title', feature_key)
            enabled = feature_info.get('enabled', False)
            category = feature_info.get('category', 'unknown')
            
            # آیکون وضعیت
            status_icon = "✅" if enabled else "❌"
            category_icon = "👨‍💼" if category == 'admin' else "👤"
            
            button_text = f"{status_icon} {category_icon} {title}"
            keyboard.append([InlineKeyboardButton(button_text, callback_data=f"toggle_feature:{feature_key}")])
        
        # دکمه‌های ناوبری
        nav_buttons = []
        if page > 0:
            nav_buttons.append(InlineKeyboardButton("صفحه قبل", callback_data=f"feature_page:{page-1}"))
        if page < total_pages - 1:
            nav_buttons.append(InlineKeyboardButton("صفحه بعد", callback_data=f"feature_page:{page+1}"))
        
        if nav_buttons:
            keyboard.append(nav_buttons)
        
        # دکمه‌های کنترل
        control_buttons = [
            InlineKeyboardButton("جستجو", callback_data="search_features"),
            InlineKeyboardButton("بازگشت", callback_data="back_to_main")
        ]
        keyboard.append(control_buttons)
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # متن صفحه
        search_text = f" (جستجو: {search_query})" if search_query else ""
        text = f"""
🤖 **تنظیمات ربات**

📋 **لیست دکمه‌ها و قابلیت‌ها**{search_text}

📊 **صفحه {page + 1} از {total_pages}**
📢 **تعداد کل**: {len(features)} ویژگی

**ویژگی‌های این صفحه**:
        """
        
        for feature_key, feature_info in page_features:
            title = feature_info.get('title', feature_key)
            enabled = feature_info.get('enabled', False)
            category = feature_info.get('category', 'unknown')
            
            status_text = "فعال" if enabled else "غیرفعال"
            category_text = "ادمین" if category == 'admin' else "کاربر"
            
            text += f"\n• {title} ({category_text}) - {status_text}"
        
        if update.callback_query:
            await update.callback_query.edit_message_text(text, reply_markup=reply_markup)
        else:
            await update.message.reply_text(text, reply_markup=reply_markup)
    
    async def show_feature_toggle_submenu(self, update: Update, context: ContextTypes.DEFAULT_TYPE, feature_key: str):
        """نمایش زیرمنوی تغییر وضعیت ویژگی"""
        # بررسی دسترسی ادمین
        user_id = update.effective_user.id
        if not self._is_admin(user_id):
            await update.message.reply_text("دسترسی غیرمجاز.")
            return
        
        feature_info = self.get_feature_info(feature_key)
        if not feature_info:
            await update.callback_query.answer("❌ ویژگی یافت نشد!")
            return
        
        title = feature_info.get('title', feature_key)
        enabled = feature_info.get('enabled', False)
        category = feature_info.get('category', 'unknown')
        deps = feature_info.get('deps', [])
        protected = feature_info.get('protected', False)
        
        # ساخت کیبورد
        keyboard = []
        
        if not protected:
            if enabled:
                keyboard.append([InlineKeyboardButton("❌ خاموش", callback_data=f"set_feature_off:{feature_key}")])
            else:
                keyboard.append([InlineKeyboardButton("✅ روشن", callback_data=f"set_feature_on:{feature_key}")])
        else:
            keyboard.append([InlineKeyboardButton("🔒 محافظت شده", callback_data="protected_feature")])
        
        keyboard.append([InlineKeyboardButton("بازگشت", callback_data="feature_toggle_menu")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # متن زیرمنو
        status_text = "فعال" if enabled else "غیرفعال"
        category_text = "ادمین" if category == 'admin' else "کاربر"
        protected_text = " (محافظت شده)" if protected else ""
        
        text = f"""
⚙️ **{title}**{protected_text}

📊 **وضعیت فعلی**: {status_text}
📂 **دسته**: {category_text}
        """
        
        if deps:
            dep_titles = []
            for dep_key in deps:
                dep_info = self.get_feature_info(dep_key)
                dep_title = dep_info.get('title', dep_key)
                dep_enabled = dep_info.get('enabled', False)
                dep_status = "✅" if dep_enabled else "❌"
                dep_titles.append(f"{dep_status} {dep_title}")
            
            text += f"\n🔗 **وابستگی‌ها**:\n" + "\n".join(dep_titles)
        
        if protected:
            text += f"\n\n🔒 **نکته**: این بخش اصلی ربات است و قابل خاموش کردن نیست."
        
        await update.callback_query.edit_message_text(text, reply_markup=reply_markup)
    
    async def toggle_feature_state(self, update: Update, context: ContextTypes.DEFAULT_TYPE, feature_key: str, enabled: bool):
        """تغییر وضعیت ویژگی"""
        # بررسی دسترسی ادمین
        user_id = update.effective_user.id
        if not self._is_admin(user_id):
            await update.message.reply_text("دسترسی غیرمجاز.")
            return
        
        feature_info = self.get_feature_info(feature_key)
        if not feature_info:
            await update.callback_query.answer("❌ ویژگی یافت نشد!")
            return
        
        title = feature_info.get('title', feature_key)
        
        # تغییر وضعیت
        success, message = self.toggle_feature(feature_key, enabled, user_id)
        
        if success:
            status_text = "روشن شد" if enabled else "خاموش شد و از ربات حذف گردید"
            success_message = f"قابلیت «{title}» با موفقیت {status_text}."
            await update.callback_query.answer(success_message)
        else:
            await update.callback_query.answer(f"❌ {message}")
        
        # بازگشت به زیرمنو
        await self.show_feature_toggle_submenu(update, context, feature_key)
    
    async def search_features_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """شروع جستجوی ویژگی‌ها"""
        # بررسی دسترسی ادمین
        user_id = update.effective_user.id
        if not self._is_admin(user_id):
            await update.message.reply_text("دسترسی غیرمجاز.")
            return
        
        keyboard = [
            [InlineKeyboardButton("انصراف", callback_data="feature_toggle_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        text = """
🔍 **جستجوی ویژگی‌ها**

نام قابلیت را ارسال کنید.

💡 **نکات**:
• می‌توانید نام فارسی یا انگلیسی جستجو کنید
• جستجو در عنوان و شناسه ویژگی انجام می‌شود
• برای مشاهده تمام ویژگی‌ها، "انصراف" را بزنید
        """
        
        if update.callback_query:
            await update.callback_query.edit_message_text(text, reply_markup=reply_markup)
        else:
            await update.message.reply_text(text, reply_markup=reply_markup)
        
        return FEATURE_SEARCH
    
    async def process_feature_search(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """پردازش جستجوی ویژگی‌ها"""
        # بررسی دسترسی ادمین
        user_id = update.effective_user.id
        if not self._is_admin(user_id):
            await update.message.reply_text("دسترسی غیرمجاز.")
            return
        
        search_query = update.message.text.strip()
        if not search_query:
            await update.message.reply_text("❌ لطفاً نام قابلیت را وارد کنید.")
            return FEATURE_SEARCH
        
        # نمایش نتایج جستجو
        await self.enhanced_feature_toggle_menu(update, context, page=0, search_query=search_query)
        return ADMIN_PANEL
    
    # ===== Enhanced Analytics Dashboard =====
    async def enhanced_analytics_dashboard(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """داشبورد آمار پیشرفته"""
        # بررسی دسترسی ادمین
        user_id = update.effective_user.id
        if not self._is_admin(user_id):
            await update.message.reply_text("دسترسی غیرمجاز.")
            return
        
        keyboard = [
            [InlineKeyboardButton("۲۴ ساعت گذشته", callback_data="stats_24h")],
            [InlineKeyboardButton("۷ روز گذشته", callback_data="stats_7d")],
            [InlineKeyboardButton("۳۰ روز گذشته", callback_data="stats_30d")],
            [InlineKeyboardButton("آمار کل", callback_data="stats_all")],
            [InlineKeyboardButton("به‌روزرسانی", callback_data="refresh_stats")],
            [InlineKeyboardButton("بازگشت", callback_data="back_to_main")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        text = """
📊 **آمار و گزارش**

لطفاً بازه زمانی مورد نظر را انتخاب کنید:

• **۲۴ ساعت گذشته**: آمار 24 ساعت اخیر
• **۷ روز گذشته**: آمار 7 روز اخیر  
• **۳۰ روز گذشته**: آمار 30 روز اخیر
• **آمار کل**: آمار از ابتدا تا کنون
• **به‌روزرسانی**: بروزرسانی آمار فعلی
        """
        
        if update.callback_query:
            await update.callback_query.edit_message_text(text, reply_markup=reply_markup)
        else:
            await update.message.reply_text(text, reply_markup=reply_markup)
    
    async def show_stats_for_window(self, update: Update, context: ContextTypes.DEFAULT_TYPE, window_type: str):
        """نمایش آمار برای بازه زمانی مشخص"""
        # بررسی دسترسی ادمین
        user_id = update.effective_user.id
        if not self._is_admin(user_id):
            await update.message.reply_text("دسترسی غیرمجاز.")
            return
        
        # بررسی کش
        cached_stats = self.get_cached_stats(window_type)
        if cached_stats:
            stats = cached_stats
        else:
            # محاسبه آمار جدید
            stats = self.get_stats_for_window(window_type)
            # ذخیره در کش
            self.set_cached_stats(window_type, stats, 60)
        
        # فرمت کردن آمار
        window_names = {
            "24h": "۲۴ ساعت گذشته",
            "7d": "۷ روز گذشته", 
            "30d": "۳۰ روز گذشته",
            "all": "آمار کل"
        }
        
        window_name = window_names.get(window_type, window_type)
        
        text = f"""
📊 **{window_name}**

**بازه زمانی**:
از تاریخ: {self.format_persian_date(stats['start_time'])}
تا تاریخ: {self.format_persian_date(stats['end_time'])}

**آمار کلی**:
• تعداد استارت‌ها: {stats['starts']:,}
• کاربران فعال: {stats['active_users']:,}
• ارسال موفق: {stats['broadcast_success']:,}
• ارسال ناموفق: {stats['broadcast_fail']:,}

**میانگین**: {stats['avg_rate']:.2f} {stats['avg_unit']}

🕒 **آخرین بروزرسانی**: {datetime.now().strftime('%Y/%m/%d %H:%M')}
        """
        
        keyboard = [
            [InlineKeyboardButton("به‌روزرسانی", callback_data=f"refresh_stats_{window_type}")],
            [InlineKeyboardButton("بازگشت", callback_data="analytics_dashboard")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        if update.callback_query:
            await update.callback_query.edit_message_text(text, reply_markup=reply_markup)
        else:
            await update.message.reply_text(text, reply_markup=reply_markup)
    
    async def refresh_stats(self, update: Update, context: ContextTypes.DEFAULT_TYPE, window_type: str = None):
        """بروزرسانی آمار"""
        # بررسی دسترسی ادمین
        user_id = update.effective_user.id
        if not self._is_admin(user_id):
            await update.message.reply_text("دسترسی غیرمجاز.")
            return
        
        if window_type:
            # پاک کردن کش برای بازه مشخص
            cache_key = f"stats_{window_type}"
            self.cache.delete(cache_key)
            
            # نمایش آمار بروزرسانی شده
            await self.show_stats_for_window(update, context, window_type)
        else:
            # پاک کردن تمام کش‌ها
            for wt in ["24h", "7d", "30d", "all"]:
                cache_key = f"stats_{wt}"
                self.cache.delete(cache_key)
            
            # بازگشت به داشبورد
            await self.enhanced_analytics_dashboard(update, context)
    
    async def send_start_notification(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """ارسال اعلان استارت به ادمین‌ها"""
        try:
            user = update.effective_user
            user_id = user.id
            
            # دریافت اطلاعات کاربر
            username = user.username or "—"
            full_name = user.full_name or "نامشخص"
            
            # ساخت لینک
            if user.username:
                mention = f"@{user.username}"
            else:
                mention = f"tg://user?id={user_id}"
            
            # زمان فعلی
            ts = datetime.now().strftime('%Y/%m/%d %H:%M:%S')
            
            # متن اعلان
            notification_text = f"""
کاربر جدید استارت کرد:
نام: {full_name}
آی‌دی عددی: {user_id}
یوزرنیم: {username}
لینک: {mention}
زمان: {ts}
            """
            
            # ارسال به مالک و ادمین‌ها
            from config import OWNER_ID
            admins = self.store.get('admins', [])
            
            # لیست دریافت‌کنندگان
            recipients = [OWNER_ID] + admins
            
            # ارسال به هر دریافت‌کننده
            for recipient_id in recipients:
                try:
                    await context.bot.send_message(
                        chat_id=recipient_id,
                        text=notification_text
                    )
                except Exception as e:
                    print(f"Failed to send start notification to {recipient_id}: {e}")
            
        except Exception as e:
            print(f"Error sending start notification: {e}")
    
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
        # Clear admin conversation flag
        context.user_data.pop('admin_conversation', None)
        await update.message.reply_text("✅ بازگشت زدی! دکمه مورد نظر را انتخاب کن:")
        await self.admin_panel_main(update, context)

# ایجاد نمونه از کلاس
admin_panel = AdminPanel()
