import os
from core.asin_search import fetch_amazon_categories, fetch_asins_in_category

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
        results = fetch_asins_in_category(cat, keyword, "com")
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