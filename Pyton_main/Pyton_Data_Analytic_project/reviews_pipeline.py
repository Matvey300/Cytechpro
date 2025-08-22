import os
import time
import json
import pandas as pd
import requests
from pathlib import Path
from typing import List, Tuple

from core.env_check import validate_environment

from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from core.auth_amazon import get_chrome_driver_with_profile, is_logged_in


HEADERS = {
    "Accept": "application/json"
}


def collect_reviews_for_asins(
    df_asin: pd.DataFrame,
    max_reviews_per_asin: int,
    marketplace: str,
    out_dir: Path,
    collection_id: str
) -> Tuple[pd.DataFrame, dict]:

    driver = get_chrome_driver_with_profile(
        user_data_dir=os.getenv("CHROME_USER_DATA_DIR"),
        profile_dir=os.getenv("CHROME_PROFILE_DIR")
    )

    if not is_logged_in(driver):
        raise RuntimeError("Not logged in to Amazon in Chrome profile.")

    all_reviews = []
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
            url = f"https://www.amazon.{marketplace}/product-reviews/{asin}/"
            try:
                driver.get(url)
                time.sleep(2)
                soup = BeautifulSoup(driver.page_source, "html.parser")
                review_blocks = soup.select("div[data-hook=review]")

                if not review_blocks:
                    print(f"[WARN] No reviews found on page {page} for ASIN {asin}")
                    break

                new_valid = []
                for block in review_blocks:
                    rid = block.get("id")
                    if rid and rid not in seen_ids:
                        seen_ids.add(rid)
                        review = {
                            "id": rid,
                            "asin": asin,
                            "category_path": cat,
                            "title": block.select_one("a[data-hook=review-title]").text.strip() if block.select_one("a[data-hook=review-title]") else "",
                            "rating": block.select_one("i[data-hook=review-star-rating]").text.strip() if block.select_one("i[data-hook=review-star-rating]") else "",
                            "text": block.select_one("span[data-hook=review-body]").text.strip() if block.select_one("span[data-hook=review-body]") else "",
                            "date": block.select_one("span[data-hook=review-date]").text.strip() if block.select_one("span[data-hook=review-date]") else ""
                        }
                        new_valid.append(review)

                if not new_valid:
                    break

                reviews.extend(new_valid)
                fetched += len(new_valid)
                time.sleep(1.5)

                try:
                    next_button = driver.find_element(By.CSS_SELECTOR, "li.a-last a")
                    driver.execute_script("arguments[0].scrollIntoView(true);", next_button)
                    next_button.click()
                    time.sleep(2)
                    page += 1
                except Exception as e:
                    print(f"[INFO] No next page or failed to click 'Next': {e}")
                    break

            except Exception as e:
                print(f"[ERROR] Failed to fetch page {page} for ASIN {asin}: {e}")
                break

        print(f"[✓] Collected {len(reviews)} reviews for ASIN: {asin}")
        all_reviews.extend(reviews)
        per_cat_counts[cat] = per_cat_counts.get(cat, 0) + len(reviews)

    df_reviews = pd.DataFrame(all_reviews)
    if out_dir.suffix == ".csv":
        out_dir = out_dir.parent
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "reviews.csv"

    if out_path.exists():
        existing = pd.read_csv(out_path)
        df_reviews = pd.concat([existing, df_reviews], ignore_index=True).drop_duplicates(subset=["id", "asin"])

    df_reviews.to_csv(out_path, index=False)
    return df_reviews, per_cat_counts