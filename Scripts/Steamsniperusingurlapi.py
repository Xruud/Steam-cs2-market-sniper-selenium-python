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

# ===== URL CONFIGURATION ===== #
MARKET_URLS = OrderedDict([
    (1, "https://steamcommunity.com/market/listings/730/Nova%20%7C%20Yorkshire%20%28Minimal%20Wear%29"),
    (2, "https://steamcommunity.com/market/listings/730/FAMAS%20%7C%20Half%20Sleeve%20%28Minimal%20Wear%29"),
    (3, "https://steamcommunity.com/market/listings/730/MP5-SD%20%7C%20Savannah%20Halftone%20%28Field-Tested%29"),
    (4, "https://steamcommunity.com/market/listings/730/Negev%20%7C%20Sour%20Grapes%20%28Minimal%20Wear%29")
])

# Sniper settings for each URL (now with per-URL float settings)
URL_SNIPER_CONFIG = {
    1: {
        'check_pattern': 0, 
        'target_pattern': 699,
        'auto_purchase': True,
        'pages_to_check': 1,
        'sniping_window_close_delay': (3, 5), #in seconds
        'click_reload_button': 0,
        'float_direction': 0,  # 0 for low float, 1 for high float
        'price_float_table': {
            1.15: 0.1025,
            1.3: 0.1
        } # price on the left, float on the right, if float is under 0.1 and price is under 1,3 it can buy in this example, when float_direction is set to 0
    },
    2: {
        'check_pattern': 0,
        'target_pattern': 699,
        'auto_purchase': True,
        'pages_to_check': 12,
        'sniping_window_close_delay': (3, 5),
        'click_reload_button': 0,
        'float_direction': 0,  # 0 for low float, 1 for high float
        'price_float_table': {
            0.17: 0.1025,
            0.2: 0.1
        }
    },
    3: {
        'check_pattern': 0,
        'target_pattern': 699,
        'auto_purchase': True,
        'pages_to_check': 25,
        'sniping_window_close_delay': (3, 5),
        'click_reload_button': 0,
        'float_direction': 0,  # 0 for low float, 1 for high float
        'price_float_table': {
            0.16: 0.30125,
            0.2: 0.3
        }
    },
    4: {
        'check_pattern': 0,
        'target_pattern': 699,
        'auto_purchase': True,
        'pages_to_check': 1,
        'sniping_window_close_delay': (3, 5),
        'click_reload_button': 0,
        'float_direction': 0,  # 0 for low float, 1 for high float
        'price_float_table': {
            0.23: 0.09333,
            0.26: 0.0865,
            0.3: 0.08
        }
    }
}

# Timing settings (all in seconds)
TIMING_SETTINGS = {
    'monitoring_js_delay': (3, 5), # in seconds
    'verification_start_delay': 0, # in seconds
    'tab_switch_interval': (1, 2), # in seconds
    'page_nav_delay_min': 0, # in milliseconds
    'page_nav_delay_max': 51, # in milliseconds
    'wait_after_sort_min': 0, # in milliseconds
    'wait_after_sort_max': 50, # in milliseconds
    'verification_retry_delay': (15, 20), # in seconds
    'verification_mismatch_close': (3, 5), # in seconds
    'sort_button_press_delay': (0, 0.05), # in seconds
    'sniper_timeout': 30, # in seconds
    'reload_button_wait': 0.01, # in seconds
    '429_check_interval': 1, # in seconds
    'global_cooldown_min': 300, # in seconds
    'global_cooldown_max': 350 # in seconds
}

# Verification system settings
VERIFICATION_SETTINGS = {
    'initial_attempts': 1,
    'retry_increment': 1,
    'max_attempts': 12,
    'max_count_diff': 5,
    'max_skins_to_buy_limit': 5
}

