"""
# === Module Header ===
# 📁 Module: actions/asin_search.py
# 📅 Last Reviewed: 2025-10-15
# 🔧 Status: 🟢 Stable
# 👤 Owner: MatveyB
# 📝 Summary: ASIN search flow (keywords → categories → ASINs) and persistence.
# =====================
"""

import json
import re
import time
from datetime import datetime
from pathlib import Path
from time import sleep
from urllib.parse import quote_plus

import pandas as pd
import requests
from core.collection_io import collection_csv, save_collection
from core.env_check import ENV_VARS, get_env, get_env_bool
from core.log import print_error, print_info
from core.marketplaces import to_domain
from scraper.driver import init_driver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


def fetch_amazon_categories(keyword):
    """
    Load category tree from local JSON and return full paths where the keyword appears.
    """
    json_path = Path(__file__).parent.parent / "core" / "amazon_categories_us.json"
    with open(json_path, "r", encoding="utf-8") as f:
        tree = json.load(f)

    matches = []

    def recurse(subtree, path):
        for k, v in subtree.items():
            new_path = path + [k]
            if keyword.lower() in k.lower():
                matches.append(" > ".join(new_path))
            if isinstance(v, dict):
                recurse(v, new_path)

    recurse(tree, [])
    return matches


def extract_asin_from_url(url: str | None) -> str | None:
    if not url:
        return None
    try:
        # Common patterns: /dp/B0XXXXXXXX/, /gp/product/B0XXXXXXXX/, query params etc.
        m = re.search(r"/(?:dp|gp/product)/([A-Z0-9]{10})(?:[/?]|$)", url, re.I)
        if m:
            return m.group(1).upper()
        # Fallback: try to find a 10-char ASIN-like token in path
        m = re.search(r"/([A-Z0-9]{10})(?:[/?]|$)", url, re.I)
        if m:
            return m.group(1).upper()
    except Exception:
        pass
    return None


SCRAPINGDOG_LIMIT_PHRASE = "account limit"


def _scrapingdog_fetch(url: str) -> requests.Response:
    """Low-level fetch with timeout."""
    return requests.get(url, timeout=30)


def _extract_asins_from_scrapingdog_json(data: dict) -> list[dict]:
    """Extract ASIN rows from possible Scrapingdog shapes."""
    rows: list[dict] = []
    # Try several possible containers
    candidates = []
    for key in ("results", "products", "organic_results"):
        val = data.get(key)
        if isinstance(val, list):
            candidates = val
            break
    for item in candidates:
        # some payloads mark items by type
        if isinstance(item, dict) and item.get("type") not in (None, "search_product"):
            continue
        asin = None
        if isinstance(item, dict):
            asin = item.get("asin") or extract_asin_from_url(item.get("url"))
        if not asin:
            continue
        rows.append(
            {
                "asin": asin,
                "title": item.get("title") if isinstance(item, dict) else None,
                "price": (item.get("price") if isinstance(item, dict) else None),
                "rating": (
                    (item.get("stars") or item.get("rating")) if isinstance(item, dict) else None
                ),
                "review_count": (
                    (item.get("total_reviews") or item.get("reviews"))
                    if isinstance(item, dict)
                    else None
                ),
            }
        )
    return rows


def _serpapi_fetch_asins(query: str, domain_full: str, pages: int = 2) -> list[dict]:
    api_key = (get_env("SERPAPI_API_KEY", "") or "").strip()
    if not api_key:
        print("[!] SERPAPI_API_KEY missing; SerpAPI fallback unavailable")
        return []

    out: list[dict] = []
    for page in range(1, pages + 1):
        try:
            r = requests.get(
                "https://serpapi.com/search.json",
                params={
                    "engine": "amazon",
                    "amazon_domain": domain_full,
                    "k": query,  # correct query param for Amazon engine
                    "page": page,
                    "api_key": api_key,
                },
                timeout=30,
            )
            if r.status_code != 200:
                print(f"[!] SerpAPI HTTP {r.status_code} for page {page}")
                continue
            j = r.json()
        except Exception as e:
            print(f"[!] SerpAPI request failed: {e}")
            continue
        results = j.get("organic_results") or j.get("search_results") or []
        for item in results:
            asin = item.get("asin") or extract_asin_from_url(item.get("link") or item.get("url"))
            if not asin:
                continue
            out.append(
                {
                    "asin": asin,
                    "title": item.get("title"),
                    "price": None,
                    "rating": item.get("rating"),
                    "review_count": item.get("reviews_count") or item.get("reviews"),
                }
            )
    # de-dup
    seen: set[str] = set()
    dedup: list[dict] = []
    for row in out:
        a = row["asin"]
        if a in seen:
            continue
        seen.add(a)
        dedup.append(row)
    return dedup


