# amazon_review_collector.py
# All comments in English.

from __future__ import annotations

import json
import os
import re
import shutil
import tempfile
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Iterable, List, Dict, Any, Optional

import pandas as pd
from bs4 import BeautifulSoup

from selenium import webdriver
from selenium.common.exceptions import (
    NoSuchElementException,
    TimeoutException,
    WebDriverException,
    StaleElementReferenceException,
    ElementClickInterceptedException,
)
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

# ============================== Config =======================================

MARKET_BASE = {
    "US": "https://www.amazon.com",
    "UK": "https://www.amazon.co.uk",
}

PAGE_DELAY_SEC = float(os.getenv("AMZ_PAGE_DELAY_SEC", "1.6"))
MAX_REVIEW_PAGES = int(os.getenv("AMZ_MAX_REVIEW_PAGES", "50"))
TEST_PAGE_LIMIT = int(os.getenv("AMZ_MAX_REVIEW_PAGES_TEST", "2"))  # 0 = unlimited

HTML_ROOT = Path("Out") / "_raw_review_pages"

PERSIST_PROFILE = os.getenv("AMZ_PERSIST_PROFILE", "0").lower() in {"1", "true", "yes"}
PERSIST_DIR = (Path(".chrome-profile-clean").resolve() if PERSIST_PROFILE else None)

# ============================== Chrome bootstrap ============================

@contextmanager
def _temp_profile_dir():
    d = tempfile.mkdtemp(prefix="amz_chrome_profile_")
    try:
        yield d
    finally:
        shutil.rmtree(d, ignore_errors=True)

def _chrome_options_for_profile(profile_dir: str, lang: str) -> ChromeOptions:
    opts = ChromeOptions()
    # Headed is safer for Amazon challenges:
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
    opts.add_argument(f"--lang={lang}")
    # Reduce obvious automation flags
    opts.add_experimental_option("excludeSwitches", ["enable-automation"])
    opts.add_experimental_option("useAutomationExtension", False)
    return opts

def _make_driver(lang: str) -> webdriver.Chrome:
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

def _ensure_dir(p: Path):
    p.mkdir(parents=True, exist_ok=True)

def _save_html(path: Path, html: str) -> None:
    _ensure_dir(path.parent)
    path.write_text(html or "", encoding="utf-8", errors="ignore")

def _base(marketplace: str) -> str:
    return MARKET_BASE.get((marketplace or "US").upper(), MARKET_BASE["US"])

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
    url = (driver.current_url or "").lower()
    if "captcha" in url:
        return True
    try:
        body = driver.find_element(By.TAG_NAME, "body").text.lower()
        return "enter the characters you see" in body or "type the characters" in body
    except Exception:
        return False

def _looks_signed_in(driver) -> bool:
    try:
        el = driver.find_element(By.ID, "nav-link-accountList")
        txt = (el.text or "").strip().lower()
        return ("sign in" not in txt) and ("hello" in txt or "account" in txt or "returns" in txt)
    except Exception:
        return False

# ============================== Login flow ==================================

def _go_to_signin_via_header(driver, base_url: str) -> None:
    driver.get(base_url)
    _accept_consent_if_any(driver)
    try:
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.ID, "nav-link-accountList"))
        )
        el = driver.find_element(By.ID, "nav-link-accountList")
        try:
            a = el.find_element(By.TAG_NAME, "a")
            driver.execute_script("arguments[0].click();", a)
        except Exception:
            driver.execute_script("arguments[0].click();", el)
    except Exception:
        driver.get(f"{base_url}/ap/signin")
    time.sleep(1.0)

def _ensure_on_market_home(driver, base_url: str) -> None:
    try:
        cu = driver.current_url or ""
        if not cu.startswith(base_url):
            driver.get(base_url)
            _accept_consent_if_any(driver)
            time.sleep(0.8)
    except Exception:
        pass

def _require_manual_login(driver, base_url: str) -> None:
    print("\n[LOGIN] Opening Amazon and navigating to Sign in…")
    _go_to_signin_via_header(driver, base_url)
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

# ============================== URL builders & parse utils ===================