# Cooldown settings
COOLDOWN_SETTINGS = {
    'change_threshold': 120, # in seconds
    'time_window': 120, # in seconds
    'cooldown_period': 120 # in seconds
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

# Status tracking
URL_STATUS = {}
for url_id in MARKET_URLS:
    URL_STATUS[url_id] = {
        'request_count': 0,
        'current_count': "N/A",
        'last_change': "N/A",
        'last_activity': "",
        'monitoring_injected': False
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
        'extracted_data': [],
        'current_max_price': 0,
        'current_float_threshold': 0
    }

# Statistics tracking
URL_STATISTICS = {}
for url_id in MARKET_URLS:
    URL_STATISTICS[url_id] = {
        'changes_count': 0,
        'matches_count': 0,
        'total_difference': 0,
        'good_skins_found': 0
    }

# Cooldown tracking
URL_COOLDOWN_STATUS = {}
for url_id in MARKET_URLS:
    URL_COOLDOWN_STATUS[url_id] = {
        'change_history': [],
        'cooldown_until': 0,
        'total_changes': 0
    }

# Global profile tracking per URL (persistent across verifications)
URL_PROFILE_INDEX = {}
for url_id in MARKET_URLS:
    URL_PROFILE_INDEX[url_id] = random.randint(0, len(PROFILE_PATHS)-1)

# Global 429 error tracking
GLOBAL_429_STATUS = {
    'cooldown_until': 0,
    'last_detected': 0,
    'detection_count': 0,
    'status': 'Active'
}
GLOBAL_429_LOCK = threading.Lock()

# Lock for thread-safe status updates
URL_STATUS_LOCK = threading.Lock()

# Lock for cooldown status updates
COOLDOWN_LOCK = threading.Lock()

# Global task tracking
ACTIVE_TASKS = {}
TASK_LOCK = threading.Lock()

# Hotkey control
VERIFICATION_PAUSED = False
PAUSE_LOCK = threading.Lock()

# ===== FLOAT UTILITY FUNCTIONS ===== #
def get_float_threshold_for_price(price, price_float_table):
    """Get the appropriate float threshold for a given price using the price-float table"""
    # Sort prices in descending order to find the highest price threshold that applies
    sorted_prices = sorted(price_float_table.keys(), reverse=True)
    
    for threshold_price in sorted_prices:
        if price <= threshold_price:
            return price_float_table[threshold_price]
    
    # If price is lower than all thresholds, use the lowest threshold price's float value
    if sorted_prices:
        return price_float_table[min(price_float_table.keys())]
    
    # Fallback
    return 0.1

def get_max_price_for_skin(price_float_table):
    """Get the maximum price to consider based on the price-float table"""
    return max(price_float_table.keys())

# ===== 429 ERROR DETECTION FUNCTIONS ===== #
def check_429_error(driver):
    """Check if the page contains a 429 Too Many Requests error"""
    try:
        error_elements = driver.find_elements(By.XPATH, "//span[contains(@class, 'sih_label_warning') and contains(text(), 'Steam error: 429')]")
        if error_elements:
            return True
            
        page_text = driver.page_source
        if "429 Too Many Requests" in page_text or "Too Many Requests" in page_text:
            return True
            
        if "Steam error: 429" in page_text:
            return True
            
    except Exception as e:
        pass
        
    return False

def update_global_429_status(detected=False):
    """Update the global 429 status and trigger cooldown if detected"""
    global GLOBAL_429_STATUS
    
    with GLOBAL_429_LOCK:
        current_time = time.time()
        
        if detected:
            cooldown_duration = random.randint(
                TIMING_SETTINGS['global_cooldown_min'], 
                TIMING_SETTINGS['global_cooldown_max']
            )
            
            GLOBAL_429_STATUS['cooldown_until'] = current_time + cooldown_duration
            GLOBAL_429_STATUS['last_detected'] = current_time
            GLOBAL_429_STATUS['detection_count'] += 1
            GLOBAL_429_STATUS['status'] = f'Cooldown until {time.strftime("%H:%M:%S", time.localtime(current_time + cooldown_duration))}'
            
            print(f"\n!!! 429 ERROR DETECTED - GLOBAL COOLDOWN ACTIVATED FOR {cooldown_duration} SECONDS !!!")
            
            with TASK_LOCK:
                for task_id, task in list(ACTIVE_TASKS.items()):
                    if hasattr(task, 'stop_event'):
                        task.stop_event.set()
                        print(f"Stopping task {task_id} due to 429 error")
            
            return True
        else:
            if current_time >= GLOBAL_429_STATUS['cooldown_until']:
                if GLOBAL_429_STATUS['status'] != 'Active':
                    print("Global 429 cooldown expired, resuming normal operations")
                GLOBAL_429_STATUS['status'] = 'Active'
                return False
            else:
                time_left = GLOBAL_429_STATUS['cooldown_until'] - current_time
                GLOBAL_429_STATUS['status'] = f'Cooldown - {int(time_left)}s left'
                return True

def is_global_cooldown_active():
    """Check if global cooldown due to 429 error is active"""
    with GLOBAL_429_LOCK:
        current_time = time.time()
        if current_time < GLOBAL_429_STATUS['cooldown_until']:
            return True, GLOBAL_429_STATUS['cooldown_until'] - current_time
        return False, 0

def start_429_monitor(driver, stop_event, check_interval=1):
    """Monitor for 429 errors in a separate thread"""
    def monitor():
        while not stop_event.is_set():
            try:
                if check_429_error(driver):
                    update_global_429_status(detected=True)
                    stop_event.set()
                    break
                time.sleep(check_interval)
            except Exception as e:
                time.sleep(check_interval)
    
    monitor_thread = threading.Thread(target=monitor)
    monitor_thread.daemon = True
    monitor_thread.start()
    return monitor_thread

# ===== COOLDOWN FUNCTIONS ===== #
def update_cooldown_status(url_id, change_amount):
    """Update cooldown status for a URL and check if cooldown should be triggered"""
    with COOLDOWN_LOCK:
        current_time = time.time()
        cooldown_status = URL_COOLDOWN_STATUS[url_id]
        
        cooldown_status['change_history'] = [
            (ts, amount) for ts, amount in cooldown_status['change_history'] 
            if current_time - ts <= COOLDOWN_SETTINGS['time_window']
        ]
        
        cooldown_status['change_history'].append((current_time, change_amount))
        
        total_changes = sum(amount for ts, amount in cooldown_status['change_history'])
        cooldown_status['total_changes'] = total_changes
        
        if total_changes >= COOLDOWN_SETTINGS['change_threshold']:
            cooldown_status['cooldown_until'] = current_time + COOLDOWN_SETTINGS['cooldown_period']
            print(f"URL {url_id}: Cooldown triggered! {total_changes} changes in {COOLDOWN_SETTINGS['time_window']}s")
            return True
        
        return False

def is_url_in_cooldown(url_id):
    """Check if a URL is currently in cooldown"""
    with COOLDOWN_LOCK:
        cooldown_status = URL_COOLDOWN_STATUS[url_id]
        current_time = time.time()
        
        if cooldown_status['cooldown_until'] > current_time:
            time_left = cooldown_status['cooldown_until'] - current_time
            return True, time_left
        
        if cooldown_status['cooldown_until'] > 0 and cooldown_status['cooldown_until'] <= current_time:
            cooldown_status['cooldown_until'] = 0
            cooldown_status['change_history'] = []
            cooldown_status['total_changes'] = 0
            print(f"URL {url_id}: Cooldown expired")
        
        return False, 0

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

# ===== JAVASCRIPT CODE ===== #
def get_monitor_js(url_id):
    return f"""
// == Steam Market Sell Order Monitor ==
// Unique ID: {url_id}

// Configuration
const TARGET_ENDPOINT = 'itemordershistogram';
const MONITOR_COLOR = '#1a2a6c';
const ALERT_COLOR = '#b21f1f';

// Create console logging functions for Python
window.pythonRequest = function(count) {{
    console.log("STEAM_REQUEST_{url_id}:" + count);
}};

window.pythonAlert = function(oldCount, newCount) {{
    console.log("STEAM_ALERT_{url_id}:" + oldCount + "→" + newCount);
}};

// State management
let lastSellCount = null;
let isMonitoring = true;
let requestCount = 0;

// Extract sell count from JSON response
function extractSellCount(data) {{
    try {{
        const summary = data.sell_order_summary || '';
        
        let match = summary.match(/<span class="market_commodity_orders_header_promote">(\\d+)<\\/span>/);
        if (match) return parseInt(match[1]);
        
        match = summary.match(/sell order\\(s\\)\\)<[^>]+>(\\d+)</);
        if (match) return parseInt(match[1]);
        
        match = summary.match(/(\\d+(?:,\\\\d+)?) sell orders?/i);
        if (match) return parseInt(match[1].replace(',', ''));
        
        console.warn('Could not find sell count in summary:', summary);
        return null;
    }} catch(e) {{
        console.error('Extract error:', e);
        return null;
    }}
}}

// Play alert sound
function playAlert() {{
    try {{
        const audio = new Audio('https://assets.mixkit.co/sfx/preview/mixkit-alert-quick-chime-766.mp3');
        audio.play().catch(e => console.log('Audio error:', e));
    }} catch(e) {{
        console.log('Audio error:', e);
    }}
}}

// Create visual alert
function createVisualAlert(oldCount, newCount) {{
    try {{
        const existing = document.getElementById('steam-monitor-alert');
        if (existing) existing.remove();
        
        const alertBox = document.createElement('div');
        alertBox.id = 'steam-monitor-alert';
        alertBox.style = `position: fixed;
            top: 20px;
            left: 50%;
            transform: translateX(-50%);
            background: ${{ALERT_COLOR}};
            color: white;
            padding: 15px 30px;
            border-radius: 5px;
            z-index: 10000;
            font-weight: bold;
            font-size: 1.2rem;
            box-shadow: 0 4px 15px rgba(0,0,0,0.3);
            text-align: center;`;
        alertBox.innerHTML = `<div>🔄 SELL ORDERS CHANGED!</div>
            <div style="font-size: 2rem; margin: 10px 0">${{oldCount}} → ${{newCount}}</div>`;
        document.body.appendChild(alertBox);
        
        setTimeout(() => {{
            if (alertBox.parentNode) alertBox.remove();
        }}, 5000);
    }} catch(e) {{
        console.error('Alert creation error:', e);
    }}
}}

// Process new sell count
function processNewCount(count) {{
    window.pythonRequest(count);
    
    if (lastSellCount === null) {{
        lastSellCount = count;
        console.log(`%c[Initial] Sell count set: ${{count}}`, `color: ${{MONITOR_COLOR}}; font-weight: bold`);
        return;
    }}

    if (count > lastSellCount) {{
        console.log(`%c[CHANGE] Detected! ${{lastSellCount}} → ${{count}}`, `background: ${{ALERT_COLOR}}; color: white; padding: 5px; font-size: 16px; font-weight: bold`);
        playAlert();
        createVisualAlert(lastSellCount, count);
        
        window.pythonAlert(lastSellCount, count);
    }}
    lastSellCount = count;
}}

// Setup monitoring
function setupMonitoring() {{
    const originalOpen = XMLHttpRequest.prototype.open;
    XMLHttpRequest.prototype.open = function(method, url) {{
        this._url = url;
        return originalOpen.apply(this, arguments);
    }};

    const originalSend = XMLHttpRequest.prototype.send;
    XMLHttpRequest.prototype.send = function(body) {{
        if (this._url.includes(TARGET_ENDPOINT)) {{
            this.addEventListener('load', () => {{
                if (this.status === 200 && isMonitoring) {{
                    try {{
                        const data = JSON.parse(this.responseText);
                        const sellCount = extractSellCount(data);
                        if (sellCount !== null) {{
                            requestCount++;
                            console.log(`[Request #${{requestCount}}] Sell orders: ${{sellCount}}`);
                            processNewCount(sellCount);
                        }} else {{
                            console.warn('No sell count found in response');
                        }}
                    }} catch(e) {{
                        console.error('XHR processing error:', e);
                    }}
                }}
            }});
        }}
        return originalSend.apply(this, arguments);
    }};

    const originalFetch = window.fetch;
    window.fetch = function(input, init) {{
        const url = typeof input === 'string' ? input : input.url;
        if (url.includes(TARGET_ENDPOINT)) {{
            return originalFetch(input, init).then(response => {{
                if (response.ok && isMonitoring) {{
                    response.clone().json().then(data => {{
                        const sellCount = extractSellCount(data);
                        if (sellCount !== null) {{
                            requestCount++;
                            console.log(`[Request #${{requestCount}}] Sell orders: ${{sellCount}}`);
                            processNewCount(sellCount);
                        }} else {{
                            console.warn('No sell count found in fetch response');
                        }}
                    }}).catch(e => {{
                        console.error('Fetch processing error:', e);
                    }});
                }}
                return response;
    }});
        }}
        return originalFetch(input, init);
    }};

    console.log(`%cMonitoring started for URL {url_id}!`, 'color: #4CAF50; font-weight: bold');
}}

// Initialize
setupMonitoring();

// Control functions
window.steamMonitor = {{
    pause: () => {{
        isMonitoring = false;
        console.log('%cMonitoring PAUSED', 'color: #FF9800; font-weight: bold');
    }},
    resume: () => {{
        isMonitoring = true;
        console.log('%cMonitoring RESUMED', 'color: #4CAF50; font-weight: bold');
    }}
}};
"""

# ===== SNIPER FUNCTIONS ===== #
def get_random_delay(min_ms, max_ms):
    """Generate a random delay in seconds within specified range"""
    return random.uniform(min_ms, max_ms) / 1000.0

def verify_total_listings(driver, expected_count):
    """Verify the number of listings matches expected value"""
    try:
        total_element = WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.ID, "searchResults_total"))
        )
        
        total_text = total_element.text
        total_number = int(total_text.replace(',', ''))
        expected_int = int(expected_count)
        
        return total_number >= expected_int, total_number
    except Exception as e:
        print(f"Error verifying total listings: {str(e)}")
        return False, 0

