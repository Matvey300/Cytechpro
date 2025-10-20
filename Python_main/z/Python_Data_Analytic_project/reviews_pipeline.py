import os
import time
from pathlib import Path
from typing import List, Tuple

import pandas as pd
import requests
from core.env_check import check_required_env_vars

check_required_env_vars()

HEADERS = {"Accept": "application/json"}

BASE_URL = "https://api.scrapingdog.com/amazon/reviews"


def collect_reviews_for_asins(
    df_asin: pd.DataFrame,
    max_reviews_per_asin: int,
    marketplace: str,
    out_dir: Path,
    collection_id: str,
) -> Tuple[pd.DataFrame, dict]:

    api_key = os.getenv("SCRAPINGDOG_API_KEY")
    if not api_key:
        raise RuntimeError("Missing SCRAPINGDOG_API_KEY")

    all_reviews: List[dict] = []
    per_cat_counts = {}

    for i, row in df_asin.iterrows():
        asin = row["asin"]
        cat = row.get("category_path", "unknown")
        print(f"[{i+1}/{len(df_asin)}] Fetching reviews for ASIN: {asin}")

        reviews = []
        page = 1
        fetched = 0
        seen_ids = set()

        while fetched < max_reviews_per_asin:
            params = {
                "api_key": api_key,
                "type": "review",
                "amazon_domain": f"amazon.{marketplace.lower()}",
                "asin": asin,
                "page": page,
            }

            try:
                r = requests.get(BASE_URL, headers=HEADERS, params=params, timeout=20)
                if r.status_code != 200:
                    print(f"[WARN] Status {r.status_code} for ASIN {asin}")
                    break

                data = r.json()
                new_reviews = data.get("reviews", [])

                # Stop if no new reviews found
                new_valid = [r for r in new_reviews if r.get("id") not in seen_ids]
                if not new_valid:
                    break

                for r in new_valid:
                    r["asin"] = asin
                    r["category_path"] = cat
                    seen_ids.add(r.get("id"))
                    reviews.append(r)

                fetched += len(new_valid)
                page += 1
                time.sleep(1.5)

            except Exception as e:
                print(f"[ERROR] Failed to fetch page {page} for ASIN {asin}: {e}")
                break

        print(f"[✓] Collected {len(reviews)} reviews for ASIN: {asin}")
        all_reviews.extend(reviews)

        if cat not in per_cat_counts:
            per_cat_counts[cat] = 0
        per_cat_counts[cat] += len(reviews)

    df_reviews = pd.DataFrame(all_reviews)
    out_path = out_dir / "reviews.csv"

    if out_path.exists():
        existing = pd.read_csv(out_path)
        df_reviews = pd.concat([existing, df_reviews], ignore_index=True).drop_duplicates(
            subset=["id", "asin"]
        )

    df_reviews.to_csv(out_path, index=False)
    return df_reviews, per_cat_counts
