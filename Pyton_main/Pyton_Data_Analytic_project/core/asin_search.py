# core/asin_search.py

import os
import time
import requests
import pandas as pd
from typing import List, Dict
from pathlib import Path
import json

SERP_API_KEY = os.getenv("SERPAPI_API_KEY")
SCRAPINGDOG_API_KEY = os.getenv("SCRAPINGDOG_API_KEY")

SERPAPI_CATEGORY_URL = "https://serpapi.com/search.json"
SCRAPINGDOG_SEARCH_URL = "https://api.scrapingdog.com/amazon/search"

def fetch_amazon_categories(keyword: str) -> list[str]:
    api_key = os.getenv("SERPAPI_API_KEY")

    print(f"🕵️  [DEBUG] Python видит следующий API ключ: '{api_key}'")

    if not api_key:
        raise RuntimeError("Missing SERPAPI_API_KEY")

    params = {
        "engine": "amazon",
        "amazon_domain": "amazon.com",
        "k": keyword,
        "api_key": api_key
    }

    r = requests.get(SERPAPI_CATEGORY_URL, params=params)
    if r.status_code != 200:
        print(f"[WARN] SerpAPI status: {r.status_code}")
        return []

    data = r.json()
    print(f"[DEBUG] Raw text response: {r.text}")
    print("[DEBUG] SerpAPI raw response:", json.dumps(data, indent=2))

    if "error" in data:
        print(f"[ERROR] SerpAPI returned error: {data['error']}")
        return []
    print("[DEBUG] SerpAPI raw response:", json.dumps(data, indent=2))
    categories = []

    for block in data.get("category_results", []):
        if isinstance(block, dict) and "title" in block:
            categories.append(block["title"])

    return categories

def fetch_asins_in_category(category_path: str, keyword: str, marketplace: str, max_pages: int = 5) -> List[Dict]:
    if not SCRAPINGDOG_API_KEY:
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
            resp = requests.get(SCRAPINGDOG_SEARCH_URL, params=params, timeout=20)
            data = resp.json().get("results", [])

            for item in data:
                if item.get("type") != "search_product":
                    continue

                asin = extract_asin_from_url(item.get("url", ""))
                if asin:
                    results.append({
                        "asin": asin,
                        "title": item.get("title"),
                        "rating": item.get("stars"),
                        "review_count": item.get("total_reviews"),
                        "category_path": category_path,
                        "country": marketplace
                    })

            time.sleep(1.5)
        except Exception as e:
            print(f"[ERROR] {category_path} page {page}: {e}")
            break

    return results


def extract_asin_from_url(url: str) -> str:
    try:
        parts = url.split("/dp/")
        if len(parts) > 1:
            return parts[1].split("/")[0]
    except:
        return None


def save_asins(df: pd.DataFrame, out_dir: Path):
    out_path = out_dir / "search_results.csv"
    df = df.drop_duplicates(subset="asin")
    df["review_count"] = pd.to_numeric(df["review_count"].str.replace(",", ""), errors="coerce")
    df = df.sort_values(by="review_count", ascending=False)
    df.head(100).to_csv(out_path, index=False)
    print(f"[✅] Saved top {min(len(df), 100)} ASINs to {out_path}")
