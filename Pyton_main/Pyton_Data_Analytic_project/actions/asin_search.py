# actions/asin_search.py

from core.session_state import SessionState
from core.asin_search import fetch_amazon_categories, fetch_asins_in_category
import pandas as pd

def run_asin_search(session: SessionState):
    """Search and import ASINs by keyword and selected categories."""

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

    selected_input = input("Select categories by numbers (comma-separated, e.g., 1,3): ").strip()
    try:
        selected_indexes = [int(i.strip()) - 1 for i in selected_input.split(",")]
        selected_categories = [categories[i] for i in selected_indexes if 0 <= i < len(categories)]
    except Exception:
        print("[!] Invalid selection.")
        return

    if not selected_categories:
        print("[!] No valid categories selected.")
        return

    all_asins = []
    for cat_path in selected_categories:
        print(f"\n→ Fetching ASINs in category: {cat_path}")
        asin_data = fetch_asins_in_category(
            category_path=cat_path,
            keyword=keyword,
            marketplace="com"
        )
        all_asins.extend(asin_data)

    if not all_asins:
        print("[!] No ASINs found.")
        return

    df_new = pd.DataFrame(all_asins).drop_duplicates(subset="asin")

    # Merge with existing if present
    if session.df_asin is not None:
        df_combined = pd.concat([session.df_asin, df_new], ignore_index=True)
        df_combined = df_combined.drop_duplicates(subset="asin")
    else:
        df_combined = df_new

    session.df_asin = df_combined

    # Ensure path is initialized
    if session.collection_path is None:
        print("[!] No active collection path. Please (re)load a collection first.")
        return

    session.collection_path.mkdir(parents=True, exist_ok=True)
    out_path = session.collection_path / "asins.csv"
    df_combined.to_csv(out_path, index=False)

    print(f"[✅] Collected total {len(df_combined)} ASINs in session.")
    print(f"[💾] Saved to: {out_path}")