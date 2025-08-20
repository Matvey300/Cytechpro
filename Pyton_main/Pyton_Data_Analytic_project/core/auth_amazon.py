# core/auth_amazon.py

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.webdriver import WebDriver

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
    options = Options()
    options.add_argument(f"--user-data-dir={user_data_dir}")
    options.add_argument(f"--profile-directory={profile_dir}")
    options.add_argument("--disable-notifications")
    options.add_argument("--start-maximized")
    options.add_experimental_option("detach", True)  # Keeps the browser open

    driver = webdriver.Chrome(options=options)
    return driver


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
        return "Sign in" not in account_element.text
    except Exception:
        return False