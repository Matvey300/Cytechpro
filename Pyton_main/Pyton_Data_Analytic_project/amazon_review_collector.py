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
from selenium.common.exceptions import NoSuchElementException, WebDriverException


# ----------------------------- Constants ------------------------------------

# Marketplace base URLs
MARKET_BASE = {
    "US": "https://www.amazon.com",
    "UK": "https://www.amazon.co.uk",
}

# Gentle pacing to reduce bot suspicion (seconds)
PAGE_DELAY_SEC = 1.0

# Max pages to traverse for reviews per ASIN (safety cap)
MAX_REVIEW_PAGES = 50


# ----------------------------- Chrome bootstrap -----------------------------

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
    # Headed is safer for Amazon; enable headless if you really need it:
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


# ----------------------------- Parsing utils --------------------------------

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
    """
    Extract Best Sellers Rank and category path from mixed text.
    Returns (rank:int or None, path:str or None).
    """
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


def _reviews_url(base: str, asin: str, page: int) -> str:
    return f"{base}/product-reviews/{asin}/?sortBy=recent&pageNumber={page}"


# ----------------------------- Product meta ---------------------------------

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
        time.sleep(1.0)

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


# ----------------------------- Reviews parsing ------------------------------

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


# ----------------------------- Public API -----------------------------------

def collect_reviews(asins: Iterable[str], max_reviews: int, marketplace: str) -> pd.DataFrame:
    """
    Selenium-only reviews collector.
    Steps per ASIN:
      1) Fetch product meta (Buy Box price, currency, BSR rank/path) from /dp/<ASIN>.
      2) Paginate recent reviews and parse all review cards.
    Returns a DataFrame with at least:
      asin, review_id, review_date, rating, review_text, verified, helpful_votes,
      buybox_price, currency, bsr_rank, bsr_path
    """
    base = MARKET_BASE.get((marketplace or "US").upper(), MARKET_BASE["US"])
    driver = _make_driver()

    try:
        all_rows: List[Dict[str, Any]] = []

        for raw_asin in asins:
            asin = str(raw_asin).strip()
            if not asin:
                continue

            # 1) Product meta once per ASIN
            meta = _fetch_product_meta(driver, base, asin)

            # 2) Reviews pagination
            collected = 0
            seen_ids: set[str] = set()
            page = 1

            while collected < max_reviews and page <= MAX_REVIEW_PAGES:
                url = _reviews_url(base, asin, page)
                try:
                    driver.get(url)
                except WebDriverException:
                    break

                time.sleep(PAGE_DELAY_SEC)

                rows = _parse_reviews_from_dom(driver, asin)
                if not rows:
                    break

                for r in rows:
                    # attach product meta to each review row (useful for weekly aggregations)
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

                page += 1
                time.sleep(PAGE_DELAY_SEC)

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