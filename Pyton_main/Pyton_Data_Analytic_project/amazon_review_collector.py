# amazon_review_collector.py
# All comments in English.

from __future__ import annotations

import re
import time
from typing import Iterable, List, Dict, Any, Optional

import pandas as pd
import requests
from bs4 import BeautifulSoup
import psutil
import time
import sys


# ----------------------------- Config & Utils -----------------------------

MARKET_BASE = {
    # Marketplace → product-reviews base URL
    "US": "https://www.amazon.com/product-reviews",
    "UK": "https://www.amazon.co.uk/product-reviews",
}

HEADERS = {
    # Very vanilla desktop UA; adjust if needed
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Cache-Control": "no-cache",
    "Pragma": "no-cache",
}

REQUIRED_COLS = [
    "asin",
    "review_id",
    "review_date",
    "rating",
    "review_text",
    "verified",
    "helpful_votes",
]

STAR_RE = re.compile(r"([0-5](?:\.\d)?) out of 5")
HELPFUL_RE = re.compile(r"([\d,]+|One)\s+person|people")  # matches "One person" or "2,345 people"
DATE_CLEAN_RE = re.compile(r"on\s+", re.IGNORECASE)       # strip "on " before date

def ensure_chrome_closed():
    """
    Ensure no Chrome processes are running.
    Ask user to close all Chrome windows if needed.
    """
    while True:
        chrome_running = any("Google Chrome" in p.name() or "chrome" in p.name().lower()
                             for p in psutil.process_iter(['name']))
        if not chrome_running:
            return
        print("⚠️ Please close all Google Chrome windows before continuing...")
        time.sleep(3)

def _market_base(marketplace: str) -> str:
    """Resolve marketplace into base URL for reviews."""
    return MARKET_BASE.get((marketplace or "US").upper(), MARKET_BASE["US"])

def _sleep_backoff(attempt: int, base: float = 1.0) -> None:
    """Linear backoff with jitter."""
    time.sleep(base * attempt + 0.25)

def _parse_star(text: str) -> Optional[float]:
    """Extract 'x out of 5' → float(x)."""
    if not text:
        return None
    m = STAR_RE.search(text)
    if not m:
        return None
    try:
        return float(m.group(1))
    except Exception:
        return None

