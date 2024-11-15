import threading
import time
import os
import sqlite3
import shutil
from datetime import datetime, timedelta
import json
import platform
import logging
import tempfile
import pytz

logger = logging.getLogger(__name__)

class BrowserMonitor:
    def __init__(self, stop_event=None, interval=5):
        self.stop_event = stop_event or threading.Event()
        self.interval = interval
        self.last_activity = datetime.now()
        self.notification_timeout = 300
        
        # Get user profile directory based on OS
        if platform.system().lower() == 'windows':
            self.user_data = os.getenv('LOCALAPPDATA')
            self.app_data = os.getenv('APPDATA')
        else:
            self.user_data = os.getenv('HOME')
            self.app_data = os.getenv('HOME')

        # Updated Chrome paths to include more profile variations
        chrome_base_paths = {
            'windows': [
                os.path.join(self.user_data, 'Google', 'Chrome', 'User Data'),
                os.path.join(self.user_data, 'Google', 'Chrome Beta', 'User Data'),
                os.path.join(self.user_data, 'Google', 'Chrome Dev', 'User Data'),
            ],
            'linux': [
                os.path.join(self.user_data, '.config', 'google-chrome'),
                os.path.join(self.user_data, '.config', 'google-chrome-beta'),
            ],
            'darwin': [
                os.path.join(self.user_data, 'Library', 'Application Support', 'Google', 'Chrome'),
                os.path.join(self.user_data, 'Library', 'Application Support', 'Google', 'Chrome Beta'),
            ]
        }

        # Function to generate profile paths
        def get_chrome_profiles(base_path):
            profiles = []
            if os.path.exists(base_path):
                # Add Default profile
                profiles.append(os.path.join(base_path, 'Default', 'History'))
                
                # Add numbered profiles
                for i in range(1, 10):  # Check up to Profile 9
                    profile_path = os.path.join(base_path, f'Profile {i}', 'History')
                    if os.path.exists(os.path.dirname(profile_path)):
                        profiles.append(profile_path)
                        
                # Look for named profiles
                try:
                    local_state_path = os.path.join(base_path, 'Local State')
                    if os.path.exists(local_state_path):
                        with open(local_state_path, 'r', encoding='utf-8') as f:
                            local_state = json.load(f)
                            if 'profile' in local_state and 'info_cache' in local_state['profile']:
                                for profile_name in local_state['profile']['info_cache'].keys():
                                    if profile_name not in ['Default', 'System Profile']:
                                        profile_path = os.path.join(base_path, profile_name, 'History')
                                        if os.path.exists(os.path.dirname(profile_path)):
                                            profiles.append(profile_path)
                except Exception as e:
                    logger.error(f"Error reading Chrome profiles: {e}")
                    
            return profiles

        # Generate all possible Chrome profile paths
        chrome_paths = []
        system = platform.system().lower()
        if system in chrome_base_paths:
            for base_path in chrome_base_paths[system]:
                chrome_paths.extend(get_chrome_profiles(base_path))

        # Comprehensive browser paths for different operating systems
        self.browsers_data = {
            'chrome': {
                'windows': chrome_paths if system == 'windows' else [],
                'linux': chrome_paths if system == 'linux' else [],
                'darwin': chrome_paths if system == 'darwin' else [],
            },
            'brave': {
                'windows': [
                    os.path.join(self.user_data, 'BraveSoftware\\Brave-Browser\\User Data\\Default\\History'),
                ],
                'linux': [
                    os.path.join(self.user_data, '.config/BraveSoftware/Brave-Browser/Default/History'),
                ],
                'darwin': [
                    os.path.join(self.user_data, 'Library/Application Support/BraveSoftware/Brave-Browser/Default/History'),
                ]
            },
            'edge': {
                'windows': [
                    os.path.join(self.user_data, 'Microsoft\\Edge\\User Data\\Default\\History'),
                    os.path.join(self.user_data, 'Microsoft\\Edge\\User Data\\Profile 1\\History'),
                ],
                'linux': [
                    os.path.join(self.user_data, '.config/microsoft-edge/Default/History'),
                ],
                'darwin': [
                    os.path.join(self.user_data, 'Library/Application Support/Microsoft Edge/Default/History'),
                ]
            },
            'firefox': {
                'windows': os.path.join(self.app_data, 'Mozilla\\Firefox\\Profiles'),
                'linux': os.path.join(self.user_data, '.mozilla/firefox'),
                'darwin': os.path.join(self.user_data, 'Library/Application Support/Firefox/Profiles')
            },
            'safari': {
                'darwin': os.path.join(self.user_data, 'Library/Safari/History.db')
            },
            'opera': {
                'windows': [
                    os.path.join(self.app_data, 'Opera Software\\Opera Stable\\History'),
                ],
                'linux': [
                    os.path.join(self.user_data, '.config/opera/History'),
                ],
                'darwin': [
                    os.path.join(self.user_data, 'Library/Application Support/com.operasoftware.Opera/History'),
                ]
            },
            'chromium': {
                'windows': [
                    os.path.join(self.user_data, 'Chromium\\User Data\\Default\\History'),
                ],
                'linux': [
                    os.path.join(self.user_data, '.config/chromium/Default/History'),
                ],
                'darwin': [
                    os.path.join(self.user_data, 'Library/Application Support/Chromium/Default/History'),
                ]
            }
        }
        self.last_checked = {}
        self._processed_urls = set()
        logger.info("Browser monitor initialized")
        self.timezone = pytz.timezone('America/New_York')

    def start(self):
        """Start monitoring browser history"""
        logger.info("Starting browser history monitoring")
        try:
            while not self.stop_event.is_set():
                try:
                    self.check_browser_history()
                    time.sleep(self.interval)
                except Exception as e:
                    logger.error(f"Error monitoring browser history: {e}")
                    time.sleep(1)
        except Exception as e:
            logger.error(f"Browser monitor thread error: {e}")

    def check_browser_history(self):
        """Check for new browser history entries"""
        system = platform.system().lower()
        logger.debug(f"Checking browser history on {system}")
        
        for browser, paths in self.browsers_data.items():
            if system in paths:
                try:
                    self.process_browser(browser, paths[system])
                except Exception as e:
                    logger.error(f"Error processing {browser} history: {e}")

    def process_browser(self, browser_name, history_paths):
        """Process browser history for a specific browser"""
        try:
            # Chrome-based browsers (Chrome, Brave, Edge, Chromium, Opera)
            chrome_based = ['chrome', 'brave', 'edge', 'chromium', 'opera']
            if browser_name in chrome_based:
                if isinstance(history_paths, list):
                    for path in history_paths:
                        if os.path.exists(path):
                            # Only log when first discovering the history file
                            if not hasattr(self, '_found_browsers'):
                                self._found_browsers = set()
                            if path not in self._found_browsers:
                                logger.info(f"Found {browser_name} history at: {path}")
                                self._found_browsers.add(path)
                            self.process_chrome_history(path)
                            return
                    # Only log missing history files once during startup
                    if not hasattr(self, '_logged_missing'):
                        self._logged_missing = set()
                    if browser_name not in self._logged_missing:
                        logger.debug(f"No valid {browser_name} history file found")
                        self._logged_missing.add(browser_name)
                else:
                    self.process_chrome_history(history_paths)
            
            # Firefox
            elif browser_name == 'firefox':
                self.process_firefox_history(history_paths)
            
            # Safari (macOS only)
            elif browser_name == 'safari' and platform.system().lower() == 'darwin':
                self.process_safari_history(history_paths)
                
        except Exception as e:
            logger.error(f"Error processing {browser_name} history: {e}")

    def process_chrome_history(self, history_path):
        """Process Chrome browser history"""
        try:
            if not os.path.exists(history_path):
                return

            # Get current time in Eastern timezone
            current_time = datetime.now(self.timezone)
            five_minutes_ago = current_time - timedelta(minutes=5)
            five_seconds_ago = current_time - timedelta(seconds=5)
            
            # Track processed URLs to avoid duplicates
            if not hasattr(self, '_processed_urls'):
                self._processed_urls = set()

            temp_dir = os.path.join(tempfile.gettempdir(), f'browser_history_temp_{int(time.time())}')
            temp_path = os.path.join(temp_dir, 'History')
            
            try:
                os.makedirs(temp_dir, exist_ok=True)
                
                max_attempts = 3
                success = False
                
                for attempt in range(max_attempts):
                    try:
                        connection_str = f"file:{history_path}?mode=ro"
                        try:
                            tmp_conn = sqlite3.connect(connection_str, uri=True)
                            tmp_conn.close()
                        except sqlite3.OperationalError:
                            pass

                        with open(history_path, 'rb') as src, open(temp_path, 'wb') as dst:
                            dst.write(src.read())
                        
                        success = True
                        break
                    except (PermissionError, IOError) as e:
                        if attempt == max_attempts - 1:
                            logger.error(f"Failed to access history file: {str(e)}")
                            return
                        time.sleep(1)
                
                if not success:
                    return

                time.sleep(0.2)

                try:
                    conn = sqlite3.connect(f'file:{temp_path}?mode=ro&journal_mode=WAL', uri=True)
                    conn.row_factory = sqlite3.Row
                    cursor = conn.cursor()
                    
                    # First check if there are any very recent entries (within 5 seconds)
                    check_query = """
                        SELECT COUNT(*) 
                        FROM urls 
                        WHERE last_visit_time > ? 
                        AND url NOT LIKE 'chrome://%'
                        AND url NOT LIKE 'about:%'
                        AND url NOT LIKE 'edge://%'
                        AND url NOT LIKE 'brave://%'
                        AND url NOT LIKE 'chrome-extension://%'
                        AND visit_count > 0
                    """
                    
                    cursor.execute(check_query, (five_seconds_ago.timestamp(),))
                    recent_count = cursor.fetchone()[0]
                    
                    if recent_count == 0:
                        # No very recent activity, skip processing
                        return

                    query = """
                        SELECT url, title, last_visit_time, visit_count
                        FROM urls 
                        WHERE last_visit_time > 0
                        AND url NOT LIKE 'chrome://%'
                        AND url NOT LIKE 'about:%'
                        AND url NOT LIKE 'edge://%'
                        AND url NOT LIKE 'brave://%'
                        AND url NOT LIKE 'chrome-extension://%'
                        AND visit_count > 0
                        ORDER BY last_visit_time DESC
                        LIMIT 10
                    """
                    
                    cursor.execute(query)
                    results = cursor.fetchall()
                    
                    new_entries = 0
                    chrome_epoch = datetime(1601, 1, 1, tzinfo=pytz.UTC)
                    
                    for row in results:
                        try:
                            # Convert Chrome timestamp to Eastern time
                            utc_time = chrome_epoch + timedelta(microseconds=row['last_visit_time'])
                            visit_time = utc_time.astimezone(self.timezone)
                            url = row['url']
                            
                            # Debug logging
                            logger.debug(f"Processing URL: {url}")
                            logger.debug(f"Visit time: {visit_time}")
                            logger.debug(f"Current time: {current_time}")
                            
                            # Check if this is a recent entry
                            time_diff = (current_time - visit_time).total_seconds()
                            
                            if url and len(url) > 0 and url not in self._processed_urls and time_diff <= 300:  # 5 minutes
                                self.log_browser_history(
                                    'chrome',
                                    url,
                                    row['title'],
                                    visit_time,
                                    notify=(time_diff <= 5)  # Only notify if within last 5 seconds
                                )
                                new_entries += 1
                                self._processed_urls.add(url)
                                
                                # Limit size of processed URLs set
                                if len(self._processed_urls) > 1000:
                                    self._processed_urls.clear()
                        
                        except Exception as e:
                            logger.error(f"Error processing history entry: {e}")
                    
                    if new_entries > 0:
                        logger.info(f"Logged {new_entries} new browser history entries")
                        self.last_checked['chrome'] = current_time
                    
                except sqlite3.Error as e:
                    logger.error(f"SQLite error: {e}")
                finally:
                    if 'conn' in locals():
                        conn.close()
                    
            finally:
                try:
                    if os.path.exists(temp_path):
                        os.remove(temp_path)
                    if os.path.exists(temp_dir):
                        shutil.rmtree(temp_dir)
                except Exception:
                    pass
                    
        except Exception as e:
            logger.error(f"Error processing Chrome history: {e}")

    def process_firefox_history(self, profile_path):
        """Process Firefox browser history"""
        try:
            if not os.path.exists(profile_path):
                logger.debug(f"Firefox profile path not found: {profile_path}")
                return
                
            profiles = [d for d in os.listdir(profile_path) 
                       if d.endswith('.default') or d.endswith('.default-release')]
            
            if not profiles:
                logger.debug("No Firefox profiles found")
                return
                
            history_path = os.path.join(profile_path, profiles[0], 'places.sqlite')
            if not os.path.exists(history_path):
                logger.debug(f"Firefox history file not found: {history_path}")
                return
            
            # Create a copy of the history file
            temp_path = os.path.join(os.path.dirname(history_path), 'places_temp.sqlite')
            try:
                shutil.copy2(history_path, temp_path)
            except Exception as e:
                logger.error(f"Error copying Firefox history file: {e}")
                return
            
            try:
                conn = sqlite3.connect(temp_path)
                cursor = conn.cursor()
                
                last_check = self.last_checked.get('firefox', datetime.min)
                
                query = """
                    SELECT url, title, last_visit_date/1000000 
                    FROM moz_places 
                    WHERE last_visit_date/1000000 > ?
                    ORDER BY last_visit_date DESC
                    LIMIT 10
                """
                
                cursor.execute(query, (last_check.timestamp(),))
                results = cursor.fetchall()
                
                for url, title, visit_time in results:
                    visit_datetime = datetime.fromtimestamp(visit_time)
                    self.log_browser_history('firefox', url, title, visit_datetime)
                
                if results:
                    self.last_checked['firefox'] = datetime.now()
                    logger.info(f"Found {len(results)} new Firefox history entries")
                    
            finally:
                if 'conn' in locals():
                    conn.close()
                if os.path.exists(temp_path):
                    os.remove(temp_path)
                    
        except Exception as e:
            logger.error(f"Error processing Firefox history: {e}")

    def log_browser_history(self, browser, url, title, visit_time, notify=False):
        """Log browser history entry"""
        try:
            if not url or url.startswith(('chrome://', 'edge://', 'brave://', 'about:')):
                return
            
            from src.central_logger import central_logger
            
            # Ensure timestamp is in Eastern time
            current_time = datetime.now(self.timezone)
            
            data = {
                "browser": browser,
                "url": url,
                "title": title or "No Title",
                "visit_time": visit_time.isoformat(),
                "timestamp": current_time.isoformat(),
                "notify": notify
            }
            
            central_logger.log_event("browser_history", data)
            
        except Exception as e:
            logger.error(f"Error logging browser history: {e}", exc_info=True)

    def stop(self):
        """Stop the browser monitor"""
        if self.stop_event:
            self.stop_event.set()
            logger.info("Browser monitor stopped")

if __name__ == "__main__":
    from threading import Event
    stop_event = Event()
    monitor = BrowserMonitor(stop_event)
    monitor.start()
