# === Module Status ===
# 📁 Module: scraper/navigator
# 📅 Last Reviewed: 2025-09-17
# 🔧 Status: ⚠️ Import fixed (print_info)
# 👤 Owner: Matvey Bosin
# 📝 Notes:
# - print replaced with print_info
# - returns normalized (True / -1)
# - ready for use
# =====================

import time

from core.env_check import ENV_VARS
from core.marketplaces import to_domain
from core.session import print_info
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


def navigate_to_reviews(driver, asin, marketplace=None):
    """Navigate to the reviews page of a product."""
    t = marketplace or ENV_VARS.get("DEFAULT_MARKETPLACE", "com")
    domain = to_domain(t)
    reviews_url = f"https://{domain}/product-reviews/{asin}/?sortBy=recent&pageNumber=1"
    print_info(f"[nav] Navigating to reviews URL: {reviews_url}")
    driver.get(reviews_url)
    time.sleep(1)  # Give page a moment to load
    return True


def _next_page_with_max_guard(driver, asin, current_page):
    """Attempt to click the 'Next' button on the reviews page."""
    try:
        next_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "li.a-last a"))
        )
        next_button.click()
        print_info(f"[{asin}] Clicked next page.")
        time.sleep(2)
        return current_page + 1
    except Exception as e:
        print_info(f"[{asin}] Failed to click 'Next': {e}")
        return -1


# === Added function: open_reviews_page ===
def open_reviews_page(driver, asin: str, marketplace: str) -> bool:
    """Open the reviews page for a given ASIN and verify load success."""
    t = marketplace or ENV_VARS.get("DEFAULT_MARKETPLACE", "com")
    domain = to_domain(t)
    url = f"https://{domain}/product-reviews/{asin}/?sortBy=recent&pageNumber=1"

    try:
        print_info(f"[nav] {asin}: opening reviews page")
        driver.get(url)
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "cm_cr-review_list"))
        )
        print_info(f"[nav] {asin}: reviews page loaded successfully.")
        return True
    except Exception as e:
        print_info(f"[nav] {asin}: failed to load reviews page: {e}")
        return False


"""
# === Module Header ===
# 📁 Module: scraper/navigator.py
# 📅 Last Reviewed: 2025-10-15
# 🔧 Status: 🟢 Stable
# 👤 Owner: MatveyB
# 📝 Summary: Navigation helpers for Selenium to reach target pages.
# =====================
"""
