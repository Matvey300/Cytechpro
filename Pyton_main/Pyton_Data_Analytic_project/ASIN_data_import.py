# ASIN_data_import.py
# All comments in English.

from __future__ import annotations

import os
import time
from typing import List, Dict, Optional

import pandas as pd
import requests

AMZ_DOMAIN = {"US": "amazon.com", "UK": "amazon.co.uk"}

# ----------------------------
# Internal helpers
# ----------------------------

def _serpapi_key() -> Optional[str]:
    k = os.getenv("SERPAPI_KEY") or os.getenv("SERP_API_KEY")
    return k.strip() if k else None

def _amazon_domain(region: str) -> str:
    return AMZ_DOMAIN.get((region or "US").upper(), AMZ_DOMAIN["US"])

def _serpapi_search_page(query: str, region: str, page: int = 1, timeout: int = 20) -> Optional[Dict]:
    """
    Calls SerpApi Amazon engine for a single page of results.
    IMPORTANT: for Amazon engine the keyword parameter is 'k', not 'q'.
    """
    key = _serpapi_key()
    if not key:
        raise RuntimeError("SERPAPI_KEY is not set in environment")

    url = "https://serpapi.com/search.json"
    params = {
        "engine": "amazon",
        "amazon_domain": _amazon_domain(region),
        "k": query,
        "page": page,
        "api_key": key,
    }
    try:
        r = requests.get(url, params=params, timeout=timeout)
        if r.status_code != 200:
            # Soft-fail with None; caller will stop on empty responses
            return None
        return r.json()
    except Exception:
        return None

def _extract_asins(data: Dict) -> List[str]:
    """
    Extract ASINs from SerpApi response.
    Primary source: 'organic_results'[i]['asin'].
    """
    asins: List[str] = []
    if not isinstance(data, dict):
        return asins
    for item in (data.get("organic_results") or []):
        asin = item.get("asin")
        if asin:
            asins.append(str(asin).strip())
    # Dedup preserving order
    seen = set()
    out = []
    for a in asins:
        if a and a not in seen:
            seen.add(a)
            out.append(a)
    return out

# ----------------------------
# Public API expected by app.py
# ----------------------------

def collect_asins(category_path: str, region: str = "US", top_k: int = 100, max_pages: int = 10, sleep_sec: float = 1.0) -> pd.DataFrame:
    """
    Collect up to top_k unique ASINs for the given category_path by querying SerpApi Amazon search.
    We use the human-readable 'category_path' as the search phrase (works robustly enough for MVP).

    Returns DataFrame with columns:
      - asin
      - category_path
    """
    if not category_path or not str(category_path).strip():
        raise ValueError("category_path must be a non-empty string")

    region = (region or "US").upper()
    bag: List[str] = []
    for p in range(1, max_pages + 1):
        data = _serpapi_search_page(query=str(category_path), region=region, page=p)
        page_asins = _extract_asins(data or {})
        # Stop if no results returned
        if not page_asins:
            break
        # Accumulate unique
        for a in page_asins:
            if a not in bag:
                bag.append(a)
                if len(bag) >= int(top_k or 100):
                    break
        if len(bag) >= int(top_k or 100):
            break
        # be polite with the API
        time.sleep(float(sleep_sec or 0))

    df = pd.DataFrame({"asin": bag})
    df["category_path"] = str(category_path)
    return df

def collect_asins_for_categories(categories: List[str], region: str = "US", top_k: int = 100) -> pd.DataFrame:
    """
    Convenience helper: collect ASINs for multiple categories and concat.
    """
    frames: List[pd.DataFrame] = []
    for cat in categories or []:
        try:
            df = collect_asins(category_path=cat, region=region, top_k=top_k)
            frames.append(df)
        except Exception:
            # Skip failing category silently (MVP behavior)
            continue
    if not frames:
        return pd.DataFrame(columns=["asin", "category_path"])
    # If same ASIN appears across categories, keep first occurrence
    all_df = pd.concat(frames, ignore_index=True)
    all_df = all_df.drop_duplicates(subset=["asin"], keep="first")
    return all_df

# ----------------------------
# CLI (optional quick test)
# ----------------------------

if __name__ == "__main__":
    import sys as _sys
    if len(_sys.argv) < 2:
        print("Usage: python ASIN_data_import.py 'Category Path' [US|UK] [top_k]")
        _sys.exit(1)
    cat = _sys.argv[1]
    reg = _sys.argv[2] if len(_sys.argv) > 2 else "US"
    k = int(_sys.argv[3]) if len(_sys.argv) > 3 else 50
    print(f"Collecting up to {k} ASIN for [{cat}] in {reg}…")
    df_test = collect_asins(category_path=cat, region=reg, top_k=k)
    print(df_test.head())
    print(f"Total collected: {len(df_test)}")