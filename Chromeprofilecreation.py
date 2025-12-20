import os
import time
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager

def setup_profiles():
    # Create profile directories if they don't exist
    profiles = [
        {"id": 1, "path": os.path.join(os.getcwd(), "ChromeSteamProfiles01")},
        {"id": 2, "path": os.path.join(os.getcwd(), "ChromeSteamProfiles02")},
        {"id": 3, "path": os.path.join(os.getcwd(), "ChromeSteamProfiles03")},
        {"id": 4, "path": os.path.join(os.getcwd(), "ChromeSteamProfiles04")},
        {"id": 5, "path": os.path.join(os.getcwd(), "ChromeSteamProfiles05")}
    ]

    for profile in profiles:
        if not os.path.exists(profile['path']):
            os.makedirs(profile['path'])
            print(f"Created profile directory: {profile['path']}")

    return profiles

def login_to_steam(profiles):
    print("\nSTEAM LOGIN SETUP")
    print("=" * 60)
    print("This script will open 5 Chrome windows with separate profiles.")
    print("Please login to your Steam account and install the Csfloat and Steam Inventory Helper extension in each window.")
    print("After, you can close the browser windows.")
    print("=" * 60 + "\n")

    drivers = []
    
    try:
        # Open a browser for each profile
        for profile in profiles:
            print(f"Opening Chrome for Profile {profile['id']}...")
            
            options = Options()
            options.add_argument(f"--user-data-dir={profile['path']}")
            options.add_argument("--start-maximized")
            
            # Disable automation flags
            options.add_argument("--disable-blink-features=AutomationControlled")
            options.add_experimental_option("excludeSwitches", ["enable-automation"])
            options.add_experimental_option('useAutomationExtension', False)
            
            # Create driver
            service = Service(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=options)
            
            # Navigate to Steam login
            driver.get("https://store.steampowered.com/login/")
            print(f"Profile {profile['id']} browser opened. Please login to Steam.")
            
            drivers.append(driver)
            time.sleep(2)  # Stagger window openings

        print("\nAll browsers opened successfully!")
        print("Please complete the Steam login process in all 3 windows.")
        print("After logging in, you can close the browsers and run the main monitoring script.\n")

        # Keep the script running until all browsers are closed
        while any([driver.service.process for driver in drivers if hasattr(driver, 'service')]):
            time.sleep(1)

    except Exception as e:
        print(f"Error occurred: {str(e)}")
    finally:
        # Clean up any remaining drivers
        for driver in drivers:
            try:
                if driver.service.process:
                    driver.quit()
            except:
                pass

if __name__ == "__main__":
    profiles = setup_profiles()
    login_to_steam(profiles)
    print("\nSetup complete! You can now run the main script.")