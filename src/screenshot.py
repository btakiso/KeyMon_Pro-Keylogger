import os
import time
from PIL import ImageGrab
from datetime import datetime
import threading

try:
    import cv2
    import numpy as np
    USE_OPENCV = True
except ImportError:
    USE_OPENCV = False

# Change the screenshot directory to root/screenshots
SCREENSHOT_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'screenshots')

class ScreenshotCapture:
    def __init__(self, interval=5, stop_event=None, use_opencv=False):
        self.interval = interval
        self.stop_event = stop_event or threading.Event()
        self.screenshot_dir = SCREENSHOT_DIR
        self.use_opencv = use_opencv and USE_OPENCV  # Only use OpenCV if available and requested
        
        # Create screenshots directory if it doesn't exist
        if not os.path.exists(self.screenshot_dir):
            os.makedirs(self.screenshot_dir)

    def start(self):
        """Start the screenshot capture loop"""
        try:
            while not self.stop_event.is_set():
                try:
                    self.capture_screenshot()
                    time.sleep(self.interval)
                except Exception as e:
                    print(f"Error capturing screenshot: {e}")
                    time.sleep(1)  # Wait a bit before retrying
        except Exception as e:
            print(f"Screenshot capture thread error: {e}")

    def capture_screenshot(self):
        """Capture a screenshot and save it"""
        try:
            # Generate timestamp for filename
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"screenshot_{timestamp}.png"
            filepath = os.path.join(self.screenshot_dir, filename)
            
            if self.use_opencv:
                # OpenCV method (more features, might be faster)
                screen = ImageGrab.grab()
                frame = np.array(screen)
                frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
                cv2.imwrite(filepath, frame)
            else:
                # PIL method (simpler, more portable)
                screenshot = ImageGrab.grab()
                screenshot.save(filepath, 'PNG')
            
            # Log the screenshot
            from src.central_logger import central_logger
            central_logger.log_event("screenshot", {"filepath": filepath})
            
        except Exception as e:
            print(f"Error in capture_screenshot: {e}")

    def stop(self):
        """Stop the screenshot capture"""
        if self.stop_event:
            self.stop_event.set()
