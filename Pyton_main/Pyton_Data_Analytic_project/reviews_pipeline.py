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
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC



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

    base_dir = out_dir / collection_id

    chrome_options = Options()
    chrome_options.add_argument(f'--user-data-dir={os.getenv("CHROME_USER_DATA_DIR")}')
    chrome_options.add_argument(f'--profile-directory={os.getenv("CHROME_PROFILE_DIR")}')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--disable-gpu')

    print("[🔐] Please log into Amazon in the opened Chrome window.")
    try:
        driver = webdriver.Chrome(options=chrome_options)
    except Exception as e:
        print("[❌] Failed to start Chrome with the selected user profile.")
        print("This usually happens if Chrome is already running with that profile.")
        print("Please close all Chrome windows or choose another profile.")
        choice = input("Do you want to try with a temporary profile instead? (y/n): ").strip().lower()
        if choice == "y" or choice == "":
            temp_options = Options()
            temp_options.add_argument("--no-sandbox")
            temp_options.add_argument("--disable-dev-shm-usage")
            temp_options.add_argument("--disable-gpu")
            try:
                driver = webdriver.Chrome(options=temp_options)
                print("[🧪] Started Chrome with temporary profile. You will need to log in manually.")
            except Exception as e2:
                print("[❌] Failed to launch Chrome even with temporary profile.")
                raise e2
        else:
            raise e
    driver.get(f"https://www.amazon.{marketplace}/")
    driver.get(f"https://www.amazon.{marketplace}/product-reviews/{df_asin.iloc[0]['asin']}?sortBy=recent")
    input("Press [Enter] when you have completed login...")  

    all_reviews = []
    per_cat_counts = {}

    for i, row in df_asin.iterrows():
        asin = row["asin"]
        cat = row.get("category_path", "unknown")
        print(f"[{i+1}/{len(df_asin)}] Fetching reviews for ASIN: {asin}")

        reviews = []
        page = 1
        seen_ids = set()

        # Count previous reviews for this ASIN from the output file, if any
        html_dir = base_dir / "RawData"
        if base_dir.exists() and not base_dir.is_dir():
            raise RuntimeError(f"[ERROR] Path '{base_dir}' exists as a file, not directory. Please remove it manually.")
        base_dir.mkdir(parents=True, exist_ok=True)
        html_dir.mkdir(parents=True, exist_ok=True)
        reviews_path = base_dir / "reviews.csv"
        previous_reviews_count = 0
        if reviews_path.exists() and reviews_path.stat().st_size > 0:
            try:
                existing = pd.read_csv(reviews_path)
                previous_reviews_count = existing[existing["asin"] == asin].shape[0]
            except Exception:
                previous_reviews_count = 0
        fetched = 0
        max_pages = int(((max_reviews_per_asin - previous_reviews_count) / 10) + 2)

        while page <= max_pages:
            url = f"https://www.amazon.{marketplace}/product-reviews/{asin}/?sortBy=recent"
            try:
                driver.get(url)
                try:
                    WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located((By.CLASS_NAME, "a-section"))
                    )
                except TimeoutException:
                    print(f"[WARN] No review block found after 10s for ASIN {asin}")
                    break
                html_path = html_dir / f"{collection_id}__{asin}_p{page}.html"
                with open(html_path, "w", encoding="utf-8") as f:
                    f.write(driver.page_source)
                soup = BeautifulSoup(driver.page_source, "html.parser")
                print(f"[DEBUG] Loaded URL: {driver.current_url}")
                print("[DEBUG] Page snippet:", driver.page_source[:1000])
                review_blocks = soup.find_all("div", class_="a-section review aok-relative")
                print(f"[DEBUG] Found {len(review_blocks)} review blocks on page {page}")
                input("[PAUSE] Please confirm the page loaded correctly in Chrome. Press Enter to continue...")

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

                print(f"[DEBUG] Skipped {len(review_blocks) - len(new_valid)} duplicate reviews on page {page}")

                if not new_valid:
                    print(f"[INFO] No new unique reviews found on page {page}. Stopping pagination.")
                    break

                reviews.extend(new_valid)
                fetched = len(reviews)
                time.sleep(1.5)

                try:
                    next_button = driver.find_element(By.CSS_SELECTOR, "li.a-last a")
                    driver.execute_script("arguments[0].scrollIntoView(true);", next_button)
                    next_button.click()
                    time.sleep(2)
                    new_url = driver.current_url
                    if new_url == url:
                        print("[WARN] Page did not change after clicking 'Next'. Stopping pagination.")
                        break
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

    if not all_reviews:
        print("[INFO] No reviews were collected for the selected ASINs. Check if login was successful or if reviews are available.")
    df_reviews = pd.DataFrame(all_reviews)
    base_dir.mkdir(parents=True, exist_ok=True)

    if reviews_path.exists() and reviews_path.stat().st_size > 0:
        try:
            existing = pd.read_csv(reviews_path)
            df_reviews = pd.concat([existing, df_reviews], ignore_index=True).drop_duplicates(subset=["id", "asin"])
        except pd.errors.EmptyDataError:
            print(f"[WARN] Existing file {reviews_path} is unreadable or empty. Overwriting.")

    df_reviews.to_csv(reviews_path, index=False)
    if df_reviews.shape[0] > 0:
        for asin in df_asin["asin"]:
            for html_file in html_dir.glob(f"{collection_id}__{asin}_p*.html"):
                html_file.unlink(missing_ok=True)
    return df_reviews, per_cat_counts