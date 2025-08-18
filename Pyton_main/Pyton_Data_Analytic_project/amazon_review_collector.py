# amazon_review_collector.py
# -*- coding: utf-8 -*-
"""
Full rewrite: stable Amazon reviews scraper using Selenium (Chrome) + BeautifulSoup.
- Forces Chrome (no browser choice), assumes chromedriver is on PATH.
- Manual login pause (blocking prompt) before scraping.
- Opens canonical reviews URL with sort=recent and English-only filter.
- Robust "Next page" navigation by clicking the real pagination button (no URL hacking).
- Saves every reviews page HTML locally (per ASIN, per page).
- Parses reviews from static HTML with BeautifulSoup (no JS execution assumptions).
- Hard test limiter TEST_PAGE_LIMIT for early debugging.
- Returns a pandas DataFrame with normalized fields.
All comments are in English, as requested.
"""

from __future__ import annotations

import os
import sys
import time
import json
import hashlib
import traceback
from pathlib import Path
from typing import List, Dict, Tuple, Optional

import pandas as pd
from bs4 import BeautifulSoup

# Selenium imports
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import (
    NoSuchElementException,
    TimeoutException,
    WebDriverException,
    StaleElementReferenceException,
    ElementClickInterceptedException,
)
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# -----------------------------
# Config / constants
# -----------------------------

# Save raw HTML pages locally for debug/audit
SAVE_HTML_PAGES: bool = True

# Where to store raw pages
RAW_DIR = Path("Out/_raw_review_pages")

# Default marketplace: "US" or "UK"
DEFAULT_MARKETPLACE = "US"

# Max pages for TEST runs (env override: AMZ_MAX_REVIEW_PAGES_TEST)
# Set to "2" by default per our testing need
TEST_PAGE_LIMIT = int(os.getenv("AMZ_MAX_REVIEW_PAGES_TEST", "2"))

# How long we wait for page loaded and widgets visible (seconds)
PAGE_LOAD_TIMEOUT = 20

# Small waits between actions to reduce anti-bot triggers
SMALL_SLEEP = 0.8

# -----------------------------
# Helpers
# -----------------------------

def _domain(marketplace: str) -> str:
    """Return Amazon domain for marketplace."""
    mk = (marketplace or DEFAULT_MARKETPLACE).upper()
    if mk == "UK":
        return "https://www.amazon.co.uk"
    # default US
    return "https://www.amazon.com"


def _reviews_url(asin: str, marketplace: str, page: int = 1) -> str:
    """
    Build canonical Customer Reviews URL.
    - sort=recent (Most recent)
    - reviewerType=all_reviews
    - filterByLanguage=en_* to keep English-only
    NOTE: We still click the dropdown later to guarantee sort order.
    """
    base = _domain(marketplace)
    # Language filter used by Amazon; en_US works on .com, en_GB on .co.uk
    lang = "en_GB" if (marketplace or DEFAULT_MARKETPLACE).upper() == "UK" else "en_US"
    # We DO NOT rely on pageNumber here for pagination; actual navigation is by clicking Next.
    return (
        f"{base}/product-reviews/{asin}"
        f"/?reviewerType=all_reviews&sortBy=recent&filterByLanguage={lang}&pageNumber={page}"
    )


def _ensure_dirs():
    """Ensure directories exist for raw HTML saves."""
    if SAVE_HTML_PAGES:
        RAW_DIR.mkdir(parents=True, exist_ok=True)


def _slug(s: str) -> str:
    return "".join(ch.lower() if ch.isalnum() else "-" for ch in s).strip("-")


def _hash_text(s: str) -> str:
    return hashlib.md5(s.encode("utf-8", errors="ignore")).hexdigest()


def _wait_visible(driver, by, selector, timeout=PAGE_LOAD_TIMEOUT):
    return WebDriverWait(driver, timeout).until(EC.visibility_of_element_located((by, selector)))


def _sleep(sec: float = SMALL_SLEEP):
    time.sleep(sec)


# -----------------------------
# Chrome setup + login pause
# -----------------------------

