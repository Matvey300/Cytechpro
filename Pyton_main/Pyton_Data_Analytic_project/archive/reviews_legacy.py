from typing import List

from bs4 import BeautifulSoup
from core.session_state import SESSION
from scraper.driver import get_driver
from scraper.html_saver import ensure_rawdata_dir
from scraper.navigator import open_next_review_page, open_reviews_page
from scraper.product_info import extract_product_details
from scraper.review_parser import parse_reviews_from_page


def collect_reviews_for_asins(asins: List[str]):
    """Main pipeline: collect reviews for provided ASINs list."""
    driver = get_driver()
    all_reviews = []

    for asin in asins:
        try:
            print(f"[{asin}] Starting review collection...")

            row = SESSION.df_asins[SESSION.df_asins["asin"] == asin].iloc[0]
            marketplace = SESSION.marketplace
            max_pages = SESSION.reviews_max_pages
            max_reviews = SESSION.reviews_max_per_asin
            snapshot_ts = SESSION.snapshot_timestamp
            raw_dir = ensure_rawdata_dir(snapshot_ts, asin)

            open_reviews_page(driver, asin, marketplace)
            html = driver.page_source
            soup = BeautifulSoup(html, "html.parser")
            product_info = extract_product_details(soup, row)
            category_path = product_info["category_path"]

            seen_review_ids = set()
            page_num = 1
            reviews = []

            while page_num <= max_pages and len(reviews) < max_reviews:
                page_reviews, found_count = parse_reviews_from_page(
                    driver,
                    asin,
                    marketplace,
                    category_path,
                    seen_review_ids,
                    max_reviews,
                    raw_dir,
                    page_num,
                )
                if not page_reviews:
                    break
                reviews.extend(page_reviews)
                page_num += 1
                if not open_next_review_page(driver):
                    break

            print(f"[{asin}] ✅ Collected {len(reviews)} reviews (in {page_num} pages)")
            all_reviews.extend(reviews)

        except Exception as e:
            print(f"[!] Error collecting for {asin}: {e}")

    driver.quit()
    return all_reviews
