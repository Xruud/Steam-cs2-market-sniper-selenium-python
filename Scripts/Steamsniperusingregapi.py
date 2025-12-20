import threading
import time
import random
import os
import winsound
import json
import queue
import shutil
import platform
import sys
import re
import requests
import urllib.parse
from collections import deque
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (TimeoutException, WebDriverException, 
                                      NoSuchWindowException, NoSuchElementException,
                                      StaleElementReferenceException)
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from collections import OrderedDict
import copy
from fake_useragent import UserAgent
from concurrent.futures import ThreadPoolExecutor, as_completed

# ===== CONFIGURATION ===== #
MARKET_URLS = OrderedDict([
    (1, "https://steamcommunity.com/market/listings/730/M4A4%20%7C%20Choppa%20(Minimal%20Wear)"),
    (2, "https://steamcommunity.com/market/listings/730/USP-S%20%7C%20PC-GRN%20(Minimal%20Wear)"),
    (3, "https://steamcommunity.com/market/listings/730/XM1014%20%7C%20Mockingbird%20(Minimal%20Wear)"),
    (4, "https://steamcommunity.com/market/listings/730/SSG%2008%20%7C%20Memorial%20(Minimal%20Wear)"),
    (5, "https://steamcommunity.com/market/listings/730/P2000%20%7C%20Sure%20Grip%20(Minimal%20Wear)"),
    (6, "https://steamcommunity.com/market/listings/730/MP9%20%7C%20Nexus%20(Minimal%20Wear)"),
    (7, "https://steamcommunity.com/market/listings/730/MAG-7%20%7C%20Resupply%20(Minimal%20Wear)")
])

# ===== PER-URL FLOAT SETTINGS ===== #
URL_FLOAT_CONFIG = {
    1: { 
        'float_direction': 0,  # 0 = low float (<= threshold), 1 = high float (>= threshold)
        'price_float_table': {
            1.15: 0.1025,
            1.3: 0.1
        }
    },
    2: {  
        'float_direction': 0,
        'price_float_table': {
            0.17: 0.1025,
            0.2: 0.1
        }
    },
    3: { 
        'float_direction': 0,
        'price_float_table': {
            0.16: 0.30125,
            0.2: 0.3
        }
    },
    4: { 
        'float_direction': 0,
        'price_float_table': {
            0.23: 0.09333,
            0.26: 0.0865,
            0.3: 0.08
        }
    }
}

# Sniper settings for each URL
URL_SNIPER_CONFIG = {
    1: {
        'check_pattern': 0,
        'target_pattern': 699,
        'auto_purchase': True,
        'pages_to_check': 1,
        'sniping_window_close_delay': (3, 5),
        'click_reload_button': 0
    },
    2: {
        'check_pattern': 0,
        'target_pattern': 699,
        'auto_purchase': True,
        'pages_to_check': 12,
        'sniping_window_close_delay': (3, 5),
        'click_reload_button': 0
    },
    3: {
        'check_pattern': 0,
        'target_pattern': 699,
        'auto_purchase': True,
        'pages_to_check': 25,
        'sniping_window_close_delay': (3, 5),
        'click_reload_button': 0
    },
    4: {
        'check_pattern': 0,
        'target_pattern': 699,
        'auto_purchase': True,
        'pages_to_check': 1,
        'sniping_window_close_delay': (3, 5),
        'click_reload_button': 0
    }
}

# Timing settings (all in seconds)
TIMING_SETTINGS = {
    'monitoring_delay_min': 1.5,  # Minimum delay between API checks
    'monitoring_delay_max': 1.5,  # Maximum delay between API checks
    'verification_start_delay': 0, # in seconds
    'page_nav_delay_min': 0, 
    'page_nav_delay_max': 51,
    'wait_after_sort_min': 0,
    'wait_after_sort_max': 50,
    'verification_retry_delay': (15, 20),# in seconds
    'verification_mismatch_close': (8, 10), # in seconds
    'sort_button_press_delay': (0, 0.05), # in seconds
    'sniper_timeout': 30, # in seconds
    'reload_button_wait': 0.01,  # Wait time for reload button to appear in seconds
    'error_429_cooldown_min': 300,  # Minimum cooldown for 429 errors in seconds
    'error_429_cooldown_max': 350,  # Maximum cooldown for 429 errors in seconds
    'error_check_interval': 2,  # Interval to check for 429 errors
    'steam_rate_limit_check_delay': 10  # Delay for Steam rate limit check (seconds)
}

# Verification system settings
VERIFICATION_SETTINGS = {
    'initial_attempts': 1,
    'retry_increment': 1,
    'max_attempts': 12,
    'max_count_diff': 5,
    'max_skins_to_buy_limit': 5
}

# Cooldown configuration
COOLDOWN_CONFIG = {
    'threshold': 120,          # Count change threshold to trigger cooldown
    'time_window': 120,       # Time window to check for changes (2 minutes)
    'cooldown_period': 120,   # Cooldown duration (5 minutes)
    'min_data_points': 5      # Minimum data points needed before checking
}

# Window size settings for verification windows
WINDOW_SETTINGS = {
    'min_width': 1000,
    'max_width': 1200,
    'min_height': 800,
    'max_height': 900
}

# Profile paths
PROFILE_PATHS = [
    os.path.join(os.getcwd(), "ChromeSteamProfiles01"),
    os.path.join(os.getcwd(), "ChromeSteamProfiles02"),
    os.path.join(os.getcwd(), "ChromeSteamProfiles03"),
    os.path.join(os.getcwd(), "ChromeSteamProfiles04"),
    os.path.join(os.getcwd(), "ChromeSteamProfiles05")
]

# Prewarmed profiles directory
PREWARMED_DIR = os.path.join(os.getcwd(), "prewarmed__profile0")

# Monitoring settings
MONITORING_SETTINGS = {
    'extraction_timeout': 15,  # seconds for item_nameid extraction
    'max_workers': 4,  # number of parallel threads for item_nameid extraction
}

# Status tracking
URL_STATUS = {}
for url_id in MARKET_URLS:
    URL_STATUS[url_id] = {
        'request_count': 0,
        'current_count': "N/A",
        'last_change': "N/A",
        'last_activity': "",
        'item_nameid': "N/A"
    }

# Verification status tracking
URL_VERIFICATION_STATUS = {}
for url_id in MARKET_URLS:
    URL_VERIFICATION_STATUS[url_id] = {
        'expected_count': "N/A",
        'actual_count': "N/A",
        'profile_used': "N/A",
        'retry_left': "N/A",
        'next_retry': "",
        'status': "Idle",
        'last_verification': "",
        'attempts': 0
    }

# Sniper status tracking
URL_SNIPER_STATUS = {}
for url_id in MARKET_URLS:
    URL_SNIPER_STATUS[url_id] = {
        'max_skins_to_buy': 0,
        'skins_remaining': 0,
        'pages_remaining': 0,
        'skins_bought': 0,
        'lowest_float': None,
        'highest_price': 0,
        'current_page': 0,
        'status': 'Idle',
        'extracted_data': []
    }

# Statistics tracking
URL_STATISTICS = {}
for url_id in MARKET_URLS:
    URL_STATISTICS[url_id] = {
        'changes_count': 0,           # Number of changes detected
        'matches_count': 0,           # Number of successful verifications
        'total_difference': 0,        # Total difference in counts (capped)
        'good_skins_found': 0         # Number of good skins found and purchased
    }

# Cooldown tracking
URL_COOLDOWN = {}
for url_id in MARKET_URLS:
    URL_COOLDOWN[url_id] = {
        'cooldown_until': 0,          # Timestamp when cooldown ends
        'count_history': deque(maxlen=1000),  # History of (timestamp, count) pairs
        'last_checked': 0             # Last time cooldown was checked
    }

# Global profile tracking per URL (persistent across verifications)
URL_PROFILE_INDEX = {}
for url_id in MARKET_URLS:
    URL_PROFILE_INDEX[url_id] = random.randint(0, len(PROFILE_PATHS)-1)

# Lock for thread-safe status updates
URL_STATUS_LOCK = threading.Lock()

# Global task tracking - now using a list to track multiple tasks per URL
ACTIVE_TASKS = {}
TASK_LOCK = threading.Lock()

# Hotkey control
VERIFICATION_PAUSED = False
PAUSE_LOCK = threading.Lock()

# Global 429 error tracking
ERROR_429_COOLDOWN = {
    'cooldown_until': 0,  # Timestamp when 429 cooldown ends
    'last_detected': 0,   # Timestamp when 429 was last detected
    'detected_by': None   # URL ID that detected the 429 error
}
ERROR_429_LOCK = threading.Lock()

# Store item_nameid for each URL
URL_ITEM_NAMEIDS = {}

# ===== HOTKEY HANDLER ===== #
def check_hotkey():
    """Check for Ctrl+D hotkey to toggle verification pause state"""
    global VERIFICATION_PAUSED
    
    if platform.system() == 'Windows':
        import msvcrt
        if msvcrt.kbhit():
            key = msvcrt.getch()
            if key == b'\x04':  # Ctrl+D
                with PAUSE_LOCK:
                    VERIFICATION_PAUSED = not VERIFICATION_PAUSED
                return True
    else:
        import select
        import termios
        import tty
        
        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)
        try:
            tty.setcbreak(fd)
            if select.select([sys.stdin], [], [], 0) == ([sys.stdin], [], []):
                key = sys.stdin.read(1)
                if key == '\x04':  # Ctrl+D
                    with PAUSE_LOCK:
                        VERIFICATION_PAUSED = not VERIFICATION_PAUSED
                    return True
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
    return False

