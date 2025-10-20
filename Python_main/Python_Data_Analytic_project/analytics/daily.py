"""
# === Module Header ===
# 📁 Module: analytics/daily.py
# 📅 Last Reviewed: 2025-10-15
# 🔧 Status: 🟠 Under Refactor
# 👤 Owner: MatveyB
# 📝 Summary: Daily scraping of product metrics and snapshot persistence.
# =====================
"""

import re
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

import pandas as pd
from bs4 import BeautifulSoup
from core.auth_amazon import get_chrome_driver_with_profile
from core.env_check import ENV_VARS, get_chrome_profile_env, get_env_or_raise
from core.marketplaces import to_domain
from core.session_state import print_info

# analytics/daily.py


def extract_amazon_metrics(html: str) -> dict:
    """
    Extract rating, price, review count, and BSR from a product page.
    """
    soup = BeautifulSoup(html, "html.parser")

    def extract_text(selector: str) -> Optional[str]:
        el = soup.select_one(selector)
        return el.get_text(strip=True) if el else None

    def parse_number(s: Optional[str]) -> Optional[float]:
        try:
            return float(s.replace(",", "").strip()) if s else None
        except Exception:
            return None

    # Extract values using typical selectors
    rating_text = extract_text("span.a-icon-alt")
    review_count_text = extract_text("#acrCustomerReviewText")
    price_text = extract_text(".a-price .a-offscreen")

    # Attempt to extract BSR (Best Sellers Rank)
    bsr_text = None
    details_div = soup.find(id="productDetails_detailBullets_sections1")
    if details_div:
        bsr_entry = details_div.find(string=lambda t: "Best Sellers Rank" in t)
        if bsr_entry:
            parent = bsr_entry.find_parent("tr")
            if parent:
                bsr_text = parent.get_text(strip=True)

    # Extract numeric parts
    rating = parse_number(rating_text.split()[0] if rating_text else None)
    review_count = parse_number(review_count_text.split()[0] if review_count_text else None)
    price = parse_number(price_text.replace("$", "") if price_text else None)

    # BSR can look like "#3,214 in Electronics (See Top 100)"
    bsr = None
    if bsr_text:
        match = re.search(r"#([\d,]+)", bsr_text)
        if match:
            bsr = parse_number(match.group(1))

    return {
        "rating": rating,
        "review_count": review_count,
        "price": price,
        "bsr": bsr,
    }


def run_daily_screening(session, base_path: Optional[Path] = None):
    """Scrape price/rating/review_count/BSR for session's ASINs and append to snapshot.csv.
    Uses a single Selenium session; saves Raw HTML+PNG for reproducibility.
    """
    from core.collection_io import collection_csv

    if getattr(session, "collection_path", None) is None:
        print_info("❌ No active collection. Load or create a collection first.")
        return

    out_dir = Path(base_path or session.collection_path)

    df_asin = getattr(session, "df_asin", None)
    if df_asin is None or "asin" not in getattr(df_asin, "columns", []):
        try:
            df_asin = pd.read_csv(collection_csv(session.collection_path))
            session.df_asin = df_asin
        except Exception as e:
            print_info(f"❌ Failed to load ASIN collection: {e}")
            return

    # Start Selenium with the configured user profile
    user_data_dir = get_env_or_raise("CHROME_USER_DATA_DIR")
    profile_dir = get_chrome_profile_env()
    driver = get_chrome_driver_with_profile(user_data_dir, profile_dir)

    # Snapshot-specific visibility override to avoid focus stealing
    # Use SNAPSHOT_VISIBILITY env if set; default to 'offscreen' for daily runs
    snap_mode = (ENV_VARS.get("SNAPSHOT_VISIBILITY") or "offscreen").lower()
    try:
        if snap_mode == "minimize":
            driver.minimize_window()
        elif snap_mode == "offscreen":
            driver.set_window_position(-2000, 0)
            driver.set_window_size(1280, 800)
        # headless requires pre-launch flag; warn but continue
    except Exception:
        pass

    snapshot_rows = []
    captured_at = datetime.utcnow().isoformat(timespec="seconds")
    raw_dir = out_dir / "Raw" / "snapshots" / captured_at.replace(":", "")
    raw_dir.mkdir(parents=True, exist_ok=True)

    # Normalize marketplace to a full domain (e.g., 'US' → 'amazon.com', 'com' → 'amazon.com')
    domain = to_domain(ENV_VARS.get("DEFAULT_MARKETPLACE", "com"))

    for asin in df_asin["asin"]:
        url = f"https://{domain}/dp/{asin}"
        try:
            driver.get(url)
            time.sleep(3)  # allow product page to render

            raw_html_path = raw_dir / f"{asin}.html"
            raw_png_path = raw_dir / f"{asin}.png"
            with open(raw_html_path, "w", encoding="utf-8") as f:
                f.write(driver.page_source)
            driver.save_screenshot(str(raw_png_path))

            metrics = extract_amazon_metrics(driver.page_source)
            row = {"asin": asin, "captured_at": captured_at, **metrics}
            snapshot_rows.append(row)
            print_info(f"[✓] {asin} → {metrics}")
        except Exception as e:
            print_info(f"[!] Failed to extract metrics for {asin}: {e}")

    try:
        driver.quit()
    except Exception as e:
        print_info(f"[WARN] Failed to quit driver: {e}")

    if not snapshot_rows:
        print_info("[WARN] No snapshots collected.")
        return

    snap_df = pd.DataFrame(snapshot_rows)
    out_path = out_dir / "snapshot.csv"
    if out_path.exists():
        existing = pd.read_csv(out_path)
        snap_df = pd.concat([existing, snap_df], ignore_index=True)
        if {"asin", "captured_at"}.issubset(snap_df.columns):
            snap_df = snap_df.drop_duplicates(subset=["asin", "captured_at"], keep="first")
        else:
            snap_df = snap_df.drop_duplicates(keep="first")

    snap_df.to_csv(out_path, index=False)
    print_info(f"[INFO] Daily snapshot saved to {out_path}")
