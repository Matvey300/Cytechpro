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


def extract_total_reviews(soup: BeautifulSoup) -> int | None:
    """
    Best-effort extraction of total reviews/ratings from a product's review context.

    Supports both product page and reviews page structures.
    Returns an integer count if detected; otherwise None.
    """
    # 1) Reviews page: data-hook="total-review-count" ("10,132 global ratings")
    try:
        el = soup.select_one("[data-hook='total-review-count']")
        if el:
            text = el.get_text(" ", strip=True)
            digits = "".join(c for c in text if c.isdigit() or c == ",")
            if digits:
                return int(digits.replace(",", ""))
    except Exception:
        pass

    # 2) Product page: #acrCustomerReviewText ("1,234 ratings")
    try:
        el = soup.select_one("#acrCustomerReviewText")
        if el:
            text = el.get_text(" ", strip=True)
            digits = "".join(c for c in text if c.isdigit() or c == ",")
            if digits:
                return int(digits.replace(",", ""))
    except Exception:
        pass

    # 3) Reviews page: filter info section: "Showing 1-10 of 2,642 reviews"
    try:
        el = soup.select_one("[data-hook='cr-filter-info-review-rating-count']")
        if el:
            text = el.get_text(" ", strip=True)
        else:
            cont = soup.select_one("#filter-info-section")
            text = cont.get_text(" ", strip=True) if cont else ""
        if text:
            import re

            m = re.search(r"of\s+([\d,]+)\s+(reviews|ratings)", text, flags=re.IGNORECASE)
            if m:
                return int(m.group(1).replace(",", ""))
    except Exception:
        pass

    return None
