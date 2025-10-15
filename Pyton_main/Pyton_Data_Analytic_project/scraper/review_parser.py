"""
# === Module Header ===
# 📁 Module: scraper/review_parser.py
# 📅 Last Reviewed: 2025-10-15
# 🔧 Status: 🟢 Stable
# 👤 Owner: MatveyB
# 📝 Summary: Extracts reviews from review pages (legacy and compact templates).
# =====================
"""


def extract_reviews_from_html(soup, asin: str, marketplace: str, category_path: str) -> list[dict]:
    """Extract all reviews from a BeautifulSoup HTML page.

    Supports both legacy and compact templates:
      - [data-hook="review"] nodes (often <li>…)</n+      - [data-hook="cmps-review"] fallback
    """
    reviews: list[dict] = []
    nodes = soup.select('[data-hook="review"]')
    if not nodes:
        nodes = soup.select('[data-hook="cmps-review"]')
    if not nodes:
        print_info(f"[WARN] No review blocks found for ASIN {asin}")
        return reviews

    for node in nodes:
        review = _parse_review_div(node, asin, marketplace, category_path)
        reviews.append(review)

    return reviews


# === Module Status ===
# 📁 Module: scraper/review_parser
# 📅 Last Reviewed: 2025-09-15
# 🔧 Status: ✅ Completed
# 👤 Owner: Matvey Bosin
# 📝 Notes:
# - Replace print with print_info
# - Add fallback return for parse failure
# =====================

import re
from datetime import datetime
from typing import Any, Dict

import dateparser
from core.session_state import print_info


def _parse_review_div(div, asin: str, marketplace: str, category_path: str) -> Dict[str, Any]:
    """Parse a single review div and return review data."""
    review = {
        "asin": asin,
        "marketplace": marketplace,
        "category_path": category_path,
        "scan_timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "review_title": None,
        "review_rating": None,
        "review_author": None,
        "review_date": None,
        "review_text": None,
        "review_location": None,
        "review_verified_purchase": None,
        "review_helpful_votes": None,
        "review_id": None,
    }

    if div is None:
        print_info(f"[WARN] Review div is None for ASIN {asin}")
        return review

    try:
        rid = (div.get("id") or div.get("data-review-id") or "").strip()
        if rid.startswith("customer_review-"):
            rid = rid.replace("customer_review-", "").strip()
        review["review_id"] = rid
    except Exception as e:
        print_info(f"[WARN] Failed to parse review_id for ASIN {asin}: {e}")

    try:
        title_tag = div.select_one('a[data-hook="review-title"]') or div.select_one(
            'span[data-hook="review-title"]'
        )
        if title_tag:
            review["review_title"] = title_tag.text.strip()
    except Exception as e:
        print_info(f"[WARN] Failed to parse review_title for ASIN {asin}: {e}")

    try:
        rating_tag = div.select_one('i[data-hook="review-star-rating"] span') or div.select_one(
            'i[data-hook="cmps-review-star-rating"] span'
        )
        if rating_tag:
            rating_text = rating_tag.text.strip()
            review["review_rating"] = float(rating_text.split()[0])
    except Exception as e:
        print_info(f"[WARN] Failed to parse review_rating for ASIN {asin}: {e}")

    try:
        author_tag = div.select_one("span.a-profile-name")
        if author_tag:
            review["review_author"] = author_tag.text.strip()
    except Exception as e:
        print_info(f"[WARN] Failed to parse review_author for ASIN {asin}: {e}")

    try:
        verified_tag = div.select_one('span[data-hook="avp-badge"]')
        review["review_verified_purchase"] = bool(
            verified_tag and "Verified Purchase" in verified_tag.text
        )
    except Exception as e:
        print_info(f"[WARN] Failed to parse review_verified_purchase for ASIN {asin}: {e}")

    try:
        date_tag = div.select_one('span[data-hook="review-date"]')
        if date_tag:
            date_text = date_tag.text.strip()
            date_clean = re.sub(r"^Reviewed in .* on ", "", date_text)
            review["review_date"] = dateparser.parse(date_clean).date()
            if " in " in date_text:
                review["review_location"] = date_text.split(" in ")[-1].split(" on ")[0].strip()
    except Exception as e:
        print_info(f"[WARN] Failed to parse review_date for ASIN {asin}: {e}")

    try:
        review_text_tag = div.select_one('span[data-hook="review-body"]')
        if review_text_tag:
            review["review_text"] = review_text_tag.text.strip()
    except Exception as e:
        print_info(f"[WARN] Failed to parse review_text for ASIN {asin}: {e}")

    try:
        helpful_tag = div.select_one('span[data-hook="helpful-vote-statement"]')
        if helpful_tag:
            txt = helpful_tag.get_text(strip=True)
            if "One person found this helpful" in txt:
                review["review_helpful_votes"] = 1
            elif "people found this helpful" in txt:
                review["review_helpful_votes"] = int(txt.split()[0].replace(",", ""))
            else:
                review["review_helpful_votes"] = 0
        else:
            review["review_helpful_votes"] = 0
    except Exception as e:
        print_info(f"[WARN] Failed to parse review_helpful_votes for ASIN {asin}: {e}")

    return review
