# actions/asin_search.py
# Keyword-based ASIN search using SerpApi

from core.session_state import SessionState
from asin_search import fetch_amazon_categories, fetch_asins_in_category
import pandas as pd

def run_asin_search(session: SessionState):
    """Search and import ASINs by keyword and category."""
    keyword = input("Enter keyword to search categories (e.g., 'headphones'): ").strip()
    if not keyword:
        print("[!] Empty keyword.")
        return

    categories = fetch_amazon_categories(keyword)
    if not categories:
        print("[!] No categories found for that keyword.")
        return

    print("\nMatched categories:")
    for i, cat in enumerate(categories):
        print(f"{i + 1}) {cat}")

    try:
        selection = int(input("Select category by number: ")) - 1
        category_path = categories[selection]
    except Exception:
        print("[!] Invalid selection.")
        return

    print(f"\n→ Fetching ASINs in category: {category_path}")
    asin_data = fetch_asins_in_category(category_path)

    if not asin_data:
        print("[!] No ASINs found.")
        return

    df_new = pd.DataFrame(asin_data)
    df_new = df_new.drop_duplicates(subset="asin")

    session.df_asin = df_new
    session.collection_id = category_path.replace(" > ", "_")[:40]
    session.collection_path = session.get_collection_path()
    session.collection_path.mkdir(parents=True, exist_ok=True)

    out_path = session.collection_path / "asins.csv"
    df_new.to_csv(out_path, index=False)

    print(f"[✓] Collected {len(df_new)} ASINs.")
    print(f"[📁] Saved to: {out_path}")