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

# ===== CONFIGURATION ===== #
MARKET_URLS = OrderedDict([
    (1, "https://steamcommunity.com/market/listings/730/Nova%20%7C%20Yorkshire%20%28Minimal%20Wear%29?query=&start=0&count=100"),
    (2, "https://steamcommunity.com/market/listings/730/FAMAS%20%7C%20Half%20Sleeve%20%28Minimal%20Wear%29?query=&start=0&count=100"),
    (3, "https://steamcommunity.com/market/listings/730/MP5-SD%20%7C%20Savannah%20Halftone%20%28Field-Tested%29?query=&start=0&count=100"),
    (4, "https://steamcommunity.com/market/listings/730/Negev%20%7C%20Sour%20Grapes%20%28Minimal%20Wear%29?query=&start=0&count=100")
])

# URL-specific settings (REMOVED click_reload_button FROM ALL CONFIGS)
URL_CONFIG = {
    1: {
        'check_pattern': 0,
        'target_pattern': 699,
        'auto_purchase': True,
        'pages_to_check': 1,
        'sniping_window_close_delay': (3, 5),
        'max_skins_to_buy': 10,
        'cycle_time_range': (270, 330),
        'initial_wait_range': (0, 10)
    },
    2: {
        'check_pattern': 0,
        'target_pattern': 699,
        'auto_purchase': True,
        'pages_to_check': 12,
        'sniping_window_close_delay': (3, 5),
        'max_skins_to_buy': 10,
        'cycle_time_range': (270, 330),
        'initial_wait_range': (100, 110)
    },
    3: {
        'check_pattern': 0,
        'target_pattern': 699,
        'auto_purchase': True,
        'pages_to_check': 25,
        'sniping_window_close_delay': (3, 5),
        'max_skins_to_buy': 10,
        'cycle_time_range': (270, 330),
        'initial_wait_range': (210, 220)
    },
    4: {
        'check_pattern': 0,
        'target_pattern': 699,
        'auto_purchase': True,
        'pages_to_check': 1,
        'sniping_window_close_delay': (3, 5),
        'max_skins_to_buy': 10,
        'cycle_time_range': (270, 330),
        'initial_wait_range': (320, 330)
    }
}

