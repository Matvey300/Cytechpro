# core/auth_amazon.py

from pathlib import Path
from typing import Optional, Tuple

from core.env_check import ENV_VARS
from selenium import webdriver
from selenium.common.exceptions import SessionNotCreatedException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.webdriver import WebDriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

try:
    import keyring  # type: ignore
except Exception:
    keyring = None  # type: ignore


__all__ = [
    "ask_yes_no",
    "open_amazon_home",
    "get_amazon_credentials",
    "apply_chrome_profile_options",
    "build_chrome_driver_with_profile",
    "get_chrome_driver_with_profile",
    "is_logged_in",
    "start_amazon_browser_session",
]


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


# ---------------------------------
# Credentials & profile helpers
# ---------------------------------


def get_amazon_credentials() -> Tuple[Optional[str], Optional[str]]:
    """Return (email, password) for Amazon login.
    Priority:
      1) AMAZON_EMAIL / AMAZON_PASSWORD from environment (conf.env/.env)
      2) System keyring (password only) for the given AMAZON_EMAIL
    If `AMAZON_EMAIL` is unset, keyring is not queried.
    """
    email = ENV_VARS.get("AMAZON_EMAIL")
    password = ENV_VARS.get("AMAZON_PASSWORD")

    if email and not password and keyring is not None:
        try:
            password = keyring.get_password("amazon", email)
        except Exception:
            # keyring backend may be unavailable in some environments; ignore
            pass

    return email, password


def apply_chrome_profile_options(options) -> None:
    """Augment Selenium Chrome Options with a persisted user profile if configured.
    Uses CHROME_USER_DATA_DIR and CHROME_PROFILE_DIR (optional, defaults to 'Default').
    Safe to call even if variables are not set.
    """
    user_data_dir = ENV_VARS.get("CHROME_USER_DATA_DIR")
    profile_dir = ENV_VARS.get("CHROME_PROFILE_DIR", "Default")
    if user_data_dir:
        # Normalize and ensure the directory exists
        udd_path = Path(user_data_dir).expanduser()
        try:
            udd_path.mkdir(parents=True, exist_ok=True)
        except Exception:
            # If creation fails (e.g., permissions), we still attempt to pass as-is
            pass
        options.add_argument(f"--user-data-dir={str(udd_path)}")
        options.add_argument(f"--profile-directory={profile_dir}")


def build_chrome_driver_with_profile() -> WebDriver:
    """Create a Selenium Chrome driver using the configured persistent profile (if any).
    Convenience wrapper for callers that don't construct Options manually.
    """
    opts = Options()
    apply_chrome_profile_options(opts)
    _apply_visibility_options_to_options(opts)
    opts.add_argument("--disable-notifications")
    # Start maximized only in normal mode to avoid focus stealing flashes
    try:
        mode = (ENV_VARS.get("BROWSER_VISIBILITY") or "normal").lower()
    except Exception:
        mode = "normal"
    if mode == "normal":
        opts.add_argument("--start-maximized")
    # Stability flags to avoid DevToolsActivePort and automation detection issues
    opts.add_argument("--no-first-run")
    opts.add_argument("--no-default-browser-check")
    opts.add_argument("--disable-blink-features=AutomationControlled")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--remote-allow-origins=*")
    # note: 'detach' experimental option removed (unsupported by current ChromeDriver)
    driver = webdriver.Chrome(options=opts)
    # Apply post-launch minimize/offscreen handling
    _apply_visibility_post_create(driver)
    return driver


# -------------------------
# Window visibility controls (optional; default keeps behavior unchanged)
# -------------------------


def _apply_visibility_options_to_options(options) -> None:
    """Apply pre-launch Chrome options based on BROWSER_VISIBILITY.
    Modes:
      - headless  : run without a visible window (Chrome Headless New)
      - normal    : default, visible window
    Always add flags to reduce background throttling.
    """
    mode = (ENV_VARS.get("BROWSER_VISIBILITY") or "offscreen").lower()
    if mode == "headless":
        options.add_argument("--headless=new")  # modern headless mode
    # Reduce throttling when window is backgrounded/minimized
    options.add_argument("--disable-background-timer-throttling")
    options.add_argument("--disable-backgrounding-occluded-windows")
    options.add_argument("--disable-renderer-backgrounding")


