# === Module Status ===
# 📁 Module: scraper/product_info
# 📅 Last Reviewed: 2025-09-15 (finalized)
# 🔧 Status: 🟢 Complete
# 👤 Owner: Matvey
# 📝 Notes:
# - Replace print with print_info
# - Consider separating extraction methods for breadcrumb, price, and BSR
# =====================

import re
from typing import Any, Dict, Optional, Tuple

import pandas as pd
from bs4 import BeautifulSoup
from core.session_state import print_info


def extract_bsr_and_reviews(text: str) -> Tuple[Optional[str], Optional[str]]:
    bsr_match = re.search(r"Best Sellers Rank\s*#([\d,]+)", text)
    bsr = bsr_match.group(1).replace(",", "") if bsr_match else None
    review_count_match = re.search(r"Customer Reviews\s*([\d,]+)", text)
    review_count = review_count_match.group(1).replace(",", "") if review_count_match else None
    return bsr, review_count


def extract_product_details(soup: BeautifulSoup, row: pd.Series) -> Dict[str, Any]:
    """Extract product details from BeautifulSoup object."""
    category_path = "unknown"
    try:
        breadcrumb = soup.select_one("#wayfinding-breadcrumbs_feature_div ul.a-unordered-list")
        if breadcrumb:
            category_path = " > ".join(
                [
                    li.get_text(strip=True)
                    for li in breadcrumb.find_all("li")
                    if li.get_text(strip=True)
                ]
            )
    except Exception as e:
        print_info(f"[WARN] Failed to parse breadcrumb: {e}")

    if (
        (category_path == "unknown" or not category_path.strip())
        and "category_path" in row
        and pd.notna(row["category_path"])
    ):
        category_path = row["category_path"]

    # Price extraction
    price = None
    try:
        price_tag = soup.select_one("span.a-price span.a-offscreen")
        if price_tag:
            price = price_tag.text.strip()
    except Exception as e:
        print_info(f"[WARN] Failed to parse price: {e}")

    # BSR and review count extraction
    bsr = None
    review_count = None
    try:
        product_details = soup.select_one("#prodDetails")

        if product_details:
            text = product_details.get_text(separator=" ", strip=True)
            bsr, review_count = extract_bsr_and_reviews(text)
    except Exception as e:
        print_info(f"[WARN] Failed to parse product details: {e}")

    # Alternative extraction
    if not bsr or not review_count:
        try:
            detail_bullets = soup.select_one("#detailBullets_feature_div")
            if detail_bullets:
                text = detail_bullets.get_text(separator=" ", strip=True)
                alt_bsr, alt_reviews = extract_bsr_and_reviews(text)
                bsr = bsr or alt_bsr
                review_count = review_count or alt_reviews
        except Exception as e:
            print_info(f"[WARN] Failed to parse detail bullets: {e}")

    # Fallback to row values
    if not bsr and pd.notna(row.get("best_sellers_rank")):
        bsr = str(row["best_sellers_rank"])
    if not review_count and pd.notna(row.get("total_review_count")):
        review_count = str(row["total_review_count"])
    if not price and pd.notna(row.get("price")):
        price = str(row["price"])

    return {
        "category_path": category_path,
        "price": price,
        "bsr": bsr,
        "review_count": review_count,
    }