# PER-URL FLOAT SETTINGS
URL_FLOAT_CONFIG = {
    1: {  
        'float_direction': 0,  # 0 = low float, 1 = high float
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
    4: {  # MAG-7 | Resupply (Minimal Wear)
        'float_direction': 0,
        'price_float_table': {
            0.23: 0.09333,
            0.26: 0.0865,
            0.3: 0.08
        }
    }
}

# Timing settings (REMOVED reload_button_wait)
TIMING_SETTINGS = {
    'page_nav_delay_min': 50,
    'page_nav_delay_max': 150,
    'wait_after_sort_min': 0,
    'wait_after_sort_max': 30,
    'sort_button_press_delay': (0, 0.05),
    'sniper_timeout': 30,
    '429_check_interval': 1,
    'global_cooldown_min': 300,
    'global_cooldown_max': 350,
    'global_error_check_delay': 10
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
        'current_cycle': 0,
        'next_snipe_time': "Calculating...",
        'status': "Waiting initial cycle",
        'last_snipe_result': "N/A",
        'skins_bought_total': 0,
        'current_skins_bought': 0,
        'profile_used': "N/A",
        'current_attempt': 0
    }

# Global 429 error tracking
GLOBAL_429_STATUS = {
    'cooldown_until': 0,
    'last_detected': 0,
    'detection_count': 0,
    'status': 'Active',
    'cooldown_added': 0
}
GLOBAL_429_LOCK = threading.Lock()

# Global cycle tracking
GLOBAL_CYCLE_STATUS = {
    'cycle_start_time': 0,
    'current_cycle': 0,
    'total_skins_bought': 0,
    'total_snipe_attempts': 0
}
CYCLE_LOCK = threading.Lock()

# Lock for thread-safe status updates
URL_STATUS_LOCK = threading.Lock()

# Global task tracking
ACTIVE_SNIPERS = {}
SNIPER_LOCK = threading.Lock()

# Profile tracking per URL
URL_PROFILE_INDEX = {}
for url_id in MARKET_URLS:
    URL_PROFILE_INDEX[url_id] = random.randint(0, len(PROFILE_PATHS)-1)

# ===== 429 ERROR DETECTION FUNCTIONS ===== #
def check_429_error(driver):
    """Check if the page contains a 429 Too Many Requests error (SIH extension warning)"""
    try:
        # Check for the specific error message shown in the HTML structure
        error_elements = driver.find_elements(By.XPATH, "//span[contains(@class, 'sih_label_warning') and contains(text(), 'Steam error: 429')]")
        if error_elements:
            return True
            
        # Also check for other indicators of rate limiting
        page_text = driver.page_source
        if "429 Too Many Requests" in page_text or "Too Many Requests" in page_text:
            return True
            
        # Check for Steam-specific error patterns
        if "Steam error: 429" in page_text:
            return True
            
    except Exception as e:
        # If we can't check, assume no error for now
        pass
        
    return False

def check_global_rate_limit_error(driver):
    """Check for the second type of rate limiting error (full page error)"""
    try:
        # Check for the error page structure with h2 Error element
        error_elements = driver.find_elements(By.XPATH, "//div[@class='error_ctn']//h2[contains(text(), 'Error')]")
        if error_elements:
            print("!!! GLOBAL RATE LIMIT ERROR DETECTED (Full Page Error) !!!")
            return True
            
        # Additional check for error page content
        page_text = driver.page_source
        if '<h2>Error</h2>' in page_text and 'error_ctn' in page_text:
            print("!!! GLOBAL RATE LIMIT ERROR DETECTED (Error Page Structure) !!!")
            return True
            
        # Check for error in main content area
        try:
            main_content = driver.find_element(By.ID, "mainContents")
            if "Error" in main_content.text and main_content.is_displayed():
                error_headers = main_content.find_elements(By.TAG_NAME, "h2")
                for header in error_headers:
                    if "Error" in header.text:
                        print("!!! GLOBAL RATE LIMIT ERROR DETECTED (Main Content Error) !!!")
                        return True
        except:
            pass
            
    except Exception as e:
        # If we can't check, assume no error for now
        pass
        
    return False

def update_global_429_status(detected=False):
    """Update the global 429 status and trigger cooldown if detected"""
    global GLOBAL_429_STATUS
    
    with GLOBAL_429_LOCK:
        current_time = time.time()
        
        if detected:
            # Calculate cooldown duration
            cooldown_duration = random.randint(
                TIMING_SETTINGS['global_cooldown_min'], 
                TIMING_SETTINGS['global_cooldown_max']
            )
            
            GLOBAL_429_STATUS['cooldown_until'] = current_time + cooldown_duration
            GLOBAL_429_STATUS['last_detected'] = current_time
            GLOBAL_429_STATUS['detection_count'] += 1
            GLOBAL_429_STATUS['status'] = f'Cooldown until {time.strftime("%H:%M:%S", time.localtime(current_time + cooldown_duration))}'
            GLOBAL_429_STATUS['cooldown_added'] = cooldown_duration
            
            print(f"\n!!! 429 ERROR DETECTED - GLOBAL COOLDOWN ACTIVATED FOR {cooldown_duration} SECONDS !!!")
            print(f"!!! ADDING {cooldown_duration} SECONDS TO ALL CYCLE TIMERS !!!")
            
            # Stop all active sniper tasks
            with SNIPER_LOCK:
                for url_id, sniper in list(ACTIVE_SNIPERS.items()):
                    if hasattr(sniper, 'stop_event'):
                        sniper.stop_event.set()
                        print(f"Stopping sniper for URL {url_id} due to 429 error")
            
            return True
        else:
            # Check if cooldown has expired
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
                # Check for both types of errors
                if check_429_error(driver) or check_global_rate_limit_error(driver):
                    update_global_429_status(detected=True)
                    stop_event.set()  # Signal to stop the sniper task
                    break
                time.sleep(check_interval)
            except Exception as e:
                # If we can't check, continue monitoring
                time.sleep(check_interval)
    
    monitor_thread = threading.Thread(target=monitor)
    monitor_thread.daemon = True
    monitor_thread.start()
    return monitor_thread

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

# ===== SNIPER FUNCTIONS ===== #
def get_random_delay(min_ms, max_ms):
    """Generate a random delay in seconds within specified range"""
    return random.uniform(min_ms, max_ms) / 1000.0

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

def is_sorting_complete(driver, url_id):
    """Checks if sorting is complete based on button text for specific URL"""
    button_text = get_sort_button_text(driver)
    
    float_direction = URL_FLOAT_CONFIG[url_id]['float_direction']
    
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

def perform_sorting(driver, clicks, url_id, delay_between_clicks=0):
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
            lambda d: is_sorting_complete(d, url_id)
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
    """Navigate to next page using CSFloat extension pagination"""
    max_retries = 5
    for attempt in range(max_retries):
        try:
            print(f"Attempt {attempt + 1}/{max_retries} to navigate to next page")
            
            # Wait for the page to be fully loaded
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.ID, "searchResultsRows"))
            )
            
            # Get current listing IDs for comparison
            current_listings = driver.find_elements(
                By.CSS_SELECTOR, "#searchResultsRows > div.market_listing_row"
            )[:2]
            previous_page_data = [listing.get_attribute("id") for listing in current_listings if listing.get_attribute("id")]
            
            # STRATEGY 1: Look for CSFloat extension pagination
            try:
                # Find the sih_pagination container
                sih_pagination = driver.find_element(By.CSS_SELECTOR, "div.sih_pagination")
                
                # Look for the next button inside
                next_button = sih_pagination.find_element(By.CSS_SELECTOR, "a.sih_button.next_page")
                
                # Check if disabled
                if "disabled" in next_button.get_attribute("class"):
                    print("Next page button is disabled (last page)")
                    return False
                
                print("Found CSFloat extension next button")
                
            except NoSuchElementException:
                # STRATEGY 2: Try alternative selectors
                selectors_to_try = [
                    "a.sih_button.next_page",
                    "div.sih_pagination a.next_page",
                    "div.pagination a.next_page",
                    "a.pagebtn",
                    "a.next_page"
                ]
                
                next_button = None
                for selector in selectors_to_try:
                    try:
                        next_button = driver.find_element(By.CSS_SELECTOR, selector)
                        print(f"Found next button with selector: {selector}")
                        break
                    except NoSuchElementException:
                        continue
                
                if not next_button:
                    print("Next page button not found with any selector")
                    return False
            
            # Check if button is clickable
            if not is_button_clickable(next_button):
                print("Button not clickable, scrolling into view...")
                driver.execute_script("arguments[0].scrollIntoView({block: 'center', behavior: 'smooth'});", next_button)
                time.sleep(0.5)
            
            # Add a small random delay before clicking
            nav_delay = get_random_delay(TIMING_SETTINGS['page_nav_delay_min'], TIMING_SETTINGS['page_nav_delay_max'])
            if nav_delay > 0:
                time.sleep(nav_delay)
            
            print("Clicking next page button...")
            
            # Try to click using JavaScript (more reliable for CSFloat)
            try:
                driver.execute_script("arguments[0].click();", next_button)
                print("JavaScript click executed")
            except Exception as e:
                print(f"JavaScript click failed: {str(e)}")
                try:
                    next_button.click()
                    print("Direct click executed")
                except Exception as e2:
                    print(f"Direct click failed: {str(e2)}")
                    continue
            
            # IMPORTANT: CSFloat uses AJAX for pagination
            # Wait for page to start loading
            time.sleep(2)
            
            # Wait for the "info" div to update (shows "2 from 3" etc.)
            try:
                WebDriverWait(driver, 10).until(
                    lambda d: any("from" in info_div.text and "1 from" not in info_div.text
                                 for info_div in d.find_elements(By.CSS_SELECTOR, "div.sih_pagination div.info"))
                )
                print("Pagination info updated - page changed")
                return True
            except TimeoutException:
                # Fallback: check if listings changed
                current_listings = driver.find_elements(
                    By.CSS_SELECTOR, "#searchResultsRows > div.market_listing_row"
                )[:2]
                current_ids = [listing.get_attribute("id") for listing in current_listings if listing.get_attribute("id")]
                
                if current_ids and current_ids != previous_page_data:
                    print("Listings changed - page navigation successful")
                    return True
                else:
                    print("Page might not have changed")
                    continue
                
        except StaleElementReferenceException:
            print(f"Stale element on attempt {attempt + 1}, retrying...")
            time.sleep(1)
        except Exception as e:
            print(f"Navigation error on attempt {attempt + 1}: {str(e)}")
            time.sleep(1)
    
    print("Failed to navigate to next page after all attempts")
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

