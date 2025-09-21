# api/serpapi.py
# SerpApi integration for Amazon keyword → category extraction

import os
from typing import List, Optional

import requests
from core.marketplaces import MARKETPLACES
from core.synonyms import SYNONYMS


def get_serpapi_key() -> Optional[str]:
    """Retrieve SerpApi key from environment."""
    key = os.getenv("SERPAPI_KEY") or os.getenv("SERP_API_KEY")
    return key.strip() if key else None


def get_amazon_domain(marketplace: str) -> str:
    """Return Amazon domain for the given marketplace, defaulting to amazon.com."""
    return MARKETPLACES.get(marketplace.upper(), "amazon.com")


def check_serpapi_quota(api_key: str) -> dict:
    """
    Returns quota information from SerpApi:
    {'account_email': ..., 'total_requests': ..., 'request_searches_left': ...}
    """
    try:
        url = "https://serpapi.com/account-api"
        r = requests.get(url, params={"api_key": api_key}, timeout=10)
        return r.json()
    except Exception as e:
        return {"error": f"Quota check failed: {e}"}


def search_amazon_categories(keyword: str, marketplace: str) -> List[str]:
    """
    Call SerpApi (Amazon engine) and extract relevant category paths
    that match the keyword or its synonyms.
    """
    api_key = get_serpapi_key()
    if not api_key:
        return []

    url = "https://serpapi.com/search.json"
    params = {
        "engine": "amazon",
        "amazon_domain": get_amazon_domain(marketplace),
        "api_key": api_key,
        "k": keyword,
        "page": 1,
    }

    try:
        r = requests.get(url, params=params, timeout=15)
        if r.status_code != 200:
            return []
        data = r.json()
    except Exception:
        return []

    # Token set based on keyword + synonyms
    kw = keyword.strip().lower()
    tokens = set([kw] + SYNONYMS.get(kw, []))

    def _match(text: str) -> bool:
        s = (text or "").lower()
        return any(tok in s for tok in tokens)

    candidates: List[str] = []

    # 1. Category-like result blocks
    for block in ("category_results", "categories", "category_information"):
        for item in data.get(block, []):
            name = (item.get("name") or item.get("title") or item.get("category") or "").strip()
            if name and _match(name):
                candidates.append(name)

    # 2. Breadcrumb trails from organic results
    for res in data.get("organic_results", []):
        crumbs = res.get("breadcrumbs") or res.get("category_browse_nodes")
        if isinstance(crumbs, list) and crumbs:
            trail = " > ".join(str(c).strip() for c in crumbs if str(c).strip())
            if trail and _match(trail):
                candidates.append(trail)

    # Deduplicate, preserving order
    seen = set()
    out: List[str] = []
    for c in candidates:
        if c not in seen:
            seen.add(c)
            out.append(c)

    if not out:
        print(f"[WARN] No matching categories found for keyword '{keyword}' on {marketplace}")

    return out
