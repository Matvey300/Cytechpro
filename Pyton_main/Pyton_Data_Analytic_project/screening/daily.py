# screening/daily.py

import os
import time
import json
import re
import pandas as pd
from pathlib import Path
from datetime import datetime
from bs4 import BeautifulSoup

from core.auth_amazon import get_chrome_driver_with_profile
from api.scrapingdog import fetch_amazon_product_page

def parse_snapshot_fields(html: str) -> dict:
    """Extract price, rating, and review count from HTML using BeautifulSoup."""
    soup = BeautifulSoup(html, "html.parser")

    def extract_price():
        for selector in ["#priceblock_ourprice", "#priceblock_dealprice", "span.a-price > span.a-offscreen"]:
            tag = soup.select_one(selector)
            if tag:
                return tag.get_text(strip=True)
        return None

    def extract_rating():
        tag = soup.select_one("#acrPopover") or soup.select_one("span[data-asin-review-stars-count]")
        if tag:
            return tag.get("title") or tag.get_text(strip=True)
        return None

    def extract_review_count():
        tag = soup.select_one("#acrCustomerReviewText") or soup.find("span", {"data-asin-review-count": True})
        if tag:
            return tag.get_text(strip=True)
        return None

    return {
        "price": extract_price(),
        "rating": extract_rating(),
        "review_count": extract_review_count()
    }

def run_daily_screening(df_asin: pd.DataFrame, out_dir: Path):
    """Run screening over all ASINs and store results in daily_snapshots.csv."""
    snapshot = []
    ts = int(time.time())
    date_str = datetime.utcnow().strftime("%Y-%m-%d %H:%M")

    for _, row in df_asin.iterrows():
        asin = str(row["asin"]).strip()
        try:
            html = fetch_amazon_product_page(asin=asin, marketplace="US")
            fields = parse_snapshot_fields(html)
            snapshot.append({
                "timestamp": ts,
                "datetime": date_str,
                "asin": asin,
                "price": fields["price"],
                "rating": fields["rating"],
                "review_count": fields["review_count"]
            })
            print(f"[✓] {asin}: P={fields['price']} | R={fields['rating']} | C={fields['review_count']}")
        except Exception as e:
            print(f"[!] Failed for {asin}: {e}")

    if not snapshot:
        print("[!] No data collected, skipping CSV save.")
        return

    df_new = pd.DataFrame(snapshot)
    out_path = out_dir / "daily_snapshots.csv"
    if out_path.exists():
        df_old = pd.read_csv(out_path)
        df_combined = pd.concat([df_old, df_new], ignore_index=True)
    else:
        df_combined = df_new

    df_combined.to_csv(out_path, index=False)
    print(f"[✓] Snapshot saved: {out_path}")