def launch_chrome(headless: bool = False) -> webdriver.Chrome:
    """
    Launch Chrome with sensible defaults.
    Requires chromedriver to be compatible with local Chrome.
    """
    options = Options()
    if headless:
        options.add_argument("--headless=new")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    # Make automation a bit less obvious
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)

    try:
        driver = webdriver.Chrome(options=options)
    except WebDriverException as e:
        raise RuntimeError(
            "Failed to start Chrome. Make sure Chrome and chromedriver versions match, "
            "and chromedriver is on PATH. Original error: " + str(e)
        )
    driver.set_page_load_timeout(PAGE_LOAD_TIMEOUT)
    return driver


def pause_for_manual_login(driver: webdriver.Chrome, marketplace: str):
    """
    Open Amazon and allow the user to login manually.
    We block until user confirms in the console.
    """
    home = _domain(marketplace)
    signin_hint = f"{home}/ap/signin"
    # Open reviews root to ensure correct domain + cookies
    driver.get(home)
    print("\n=== Manual login required ===")
    print(f"1) If not redirected automatically, you can open: {signin_hint}")
    print("2) Please complete Amazon login in this Chrome window.")
    print("3) Close any modal/CAPTCHA if shown.")
    input("Press ENTER here when login is complete and you see Amazon homepage...\n")


# -----------------------------
# Sorting + pagination controls
# -----------------------------

def force_sort_most_recent(driver: webdriver.Chrome) -> None:
    """
    Ensure 'Most recent' is selected in the reviews sort dropdown.
    We first try URL param sortBy=recent; this function double-guarantees via UI.
    """
    try:
        # There are two common sort UIs:
        # A) select#sort-order-dropdown (or data-hook="review-star-count-dropdown")
        # B) a fake button that opens aul dropdown with role="listbox".
        # We try the native select first.
        _sleep(0.5)
        select = driver.find_elements(By.ID, "sort-order-dropdown")
        if select:
            select[0].click()
            _sleep(0.3)
            # "Most recent" option usually has value "recent"
            opts = driver.find_elements(By.XPATH, '//select[@id="sort-order-dropdown"]/option[contains(@value,"recent")]')
            if opts:
                opts[0].click()
                _sleep(1.0)
                return

        # Fallback: click the faux dropdown and choose 'Most recent'
        trigger = driver.find_elements(By.XPATH, '//span[@data-action="a-dropdown-button"]//span[contains(@class,"a-dropdown-prompt")]')
        if trigger:
            trigger[0].click()
            _sleep(0.4)
            choice = driver.find_elements(By.XPATH, '//a[contains(@class,"a-dropdown-link") and (contains(., "Most recent") or contains(., "Newest"))]')
            if choice:
                choice[0].click()
                _sleep(1.2)
    except Exception:
        # Non-fatal; sorting via URL may already be applied.
        pass


def english_only_filter_is_on(driver: webdriver.Chrome) -> bool:
    """
    Check that the page state says English filter is active.
    We look for cr-state-object JSON blob and inspect language settings.
    """
    try:
        span = driver.find_element(By.ID, "cr-state-object")
        raw = span.get_attribute("data-state") or "{}"
        data = json.loads(raw)
        # Amazon uses languageOfPreference + filterByLanguage; we accept either hint
        lang_pref = (data.get("languageOfPreference") or "").lower()
        return "en" in lang_pref or data.get("filterByLanguage", "").startswith("en")
    except Exception:
        return False


def click_next_page(driver: webdriver.Chrome) -> bool:
    """
    Click 'Next' in reviews pagination.
    Returns True if navigation started, False if no further pages available.
    """
    try:
        # Typical structure: ul.a-pagination li.a-last a
        ul = driver.find_element(By.XPATH, '//ul[contains(@class,"a-pagination")]')
        # If next is disabled: li.a-disabled.a-last
        disabled = ul.find_elements(By.XPATH, './/li[contains(@class,"a-disabled") and contains(@class,"a-last")]')
        if disabled:
            return False
        nxt = ul.find_elements(By.XPATH, './/li[contains(@class,"a-last")]//a')
        if not nxt:
            return False
        driver.execute_script("arguments[0].scrollIntoView({block:'center'});", nxt[0])
        _sleep(0.2)
        nxt[0].click()
        return True
    except (NoSuchElementException, StaleElementReferenceException, ElementClickInterceptedException):
        return False


# -----------------------------
# Parsing
# -----------------------------

