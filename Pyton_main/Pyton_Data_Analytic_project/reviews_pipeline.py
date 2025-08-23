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

def normalize_date(date_str):
    try:
        dt = dateparser.parse(date_str, dayfirst=False, fuzzy=True)
        return dt.date().isoformat()
    except Exception:
        return None

def parse_int(s):
    if not s:
        return None
    s = s.replace(',', '').replace('.', '')
    digits = re.findall(r'\d+', s)
    return int(''.join(digits)) if digits else None

def get_soup_from_file(filepath):
    with open(filepath, encoding='utf-8') as f:
        return BeautifulSoup(f.read(), 'html.parser')

def extract_review_blocks(soup):
    return soup.select('div[data-hook="review"]')

def extract_category_path(soup):
    breadcrumb = soup.select('ul.a-unordered-list.a-horizontal.a-size-small li span')
    if breadcrumb:
        return ' > '.join([el.get_text(strip=True) for el in breadcrumb])
    # fallback for some layouts
    nav = soup.select('a.a-link-normal.a-color-tertiary')
    if nav:
        return ' > '.join([el.get_text(strip=True) for el in nav])
    return None

def extract_bsr(soup):
    bsr = None
    bsr_block = soup.find('th', string=re.compile(r'Best Sellers Rank'))
    if bsr_block:
        bsr_text = bsr_block.find_next('td').get_text(" ", strip=True)
        bsr = re.search(r'#([\d,]+)', bsr_text)
        if bsr:
            return parse_int(bsr.group(1))
    # alt: try for new layout
    bsr_alt = soup.select_one('span#productDetails_detailBullets_sections1')
    if bsr_alt:
        m = re.search(r'#([\d,]+)', bsr_alt.get_text(" ", strip=True))
        if m:
            return parse_int(m.group(1))
    return None

def extract_price(soup):
    price = None
    selectors = [
        'span.a-price span.a-offscreen',
        'span#priceblock_ourprice',
        'span#priceblock_dealprice',
        'span#priceblock_saleprice'
    ]
    for sel in selectors:
        el = soup.select_one(sel)
        if el:
            price = el.get_text(strip=True)
            break
    if price:
        price_num = re.findall(r'[\d,.]+', price)
        if price_num:
            return float(price_num[0].replace(',', '').replace(' ', ''))
    return None

def extract_review_count(soup):
    el = soup.select_one('#acrCustomerReviewText')
    if el:
        return parse_int(el.get_text())
    # fallback
    el2 = soup.select_one('span[data-asin][data-rt]')
    if el2:
        return parse_int(el2.get_text())
    return None

def parse_review_div(div):
    asin = div.get('data-asin')
    date = None
    date_el = div.select_one('span[data-hook="review-date"]')
    if date_el:
        date = normalize_date(date_el.get_text())
    rating = None
    rating_el = div.select_one('i[data-hook="review-star-rating"], i[data-hook="cmps-review-star-rating"]')
    if rating_el:
        m = re.search(r'([0-9.]+)', rating_el.get_text())
        if m:
            rating = float(m.group(1))
    title = None
    title_el = div.select_one('a[data-hook="review-title"] span')
    if not title_el:
        title_el = div.select_one('a[data-hook="review-title"]')
    if title_el:
        title = title_el.get_text(strip=True)
    body = None
    body_el = div.select_one('span[data-hook="review-body"] span')
    if not body_el:
        body_el = div.select_one('span[data-hook="review-body"]')
    if body_el:
        body = body_el.get_text(strip=True)
    verified = False
    verified_el = div.select_one('span[data-hook="avp-badge"]')
    if verified_el and 'Verified Purchase' in verified_el.get_text():
        verified = True
    helpful = 0
    helpful_el = div.select_one('span[data-hook="helpful-vote-statement"]')
    if helpful_el:
        m = re.search(r'(\d+)', helpful_el.get_text().replace(',', ''))
        if m:
            helpful = int(m.group(1))
        elif 'One' in helpful_el.get_text():
            helpful = 1
    author = None
    author_el = div.select_one('span.a-profile-name')
    if author_el:
        author = author_el.get_text(strip=True)
    location = None
    date_location_el = div.select_one('span[data-hook="review-date"]')
    if date_location_el:
        m = re.search(r'on (.*)', date_location_el.get_text())
        if m:
            location = m.group(1)
    return {
        'asin': asin,
        'date': date,
        'rating': rating,
        'title': title,
        'body': body,
        'verified_purchase': verified,
        'helpful_votes': helpful,
        'author': author,
        'location': location
    }