def get_float_threshold_for_price(price_value, url_id):
    """Get the appropriate float threshold for a given price from the per-URL table"""
    # Find the closest price in the table that is <= the current price
    eligible_prices = [p for p in URL_FLOAT_CONFIG[url_id]['price_float_table'].keys() if p <= price_value]
    
    if not eligible_prices:
        # If no eligible price found, use the lowest price in table
        min_price = min(URL_FLOAT_CONFIG[url_id]['price_float_table'].keys())
        return URL_FLOAT_CONFIG[url_id]['price_float_table'][min_price]
    
    # Use the highest eligible price
    max_eligible_price = max(eligible_prices)
    return URL_FLOAT_CONFIG[url_id]['price_float_table'][max_eligible_price]

def check_skin_match(driver, listing_data, index, listing_element, remaining_purchases, url_config, sniper_status, url_id):
    """
    Checks if a skin matches the specified criteria using per-URL price-float table
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
    
    # Get dynamic float threshold based on price for this URL
    float_threshold = get_float_threshold_for_price(price_value, url_id)
    
    # Update sniper status with highest price
    if price_value > sniper_status['highest_price']:
        sniper_status['highest_price'] = price_value
    
    # Update sniper status with lowest float
    if sniper_status['lowest_float'] is None or float_value < sniper_status['lowest_float']:
        sniper_status['lowest_float'] = float_value
    
    # Get float direction for this URL
    float_direction = URL_FLOAT_CONFIG[url_id]['float_direction']
    
    # Check float based on direction
    if float_direction == 0:  # Low float
        float_match = float_value <= float_threshold
        float_info = f"Float: {listing_data['float_value']} {'✓' if float_match else '✗'} (Max: {float_threshold})"
    else:  # High float
        float_match = float_value >= float_threshold
        float_info = f"Float: {listing_data['float_value']} {'✓' if float_match else '✗'} (Min: {float_threshold})"
    
    # Check other criteria
    max_allowed_price = max(URL_FLOAT_CONFIG[url_id]['price_float_table'].keys())
    price_match = price_value <= max_allowed_price
    pattern_match = True
    
    if url_config['check_pattern'] == 1:
        try:
            pattern_match = int(listing_data["paint_seed"]) == url_config['target_pattern']
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
        if url_config['check_pattern'] == 1:
            print(f"Paint Seed: {listing_data['paint_seed']} (== {url_config['target_pattern']})")
        print("="*50 + "\n")
        
        # Attempt to purchase if enabled and we have remaining purchases
        purchase_attempted = False
        if url_config['auto_purchase'] and remaining_purchases > 0:
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
    if url_config['check_pattern'] == 1:
        print(f"  Pattern: {listing_data['paint_seed']} {'✓' if pattern_match else '✗'} (Target: {url_config['target_pattern']})")
    
    return False, False, remaining_purchases

def process_current_page(driver, number_of_skins, remaining_purchases, url_config, sniper_status, url_id):
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
            if url_config['check_pattern'] == 1:
                print(f"Paint Seed: {listing_data['paint_seed']}")
            
            is_match, purchase_attempted, remaining_purchases = check_skin_match(
                driver, listing_data, i, listing, remaining_purchases, url_config, sniper_status, url_id
            )
            
            if is_match:
                matches_found += 1
            if purchase_attempted:
                purchases_made += 1
                
            # Check if price exceeds max price (stopping condition)
            try:
                price_str = listing_data["price"].replace('€', '').replace(',', '.')
                price_value = float(price_str)
                max_allowed_price = max(URL_FLOAT_CONFIG[url_id]['price_float_table'].keys())
                if price_value > max_allowed_price:
                    print(f"Price {price_value} exceeds max allowed price {max_allowed_price}, stopping after this page")
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
                if url_config['check_pattern'] == 1:
                    print(f"Paint Seed: {listing_data['paint_seed']}")
                is_match, purchase_attempted, remaining_purchases = check_skin_match(
                    driver, listing_data, i, listing, remaining_purchases, url_config, sniper_status, url_id
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

# ===== CYCLE SNIPER TASK ===== #
class CycleSniperTask(threading.Thread):
    def __init__(self, url_id, url, url_config):
        super().__init__()
        self.url_id = url_id
        self.url = url
        self.url_config = url_config
        self.driver = None
        self.profile_num = 0
        self.profile_path = ""
        self.stop_event = threading.Event()
        self.status = "Initializing"
        self.base_profile_path = ""
        self.sniper_timeout_timer = None
        self._429_monitor_thread = None
        self._global_error_timer = None
        self.current_skins_bought = 0
        
        # Initialize sniper status for this URL
        with URL_STATUS_LOCK:
            URL_STATUS[self.url_id]['status'] = "Initializing"
            URL_STATUS[self.url_id]['current_attempt'] = 0
        
    def run(self):
        """Main cycle sniper execution"""
        try:
            # Update status
            self.status = "Starting sniper cycle"
            with URL_STATUS_LOCK:
                URL_STATUS[self.url_id]['status'] = "Starting"
                URL_STATUS[self.url_id]['current_attempt'] += 1
            
            # Open browser with next profile
            self.open_browser()
            
            # NEW: Check for global error immediately after page loads
            if check_global_rate_limit_error(self.driver):
                print("!!! GLOBAL RATE LIMIT ERROR DETECTED ON PAGE LOAD - ABORTING SNIPER !!!")
                update_global_429_status(detected=True)
                self.cleanup_browser()
                return
            
            # Start 429 error monitoring thread
            if self.driver:
                self._429_monitor_thread = start_429_monitor(
                    self.driver, 
                    self.stop_event, 
                    TIMING_SETTINGS['429_check_interval']
                )
            
            # NEW: Start global error check timer (10 seconds)
            self._global_error_timer = threading.Timer(
                TIMING_SETTINGS['global_error_check_delay'], 
                self._check_global_error_after_delay
            )
            self._global_error_timer.start()
            
            # Perform sniping
            result = self.run_sniper_cycle()
            
            # Cleanup browser
            self.cleanup_browser()
            
            # Update statistics
            if result == "success":
                with URL_STATUS_LOCK:
                    URL_STATUS[self.url_id]['skins_bought_total'] += self.current_skins_bought
                    URL_STATUS[self.url_id]['current_skins_bought'] = self.current_skins_bought
                with CYCLE_LOCK:
                    GLOBAL_CYCLE_STATUS['total_skins_bought'] += self.current_skins_bought
                
        except Exception as e:
            self.status = f"Error: {str(e)[:30]}"
            with URL_STATUS_LOCK:
                URL_STATUS[self.url_id]['status'] = f"Error: {str(e)[:30]}"
        
        finally:
            # Remove from active snipers
            with SNIPER_LOCK:
                if self.url_id in ACTIVE_SNIPERS:
                    del ACTIVE_SNIPERS[self.url_id]
            
            # Cancel timeout timer if it exists
            if self.sniper_timeout_timer:
                self.sniper_timeout_timer.cancel()
            
            # Cancel global error timer if it exists
            if self._global_error_timer:
                self._global_error_timer.cancel()

    def _check_global_error_after_delay(self):
        """Check for global error after 10 seconds delay"""
        if self.driver is None:
            return
            
        if check_global_rate_limit_error(self.driver):
            print("!!! GLOBAL RATE LIMIT ERROR DETECTED AFTER DELAY - ABORTING SNIPER !!!")
            update_global_429_status(detected=True)
            self.stop_event.set()

    def open_browser(self):
        """Open browser window for this cycle"""
        # Get next profile in rotation for this URL
        base_path, profile_num = self.get_next_profile()
        self.base_profile_path = base_path
        
        # Get temporary profile path
        temp_path = PROFILE_MANAGER.get_temp_profile(base_path)
        
        # Configure options with cache optimizations (NO TEMP FILE DELETION)
        options = Options()
        options.add_argument(f"--user-data-dir={temp_path}")
        
        # Cache optimization settings (DISABLE CACHE WITHOUT DELETING TEMP FILES)
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
        
        # Randomize window size
        width = random.randint(1000, 1200)
        height = random.randint(800, 900)
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
            URL_STATUS[self.url_id]['profile_used'] = self.profile_num
        
        # Load URL with random parameter to avoid caching
        rand_num = random.randint(1, 1000000)
        full_url = f"{self.url}?★%20&rand={rand_num}"
        
        # Clear cache before loading page (NO TEMP FILE DELETION)
        self.driver.execute_script("window.localStorage.clear();")
        self.driver.execute_script("window.sessionStorage.clear();")
        
        self.driver.get(full_url)
        self.status = f"Page loading (Profile {self.profile_num})"

    def run_sniper_cycle(self):
        """Run the sniper cycle logic with 429 error checking"""
        try:
            # STEP 1: Check for errors immediately after page loads
            print("Checking for errors after page load...")
            if check_429_error(self.driver) or check_global_rate_limit_error(self.driver):
                print("!!! ERROR DETECTED ON PAGE LOAD - ABORTING SNIPER !!!")
                update_global_429_status(detected=True)
                return "429_error"
            
            # Update status
            self.status = "Starting sniper"
            with URL_STATUS_LOCK:
                URL_STATUS[self.url_id]['status'] = "Sniping"
            
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
            
            # Initialize sniper status
            sniper_status = {
                'skins_bought': 0,
                'lowest_float': None,
                'highest_price': 0,
                'current_page': 0,
                'extracted_data': []
            }
            
            total_matches = 0
            total_purchases = 0
            remaining_purchases = self.url_config['max_skins_to_buy']
            
            # Get float direction for this URL
            float_direction = URL_FLOAT_CONFIG[self.url_id]['float_direction']
            
            # Process each page
            for page in range(1, self.url_config['pages_to_check'] + 1):
                # Check for errors before processing each page
                if check_429_error(self.driver) or check_global_rate_limit_error(self.driver):
                    print("!!! ERROR DETECTED DURING PAGE PROCESSING - ABORTING SNIPER !!!")
                    update_global_429_status(detected=True)
                    return "429_error"
                
                # Check if stop event is set (could be from 429 monitor thread or global error timer)
                if self.stop_event.is_set():
                    print("Stop event set (likely from error detection), aborting sniper")
                    return "429_error"
                
                # Update sniper status
                sniper_status['current_page'] = page
                
                # Check if we've reached the purchase limit before processing page
                if remaining_purchases <= 0:
                    print("\nPurchase limit reached before page processing")
                    break
                    
                print(f"\n{'='*50}")
                print(f"PROCESSING PAGE {page}/{self.url_config['pages_to_check']}")
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
                    if not perform_sorting(self.driver, clicks, self.url_id):
                        print("Failed to sort listings, skipping page")
                        continue
                else:
                    # For pages after the first, press sort button 3 times with delays
                    print("Pressing sort button 3 times with delays...")
                    delay_between_clicks = random.uniform(*TIMING_SETTINGS['sort_button_press_delay'])
                    if not perform_sorting(self.driver, 3, self.url_id, delay_between_clicks):
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
                    self.driver, self.url_config['max_skins_to_buy'], remaining_purchases, self.url_config, sniper_status, self.url_id
                )
                total_matches += page_matches
                total_purchases += page_purchases
                self.current_skins_bought = total_purchases
                
                print(f"\nPage {page} summary: {page_matches} matches, {page_purchases} purchases")
                
                # Check if we should stop after this page
                if should_stop:
                    print("Stopping condition met, ending sniper")
                    break
                    
                # Stop if we've processed all requested pages
                if page >= self.url_config['pages_to_check']:
                    break
                    
                # Go to next page if available
                print("\nMoving to next page...")
                if not go_to_next_page(self.driver):
                    print("No more pages available")
                    break

            # Print final summary
            print("\n" + "="*50)
            print("SNIPER CYCLE COMPLETE - SUMMARY")
            print("="*50)
            print(f"Checked {min(page, self.url_config['pages_to_check'])}/{self.url_config['pages_to_check']} pages")
            print(f"Found {total_matches} skins matching your criteria")
            if self.url_config['auto_purchase']:
                print(f"Purchased {total_purchases} skins")
            print(f"Purchase limit: {self.url_config['max_skins_to_buy']}")
            print(f"Remaining skins to buy: {max(0, remaining_purchases)}")
            print("="*50)
            
            # Cancel timeout timer since we completed successfully
            if self.sniper_timeout_timer:
                self.sniper_timeout_timer.cancel()
                print("Sniper timeout timer cancelled")
            
            # Update final status
            self.status = f"Completed - {total_purchases} skins bought"
            with URL_STATUS_LOCK:
                URL_STATUS[self.url_id]['status'] = f"Completed - {total_purchases} skins"
                URL_STATUS[self.url_id]['last_snipe_result'] = f"{total_purchases} skins bought"
            
            # Wait before closing if needed
            close_delay = random.randint(*self.url_config['sniping_window_close_delay'])
            print(f"Waiting {close_delay}s before closing...")
            time.sleep(close_delay)
            
            return "success"
                
        except Exception as e:
            self.status = f"Error: {str(e)[:30]}"
            with URL_STATUS_LOCK:
                URL_STATUS[self.url_id]['status'] = f"Error: {str(e)[:30]}"
            return "error"
    
    def sniper_timeout_handler(self):
        """Handler for sniper timeout - closes the browser if still open"""
        print(f"\n!!! SNIPER TIMEOUT REACHED ({TIMING_SETTINGS['sniper_timeout']}s) - CLOSING WINDOW !!!")
        self.cleanup_browser()
        self.stop_event.set()
    
    def get_next_profile(self):
        """Get next profile in rotation for this URL"""
        global URL_PROFILE_INDEX
        
        # Rotate to next profile
        URL_PROFILE_INDEX[self.url_id] = (URL_PROFILE_INDEX[self.url_id] + 1) % len(PROFILE_PATHS)
        
        profile_idx = URL_PROFILE_INDEX[self.url_id]
        return PROFILE_PATHS[profile_idx], profile_idx + 1
    
    def cleanup_browser(self):
        """Clean up browser resources for this attempt if needed"""
        if self.driver:
            try:
                # Clear browser cache before closing (NO TEMP FILE DELETION)
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

# ===== CYCLE MANAGER ===== #
class CycleManager(threading.Thread):
    def __init__(self, url_id, url, url_config):
        super().__init__()
        self.url_id = url_id
        self.url = url
        self.url_config = url_config
        self.stop_event = threading.Event()
        self.current_cycle = 0
        self.status = "Initializing"
        
    def run(self):
        """Main cycle management loop"""
        print(f"URL {self.url_id}: Cycle manager started")
        
        # Initial wait before starting cycles
        initial_wait = random.randint(*self.url_config['initial_wait_range'])
        self.status = f"Waiting initial {initial_wait}s"
        with URL_STATUS_LOCK:
            URL_STATUS[self.url_id]['status'] = f"Waiting initial {initial_wait}s"
        
        print(f"URL {self.url_id}: Initial wait for {initial_wait} seconds")
        self.wait_with_stop_check(initial_wait)
        
        if self.stop_event.is_set():
            return
        
        # Main cycle loop
        while not self.stop_event.is_set():
            self.current_cycle += 1
            
            with CYCLE_LOCK:
                GLOBAL_CYCLE_STATUS['current_cycle'] = self.current_cycle
                GLOBAL_CYCLE_STATUS['total_snipe_attempts'] += 1
            
            # Calculate cycle time (with potential 429 cooldown addition)
            base_cycle_time = random.randint(*self.url_config['cycle_time_range'])
            
            # Check if we need to add 429 cooldown time
            with GLOBAL_429_LOCK:
                if GLOBAL_429_STATUS['cooldown_added'] > 0:
                    cycle_time = base_cycle_time + GLOBAL_429_STATUS['cooldown_added']
                    print(f"URL {self.url_id}: Adding {GLOBAL_429_STATUS['cooldown_added']}s to cycle due to 429 cooldown")
                    # Reset the added time so it's only applied once
                    GLOBAL_429_STATUS['cooldown_added'] = 0
                else:
                    cycle_time = base_cycle_time
            
            # Update status for next snipe time
            next_snipe_time = time.strftime('%H:%M:%S', time.localtime(time.time() + cycle_time))
            with URL_STATUS_LOCK:
                URL_STATUS[self.url_id]['current_cycle'] = self.current_cycle
                URL_STATUS[self.url_id]['next_snipe_time'] = next_snipe_time
                URL_STATUS[self.url_id]['status'] = f"Waiting cycle ({cycle_time}s)"
            
            print(f"URL {self.url_id}: Cycle {self.current_cycle} - waiting {cycle_time}s until {next_snipe_time}")
            
            # Wait for cycle time
            self.wait_with_stop_check(cycle_time)
            
            if self.stop_event.is_set():
                break
            
            # Check for global cooldown before starting sniper
            global_cooldown_active, time_left = is_global_cooldown_active()
            if global_cooldown_active:
                print(f"URL {self.url_id}: Global cooldown active ({int(time_left)}s left), skipping cycle")
                # Add the remaining cooldown time to the next cycle
                with GLOBAL_429_LOCK:
                    GLOBAL_429_STATUS['cooldown_added'] = max(GLOBAL_429_STATUS['cooldown_added'], int(time_left))
                continue
            
            # Start sniper task
            print(f"URL {self.url_id}: Starting sniper cycle {self.current_cycle}")
            self.status = "Starting sniper"
            with URL_STATUS_LOCK:
                URL_STATUS[self.url_id]['status'] = "Starting sniper"
            
            sniper = CycleSniperTask(self.url_id, self.url, self.url_config)
            
            with SNIPER_LOCK:
                ACTIVE_SNIPERS[self.url_id] = sniper
            
            sniper.start()
            
            # Wait for sniper to complete
            while sniper.is_alive() and not self.stop_event.is_set():
                time.sleep(1)
            
            # Small delay between cycles
            if not self.stop_event.is_set():
                time.sleep(5)
    
    def wait_with_stop_check(self, wait_time):
        """Wait for specified time while checking for stop event"""
        start_time = time.time()
        while time.time() - start_time < wait_time:
            if self.stop_event.is_set():
                return
            time.sleep(1)

# ===== STATUS DISPLAY ===== #
def display_status():
    """Display consolidated status for all URLs"""
    os.system('cls' if os.name == 'nt' else 'clear')
    print("STEAM MARKET CYCLE-BASED SNIPER")
    print("=" * 100)
    print("Ctrl+C to exit")
    print("=" * 100)
    
    # Create thread-safe copies of the status
    with URL_STATUS_LOCK:
        status_copy = copy.deepcopy(URL_STATUS)
    
    with CYCLE_LOCK:
        cycle_copy = copy.deepcopy(GLOBAL_CYCLE_STATUS)
    
    with GLOBAL_429_LOCK:
        global_429_copy = copy.deepcopy(GLOBAL_429_STATUS)
    
    # Get global 429 status
    global_cooldown_active, global_time_left = is_global_cooldown_active()
    
    # Global Status
    print("\nGLOBAL STATUS")
    print("=" * 100)
    print(f"Current Cycle: {cycle_copy['current_cycle']} | Total Skins Bought: {cycle_copy['total_skins_bought']} | Total Attempts: {cycle_copy['total_snipe_attempts']}")
    
    # Global 429 Status
    print("\nGLOBAL 429 STATUS")
    print("=" * 100)
    if global_cooldown_active:
        print(f"!!! GLOBAL COOLDOWN ACTIVE - {int(global_time_left)}s LEFT !!!")
    else:
        print("Status: Active")
    print(f"Last Status: {global_429_copy['status']}")
    print(f"Detection Count: {global_429_copy['detection_count']}")
    
    # URL Status table
    print("\nURL STATUS")
    print("=" * 100)
    print(f"{'ID':<3} {'Cycle':<6} {'Next Snipe':<12} {'Status':<25} {'Last Result':<20} {'Total Bought':<12} {'Current Bought':<14} {'Profile':<8}")
    print("-" * 100)
    
    for url_id in MARKET_URLS:
        status = status_copy[url_id]
        print(f"{url_id:<3} {status['current_cycle']:<6} {status['next_snipe_time']:<12} "
              f"{status['status'][:24]:<25} {status['last_snipe_result'][:19]:<20} "
              f"{status['skins_bought_total']:<12} {status['current_skins_bought']:<14} "
              f"{status['profile_used']:<8}")
    
    # Per-URL Float Configuration
    print("\nPER-URL FLOAT CONFIGURATION")
    print("=" * 100)
    for url_id in MARKET_URLS:
        float_config = URL_FLOAT_CONFIG[url_id]
        direction_str = "Low Float" if float_config['float_direction'] == 0 else "High Float"
        print(f"\nURL {url_id}: {direction_str}")
        print(f"{'Price (€)':<10} {'Max Float':<10}")
        print("-" * 20)
        for price, max_float in sorted(float_config['price_float_table'].items()):
            print(f"{price:<10.2f} {max_float:<10.4f}")
    
    # Active Snipers
    print("\nACTIVE SNIPERS")
    print("=" * 100)
    with SNIPER_LOCK:
        if ACTIVE_SNIPERS:
            for url_id, sniper in ACTIVE_SNIPERS.items():
                print(f"URL {url_id}: {sniper.status}")
        else:
            print("No active snipers")
    
    # Cycle configuration
    print("\nCYCLE CONFIGURATION")
    print("=" * 100)
    print(f"{'ID':<3} {'Pages':<6} {'Max Buy':<8} {'Cycle Time':<12} {'Initial Wait':<12} {'Auto Buy':<8}")
    print("-" * 100)
    
    for url_id in MARKET_URLS:
        config = URL_CONFIG[url_id]
        auto_buy = 'Yes' if config['auto_purchase'] else 'No'
        print(f"{url_id:<3} {config['pages_to_check']:<6} {config['max_skins_to_buy']:<8} "
              f"{config['cycle_time_range'][0]}-{config['cycle_time_range'][1]:<12} "
              f"{config['initial_wait_range'][0]}-{config['initial_wait_range'][1]:<12} "
              f"{auto_buy:<8}")

# ===== MAIN FUNCTION ===== #
def main():
    global PROFILE_MANAGER
    
    print("Initializing Cycle-Based Steam Market Sniper...")
    print("=" * 80)
    
    # Initialize global cycle status
    with CYCLE_LOCK:
        GLOBAL_CYCLE_STATUS['cycle_start_time'] = time.time()
        GLOBAL_CYCLE_STATUS['current_cycle'] = 0
        GLOBAL_CYCLE_STATUS['total_skins_bought'] = 0
        GLOBAL_CYCLE_STATUS['total_snipe_attempts'] = 0
    
    # Start cycle managers for each URL
    cycle_managers = []
    for url_id, url in MARKET_URLS.items():
        manager = CycleManager(url_id, url, URL_CONFIG[url_id])
        cycle_managers.append(manager)
        manager.start()
        print(f"Started cycle manager for URL {url_id}")
    
    # Start status update thread
    status_running = True
    def status_updater():
        while status_running:
            display_status()
            time.sleep(2)  # Update every 2 seconds
    
    status_thread = threading.Thread(target=status_updater)
    status_thread.daemon = True
    status_thread.start()
    
    # Main loop
    try:
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\nShutting down cycle sniper...")
        status_running = False
        
        # Stop all cycle managers
        for manager in cycle_managers:
            manager.stop_event.set()
        
        # Wait for cycle managers to stop
        for manager in cycle_managers:
            manager.join(timeout=5)
        
        # Stop all active snipers
        with SNIPER_LOCK:
            for url_id, sniper in list(ACTIVE_SNIPERS.items()):
                sniper.stop_event.set()
        
        print("Cycle sniper shutdown complete")

if __name__ == "__main__":
    main()