# actions/create_collection.py

from typing import List

import pandas as pd
from api.serpapi import fetch_categories_strict
from ASIN_data_import import collect_asins
from core.session_state import SESSION
from storage.io_utils import save_asin_collection
from utils.console import ask, info, slugify, split_tokens, today_ymd, warn


def prompt_marketplace_inside() -> str:
    print("Select marketplace: 1) US   2) UK")
    ch = ask("> Enter 1 or 2: ").strip()
    return "UK" if ch == "2" else "US"


def create_collection_by_keyword_flow() -> None:
    """
    Keyword → categories (multi-select) → collect top-100 ASIN per category (via ASIN_data_import)
    """
    marketplace = prompt_marketplace_inside()
    keyword = ask("Enter keyword to search categories (e.g., 'headphones'): ").strip()
    if not keyword:
        warn("Empty keyword. Aborting.")
        return

    categories = fetch_categories_strict(keyword=keyword, marketplace=marketplace)
    if not categories:
        warn("No categories found. You may enter paths manually (e.g., 'Electronics > Headphones')")
        manual = ask("Enter categories (comma-separated): ").strip()
        categories = split_tokens(manual)

    if not categories:
        warn("No categories to process. Aborting.")
        return

    print("\nMatched categories:")
    for i, cat in enumerate(categories, 1):
        print(f"{i}) {cat}")

    sel = ask("Select categories by numbers (comma-separated): ").strip()
    idxs = [int(t) - 1 for t in split_tokens(sel) if t.isdigit() and 1 <= int(t) <= len(categories)]
    if not idxs:
        warn("No valid selections.")
        return

    selected = [categories[i] for i in idxs]

    all_rows: List[pd.DataFrame] = []
    for cat in selected:
        try:
            df = collect_asins(category_path=cat, region=marketplace, top_k=100)
            df["category_path"] = cat
            all_rows.append(df)
            info(f"Collected {len(df)} ASINs for: {cat}")
        except Exception as e:
            warn(f"Failed to collect ASINs for {cat}: {e}")

    if not all_rows:
        warn("No ASINs collected.")
        return

    df_all = pd.concat(all_rows, ignore_index=True).drop_duplicates(subset="asin")

    cid = f"{slugify(keyword)}_kw_{marketplace}_{today_ymd()}"
    path = save_asin_collection(
        df_all, cid, marketplace, meta_extra={"keyword": keyword, "categories": selected}
    )

    SESSION.collection_id = cid
    SESSION.collection_path = path
    SESSION.df_asin = df_all
    SESSION.marketplace = marketplace

    info(f"Saved collection: {cid} (ASINs={len(df_all)})")


def create_collection_manual_flow() -> None:
    """
    Manual ASIN input.
    """
    marketplace = prompt_marketplace_inside()
    name = ask("Collection base name (e.g., 'headphones'): ").strip() or "asin-collection"
    suffix = ask("Optional suffix (e.g., '_test'; press Enter to skip): ").strip()

    cid = f"{slugify(name)}{('-' + suffix) if suffix else ''}_{marketplace}_{today_ymd()}"

    print("Enter ASINs (comma or space separated):")
    raw = ask("> ").strip()
    asins = [a.strip().upper() for a in split_tokens(raw)]
    if not asins:
        warn("No ASINs provided.")
        return

    df = pd.DataFrame({"asin": asins})
    path = save_asin_collection(df, cid, marketplace)

    SESSION.collection_id = cid
    SESSION.collection_path = path
    SESSION.df_asin = df
    SESSION.marketplace = marketplace

    info(f"Saved manual collection: {cid} (ASINs={len(df)})")
