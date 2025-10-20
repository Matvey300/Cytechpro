"""
# === Module Header ===
# 📁 Module: scraper/driver.py
# 📅 Last Reviewed: 2025-10-15
# 🔧 Status: 🟢 Stable
# 👤 Owner: MatveyB
# 📝 Summary: Selenium driver setup; respects visibility/profile from env.
# =====================
"""

from core.env_check import ENV_VARS, get_chrome_profile_env
from core.session import print_info
from selenium import webdriver
from selenium.webdriver.chrome.options import Options


def start_amazon_browser_session(profile: str, user_data_dir: str):
    chrome_options = Options()
    if profile:
        chrome_options.add_argument(f"--profile-directory={profile}")
    if user_data_dir:
        chrome_options.add_argument(f"--user-data-dir={user_data_dir}")
    chrome_options.add_argument("--start-maximized")
    chrome_options.add_argument("--disable-infobars")
    chrome_options.add_argument("--disable-extensions")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")

    visibility = (ENV_VARS.get("BROWSER_VISIBILITY") or "offscreen").lower()
    if visibility in ("headless", "offscreen"):
        chrome_options.add_argument("--headless=new")

    try:
        driver = webdriver.Chrome(options=chrome_options)
        if visibility == "minimize":
            try:
                driver.minimize_window()
            except Exception:
                pass
    except Exception as e:
        print_info(f"[driver] Failed to start Chrome WebDriver: {e}")
        raise
    return driver


def init_driver(session_dir):
    # Use unified profile resolver; fall back to Default handled inside helper
    profile = get_chrome_profile_env()
    return start_amazon_browser_session(profile, session_dir)
