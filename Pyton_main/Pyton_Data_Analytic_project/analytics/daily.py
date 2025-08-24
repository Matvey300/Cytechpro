# analytics/daily.py

import os
import time
import json
import pandas as pd
from pathlib import Path
from typing import List, Optional
from bs4 import BeautifulSoup

from core.auth_amazon import get_chrome_driver_with_profile
from datetime import datetime

from core.env_check import get_env_or_raise


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
    bsr_rank = None
    if bsr_text:
        import re
        match = re.search(r"#([\d,]+)", bsr_text)
        if match:
            bsr_rank = parse_number(match.group(1))

    return {
        "rating": rating,
        "review_count": review_count,
        "price": price,
        "bsr_rank": bsr_rank,
    }


def run_daily_screening(df_asin: pd.DataFrame, out_dir: Path):
    """
    For each ASIN in df_asin, scrape current rating / price / review count / BSR
    and store results in daily_snapshots.csv inside collection folder.
    """
    user_data_dir = get_env_or_raise("CHROME_USER_DATA_DIR")
    profile_dir = os.getenv("CHROME_PROFILE", "Profile 2")
    driver = get_chrome_driver_with_profile(user_data_dir, profile_dir)

    snapshot_rows = []
    utc_now = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")

    for asin in df_asin["asin"]:
        url = f"https://www.amazon.com/dp/{asin}"
        try:
            driver.get(url)
            time.sleep(3)  # give time to load

            metrics = extract_amazon_metrics(driver.page_source)
            row = {
                "asin": asin,
                "timestamp_utc": utc_now,
                **metrics
            }
            snapshot_rows.append(row)
            print(f"[✓] {asin} → {metrics}")
        except Exception as e:
            print(f"[!] Failed to extract metrics for {asin}: {e}")

    driver.quit()

    if not snapshot_rows:
        print("[WARN] No snapshots collected.")
        return

    snap_df = pd.DataFrame(snapshot_rows)
    out_path = out_dir / "daily_snapshots.csv"
    if out_path.exists():
        existing = pd.read_csv(out_path)
        snap_df = pd.concat([existing, snap_df], ignore_index=True)

    snap_df.to_csv(out_path, index=False)
    print(f"[INFO] Daily snapshot saved to {out_path}")