def _click_next_page(driver) -> bool:
    try:
        # New pagination button
        btn = driver.find_element(By.CSS_SELECTOR, "a.s-pagination-next")
        if btn.get_attribute("aria-disabled") == "true":
            return False
        driver.execute_script("arguments[0].click();", btn)
        return True
    except Exception:
        try:
            btn = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "li.a-last a"))
            )
            driver.execute_script("arguments[0].click();", btn)
            return True
        except Exception:
            return False


def _selenium_fetch_asins(query: str, domain: str, pages: int = 2, limit: int = 200) -> list[dict]:
    """Fallback: use Selenium to fetch ASINs from Amazon search results."""
    user_data_dir = ENV_VARS.get("CHROME_USER_DATA_DIR")
    driver = init_driver(user_data_dir)
    out: list[dict] = []
    seen: set[str] = set()
    try:
        # 'domain' may be a TLD (com) or already a full domain (amazon.com)
        dom_full = to_domain(domain)
        url = f"https://{dom_full}/s?k={quote_plus(query)}"
        print_info(f"[asin-fb] opening {url}")
        driver.get(url)
        WebDriverWait(driver, 12).until(EC.presence_of_element_located((By.ID, "search")))
        for page in range(1, pages + 1):
            html = driver.page_source.lower()
            if ("captchacharacters" in html) or ("enter the characters you see" in html):
                print_info(
                    "[asin-fb] Robot check detected. Solve in Chrome, then press Enter here…"
                )
                try:
                    input()
                except Exception:
                    pass
                sleep(1)
            cards = driver.find_elements(By.CSS_SELECTOR, "div.s-main-slot [data-asin]")
            new_on_page = 0
            for c in cards:
                try:
                    a = (c.get_attribute("data-asin") or "").strip().upper()
                    if len(a) != 10 or not a.isalnum() or a in seen:
                        continue
                    seen.add(a)
                    try:
                        title = c.find_element(By.CSS_SELECTOR, "h2 a span").text.strip()
                    except Exception:
                        title = None
                    out.append({"asin": a, "title": title})
                    new_on_page += 1
                    if len(out) >= limit:
                        break
                except Exception:
                    continue
            print_info(f"[asin-fb] page {page}: new={new_on_page}, total={len(out)}")
            if len(out) >= limit or new_on_page == 0:
                break
            if not _click_next_page(driver):
                break
            WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, "search")))
            sleep(1)
    except Exception as e:
        print_error(f"[asin-fb] selenium fallback failed: {e}")
    finally:
        try:
            driver.quit()
        except Exception:
            pass
    return out