# ===== PROFILE MANAGEMENT ===== #
class ProfileManager:
    def __init__(self):
        self.base_profiles = PROFILE_PATHS
        self.temp_profiles = {}
        self.profile_queues = {}
        self.lock = threading.Lock()
        self.running = True
        self.initialize_profiles()
        
    def initialize_profiles(self):
        """Create or load persistent prewarmed profiles"""
        if not os.path.exists(PREWARMED_DIR):
            os.makedirs(PREWARMED_DIR)
            
        for base_path in self.base_profiles:
            base_name = os.path.basename(base_path)
            self.temp_profiles[base_path] = []
            self.profile_queues[base_path] = queue.Queue()
            
            base_prewarmed = os.path.join(PREWARMED_DIR, base_name)
            if not os.path.exists(base_prewarmed):
                os.makedirs(base_prewarmed)
                
            for i in range(2):
                temp_path = os.path.join(base_prewarmed, f"temp_{i}")
                if not os.path.exists(temp_path):
                    shutil.copytree(base_path, temp_path)
                self.temp_profiles[base_path].append(temp_path)
                self.profile_queues[base_path].put(temp_path)
    
    def get_temp_profile(self, base_path):
        """Get next available temporary profile for a base"""
        with self.lock:
            if self.profile_queues[base_path].empty():
                temp_idx = len(self.temp_profiles[base_path])
                base_name = os.path.basename(base_path)
                base_prewarmed = os.path.join(PREWARMED_DIR, base_name)
                temp_path = os.path.join(base_prewarmed, f"temp_{temp_idx}")
                shutil.copytree(base_path, temp_path)
                self.temp_profiles[base_path].append(temp_path)
                return temp_path
            
            return self.profile_queues[base_path].get()
    
    def return_temp_profile(self, base_path, temp_path):
        """Return profile to queue after use"""
        with self.lock:
            self.profile_queues[base_path].put(temp_path)

# Global profile manager
PROFILE_MANAGER = ProfileManager()

# ===== ERROR 429 HANDLING ===== #
def check_429_error(driver):
    """Check if the page contains a 429 error message (SIH extension type)"""
    try:
        # Look for the specific 429 error element
        error_elements = driver.find_elements(
            By.XPATH, 
            "//span[contains(@class, 'sih_label') and contains(@class, 'sih_label_warning') and contains(text(), '429')]"
        )
        
        # Also check for other indicators of 429 errors
        page_text = driver.page_source
        if "Too Many Requests" in page_text or "429" in page_text:
            return True
            
        return len(error_elements) > 0
    except:
        return False

# NEW: Steam rate limit error detection (full page type)
def check_steam_rate_limit_error(driver):
    """Check if the page contains Steam's full-page rate limiting error"""
    try:
        # Check for the error container structure from the provided HTML
        error_container = driver.find_elements(By.CLASS_NAME, "error_ctn")
        if error_container:
            # Check for mainContents div with Error text
            main_contents = driver.find_elements(By.ID, "mainContents")
            if main_contents:
                error_text = main_contents[0].text
                if "Error" in error_text and "h2" in driver.page_source:
                    # Additional check for the specific error page structure
                    page_html = driver.page_source
                    if '<h2>Error</h2>' in page_html or 'class="error_ctn"' in page_html:
                        return True
        
        # Alternative check for Steam rate limiting pages
        page_title = driver.title.lower()
        if "error" in page_title and "steam" in page_title:
            return True
            
        # Check for rate limiting specific text
        page_text = driver.page_source.lower()
        if "too many requests" in page_text or "rate limit" in page_text:
            return True
            
        return False
    except Exception as e:
        print(f"Error checking Steam rate limit: {e}")
        return False

def is_in_429_cooldown():
    """Check if we're currently in a 429 cooldown period"""
    with ERROR_429_LOCK:
        return time.time() < ERROR_429_COOLDOWN['cooldown_until']

def get_429_cooldown_remaining():
    """Get remaining 429 cooldown time"""
    with ERROR_429_LOCK:
        cooldown_end = ERROR_429_COOLDOWN['cooldown_until']
        remaining = max(0, cooldown_end - time.time())
        return remaining

def trigger_429_cooldown(detected_by=None):
    """Trigger a 429 cooldown period for all URLs"""
    with ERROR_429_LOCK:
        cooldown_end = time.time() + random.randint(
            TIMING_SETTINGS['error_429_cooldown_min'], 
            TIMING_SETTINGS['error_429_cooldown_max']
        )
        ERROR_429_COOLDOWN['cooldown_until'] = cooldown_end
        ERROR_429_COOLDOWN['last_detected'] = time.time()
        ERROR_429_COOLDOWN['detected_by'] = detected_by
        
        # Cancel all active tasks
        with TASK_LOCK:
            for task_id, task in list(ACTIVE_TASKS.items()):
                task.stop_event.set()
                del ACTIVE_TASKS[task_id]
        
        # Update all URL statuses
        with URL_STATUS_LOCK:
            for url_id in MARKET_URLS:
                URL_STATUS[url_id]['last_activity'] = f"429 Cooldown until {time.strftime('%H:%M:%S', time.localtime(cooldown_end))}"
        
        print(f"429 Error detected! Cooldown triggered for {int(cooldown_end - time.time())} seconds")

# ===== COOLDOWN MANAGEMENT ===== #
def check_cooldown_condition(url_id, current_count):
    """
    Check if the URL should enter cooldown based on count changes
    Returns True if cooldown should be triggered
    """
    with URL_STATUS_LOCK:
        cooldown_info = URL_COOLDOWN[url_id]
        current_time = time.time()
        
        # Add current count to history
        cooldown_info['count_history'].append((current_time, current_count))
        
        # Remove entries older than time window
        while (cooldown_info['count_history'] and 
               current_time - cooldown_info['count_history'][0][0] > COOLDOWN_CONFIG['time_window']):
            cooldown_info['count_history'].popleft()
        
        # Check if we have enough data points
        if len(cooldown_info['count_history']) < COOLDOWN_CONFIG['min_data_points']:
            return False
        
        # Calculate min and max counts in the time window
        counts = [count for _, count in cooldown_info['count_history']]
        min_count = min(counts)
        max_count = max(counts)
        
        # Check if the difference exceeds threshold
        if abs(max_count - min_count) >= COOLDOWN_CONFIG['threshold']:
            return True
        
        return False

def trigger_cooldown(url_id):
    """Trigger cooldown for a specific URL"""
    with URL_STATUS_LOCK:
        cooldown_end = time.time() + COOLDOWN_CONFIG['cooldown_period']
        URL_COOLDOWN[url_id]['cooldown_until'] = cooldown_end
        URL_STATUS[url_id]['last_activity'] = f"Cooldown until {time.strftime('%H:%M:%S', time.localtime(cooldown_end))}"
        
        # Cancel any ongoing verification tasks for this URL
        with TASK_LOCK:
            tasks_to_remove = []
            for task_id, task in ACTIVE_TASKS.items():
                if task.url_id == url_id:
                    task.stop_event.set()
                    tasks_to_remove.append(task_id)
            
            for task_id in tasks_to_remove:
                del ACTIVE_TASKS[task_id]
        
        print(f"URL {url_id}: Cooldown triggered for {COOLDOWN_CONFIG['cooldown_period']} seconds")

def is_in_cooldown(url_id):
    """Check if a URL is currently in cooldown"""
    with URL_STATUS_LOCK:
        return time.time() < URL_COOLDOWN[url_id]['cooldown_until']

def get_cooldown_remaining(url_id):
    """Get remaining cooldown time for a URL"""
    with URL_STATUS_LOCK:
        cooldown_end = URL_COOLDOWN[url_id]['cooldown_until']
        remaining = max(0, cooldown_end - time.time())
        return remaining

# ===== ITEM NAMEID EXTRACTION ===== #
def extract_item_nameid_for_url(market_url):
    """
    Extracts item_nameid for a single URL using its own browser instance.
    """
    chrome_options = Options()
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--log-level=3")
    chrome_options.add_argument("--headless")  # Run in background
    chrome_options.add_experimental_option("excludeSwitches", ["enable-logging"])
    
    # Use a random user agent
    ua = UserAgent()
    chrome_options.add_argument(f'--user-agent={ua.random}')
    
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    item_nameid = None
    
    try:
        # Navigate to the market page
        driver.get(market_url)
        
        # Wait for the page to load
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "searchResultsRows"))
        )
        
        # Inject script to capture network requests
        script = """
        window.capturedItemUrl = null;
        const originalOpen = XMLHttpRequest.prototype.open;
        XMLHttpRequest.prototype.open = function(method, url) {
            if (url.includes('itemordershistogram')) {
                window.capturedItemUrl = url;
            }
            return originalOpen.apply(this, arguments);
        };
        
        const originalFetch = window.fetch;
        window.fetch = function(input, init) {
            const url = typeof input === 'string' ? input : input.url;
            if (url.includes('itemordershistogram')) {
                window.capturedItemUrl = url;
            }
            return originalFetch(input, init);
        };
        """
        driver.execute_script(script)
        
        # Wait for the request to be captured with a timeout
        start_time = time.time()
        while time.time() - start_time < MONITORING_SETTINGS['extraction_timeout']:
            captured_url = driver.execute_script("return window.capturedItemUrl;")
            if captured_url:
                # Extract item_nameid from the URL
                parsed_url = urllib.parse.urlparse(captured_url)
                query_params = urllib.parse.parse_qs(parsed_url.query)
                if 'item_nameid' in query_params:
                    item_nameid = query_params['item_nameid'][0]
                    break
            time.sleep(0.5)
        
        # If network method failed, try other methods
        if not item_nameid:
            # Method 1: Try to find item_nameid in the page source
            page_source = driver.page_source
            match = re.search(r"g_rgAppContextData.*?item_nameid.*?(\d+)", page_source)
            if match:
                item_nameid = match.group(1)
            else:
                # Method 2: Try to extract from JavaScript variables
                try:
                    item_nameid = driver.execute_script("""
                        if (typeof g_rgAppContextData !== 'undefined' && g_rgAppContextData[730]) {
                            return g_rgAppContextData[730].item_nameid;
                        }
                        return null;
                    """)
                except:
                    pass
            
    except Exception as e:
        print(f"Error extracting item_nameid for {market_url}: {e}")
    finally:
        driver.quit()
    
    return market_url, item_nameid