def _reviews_url(asin: str, marketplace: str, page: int = 1) -> str:
    base = _base(marketplace)
    lang = "en_GB" if (marketplace or "US").upper() == "UK" else "en_US"
    return f"{base}/product-reviews/{asin}/?reviewerType=all_reviews&sortBy=recent&filterByLanguage={lang}&pageNumber={page}"

def _parse_star(text: str) -> Optional[float]:
    m = re.search(r"([0-5](?:\.\d)?) out of 5", text or "")
    try:
        return float(m.group(1)) if m else None
    except Exception:
        return None

def _parse_helpful(text: str) -> Optional[int]:
    if not text:
        return None
    tx = text.replace("\xa0", " ").strip()
    if tx.lower().startswith("one"):
        return 1
    nums = re.findall(r"[\d,]+", tx)
    if nums:
        try:
            return int(nums[0].replace(",", ""))
        except Exception:
            return None
    return None

# ============================== Reviews UI preparation ======================

def _choose_all_reviewers_if_possible(driver) -> None:
    """Switch from 'Top reviews from …' to 'All reviewers' if dropdown exists."""
    # Modern dropdown
    try:
        trigger = driver.find_element(By.CSS_SELECTOR, '#reviews-filter-info-segment-dropdown')
        driver.execute_script("arguments[0].click();", trigger)
        time.sleep(0.3)
        items = driver.find_elements(By.CSS_SELECTOR, '.a-popover-wrapper a.a-dropdown-link')
        for it in items:
            if "all reviewers" in (it.text or "").strip().lower():
                driver.execute_script("arguments[0].click();", it)
                time.sleep(1.0)
                return
    except Exception:
        pass
    # Legacy dropdown
    try:
        triggers = driver.find_elements(By.CSS_SELECTOR, 'span[data-action="a-dropdown-button"]')
        for t in triggers:
            driver.execute_script("arguments[0].click();", t)
            time.sleep(0.3)
            links = driver.find_elements(By.CSS_SELECTOR, 'ul.a-nostyle.a-list-link a')
            for a in links:
                if "all reviewers" in (a.text or "").strip().lower():
                    driver.execute_script("arguments[0].click();", a)
                    time.sleep(1.0)
                    return
    except Exception:
        pass

def _set_sort_most_recent(driver) -> None:
    """Force 'Most recent' sorting."""
    try:
        sel = driver.find_element(By.CSS_SELECTOR, 'select#sort-order-dropdown')
        sel.click()
        time.sleep(0.3)
        opts = driver.find_elements(By.XPATH, '//select[@id="sort-order-dropdown"]/option[contains(@value,"recent") or contains(., "Most recent")]')
        if opts:
            opts[0].click()
            time.sleep(1.0)
            return
    except Exception:
        pass
    try:
        triggers = driver.find_elements(By.CSS_SELECTOR, 'span[data-action="a-dropdown-button"] > span.a-button-inner')
        for t in triggers:
            driver.execute_script("arguments[0].click();", t)
            time.sleep(0.3)
            links = driver.find_elements(By.CSS_SELECTOR, 'ul.a-nostyle.a-list-link a')
            for a in links:
                if "most recent" in (a.text or "").strip().lower():
                    driver.execute_script("arguments[0].click();", a)
                    time.sleep(1.0)
                    return
    except Exception:
        pass

def _scroll_to_reviews_list(driver) -> None:
    try:
        container = driver.find_element(By.CSS_SELECTOR, "#cm_cr-review_list")
        driver.execute_script("arguments[0].scrollIntoView({block:'start'});", container)
        time.sleep(0.7)
    except Exception:
        pass

# ============================== Parsing reviews from HTML ===================

