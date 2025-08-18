# All comments in English.

from __future__ import annotations

import re
import time
import shutil
import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import Iterable, List, Dict, Any, Optional

import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    NoSuchElementException,
    TimeoutException,
    WebDriverException,
)


# ============================== Constants ===================================

# Marketplace base URLs
MARKET_BASE = {
    "US": "https://www.amazon.com",
    "UK": "https://www.amazon.co.uk",
}

# Gentle pacing to reduce bot suspicion (seconds)
PAGE_DELAY_SEC = 1.2

# Safety cap for review pages per ASIN
MAX_REVIEW_PAGES = 50

# Enable manual sign-in before scraping by setting AMZ_ENABLE_LOGIN=1 in env.
import os
ENABLE_LOGIN = os.getenv("AMZ_ENABLE_LOGIN", "0") in {"1", "true", "yes"}


# ============================== Chrome bootstrap ============================

@contextmanager
def _temp_profile_dir():
    """Create an isolated temporary Chrome profile directory; auto-clean on exit."""
    d = tempfile.mkdtemp(prefix="amz_chrome_profile_")
    try:
        yield d
    finally:
        try:
            shutil.rmtree(d, ignore_errors=True)
        except Exception:
            pass


def _chrome_options_for_profile(profile_dir: str) -> ChromeOptions:
    """Build ChromeOptions for an isolated profile."""
    opts = ChromeOptions()
    # Headed is safer for Amazon; enable headless only if you must:
    # opts.add_argument("--headless=new")
    opts.add_argument(f"--user-data-dir={profile_dir}")
    opts.add_argument("--profile-directory=Default")
    opts.add_argument("--no-first-run")
    opts.add_argument("--no-default-browser-check")
    opts.add_argument("--disable-features=Translate,PasswordManagerOnboarding")
    opts.add_argument("--disable-notifications")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--window-size=1280,1200")
    return opts


def _make_driver() -> webdriver.Chrome:
    """Create a Chrome WebDriver with a temporary isolated profile."""
    ctx = _temp_profile_dir()
    profile_dir = ctx.__enter__()

    class _CtxChrome(webdriver.Chrome):
        def quit(self, *args, **kwargs):
            try:
                super().quit(*args, **kwargs)
            finally:
                try:
                    ctx.__exit__(None, None, None)
                except Exception:
                    pass

    return _CtxChrome(options=_chrome_options_for_profile(profile_dir))


# ============================== Utilities ===================================

STAR_RE = re.compile(r"([0-5](?:\.\d)?) out of 5")
PRICE_RE = re.compile(r"([€£$])\s*([\d\.,]+)")

def _parse_star(text: str) -> Optional[float]:
    """Extract 'x out of 5' → float(x)."""
    if not text:
        return None
    m = STAR_RE.search(text)
    try:
        return float(m.group(1)) if m else None
    except Exception:
        return None


def _parse_helpful(text: str) -> int:
    """Parse 'One person found this helpful' or '2,345 people found this helpful' → int."""
    if not text:
        return 0
    text = text.replace("\xa0", " ").strip()
    if "One person" in text:
        return 1
    nums = re.findall(r"[\d,]+", text)
    if nums:
        try:
            return int(nums[0].replace(",", ""))
        except Exception:
            return 0
    return 0


def _clean_review_date(text: str) -> str:
    """
    Keep only the date portion after 'on ' (works for en-US/en-UK).
    Examples:
      'Reviewed in the United States on July 1, 2025'  -> 'July 1, 2025'
      'Reviewed in the United Kingdom on 12 May 2024'  -> '12 May 2024'
    """
    if not text:
        return ""
    parts = re.split(r"on\s+", text, maxsplit=1, flags=re.IGNORECASE)
    return parts[-1].strip() if parts else text.strip()


def _parse_price_text(txt: str) -> tuple[Optional[float], Optional[str]]:
    """Parse text like '$29.99' or '£15.99' -> (29.99, 'USD/GBP/EUR')."""
    if not txt:
        return None, None
    m = PRICE_RE.search(txt.replace("\xa0", " "))
    if not m:
        return None, None
    sym, num = m.group(1), m.group(2)
    num = num.replace(",", "")
    try:
        val = float(num)
    except Exception:
        return None, None
    cur = {"$": "USD", "£": "GBP", "€": "EUR"}.get(sym)
    return val, cur