def extract_all_item_nameids_parallel():
    """
    Extracts all item_nameid values from Steam market pages using parallel processing.
    """
    print("Extracting item_nameid values in parallel...")
    
    # Use ThreadPoolExecutor to process all URLs simultaneously
    with ThreadPoolExecutor(max_workers=MONITORING_SETTINGS['max_workers']) as executor:
        # Submit all tasks
        future_to_url = {executor.submit(extract_item_nameid_for_url, url): url for url in MARKET_URLS.values()}
        
        # Process results as they complete
        item_nameids = {}
        for future in as_completed(future_to_url):
            url = future_to_url[future]
            try:
                result_url, item_nameid = future.result()
                if item_nameid:
                    item_nameids[result_url] = item_nameid
                    print(f"Extracted item_nameid for {result_url}: {item_nameid}")
                    
                    # Update URL status
                    url_id = [k for k, v in MARKET_URLS.items() if v == result_url][0]
                    with URL_STATUS_LOCK:
                        URL_STATUS[url_id]['item_nameid'] = item_nameid
                        URL_STATUS[url_id]['last_activity'] = f"NameID extracted: {item_nameid}"
                else:
                    print(f"Failed to extract item_nameid for {url}")
            except Exception as e:
                print(f"Error processing {url}: {e}")
    
    return item_nameids

# ===== API-BASED MONITORING ===== #
def get_listings_count(item_nameid):
    """
    Fetches and extracts the total number of sell listings from a Steam Market itemordershistogram API.
    Uses a random User-Agent for each request.
    """
    # Check if we're in 429 cooldown
    if is_in_429_cooldown():
        return None
    
    # Generate a random user agent for this request
    ua = UserAgent()
    random_user_agent = ua.random
    
    # Construct the URL with the provided item_nameid
    url = f"https://steamcommunity.com/market/itemordershistogram?country=UK&language=english&currency=3&item_nameid={item_nameid}"
    
    # Set headers with random user agent and referer
    headers = {
        'User-Agent': random_user_agent,
        'Referer': 'https://steamcommunity.com/market/',
        'Accept': 'application/json',
    }
    
    try:
        # Make the request
        response = requests.get(url, headers=headers, timeout=10)
        
        # Check for 429 status code
        if response.status_code == 429:
            print("API returned 429 status code - triggering cooldown")
            trigger_429_cooldown("API")
            return None
            
        response.raise_for_status()  # Raise an exception for bad status codes
        
        # Parse JSON response
        data = response.json()
        
        # Extract the sell order summary HTML
        sell_order_summary = data.get('sell_order_summary', '')
        
        # Use regex to extract the number of listings
        match = re.search(r'<span class="market_commodity_orders_header_promote">(\d+,?\d*)<\/span>', sell_order_summary)
        
        if match:
            # Extract the number and remove any commas (e.g., "52,301" -> "52301")
            number_str = match.group(1).replace(',', '')
            return int(number_str)
        else:
            return None
            
    except (requests.exceptions.RequestException, json.JSONDecodeError):
        return None

def monitor_item(item_nameid, market_url, url_id):
    """
    Monitors a specific item using its item_nameid, detects count changes.
    """
    last_count = None
    
    while True:
        # Check if verification is paused
        with PAUSE_LOCK:
            if VERIFICATION_PAUSED:
                time.sleep(1)
                continue
        
        # Check if we're in 429 cooldown
        if is_in_429_cooldown():
            cooldown_left = get_429_cooldown_remaining()
            if cooldown_left > 0:
                with URL_STATUS_LOCK:
                    URL_STATUS[url_id]['last_activity'] = f"429 Cooldown: {int(cooldown_left)}s remaining"
                time.sleep(min(10, cooldown_left))
                continue
        
        # Check if URL is in cooldown
        if is_in_cooldown(url_id):
            cooldown_left = get_cooldown_remaining(url_id)
            if cooldown_left > 0:
                with URL_STATUS_LOCK:
                    URL_STATUS[url_id]['last_activity'] = f"Cooldown: {int(cooldown_left)}s remaining"
                time.sleep(min(10, cooldown_left))
                continue
        
        # Get the current listings count
        count = get_listings_count(item_nameid)
        
        if count is not None:
            with URL_STATUS_LOCK:
                URL_STATUS[url_id]['request_count'] += 1
                URL_STATUS[url_id]['current_count'] = count
                URL_STATUS[url_id]['last_activity'] = f"API check: {count}"
            
            # Check for cooldown condition
            if check_cooldown_condition(url_id, count):
                trigger_cooldown(url_id)
                continue
            
            # Check for count changes
            if last_count is not None and count > last_count:
                print(f"URL {url_id}: Count changed {last_count} → {count}")
                handle_count_change(url_id, last_count, count)
            
            last_count = count
        
        # Random delay between checks
        delay = random.uniform(TIMING_SETTINGS['monitoring_delay_min'], 
                              TIMING_SETTINGS['monitoring_delay_max'])
        time.sleep(delay)

# ===== SNIPER FUNCTIONS ===== #
def get_random_delay(min_ms, max_ms):
    """Generate a random delay in seconds within specified range"""
    return random.uniform(min_ms, max_ms) / 1000.0

def verify_total_listings(driver, expected_count):
    """Verify the number of listings matches expected value"""
    try:
        # Wait for the page to fully load and the total count element to be present
        total_element = WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.ID, "searchResults_total"))
        )
        
        total_text = total_element.text
        # Ensure we're comparing integers
        total_number = int(total_text.replace(',', ''))
        expected_int = int(expected_count)
        
        # Accept counts that are equal to or higher than expected
        return total_number >= expected_int, total_number
    except Exception as e:
        print(f"Error verifying total listings: {str(e)}")
        return False, 0

def get_sort_button(driver):
    """Retrieves the sort button element through shadow DOM"""
    try:
        # Wait for the utility belt to be present and fully loaded
        utility_belt = WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.TAG_NAME, "csfloat-utility-belt"))
        )
        
        utility_shadow = driver.execute_script("return arguments[0].shadowRoot", utility_belt)
        sort_listings = utility_shadow.find_element(By.CSS_SELECTOR, "csfloat-sort-listings")
        sort_shadow = driver.execute_script("return arguments[0].shadowRoot", sort_listings)
        steam_button = sort_shadow.find_element(By.CSS_SELECTOR, "csfloat-steam-button")
        button_shadow = driver.execute_script("return arguments[0].shadowRoot", steam_button)
        
        return button_shadow.find_element(By.CSS_SELECTOR, "a.btn_small")
    except Exception as e:
        print(f"Failed to locate sort button: {str(e)}")
        return None

def get_sort_button_text(driver):
    """Gets the text of the sort button to check sorting status"""
    sort_button = get_sort_button(driver)
    if sort_button:
        return sort_button.text.strip()
    return ""

def is_sorting_complete(driver, float_direction):
    """Checks if sorting is complete based on button text"""
    button_text = get_sort_button_text(driver)
    
    if float_direction == 0:  # Low float
        return "▲" in button_text
    else:  # High float
        return "▼" in button_text

def wait_for_listing_float_loaded(driver, listing_index):
    """Waits for a specific listing to have its float loaded (not showing 'Loading')"""
    try:
        WebDriverWait(driver, 15).until(
            lambda d: not any("Loading" in listing.text 
                             for listing in d.find_elements(
                                 By.CSS_SELECTOR, 
                                 f"#searchResultsRows > div.market_listing_row:nth-child({listing_index})"
                             ))
        )
        return True
    except TimeoutException:
        print(f"Timed out waiting for listing #{listing_index} to load float")
        return False

def wait_for_all_listings_loaded(driver):
    """Waits for all 100 listings to be present in DOM"""
    try:
        WebDriverWait(driver, 15).until(
            lambda d: len(d.find_elements(By.CSS_SELECTOR, "#searchResultsRows > div.market_listing_row")) >= 100
        )
        return True
    except TimeoutException:
        print("Timed out waiting for all listings to load")
        return False

def get_listing_ids(driver, count=2):
    """Gets the IDs of the first few listings"""
    try:
        listings = driver.find_elements(
            By.CSS_SELECTOR, 
            "#searchResultsRows > div.market_listing_row"
        )[:count]
        return [listing.get_attribute("id") for listing in listings if listing.get_attribute("id")]
    except Exception as e:
        print(f"Error getting listing IDs: {e}")
        return []

def float_value_extracted(driver, listing):
    """Check if a listing has its float value fully extracted"""
    try:
        shadow_host = listing.find_element(By.CSS_SELECTOR, "csfloat-item-row-wrapper")
        shadow_text = driver.execute_script("""
            return arguments[0].shadowRoot
                .querySelector('div.float-row-wrapper')
                .textContent;
        """, shadow_host)
        return "Float:" in shadow_text and "Loading" not in shadow_text
    except:
        return False

def monitor_listing_updates(driver, timeout=3):
    """Monitor for dynamic updates to listings"""
    print("Monitoring for dynamic listing updates...")
    start_time = time.time()
    update_count = 0
    
    while time.time() - start_time < timeout:
        try:
            listings = driver.find_elements(
                By.CSS_SELECTOR, 
                "#searchResultsRows > div.market_listing_row"
            )[:5]
            
            updating = False
            for listing in listings:
                style = listing.get_attribute("style")
                if "opacity: 0.5" in style or "transition" in style:
                    updating = True
                    break
                    
                listing_text = listing.text
                if "Loading" in listing_text:
                    updating = True
                    break
            
            if not updating:
                if update_count > 0:
                    print("Dynamic updates completed")
                    return True
                else:
                    print("No dynamic updates detected")
                    return True
            else:
                update_count += 1
                
            time.sleep(0.1)
            
        except StaleElementReferenceException:
            update_count += 1
            time.sleep(0.1)
    
    print("Dynamic updates may still be in progress")
    return update_count > 0

def detect_visual_changes(driver):
    """Detect visual changes in listings that indicate sorting"""
    try:
        listings = driver.find_elements(
            By.CSS_SELECTOR, 
            "#searchResultsRows > div.market_listing_row"
        )[:3]
        
        for listing in listings:
            style = listing.get_attribute("style")
            if "display: none" not in style and "visibility: hidden" not in style:
                if float_value_extracted(driver, listing):
                    return True
        return False
    except Exception as e:
        print(f"Error detecting visual changes: {e}")
        return False

