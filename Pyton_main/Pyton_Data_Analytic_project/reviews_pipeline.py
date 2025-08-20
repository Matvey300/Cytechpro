# reviews_pipeline.py

import os
import time
import json
import requests
import pandas as pd
from typing import Tuple

SCRAPINGDOG_API_URL = "https://api.scrapingdog.com/amazon/reviews"

class ScrapingdogReviewError(Exception):
    pass

def get_reviews_for_asin(asin: str, region: str, max_reviews: int = 500, max_pages: int = 20) -> pd.DataFrame:
    """
    Collect reviews for a single ASIN using Scrapingdog Amazon Reviews API.
    Returns a pandas DataFrame with raw review data.
    """
    api_key = os.getenv("SCRAPINGDOG_API_KEY")
    if not api_key:
        raise ScrapingdogReviewError("Missing SCRAPINGDOG_API_KEY in environment.")

    all_reviews = []
    seen_ids = set()

    for page in range(1, max_pages + 1):
        params = {
            "api_key": api_key,
            "type": "review",
            "asin": asin,
            "region": region.lower(),
            "page": page,
        }

        try:
            response = requests.get(SCRAPINGDOG_API_URL, params=params, headers={"Accept": "application/json"}, timeout=15)

            if response.status_code == 429:
                raise ScrapingdogReviewError("Rate limit exceeded. Check your API quota.")
            elif response.status_code != 200:
                raise ScrapingdogReviewError(f"Failed to fetch reviews (status code {response.status_code}).")

            data = response.json()
            reviews = data.get("reviews") or []
            if not reviews:
                break

            new_rows = []
            for r in reviews:
                rid = r.get("review_id")
                if rid and rid not in seen_ids:
                    seen_ids.add(rid)
                    r["asin"] = asin  # attach ASIN to each review
                    new_rows.append(r)

            all_reviews.extend(new_rows)

            if len(all_reviews) >= max_reviews:
                break

            time.sleep(1)  # avoid hammering API

        except Exception as e:
            raise ScrapingdogReviewError(f"Error fetching reviews for {asin} (page={page}): {e}")

    df = pd.DataFrame(all_reviews)
    return df


def collect_reviews_for_asins(
    df_asin: pd.DataFrame,
    marketplace: str,
    out_dir,
    collection_id: str,
    max_reviews_per_asin: int = 500,
) -> Tuple[pd.DataFrame, dict]:
    """
    Loop over ASINs in the provided DataFrame, collect reviews using Scrapingdog.
    Append results to CSV file incrementally and return combined DataFrame.
    """
    all_rows = []
    counts_per_asin = {}

    out_file = os.path.join(out_dir, "reviews.csv")
    seen_asins = set()

    if os.path.exists(out_file):
        try:
            existing = pd.read_csv(out_file)
            seen_asins = set(existing["asin"].unique())
            print(f"[INFO] Resuming review collection. Found existing reviews for {len(seen_asins)} ASINs.")
        except Exception:
            print(f"[WARN] Failed to read existing reviews file. Starting fresh.")

    for _, row in df_asin.iterrows():
        asin = str(row.get("asin")).strip()
        if not asin or asin in seen_asins:
            continue

        print(f"[INFO] Collecting reviews for ASIN {asin}…")
        try:
            df_reviews = get_reviews_for_asin(
                asin=asin,
                region=marketplace.lower(),
                max_reviews=max_reviews_per_asin,
            )
            if not df_reviews.empty:
                df_reviews.to_csv(out_file, mode="a", header=not os.path.exists(out_file), index=False)
                all_rows.append(df_reviews)
                counts_per_asin[asin] = len(df_reviews)
                print(f"[OK] {len(df_reviews)} reviews collected for {asin}.")
            else:
                print(f"[WARN] No reviews found for {asin}.")

        except ScrapingdogReviewError as e:
            print(f"[ERROR] {e}")
        except Exception as e:
            print(f"[ERROR] Unexpected error for {asin}: {e}")

    combined = pd.concat(all_rows, ignore_index=True) if all_rows else pd.DataFrame()
    return combined, counts_per_asin