def parse_reviews_from_html(html: str, asin: str, marketplace: str) -> List[Dict]:
    """
    Static parse of review blocks.
    Returns list of dicts.
    """
    soup = BeautifulSoup(html, "html.parser")
    blocks = soup.select('div[data-hook="review"]')
    items: List[Dict] = []

    for b in blocks:
        try:
            review_id = b.get("id") or ""
            title = (b.select_one('a[data-hook="review-title"] span') or {}).get_text(strip=True) if b.select_one('a[data-hook="review-title"] span') else ""
            rating_el = b.select_one('i[data-hook="review-star-rating"] span') or b.select_one('i[data-hook="cmps-review-star-rating"] span')
            rating_text = rating_el.get_text(strip=True) if rating_el else ""
            # Rating like "5.0 out of 5 stars"
            rating = None
            if rating_text:
                try:
                    rating = float(rating_text.split()[0].replace(",", "."))
                except Exception:
                    rating = None
            date_el = b.select_one('span[data-hook="review-date"]')
            review_date = date_el.get_text(strip=True) if date_el else ""
            body = (b.select_one('span[data-hook="review-body"]') or {}).get_text(strip=True) if b.select_one('span[data-hook="review-body"]') else ""
            verified = bool(b.select_one('span[data-hook="avp-badge"]'))

            helpful = None
            help_el = b.select_one('span[data-hook="helpful-vote-statement"]')
            if help_el:
                txt = help_el.get_text(strip=True)
                # "12 people found this helpful" or "One person found this helpful"
                try:
                    if txt.lower().startswith("one"):
                        helpful = 1
                    else:
                        helpful = int("".join(ch for ch in txt.split()[0] if ch.isdigit()))
                except Exception:
                    helpful = None

            # Fallback dedupe hash if no review_id
            fallback_key = _hash_text(f"{asin}|{review_date}|{rating}|{title}|{body[:80]}")

            items.append(
                {
                    "asin": asin,
                    "marketplace": marketplace.upper(),
                    "review_id": review_id or f"FALLBACK-{fallback_key}",
                    "review_date_raw": review_date,
                    "rating": rating,
                    "title": title,
                    "body": body,
                    "verified_purchase": verified,
                    "helpful_votes": helpful,
                }
            )
        except Exception:
            # Keep scraping even if one block fails
            continue

    return items


# -----------------------------
# ASIN-level collection
# -----------------------------

def _save_page(asin: str, page_idx: int, html: str):
    if not SAVE_HTML_PAGES:
        return
    _ensure_dirs()
    fname = RAW_DIR / f"{asin}_p{page_idx}.html"
    fname.write_text(html, encoding="utf-8", errors="ignore")


def _wait_reviews_loaded(driver: webdriver.Chrome):
    """Wait until review container appears."""
    _wait_visible(driver, By.ID, "cm_cr-review_list", timeout=PAGE_LOAD_TIMEOUT)


def collect_reviews_for_one_asin(
    driver: webdriver.Chrome,
    asin: str,
    marketplace: str,
    max_pages: int,
    max_reviews: int,
) -> Tuple[List[Dict], int]:
    """
    Navigate through 'Most recent' review pages by clicking Next; parse each page.
    Returns (reviews_list, pages_scraped).
    """
    pages_done = 0
    collected: List[Dict] = []

    # Open page 1
    url = _reviews_url(asin, marketplace, page=1)
    driver.get(url)

    # Force 'Most recent' and English filter if possible
    try:
        _wait_reviews_loaded(driver)
    except TimeoutException:
        # Sometimes lazy load; try small scroll
        driver.execute_script("window.scrollTo(0, 600);")
        _sleep(1.0)
        _wait_reviews_loaded(driver)

    # Ensure sorting
    force_sort_most_recent(driver)
    _sleep(0.6)

    # If language filter isn't English, reload with explicit filter param (already in URL but double check)
    if not english_only_filter_is_on(driver):
        driver.get(_reviews_url(asin, marketplace, page=1))
        _wait_reviews_loaded(driver)
        force_sort_most_recent(driver)
        _sleep(0.5)

    # Paginate
    while pages_done < max_pages and (len(collected) < max_reviews):
        # Wait list visible
        _wait_reviews_loaded(driver)
        _sleep(0.4)

        # Save raw page
        html = driver.page_source
        pages_done += 1
        _save_page(asin, pages_done, html)

        # Parse
        page_items = parse_reviews_from_html(html, asin, marketplace)
        collected.extend(page_items)

        # Early stop if we've got enough reviews
        if len(collected) >= max_reviews:
            break

        # Try next page
        moved = click_next_page(driver)
        if not moved:
            break

        # Wait for navigation (either URL changes or list refreshed)
        try:
            WebDriverWait(driver, PAGE_LOAD_TIMEOUT).until(
                EC.staleness_of(driver.find_element(By.ID, "cm_cr-review_list"))
            )
        except Exception:
            pass

        # Then list becomes visible again
        _wait_reviews_loaded(driver)
        _sleep(0.4)

    return collected[:max_reviews], pages_done