def _extract_bsr_from_text(txt: str) -> tuple[Optional[int], Optional[str]]:
    """Extract Best Sellers Rank and category path from mixed text."""
    if not txt:
        return None, None
    m = re.search(r"#\s*([\d,]+)", txt)
    rank = int(m.group(1).replace(",", "")) if m else None
    path = None
    m2 = re.search(r"in\s+([^\(]+)", txt)
    if m2:
        path = m2.group(1).strip()
        path = re.sub(r"\s*\(.*$", "", path).strip()
    return rank, path


def _product_url(base: str, asin: str) -> str:
    return f"{base}/dp/{asin}"


def _reviews_root_url(base: str, asin: str) -> str:
    # Start at the root reviews page (Amazon manages paging client-side)
    return f"{base}/product-reviews/{asin}/?sortBy=recent"


# ============================== Login (optional) ============================

def _optional_manual_login(driver: webdriver.Chrome, base_url: str) -> None:
    """
    Optional manual login flow with proper waits. Enabled via AMZ_ENABLE_LOGIN=1.
    We never collect credentials; the user completes sign-in in the opened window.
    """
    if not ENABLE_LOGIN:
        return

    signin_url = f"{base_url}/ap/signin"
    print("\n[INFO] Opening Amazon sign-in page. Complete login in the browser window.")
    driver.get(signin_url)

    # Wait for the email field or page stability (not fatal if layout is different).
    try:
        WebDriverWait(driver, 20).until(
            EC.any_of(
                EC.presence_of_element_located((By.ID, "ap_email")),
                EC.presence_of_element_located((By.ID, "ap_password")),
                EC.presence_of_element_located((By.ID, "nav-link-accountList")),
            )
        )
    except TimeoutException:
        pass

    input("[INFO] Press Enter here AFTER you have successfully signed in (or to continue anyway)... ")
    # Give Amazon a moment to settle (MFA redirects, etc.)
    time.sleep(3.0)


# ============================== Product meta =================================

def _fetch_product_meta(driver: webdriver.Chrome, base_url: str, asin: str) -> dict:
    """
    Open /dp/<ASIN> and extract:
      - buybox_price (float)
      - currency ('USD'/'GBP'/...)
      - bsr_rank (Int) and bsr_path (str)
    """
    url = _product_url(base_url, asin)
    meta = {"asin": asin, "buybox_price": None, "currency": None, "bsr_rank": None, "bsr_path": None}
    try:
        driver.get(url)
        # Wait for either price block or page body presence
        try:
            WebDriverWait(driver, 15).until(
                EC.any_of(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "#corePriceDisplay_desktop_feature_div")),
                    EC.presence_of_element_located((By.TAG_NAME, "body")),
                )
            )
        except TimeoutException:
            pass
        time.sleep(0.8)

        # --- Price: try core price block first ---
        price_txt = ""
        try:
            price_txt = driver.find_element(By.CSS_SELECTOR, "#corePriceDisplay_desktop_feature_div span.a-offscreen").text.strip()
        except Exception:
            pass
        if not price_txt:
            # Fallback: any visible .a-offscreen (still fairly reliable)
            try:
                price_txt = driver.find_element(By.CSS_SELECTOR, "span.a-offscreen").text.strip()
            except Exception:
                pass
        price, cur = _parse_price_text(price_txt)
        if price is not None:
            meta["buybox_price"] = price
            meta["currency"] = cur

        # --- BSR: multiple placements across layouts ---
        bsr_txt = ""
        # 1) Detail bullets block
        try:
            blk = driver.find_element(By.ID, "detailBullets_feature_div").text
            if "Best Sellers Rank" in blk or "#" in blk:
                for line in blk.splitlines():
                    if "Best Sellers Rank" in line or "#" in line:
                        bsr_txt = line
                        break
        except Exception:
            pass
        # 2) Old technical table
        if not bsr_txt:
            try:
                tbl = driver.find_element(By.ID, "productDetails_detailBullets_sections1").text
                if "Best Sellers Rank" in tbl or "#" in tbl:
                    for line in tbl.splitlines():
                        if "Best Sellers Rank" in line or "#" in line:
                            bsr_txt = line
                            break
            except Exception:
                pass
        # 3) Last-resort: scan full page text
        if not bsr_txt:
            try:
                body_txt = driver.find_element(By.TAG_NAME, "body").text
                m = re.search(r"Best Sellers Rank.*?#\s*[\d,]+\s+in\s+[^\n]+", body_txt, flags=re.IGNORECASE | re.DOTALL)
                if m:
                    bsr_txt = m.group(0)
            except Exception:
                pass

        rank, path = _extract_bsr_from_text(bsr_txt)
        meta["bsr_rank"] = rank
        meta["bsr_path"] = path

    except Exception:
        # swallow meta errors; reviews scraping can still continue
        pass
    return meta