def download_amazon_reviews(
    asin,
    collection_dir,
    recent_only=False,
    max_pages=None,
    delay=2.0,
    cleanup=True
):
    os.makedirs(collection_dir, exist_ok=True)
    raw_dir = os.path.join(collection_dir, "RawData")
    os.makedirs(raw_dir, exist_ok=True)

    # Selenium setup
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    driver = webdriver.Chrome(options=chrome_options)

    # Load product page for meta
    product_url = f"https://www.amazon.com/dp/{asin}"
    driver.get(product_url)
    time.sleep(delay)
    page_source = driver.page_source
    product_soup = BeautifulSoup(page_source, 'html.parser')
    category_path = extract_category_path(product_soup)
    bsr = extract_bsr(product_soup)
    price = extract_price(product_soup)
    review_count = extract_review_count(product_soup)

    # Go to reviews
    reviews_url = f"https://www.amazon.com/product-reviews/{asin}/?reviewerType=all_reviews"
    driver.get(reviews_url)
    time.sleep(delay)
    reviews = []
    page = 1
    while True:
        html = driver.page_source
        html_file = os.path.join(raw_dir, f"reviews_{asin}_p{page}.html")
        with open(html_file, "w", encoding="utf-8") as f:
            f.write(html)
        soup = BeautifulSoup(html, 'html.parser')
        review_blocks = extract_review_blocks(soup)
        if not review_blocks:
            break
        for div in review_blocks:
            r = parse_review_div(div)
            r['category_path'] = category_path
            r['price'] = price
            r['review_count'] = review_count
            r['bsr'] = bsr
            reviews.append(r)
        if max_pages and page >= max_pages:
            break
        try:
            next_btn = driver.find_element(By.CSS_SELECTOR, 'li.a-last a')
            if not next_btn.is_displayed() or not next_btn.is_enabled():
                break
            next_btn.click()
            page += 1
            time.sleep(delay)
        except NoSuchElementException:
            break
        except Exception:
            break
    driver.quit()

    # Parse dates and filter if recent_only
    if recent_only:
        # consider recent as last 365 days
        import datetime
        cutoff = datetime.date.today() - datetime.timedelta(days=365)
        reviews = [r for r in reviews if r['date'] and normalize_date(r['date']) and dateparser.parse(r['date']).date() >= cutoff]

    # Build DataFrame
    df = pd.DataFrame(reviews)
    # Normalize date column
    if not df.empty and 'date' in df.columns:
        df['date'] = df['date'].apply(normalize_date)
    csv_path = os.path.join(collection_dir, 'reviews.csv')
    df.to_csv(csv_path, index=False)
    print(f"Saved {len(df)} reviews to {csv_path}")

    # Cleanup temp html files
    if cleanup:
        shutil.rmtree(raw_dir, ignore_errors=True)



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
    for _, row in df_asin.iterrows():
        asin = row['asin']
        print(f"[{asin}] Collecting reviews...")

        try:
            download_amazon_reviews(
                asin=asin,
                collection_dir=str(collection_dir),
                recent_only=False,
                max_pages=ceil(max_reviews_per_asin / 10),
                delay=2.0,
                cleanup=True
            )

            review_path = collection_dir / 'reviews.csv'
            if review_path.exists():
                df = pd.read_csv(review_path)
                df['asin'] = asin
                all_reviews.append(df)

                cat = df['category_path'].dropna().unique()
                cat_label = cat[0] if len(cat) > 0 else 'unknown'
                stats[cat_label] = stats.get(cat_label, 0) + len(df)
        except Exception as e:
            print(f"[!] Failed to collect for ASIN {asin}: {e}")

    if all_reviews:
        df_all = pd.concat(all_reviews, ignore_index=True)
        df_all.to_csv(collection_dir / 'reviews.csv', index=False)
    else:
        df_all = pd.DataFrame()

    return df_all, stats
