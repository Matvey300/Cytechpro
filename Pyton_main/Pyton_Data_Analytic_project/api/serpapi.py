# api/serpapi.py

import os
import requests
from typing import List, Optional

MARKETPLACES = {
    "US": "amazon.com",
    "UK": "amazon.co.uk"
}

SYNONYMS = {
    "headphones": ["headphones", "earbuds", "earbud", "earphone", "earphones", "headset"]
}

def get_serpapi_key() -> Optional[str]:
    """
    Retrieve the SerpApi key from environment variables.
    Returns None if not set.
    """
    return os.getenv("SERPAPI_KEY") or os.getenv("SERP_API_KEY")


def check_serpapi_quota() -> Optional[int]:
    """
    Check remaining request quota for SerpApi account.

    Returns:
        Remaining request count or None if failed.
    """
    key = get_serpapi_key()
    if not key:
        print("[WARN] SerpApi key not found.")
        return None
    try:
        r = requests.get("https://serpapi.com/account", params={"api_key": key}, timeout=10)
        if r.status_code == 200:
            data = r.json()
            return data.get("request_remaining")
        else:
            print(f"[WARN] Failed to check quota. Status {r.status_code}")
            return None
    except Exception as e:
        print(f"[ERROR] Quota check failed: {e}")
        return None


def fetch_amazon_categories(keyword: str, marketplace: str = "US") -> List[str]:
    """
    Fetch category suggestions from Amazon via SerpApi using a keyword.

    Args:
        keyword: Search keyword (e.g., 'headphones')
        marketplace: Marketplace code ('US', 'UK', ...)

    Returns:
        A list of category names/paths containing the keyword or its synonyms.
    """
    serpapi_key = get_serpapi_key()
    if not serpapi_key:
        print("[WARN] SerpApi key not found in environment.")
        return []

    amazon_domain = MARKETPLACES.get(marketplace.upper(), "amazon.com")

    url = "https://serpapi.com/search.json"
    params = {
        "engine": "amazon",
        "amazon_domain": amazon_domain,
        "keyword": keyword,
        "api_key": serpapi_key,
        "page": 1
    }

    try:
        response = requests.get(url, params=params, timeout=15)
        if response.status_code != 200:
            print(f"[WARN] SerpApi response code {response.status_code}")
            print(f"[DEBUG] URL: {response.url}")
            print(f"[DEBUG] Response body: {response.text[:500]}")
            return []
        data = response.json()
    except Exception as e:
        print(f"[ERROR] SerpApi request failed: {e}")
        return []

    kw = keyword.strip().lower()
    tokens = set([kw] + SYNONYMS.get(kw, []))

    def match(text: str) -> bool:
        norm = (text or "").lower()
        return any(t in norm for t in tokens)

    candidates = []

    for section in ("categories", "category_results", "category_information"):
        for item in data.get(section, []):
            name = item.get("name") or item.get("title") or item.get("category")
            if name and match(name):
                candidates.append(name.strip())

    for result in data.get("organic_results", []):
        breadcrumbs = result.get("breadcrumbs") or result.get("category_browse_nodes")
        if isinstance(breadcrumbs, list):
            path = " > ".join(str(b).strip() for b in breadcrumbs)
            if path and match(path):
                candidates.append(path)

    # Deduplicate while preserving order
    seen = set()
    output = []
    for cat in candidates:
        if cat not in seen:
            seen.add(cat)
            output.append(cat)

    if not output:
        print("[WARN] No matching categories found in SerpApi response.")

    return output