def check_sorting_completion(driver, original_ids, timeout=5):
    """
    Comprehensive check for sorting completion
    Combines multiple detection methods
    """
    print("Comprehensive check for sorting completion...")
    start_time = time.time()
    
    while time.time() - start_time < timeout:
        try:
            current_ids = get_listing_ids(driver, len(original_ids))
            if current_ids and current_ids != original_ids:
                print("Listing IDs changed - sorting completed")
                return True
            
            if detect_visual_changes(driver):
                print("Visual changes detected - sorting completed")
                return True
                
            if not monitor_listing_updates(driver, 1):
                print("No dynamic updates detected - sorting likely completed")
                return True
                
            time.sleep(0.1)
            
        except StaleElementReferenceException:
            print("Elements being refreshed - sorting in progress")
            time.sleep(0.1)
    
    print("NOTIFICATION: Sorting completion not fully confirmed")
    print("This could mean listings were already correctly sorted")
    return False

def perform_sorting(driver, clicks, float_direction, delay_between_clicks=0):
    """Performs sorting with precise timing control and optional delay between clicks"""
    if clicks < 1:
        return True
    
    sort_button = get_sort_button(driver)
    if not sort_button:
        print("Skipping sorting - button not found")
        return False
    
    print(f"Performing {clicks} sort clicks...")
    
    for click_num in range(1, clicks + 1):
        driver.execute_script("arguments[0].click();", sort_button)
        print(f"Click #{click_num} completed")
        
        # Add delay between clicks if specified (except after the last click)
        if click_num < clicks and delay_between_clicks > 0:
            time.sleep(delay_between_clicks)
    
    try:
        WebDriverWait(driver, 10).until(
            lambda d: is_sorting_complete(d, float_direction)
        )
        print("Sorting arrow appeared")
        return True
    except TimeoutException:
        print("Timed out waiting for sorting arrow to appear")
        return False

def is_button_clickable(button_element):
    """Comprehensive check if button is truly clickable"""
    try:
        is_enabled = button_element.is_enabled()
        is_displayed = button_element.is_displayed()
        disabled_attr = button_element.get_attribute("disabled")
        has_disabled_attr = disabled_attr is not None
        
        rect = button_element.rect
        if rect['width'] > 0 and rect['height'] > 0:
            is_in_viewport = True
        else:
            is_in_viewport = False
            
        button_classes = button_element.get_attribute("class")
        has_disabled_class = "disabled" in button_classes
            
        return (is_enabled and is_displayed and not has_disabled_attr and 
                is_in_viewport and not has_disabled_class)
        
    except StaleElementReferenceException:
        return False

def wait_for_content_stability(driver, timeout=10):
    """Wait for page content to stabilize after navigation"""
    start_time = time.time()
    previous_listing_count = 0
    stable_count = 0
    
    while time.time() - start_time < timeout:
        try:
            current_listings = driver.find_elements(
                By.CSS_SELECTOR, "#searchResultsRows > div.market_listing_row"
            )
            
            if len(current_listings) == previous_listing_count:
                stable_count += 1
                if stable_count >= 3:
                    return True
            else:
                stable_count = 0
                previous_listing_count = len(current_listings)
            
            time.sleep(0.1)
        except Exception:
            time.sleep(0.1)
    
    return False

def verify_page_change(driver, previous_page_data, timeout=5):
    """Verify that the page has actually changed after navigation"""
    start_time = time.time()
    
    while time.time() - start_time < timeout:
        try:
            current_listings = driver.find_elements(
                By.CSS_SELECTOR, "#searchResultsRows > div.market_listing_row"
            )[:2]
            
            current_data = []
            for listing in current_listings:
                try:
                    listing_id = listing.get_attribute("id")
                    current_data.append(listing_id)
                except:
                    pass
            
            if current_data and current_data != previous_page_data:
                return True
                
            time.sleep(0.1)
            
        except Exception as e:
            print(f"Error verifying page change: {str(e)}")
            time.sleep(0.1)
    
    return False

def wait_for_utility_belt_stable(driver):
    """Wait for CSFloat utility belt to be fully stable"""
    try:
        WebDriverWait(driver, 10).until(
            lambda d: d.execute_script("""
                return document.querySelector('csfloat-utility-belt') !== null &&
                       document.querySelector('csfloat-utility-belt').shadowRoot !== null;
            """)
        )
        return True
    except TimeoutException:
        print("Utility belt did not become stable")
        return False

def go_to_next_page(driver):
    """Enhanced navigation with robust pressability checks"""
    max_retries = 5
    for attempt in range(max_retries):
        try:
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.ID, "searchResultsRows"))
            )
            
            current_listings = driver.find_elements(
                By.CSS_SELECTOR, "#searchResultsRows > div.market_listing_row"
            )[:2]
            previous_page_data = [listing.get_attribute("id") for listing in current_listings if listing.get_attribute("id")]
            
            next_button = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "a.next_page"))
            )
            
            if not is_button_clickable(next_button):
                print("Button not clickable, retrying...")
                time.sleep(0.1)
                continue
                
            button_classes = next_button.get_attribute("class")
            if "disabled" in button_classes:
                print("Button has disabled class, stopping navigation")
                return False
                
            driver.execute_script("arguments[0].scrollIntoView(true);", next_button)
            
            nav_delay = get_random_delay(TIMING_SETTINGS['page_nav_delay_min'], TIMING_SETTINGS['page_nav_delay_max'])
            if nav_delay > 0:
                time.sleep(nav_delay)
            
            driver.execute_script("arguments[0].click();", next_button)
            
            if wait_for_content_stability(driver):
                if verify_page_change(driver, previous_page_data):
                    print("Page navigation successful")
                    return True
                else:
                    print("Page content did not change after navigation")
                    continue
            else:
                print("Content did not stabilize after navigation")
                continue
                
        except StaleElementReferenceException:
            print(f"Stale element on attempt {attempt + 1}, retrying...")
            time.sleep(0.1)
        except Exception as e:
            print(f"Navigation error on attempt {attempt + 1}: {str(e)}")
            time.sleep(0.1)
    
    return False

def extract_price(listing):
    """Extracts the first visible price from a listing using multiple methods"""
    try:
        price_container = listing.find_element(
            By.CSS_SELECTOR, 
            ".market_listing_right_cell.market_listing_their_price"
        )
        
        price_spans = price_container.find_elements(
            By.CSS_SELECTOR, 
            "span.market_listing_price"
        )
        
        for span in price_spans:
            if span.is_displayed():
                return span.text.strip()
        
        return price_container.text.strip().split('\n')[0]
    except Exception:
        pass
    
    try:
        price_container = listing.find_element(
            By.CSS_SELECTOR, 
            ".market_listing_action_buttons"
        )
        price_element = price_container.find_element(
            By.CSS_SELECTOR, 
            ".market_listing_price"
        )
        return price_element.text.strip()
    except Exception:
        pass
    
    listing_text = listing.text
    price_match = re.search(r"(\d+,\d+€)", listing_text)
    if price_match:
        return price_match.group(1)
    
    return "N/A"

def extract_listing_data(driver, listing):
    data = {"price": "N/A", "float_value": "N/A", "paint_seed": "N/A"}
    
    data["price"] = extract_price(listing)
    
    try:
        shadow_host = WebDriverWait(listing, 3).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "csfloat-item-row-wrapper"))
        )
        
        shadow_text = driver.execute_script("""
            return arguments[0].shadowRoot
                .querySelector('div.float-row-wrapper')
                .textContent;
        """, shadow_host)
        
        float_match = re.search(r"Float:\s*(\d+\.\d+)", shadow_text)
        if float_match:
            data["float_value"] = float_match.group(1)
        
        seed_match = re.search(r"Paint Seed:\s*(\d+)", shadow_text)
        if seed_match:
            data["paint_seed"] = seed_match.group(1)
    except Exception as e:
        print(f"Float/seed extraction failed: {str(e)}")
    
    return data

def click_reload_listings_button(driver):
    """Clicks the Reload Listings button if it exists"""
    try:
        # Wait for the reload button to be present
        reload_button = WebDriverWait(driver, TIMING_SETTINGS['reload_button_wait']).until(
            EC.presence_of_element_located((By.XPATH, "//a[contains(@class, 'btn_grey_white_innerfade') and contains(., 'Reload listings')]"))
        )
        
        if reload_button and reload_button.is_displayed():
            print("Reload listings button found, clicking it...")
            driver.execute_script("arguments[0].scrollIntoView({block: 'center', behavior: 'auto'});", reload_button)
            driver.execute_script("arguments[0].click();", reload_button)
            
            # Wait a moment for the reload to start
            time.sleep(1)
            
            # Wait for the page to reload by checking if the total count element is present again
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.ID, "searchResults_total"))
            )
            
            print("Page reloaded successfully")
            return True
    except Exception as e:
        print(f"Reload listings button not found or error clicking: {str(e)}")
    
    return False

def click_quick_buy(driver, listing_element):
    """Clicks the Quick Buy button for a listing"""
    try:
        action_container = listing_element.find_element(
            By.CSS_SELECTOR, 
            ".market_listing_right_cell.market_listing_action_buttons"
        )
        
        quick_buy_button = action_container.find_element(
            By.CSS_SELECTOR, 
            "a.item_market_action_button_green"
        )
        
        driver.execute_script("arguments[0].scrollIntoView({block: 'center', behavior: 'auto'});", quick_buy_button)
        
        print("Clicking Quick Buy button...")
        driver.execute_script("arguments[0].click();", quick_buy_button)
        return True
    except Exception as e:
        print(f"Failed to click Quick Buy button: {str(e)}")
        return False

def get_float_threshold_for_price(price_value, url_id):
    """
    Get the appropriate float threshold for a given price from the per-URL price-float table.
    Returns the float threshold for the closest price that is <= the given price.
    """
    price_float_table = URL_FLOAT_CONFIG[url_id]['price_float_table']
    
    # Find all prices in the table that are <= the given price
    valid_prices = [table_price for table_price in price_float_table.keys() if table_price <= price_value]
    
    if not valid_prices:
        # If no price in table is <= given price, use the lowest price in table
        min_price = min(price_float_table.keys())
        return price_float_table[min_price]
    
    # Use the highest valid price (closest to but not exceeding the given price)
    best_price = max(valid_prices)
    return price_float_table[best_price]

