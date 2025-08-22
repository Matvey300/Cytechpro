# core/auth_amazon.py

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.webdriver import WebDriver
from selenium.common.exceptions import SessionNotCreatedException
import os

def get_chrome_driver_with_profile(user_data_dir: str, profile_dir: str) -> WebDriver:
    """
    Launch a Chrome WebDriver session using an existing user profile
    where the user is already logged into Amazon.

    Args:
        user_data_dir: Path to the Chrome user data directory.
        profile_dir: Name of the specific profile directory (e.g. 'Profile 2').

    Returns:
        Configured Selenium WebDriver instance.
    """
    if not user_data_dir or not profile_dir:
        raise ValueError("Both user_data_dir and profile_dir must be provided. Please check your environment variables.")
        print("[ℹ] Proceeding without Amazon login. Some reviews may be unavailable or limited.")
    options = Options()
    options.add_argument(f"--user-data-dir={user_data_dir}")
    options.add_argument(f"--profile-directory={profile_dir}")
    options.add_argument("--disable-notifications")
    options.add_argument("--start-maximized")
    options.add_experimental_option("detach", True)  # Keeps the browser open

    try:
        driver = webdriver.Chrome(options=options)
        return driver
    except SessionNotCreatedException as e:
        print("[⚠] Chrome profile is currently in use or unavailable.")
        print("[ℹ] Proceeding without Amazon login. Some reviews may be unavailable or limited.")

        temp_options = Options()
        temp_options.add_argument("--disable-notifications")
        temp_options.add_argument("--start-maximized")
        temp_options.add_experimental_option("detach", True)
        try:
            driver = webdriver.Chrome(options=temp_options)
            return driver
        except Exception as temp_e:
            print("[❌] Failed to start temporary session.")
            raise temp_e


def is_logged_in(driver: WebDriver) -> bool:
    """
    Check if the user is logged into Amazon by looking for the account menu.
    
    Args:
        driver: Selenium WebDriver currently on amazon.com

    Returns:
        True if logged in, False otherwise
    """
    try:
        driver.get("https://www.amazon.com/")
        driver.implicitly_wait(5)
        account_element = driver.find_element("id", "nav-link-accountList")
        if "Sign in" not in account_element.text:
            print("[✅] Amazon session is active.")
            return True
        else:
            print("[❌] Not logged into Amazon.")
            return False
    except Exception:
        return False