def _apply_visibility_post_create(driver) -> None:
    """Apply post-launch tweaks based on BROWSER_VISIBILITY.
    Modes:
      - minimize : immediately minimize the browser window
      - offscreen: move window outside visible area (macOS friendly)
      - normal   : do nothing
    """
    mode = (ENV_VARS.get("BROWSER_VISIBILITY") or "offscreen").lower()
    try:
        if mode == "minimize":
            driver.minimize_window()
        elif mode == "offscreen":
            driver.set_window_position(-2000, 0)
            driver.set_window_size(1280, 800)
    except Exception:
        # Some platforms/drivers may not support these operations
        pass


# -------------------------
# Interstitial/redirect normalizer
# -------------------------


def resolve_amazon_interstitials(driver: WebDriver, timeout: int = 10) -> None:
    """Best-effort cleanup after login: click 'Continue shopping' if present,
    and recover from Amazon 404/redirect pages by navigating to the homepage.
    Non-fatal: all exceptions are swallowed.
    """
    try:
        # Try the classic 'Continue shopping' button
        try:
            btn = WebDriverWait(driver, 3).until(
                EC.presence_of_element_located((By.ID, "continue"))
            )
            try:
                label = (btn.text or "").strip().lower()
            except Exception:
                label = ""
            if not label:
                # Sometimes the button contains a span
                try:
                    label = (btn.get_attribute("value") or "").strip().lower()
                except Exception:
                    pass
            if "continue" in label:
                btn.click()
                WebDriverWait(driver, 5).until(EC.url_contains("amazon."))
        except Exception:
            pass

        # Detect the common 404/invalid page Amazon shows after auth flows
        try:
            page_text = driver.page_source.lower()
            if "not a functioning page" in page_text or "looking for something" in page_text:
                driver.get("https://www.amazon.com/")
                WebDriverWait(driver, timeout).until(
                    EC.presence_of_element_located((By.ID, "nav-logo-sprites"))
                )
        except Exception:
            pass
    except Exception:
        # Never fail the caller
        pass


# -------------------------
# Auto-login helper
# -------------------------


def perform_amazon_login(driver: WebDriver, email: str, password: str, timeout: int = 20) -> bool:
    """Attempt to sign in to Amazon using provided credentials.
    Returns True if login is successful, False otherwise.
    """
    try:
        driver.get("https://www.amazon.com/ap/signin")
        WebDriverWait(driver, timeout).until(EC.presence_of_element_located((By.ID, "ap_email")))
        email_el = driver.find_element(By.ID, "ap_email")
        email_el.clear()
        email_el.send_keys(email)
        try:
            driver.find_element(By.ID, "continue").click()
        except Exception:
            pass
        WebDriverWait(driver, timeout).until(EC.presence_of_element_located((By.ID, "ap_password")))
        pwd_el = driver.find_element(By.ID, "ap_password")
        pwd_el.clear()
        pwd_el.send_keys(password)
        driver.find_element(By.ID, "signInSubmit").click()
        WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located((By.ID, "nav-link-accountList"))
        )
        acc = driver.find_element(By.ID, "nav-link-accountList").text or ""
        if "Sign in" not in acc:
            return True
        driver.get("https://www.amazon.com/")
        return is_logged_in(driver)
    except Exception:
        return False


# -------------------------
# Manual login prompt loop (wait for Enter; ignore any text)
# -------------------------


