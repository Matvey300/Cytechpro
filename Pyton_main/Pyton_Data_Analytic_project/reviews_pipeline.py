# -*- coding: utf-8 -*-
import os
import re
import time
import shutil
import glob
import pandas as pd
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from dateutil import parser as dateparser
from datetime import datetime



from math import ceil
from pathlib import Path
from typing import Tuple, Dict

def collect_reviews_for_asins(
    df_asin: pd.DataFrame,
    max_reviews_per_asin: int,
    marketplace: str,
    out_dir: Path,
    collection_id: str
) -> Tuple[pd.DataFrame, Dict[str, int]]:
    all_reviews = []
    stats = {}

    collection_dir = out_dir / collection_id
    collection_dir.mkdir(parents=True, exist_ok=True)

    for _, row in df_asin.iterrows():
        asin = row['asin']
        print(f"[{asin}] Starting review collection...")

        try:
            driver = start_amazon_browser_session(asin, collection_dir)

            print(f"[{asin}] Loading first reviews page...")
            url = f"https://www.amazon.{marketplace}/product-reviews/{asin}/?pageNumber=1"
            driver.get(url)
            time.sleep(3)  # Wait for page to load

            reviews = []
            page_hashes = set()
            current_page = 1
            max_pages = ceil(max_reviews_per_asin / 10)  # Amazon shows 10 reviews per page

            while current_page <= max_pages:
                html = driver.page_source
                soup = BeautifulSoup(html, 'html.parser')

                page_hash = hash(html)
                if page_hash in page_hashes:
                    print(f"[{asin}] Detected repeated page content at page {current_page}, stopping pagination.")
                    break
                page_hashes.add(page_hash)
                print(f"[{asin}] Parsing page {current_page}...")

                # Extract category path
                category_path = 'unknown'
                breadcrumb = soup.select_one('#wayfinding-breadcrumbs_feature_div ul.a-unordered-list')
                if breadcrumb:
                    category_path = ' > '.join([li.get_text(strip=True) for li in breadcrumb.find_all('li') if li.get_text(strip=True)])
                if category_path == 'unknown' and 'category_path' in row and pd.notna(row['category_path']):
                    category_path = row['category_path']

                # Extract price, BSR, review_count from product details on first page
                price = None
                bsr = None
                review_count = None
                if current_page == 1:
                    # Try to extract price
                    price_tag = soup.select_one('span.a-price span.a-offscreen')
                    if price_tag:
                        price = price_tag.text.strip()

                    # Try to extract BSR and review count from product details
                    product_details = soup.select_one('#prodDetails')
                    if product_details:
                        text = product_details.get_text(separator=' ', strip=True)
                        bsr_match = re.search(r'Best Sellers Rank\s*#([\d,]+)', text)
                        if bsr_match:
                            bsr = bsr_match.group(1).replace(',', '')
                        review_count_match = re.search(r'Customer Reviews\s*([\d,]+)', text)
                        if review_count_match:
                            review_count = review_count_match.group(1).replace(',', '')

                    # Alternative location for BSR and review count
                    if not bsr or not review_count:
                        detail_bullets = soup.select_one('#detailBullets_feature_div')
                        if detail_bullets:
                            text = detail_bullets.get_text(separator=' ', strip=True)
                            bsr_match = re.search(r'Best Sellers Rank\s*#([\d,]+)', text)
                            if bsr_match:
                                bsr = bsr_match.group(1).replace(',', '')
                            review_count_match = re.search(r'Customer Reviews\s*([\d,]+)', text)
                            if review_count_match:
                                review_count = review_count_match.group(1).replace(',', '')

                # Parse reviews on current page
                review_divs = soup.select('div[data-hook="review"]')
                for div in review_divs:
                    review = {}
                    review['asin'] = asin
                    review['marketplace'] = marketplace
                    review['category_path'] = category_path
                    review['scan_timestamp'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

                    # Review title
                    title_tag = div.select_one('a[data-hook="review-title"] span')
                    review['review_title'] = title_tag.text.strip() if title_tag else None

                    # Review rating
                    rating_tag = div.select_one('i[data-hook="review-star-rating"] span')
                    if not rating_tag:
                        rating_tag = div.select_one('i[data-hook="cmps-review-star-rating"] span')
                    if rating_tag:
                        rating_text = rating_tag.text.strip()
                        review['review_rating'] = float(rating_text.split()[0])
                    else:
                        review['review_rating'] = None

                    # Review author
                    author_tag = div.select_one('span.a-profile-name')
                    review['review_author'] = author_tag.text.strip() if author_tag else None

                    # Review date
                    date_tag = div.select_one('span[data-hook="review-date"]')
                    if date_tag:
                        try:
                            review['review_date'] = dateparser.parse(date_tag.text.strip()).date()
                        except Exception:
                            review['review_date'] = None
                    else:
                        review['review_date'] = None

                    # Review text
                    review_text_tag = div.select_one('span[data-hook="review-body"] span')
                    review['review_text'] = review_text_tag.text.strip() if review_text_tag else None

                    # Add price, BSR, review count to each review (only from first page)
                    if current_page == 1:
                        review['price'] = price
                        review['best_sellers_rank'] = bsr
                        review['total_review_count'] = review_count
                    else:
                        review['price'] = None
                        review['best_sellers_rank'] = None
                        review['total_review_count'] = None

                    reviews.append(review)

                # Check if next page exists and navigate
                try:
                    next_button = driver.find_element(By.CSS_SELECTOR, 'li.a-last a')
                    if not next_button.is_enabled():
                        print(f"[{asin}] Next button disabled on page {current_page}, ending pagination.")
                        break
                    prev_html_hash = page_hash
                    next_button.click()
                    time.sleep(3)  # Wait for page to load

                    # Confirm page changed by checking new HTML hash
                    new_html = driver.page_source
                    new_hash = hash(new_html)
                    if new_hash == prev_html_hash:
                        print(f"[{asin}] Page did not change after clicking next on page {current_page}, stopping.")
                        break

                    current_page += 1
                except NoSuchElementException:
                    print(f"[{asin}] No next button found on page {current_page}, ending pagination.")
                    break

            df = pd.DataFrame(reviews)
            if not df.empty:
                all_reviews.append(df)
                cat_label = category_path if category_path != 'unknown' else 'unknown'
                stats[cat_label] = stats.get(cat_label, 0) + len(df)
                print(f"[{asin}] Collected {len(df)} reviews.")
            else:
                print(f"[{asin}] No reviews found.")

            driver.quit()

        except Exception as e:
            print(f"[!] Failed to collect for ASIN {asin}: {e}")

    if all_reviews:
        df_all = pd.concat(all_reviews, ignore_index=True)
        timestamp = datetime.now().strftime("%y%m%d_%H%M")
        filename = f"{timestamp}__{collection_id}__reviews.csv"
        df_all.to_csv(collection_dir / filename, index=False)
        print(f"Saved all reviews to {collection_dir / filename}")
    else:
        df_all = pd.DataFrame()
        print("No reviews collected for any ASIN.")

    return df_all, stats

def start_amazon_browser_session(asin: str, save_dir: Path):
    from selenium.webdriver.chrome.service import Service
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.chrome.webdriver import WebDriver
    import subprocess

    print(f"[{asin}] Preparing browser session...")

    chrome_options = Options()
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_experimental_option("detach", True)

    # Check if Chrome is already running
    if subprocess.run(["pgrep", "-i", "chrome"], capture_output=True, text=True).stdout.strip():
        print("[❌] Chrome is already running. Please close all Chrome windows and try again.")
        raise RuntimeError("Chrome already running.")

    use_temp_profile = input("Do you want to proceed with a temporary profile? (y/n): ").strip().lower()
    if use_temp_profile not in ("y", "n"):
        print("[!] Invalid input. Defaulting to 'y'.")
        use_temp_profile = "y"

    if use_temp_profile == "y":
        print("[🧪] Starting Chrome with a temporary profile...")
        chrome_options.add_argument("--user-data-dir=/tmp/temp_chrome_profile")
    else:
        print("[ℹ️] You must provide a custom user profile if not using temporary. Exiting.")
        raise RuntimeError("Custom profile not supported yet.")

    service = Service()
    driver = webdriver.Chrome(service=service, options=chrome_options)

    driver.get("https://www.amazon.com/")
    input("🔐 Please log in to Amazon in the opened Chrome window, then press [Enter] to continue...")

    return driver