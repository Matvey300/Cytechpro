# core/asin_search.py

import os
import time
import re
import requests
import pandas as pd
from typing import List, Dict, Optional
from pathlib import Path
import json
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

SERP_API_KEY = os.getenv("SERPAPI_API_KEY")
SCRAPINGDOG_API_KEY = os.getenv("SCRAPINGDOG_API_KEY")

SERPAPI_CATEGORY_URL = "https://serpapi.com/search.json"
SCRAPINGDOG_SEARCH_URL = "https://api.scrapingdog.com/amazon/search"

def fetch_amazon_categories(keyword: str) -> List[str]:
    """Fetch Amazon categories for a given keyword using SerpAPI."""
    if not SERP_API_KEY:
        logger.error("Missing SERPAPI_API_KEY environment variable")
        raise RuntimeError("Missing SERPAPI_API_KEY")

    params = {
        "engine": "amazon",
        "amazon_domain": "amazon.com",
        "q": keyword,
        "api_key": SERP_API_KEY
    }

    try:
        response = requests.get(SERPAPI_CATEGORY_URL, params=params, timeout=30)
        response.raise_for_status()
        
        data = response.json()
        
        if "error" in data:
            logger.error(f"SerpAPI returned error: {data['error']}")
            return []
        
        categories = []
        for block in data.get("category_results", []):
            if isinstance(block, dict) and "title" in block:
                categories.append(block["title"])
        
        logger.info(f"Found {len(categories)} categories for keyword: {keyword}")
        return categories
        
    except requests.exceptions.RequestException as e:
        logger.error(f"Request failed: {e}")
        return []
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse JSON response: {e}")
        return []

def fetch_asins_in_category(category_path: str, keyword: str, marketplace: str, max_pages: int = 5) -> List[Dict]:
    """Fetch ASINs in a given category using ScrapingDog API."""
    if not SCRAPINGDOG_API_KEY:
        logger.error("Missing SCRAPINGDOG_API_KEY environment variable")
        raise RuntimeError("Missing SCRAPINGDOG_API_KEY")

    results = []
    
    for page in range(1, max_pages + 1):
        params = {
            "api_key": SCRAPINGDOG_API_KEY,
            "type": "search",
            "amazon_domain": f"amazon.{marketplace}",
            "query": keyword,
            "page": page,
            "category": category_path
        }

        try:
            response = requests.get(SCRAPINGDOG_SEARCH_URL, params=params, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            items = data.get("results", [])
            
            for item in items:
                if item.get("type") != "search_product":
                    continue

                asin = extract_asin_from_url(item.get("url", ""))
                if asin:
                    results.append({
                        "asin": asin,
                        "title": item.get("title", ""),
                        "rating": item.get("stars", 0),
                        "review_count": item.get("total_reviews", "0"),
                        "category_path": category_path,
                        "country": marketplace,
                        "url": item.get("url", "")
                    })
            
            logger.info(f"Processed page {page} for category {category_path}, found {len(items)} items")
            
            # Be respectful to the API with a delay
            time.sleep(1.5)
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed for {category_path} page {page}: {e}")
            break
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response for {category_path} page {page}: {e}")
            break
        except Exception as e:
            logger.error(f"Unexpected error for {category_path} page {page}: {e}")
            break

    return results

def extract_asin_from_url(url: str) -> Optional[str]:
    """Extract ASIN from Amazon product URL."""
    if not url:
        return None
    
    # Try multiple patterns to extract ASIN
    patterns = [
        r"/dp/([A-Z0-9]{10})",  # Standard pattern
        r"/gp/product/([A-Z0-9]{10})",  # Alternative pattern
        r"ASIN=([A-Z0-9]{10})"  # ASIN parameter pattern
    ]
    
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    
    return None

def save_asins(df: pd.DataFrame, out_dir: Path):
    """Save ASINs to CSV file."""
    if df.empty:
        logger.warning("No ASINs to save")
        return
    
    # Clean and process data
    df_clean = df.drop_duplicates(subset="asin").copy()
    
    # Clean review_count column
    df_clean["review_count"] = (
        df_clean["review_count"]
        .astype(str)
        .str.replace(",", "")
        .str.extract(r"(\d+)", expand=False)
        .fillna("0")
        .astype(int)
    )
    
    # Sort by review count (descending)
    df_sorted = df_clean.sort_values(by="review_count", ascending=False)
    
    # Save all results and top 100
    out_path = out_dir / "search_results.csv"
    top_100_path = out_dir / "top_100_asins.csv"
    
    df_sorted.to_csv(out_path, index=False)
    df_sorted.head(100).to_csv(top_100_path, index=False)
    
    logger.info(f"Saved {len(df_sorted)} ASINs to {out_path}")
    logger.info(f"Saved top {min(len(df_sorted), 100)} ASINs to {top_100_path}")