# ============================== Reviews parsing ==============================

def _parse_reviews_from_dom(driver: webdriver.Chrome, asin: str) -> List[Dict[str, Any]]:
    """Parse currently loaded reviews page into list of dicts."""
    rows: List[Dict[str, Any]] = []
    cards = driver.find_elements(By.CSS_SELECTOR, 'div[data-hook="review"]')
    for card in cards:
        try:
            review_id = card.get_attribute("id") or card.get_attribute("data-review-id") or None

            # rating
            rating_text = ""
            try:
                rating_text = card.find_element(By.CSS_SELECTOR, 'i[data-hook="review-star-rating"] span').text.strip()
            except NoSuchElementException:
                try:
                    rating_text = card.find_element(By.CSS_SELECTOR, 'i[data-hook="cmps-review-star-rating"] span').text.strip()
                except NoSuchElementException:
                    rating_text = ""
            rating = _parse_star(rating_text)

            # date
            try:
                review_date = _clean_review_date(card.find_element(By.CSS_SELECTOR, 'span[data-hook="review-date"]').text.strip())
            except NoSuchElementException:
                review_date = ""

            # text
            try:
                body_el = card.find_element(By.CSS_SELECTOR, 'span[data-hook="review-body"]')
                review_text = body_el.text.strip()
            except NoSuchElementException:
                review_text = ""

            # verified
            try:
                ver_el = card.find_element(By.CSS_SELECTOR, 'span[data-hook="avp-badge"]')
                verified = "Verified Purchase" in ver_el.text
            except NoSuchElementException:
                verified = False

            # helpful votes
            try:
                hv_text = card.find_element(By.CSS_SELECTOR, 'span[data-hook="helpful-vote-statement"]').text.strip()
                helpful_votes = _parse_helpful(hv_text)
            except NoSuchElementException:
                helpful_votes = 0

            rows.append({
                "asin": asin,
                "review_id": review_id,
                "review_date": review_date,
                "rating": rating,
                "review_text": review_text,
                "verified": verified,
                "helpful_votes": helpful_votes,
            })
        except WebDriverException:
            continue
    return rows


def _click_next_reviews_page(driver: webdriver.Chrome) -> bool:
    """
    Click the 'Next' pagination link on the reviews page.
    Returns True if clicked (i.e., next page exists), False if at the last page.
    Amazon uses 'li.a-last' item with anchor when a next page is available.
    """
    try:
        # Wait for pagination container to be present or timeout
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "ul.a-pagination"))
        )
    except TimeoutException:
        # No pagination visible → treat as single page
        return False

    # Detect 'Next' li
    try:
        last_li = driver.find_element(By.CSS_SELECTOR, "ul.a-pagination li.a-last")
    except NoSuchElementException:
        return False

    # If it's disabled or has no link, there is no next page
    cls = last_li.get_attribute("class") or ""
    if "a-disabled" in cls.lower():
        return False

    # Otherwise, click the anchor inside
    try:
        link = last_li.find_element(By.TAG_NAME, "a")
        driver.execute_script("arguments[0].click();", link)
        # Wait for some sign of page change: presence of first review or pagination refresh
        time.sleep(PAGE_DELAY_SEC)
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, 'div[data-hook="review"]'))
        )
        return True
    except Exception:
        return False


# ============================== Public API ===================================