def check_skin_match(driver, listing_data, index, listing_element, remaining_purchases, sniper_config, sniper_status, url_id):
    """
    Checks if a skin matches the specified criteria using dynamic float thresholds based on price.
    Returns tuple: (is_match, purchase_attempted, remaining_purchases)
    """
    try:
        price_str = listing_data["price"].replace('€', '').replace(',', '.')
        price_value = float(price_str)
    except:
        price_value = float('inf')
    
    try:
        float_value = float(listing_data["float_value"])
    except:
        float_value = float('inf')
    
    # Update sniper status with highest price
    if price_value > sniper_status['highest_price']:
        sniper_status['highest_price'] = price_value
    
    # Update sniper status with lowest float
    if sniper_status['lowest_float'] is None or float_value < sniper_status['lowest_float']:
        sniper_status['lowest_float'] = float_value
    
    # Get dynamic float threshold based on price for this specific URL
    float_threshold = get_float_threshold_for_price(price_value, url_id)
    
    # Get float direction for this specific URL
    float_direction = URL_FLOAT_CONFIG[url_id]['float_direction']
    
    # Check float based on URL-specific direction
    if float_direction == 0:  # Low float
        float_match = float_value <= float_threshold
        float_info = f"Float: {listing_data['float_value']} {'✓' if float_match else '✗'} (Max: {float_threshold})"
    else:  # High float
        float_match = float_value >= float_threshold
        float_info = f"Float: {listing_data['float_value']} {'✓' if float_match else '✗'} (Min: {float_threshold})"
    
    # Check price against maximum price in table for this URL
    max_allowed_price = max(URL_FLOAT_CONFIG[url_id]['price_float_table'].keys())
    price_match = price_value <= max_allowed_price
    
    pattern_match = True
    
    if sniper_config['check_pattern'] == 1:
        try:
            pattern_match = int(listing_data["paint_seed"]) == sniper_config['target_pattern']
        except:
            pattern_match = False
    
    # Determine if all active criteria are met
    if float_match and price_match and pattern_match:
        print("\n" + "="*50)
        print(f"!!! MATCHING SKIN FOUND AT POSITION #{index} !!!")
        print("="*50)
        print(f"Price: {listing_data['price']} (<= {max_allowed_price}€)")
        if float_direction == 0:
            print(f"Float Value: {listing_data['float_value']} (<= {float_threshold})")
        else:
            print(f"Float Value: {listing_data['float_value']} (>= {float_threshold})")
        if sniper_config['check_pattern'] == 1:
            print(f"Paint Seed: {listing_data['paint_seed']} (== {sniper_config['target_pattern']})")
        print("="*50 + "\n")
        
        # Attempt to purchase if enabled and we have remaining purchases
        purchase_attempted = False
        if sniper_config['auto_purchase'] and remaining_purchases > 0:
            print("Attempting to purchase skin...")
            if click_quick_buy(driver, listing_element):
                print("Purchase initiated successfully!")
                remaining_purchases -= 1
                sniper_status['skins_bought'] += 1
                purchase_attempted = True
            else:
                print("Failed to initiate purchase")
        
        return True, purchase_attempted, remaining_purchases
    
    # Print non-matching results
    print(f"\nSkin #{index} does not match criteria:")
    print(f"  Price: {listing_data['price']} {'✓' if price_match else '✗'} (Max: {max_allowed_price}€)")
    print(f"  {float_info}")
    if sniper_config['check_pattern'] == 1:
        print(f"  Pattern: {listing_data['paint_seed']} {'✓' if pattern_match else '✗'} (Target: {sniper_config['target_pattern']})")
    
    return False, False, remaining_purchases

def process_current_page(driver, number_of_skins, remaining_purchases, sniper_config, sniper_status, url_id):
    """
    Processes all listings on the current page
    Returns tuple: (matches_found, purchases_made, remaining_purchases, should_stop)
    """
    should_stop = False
    
    try:
        listings = driver.find_elements(
            By.CSS_SELECTOR, 
            "#searchResultsRows > div.market_listing_row:not([style*='display: none'])"
        )[:number_of_skins]
    except StaleElementReferenceException:
        print("Listings became stale, refreshing...")
        listings = driver.find_elements(
            By.CSS_SELECTOR, 
            "#searchResultsRows > div.market_listing_row:not([style*='display: none'])"
        )[:number_of_skins]
    
    if not listings:
        print("No listings found on this page")
        return 0, 0, remaining_purchases, should_stop
    
    print(f"\nExtracting data for top {min(len(listings), number_of_skins)} listings:")
    print(f"Remaining skins to buy: {remaining_purchases}")
    
    # Add extracted data to sniper status for display
    sniper_status['extracted_data'] = []
    
    matches_found = 0
    purchases_made = 0
    for i, listing in enumerate(listings, 1):
        print(f"\n--- Processing Listing #{i} ---")
        try:
            driver.execute_script("arguments[0].scrollIntoView({block: 'center', behavior: 'auto'});", listing)
            
            listing_data = extract_listing_data(driver, listing)
            
            # Add to extracted data for display
            sniper_status['extracted_data'].append(listing_data)
            
            print(f"Price: {listing_data['price']}")
            print(f"Float Value: {listing_data['float_value']}")
            if sniper_config['check_pattern'] == 1:
                print(f"Paint Seed: {listing_data['paint_seed']}")
            
            is_match, purchase_attempted, remaining_purchases = check_skin_match(
                driver, listing_data, i, listing, remaining_purchases, sniper_config, sniper_status, url_id
            )
            
            if is_match:
                matches_found += 1
            if purchase_attempted:
                purchases_made += 1
                
            # Check if price exceeds max price (stopping condition)
            max_allowed_price = max(URL_FLOAT_CONFIG[url_id]['price_float_table'].keys())
            try:
                price_str = listing_data["price"].replace('€', '').replace(',', '.')
                price_value = float(price_str)
                if price_value > max_allowed_price:
                    print(f"Price {price_value} exceeds max price {max_allowed_price}, stopping after this page")
                    should_stop = True
            except:
                pass
                
            # Stop processing if we've reached the purchase limit
            if remaining_purchases <= 0:
                print("\n" + "="*50)
                print("!!! PURCHASE LIMIT REACHED !!!")
                print("="*50)
                print("Stopping further processing")
                print("="*50)
                should_stop = True
                break
                
        except StaleElementReferenceException:
            print("Listing became stale, retrying...")
            listings = driver.find_elements(
                By.CSS_SELECTOR, 
                "#searchResultsRows > div.market_listing_row:not([style*='display: none'])"
            )[:number_of_skins]
            if i <= len(listings):
                listing = listings[i-1]
                listing_data = extract_listing_data(driver, listing)
                sniper_status['extracted_data'].append(listing_data)
                print(f"Price: {listing_data['price']}")
                print(f"Float Value: {listing_data['float_value']}")
                if sniper_config['check_pattern'] == 1:
                    print(f"Paint Seed: {listing_data['paint_seed']}")
                is_match, purchase_attempted, remaining_purchases = check_skin_match(
                    driver, listing_data, i, listing, remaining_purchases, sniper_config, sniper_status, url_id
                )
                if is_match:
                    matches_found += 1
                if purchase_attempted:
                    purchases_made += 1
                    
                # Check stopping conditions after retry
                if remaining_purchases <= 0:
                    print("\n" + "="*50)
                    print("!!! PURCHASE LIMIT REACHED !!!")
                    print("="*50)
                    print("Stopping further processing")
                    print("="*50)
                    should_stop = True
                    break
            else:
                print("Could not recover stale element")
        except Exception as e:
            print(f"Error processing listing #{i}: {str(e)}")
    
    return matches_found, purchases_made, remaining_purchases, should_stop

