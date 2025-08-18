# All comments in English.

import sys
from datetime import datetime
from pathlib import Path

from categories import search_categories_by_keyword, multi_select_categories, choose_marketplace
from asin_pipeline import collect_asin_data, save_asin_collection, list_saved_collections, load_asin_collection_by_id
from reviews_pipeline import collect_reviews_for_asins, append_and_dedupe_reviews
from storage.io_utils import new_out_dir, info_msg
from analytics.weekly_builder import build_weekly_master_from_reviews_only
from analytics.integrity import run_distortion_test
from analytics.impact import run_review_sales_impact
from analytics.extras import run_volatility_profile, run_sentiment_vs_rating_drift, run_top_drivers
from sales_sources.csv_loader import load_sales_csv_or_none

# Global switches
SUPPORTED_MARKETPLACES = ["US", "UK"]  # DE removed as agreed

def main_menu():
    """Top-level CLI loop."""
    while True:
        print("\n=== Amazon Reviews – CLI ===")
        print("1) Choose marketplace (US / UK)")
        print("2) Find categories by keyword (multi-select)")
        print("3) Collect ASINs (TOP-100 per chosen category; de-dup)")
        print("4) Collect reviews for chosen or previously saved ASIN collection (up to 500 per ASIN)")
        print("5) Run tests")
        print("6) Load a previously saved ASIN collection")
        print("7) Exit")

        choice = input("> Enter choice [1-7]: ").strip()
        if choice == "1":
            marketplace = choose_marketplace(SUPPORTED_MARKETPLACES)
            info_msg(f"Marketplace selected: {marketplace}")

        elif choice == "2":
            if 'marketplace' not in locals():
                marketplace = choose_marketplace(SUPPORTED_MARKETPLACES)
            keyword = input("> Enter keyword (e.g., 'headphones'): ").strip()
            candidates = search_categories_by_keyword(keyword, marketplace)
            chosen = multi_select_categories(candidates)
            if not chosen:
                print("No categories chosen.")
                continue
            info_msg(f"Selected categories ({len(chosen)}):")
            for c in chosen:
                print(" -", c)
            # Keep in session
            session['marketplace'] = marketplace
            session['categories'] = chosen

        elif choice == "3":
            if not session.get('categories') or not session.get('marketplace'):
                print("Please run steps (1) and (2) first.")
                continue
            out_dir_ts = new_out_dir(Path("Out"))
            all_asin_df = None
            for cat in session['categories']:
                df = collect_asin_data(category_path=cat, region=session['marketplace'], top_k=100)
                all_asin_df = df if all_asin_df is None else all_asin_df._append(df, ignore_index=True)
            # Drop duplicates by ASIN
            if all_asin_df is not None and 'asin' in all_asin_df.columns:
                all_asin_df = all_asin_df.drop_duplicates(subset=['asin']).reset_index(drop=True)

            coll_path = save_asin_collection(all_asin_df, registry_path=Path("storage") / "registry.json", out_dir_ts=out_dir_ts)
            session['out_dir_ts'] = out_dir_ts
            session['asin_df'] = all_asin_df
            print(f"ASIN collection saved: {coll_path}")

        elif choice == "4":
            # Choose source of ASINs: current session or previously saved
            use_saved = input("> Use previously saved collection? [y/N]: ").strip().lower() == 'y'
            if use_saved:
                reg = list_saved_collections(Path("storage") / "registry.json")
                if not reg:
                    print("No saved collections found.")
                    continue
                for item in reg:
                    print(f"[{item['id']}] {item['timestamp']} | {item['region']} | {len(item.get('categories', []))} cats | asin_count={item['asin_count']}")
                sel = input("> Enter collection id to load: ").strip()
                df_asin, out_dir_ts = load_asin_collection_by_id(Path("storage") / "registry.json", sel)
            else:
                if 'asin_df' not in session or session['asin_df'] is None:
                    print("No ASINs in session. Please collect ASINs first.")
                    continue
                df_asin = session['asin_df']
                out_dir_ts = session.get('out_dir_ts') or new_out_dir(Path("Out"))
                session['out_dir_ts'] = out_dir_ts

            # Collect reviews (sequential, up to 500 per ASIN)
            reviews_df, per_cat_counts = collect_reviews_for_asins(df_asin, max_reviews_per_asin=500, marketplace=session.get('marketplace', 'US'))
            dest = append_and_dedupe_reviews(out_dir_ts, reviews_df)

            # Report per category and total
            print("\nReview collection summary:")
            total = 0
            for cat, n in per_cat_counts.items():
                print(f" - {cat}: {n} reviews")
                total += n
            print(f"TOTAL: {total} reviews. Saved to: {dest}")

        elif choice == "5":
            # Tests menu
            print("\nSelect tests to run (comma separated):")
            print("1) Distortion probability (rating integrity)")
            print("2) Reviews → Sales impact (requires Sales CSV; skip if missing)")
            print("3) Extras:")
            print("   a) Volatility profile (if sales available)")
            print("   b) Sentiment vs rating drift (VADER, English only; US/UK)")
            print("   c) Top drivers (if sales available)")
            sel = input("> Enter e.g. '1,3b': ").strip().lower()

            # Load reviews from last out dir (session or ask)
            out_dir_ts = session.get('out_dir_ts')
            if not out_dir_ts:
                out_dir_ts = input("> Enter output directory of the run (e.g., Out/2025-08-18-120000): ").strip()
            out_dir_ts = Path(out_dir_ts)

            # Load sales CSV if present (stub)
            sales_df = load_sales_csv_or_none(out_dir_ts)  # optional; may return None

            # Build weekly master from reviews only (sales will be merged inside tests that need it)
            weekly_reviews = build_weekly_master_from_reviews_only(out_dir_ts)

            if '1' in sel:
                run_distortion_test(weekly_reviews, out_dir_ts)

            if '2' in sel:
                run_review_sales_impact(weekly_reviews, sales_df, out_dir_ts)

            if '3' in sel:
                # Volatility
                if 'a' in sel:
                    run_volatility_profile(weekly_reviews, sales_df, out_dir_ts)
                # Sentiment vs rating drift (English only)
                if 'b' in sel:
                    run_sentiment_vs_rating_drift(out_dir_ts, marketplaces=SUPPORTED_MARKETPLACES)
                # Top drivers
                if 'c' in sel:
                    run_top_drivers(weekly_reviews, sales_df, out_dir_ts)

        elif choice == "6":
            reg = list_saved_collections(Path("storage") / "registry.json")
            if not reg:
                print("No saved collections found.")
            else:
                for item in reg:
                    print(f"[{item['id']}] {item['timestamp']} | {item['region']} | {len(item.get('categories', []))} cats | asin_count={item['asin_count']}")
        elif choice == "7":
            print("Bye.")
            sys.exit(0)
        else:
            print("Invalid choice.")

if __name__ == "__main__":
    # Session state (simple in-memory dict)
    session = {}
    main_menu()