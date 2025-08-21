import os
import requests
import pandas as pd
import json
from pathlib import Path

def fetch_amazon_categories(keyword):
    """
    Load category tree from local JSON and return full paths where the keyword appears.
    """
    json_path = Path(__file__).parent.parent / "core" / "amazon_categories_us.json"
    with open(json_path, "r", encoding="utf-8") as f:
        tree = json.load(f)

    matches = []

    def recurse(subtree, path):
        for k, v in subtree.items():
            new_path = path + [k]
            if keyword.lower() in k.lower():
                matches.append(" > ".join(new_path))
            if isinstance(v, dict):
                recurse(v, new_path)

    recurse(tree, [])
    return matches

def fetch_asins_in_category(category, keyword, domain="com"):
    """
    Fetch ASINs in a given category and keyword using SerpAPI.
    """
    api_key = os.getenv("SERPAPI_API_KEY")
    if not api_key:
        raise RuntimeError("SERPAPI_API_KEY environment variable not set.")

    params = {
        "engine": "amazon",
        "amazon_domain": f"amazon.{domain}",
        "type": "search",
        "search_term": keyword,
        "category": category,
        "api_key": api_key
    }

    response = requests.get("https://serpapi.com/search", params=params)
    print(f"[DEBUG] Request URL: {response.url}")
    try:
        data = response.json()
        print("[DEBUG] Raw response:")
        print(json.dumps(data, indent=2))
    except Exception as e:
        print(f"[ERROR] Failed to parse JSON: {e}")
        return []

    if response.status_code != 200:
        print(f"[!] Failed to fetch ASINs for category '{category}': {response.status_code}")
        return []

    products = data.get("products", [])
    results = []
    for product in products:
        asin = product.get("asin")
        title = product.get("title")
        price = product.get("price")
        if asin:
            results.append({
                "asin": asin,
                "title": title,
                "price": price,
                "category": category
            })
    return results

def run_asin_search(session):
    keyword = input("Enter keyword to search categories (e.g., 'headphones'): ").strip()
    categories = fetch_amazon_categories(keyword)
    if not categories:
        print("[!] No categories found.")
        return

    print("\nMatched categories:")
    for i, cat in enumerate(categories, 1):
        print(f"{i}) {cat}")

    selected = input("Select categories by numbers (comma-separated): ").strip()
    try:
        selected_indices = [int(i.strip()) - 1 for i in selected.split(",")]
        selected_categories = [categories[i] for i in selected_indices if 0 <= i < len(categories)]
    except Exception:
        print("[!] Invalid selection.")
        return

    all_asins = []
    for cat in selected_categories:
        category_leaf = cat.split(" > ")[-1]
        results = fetch_asins_in_category(category_leaf, keyword, "com")
        all_asins.extend(results)

    if not all_asins:
        print("[!] No ASINs found.")
        return

    df = pd.DataFrame(all_asins)
    session.df_asin = df
    print(f"[✅] Fetched {len(df)} ASINs and added to current session.")
    
def validate_environment():
    required_vars = ["SCRAPINGDOG_API_KEY", "SERPAPI_API_KEY"]
    missing = [var for var in required_vars if not os.getenv(var)]

    if missing:
        print("[❌] Missing required environment variables:")
        for var in missing:
            print(f" - {var}")
        raise RuntimeError("Please set all required API keys as environment variables.")
    else:
        print("[✅] All required environment variables are set.")