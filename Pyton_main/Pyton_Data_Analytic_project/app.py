# All comments in English.

from pathlib import Path
import sys
from typing import List

from categories import (
    choose_marketplace,
    search_categories_by_keyword,
    multi_select_categories,
)

# We only need collect_asin_data; saving/loading we will handle here to avoid legacy helpers
from asin_pipeline import collect_asin_data

from reviews_pipeline import (
    collect_reviews_for_asins,
    append_and_dedupe_reviews,
)

from screening.daily import (
    run_daily_screening,
    has_30_days_of_snapshots,
)

from analytics.weekly_builder import (
    build_weekly_master_from_reviews_only,
    merge_daily_into_weekly,
)
from analytics.integrity import run_distortion_test
from analytics.impact import run_review_sales_impact
from analytics.extras import (
    run_volatility_profile,
    run_sentiment_vs_rating_drift,
    run_top_drivers,
)

# Clean IO utilities (no legacy helpers)
from storage.io_utils import (
    slugify,
    today_ymd,
    new_out_dir_for_collection,
    save_df_csv,
    load_df_csv,
    list_saved_collections,
)

SUPPORTED_MARKETPLACES = ["US", "UK"]  # DE intentionally excluded


# ---------- Helpers local to app ----------

def _last_node(path: str) -> str:
    """Return the last node of a 'A > B > C' path; fallback to full if empty."""
    parts = [p.strip() for p in (path or "").split(">") if p.strip()]
    return parts[-1] if parts else (path or "")


def _determine_collection_id(categories: List[str], region: str) -> str:
    """
    Build a human-friendly collection_id:
      "<last-node>[+N]_<REGION>_<YYYYMMDD>"
    """
    base = _last_node(categories[0]) if categories else "collection"
    suffix = f"+{len(categories)-1}" if len(categories) > 1 else ""
    return f"{slugify(base)}{suffix}_{region.upper()}_{today_ymd()}"


def _ensure_collection_folder(collection_id: str) -> Path:
    """Create Out/<collection_id> folder (idempotent)."""
    return new_out_dir_for_collection(Path("Out"), collection_id)


def _save_asins(out_dir: Path, df):
    """Save ASIN list under Out/<collection_id>/asins_<YYYYMMDD>.csv"""
    csv_path = out_dir / f"asins_{today_ymd()}.csv"
    save_df_csv(df, csv_path)
    return csv_path


def _load_latest_asins(out_dir: Path):
    """Load the newest asins_*.csv from Out/<collection_id>."""
    candidates = sorted(out_dir.glob("asins_*.csv"))
    if not candidates:
        # Backward compatibility: old name
        legacy = out_dir / "asin_list.csv"
        if legacy.exists():
            return load_df_csv(legacy)
        raise FileNotFoundError(f"No ASIN CSV found in {out_dir}")
    return load_df_csv(candidates[-1])


def _pick_collection_interactive() -> Path | None:
    """
    Show a numbered list of Out/<collection> folders and return the chosen Path.
    """
    roots = list_saved_collections(Path("Out"))
    if not roots:
        print("No saved collections in Out/.")
        return None
    print("\nSaved collections:")
    for i, p in enumerate(roots, 1):
        # Try to show a short info line
        asin_csvs = sorted(p.glob("asins_*.csv"))
        asin_count = "?"
        if asin_csvs:
            try:
                import pandas as pd
                df = pd.read_csv(asin_csvs[-1])
                asin_count = df["asin"].nunique() if "asin" in df.columns else len(df)
            except Exception:
                pass
        print(f"{i}) {p.name}  |  ASINs≈{asin_count}")
    sel = input("> Enter number (or press Enter to cancel): ").strip()
    if not sel:
        return None
    if sel.isdigit():
        idx = int(sel) - 1
        if 0 <= idx < len(roots):
            return roots[idx]
        print("Index out of range.")
        return None
    # Also allow direct typing of folder name
    direct = Path("Out") / sel
    if direct.exists():
        return direct
    print("Unknown selection.")
    return None


