import json
import os
from datetime import datetime
from pathlib import Path

import pandas as pd
import requests
from core.collection_io import save_collection


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


def extract_asin_from_url(url):
    try:
        parts = url.split("/dp/")
        if len(parts) > 1:
            return parts[1].split("/")[0]
    except:
        return None


def fetch_asins_in_category(category, keyword, domain="com"):
    """
    Fetch ASINs using Scrapingdog API by keyword and category name.
    """

    api_key = os.getenv("SCRAPINGDOG_API_KEY")
    if not api_key:
        raise RuntimeError("SCRAPINGDOG_API_KEY environment variable not set.")

    query = f"{keyword} {category}"
    url = f"https://api.scrapingdog.com/amazon/search?api_key={api_key}&query={query}&domain={domain}&page=1"

    print(f"[DEBUG] Request URL: {url}")
    try:
        response = requests.get(url, timeout=15)
        print(f"[DEBUG] Raw response: {response.text}")
        if response.status_code != 200:
            print(f"[!] Failed to fetch ASINs for category '{category}': {response.status_code}")
            return []

        data = response.json()
        if not data.get("success", True):
            print(f"[ERROR] API reported failure: {data.get('message', 'No message')}")
            return []
        data = data.get("results", [])

        results = []

        for product in data:
            if product.get("type") != "search_product":
                continue
            asin = extract_asin_from_url(product.get("url", ""))
            if asin:
                results.append(
                    {
                        "asin": asin,
                        "title": product.get("title"),
                        "price": product.get("price"),
                        "rating": product.get("stars"),
                        "review_count": product.get("total_reviews"),
                        "category": category,
                    }
                )

        print(f"[DEBUG] Parsed {len(results)} ASINs from category '{category}'")
        return results

    except Exception as e:
        print(f"[ERROR] Exception during fetch: {e}")
        return []


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

    # Auto-generated collection name
    timestamp = datetime.now().strftime("%y%m%d_%H%M")
    first_category = selected_categories[0].split(" > ")[-1]
    collection_name = f"{timestamp}__{first_category}"

    save_collection(session, collection_name, df)
    print(f"[💾] Collection saved as: {collection_name}.csv")