def fetch_asins_in_category(
    category: str,
    keyword: str,
    domain: str = "com",
    *,
    max_pages: int = None,
    max_per_category: int = None,
) -> list[dict]:
    disable_sd = get_env_bool("DISABLE_SCRAPINGDOG", False)
    api_key = None if disable_sd else get_env("SCRAPINGDOG_API_KEY")
    if not api_key:
        print("[!] SCRAPINGDOG_API_KEY not set; using SerpAPI fallback")
        domain_full = to_domain(domain)
        base_query = f"{keyword} {category}".strip()
        rows = (
            []
            if get_env_bool("DISABLE_SERPAPI", False)
            else _serpapi_fetch_asins(base_query, domain_full, pages=2)
        )
        if not rows:
            print("[i] SerpAPI returned 0; trying Selenium fallback…")
            rows = _selenium_fetch_asins(base_query, domain, pages=3, limit=max_per_category or 200)
        # attach category for context
        for r in rows:
            r["category"] = category
        print(f"[DEBUG] Parsed {len(rows)} ASINs from category '{category}' (fallback)")
        return rows

    # Configurable limits via env with sensible defaults
    if max_pages is None:
        max_pages = int(get_env("ASIN_SEARCH_MAX_PAGES", "10"))
    if max_per_category is None:
        max_per_category = int(get_env("ASIN_SEARCH_MAX_PER_CATEGORY", "200"))

    base_query = f"{keyword} {category}".strip()
    query_variants = [base_query, base_query.replace("headphones ", "").strip(), keyword]
    backoffs = [1, 3, 7]

    seen: set[str] = set()
    out: list[dict] = []
    domain_full = f"amazon.{domain}"

    for qv in query_variants:
        for page in range(1, max_pages + 1):
            url = (
                f"https://api.scrapingdog.com/amazon/search?api_key={api_key}"
                f"&query={requests.utils.quote(qv)}&domain={domain}&page={page}"
            )
            print(f"[DEBUG] Request URL: {url}")
            try:
                resp = _scrapingdog_fetch(url)
            except Exception as e:
                print(f"[!] Request error: {e}")
                break

            # Handle HTTP status first
            if resp.status_code == 403:
                print(f"[!] HTTP 403 on '{qv}' page {page}. Applying backoff…")
                for delay in backoffs:
                    time.sleep(delay)
                    try:
                        rr = _scrapingdog_fetch(url)
                    except Exception as e:
                        print(f"[!] Retry error: {e}")
                        continue
                    if rr.status_code == 200:
                        try:
                            jj = rr.json()
                        except Exception:
                            print("[!] Non-JSON response on retry; break")
                            break
                        if isinstance(jj, dict) and jj.get("success") is False:
                            msg = (jj.get("message") or "").lower()
                            if SCRAPINGDOG_LIMIT_PHRASE in msg:
                                print("[!] Scrapingdog limit reached. Switching to SerpAPI…")
                                rows = _serpapi_fetch_asins(qv, domain_full, pages=2)
                                for r in rows:
                                    r["category"] = category
                                return rows
                        rows = _extract_asins_from_scrapingdog_json(jj)
                        for r in rows:
                            a = r.get("asin")
                            if not a or a in seen:
                                continue
                            seen.add(a)
                            r["category"] = category
                            out.append(r)
                        # move to next page
                        break
                else:
                    print("[!] 403 persists after retries; switching query variant…")
                    break
                continue

            if resp.status_code != 200:
                print(f"[!] Failed to fetch page {page} for '{category}': HTTP {resp.status_code}")
                break

            # JSON branch
            try:
                data = resp.json()
            except Exception:
                print("[!] Non-JSON response; skipping page")
                continue

            if isinstance(data, dict) and data.get("success") is False:
                msg = (data.get("message") or "").lower()
                if SCRAPINGDOG_LIMIT_PHRASE in msg:
                    print("[!] Scrapingdog limit reached (JSON). Using SerpAPI fallback…")
                    rows = _serpapi_fetch_asins(qv, domain_full, pages=2)
                    for r in rows:
                        r["category"] = category
                    return rows
                print(f"[ERROR] API failure on page {page}: {data.get('message', 'No message')}")
                break

            items = _extract_asins_from_scrapingdog_json(data)
            found_on_page = len(items)
            new_on_page = 0

            for r in items:
                asin = r.get("asin")
                if not asin or asin in seen:
                    continue
                seen.add(asin)
                new_on_page += 1
                r["category"] = category
                out.append(r)
                if len(out) >= max_per_category:
                    print(f"[i] Reached max_per_category={max_per_category} for '{category}'.")
                    break

            print(
                f"[DEBUG] page={page}: found={found_on_page}, new={new_on_page}, total={len(out)}"
            )

            if new_on_page == 0 or len(out) >= max_per_category:
                break

        if out:
            # got something with this variant, stop trying others
            break

    if not out:
        print("[→] Falling back to SerpAPI due to empty result / persistent errors…")
        rows = (
            []
            if get_env_bool("DISABLE_SERPAPI", False)
            else _serpapi_fetch_asins(base_query, domain_full, pages=2)
        )
        if not rows:
            print("[i] SerpAPI returned 0; trying Selenium fallback…")
            rows = _selenium_fetch_asins(base_query, domain, pages=3, limit=max_per_category)
        for r in rows:
            r["category"] = category
        print(f"[DEBUG] Parsed {len(rows)} ASINs from category '{category}' (fallback)")
        return rows

    print(f"[DEBUG] Parsed {len(out)} ASINs from category '{category}'")
    return out


