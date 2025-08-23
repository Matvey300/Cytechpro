# -*- coding: utf-8 -*-
import os
import re
import time
import shutil
import glob
import pandas as pd
from bs4 import BeautifulSoup
from dateutil import parser as dateparser
from datetime import datetime
from core import SESSION

from math import ceil
from pathlib import Path
from typing import Tuple, Dict

from core.auth_amazon import start_amazon_browser_session
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

def collect_reviews_for_asins(
    df_asin: pd.DataFrame,
    max_reviews_per_asin: int,
    marketplace: str,
    out_dir: Path,
    collection_id: str
) -> Tuple[pd.DataFrame, Dict[str, int]]:
    all_reviews = []
    stats = {}
    snapshots = []

    collection_dir = out_dir / collection_id
    collection_dir.mkdir(parents=True, exist_ok=True)

    driver = None
    try:
        driver = start_amazon_browser_session(None, collection_dir)
        for _, row in df_asin.iterrows():
            asin = row['asin']
            print(f"[{asin}] Starting review collection...")

            try:
                print(f"[{asin}] Loading product page...")
                product_url = f"https://www.amazon.{marketplace}/dp/{asin}"
                driver.get(product_url)

                # Wait for full product page to load (#dp)
                try:
                    WebDriverWait(driver, 15).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, "#dp"))
                    )
                except TimeoutException:
                    print(f"[{asin}] Timeout while waiting for full product page to load (#dp).")
                    continue

                if "signin" in driver.current_url:
                    print(f"[{asin}] Redirected to Amazon login page. Session expired or unauthorized.")
                    continue

                try:
                    WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located((By.ID, "productTitle"))
                    )
                except TimeoutException:
                    print(f"[{asin}] Timeout while waiting for product page to load.")
                    continue

                product_html = driver.page_source
                print(f"[{asin}] Product page HTML length: {len(product_html)}")
                if len(product_html) < 10000:
                    print(f"[{asin}] Warning: Product page source may be incomplete.")

                rawdata_dir = collection_dir / "RawData"
                rawdata_dir.mkdir(parents=True, exist_ok=True)

                # Save product HTML for snapshot
                product_html_path = rawdata_dir / f"{asin}_product.html"
                with open(product_html_path, "w", encoding="utf-8") as f:
                    f.write(product_html)
                # Save screenshot of product page
                driver.save_screenshot(str(rawdata_dir / f"{asin}_product_screenshot.png"))

                soup = BeautifulSoup(product_html, 'html.parser')

                # Extract price, BSR, review_count, category_path here (переместить соответствующий блок сюда)
                category_path = 'unknown'
                breadcrumb = soup.select_one('#wayfinding-breadcrumbs_feature_div ul.a-unordered-list')
                if breadcrumb:
                    category_path = ' > '.join([li.get_text(strip=True) for li in breadcrumb.find_all('li') if li.get_text(strip=True)])
                if (category_path == 'unknown' or not category_path.strip()) and 'category_path' in row and pd.notna(row['category_path']):
                    category_path = row['category_path']

                price = None
                bsr = None
                review_count = None

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

                # If still missing, fallback to df_asin values if available
                if not bsr and 'best_sellers_rank' in row and pd.notna(row['best_sellers_rank']):
                    bsr = str(row['best_sellers_rank'])
                if not review_count and 'total_review_count' in row and pd.notna(row['total_review_count']):
                    review_count = str(row['total_review_count'])
                if not price and 'price' in row and pd.notna(row['price']):
                    price = str(row['price'])

                # Prepare snapshot dictionary
                snapshot = {
                    'asin': asin,
                    'marketplace': marketplace,
                    'category_path': category_path,
                    'price': price,
                    'best_sellers_rank': bsr,
                    'review_count': review_count,
                    'scan_timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }
                snapshots.append(snapshot)

                print(f"[{asin}] Loading first reviews page...")
                url = f"https://www.amazon.{marketplace}/product-reviews/{asin}/?sortBy=recent&pageNumber=1"
                driver.get(url)
                time.sleep(3)  # Wait for page to load

                reviews = []
                page_hashes = set()
                current_page = 1
                max_pages = ceil(max_reviews_per_asin / 10)  # Amazon shows 10 reviews per page
                pagination_limit_reached = False

                while current_page <= max_pages:
                    # Insert pagination max check at the top of the loop
                    if current_page >= max_pages:
                        print(f"[{asin}] Reached max page {current_page}, stopping pagination.")
                        break

                    html = driver.page_source

                    # Save raw HTML
                    raw_html_path = rawdata_dir / f"{asin}_p{current_page}.html"
                    with open(raw_html_path, "w", encoding="utf-8") as f:
                        f.write(html)

                    soup = BeautifulSoup(html, 'html.parser')

                    page_hash = hash(html)
                    if page_hash in page_hashes:
                        print(f"[{asin}] Detected repeated page content at page {current_page}, stopping pagination.")
                        break
                    page_hashes.add(page_hash)
                    print(f"[{asin}] Parsing page {current_page}...")

                    # Parse reviews on current page
                    review_divs = soup.select('[data-hook="review"]')
                    print(f"[{asin}] Found {len(review_divs)} review blocks on page {current_page}")
                    for div in review_divs:
                        review = {
                            'asin': asin,
                            'marketplace': marketplace,
                            'category_path': category_path,
                            'scan_timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            'review_title': None,
                            'review_rating': None,
                            'review_author': None,
                            'review_date': None,
                            'review_text': None,
                            'review_location': None,
                            'review_verified_purchase': None,
                            'review_helpful_votes': None,
                        }

                        try:
                            title_tag = div.select_one('a[data-hook="review-title"]') or div.select_one('span[data-hook="review-title"]')
                            if title_tag:
                                review['review_title'] = title_tag.text.strip()
                        except Exception as e:
                            print(f"[{asin}] Error parsing title: {e}")

                        try:
                            rating_tag = div.select_one('i[data-hook="review-star-rating"] span') or \
                                         div.select_one('i[data-hook="cmps-review-star-rating"] span')
                            if rating_tag:
                                rating_text = rating_tag.text.strip()
                                review['review_rating'] = float(rating_text.split()[0])
                        except Exception as e:
                            print(f"[{asin}] Error parsing rating: {e}")

                        try:
                            author_tag = div.select_one('span.a-profile-name')
                            if author_tag:
                                review['review_author'] = author_tag.text.strip()
                        except Exception as e:
                            print(f"[{asin}] Error parsing author: {e}")

                        try:
                            verified_tag = div.select_one('span[data-hook="avp-badge"]')
                            review['review_verified_purchase'] = bool(verified_tag and "Verified Purchase" in verified_tag.text)
                        except Exception as e:
                            print(f"[{asin}] Error parsing verified_purchase: {e}")

                        try:
                            date_tag = div.select_one('span[data-hook="review-date"]')
                            if date_tag:
                                date_text = date_tag.text.strip()
                                date_clean = re.sub(r'^Reviewed in .* on ', '', date_text)
                                review['review_date'] = dateparser.parse(date_clean).date()
                                if " in " in date_text:
                                    review['review_location'] = date_text.split(" in ")[-1].split(" on ")[0].strip()
                                else:
                                    review['review_location'] = None
                        except Exception as e:
                            print(f"[{asin}] Error parsing date: {e}")

                        try:
                            review_text_tag = div.select_one('span[data-hook="review-body"]')
                            if review_text_tag:
                                review['review_text'] = review_text_tag.text.strip()
                        except Exception as e:
                            print(f"[{asin}] Error parsing review text: {e}")

                        try:
                            helpful_tag = div.select_one('span[data-hook="helpful-vote-statement"]')
                            if helpful_tag:
                                txt = helpful_tag.get_text(strip=True)
                                if "One person found this helpful" in txt:
                                    review['review_helpful_votes'] = 1
                                elif "people found this helpful" in txt:
                                    review['review_helpful_votes'] = int(txt.split()[0].replace(",", ""))
                                else:
                                    review['review_helpful_votes'] = 0
                            else:
                                review['review_helpful_votes'] = 0
                        except Exception as e:
                            print(f"[{asin}] Error parsing helpful_votes: {e}")

                        reviews.append(review)

                    if not reviews:
                        print(f"[{asin}] Warning: No reviews extracted from page {current_page} despite presence of review blocks.")

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
                    except Exception:
                        print(f"[{asin}] No next button found in DOM or not clickable on page {current_page}. Possible end of pagination or selector issue.")
                        break

                df = pd.DataFrame(reviews)
                if not df.empty:
                    all_reviews.append(df)
                    cat_label = category_path if category_path != 'unknown' else 'unknown'
                    stats[cat_label] = stats.get(cat_label, 0) + len(df)
                    print(f"[{asin}] Collected {len(df)} reviews.")
                else:
                    print(f"[{asin}] No reviews found.")

            except Exception as e:
                print(f"[!] Failed to collect for ASIN {asin}: {e}")
            finally:
                page_hashes = set()

    except Exception as e:
        print(f"[!] Failed to start Amazon browser session: {e}")
    finally:
        if driver:
            driver.quit()

    if snapshots:
        snapshot_df = pd.DataFrame(snapshots)
        snapshot_filename = f"{datetime.now().strftime('%y%m%d_%H%M')}__{collection_id}__snapshot.csv"
        snapshot_path = collection_dir / snapshot_filename
        snapshot_df.to_csv(snapshot_path, index=False)
        print(f"[📈] Snapshot for {collection_id} saved: {snapshot_path}")

    if all_reviews:
        df_all = pd.concat(all_reviews, ignore_index=True)
        timestamp = datetime.now().strftime("%y%m%d_%H%M")
        filename = f"{timestamp}__{collection_id}__reviews.csv"
        df_all.to_csv(collection_dir / filename, index=False)
        print(f"[✅] Review collection complete. Saved to: {collection_dir / filename}")

        user_input = input("Do you want to delete raw HTML files? (y/n): ")
        if user_input.strip().lower() == 'y':
            shutil.rmtree(rawdata_dir)
    else:
        df_all = pd.DataFrame()
        print("No reviews collected for any ASIN.")

    # Save session state before returning
    from core import SESSION
    SESSION.df_reviews = df_all
    SESSION.df_snapshot = snapshot_df if snapshots else pd.DataFrame()
    SESSION.save()
    return df_all, stats