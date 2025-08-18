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
from urllib.parse import urljoin

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

# ============================== Configuration ===============================

MARKET_BASE = {
    "US": "https://www.amazon.com",
    "UK": "https://www.amazon.co.uk",
}

# Soft pacing to reduce bot suspicion
PAGE_DELAY_SEC = float(os.getenv("AMZ_PAGE_DELAY_SEC", "1.8"))

# Safety caps
MAX_REVIEW_PAGES = int(os.getenv("AMZ_MAX_REVIEW_PAGES", "50"))

# Test limiter: collect only first N review pages per ASIN (0 = no limit)
TEST_PAGE_LIMIT = int(os.getenv("AMZ_MAX_REVIEW_PAGES_TEST", "2"))

# Output root for raw HTML snapshots
HTML_ROOT = Path("Out") / "html"

# Optional persistent profile (disabled by default)
PERSIST_PROFILE = os.getenv("AMZ_PERSIST_PROFILE", "0") in {"1", "true", "yes"}
PERSIST_DIR = (Path(".chrome-profile-clean").resolve() if PERSIST_PROFILE else None)

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


def _chrome_options_for_profile(profile_dir: str, lang: str) -> ChromeOptions:
    """Build ChromeOptions for an isolated or persistent profile."""
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
    # Pin UI language to reduce layout variance
    opts.add_argument(f"--lang={lang}")
    return opts


def _make_driver(lang: str) -> webdriver.Chrome:
    """
    Create a Chrome WebDriver.
    - If PERSIST_PROFILE enabled, reuse .chrome-profile-clean directory;
    - otherwise use temporary isolated profile that is auto-cleaned on quit.
    """
    if PERSIST_PROFILE and PERSIST_DIR:
        PERSIST_DIR.mkdir(parents=True, exist_ok=True)
        return webdriver.Chrome(options=_chrome_options_for_profile(str(PERSIST_DIR), lang))

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

    return _CtxChrome(options=_chrome_options_for_profile(profile_dir, lang))

# ============================== Small helpers ===============================