# ===== SNIPER TASK ===== #
class SniperTask(threading.Thread):
    def __init__(self, url_id, url, expected_count, count_difference, task_id):
        super().__init__()
        self.url_id = url_id
        self.url = url
        self.expected_count = expected_count
        self.count_difference = count_difference
        self.task_id = task_id  # Unique identifier for this task
        self.driver = None
        self.profile_num = 0
        self.profile_path = ""
        self.stop_event = threading.Event()
        self.lock = threading.Lock()
        self.status = "Starting"
        self.verification_complete = False
        self.leave_window_open = False
        self.found_match = False
        self.count_obtained = False
        self.base_profile_path = ""
        self.aborted = False
        self.sniper_config = URL_SNIPER_CONFIG[url_id]
        self.sniper_timeout_timer = None
        self.error_check_timer = None
        self.steam_rate_limit_timer = None  # NEW: Timer for Steam rate limit check
        self.good_skins_found = 0
        
        # Apply hard limit to max skins to buy
        max_skins_limit = VERIFICATION_SETTINGS['max_skins_to_buy_limit']
        if count_difference > max_skins_limit:
            print(f"Count difference {count_difference} exceeds maximum limit {max_skins_limit}, capping to {max_skins_limit}")
            count_difference = max_skins_limit
        
        # Set max_skins_to_buy and number_of_skins to the count_difference
        self.max_skins_to_buy = count_difference
        self.number_of_skins = count_difference
        
        # Initialize sniper status for this URL
        with URL_STATUS_LOCK:
            URL_SNIPER_STATUS[self.url_id]['max_skins_to_buy'] = count_difference
            URL_SNIPER_STATUS[self.url_id]['skins_remaining'] = count_difference
            URL_SNIPER_STATUS[self.url_id]['pages_remaining'] = self.sniper_config['pages_to_check']
            URL_SNIPER_STATUS[self.url_id]['status'] = 'Starting'
            URL_SNIPER_STATUS[self.url_id]['skins_bought'] = 0
            URL_SNIPER_STATUS[self.url_id]['lowest_float'] = None
            URL_SNIPER_STATUS[self.url_id]['highest_price'] = 0
            URL_SNIPER_STATUS[self.url_id]['current_page'] = 0
            URL_SNIPER_STATUS[self.url_id]['extracted_data'] = []
        
    def run(self):
        try:
            # Check if we're in 429 cooldown before starting verification
            if is_in_429_cooldown():
                cooldown_left = get_429_cooldown_remaining()
                self.status = f"429 Cooldown active: {int(cooldown_left)}s remaining"
                print(f"URL {self.url_id}: Skipping verification - in 429 cooldown for {int(cooldown_left)} more seconds")
                return
            
            # Check if URL is in cooldown before starting verification
            if is_in_cooldown(self.url_id):
                cooldown_left = get_cooldown_remaining(self.url_id)
                self.status = f"Cooldown active: {int(cooldown_left)}s remaining"
                print(f"URL {self.url_id}: Skipping verification - in cooldown for {int(cooldown_left)} more seconds")
                return
            
            # ADDED VERIFICATION DELAY - Ensure this is at the very beginning
            if TIMING_SETTINGS['verification_start_delay'] > 0:
                self.status = f"Waiting {TIMING_SETTINGS['verification_start_delay']}s before starting"
                with URL_STATUS_LOCK:
                    URL_VERIFICATION_STATUS[self.url_id]['status'] = f"Waiting {TIMING_SETTINGS['verification_start_delay']}s"
                
                start_time = time.time()
                while time.time() - start_time < TIMING_SETTINGS['verification_start_delay']:
                    if self.stop_event.is_set():
                        return
                    time.sleep(0.1)
            
            # Update global verification status
            with URL_STATUS_LOCK:
                URL_VERIFICATION_STATUS[self.url_id] = {
                    'expected_count': self.expected_count,
                    'actual_count': "Pending",
                    'profile_used': "N/A",
                    'retry_left': VERIFICATION_SETTINGS['initial_attempts'],
                    'next_retry': "",
                    'status': "Verifying",
                    'last_verification': time.strftime('%H:%M:%S'),
                    'attempts': 1
                }
            
            # Main verification loop
            current_retry = 0
            while not self.stop_event.is_set() and current_retry < VERIFICATION_SETTINGS['initial_attempts']:
                current_retry += 1
                
                # Check if we entered 429 cooldown during verification delay
                if is_in_429_cooldown():
                    cooldown_left = get_429_cooldown_remaining()
                    self.status = f"429 Cooldown active: {int(cooldown_left)}s remaining"
                    print(f"URL {self.url_id}: Aborting verification - entered 429 cooldown during delay")
                    break
                
                # Check if URL entered cooldown during verification delay
                if is_in_cooldown(self.url_id):
                    cooldown_left = get_cooldown_remaining(self.url_id)
                    self.status = f"Cooldown active: {int(cooldown_left)}s remaining"
                    print(f"URL {self.url_id}: Aborting verification - entered cooldown during delay")
                    break
                
                # Update status
                with URL_STATUS_LOCK:
                    URL_VERIFICATION_STATUS[self.url_id]['attempts'] = current_retry
                    URL_VERIFICATION_STATUS[self.url_id]['retry_left'] = VERIFICATION_SETTINGS['initial_attempts'] - current_retry
                    URL_VERIFICATION_STATUS[self.url_id]['status'] = f"Attempt {current_retry}/{VERIFICATION_SETTINGS['initial_attempts']}"
                
                # Open browser with next profile
                self.open_browser()
                
                # Start error checking thread
                self.error_check_timer = threading.Thread(target=self.monitor_429_errors)
                self.error_check_timer.daemon = True
                self.error_check_timer.start()
                
                # Perform verification
                result = self.run_sniper()
                
                # Stop error checking thread
                if self.error_check_timer and self.error_check_timer.is_alive():
                    self.stop_event.set()
                
                # Cleanup browser for this attempt
                self.cleanup_browser()
                
                if result == "success":
                    # Update statistics for successful verification
                    with URL_STATUS_LOCK:
                        URL_STATISTICS[self.url_id]['matches_count'] += 1
                        URL_STATISTICS[self.url_id]['good_skins_found'] += self.good_skins_found
                    break
                elif result == "reverted":
                    break
                elif result == "429_error":
                    # 429 error already handled by monitor_429_errors
                    break
                
                # Wait before retry if needed
                if not self.stop_event.is_set() and current_retry < VERIFICATION_SETTINGS['initial_attempts']:
                    retry_delay = random.randint(*TIMING_SETTINGS['verification_retry_delay'])
                    self.status = f"Retrying in {retry_delay}s"
                    with URL_STATUS_LOCK:
                        URL_VERIFICATION_STATUS[self.url_id]['status'] = f"Retrying in {retry_delay}s"
                    
                    start_time = time.time()
                    while time.time() - start_time < retry_delay:
                        if self.stop_event.is_set():
                            break
                        time.sleep(0.1)
        
        finally:
            self.verification_complete = True
            
            # Cancel timeout timer if it exists
            if self.sniper_timeout_timer:
                self.sniper_timeout_timer.cancel()
            
            # Cancel Steam rate limit timer if it exists
            if self.steam_rate_limit_timer:
                self.steam_rate_limit_timer.cancel()
            
            # Remove this specific task from active tasks
            with TASK_LOCK:
                if self.task_id in ACTIVE_TASKS:
                    del ACTIVE_TASKS[self.task_id]
                
                # Reset verification status if no more tasks for this URL
                has_other_tasks = any(task_id.startswith(f"{self.url_id}_") for task_id in ACTIVE_TASKS.keys())
                if not has_other_tasks:
                    with URL_STATUS_LOCK:
                        URL_VERIFICATION_STATUS[self.url_id] = {
                            'expected_count': "N/A",
                            'actual_count': "N/A",
                            'profile_used': "N/A",
                            'retry_left': "N/A",
                            'next_retry': "",
                            'status': "Idle",
                            'last_verification': "",
                            'attempts': 0
                        }

    def monitor_429_errors(self):
        """Continuously monitor for 429 errors while the sniper is running"""
        while not self.stop_event.is_set() and self.driver:
            try:
                # Check for 429 error (SIH extension type)
                if check_429_error(self.driver):
                    print("429 Error detected in page! Triggering cooldown...")
                    trigger_429_cooldown(self.url_id)
                    self.stop_event.set()
                    return
                
                # Wait before checking again
                time.sleep(TIMING_SETTINGS['error_check_interval'])
            except Exception as e:
                print(f"Error in 429 monitoring: {e}")
                time.sleep(TIMING_SETTINGS['error_check_interval'])

    def check_steam_rate_limit_after_delay(self):
        """Check for Steam rate limit error after specified delay"""
        if self.stop_event.is_set() or not self.driver:
            return
            
        try:
            # Check for Steam rate limit error (full page type)
            if check_steam_rate_limit_error(self.driver):
                print("Steam rate limit error detected after delay! Triggering cooldown...")
                trigger_429_cooldown(self.url_id)
                self.stop_event.set()
        except Exception as e:
            print(f"Error in Steam rate limit check: {e}")

    def open_browser(self):
        """Open browser window for this attempt"""
        # Get next profile in rotation for this URL
        base_path, profile_num = self.get_next_profile()
        self.base_profile_path = base_path
        
        # Get temporary profile path
        temp_path = PROFILE_MANAGER.get_temp_profile(base_path)
        
        # Configure options with cache optimizations
        options = Options()
        options.add_argument(f"--user-data-dir={temp_path}")
        
        # Cache optimization settings
        options.add_argument("--disable-cache")
        options.add_argument("--disable-application-cache")
        options.add_argument("--disk-cache-size=0")
        options.add_argument("--media-cache-size=0")
        options.add_argument("--disable-gpu-shader-disk-cache")
        
        # Additional cache optimization preferences
        options.add_experimental_option("prefs", {
            "profile.exit_type": "Normal",
            "profile.exited_cleanly": True,
            "session.restore_onstartup": 0,
            "profile.default_content_setting_values.notifications": 2,
            "profile.managed_default_content_settings.images": 2,
            "disk-cache-size": 0,
            "media_cache_size": 0,
            "disable-cache": True
        })
        
        # Randomize window size within configured range
        width = random.randint(WINDOW_SETTINGS['min_width'], WINDOW_SETTINGS['max_width'])
        height = random.randint(WINDOW_SETTINGS['min_height'], WINDOW_SETTINGS['max_height'])
        options.add_argument(f"--window-size={width},{height}")
        
        options.add_argument("--no-first-run")
        options.add_argument("--no-default-browser-check")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)
        
        # Create driver
        service = Service(ChromeDriverManager().install())
        self.driver = webdriver.Chrome(service=service, options=options)
        self.profile_num = profile_num
        self.profile_path = temp_path
        
        # Update profile used in status
        with URL_STATUS_LOCK:
            URL_VERIFICATION_STATUS[self.url_id]['profile_used'] = self.profile_num
        
        # Load URL with random parameter to avoid caching
        rand_num = random.randint(1, 1000000)
        full_url = f"{self.url}?★%20&rand={rand_num}"
        
        # Clear cache before loading page
        self.driver.execute_script("window.localStorage.clear();")
        self.driver.execute_script("window.sessionStorage.clear();")
        
        self.driver.get(full_url)
        self.status = f"Page loading (Profile {self.profile_num})"
        self.count_obtained = False

    def run_sniper(self):
        """Run the sniper script logic"""
        try:
            # NEW: Check for Steam rate limit error immediately after page load
            if check_steam_rate_limit_error(self.driver):
                print("Steam rate limit error detected immediately after page load! Triggering cooldown...")
                trigger_429_cooldown(self.url_id)
                return "429_error"
            
            # NEW: Start timer to check for Steam rate limit error after specified delay
            self.steam_rate_limit_timer = threading.Timer(
                TIMING_SETTINGS['steam_rate_limit_check_delay'], 
                self.check_steam_rate_limit_after_delay
            )
            self.steam_rate_limit_timer.start()
            
            # Check if we're in 429 cooldown before proceeding
            if is_in_429_cooldown():
                self.status = "429 Cooldown active, aborting sniper"
                return "429_error"
            
            # NEW: Click reload listings button if configured to do so
            if self.sniper_config.get('click_reload_button', 0) == 1:
                print("Attempting to click reload listings button...")
                click_reload_listings_button(self.driver)
            
            # Verify total listings - accept counts that are equal to or higher than expected
            verification_passed, actual_count = verify_total_listings(self.driver, self.expected_count)
            
            # NEW: Cancel the Steam rate limit timer since we passed the verification stage
            if self.steam_rate_limit_timer:
                self.steam_rate_limit_timer.cancel()
            
            with URL_STATUS_LOCK:
                URL_VERIFICATION_STATUS[self.url_id]['actual_count'] = actual_count
            
            # Accept counts that are equal to or higher than expected
            if not verification_passed and actual_count < int(self.expected_count):
                diff = abs(actual_count - int(self.expected_count))
                if diff > VERIFICATION_SETTINGS['max_count_diff']:
                    self.status = f"❌ Aborted: Large difference ({diff})"
                    with URL_STATUS_LOCK:
                        URL_VERIFICATION_STATUS[self.url_id]['status'] = f"❌ Aborted: Diff {diff}"
                    return "aborted"
                else:
                    self.status = f"Count mismatch: Expected {self.expected_count}, got {actual_count}"
                    with URL_STATUS_LOCK:
                        URL_VERIFICATION_STATUS[self.url_id]['status'] = f"Mismatch: {actual_count}"
                    return "mismatch"
            elif actual_count >= int(self.expected_count):
                # Count is acceptable (equal to or higher than expected)
                verification_passed = True
            
            if not verification_passed:
                self.status = f"Count mismatch: Expected {self.expected_count}, got {actual_count}"
                with URL_STATUS_LOCK:
                    URL_VERIFICATION_STATUS[self.url_id]['status'] = f"Mismatch: {actual_count}"
                return "mismatch"
            
            # Update status
            self.status = "✓ Count verified, starting sniper"
            with URL_STATUS_LOCK:
                URL_VERIFICATION_STATUS[self.url_id]['status'] = "✓ Starting sniper"
                URL_SNIPER_STATUS[self.url_id]['status'] = 'Running'
            
            # Start sniper timeout timer
            print(f"Starting sniper timeout timer ({TIMING_SETTINGS['sniper_timeout']}s)")
            self.sniper_timeout_timer = threading.Timer(
                TIMING_SETTINGS['sniper_timeout'], 
                self.sniper_timeout_handler
            )
            self.sniper_timeout_timer.start()
            
            # Wait for page to fully load
            print("Waiting for initial page load...")
            if not wait_for_all_listings_loaded(self.driver):
                self.status = "Failed to load listings"
                return "error"
            
            total_matches = 0
            total_purchases = 0
            remaining_purchases = self.max_skins_to_buy
            
            # Get float direction for this specific URL
            float_direction = URL_FLOAT_CONFIG[self.url_id]['float_direction']
            
            # Process each page
            for page in range(1, self.sniper_config['pages_to_check'] + 1):
                # Check for 429 error before processing page
                if is_in_429_cooldown():
                    self.status = "429 Cooldown active, aborting sniper"
                    return "429_error"
                
                # Update sniper status
                with URL_STATUS_LOCK:
                    URL_SNIPER_STATUS[self.url_id]['current_page'] = page
                    URL_SNIPER_STATUS[self.url_id]['pages_remaining'] = self.sniper_config['pages_to_check'] - page
                    URL_SNIPER_STATUS[self.url_id]['skins_remaining'] = remaining_purchases
                
                # Check if we've reached the purchase limit before processing page
                if remaining_purchases <= 0:
                    print("\nPurchase limit reached before page processing")
                    break
                    
                print(f"\n{'='*50}")
                print(f"PROCESSING PAGE {page}/{self.sniper_config['pages_to_check']}")
                print(f"{'='*50}")
                
                # 1) Wait for first two listings to load
                print("Waiting for first two listings to load...")
                if not wait_for_listing_float_loaded(self.driver, 1) or not wait_for_listing_float_loaded(self.driver, 2):
                    print("Failed to load first two listings, skipping page")
                    continue
                
                # 2) Get IDs of first two listings
                original_ids = get_listing_ids(self.driver, 2)
                print(f"Original listing IDs: {original_ids}")
                
                # 3) Wait for 100th listing to load
                print("Waiting for 100th listing to load...")
                if not wait_for_listing_float_loaded(self.driver, 100):
                    print("Failed to load 100th listing, skipping page")
                    continue
                
                # Handle sorting based on page number
                if page == 1:
                    clicks = 2 if float_direction == 1 else 1
                    print(f"Sorting listings (clicking {clicks} times)...")
                    if not perform_sorting(self.driver, clicks, float_direction):
                        print("Failed to sort listings, skipping page")
                        continue
                else:
                    # For pages after the first, press sort button 3 times with delays
                    print("Pressing sort button 3 times with delays...")
                    delay_between_clicks = random.uniform(*TIMING_SETTINGS['sort_button_press_delay'])
                    if not perform_sorting(self.driver, 3, float_direction, delay_between_clicks):
                        print("Failed to sort listings, skipping page")
                        continue
                
                # 5) Check for sorting completion
                sorting_complete = check_sorting_completion(self.driver, original_ids, timeout=5)
                
                if not sorting_complete:
                    print("WARNING: Sorting completion not fully confirmed, proceeding anyway")
                
                # 7) Wait after sorting
                after_sort_delay = get_random_delay(TIMING_SETTINGS['wait_after_sort_min'], TIMING_SETTINGS['wait_after_sort_max'])
                if after_sort_delay > 0:
                    print(f"Waiting {after_sort_delay*1000:.0f}ms after sorting...")
                    time.sleep(after_sort_delay)
                
                # 8) Process current page
                page_matches, page_purchases, remaining_purchases, should_stop = process_current_page(
                    self.driver, self.number_of_skins, remaining_purchases, self.sniper_config, URL_SNIPER_STATUS[self.url_id], self.url_id
                )
                total_matches += page_matches
                total_purchases += page_purchases
                
                print(f"\nPage {page} summary: {page_matches} matches, {page_purchases} purchases")
                
                # Check if we should stop after this page
                if should_stop:
                    print("Stopping condition met, ending sniper")
                    break
                    
                # Stop if we've processed all requested pages
                if page >= self.sniper_config['pages_to_check']:
                    break
                    
                # Go to next page if available
                print("\nMoving to next page...")
                if not go_to_next_page(self.driver):
                    print("No more pages available")
                    break

            # Store the number of good skins found
            self.good_skins_found = total_purchases
            
            # Print final summary
            print("\n" + "="*50)
            print("SNIPER COMPLETE - SUMMARY")
            print("="*50)
            print(f"Checked {min(page, self.sniper_config['pages_to_check'])}/{self.sniper_config['pages_to_check']} pages")
            print(f"Found {total_matches} skins matching your criteria")
            if self.sniper_config['auto_purchase']:
                print(f"Purchased {total_purchases} skins")
            print(f"Purchase limit: {self.max_skins_to_buy}")
            print(f"Remaining skins to buy: {max(0, remaining_purchases)}")
            print("="*50)
            
            # Cancel timeout timer since we completed successfully
            if self.sniper_timeout_timer:
                self.sniper_timeout_timer.cancel()
                print("Sniper timeout timer cancelled")
            
            # Wait before closing if needed
            close_delay = random.randint(*self.sniper_config['sniping_window_close_delay'])
            print(f"Waiting {close_delay}s before closing...")
            time.sleep(close_delay)
            
            return "success"
                
        except Exception as e:
            self.status = f"Error: {str(e)[:30]}"
            with URL_STATUS_LOCK:
                URL_VERIFICATION_STATUS[self.url_id]['status'] = f"Error: {str(e)[:30]}"
            return "error"
    
    def sniper_timeout_handler(self):
        """Handler for sniper timeout - closes the browser if still open"""
        print(f"\n!!! SNIPER TIMEOUT REACHED ({TIMING_SETTINGS['sniper_timeout']}s) - CLOSING WINDOW !!!")
        self.cleanup_browser()
        self.stop_event.set()
    
    def get_next_profile(self):
        """Get next profile in rotation for this URL (persistent across verifications)"""
        global URL_PROFILE_INDEX
        
        # Rotate to next profile (this persists even after verification completes)
        URL_PROFILE_INDEX[self.url_id] = (URL_PROFILE_INDEX[self.url_id] + 1) % len(PROFILE_PATHS)
        
        profile_idx = URL_PROFILE_INDEX[self.url_id]
        return PROFILE_PATHS[profile_idx], profile_idx + 1
    
    def cleanup_browser(self):
        """Clean up browser resources for this attempt if needed"""
        if self.driver and not self.leave_window_open:
            try:
                # Clear browser cache before closing
                self.driver.execute_script("window.localStorage.clear();")
                self.driver.execute_script("window.sessionStorage.clear();")
                self.driver.execute_cdp_cmd('Network.clearBrowserCache', {})
                
                self.driver.quit()
                print("Browser window closed successfully")
            except Exception as e:
                print(f"Error closing browser: {str(e)}")
            
            # Return profile to manager for reuse
            if self.base_profile_path and self.profile_path:
                PROFILE_MANAGER.return_temp_profile(self.base_profile_path, self.profile_path)