def run_asin_search(session):
    keyword = input("Enter keyword to search categories (e.g., 'headphones'): ").strip()
    categories = fetch_amazon_categories(keyword)
    if not categories:
        print("[!] No categories found.")
        return

    print("\nMatched categories:")
    for i, cat in enumerate(categories, 1):
        print(f"{i}) {cat}")

    selected = input("Select categories by numbers (comma-separated): ").strip()
    try:
        selected_indices = [int(i.strip()) - 1 for i in selected.split(",")]
        selected_categories = [categories[i] for i in selected_indices if 0 <= i < len(categories)]
    except Exception:
        print("[!] Invalid selection.")
        return

    domain = get_env("DEFAULT_MARKETPLACE", "com")
    max_pages = int(get_env("ASIN_SEARCH_MAX_PAGES", "10"))
    max_per_category = int(get_env("ASIN_SEARCH_MAX_PER_CATEGORY", "200"))
    print(
        f"[CFG] domain={domain} (normalized {to_domain(domain)}), max_pages={max_pages}, max_per_category={max_per_category}"
    )

    all_asins: list[dict] = []
    seen_global: set[str] = set()
    for cat in selected_categories:
        category_leaf = cat.split(" > ")[-1]
        results = fetch_asins_in_category(
            category_leaf,
            keyword,
            domain,
            max_pages=max_pages,
            max_per_category=max_per_category,
        )
        # global dedup across categories
        for r in results:
            a = r.get("asin")
            if a and a not in seen_global:
                seen_global.add(a)
                all_asins.append(r)

    if not all_asins:
        print("[!] No ASINs found.")
        return

    df = pd.DataFrame(all_asins)
    # Derive country code from domain (best-effort)
    domain_l = (domain or "com").lower()
    country_map = {
        "com": "US",
        "co.uk": "UK",
        "de": "DE",
        "fr": "FR",
        "co.jp": "JP",
        "ca": "CA",
        "in": "IN",
        "it": "IT",
        "es": "ES",
        "com.mx": "MX",
        "com.au": "AU",
    }
    country_code = country_map.get(domain_l, domain_l.upper())
    if "country" not in df.columns:
        df["country"] = country_code
    # Popularity: sort by review_count (desc) when available and keep top 100
    try:
        if "review_count" in df.columns:
            df["_rc"] = pd.to_numeric(
                df["review_count"].astype(str).str.replace(",", ""), errors="coerce"
            )
            df = df.sort_values(by=["_rc"], ascending=False).drop(columns=["_rc"])  # largest first
        df = df.head(100)
    except Exception:
        df = df.head(100)
    if "category" in df.columns and "category_path" not in df.columns:
        df = df.rename(columns={"category": "category_path"})
    session.df_asins = df
    print(f"[✅] Selected top {len(df)} ASINs (by popularity) and added to session.")

    # If a collection is already loaded, offer to replace its collection.csv
    try:
        is_loaded = session.is_collection_loaded()
    except Exception:
        is_loaded = bool(getattr(session, "collection_path", None))

    if is_loaded:
        ans = (
            input(
                "Update current collection with these ASINs? [R]eplace/[N]ew collection (default R): "
            )
            .strip()
            .lower()
        )
        if ans in ("", "r", "replace"):
            out = collection_csv(session.collection_path)
            before = 0
            if out.exists():
                try:
                    before = sum(1 for _ in open(out, "r", encoding="utf-8", errors="ignore")) - 1
                except Exception:
                    before = 0
            df.to_csv(out, index=False)
            print(f"[💾] Updated current collection.csv ({before} → {len(df)}) at {out}")
            return
        # else fall through to create a new collection

    # Create a new collection folder using auto-generated id
    timestamp = datetime.now().strftime("%y%m%d_%H%M")
    first_category = selected_categories[0].split(" > ")[-1]
    collection_name = f"{timestamp}__{first_category}"

    save_collection(session, collection_name, df)
    coll_path = getattr(session, "collection_path", None)
    print(
        f"[💾] Collection saved. See: {coll_path / 'collection.csv' if coll_path else 'DATA/<...>/collection.csv'}"
    )