def _parse_reviews_from_html(html: str, asin: str, marketplace: str) -> List[Dict[str, Any]]:
    soup = BeautifulSoup(html or "", "html.parser")
    cards = soup.select('div[data-hook="review"]')
    if not cards:
        cards = soup.select('div[data-hook="cmps-review"]')

    out: List[Dict[str, Any]] = []
    for card in cards:
        try:
            review_id = card.get("id") or card.get("data-review-id") or ""
            title_el = card.select_one('a[data-hook="review-title"] span')
            title = title_el.get_text(strip=True) if title_el else ""
            star_el = card.select_one('i[data-hook="review-star-rating"] span') or card.select_one('i[data-hook="cmps-review-star-rating"] span')
            rating_text = star_el.get_text(strip=True) if star_el else ""
            rating = _parse_star(rating_text) if rating_text else None
            date_el = card.select_one('span[data-hook="review-date"]')
            review_date = date_el.get_text(strip=True) if date_el else ""
            body_el = card.select_one('span[data-hook="review-body"]')
            body = body_el.get_text(strip=True) if body_el else ""
            verified = bool(card.select_one('span[data-hook="avp-badge"]'))
            helpful_el = card.select_one('span[data-hook="helpful-vote-statement"]')
            helpful = _parse_helpful(helpful_el.get_text(strip=True)) if helpful_el else None

            out.append({
                "asin": asin,
                "marketplace": (marketplace or "US").upper(),
                "review_id": review_id,
                "review_date_raw": review_date,
                "rating": rating,
                "title": title,
                "body": body,
                "verified_purchase": verified,
                "helpful_votes": helpful,
            })
        except Exception:
            continue
    return out

# ============================== Pagination ==================================

def _click_next_reviews_page(driver: webdriver.Chrome) -> bool:
    """Click 'Next' in pagination; return True if navigation is possible."""
    try:
        ul = driver.find_element(By.XPATH, '//ul[contains(@class,"a-pagination")]')
        disabled = ul.find_elements(By.XPATH, './/li[contains(@class,"a-disabled") and contains(@class,"a-last")]')
        if disabled:
            return False
        nxt = ul.find_elements(By.XPATH, './/li[contains(@class,"a-last")]//a')
        if not nxt:
            return False
        driver.execute_script("arguments[0].scrollIntoView({block:'center'});", nxt[0])
        time.sleep(0.2)
        driver.execute_script("arguments[0].click();", nxt[0])
        return True
    except (NoSuchElementException, StaleElementReferenceException, ElementClickInterceptedException):
        return False

# ============================== Freshness gate ==============================

def _has_new_vs_checkpoint(page_rows: List[Dict[str, Any]], chk: Optional[Dict[str, Any]]) -> bool:
    """
    Return True if current page likely contains something newer than checkpoint.
    Check by 'review_id' presence not seen before; fall back to True if checkpoint absent.
    """
    if not chk:
        return True
    last_ids = set(map(str, (chk.get("ids") or [])))
    if not page_rows:
        return False
    for r in page_rows:
        rid = str(r.get("review_id") or "")
        if rid and rid not in last_ids:
            return True
    return False

# ============================== Public API ==================================