def _parse_helpful(text: str) -> int:
    """Parse 'One person found this helpful' or '2,345 people found this helpful' → int."""
    if not text:
        return 0
    # Normalize thousand separators
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
    Amazon renders like:
      'Reviewed in the United States on July 1, 2025'
      'Reviewed in the United Kingdom on 12 May 2024'
    We keep only the date part for robustness; later pipeline casts with pandas.
    """
    if not text:
        return ""
    # Keep the tail after 'on '
    parts = DATE_CLEAN_RE.split(text, maxsplit=1)
    date_part = parts[-1].strip() if parts else text.strip()
    # Sometimes there's locale prefix 'Reviewed on 12 May 2024' → we still return the tail
    return date_part

# ----------------------------- Core Scraper ------------------------------

def _reviews_page_url(market_base: str, asin: str, page: int) -> str:
    # 'sortBy=recent' to get newest first; tweak if you need "top" order
    return f"{market_base}/{asin}/?sortBy=recent&pageNumber={page}"

def _fetch_html(session: requests.Session, url: str, attempt: int = 1, timeout: int = 25) -> Optional[str]:
    """GET with basic retry/backoff. Returns HTML or None on failure/block."""
    try:
        r = session.get(url, timeout=timeout)
        # Basic anti-bot: if we get a Captcha/503, bail out early
        if r.status_code != 200:
            return None
        # If Amazon serves a robot/CAPTCHA page, it often lacks expected hooks
        if 'captchacharacters' in r.text.lower() or 'sorry' in r.text[:200].lower():
            return None
        return r.text
    except requests.RequestException:
        return None

def _parse_reviews_from_html(html: str, asin: str) -> List[Dict[str, Any]]:
    """Parse a single reviews page HTML into a list of dict rows."""
    out: List[Dict[str, Any]] = []
    soup = BeautifulSoup(html, "html.parser")

    # Each review is in a container with data-hook='review'
    for div in soup.select('div[data-hook="review"]'):
        # Review ID
        review_id = div.get("id") or div.get("data-review-id") or None

        # Rating (i[data-hook="review-star-rating"] > span)
        rating_text = ""
        star = div.select_one('i[data-hook="review-star-rating"] span')
        if star and star.text:
            rating_text = star.text.strip()
        else:
            # Some locales use 'cmps-review-star-rating'
            star = div.select_one('i[data-hook="cmps-review-star-rating"] span')
            rating_text = star.text.strip() if star else ""

        rating = _parse_star(rating_text)

        # Date
        date_el = div.select_one('span[data-hook="review-date"]')
        review_date = _clean_review_date(date_el.text.strip()) if date_el else ""

        # Text
        body_el = div.select_one('span[data-hook="review-body"]')
        review_text = body_el.get_text(separator=" ", strip=True) if body_el else ""

        # Verified badge
        ver_el = div.select_one('span[data-hook="avp-badge"]')
        verified = bool(ver_el and "Verified Purchase" in ver_el.text)

        # Helpful votes
        hv_el = div.select_one('span[data-hook="helpful-vote-statement"]')
        helpful_votes = _parse_helpful(hv_el.text.strip()) if hv_el else 0

        out.append({
            "asin": asin,
            "review_id": review_id,
            "review_date": review_date,   # string; pipeline will cast with pandas later
            "rating": rating,
            "review_text": review_text,
            "verified": verified,
            "helpful_votes": helpful_votes,
        })
    return out

def _dedupe_reviews(df: pd.DataFrame) -> pd.DataFrame:
    """Deduplicate by (asin, review_id) then fallback to (asin, date, rating, hash(text))."""
    df = df.copy()
    # Primary key
    if "review_id" in df.columns:
        key1 = df["asin"].astype(str) + "|" + df["review_id"].astype(str)
        df = df.loc[~key1.duplicated(keep="first")].reset_index(drop=True)
    # Fallback key
    key2 = (
        df["asin"].astype(str) + "|" +
        df["review_date"].astype(str) + "|" +
        df["rating"].astype(str) + "|" +
        df["review_text"].astype(str).map(lambda t: str(hash(t)))
    )
    df = df.loc[~key2.duplicated(keep="first")].reset_index(drop=True)
    return df

# ----------------------------- Public API --------------------------------

def collect_reviews(asins: Iterable[str], max_reviews: int, marketplace: str) -> pd.DataFrame:
    """
    Fetch up to `max_reviews` most recent reviews for each ASIN and return a normalized DataFrame.
    Columns guaranteed: asin, review_id, review_date, rating, review_text, verified, helpful_votes
    """
    base = _market_base(marketplace)
    session = requests.Session()
    session.headers.update(HEADERS)

    all_rows: List[Dict[str, Any]] = []

    for asin in map(str, asins):
        asin = asin.strip()
        if not asin:
            continue

        collected = 0
        page = 1
        seen_ids: set[str] = set()

        # Up to ~50 pages to be safe; we stop earlier once max_reviews is reached.
        while collected < max_reviews and page <= 50:
            url = _reviews_page_url(base, asin, page)
            html = _fetch_html(session, url, attempt=page)

            if not html:
                # If blocked or empty — small backoff and one more try
                _sleep_backoff(page, base=0.8)
                html = _fetch_html(session, url, attempt=page)
                if not html:
                    # Give up on this ASIN page
                    break

            rows = _parse_reviews_from_html(html, asin)

            if not rows:
                # No reviews parsed on this page → likely out of pages
                break

            # Append, respecting max_reviews and avoiding duplicates by review_id within this run
            for r in rows:
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
            # Gentle delay between pages to reduce bot-detection chance
            _sleep_backoff(1, base=0.6)

    # Normalize to DataFrame & enforce schema
    df = pd.DataFrame(all_rows)

    # Ensure required columns exist
    for c in REQUIRED_COLS:
        if c not in df.columns:
            df[c] = None

    # Type coercions
    df["rating"] = pd.to_numeric(df["rating"], errors="coerce")
    # Keep date as string; your weekly builder will convert with pandas.to_datetime
    df["verified"] = df["verified"].astype("boolean")
    df["helpful_votes"] = pd.to_numeric(df["helpful_votes"], errors="coerce").fillna(0).astype("Int64")

    # Final dedupe
    df = _dedupe_reviews(df)

    return df.reset_index(drop=True)