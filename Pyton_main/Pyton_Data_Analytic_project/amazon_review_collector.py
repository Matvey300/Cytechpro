# amazon_review_collector.py
# All comments in English.

from __future__ import annotations

import os
import re
import time
import shutil
import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import Iterable, List, Dict, Any, Optional, Tuple

import pandas as pd
from bs4 import BeautifulSoup

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

# ============================== Config ======================================

# Marketplace base URLs
MARKET_BASE = {
    "US": "https://www.amazon.com",
    "UK": "https://www.amazon.co.uk",
}

# Gentle pacing
PAGE_DELAY_SEC = 1.2

# Safety cap for review pages per ASIN (Selenium next-clicks)
MAX_REVIEW_PAGES = 50

# Test page limit (first N pages only). Default 2 for your current tests.
# You can override via env: AMZ_MAX_REVIEW_PAGES_TEST=2 (or set to 0 to disable limit).
TEST_PAGE_LIMIT = int(os.getenv("AMZ_MAX_REVIEW_PAGES_TEST", "2"))

# Output root for HTML snapshots
HTML_ROOT = Path("Out") / "html"

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

# ============================== Login helpers ===============================

def _is_captcha(driver) -> bool:
    """Heuristic check if we are on a CAPTCHA page."""
    url = (driver.current_url or "").lower()
    if "captcha" in url:
        return True
    try:
        body = driver.find_element(By.TAG_NAME, "body").text.lower()
        return "enter the characters you see" in body or "type the characters" in body
    except Exception:
        return False


def _looks_signed_in(driver) -> bool:
    """Detect if account nav no longer shows 'Sign in'."""
    try:
        el = driver.find_element(By.ID, "nav-link-accountList")
        txt = (el.text or "").strip().lower()
        return ("sign in" not in txt) and ("hello" in txt or "account" in txt or "returns" in txt)
    except Exception:
        return False


def _require_manual_login(driver, base_url: str):
    """
    Hard stop until the user confirms login is complete.
    We keep looping until user confirms and we don't see a CAPTCHA.
    """
    signin_url = f"{base_url}/ap/signin"
    print("\n[LOGIN] Opening Amazon sign-in page in the browser…")
    driver.get(signin_url)

    try:
        WebDriverWait(driver, 20).until(
            EC.any_of(
                EC.presence_of_element_located((By.ID, "ap_email")),
                EC.presence_of_element_located((By.ID, "ap_password")),
                EC.presence_of_element_located((By.ID, "nav-link-accountList")),
                EC.presence_of_element_located((By.TAG_NAME, "body")),
            )
        )
    except Exception:
        pass

    while True:
        if _is_captcha(driver):
            print("⚠️  CAPTCHA detected. Please solve it in the browser.")
        ans = input("[LOGIN] After you finish signing in, type 'y' to continue, 'r' to reload login page, or 's' to skip login: ").strip().lower()
        if ans == "r":
            driver.get(signin_url)
            continue
        if ans == "s":
            print("[LOGIN] Skipping login. Proceeding unauthenticated.")
            break
        if ans == "y":
            try:
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.ID, "nav-link-accountList"))
                )
            except Exception:
                pass
            time.sleep(2.0)
            if _is_captcha(driver):
                print("⚠️  You appear to be on a CAPTCHA page. Solve it and try 'y' again.")
                continue
            # If we cannot confirm, we still proceed as requested by the user
            if _looks_signed_in(driver):
                print("[LOGIN] Login detected. Continuing…")
            else:
                print("ℹ️  Could not confirm login heuristically. Continuing anyway.")
            break

# ============================== URL builders ================================

def _product_url(base: str, asin: str) -> str:
    return f"{base}/dp/{asin}"

def _reviews_root_url(base: str, asin: str) -> str:
    # Amazon manages paging; we start at the recent sort root.
    return f"{base}/product-reviews/{asin}/?sortBy=recent"

# ============================== Regex helpers ===============================

STAR_RE = re.compile(r"([0-5](?:\.\d)?) out of 5")
PRICE_RE = re.compile(r"([€£$])\s*([\d\.,]+)")

