
import sys
import re

from pathlib import Path

from categories import choose_marketplace, search_categories_by_keyword, multi_select_categories
from asin_pipeline import collect_asin_data, save_asin_collection, list_saved_collections, load_asin_collection_by_id
from reviews_pipeline import collect_reviews_for_asins, append_and_dedupe_reviews
from storage.io_utils import new_out_dir, info_msg
from analytics.weekly_builder import build_weekly_master_from_reviews_only, merge_daily_into_weekly
from analytics.integrity import run_distortion_test
from analytics.impact import run_review_sales_impact
from analytics.extras import run_volatility_profile, run_sentiment_vs_rating_drift, run_top_drivers
from screening.daily import run_daily_screening, has_30_days_of_snapshots

SUPPORTED_MARKETPLACES = ["US", "UK"]  # DE removed by design

from datetime import datetime

def slugify(value: str) -> str:
    """
    Make a filesystem-safe slug from a string.
    Example: "Headphones & Ear-buds" -> "headphones-ear-buds"
    """
    value = str(value).strip().lower()
    # Replace any non-word character with dash
    value = re.sub(r"[^\w]+", "-", value)
    return value.strip("-")

def main_menu():
    session = {}

    while True:
        print("\n=== Amazon Reviews – CLI ===")
        print("1) Choose marketplace (US / UK)")
        print("2) Find categories by keyword (multi-select)")
        print("3) Collect ASINs (TOP-100 per chosen category; de-dup)")
        print("4) Collect reviews for chosen or previously saved ASIN collection (up to 500 per ASIN)")
        print("5) Run analytics/tests (integrity, volatility, sentiment)")
        print("6) Load a previously saved ASIN collection")
        print("7) Daily screening (price + BSR + new reviews): run now")
        print("8) Run Reputation - Sales correlation tests (available after 30 daily snapshots)")
        print("0) Exit")

        choice = input("> Enter choice [0-8]: ").strip()

        if choice == "1":
            session["marketplace"] = choose_marketplace(SUPPORTED_MARKETPLACES)
            info_msg(f"Marketplace selected: {session['marketplace']}")

        elif choice == "2":
            if "marketplace" not in session:
                session["marketplace"] = choose_marketplace(SUPPORTED_MARKETPLACES)
            kw = input("> Enter keyword (e.g., 'headphones'): ").strip()
            candidates = search_categories_by_keyword(kw, session["marketplace"])
            chosen = multi_select_categories(candidates)
            if not chosen:
                print("No categories chosen.")
                continue
            session["categories"] = chosen
            info_msg(f"Selected categories: {', '.join(chosen)}")

        elif choice == "3":
            if not session.get("categories") or not session.get("marketplace"):
                print("Please run steps (1) and (2) first.")
                continue

            # Build a human-readable collection_id: "<cat-last-node>_<REGION>_<YYYYMMDD>"
            # If multiple categories chosen, use first + "+N"
            cats = session["categories"]
            def _last_node(path: str) -> str:
                parts = [p.strip() for p in path.split(">") if p.strip()]
                return parts[-1] if parts else path
            base = _last_node(cats[0])
            suffix = f"+{len(cats)-1}" if len(cats) > 1 else ""
            region = session["marketplace"].upper()
            collection_id = f"{slugify(base)}{suffix}_{region}_{today_ymd()}"

            # Create Out/<collection_id>
            out_dir = new_out_dir_for_collection(Path("Out"), collection_id)
            session["out_dir_ts"] = out_dir
            session["collection_id"] = collection_id

            all_df = None
            for cat in cats:
                df = collect_asin_data(category_path=cat, region=session["marketplace"], top_k=100)
                all_df = df if all_df is None else all_df._append(df, ignore_index=True)
            if all_df is not None and "asin" in all_df.columns:
                all_df = all_df.drop_duplicates(subset=["asin"]).reset_index(drop=True)

            coll_path = save_asin_collection(
                all_df,
                registry_path=Path("storage")/"registry.json",
                out_dir_ts=out_dir,
                collection_id=collection_id
            )
            session["asin_df"] = all_df
            print(f"ASIN collection saved: {coll_path}")
            print(f"Collection ID: {collection_id} (folder: {out_dir})")

        elif choice == "4":
            use_saved = input("> Use previously saved collection? [y/N]: ").strip().lower() == "y"
            if use_saved:
                reg = list_saved_collections(Path("storage") / "registry.json")
                if not reg:
                    print("No saved collections found.")
                    continue

                print("\nSaved collections:")
                for i, item in enumerate(reg, 1):
                    cats = item.get('categories', [])
                    cats_display = ", ".join(cats[:2]) + ("..." if len(cats) > 2 else "")
                    print(f"{i}) ID={item.get('id')} | {item.get('timestamp')} | {item.get('region')} | "
                        f"{len(cats)} cats [{cats_display}] | ASINs={item.get('asin_count')}")

                sel = input("> Enter number OR collection ID to load: ").strip()
                df_asin, out_dir_ts = load_asin_collection_by_id(Path("storage") / "registry.json", sel)
                session["out_dir_ts"] = out_dir_ts
                session["asin_df"] = df_asin
                # Try to remember collection_id for later steps
                session["collection_id"] = str(sel) if not sel.isdigit() else reg[int(sel)-1].get("id")
            else:
                if "asin_df" not in session or session["asin_df"] is None:
                    print("No ASINs in session. Please collect ASINs first.")
                    continue
                df_asin = session["asin_df"]
                out_dir_ts = session.get("out_dir_ts") or new_out_dir_for_collection(Path("Out"), session.get("collection_id", today_ymd()))
                session["out_dir_ts"] = out_dir_ts

            reviews_df, per_cat_counts = collect_reviews_for_asins(
                df_asin, max_reviews_per_asin=500, marketplace=session.get("marketplace", "US")
            )
            dest = append_and_dedupe_reviews(session["out_dir_ts"], reviews_df)

            print("\nReview collection summary:")
            total = 0
            for cat, n in per_cat_counts.items():
                print(f" - {cat}: {n} reviews")
                total += n
            print(f"TOTAL: {total} reviews. Saved to: {dest}")
        elif choice == "5":
            out_dir_ts = session.get("out_dir_ts") or Path(input("> Enter Out/<timestamp> folder: ").strip())
            weekly_reviews = build_weekly_master_from_reviews_only(out_dir_ts)

            print("\nSelect tests (comma separated): 1) Integrity  2) Volatility  3) Sentiment vs rating  4) Top drivers (needs sales)")
            sel = input("> e.g. '1,2': ").strip()

            if "1" in sel:
                run_distortion_test(weekly_reviews, out_dir_ts)
            if "2" in sel:
                run_volatility_profile(weekly_reviews, sales_df=None, out_dir_ts=out_dir_ts)
            if "3" in sel:
                run_sentiment_vs_rating_drift(out_dir_ts, marketplaces=SUPPORTED_MARKETPLACES)
            if "4" in sel:
                run_top_drivers(weekly_reviews, sales_df=None, out_dir_ts=out_dir_ts)

        elif choice == "6":
            reg = list_saved_collections(Path("storage") / "registry.json")
            if not reg:
                print("No saved collections found.")
            else:
                print("\nSaved collections:")
                for i, item in enumerate(reg, 1):
                    cats = item.get('categories', [])
                    cats_display = ", ".join(cats[:2]) + ("..." if len(cats) > 2 else "")
                    print(f"{i}) ID={item.get('id')} | {item.get('timestamp')} | {item.get('region')} | "
                        f"{len(cats)} cats [{cats_display}] | ASINs={item.get('asin_count')}")
                sel = input("> Enter number OR collection ID to load into session (or press Enter to cancel): ").strip()
                if sel:
                    try:
                        df_asin, out_dir_ts = load_asin_collection_by_id(Path("storage") / "registry.json", sel)
                        session["out_dir_ts"] = out_dir_ts
                        session["asin_df"] = df_asin
                        session["collection_id"] = str(sel) if not sel.isdigit() else reg[int(sel)-1].get("id")
                        print(f"[INFO] Loaded into session: {session['collection_id']} ({out_dir_ts})")
                    except Exception as e:
                        print(f"Failed to load: {e}")
        elif choice == "7":
            if "asin_df" not in session or session["asin_df"] is None:
                print("No ASINs in session. Please collect or load a collection first.")
                continue
            out_dir_ts = session.get("out_dir_ts") or new_out_dir(Path("Out"))
            session["out_dir_ts"] = out_dir_ts
            run_daily_screening(session["asin_df"], marketplace=session.get("marketplace", "US"), out_dir_ts=out_dir_ts)

        elif choice == "8":
            if "out_dir_ts" not in session:
                print("No active output folder. Load a collection (6) or collect ASINs (3) first.")
                continue
            if not has_30_days_of_snapshots(session["out_dir_ts"]):
                print("Need at least 30 daily snapshots to unlock Reputation - Sales correlation tests.")
                continue
            # Build weekly from reviews + merge daily snapshots (BSR/price)
            weekly_reviews = build_weekly_master_from_reviews_only(session["out_dir_ts"])
            weekly_merged = merge_daily_into_weekly(session["out_dir_ts"], weekly_reviews)
            # Use BSR as sales proxy inside impact module (re-using function signature)
            run_review_sales_impact(weekly_merged, sales_df=None, out_dir_ts=session["out_dir_ts"])

        elif choice == "0":
            print("Bye.")
            sys.exit(0)
        else:
            print("Invalid choice.")

if __name__ == "__main__":
    main_menu()