# -----------------------------
# Public API
# -----------------------------

def collect_reviews(
    asins: List[str],
    max_reviews_per_asin: int = 500,
    marketplace: str = DEFAULT_MARKETPLACE,
) -> pd.DataFrame:
    """
    Main entry used by our pipeline.
    - Launches Chrome
    - Pauses for manual login
    - Iterates ASINs, scrapes up to TEST_PAGE_LIMIT pages (override via env) or until max_reviews_per_asin
    - Returns a DataFrame with deduplication across all ASINs

    Columns:
        asin, marketplace, review_id, review_date_raw, rating, title, body,
        verified_purchase, helpful_votes
    """
    _ensure_dirs()
    mk = (marketplace or DEFAULT_MARKETPLACE).upper()

    # Decide page cap: for MVP/testing we use TEST_PAGE_LIMIT
    max_pages = max(1, TEST_PAGE_LIMIT)

    driver = launch_chrome(headless=False)
    try:
        pause_for_manual_login(driver, mk)

        all_items: List[Dict] = []
        for idx, asin in enumerate(asins, start=1):
            print(f"[{idx}/{len(asins)}] ASIN={asin}: collecting (up to {max_pages} pages, {max_reviews_per_asin} reviews)...")
            try:
                items, pages_done = collect_reviews_for_one_asin(
                    driver=driver,
                    asin=asin,
                    marketplace=mk,
                    max_pages=max_pages,
                    max_reviews=max_reviews_per_asin,
                )
                print(f"  ✓ pages scraped: {pages_done}, reviews parsed: {len(items)}")
                all_items.extend(items)
            except Exception as e:
                print(f"  ✗ failed for ASIN={asin}: {e}")
                traceback.print_exc()
                # Keep going with next ASIN
                continue

        if not all_items:
            return pd.DataFrame(columns=[
                "asin","marketplace","review_id","review_date_raw","rating","title",
                "body","verified_purchase","helpful_votes"
            ])

        df = pd.DataFrame(all_items)

        # Deduplicate: first by (asin, review_id); fallback on hash if review_id starts with FALLBACK-
        # This keeps the earliest occurrence (stable order).
        df["_key"] = df.apply(
            lambda r: (r["asin"], r["review_id"]) if not str(r["review_id"]).startswith("FALLBACK-")
            else (r["asin"], _hash_text(f'{r["asin"]}|{r["review_date_raw"]}|{r["rating"]}|{r["title"]}|{r["body"][:80]}')),
            axis=1
        )
        df = df.drop_duplicates(subset="_key", keep="first").drop(columns=["_key"]).reset_index(drop=True)
        return df

    finally:
        try:
            driver.quit()
        except Exception:
            pass


# -----------------------------
# CLI test hook
# -----------------------------

if __name__ == "__main__":
    # Quick manual test:
    #   python amazon_review_collector.py B09DSXQZ37 B08MC6PLT4 --mk US --max 200
    import argparse

    parser = argparse.ArgumentParser(description="Amazon reviews collector (Most recent, English)")
    parser.add_argument("asins", nargs="+", help="List of ASINs")
    parser.add_argument("--mk", default=DEFAULT_MARKETPLACE, help="Marketplace: US or UK")
    parser.add_argument("--max", type=int, default=200, help="Max reviews per ASIN")
    args = parser.parse_args()

    df = collect_reviews(args.asins, max_reviews_per_asin=args.max, marketplace=args.mk)
    out = Path("Out/reviews_sample.csv")
    out.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out, index=False)
    print(f"Saved {len(df)} rows -> {out}")