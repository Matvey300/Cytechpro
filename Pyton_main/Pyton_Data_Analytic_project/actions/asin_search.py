# actions/asin_search.py

from core.session_state import COLLECTIONS_DIR  # добавлен импорт
from core.session_state import SessionState
import pandas as pd


def run_asin_search(session: SessionState):
    """
    Search ASINs by keyword and category, save to session, and assign collection path
    """
    keyword = input("Enter keyword to search categories (e.g., 'headphones'): ").strip()
    if not keyword:
        print("[!] Keyword is required.")
        return

    from core.category_tree import fetch_matching_categories
    categories = fetch_matching_categories(keyword)
    if not categories:
        print("[!] No categories found.")
        return

    print("\nMatched categories:")
    for idx, cat in enumerate(categories):
        print(f"{idx+1}) {cat}")

    selected = input("Select categories by numbers (comma-separated): ").strip()
    if not selected:
        print("[!] No selection made.")
        return

    try:
        selected_idxs = [int(i)-1 for i in selected.split(",") if i.strip().isdigit()]
        selected_cats = [categories[i] for i in selected_idxs if 0 <= i < len(categories)]
    except Exception as e:
        print("[!] Invalid input.")
        return

    if not selected_cats:
        print("[!] No valid categories selected.")
        return

    from core.asin_fetcher import fetch_asins_in_category
    all_asins = []
    for cat in selected_cats:
        asins = fetch_asins_in_category(category=cat, keyword=keyword, domain="com")
        all_asins.extend(asins)

    if not all_asins:
        print("[!] No ASINs found.")
        return

    df_asin = pd.DataFrame(all_asins).drop_duplicates(subset="asin")
    print(f"[✅] Fetched {len(df_asin)} ASINs and added to current session.")

    session.df_asin = df_asin

    # 🔧 Добавлено — установка collection_id и collection_path
    collection_id = keyword.replace(" ", "_").lower()
    collection_path = COLLECTIONS_DIR / collection_id
    session.collection_id = collection_id
    session.collection_path = collection_path

    collection_path.mkdir(parents=True, exist_ok=True)
    df_asin.to_csv(collection_path / "asins.csv", index=False)
    print(f"[💾] Saved ASINs to {collection_path/'asins.csv'}")