def collect_reviews(
    asins: List[str],
    max_reviews_per_asin: int = 500,
    marketplace: str = "US",
    last_seen: Optional[Dict[str, Dict[str, Any]]] = None,    # {"ASIN": {"ids": [...], "date": "..."}}
    per_page_sink: Optional[callable] = None,                  # callback(asin, page_idx, page_df)
) -> pd.DataFrame:
    """
    Selenium collector:
      - manual login pause,
      - forces All reviewers + Most recent + English,
      - saves each page HTML,
      - parses with BS4,
      - calls per_page_sink(asin, page_idx, page_df) right after parsing each page,
      - uses last_seen checkpoint to skip pagination when no new content on p1.
    """
    market_key = (marketplace or "US").upper()
    base = _base(market_key)
    lang = "en-GB" if market_key == "UK" else "en-US"

    driver = _make_driver(lang=lang)
    all_rows: List[Dict[str, Any]] = []

    try:
        # Manual login gate
        _require_manual_login(driver, base)

        for idx, raw_asin in enumerate(asins, start=1):
            asin = str(raw_asin).strip()
            if not asin:
                continue

            print(f"[{idx}/{len(asins)}] ASIN={asin} — opening p1 (Most recent, English)…")
            asin_dir = HTML_ROOT / market_key / asin
            _ensure_dir(asin_dir)

            # open p1
            url = _reviews_url(asin, market_key, page=1)
            try:
                driver.get(url)
            except WebDriverException as e:
                print(f"  [WARN] cannot open reviews URL for {asin}: {e}")
                continue

            _accept_consent_if_any(driver)
            # prepare UI
            try:
                WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.ID, "cm_cr-review_list")))
            except TimeoutException:
                # try scroll to trigger lazy render
                driver.execute_script("window.scrollTo(0, 600);")
                time.sleep(1.0)
                try:
                    WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, "cm_cr-review_list")))
                except TimeoutException:
                    # save for debug and continue to next ASIN
                    _save_html(asin_dir / f"{asin}_p1.html", driver.page_source or "")
                    print(f"  [WARN] reviews container not found on p1 → saved for debug.")
                    continue

            _choose_all_reviewers_if_possible(driver)
            _set_sort_most_recent(driver)
            _scroll_to_reviews_list(driver)

            # Ensure first cards visible
            try:
                WebDriverWait(driver, 25).until(
                    EC.any_of(
                        EC.presence_of_element_located((By.CSS_SELECTOR, 'div[data-hook="review"]')),
                        EC.presence_of_element_located((By.CSS_SELECTOR, 'div[data-hook="cmps-review"]')),
                    )
                )
            except TimeoutException:
                # still save p1 for diagnostics
                _save_html(asin_dir / f"{asin}_p1.html", driver.page_source or "")
                print(f"  [WARN] no review cards detected on p1 → saved for debug.")
                continue

            collected = 0
            page_idx = 1
            # ---- page 1 ----
            time.sleep(PAGE_DELAY_SEC)
            _save_html(asin_dir / f"{asin}_p{page_idx}.html", driver.page_source or "")
            page_rows = _parse_reviews_from_html(driver.page_source or "", asin, market_key)

            # freshness against checkpoint
            chk = (last_seen or {}).get(asin)
            if not _has_new_vs_checkpoint(page_rows, chk):
                print(f"  [SKIP] no new reviews vs checkpoint on p1.")
                if per_page_sink:
                    per_page_sink(asin, page_idx, pd.DataFrame(page_rows))
                all_rows.extend(page_rows)
                continue

            # write p1 immediately
            if per_page_sink:
                per_page_sink(asin, page_idx, pd.DataFrame(page_rows))
            all_rows.extend(page_rows)
            collected += len(page_rows)

            # paginate further
            while collected < max_reviews_per_asin:
                if TEST_PAGE_LIMIT > 0 and page_idx >= TEST_PAGE_LIMIT:
                    print(f"  [TEST] page limit reached ({TEST_PAGE_LIMIT}).")
                    break

                moved = _click_next_reviews_page(driver)
                if not moved:
                    print(f"  [INFO] no Next page after p{page_idx}.")
                    break

                # Wait for content refresh
                try:
                    WebDriverWait(driver, 20).until(
                        EC.presence_of_element_located((By.ID, "cm_cr-review_list"))
                    )
                except TimeoutException:
                    pass

                page_idx += 1
                time.sleep(PAGE_DELAY_SEC)
                _save_html(asin_dir / f"{asin}_p{page_idx}.html", driver.page_source or "")
                rows = _parse_reviews_from_html(driver.page_source or "", asin, market_key)
                if per_page_sink:
                    per_page_sink(asin, page_idx, pd.DataFrame(rows))
                all_rows.extend(rows)
                collected += len(rows)

                if not rows:
                    # no cards on this page – likely end
                    break

            print(f"  ✓ pages scraped: {page_idx}, reviews parsed: {collected}")

        # Return DataFrame (even if CSV already persisted via sink)
        df = pd.DataFrame(all_rows)
        if not df.empty:
            df["rating"] = pd.to_numeric(df["rating"], errors="coerce")
            df["verified_purchase"] = df["verified_purchase"].astype("boolean")
            if "helpful_votes" in df.columns:
                df["helpful_votes"] = pd.to_numeric(df["helpful_votes"], errors="coerce")
        return df

    finally:
        try:
            driver.quit()
        except Exception:
            pass

# ============================== CLI test hook ===============================

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Amazon reviews collector (Most recent, English)")
    parser.add_argument("asins", nargs="+", help="List of ASINs")
    parser.add_argument("--mk", default="US", help="Marketplace: US or UK")
    parser.add_argument("--max", type=int, default=200, help="Max reviews per ASIN")
    args = parser.parse_args()

    df = collect_reviews(args.asins, max_reviews_per_asin=args.max, marketplace=args.mk)
    out = Path("Out/reviews_sample.csv")
    out.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out, index=False)
    print(f"Saved {len(df)} rows -> {out}")