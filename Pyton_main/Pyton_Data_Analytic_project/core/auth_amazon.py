# core/auth_amazon.py

import os
from pathlib import Path

from selenium import webdriver
from selenium.common.exceptions import SessionNotCreatedException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.webdriver import WebDriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


def ask_yes_no(prompt: str) -> bool:
    while True:
        answer = input(prompt).strip().lower()
        if answer in ("y", "yes"):
            return True
        elif answer in ("n", "no"):
            return False
        else:
            print("Please enter 'y' or 'n'.")


def open_amazon_home(driver: WebDriver) -> bool:
    try:
        driver.get("https://www.amazon.com/")
        return True
    except Exception:
        print("[🚫] Failed to load Amazon page. Chrome may have been closed.")
        return False


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
        raise ValueError(
            "Both user_data_dir and profile_dir must be provided. Please check your environment variables."
        )
    options = Options()
    options.add_argument(f"--user-data-dir={user_data_dir}")
    options.add_argument(f"--profile-directory={profile_dir}")
    options.add_argument("--disable-notifications")
    options.add_argument("--start-maximized")
    options.add_experimental_option("detach", True)  # Keeps the browser open

    try:
        driver = webdriver.Chrome(options=options)
        if not driver.session_id:
            raise RuntimeError("Browser session has been closed unexpectedly.")
        if not open_amazon_home(driver):
            decision = ask_yes_no("Do you want to restart the Chrome session? (y/n): ")
            if decision:
                driver.quit()
                return get_chrome_driver_with_profile(user_data_dir, profile_dir)
            else:
                print("[✋] Review collection aborted by user.")
                driver.quit()
                raise RuntimeError("User aborted due to closed Chrome.")
        print(f"[🟢] Chrome started with user profile")
        return driver
    except SessionNotCreatedException:
        print("[⚠] Chrome profile is currently in use or unavailable.")

        temp_options = Options()
        temp_options.add_argument("--disable-notifications")
        temp_options.add_argument("--start-maximized")
        temp_options.add_experimental_option("detach", True)
        try:
            driver = webdriver.Chrome(options=temp_options)
            if not driver.session_id:
                raise RuntimeError("Browser session has been closed unexpectedly.")
            if not open_amazon_home(driver):
                decision = ask_yes_no("Do you want to restart the Chrome session? (y/n): ")
                if decision:
                    driver.quit()
                    return get_chrome_driver_with_profile(user_data_dir, profile_dir)
                else:
                    print("[✋] Review collection aborted by user.")
                    driver.quit()
                    raise RuntimeError("User aborted due to closed Chrome.")
            print("[🔐] Please log into Amazon in the opened Chrome window.")
            print("Press [Enter] when you have completed login.")
            input()

            if is_logged_in(driver):
                print("[✅] Login confirmed. Proceeding with review collection.")
            else:
                proceed = ask_yes_no(
                    "[⚠] Login not detected. Continue with limited access? (y/n): "
                )
                if not proceed:
                    print("[✋] Aborting session as requested by user.")
                    driver.quit()
                    raise RuntimeError("User aborted due to missing login.")
            print(f"[🟢] Chrome started with temporary profile")
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
        WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.ID, "nav-link-accountList"))
        )
        account_element = driver.find_element("id", "nav-link-accountList")
        if "Sign in" not in account_element.text:
            print("[✅] Amazon session is active.")
            return True
        else:
            print("[❌] Not logged into Amazon.")
            return False
    except Exception:
        return False


# ------------------------------
# Utility: Start Amazon Session
def start_amazon_browser_session(asin: str, collection_dir: Path) -> WebDriver:
    """
    Start a browser session with Chrome, navigate to Amazon, and ensure user login.

    Args:
        asin: ASIN string to construct the target URL for review scraping.
        collection_dir: Directory where HTML snapshots may be stored.

    Returns:
        Selenium WebDriver instance with an active Amazon session.
    """
    user_data_dir = os.environ.get("CHROME_USER_DATA_DIR")
    profile_dir = os.environ.get("CHROME_PROFILE_DIR")

    try:
        driver = get_chrome_driver_with_profile(user_data_dir, profile_dir)
        return driver
    except Exception:
        print("[🔄] Trying temporary Chrome profile as fallback.")
        options = Options()
        options.add_argument("--disable-notifications")
        options.add_argument("--start-maximized")
        options.add_experimental_option("detach", True)
        driver = webdriver.Chrome(options=options)

        if not open_amazon_home(driver):
            raise RuntimeError("Failed to load Amazon homepage.")

        print("[🔐] Please log into Amazon in the opened Chrome window.")
        print("Press [Enter] when you have completed login.")
        input()

        if is_logged_in(driver):
            print("[✅] Login successful.")
            return driver
        else:
            raise RuntimeError("Amazon login was not successful.")