def _manual_login_prompt_loop(driver: WebDriver, max_checks: int | None = None) -> bool:
    """Waits for user to complete login in the browser.
    On each Enter press we re-check `is_logged_in(driver)`. Any typed text is ignored.
    Returns True when login is detected or False if `max_checks` is exceeded.
    """
    attempts = 0
    while True:
        try:
            if is_logged_in(driver):
                return True
        except Exception:
            pass
        if max_checks is not None and attempts >= max_checks:
            return False
        print("[🔐] Please log into Amazon in the opened Chrome window.")
        print("Press Enter to re-check (input is ignored except for Enter).")
        try:
            input()
        except EOFError:
            # If stdin is not interactive, just try to proceed
            pass
        try:
            open_amazon_home(driver)
        except Exception:
            pass
        attempts += 1


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

    # Normalize and ensure user data directory exists (project-local safe path)
    udd_path = Path(user_data_dir).expanduser()
    udd_path.mkdir(parents=True, exist_ok=True)
    user_data_dir = str(udd_path)

    # Build options for a single, real profile
    options = Options()
    options.add_argument(f"--user-data-dir={user_data_dir}")
    options.add_argument(f"--profile-directory={profile_dir}")
    print(f"[CFG] Using Chrome profile: user_data_dir={user_data_dir} | profile_dir={profile_dir}")

    _apply_visibility_options_to_options(options)
    options.add_argument("--disable-notifications")
    # Avoid start-maximized unless explicitly normal to reduce focus stealing
    try:
        mode = (ENV_VARS.get("BROWSER_VISIBILITY") or "normal").lower()
    except Exception:
        mode = "normal"
    if mode == "normal":
        options.add_argument("--start-maximized")
    # Stability flags to avoid DevToolsActivePort and automation detection issues
    options.add_argument("--no-first-run")
    options.add_argument("--no-default-browser-check")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--no-sandbox")
    options.add_argument("--remote-allow-origins=*")

    try:
        driver = webdriver.Chrome(options=options)
    except SessionNotCreatedException:
        # Do NOT fallback to temporary profile. This causes login loss and duplicate windows.
        raise RuntimeError(
            "Chrome profile is in use or unavailable. Close ALL Chrome windows (Cmd+Q on macOS) and retry."
        )

    if not driver.session_id:
        raise RuntimeError("Browser session has been closed unexpectedly.")

    # Open home and ensure session is alive
    open_amazon_home(driver)
    resolve_amazon_interstitials(driver)

    # One try for auto-login if credentials exist
    if not is_logged_in(driver):
        email, pwd = get_amazon_credentials()
        if email and pwd:
            print(f"[i] Attempting auto-login for {email}…")
            if perform_amazon_login(driver, email, pwd):
                print("[✅] Auto-login successful.")
            else:
                print("[⚠] Auto-login failed.")
        # Regardless of success or failure, normalize to home and continue
        open_amazon_home(driver)
        resolve_amazon_interstitials(driver)

    # Apply post-launch minimize/offscreen, if configured
    _apply_visibility_post_create(driver)
    print("[🟢] Chrome started with user profile (single-session mode)")
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
        WebDriverWait(driver, 7).until(
            EC.presence_of_element_located((By.ID, "nav-link-accountList"))
        )
        # Prefer the line 1 text which usually contains "Hello, sign in" when logged out
        try:
            line1 = driver.find_element(By.ID, "nav-link-accountList-nav-line-1").text or ""
        except Exception:
            line1 = driver.find_element(By.ID, "nav-link-accountList").text or ""
        t = line1.strip().lower()
        if not t:
            # empty text is suspicious -> consider NOT logged in
            print("[ℹ] Account label empty; assuming not logged in.")
            return False
        if "sign in" in t or "signin" in t:
            print("[❌] Not logged into Amazon.")
            return False
        print("[✅] Amazon session is active.")
        return True
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
    user_data_dir = ENV_VARS.get("CHROME_USER_DATA_DIR")
    profile_dir = ENV_VARS.get("CHROME_PROFILE_DIR")

    driver = get_chrome_driver_with_profile(user_data_dir, profile_dir)

    # Try one auto-login, then force homepage either way
    if not is_logged_in(driver):
        email, pwd = get_amazon_credentials()
        if email and pwd:
            print(f"[i] Attempting auto-login for {email}…")
            if perform_amazon_login(driver, email, pwd):
                print("[✅] Auto-login successful.")
            else:
                print("[⚠] Auto-login failed.")
    open_amazon_home(driver)
    resolve_amazon_interstitials(driver)

    print("[✅] Login flow normalized (proceeding with current session).")
    _apply_visibility_post_create(driver)
    return driver
