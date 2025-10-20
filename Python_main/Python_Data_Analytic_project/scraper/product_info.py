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

_BSR_PATTERNS = [
    r"Best Sellers Rank\s*[:#]?\s*#?([\d,]+)",
    r"Amazon Best Sellers Rank\s*[:#]?\s*#?([\d,]+)",
    r"#([\d,]+)\s+in\s",
]

_REVIEW_PATTERNS = [
    r"(\d[\d,]*)\s+(?:ratings|global ratings|customer reviews|global reviews)",
    r"Customer Reviews\s*[:]?\s*([\d,]+)",
    r"Customer ratings\s*[:]?\s*([\d,]+)",
]


def _extract_first_match(text: str, patterns: list[str]) -> Optional[str]:
    normalized = " ".join(text.split())
    for pattern in patterns:
        match = re.search(pattern, normalized, flags=re.IGNORECASE)
        if match:
            return match.group(1).replace(",", "")
    return None


def extract_bsr_and_reviews(text: str) -> Tuple[Optional[str], Optional[str]]:
    bsr = _extract_first_match(text, _BSR_PATTERNS)
    review_count = _extract_first_match(text, _REVIEW_PATTERNS)
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

    # Price extraction (robust; scope to product header to avoid carousels/ads)
    price = None
    try:
        # Prefer price within known product info containers
        containers = [
            "#cm_cr-product_info",
            "#cr-product-header",
            "#cr-summarization-attributes",
            "#dp-container",
            "#ppd",
            "#dp",
        ]
        price_selectors = [
            "#corePriceDisplay_desktop_feature_div .a-price .a-offscreen",
            "#apex_desktop .a-price .a-offscreen",
            "#tp_price_block_total_price_ww .a-offscreen",
            "#tp_price_block_total_price .a-offscreen",
            "#corePrice_feature_div .a-price .a-offscreen",
            "#priceblock_ourprice",
            "#priceblock_dealprice",
            "#price_inside_buybox",
            "span[data-a-color='price'] .a-offscreen",
        ]
        for root_sel in containers:
            root = soup.select_one(root_sel)
            if not root:
                continue
            for sel in price_selectors:
                tag = root.select_one(sel)
                if tag and tag.text and tag.text.strip():
                    candidate = tag.text.strip()
                    # Skip placeholders like Click to see price
                    low = candidate.lower()
                    if "click to see price" in low or "see price" in low:
                        continue
                    price = candidate
                    break
            if price:
                break
        # Fallback: limited global search inside price blocks only
        if not price:
            for sel in [
                "#corePriceDisplay_desktop_feature_div .a-price .a-offscreen",
                "#corePrice_feature_div .a-price .a-offscreen",
            ]:
                tag = soup.select_one(sel)
                if tag and tag.text and tag.text.strip():
                    price = tag.text.strip()
                    break
        # Fallback 2: hidden attach price used by ATC panel
        if not price:
            try:
                hidden = soup.select_one("#attach-base-product-price")
                if hidden and hidden.get("value"):
                    price = hidden.get("value").strip()
            except Exception:
                pass
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

    # Prefer explicit DP review count selectors if still missing
    dp_review_count: Optional[str] = None
    if not review_count:
        try:
            # Common DP selectors for total review count label
            for sel in (
                "#acrCustomerReviewText",
                "#averageCustomerReviews_feature_div #acrCustomerReviewText",
                "#acrCustomerReviewLink #acrCustomerReviewText",
                "span[data-hook='acr-total-review-count']",
            ):
                el = soup.select_one(sel)
                if el and el.get_text(strip=True):
                    txt = el.get_text(strip=True)
                    # Typical: "25,308 ratings" / "25,308 global ratings"
                    import re as _re

                    m = _re.search(r"(\d[\d,]*)", txt)
                    if m:
                        dp_review_count = m.group(1).replace(",", "")
                        break
        except Exception as e:
            print_info(f"[WARN] Failed to parse DP review count: {e}")
    # Prefer DP selector result over heuristic matches if available
    if dp_review_count:
        review_count = dp_review_count
    # As a last resort, scan full page text for a robust pattern (avoids picking small unrelated numbers)
    try:
        if not review_count or str(review_count).isdigit() and int(str(review_count)) < 100:
            import re as _re

            full = soup.get_text(separator=" ", strip=True)
            m = _re.search(
                r"(\d[\d,]*)\s+(?:ratings|global ratings|customer reviews|global reviews)",
                full,
                _re.I,
            )
            if m:
                cand = m.group(1).replace(",", "")
                # Prefer larger plausible number
                try:
                    if not review_count or int(cand) > int(str(review_count)):
                        review_count = cand
                except Exception:
                    review_count = cand
    except Exception:
        pass

    if not bsr:
        try:
            sales_rank = soup.select_one("#SalesRank")
            if sales_rank:
                text = sales_rank.get_text(separator=" ", strip=True)
                alt_bsr, _ = extract_bsr_and_reviews(text)
                bsr = bsr or alt_bsr
        except Exception as e:
            print_info(f"[WARN] Failed to parse SalesRank block: {e}")

    # Fallback to row values
    if not bsr and pd.notna(row.get("best_sellers_rank")):
        raw_value = str(row["best_sellers_rank"]).strip()
        if raw_value and raw_value != "0":
            bsr = raw_value
    if not review_count and pd.notna(row.get("total_review_count")):
        raw_value = str(row["total_review_count"]).strip()
        if raw_value:
            review_count = raw_value
    if not price and pd.notna(row.get("price")):
        price = str(row["price"])

    return {
        "category_path": category_path,
        "price": price,
        "bsr": bsr,
        "review_count": review_count,
    }


"""
# === Module Header ===
# 📁 Module: scraper/product_info.py
# 📅 Last Reviewed: 2025-10-15
# 🔧 Status: 🟢 Stable
# 👤 Owner: MatveyB
# 📝 Summary: Extracts product metadata from HTML (rating, price, etc.).
# =====================
"""