def _parse_star(text: str) -> Optional[float]:
    if not text:
        return None
    m = STAR_RE.search(text)
    try:
        return float(m.group(1)) if m else None
    except Exception:
        return None

def _parse_helpful(text: str) -> int:
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
    if not text:
        return ""
    parts = re.split(r"on\s+", text, maxsplit=1, flags=re.IGNORECASE)
    return parts[-1].strip() if parts else text.strip()

def _parse_price_text(txt: str) -> Tuple[Optional[float], Optional[str]]:
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

def _extract_bsr_from_text(txt: str) -> Tuple[Optional[int], Optional[str]]:
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

# ============================== HTML save/parse =============================

def _save_html(path: Path, html: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(html)

def _parse_reviews_from_html(html: str, asin: str) -> List[Dict[str, Any]]:
    """Parse reviews from a saved HTML source using BeautifulSoup."""
    out: List[Dict[str, Any]] = []
    soup = BeautifulSoup(html, "html.parser")
    cards = soup.select('div[data-hook="review"]')
    for card in cards:
        try:
            review_id = card.get("id") or card.get("data-review-id")
            # rating
            rating_text = ""
            star_span = card.select_one('i[data-hook="review-star-rating"] span') or \
                        card.select_one('i[data-hook="cmps-review-star-rating"] span')
            if star_span and star_span.text:
                rating_text = star_span.text.strip()
            rating = _parse_star(rating_text)

            # date
            date_el = card.select_one('span[data-hook="review-date"]')
            review_date = _clean_review_date(date_el.text.strip()) if date_el and date_el.text else ""

            # title
            title_el = card.select_one('a[data-hook="review-title"] span')
            review_title = title_el.text.strip() if title_el and title_el.text else ""

            # text
            text_el = card.select_one('span[data-hook="review-body"]')
            review_text = text_el.text.strip() if text_el and text_el.text else ""

            # verified
            avp = card.select_one('span[data-hook="avp-badge"]')
            verified = bool(avp and "Verified Purchase" in avp.text)

            # helpful
            hv = card.select_one('span[data-hook="helpful-vote-statement"]')
            helpful_votes = _parse_helpful(hv.text.strip()) if hv and hv.text else 0

            out.append({
                "asin": asin,
                "review_id": review_id,
                "review_date": review_date,
                "review_title": review_title,
                "review_text": review_text,
                "rating": rating,
                "verified": verified,
                "helpful_votes": helpful_votes,
            })
        except Exception:
            continue
    return out

# ============================== Product meta ================================

def _fetch_product_meta(driver: webdriver.Chrome, base_url: str, asin: str) -> dict:
    """Get price and BSR from /dp/<ASIN>."""
    url = _product_url(base_url, asin)
    meta = {"asin": asin, "buybox_price": None, "currency": None, "bsr_rank": None, "bsr_path": None}
    try:
        driver.get(url)
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

        # Price
        price_txt = ""
        try:
            price_txt = driver.find_element(By.CSS_SELECTOR, "#corePriceDisplay_desktop_feature_div span.a-offscreen").text.strip()
        except Exception:
            pass
        if not price_txt:
            try:
                price_txt = driver.find_element(By.CSS_SELECTOR, "span.a-offscreen").text.strip()
            except Exception:
                pass
        price, cur = _parse_price_text(price_txt)
        if price is not None:
            meta["buybox_price"] = price
            meta["currency"] = cur

        # BSR
        bsr_txt = ""
        try:
            blk = driver.find_element(By.ID, "detailBullets_feature_div").text
            if "Best Sellers Rank" in blk or "#" in blk:
                for line in blk.splitlines():
                    if "Best Sellers Rank" in line or "#" in line:
                        bsr_txt = line
                        break
        except Exception:
            pass
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
        pass
    return meta

# ============================== Next page ===================================

def _click_next_reviews_page(driver: webdriver.Chrome) -> bool:
    """
    Click the 'Next' pagination link on the reviews page.
    Returns True if clicked, False if at the last page.
    """
    try:
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "ul.a-pagination"))
        )
    except TimeoutException:
        return False

    try:
        last_li = driver.find_element(By.CSS_SELECTOR, "ul.a-pagination li.a-last")
    except NoSuchElementException:
        return False

    cls = (last_li.get_attribute("class") or "").lower()
    if "a-disabled" in cls:
        return False

    try:
        link = last_li.find_element(By.TAG_NAME, "a")
        driver.execute_script("arguments[0].click();", link)
        time.sleep(PAGE_DELAY_SEC)
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, 'div[data-hook="review"]'))
        )
        return True
    except Exception:
        return False