# ===== TASK MANAGEMENT ===== #
def handle_count_change(url_id, old_count, new_count):
    global VERIFICATION_PAUSED
    
    # Check if verification is paused
    with PAUSE_LOCK:
        if VERIFICATION_PAUSED:
            print(f"URL {url_id}: Verification paused, skipping change")
            return
    
    # Check if we're in 429 cooldown
    if is_in_429_cooldown():
        cooldown_left = get_429_cooldown_remaining()
        print(f"URL {url_id}: 429 Cooldown active, skipping count change ({int(cooldown_left)}s remaining)")
        return
    
    # Check if URL is in cooldown
    if is_in_cooldown(url_id):
        print(f"URL {url_id}: In cooldown, skipping count change")
        return
    
    # Update statistics for count change
    with URL_STATUS_LOCK:
        URL_STATISTICS[url_id]['changes_count'] += 1
        
        # Calculate difference and add to total (capped at max_skins_to_buy_limit)
        difference = new_count - old_count
        max_limit = VERIFICATION_SETTINGS['max_skins_to_buy_limit']
        capped_difference = min(difference, max_limit)
        URL_STATISTICS[url_id]['total_difference'] += capped_difference
    
    with TASK_LOCK:
        # Record last change
        change_time = time.strftime('%H:%M:%S')
        with URL_STATUS_LOCK:
            URL_STATUS[url_id]['last_change'] = f"{old_count}→{new_count} at {change_time}"
        
        # Create a unique task ID for this verification attempt
        task_id = f"{url_id}_{time.time()}_{new_count}"
        
        # Calculate count difference for sniper settings
        count_difference = new_count - old_count
        
        # Create and start new task
        task = SniperTask(
            url_id=url_id,
            url=MARKET_URLS[url_id],
            expected_count=new_count,
            count_difference=count_difference,
            task_id=task_id
        )
        ACTIVE_TASKS[task_id] = task
        task.start()
        print(f"URL {url_id}: Started new sniper for count {new_count} (difference: {count_difference})")

