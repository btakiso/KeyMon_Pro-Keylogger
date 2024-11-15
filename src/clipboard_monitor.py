import threading
import time
import pyperclip
from datetime import datetime

class ClipboardMonitor:
    def __init__(self, stop_event=None):
        self.stop_event = stop_event or threading.Event()
        self.last_value = ''
        
    def start(self):
        """Start monitoring the clipboard"""
        try:
            while not self.stop_event.is_set():
                try:
                    current_value = pyperclip.paste()
                    
                    # Check if clipboard content has changed
                    if current_value != self.last_value:
                        self.last_value = current_value
                        self.log_clipboard_change(current_value)
                    
                    time.sleep(1)  # Check every second
                except Exception as e:
                    print(f"Error monitoring clipboard: {e}")
                    time.sleep(1)
        except Exception as e:
            print(f"Clipboard monitor thread error: {e}")

    def log_clipboard_change(self, content):
        """Log clipboard content changes"""
        try:
            # Import here to avoid circular imports
            from src.central_logger import central_logger
            
            # Log the clipboard change
            central_logger.log_event("clipboard", {
                "content": content,
                "timestamp": datetime.now().isoformat()
            })
        except Exception as e:
            print(f"Error logging clipboard change: {e}")

    def stop(self):
        """Stop the clipboard monitor"""
        if self.stop_event:
            self.stop_event.set()