def get_sort_button(driver):
    """Retrieves the sort button element through shadow DOM"""
    try:
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

def check_skin_match(driver, listing_data, index, listing_element, remaining_purchases, sniper_config, sniper_status):
    """
    Checks if a skin matches the specified criteria using per-URL float config
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
    
    # Get float threshold based on price using per-URL config
    price_float_table = sniper_config['price_float_table']
    float_threshold = get_float_threshold_for_price(price_value, price_float_table)
    max_price = get_max_price_for_skin(price_float_table)
    
    # Update current max price and float threshold in status
    sniper_status['current_max_price'] = max_price
    sniper_status['current_float_threshold'] = float_threshold
    
    # Check float based on per-URL direction
    if sniper_config['float_direction'] == 0:  # Low float
        float_match = float_value <= float_threshold
        float_info = f"Float: {listing_data['float_value']} {'✓' if float_match else '✗'} (Max: {float_threshold:.3f})"
    else:  # High float
        float_match = float_value >= float_threshold
        float_info = f"Float: {listing_data['float_value']} {'✓' if float_match else '✗'} (Min: {float_threshold:.3f})"
    
    # Check other criteria
    price_match = price_value <= max_price
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
        print(f"Price: {listing_data['price']} (<= {max_price:.2f}€)")
        if sniper_config['float_direction'] == 0:
            print(f"Float Value: {listing_data['float_value']} (<= {float_threshold:.3f})")
        else:
            print(f"Float Value: {listing_data['float_value']} (>= {float_threshold:.3f})")
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
    print(f"  Price: {listing_data['price']} {'✓' if price_match else '✗'} (Max: {max_price:.2f}€)")
    print(f"  {float_info}")
    if sniper_config['check_pattern'] == 1:
        print(f"  Pattern: {listing_data['paint_seed']} {'✓' if pattern_match else '✗'} (Target: {sniper_config['target_pattern']})")
    
    return False, False, remaining_purchases

def process_current_page(driver, number_of_skins, remaining_purchases, sniper_config, sniper_status):
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
                driver, listing_data, i, listing, remaining_purchases, sniper_config, sniper_status
            )
            
            if is_match:
                matches_found += 1
            if purchase_attempted:
                purchases_made += 1
                
            # Check if price exceeds max price (stopping condition)
            try:
                price_str = listing_data["price"].replace('€', '').replace(',', '.')
                price_value = float(price_str)
                max_price = get_max_price_for_skin(sniper_config['price_float_table'])
                if price_value > max_price:
                    print(f"Price {price_value} exceeds max price {max_price}, stopping after this page")
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
                    driver, listing_data, i, listing, remaining_purchases, sniper_config, sniper_status
                )
                if is_match:
                    matches_found += 1
                if purchase_attempted:
                    purchases_made += 1
                    
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

def click_reload_listings_button(driver):
    """Clicks the 'Reload listings' button if it exists"""
    try:
        reload_button = WebDriverWait(driver, TIMING_SETTINGS['reload_button_wait']).until(
            EC.presence_of_element_located((By.XPATH, "//a[contains(@class, 'btn_grey_white_innerfade') and contains(., 'Reload listings')]"))
        )
        
        if is_button_clickable(reload_button):
            print("Clicking 'Reload listings' button...")
            driver.execute_script("arguments[0].click();", reload_button)
            
            time.sleep(1)
            
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.ID, "searchResultsRows"))
            )
            print("Listings reloaded successfully")
            return True
        else:
            print("Reload button is not clickable")
            return False
    except TimeoutException:
        print("Reload button not found within timeout")
        return False
    except Exception as e:
        print(f"Error clicking reload button: {str(e)}")
        return False

# ===== SNIPER TASK ===== #
class SniperTask(threading.Thread):
    def __init__(self, url_id, url, expected_count, count_difference, task_id):
        super().__init__()
        self.url_id = url_id
        self.url = url
        self.expected_count = expected_count
        self.count_difference = count_difference
        self.task_id = task_id
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
        self.good_skins_found = 0
        self._429_monitor_thread = None
        
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
            URL_SNIPER_STATUS[self.url_id]['current_max_price'] = get_max_price_for_skin(self.sniper_config['price_float_table'])
            URL_SNIPER_STATUS[self.url_id]['current_float_threshold'] = 0
        
    def run(self):
        try:
            # Check for global 429 cooldown before starting
            global_cooldown_active, time_left = is_global_cooldown_active()
            if global_cooldown_active:
                self.status = f"Global cooldown active ({int(time_left)}s left), aborting"
                with URL_STATUS_LOCK:
                    URL_VERIFICATION_STATUS[self.url_id]['status'] = f"Global cooldown: {int(time_left)}s"
                return
            
            # ADDED VERIFICATION DELAY
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
                
                # Check for global 429 cooldown before each attempt
                global_cooldown_active, time_left = is_global_cooldown_active()
                if global_cooldown_active:
                    self.status = f"Global cooldown active ({int(time_left)}s left), aborting attempt"
                    with URL_STATUS_LOCK:
                        URL_VERIFICATION_STATUS[self.url_id]['status'] = f"Global cooldown: {int(time_left)}s"
                    break
                
                # Update status
                with URL_STATUS_LOCK:
                    URL_VERIFICATION_STATUS[self.url_id]['attempts'] = current_retry
                    URL_VERIFICATION_STATUS[self.url_id]['retry_left'] = VERIFICATION_SETTINGS['initial_attempts'] - current_retry
                    URL_VERIFICATION_STATUS[self.url_id]['status'] = f"Attempt {current_retry}/{VERIFICATION_SETTINGS['initial_attempts']}"
                
                # Open browser with next profile
                self.open_browser()
                
                # Start 429 error monitoring thread
                if self.driver:
                    self._429_monitor_thread = start_429_monitor(
                        self.driver, 
                        self.stop_event, 
                        TIMING_SETTINGS['429_check_interval']
                    )
                
                # Perform verification
                result = self.run_sniper()
                
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
                    # 429 error detected, global cooldown already activated
                    print("Sniper stopped due to 429 error")
                    break
                
                # Wait before retry if needed
                if not self.stop_event.is_set() and current_retry < VERIFICATION_SETTINGS['initial_attempts']:
                    # Check for global cooldown again before retry
                    global_cooldown_active, time_left = is_global_cooldown_active()
                    if global_cooldown_active:
                        self.status = f"Global cooldown active ({int(time_left)}s left), aborting retry"
                        break
                    
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
        """Run the sniper script logic with 429 error checking"""
        try:
            # STEP 1: Check for 429 error immediately after page loads
            print("Checking for 429 error after page load...")
            if check_429_error(self.driver):
                print("!!! 429 ERROR DETECTED ON PAGE LOAD - ABORTING SNIPER !!!")
                update_global_429_status(detected=True)
                return "429_error"
            
            # STEP 2: Verify total listings
            verification_passed, actual_count = verify_total_listings(self.driver, self.expected_count)
            
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
            
            # STEP 3: Check for 429 error again before reload button
            print("Checking for 429 error before reload button...")
            if check_429_error(self.driver):
                print("!!! 429 ERROR DETECTED BEFORE RELOAD - ABORTING SNIPER !!!")
                update_global_429_status(detected=True)
                return "429_error"
            
            # STEP 4: Click reload button if configured to do so
            if self.sniper_config.get('click_reload_button', 0) == 1:
                self.status = "Clicking reload button..."
                with URL_STATUS_LOCK:
                    URL_VERIFICATION_STATUS[self.url_id]['status'] = "Clicking reload button"
                
                if not click_reload_listings_button(self.driver):
                    print("Failed to click reload button, continuing anyway")
            
            # STEP 5: Check for 429 error after reload button
            print("Checking for 429 error after reload button...")
            if check_429_error(self.driver):
                print("!!! 429 ERROR DETECTED AFTER RELOAD - ABORTING SNIPER !!!")
                update_global_429_status(detected=True)
                return "429_error"
            
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
            
            # Process each page
            for page in range(1, self.sniper_config['pages_to_check'] + 1):
                # Check for 429 error before processing each page
                if check_429_error(self.driver):
                    print("!!! 429 ERROR DETECTED DURING PAGE PROCESSING - ABORTING SNIPER !!!")
                    update_global_429_status(detected=True)
                    return "429_error"
                
                # Check if stop event is set (could be from 429 monitor thread)
                if self.stop_event.is_set():
                    print("Stop event set (likely from 429 monitor), aborting sniper")
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
                    clicks = 2 if self.sniper_config['float_direction'] == 1 else 1
                    print(f"Sorting listings (clicking {clicks} times)...")
                    if not perform_sorting(self.driver, clicks, self.sniper_config['float_direction']):
                        print("Failed to sort listings, skipping page")
                        continue
                else:
                    # For pages after the first, press sort button 3 times with delays
                    print("Pressing sort button 3 times with delays...")
                    delay_between_clicks = random.uniform(*TIMING_SETTINGS['sort_button_press_delay'])
                    if not perform_sorting(self.driver, 3, self.sniper_config['float_direction'], delay_between_clicks):
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
                    self.driver, self.number_of_skins, remaining_purchases, self.sniper_config, URL_SNIPER_STATUS[self.url_id]
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
    
    # Check if global 429 cooldown is active
    global_cooldown_active, time_left = is_global_cooldown_active()
    if global_cooldown_active:
        print(f"Global 429 cooldown active ({int(time_left)}s left), skipping count change")
        return
    
    # Check if verification is paused
    with PAUSE_LOCK:
        if VERIFICATION_PAUSED:
            print(f"URL {url_id}: Verification paused, skipping change")
            return
    
    # Check if URL is in cooldown
    in_cooldown, time_left = is_url_in_cooldown(url_id)
    if in_cooldown:
        print(f"URL {url_id}: In cooldown ({time_left:.0f}s left), skipping change")
        return
    
    # Update statistics for count change
    with URL_STATUS_LOCK:
        URL_STATISTICS[url_id]['changes_count'] += 1
        
        # Calculate difference and add to total (capped at max_skins_to_buy_limit)
        difference = new_count - old_count
        max_limit = VERIFICATION_SETTINGS['max_skins_to_buy_limit']
        capped_difference = min(difference, max_limit)
        URL_STATISTICS[url_id]['total_difference'] += capped_difference
    
    # Update cooldown status and check if cooldown should be triggered
    change_amount = abs(new_count - old_count)
    cooldown_triggered = update_cooldown_status(url_id, change_amount)
    
    if cooldown_triggered:
        print(f"URL {url_id}: Cooldown activated due to rapid count changes")
        return
    
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
    
    # Get cooldown status
    cooldown_status = {}
    for url_id in MARKET_URLS:
        in_cooldown, time_left = is_url_in_cooldown(url_id)
        cooldown_status[url_id] = {
            'in_cooldown': in_cooldown,
            'time_left': time_left,
            'total_changes': URL_COOLDOWN_STATUS[url_id]['total_changes']
        }
    
    # Get global 429 status
    global_cooldown_active, global_time_left = is_global_cooldown_active()
    global_429_status = GLOBAL_429_STATUS['status']
    
    # Print URL headers
    url_line = "URLs: "
    for url_id, url in MARKET_URLS.items():
        short_url = url.split('/')[-1].replace('%20', ' ').replace('★', '★')
        url_line += f"{url_id}: {short_url} | "
    
    print(url_line)
    
    # Global 429 Status
    print("\nGLOBAL 429 STATUS")
    print("=" * 80)
    if global_cooldown_active:
        print(f"!!! GLOBAL COOLDOWN ACTIVE - {int(global_time_left)}s LEFT !!!")
    else:
        print("Status: Active")
    print(f"Last Status: {global_429_status}")
    print(f"Detection Count: {GLOBAL_429_STATUS['detection_count']}")
    
    # Monitoring status table
    print("\nMONITORING STATUS")
    print("=" * 80)
    print(f"{'ID':<3} {'Requests':<8} {'Current':<8} {'Last Change':<25} {'Last Activity':<30}")
    print("-" * 80)
    
    for url_id in MARKET_URLS:
        status = status_copy[url_id]
        print(f"{url_id:<3} {status['request_count']:<8} {status['current_count']:<8} "
              f"{status['last_change'][:25]:<25} {status['last_activity'][:30]:<30}")
    
    # Cooldown status table
    print("\nCOOLDOWN STATUS")
    print("=" * 80)
    print(f"{'ID':<3} {'Status':<12} {'Time Left':<10} {'Changes':<8}")
    print("-" * 80)
    
    for url_id in MARKET_URLS:
        status = cooldown_status[url_id]
        if status['in_cooldown']:
            status_str = "COOLDOWN"
            time_left = f"{status['time_left']:.0f}s"
        else:
            status_str = "ACTIVE"
            time_left = "N/A"
        print(f"{url_id:<3} {status_str:<12} {time_left:<10} {status['total_changes']:<8}")
    
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
    print(f"{'ID':<3} {'Pattern':<8} {'Target':<6} {'AutoBuy':<7} {'Pages':<6} {'Reload':<6} {'CloseDelay':<10} {'FloatDir':<10}")
    print("-" * 80)
    
    for url_id in MARKET_URLS:
        s_config = sniper_config_copy[url_id]
        pattern_check = 'Y' if s_config['check_pattern'] == 1 else 'N'
        auto_buy = 'Yes' if s_config['auto_purchase'] else 'No'
        reload_btn = 'Yes' if s_config.get('click_reload_button', 0) == 1 else 'No'
        close_delay = f"{s_config['sniping_window_close_delay'][0]}-{s_config['sniping_window_close_delay'][1]}s"
        float_dir = 'Low' if s_config['float_direction'] == 0 else 'High'
        print(f"{url_id:<3} {pattern_check:<8} {s_config['target_pattern']:<6} "
              f"{auto_buy:<7} {s_config['pages_to_check']:<6} {reload_btn:<6} {close_delay:<10} {float_dir:<10}")
    
    # Sniper status table
    print("\nSNIPER STATUS")
    print("=" * 80)
    print(f"{'ID':<3} {'Remain':<6} {'Bought':<6} {'Pages':<6} {'CurPrice':<8} {'CurFloat':<8} {'Status':<12}")
    print("-" * 80)
    
    for url_id in MARKET_URLS:
        s_status = sniper_status_copy[url_id]
        current_price = f"€{s_status['current_max_price']:.2f}" if s_status['current_max_price'] > 0 else "N/A"
        current_float = f"{s_status['current_float_threshold']:.3f}" if s_status['current_float_threshold'] > 0 else "N/A"
        print(f"{url_id:<3} {s_status['skins_remaining']:<6} {s_status['skins_bought']:<6} "
              f"{s_status['pages_remaining']:<6} {current_price:<8} {current_float:<8} {s_status['status'][:12]:<12}")
    
    # Price-Float Tables
    print("\nPRICE-FLOAT TABLES")
    print("=" * 80)
    for url_id in MARKET_URLS:
        s_config = sniper_config_copy[url_id]
        float_dir = 'Low Float (≤ threshold)' if s_config['float_direction'] == 0 else 'High Float (≥ threshold)'
        print(f"\nURL {url_id} - {float_dir}:")
        print("-" * 40)
        for price, float_threshold in sorted(s_config['price_float_table'].items()):
            print(f"  €{price:.2f} → Float {float_threshold:.3f}")
    
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
    if global_cooldown_active:
        print("!!! GLOBAL 429 COOLDOWN ACTIVE - ALL SNIPING SUSPENDED !!!")

# ===== TAB SWITCHING THREAD ===== #
def tab_switcher(driver, url_handles):
    """Separate thread for gentle tab switching"""
    while True:
        try:
            # Check for global cooldown before switching
            global_cooldown_active, _ = is_global_cooldown_active()
            if global_cooldown_active:
                time.sleep(5)  # Sleep longer during cooldown
                continue
                
            # Switch to a random tab
            url_id = random.choice(list(url_handles.keys()))
            driver.switch_to.window(url_handles[url_id])
            
            # Update activity status
            with URL_STATUS_LOCK:
                URL_STATUS[url_id]['last_activity'] = "Tab switched"
            
            # Wait before next switch
            switch_delay = random.randint(*TIMING_SETTINGS['tab_switch_interval'])
            time.sleep(switch_delay)
        except:
            time.sleep(1)

# ===== MAIN FUNCTION ===== #
def main():
    global PROFILE_MANAGER
    
    # Configure Chrome options for monitoring window with cache optimizations
    chrome_options = Options()
    chrome_options.add_argument("--window-size=1200,800")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_argument("--log-level=3")
    chrome_options.add_argument("--disable-logging")
    chrome_options.add_argument("--disable-dev-shm-usage")
    
    # Cache optimization settings for monitoring window
    chrome_options.add_argument("--disable-cache")
    chrome_options.add_argument("--disable-application-cache")
    chrome_options.add_argument("--disk-cache-size=0")
    chrome_options.add_argument("--media-cache-size=0")
    chrome_options.add_argument("--disable-gpu-shader-disk-cache")
    
    chrome_options.add_experimental_option("prefs", {
        "profile.exit_type": "Normal",
        "profile.exited_cleanly": True,
        "session.restore_on_startup": 0,
        "profile.default_content_setting_values.notifications": 2,
        "profile.managed_default_content_settings.images": 2,
        "disk-cache-size": 0,
        "media_cache_size": 0,
        "disable-cache": True
    })
    
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation", "enable-logging"])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    chrome_options.set_capability('goog:loggingPrefs', {'browser': 'ALL'})

    # Set up WebDriver for monitoring
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    
    # Create a mapping of window handles to URL IDs
    url_handles = {}
    
    # Navigate to all market pages in separate tabs
    print("Loading Steam market pages...")
    for url_id, url in MARKET_URLS.items():
        driver.execute_script(f"window.open('{url}', '_blank');")
        driver.switch_to.window(driver.window_handles[-1])
        url_handles[url_id] = driver.current_window_handle
        with URL_STATUS_LOCK:
            URL_STATUS[url_id]['last_activity'] = "Page loading..."
        time.sleep(0.5)
    
    # Switch back to first tab
    driver.switch_to.window(driver.window_handles[0])
    
    # Set injection times with different delays for each URL
    for url_id in MARKET_URLS:
        with URL_STATUS_LOCK:
            URL_STATUS[url_id]['monitoring_inject_time'] = time.time() + random.randint(*TIMING_SETTINGS['monitoring_js_delay'])
    
    # Start tab switcher thread
    tab_switch_thread = threading.Thread(target=tab_switcher, args=(driver, url_handles))
    tab_switch_thread.daemon = True
    tab_switch_thread.start()
    
    # Initial status display
    display_status()
    
    # Start status update thread
    status_running = True
    def status_updater():
        while status_running:
            display_status()
            time.sleep(1)
    
    status_thread = threading.Thread(target=status_updater)
    status_thread.daemon = True
    status_thread.start()
    
    # Monitoring loop
    try:
        last_injection_check = 0
        injection_check_interval = 5
        
        while True:
            current_time = time.time()
            
            # Check for hotkey
            if check_hotkey():
                with PAUSE_LOCK:
                    pause_state = "PAUSED" if VERIFICATION_PAUSED else "RESUMED"
                print(f"\nVerification process {pause_state}")
                display_status()
            
            # Process all browser logs
            try:
                logs = driver.get_log('browser')
            except Exception:
                logs = []
                
            for log in logs:
                message = log.get('message', '')
                
                # Process URL-specific messages
                for url_id in MARKET_URLS:
                    prefix = f"STEAM_REQUEST_{url_id}:"
                    if prefix in message:
                        try:
                            count_str = message.split(prefix)[1].strip().strip('"')
                            with URL_STATUS_LOCK:
                                URL_STATUS[url_id]['request_count'] += 1
                                URL_STATUS[url_id]['current_count'] = count_str
                        except Exception:
                            pass
                    
                    prefix = f"STEAM_ALERT_{url_id}:"
                    if prefix in message:
                        try:
                            alert_data = message.split(prefix)[1].strip().strip('"')
                            if '→' in alert_data:
                                old_count, new_count = alert_data.split('→', 1)
                                handle_count_change(url_id, int(old_count), int(new_count))
                        except Exception:
                            pass
            
            # Check for injections periodically
            if current_time - last_injection_check >= injection_check_interval:
                last_injection_check = current_time
                current_handle = driver.current_window_handle
                
                for url_id, handle in url_handles.items():
                    with URL_STATUS_LOCK:
                        status = URL_STATUS[url_id]
                    
                    if status['monitoring_injected']:
                        continue
                    
                    if not status['monitoring_injected'] and current_time > status['monitoring_inject_time']:
                        try:
                            driver.switch_to.window(handle)
                            driver.execute_script(get_monitor_js(url_id))
                            with URL_STATUS_LOCK:
                                URL_STATUS[url_id]['monitoring_injected'] = True
                                URL_STATUS[url_id]['last_activity'] = "Monitoring injected"
                        except Exception as e:
                            print(f"Error injecting monitoring for URL {url_id}: {e}")
                        finally:
                            driver.switch_to.window(current_handle)
            
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
        
        driver.quit()
        print("\nBrowser closed")

if __name__ == "__main__":
    main()