# ===== STATUS DISPLAY ===== #
def display_status():
    """Display consolidated status for all URLs"""
    global VERIFICATION_PAUSED
    
    os.system('cls' if os.name == 'nt' else 'clear')
    print("STEAM MARKET MULTI-URL MONITOR WITH SNIPER")
    print("=" * 80)
    print(f"Ctrl+D to {'Resume' if VERIFICATION_PAUSED else 'Pause'} | Ctrl+C to exit")
    print("=" * 80)
    
    # Create thread-safe copies of the status
    with URL_STATUS_LOCK:
        status_copy = copy.deepcopy(URL_STATUS)
        verification_status_copy = copy.deepcopy(URL_VERIFICATION_STATUS)
        sniper_status_copy = copy.deepcopy(URL_SNIPER_STATUS)
        sniper_config_copy = copy.deepcopy(URL_SNIPER_CONFIG)
        statistics_copy = copy.deepcopy(URL_STATISTICS)
        cooldown_copy = copy.deepcopy(URL_COOLDOWN)
        float_config_copy = copy.deepcopy(URL_FLOAT_CONFIG)
    
    # Check 429 cooldown status
    in_429_cooldown = is_in_429_cooldown()
    cooldown_remaining = get_429_cooldown_remaining() if in_429_cooldown else 0
    
    # Print 429 status if active
    if in_429_cooldown:
        print(f"!!! 429 COOLDOWN ACTIVE: {int(cooldown_remaining)}s REMAINING !!!")
        print("=" * 80)
    
    # Print URL headers
    url_line = "URLs: "
    for url_id, url in MARKET_URLS.items():
        short_url = url.split('/')[-1].replace('%20', ' ').replace('★', '★')
        url_line += f"{url_id}: {short_url} | "
    
    print(url_line)
    
    # Per-URL Float Configuration
    print("\nPER-URL FLOAT CONFIGURATION")
    print("=" * 80)
    for url_id in MARKET_URLS:
        float_config = float_config_copy[url_id]
        direction = 'Low Float (≤ threshold)' if float_config['float_direction'] == 0 else 'High Float (≥ threshold)'
        print(f"URL {url_id}: {direction}")
        print(f"  Price → Float Table:")
        for price, float_val in sorted(float_config['price_float_table'].items()):
            print(f"    €{price:.2f} → Float {float_val:.3f}")
        print("-" * 40)
    print("=" * 80)
    
    # Monitoring status table
    print("\nMONITORING STATUS")
    print("=" * 80)
    print(f"{'ID':<3} {'Requests':<8} {'Current':<8} {'NameID':<12} {'Last Change':<25} {'Last Activity':<30}")
    print("-" * 80)
    
    for url_id in MARKET_URLS:
        status = status_copy[url_id]
        cooldown_info = cooldown_copy[url_id]
        
        # Check if in cooldown
        cooldown_status = ""
        if time.time() < cooldown_info['cooldown_until']:
            remaining = int(cooldown_info['cooldown_until'] - time.time())
            cooldown_status = f" [COOLDOWN: {remaining}s]"
        
        print(f"{url_id:<3} {status['request_count']:<8} {status['current_count']:<8} "
              f"{status['item_nameid'][:12]:<12} {status['last_change'][:25]:<25} {status['last_activity'][:30]}{cooldown_status}")
    
    # Verification status table
    print("\nVERIFICATION STATUS")
    print("=" * 80)
    print(f"{'ID':<3} {'Expected':<8} {'Actual':<12} {'Profile':<8} {'Retry Left':<10} {'Status':<30}")
    print("-" * 80)
    
    for url_id in MARKET_URLS:
        v_status = verification_status_copy[url_id]
        print(f"{url_id:<3} {v_status['expected_count']:<8} {v_status['actual_count']:<12} "
              f"{v_status['profile_used']:<8} {v_status['retry_left']:<10} "
              f"{v_status['status'][:30]:<30}")
    
    # Sniper config table
    print("\nSNIPER CONFIGURATION")
    print("=" * 80)
    print(f"{'ID':<3} {'Pattern':<8} {'Target':<6} {'AutoBuy':<7} {'Pages':<6} {'CloseDelay':<11} {'Reload':<6}")
    print("-" * 80)
    
    for url_id in MARKET_URLS:
        s_config = sniper_config_copy[url_id]
        pattern_check = 'Y' if s_config['check_pattern'] == 1 else 'N'
        auto_buy = 'Y' if s_config['auto_purchase'] else 'N'
        reload_btn = 'Y' if s_config.get('click_reload_button', 0) == 1 else 'N'
        close_delay = f"{s_config['sniping_window_close_delay'][0]}-{s_config['sniping_window_close_delay'][1]}s"
        print(f"{url_id:<3} {pattern_check:<8} {s_config['target_pattern']:<6} {auto_buy:<7} "
              f"{s_config['pages_to_check']:<6} {close_delay:<11} {reload_btn:<6}")
    
    # Sniper status table
    print("\nSNIPER STATUS")
    print("=" * 80)
    print(f"{'ID':<3} {'Remain':<6} {'Bought':<6} {'Pages':<6} {'LowFloat':<8} {'HighPrice':<9} {'Status':<12}")
    print("-" * 80)
    
    for url_id in MARKET_URLS:
        s_status = sniper_status_copy[url_id]
        low_float = f"{s_status['lowest_float']:.6f}" if s_status['lowest_float'] is not None else "N/A"
        high_price = f"{s_status['highest_price']:.2f}€" if s_status['highest_price'] > 0 else "N/A"
        print(f"{url_id:<3} {s_status['skins_remaining']:<6} {s_status['skins_bought']:<6} "
              f"{s_status['pages_remaining']:<6} {low_float:<8} {high_price:<9} {s_status['status'][:12]:<12}")
    
    # Statistics table
    print("\nSTATISTICS")
    print("=" * 80)
    print(f"{'ID':<3} {'Changes':<8} {'Matches':<8} {'Total Diff':<10} {'Good Skins':<10}")
    print("-" * 80)
    
    for url_id in MARKET_URLS:
        stats = statistics_copy[url_id]
        print(f"{url_id:<3} {stats['changes_count']:<8} {stats['matches_count']:<8} "
              f"{stats['total_difference']:<10} {stats['good_skins_found']:<10}")
    
    # Extracted data table
    print("\nEXTRACTED DATA (Last Page)")
    print("=" * 80)
    for url_id in MARKET_URLS:
        s_status = sniper_status_copy[url_id]
        if s_status['extracted_data']:
            print(f"\nURL {url_id} (Page {s_status['current_page']}):")
            print("-" * 40)
            for i, data in enumerate(s_status['extracted_data'], 1):
                print(f"  {i}: Price: {data['price']}, Float: {data['float_value']}, Seed: {data['paint_seed']}")
    
    # Active tasks status
    print("\nACTIVE TASKS")
    print("=" * 80)
    with TASK_LOCK:
        if ACTIVE_TASKS:
            for task_id, task in ACTIVE_TASKS.items():
                url_id = task_id.split('_')[0]
                print(f"URL {url_id}: {task.status}")
        else:
            print("No active tasks")
    
    # Pause status
    print("\n" + "=" * 80)
    if VERIFICATION_PAUSED:
        print("!!! VERIFICATIONS PAUSED - PRESS CTRL+D TO RESUME !!!")

# ===== MAIN FUNCTION ===== #
def main():
    global PROFILE_MANAGER
    
    print("Extracting item_nameid values from Steam market pages...")
    
    # Extract all item_nameids using parallel processing
    item_nameids = extract_all_item_nameids_parallel()
    
    if not item_nameids:
        print("No item_nameid values extracted. Exiting.")
        return
    
    print("\nStarting API-based monitoring...")
    print("Press Ctrl+C to stop.\n")
    
    # Create and start a thread for each item
    monitor_threads = []
    for url_id, url in MARKET_URLS.items():
        if url in item_nameids:
            item_nameid = item_nameids[url]
            thread = threading.Thread(
                target=monitor_item, 
                args=(item_nameid, url, url_id),
                daemon=True
            )
            monitor_threads.append(thread)
            thread.start()
            print(f"Started monitoring for URL {url_id} (ItemNameID: {item_nameid})")
        else:
            print(f"Failed to get item_nameid for URL {url_id}, skipping monitoring")
    
    # Start status update thread
    status_running = True
    def status_updater():
        while status_running:
            display_status()
            time.sleep(1)
    
    status_thread = threading.Thread(target=status_updater)
    status_thread.daemon = True
    status_thread.start()
    
    # Main loop
    try:
        while True:
            # Check for hotkey
            if check_hotkey():
                with PAUSE_LOCK:
                    pause_state = "PAUSED" if VERIFICATION_PAUSED else "RESUMED"
                print(f"\nVerification process {pause_state}")
            
            time.sleep(0.5)
            
    except KeyboardInterrupt:
        print("\nMonitoring stopped by user")
    except Exception as e:
        print(f"\nError occurred: {str(e)}")
    finally:
        status_running = False
        status_thread.join()
        
        with TASK_LOCK:
            for task in ACTIVE_TASKS.values():
                task.stop_event.set()
            time.sleep(1)
        
        print("\nMonitoring stopped")

if __name__ == "__main__":
    main()