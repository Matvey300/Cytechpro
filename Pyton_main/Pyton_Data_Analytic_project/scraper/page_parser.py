# === Module Status ===
# 📁 Module: scraper/page_parser
# 📅 Last Reviewed: 2025-09-15
# 🔧 Status: 🟠 Under Refactor
# 👤 Owner: Matvey
# 📝 Notes:
# - Replace print with print_info
# - Consider exposing number of parsed reviews for test hooks
# =====================

from typing import Dict, List, Set, Tuple

from bs4 import BeautifulSoup
from core.session_state import print_info
from scraper.html_saver import save_html
from scraper.review_parser import _parse_review_div


def _extract_reviews_from_soup(
    soup: BeautifulSoup,
    asin: str,
    marketplace: str,
    category_path: str,
    known_for_asin: Set[str],
    max_reviews_per_asin: int,
) -> List[Dict]:
    review_divs = soup.select('[data-hook="review"]')
    print_info(f"[{asin}] Found {len(review_divs)} review blocks.")

    new_reviews = []
    for div in review_divs:
        review = _parse_review_div(div, asin, marketplace, category_path)
        rid = str(review.get("review_id") or "").strip()

        if rid and rid not in known_for_asin:
            known_for_asin.add(rid)
            new_reviews.append(review)

            if len(new_reviews) >= max_reviews_per_asin:
                break

    return new_reviews


def _process_reviews_page(
    driver,
    asin: str,
    marketplace: str,
    category_path: str,
    known_for_asin: Set[str],
    max_reviews_per_asin: int,
    rawdata_dir,
    page_num: int,
) -> Tuple[List[Dict], int]:
    """Process a single page of reviews and return new reviews and count."""
    print_info(f"[{asin}] Processing page {page_num}...")

    html = driver.page_source
    save_html(rawdata_dir, asin, page_num, html)

    soup = BeautifulSoup(html, "html.parser")

    new_reviews = _extract_reviews_from_soup(
        soup, asin, marketplace, category_path, known_for_asin, max_reviews_per_asin
    )

    return new_reviews, len(new_reviews)


# === New utility: extract_total_reviews ===
from bs4 import BeautifulSoup


def extract_total_reviews(soup: BeautifulSoup) -> int:
    """
    Extract the total number of reviews from the product page soup.

    Args:
        soup (BeautifulSoup): Parsed HTML of the product page.

    Returns:
        int: Total number of reviews found, or 0 if not found.
    """
    try:
        review_text = soup.select_one("#acrCustomerReviewText")
        if review_text:
            text = review_text.get_text(strip=True)
            # Example text: "1,234 ratings"
            digits = "".join(c for c in text if c.isdigit() or c == ",")
            return int(digits.replace(",", ""))
    except Exception:
        pass
    return 0