def _save_html(path: Path, html: str) -> None:
    """Write HTML snapshot to disk."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(html)


def _accept_consent_if_any(driver) -> None:
    """Click cookie/consent button if present (mostly UK/EU)."""
    try:
        btns = driver.find_elements(
            By.CSS_SELECTOR,
            "input#sp-cc-accept, input[name='accept'], button#sp-cc-accept, button[name='accept']"
        )
        if btns:
            try:
                driver.execute_script("arguments[0].click();", btns[0])
                time.sleep(0.7)
            except Exception:
                pass
    except Exception:
        pass


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


def _go_to_signin_via_header(driver, base_url: str) -> None:
    """Open base, accept consent, click the header 'Sign in' link (more stable than direct /ap/signin)."""
    driver.get(base_url)
    _accept_consent_if_any(driver)
    try:
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.ID, "nav-link-accountList"))
        )
        el = driver.find_element(By.ID, "nav-link-accountList")
        # Prefer clicking the anchor inside
        try:
            a = el.find_element(By.TAG_NAME, "a")
            driver.execute_script("arguments[0].click();", a)
        except Exception:
            driver.execute_script("arguments[0].click();", el)
    except Exception:
        # Fallback to direct signin
        driver.get(urljoin(base_url, "/ap/signin"))
    time.sleep(1.0)


def _ensure_on_market_home(driver, base_url: str) -> None:
    """If we drifted away during login, bring browser back to marketplace home."""
    try:
        cu = driver.current_url or ""
        if not cu.startswith(base_url):
            driver.get(base_url)
            _accept_consent_if_any(driver)
            time.sleep(0.8)
    except Exception:
        pass


def _require_manual_login(driver, base_url: str) -> None:
    """
    Hard stop until the user confirms login is complete.
    We guide via header link; user completes login (CAPTCHA/MFA) and confirms in console.
    """
    print("\n[LOGIN] Opening Amazon and navigating to Sign in…")
    _go_to_signin_via_header(driver, base_url)

    # Wait for something meaningful
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
    _accept_consent_if_any(driver)

    while True:
        if _is_captcha(driver):
            print("⚠️  CAPTCHA detected. Please solve it in the browser.")
        ans = input("[LOGIN] Finished signing in? 'y' to continue, 'h' to re-open via header, 's' to skip: ").strip().lower()
        if ans == "h":
            _go_to_signin_via_header(driver, base_url)
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
                print("⚠️  Still on CAPTCHA. Solve it and press 'y' again.")
                continue
            if _looks_signed_in(driver):
                print("[LOGIN] Login detected. Continuing…")
            else:
                print("ℹ️  Could not confirm login heuristically. Continuing anyway.")
            break

    _ensure_on_market_home(driver, base_url)

# ============================== URL builders & regex ========================

def _product_url(base: str, asin: str) -> str:
    return f"{base}/dp/{asin}"

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
    tx = text.replace("\xa0", " ").strip()
    if "One person" in tx:
        return 1
    nums = re.findall(r"[\d,]+", tx)
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

# ============================== Real reviews root ===========================

def _resolve_reviews_root_url(driver, base_url: str, asin: str) -> Optional[str]:
    """
    Open /dp/<ASIN>, accept possible interstitials, and extract the real
    'See all reviews' URL from the page.
    """
    driver.get(_product_url(base_url, asin))
    _accept_consent_if_any(driver)

    try:
        WebDriverWait(driver, 20).until(
            EC.any_of(
                EC.presence_of_element_located((By.CSS_SELECTOR, "#corePriceDisplay_desktop_feature_div")),
                EC.presence_of_element_located((By.ID, "detailBullets_feature_div")),
                EC.presence_of_element_located((By.TAG_NAME, "body")),
            )
        )
    except Exception:
        pass
    time.sleep(0.8)

    selectors = [
        'a[data-hook="see-all-reviews-link-foot"]',
        'a[data-hook="see-all-reviews-link"]',
        'a[href*="/product-reviews/"]',
    ]
    for sel in selectors:
        try:
            el = driver.find_element(By.CSS_SELECTOR, sel)
            href = el.get_attribute("href")
            if href and "/product-reviews/" in href:
                _accept_consent_if_any(driver)
                return href
        except Exception:
            continue

    # Fallback: if current URL already reviews
    cu = driver.current_url or ""
    if "/product-reviews/" in cu:
        _accept_consent_if_any(driver)
        return cu

    return f"{base_url}/product-reviews/{asin}/?sortBy=recent"

# ============================== Product meta =================================

def _fetch_product_meta(driver: webdriver.Chrome, base_url: str, asin: str) -> dict:
    """Get Buy Box price and BSR from /dp/<ASIN>."""
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

# ============================== Reviews parsing ==============================

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

# ============================== Next pagination ==============================

def _click_next_reviews_page(driver: webdriver.Chrome) -> bool:
    """
    Click the 'Next' pagination link on the reviews page.
    Returns True if the page number advanced (content changed), else False.
    """
    try:
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "ul.a-pagination"))
        )
    except TimeoutException:
        return False

    def _current_page_no() -> Optional[int]:
        try:
            sel = driver.find_element(By.CSS_SELECTOR, "ul.a-pagination li.a-selected")
            num = (sel.text or "").strip()
            return int(re.sub(r"[^\d]", "", num)) if num else None
        except Exception:
            return None

    def _first_review_fingerprint() -> str:
        try:
            first = driver.find_elements(By.CSS_SELECTOR, 'div[data-hook="review"]')[0]
            rid = first.get_attribute("id") or ""
            txt = ""
            try:
                txt = first.find_element(By.CSS_SELECTOR, 'span[data-hook="review-body"]').text[:64]
            except Exception:
                pass
            return f"{rid}|{txt}"
        except Exception:
            return ""

    cur_no = _current_page_no()
    cur_fp = _first_review_fingerprint()

    try:
        last_li = driver.find_element(By.CSS_SELECTOR, "ul.a-pagination li.a-last")
    except NoSuchElementException:
        return False

    cls = (last_li.get_attribute("class") or "").lower()
    if "a-disabled" in cls:
        return False

    # Prefer clicking anchor; if not, try href navigation
    try:
        link = last_li.find_element(By.TAG_NAME, "a")
        driver.execute_script("arguments[0].scrollIntoView({block:'center'});", link)
        time.sleep(0.2)
        driver.execute_script("arguments[0].click();", link)
    except Exception:
        try:
            href = last_li.find_element(By.TAG_NAME, "a").get_attribute("href")
            if href:
                driver.get(href)
            else:
                return False
        except Exception:
            return False

    # Wait for content to change (new active page OR first review changed)
    try:
        WebDriverWait(driver, 20).until(
            lambda d: (
                (_current_page_no() is not None and cur_no is not None and _current_page_no() != cur_no)
                or _first_review_fingerprint() != cur_fp
            )
        )
        time.sleep(PAGE_DELAY_SEC)
        return True
    except TimeoutException:
        return False

# ============================== Public API ==================================

def collect_reviews(asins: Iterable[str], max_reviews: int, marketplace: str) -> pd.DataFrame:
    """
    Selenium collector that:
      - pauses for manual login confirmation via header "Sign in" (more reliable),
      - saves every reviews page to Out/html/<MARKET>/<ASIN>/<ASIN>_p{N}.html,
      - parses reviews from saved HTML,
      - collects Buy Box price and BSR once per ASIN.

    Returns DataFrame with at least:
      asin, review_id, review_date, review_title, review_text, rating,
      verified, helpful_votes, buybox_price, currency, bsr_rank, bsr_path
    """
    market_key = (marketplace or "US").upper()
    base = MARKET_BASE.get(market_key, MARKET_BASE["US"])
    lang = "en-GB" if market_key == "UK" else "en-US"

    driver = _make_driver(lang=lang)

    try:
        # Hard stop for manual login before scraping
        _require_manual_login(driver, base)

        all_rows: List[Dict[str, Any]] = []

        for raw_asin in asins:
            asin = str(raw_asin).strip()
            if not asin:
                continue

            print(f"[ASIN] {asin} — fetching meta…")
            meta = _fetch_product_meta(driver, base, asin)

            # Prepare folder for HTML dumps
            asin_dir = HTML_ROOT / market_key / asin
            asin_dir.mkdir(parents=True, exist_ok=True)

            # Resolve real "See all reviews" URL
            print(f"[ASIN] {asin} — resolving reviews root…")
            root = _resolve_reviews_root_url(driver, base, asin)
            if not root:
                _save_html(asin_dir / f"{asin}_dp_unresolved.html", driver.page_source)
                print(f"[WARN] Could not resolve reviews URL for {asin}. Saved dp page for debug.")
                continue

            try:
                driver.get(root)
            except WebDriverException:
                print(f"[WARN] Failed to open reviews root for {asin}")
                continue

            # Ensure first batch of reviews loaded
            try:
                WebDriverWait(driver, 15).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, 'div[data-hook="review"]'))
                )
            except TimeoutException:
                _save_html(asin_dir / f"{asin}_p1.html", driver.page_source)
                print(f"[WARN] No reviews block for {asin} (saved p1 for debug).")
                continue

            collected = 0
            page_idx = 1
            seen_ids: set[str] = set()

            while collected < max_reviews and page_idx <= MAX_REVIEW_PAGES:
                time.sleep(PAGE_DELAY_SEC)

                # Save current page
                html_path = asin_dir / f"{asin}_p{page_idx}.html"
                _save_html(html_path, driver.page_source)
                print(f"[SAVE] {html_path}")

                # Parse current page
                rows = _parse_reviews_from_html((driver.page_source or ""), asin)
                if not rows:
                    print(f"[INFO] No review cards on page {page_idx} for {asin}.")
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
                    print(f"[TEST] Page limit reached ({TEST_PAGE_LIMIT}).")
                    break

                # Move to next page by clicking "Next"
                moved = _click_next_reviews_page(driver)
                if not moved:
                    print(f"[INFO] No Next page for {asin} after page {page_idx}.")
                    break

                page_idx += 1

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