def main_menu():
    session = {}  # stores marketplace, categories, collection_id, out_dir, asin_df

    while True:
        print("\n=== Amazon Reviews – CLI ===")
        print("1) Choose marketplace (US / UK)")
        print("2) Find categories by keyword (multi-select)")
        print("3) Collect ASINs (TOP-100 per chosen category; de-dup; create collection)")
        print("4) Collect reviews for chosen or previously saved ASIN collection (up to 500 per ASIN)")
        print("5) Run analytics/tests (integrity, volatility, sentiment)")
        print("6) Load a previously saved ASIN collection into session")
        print("7) Daily screening (price + BSR + new reviews): run now")
        print("8) Run Reputation - Sales correlation tests (available after 30 daily snapshots)")
        print("0) Exit")

        choice = input("> Enter choice [0-8]: ").strip()

        if choice == "1":
            session["marketplace"] = choose_marketplace(SUPPORTED_MARKETPLACES)
            print(f"[INFO] Marketplace selected: {session['marketplace']}")

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
            print(f"[INFO] Selected categories: {', '.join(chosen)}")

        elif choice == "3":
            if not session.get("categories") or not session.get("marketplace"):
                print("Please run steps (1) and (2) first.")
                continue

            # Create collection folder
            collection_id = _determine_collection_id(session["categories"], session["marketplace"])
            out_dir = _ensure_collection_folder(collection_id)
            session["collection_id"] = collection_id
            session["out_dir"] = out_dir

            # Collect ASINs across selected categories
            all_df = None
            for cat in session["categories"]:
                df = collect_asin_data(category_path=cat, region=session["marketplace"], top_k=100)
                all_df = df if all_df is None else all_df._append(df, ignore_index=True)
            if all_df is not None and "asin" in all_df.columns:
                all_df = all_df.drop_duplicates(subset=["asin"]).reset_index(drop=True)

            _save_asins(out_dir, all_df)
            session["asin_df"] = all_df
            print(f"[INFO] ASIN collection saved under Out/{collection_id}")

        elif choice == "4":
            use_saved = input("> Use previously saved collection? [y/N]: ").strip().lower() == "y"
            if use_saved:
                out_dir = _pick_collection_interactive()
                if not out_dir:
                    continue
                session["out_dir"] = out_dir
                session["collection_id"] = out_dir.name
                try:
                    df_asin = _load_latest_asins(out_dir)
                except Exception as e:
                    print(f"Failed to load ASINs: {e}")
                    continue
                session["asin_df"] = df_asin
            else:
                if "asin_df" not in session or session["asin_df"] is None:
                    print("No ASINs in session. Please collect ASINs first.")
                    continue
                out_dir = session.get("out_dir") or _ensure_collection_folder(
                    _determine_collection_id(session.get("categories", ["collection"]), session.get("marketplace", "US"))
                )
                session["out_dir"] = out_dir

            df_asin = session["asin_df"]
            reviews_df, per_cat_counts = collect_reviews_for_asins(
                df_asin, max_reviews_per_asin=500, marketplace=session.get("marketplace", "US")
            )
            dest = append_and_dedupe_reviews(session["out_dir"], reviews_df)

            print("\nReview collection summary:")
            total = 0
            for cat, n in per_cat_counts.items():
                print(f" - {cat}: {n} reviews")
                total += n
            print(f"TOTAL: {total} reviews. Saved to: {dest}")

        elif choice == "5":
            out_dir = session.get("out_dir")
            if not out_dir:
                # allow manual input
                out_dir = _pick_collection_interactive()
                if not out_dir:
                    continue
                session["out_dir"] = out_dir

            # Build weekly from reviews-only
            try:
                weekly_reviews = build_weekly_master_from_reviews_only(out_dir)
            except Exception as e:
                print(f"Cannot build weekly reviews: {e}")
                continue

            print("\nSelect tests (comma separated): 1) Integrity  2) Volatility  3) Sentiment vs rating  4) Top drivers (needs sales)")
            sel = input("> e.g., '1,2': ").strip()

            if "1" in sel:
                run_distortion_test(weekly_reviews, out_dir)
            if "2" in sel:
                run_volatility_profile(weekly_reviews, sales_df=None, out_dir_ts=out_dir)
            if "3" in sel:
                run_sentiment_vs_rating_drift(out_dir, marketplaces=SUPPORTED_MARKETPLACES)
            if "4" in sel:
                run_top_drivers(weekly_reviews, sales_df=None, out_dir_ts=out_dir)

        elif choice == "6":
            out_dir = _pick_collection_interactive()
            if out_dir:
                session["out_dir"] = out_dir
                session["collection_id"] = out_dir.name
                try:
                    df_asin = _load_latest_asins(out_dir)
                    session["asin_df"] = df_asin
                    print(f"[INFO] Loaded collection into session: {out_dir.name}")
                except Exception as e:
                    print(f"Failed to load ASINs: {e}")

        elif choice == "7":
            if "asin_df" not in session or session["asin_df"] is None:
                out_dir = _pick_collection_interactive()
                if not out_dir:
                    print("No ASINs in session. Please collect or load a collection first.")
                    continue
                session["out_dir"] = out_dir
                try:
                    session["asin_df"] = _load_latest_asins(out_dir)
                except Exception as e:
                    print(f"Failed to load ASINs: {e}")
                    continue

            run_daily_screening(
                session["asin_df"],
                marketplace=session.get("marketplace", "US"),
                out_dir_ts=session["out_dir"],
            )

        elif choice == "8":
            out_dir = session.get("out_dir") or _pick_collection_interactive()
            if not out_dir:
                continue
            if not has_30_days_of_snapshots(out_dir):
                print("Need at least 30 daily snapshots to unlock Reputation - Sales correlation tests.")
                continue

            weekly_reviews = build_weekly_master_from_reviews_only(out_dir)
            weekly_merged = merge_daily_into_weekly(out_dir, weekly_reviews)
            run_review_sales_impact(weekly_merged, sales_df=None, out_dir_ts=out_dir)

        elif choice == "0":
            print("Bye.")
            sys.exit(0)
        else:
            print("Invalid choice.")


if __name__ == "__main__":
    main_menu()