# ============================== Public API ==================================

def collect_reviews(asins: Iterable[str], max_reviews: int, marketplace: str) -> pd.DataFrame:
    """
    Selenium collector that:
      - pauses for manual login confirmation,
      - saves every reviews page to Out/html/<MARKET>/<ASIN>/ASIN_p{N}.html,
      - parses reviews from saved HTML,
      - collects price/BSR once per ASIN.

    Returns DataFrame with at least:
      asin, review_id, review_date, review_title, review_text, rating,
      verified, helpful_votes, buybox_price, currency, bsr_rank, bsr_path
    """
    base = MARKET_BASE.get((marketplace or "US").upper(), MARKET_BASE["US"])
    market_key = (marketplace or "US").upper()

    driver = _make_driver()

    try:
        # Hard stop for manual login before scraping
        _require_manual_login(driver, base)

        all_rows: List[Dict[str, Any]] = []

        for raw_asin in asins:
            asin = str(raw_asin).strip()
            if not asin:
                continue

            # --- Product meta once
            meta = _fetch_product_meta(driver, base, asin)

            # --- Prepare folder for HTML dumps
            asin_dir = HTML_ROOT / market_key / asin
            asin_dir.mkdir(parents=True, exist_ok=True)

            # --- Open root reviews
            root = _reviews_root_url(base, asin)
            try:
                driver.get(root)
            except WebDriverException:
                continue

            try:
                WebDriverWait(driver, 15).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, 'div[data-hook="review"]'))
                )
            except TimeoutException:
                # Save whatever we have (for debugging)
                _save_html(asin_dir / f"{asin}_p1.html", driver.page_source)
                continue

            collected = 0
            page_idx = 1
            pages_saved = 0
            seen_ids: set[str] = set()

            while collected < max_reviews and page_idx <= MAX_REVIEW_PAGES:
                time.sleep(PAGE_DELAY_SEC)

                # Save current page HTML
                html_path = asin_dir / f"{asin}_p{page_idx}.html"
                _save_html(html_path, driver.page_source)
                pages_saved += 1

                # Parse from saved HTML
                rows = _parse_reviews_from_html((driver.page_source or ""), asin)
                if not rows:
                    break

                for r in rows:
                    # attach product meta
                    r.setdefault("buybox_price", meta.get("buybox_price"))
                    r.setdefault("currency", meta.get("currency"))
                    r.setdefault("bsr_rank", meta.get("bsr_rank"))
                    r.setdefault("bsr_path", meta.get("bsr_path"))

                    rid = str(r.get("review_id") or "")
                    if rid and rid in seen_ids:
                        continue
                    if rid:
                        seen_ids.add(rid)

                    all_rows.append(r)
                    collected += 1
                    if collected >= max_reviews:
                        break

                if collected >= max_reviews:
                    break

                # Test limiter: stop after first N pages (default 2)
                if TEST_PAGE_LIMIT > 0 and page_idx >= TEST_PAGE_LIMIT:
                    break

                # Move to next page by clicking "Next"
                page_idx += 1
                moved = _click_next_reviews_page(driver)
                if not moved:
                    break

        # ---- Normalize to DataFrame and enforce schema ----
        df = pd.DataFrame(all_rows)
        required = [
            "asin", "review_id", "review_date", "review_title", "review_text",
            "rating", "verified", "helpful_votes",
            "buybox_price", "currency", "bsr_rank", "bsr_path"
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