def collect_reviews(asins: Iterable[str], max_reviews: int, marketplace: str) -> pd.DataFrame:
    """
    Selenium-only collector with optional manual login and real 'Next' clicks.
    Steps per ASIN:
      1) (optional) Manual sign-in if AMZ_ENABLE_LOGIN=1.
      2) Read product meta (price, BSR) from /dp/<ASIN>.
      3) Open /product-reviews/<ASIN> and iterate pages by clicking 'Next'.
    Returns DataFrame with columns:
      asin, review_id, review_date, rating, review_text, verified, helpful_votes,
      buybox_price, currency, bsr_rank, bsr_path
    """
    base = MARKET_BASE.get((marketplace or "US").upper(), MARKET_BASE["US"])
    driver = _make_driver()

    try:
        # 0) Optional sign-in (with proper waits)
        _optional_manual_login(driver, base)

        all_rows: List[Dict[str, Any]] = []

        for raw_asin in asins:
            asin = str(raw_asin).strip()
            if not asin:
                continue

            # 1) Product meta once per ASIN
            meta = _fetch_product_meta(driver, base, asin)

            # 2) Reviews pagination with real "Next" clicks
            collected = 0
            seen_ids: set[str] = set()

            # Open root reviews page once
            root = _reviews_root_url(base, asin)
            try:
                driver.get(root)
            except WebDriverException:
                continue

            # Ensure first batch of reviews loaded
            try:
                WebDriverWait(driver, 15).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, 'div[data-hook="review"]'))
                )
            except TimeoutException:
                # No reviews block → skip
                continue

            page_idx = 1
            while collected < max_reviews and page_idx <= MAX_REVIEW_PAGES:
                time.sleep(PAGE_DELAY_SEC)

                rows = _parse_reviews_from_dom(driver, asin)
                if not rows:
                    break

                for r in rows:
                    # attach product meta to each review row
                    r.setdefault("buybox_price", meta.get("buybox_price"))
                    r.setdefault("currency", meta.get("currency"))
                    r.setdefault("bsr_rank", meta.get("bsr_rank"))
                    r.setdefault("bsr_path", meta.get("bsr_path"))

                    rid = str(r.get("review_id") or "")
                    if rid and rid in seen_ids:
                        continue

                    all_rows.append(r)
                    if rid:
                        seen_ids.add(rid)

                    collected += 1
                    if collected >= max_reviews:
                        break

                if collected >= max_reviews:
                    break

                # Try to go to the next page by clicking 'Next'
                page_idx += 1
                moved = _click_next_reviews_page(driver)
                if not moved:
                    break  # last page reached

        # ---- Normalize to DataFrame and enforce schema ----
        df = pd.DataFrame(all_rows)

        # Ensure all expected columns exist
        required = [
            "asin", "review_id", "review_date", "rating", "review_text",
            "verified", "helpful_votes", "buybox_price", "currency", "bsr_rank", "bsr_path"
        ]
        for c in required:
            if c not in df.columns:
                df[c] = None

        # Types
        df["rating"] = pd.to_numeric(df["rating"], errors="coerce")
        df["verified"] = df["verified"].astype("boolean")
        df["helpful_votes"] = pd.to_numeric(df["helpful_votes"], errors="coerce").fillna(0).astype("Int64")
        df["buybox_price"] = pd.to_numeric(df["buybox_price"], errors="coerce")
        df["bsr_rank"] = pd.to_numeric(df["bsr_rank"], errors="coerce").astype("Int64")

        # Deduplicate: (asin, review_id) primary; fallback (asin, date, rating, hash(text))
        if not df.empty:
            key1 = df["asin"].astype(str) + "|" + df["review_id"].astype(str)
            df = df.loc[~key1.duplicated(keep="first")].reset_index(drop=True)

            key2 = (
                df["asin"].astype(str) + "|" +
                df["review_date"].astype(str) + "|" +
                df["rating"].astype(str) + "|" +
                df["review_text"].astype(str).map(lambda t: str(hash(t)))
            )
            df = df.loc[~key2.duplicated(keep="first")].reset_index(drop=True)

        return df

    finally:
        try:
            driver.quit()
        except Exception:
            pass