
from pathlib import Path
from typing import Dict, Tuple
import importlib
import pandas as pd

from storage.io_utils import append_csv_with_dedupe

def collect_reviews_for_asins(df_asin: pd.DataFrame, max_reviews_per_asin: int, marketplace: str) -> Tuple[pd.DataFrame, Dict[str, int]]:
    """Call user's amazon_review_collector on a list of ASINs (sequential, up to max_reviews_per_asin).
       Returns (reviews_df, per_category_counts).
       NOTE: We assume user's collector exposes a function collect_reviews(asins, max_reviews, marketplace) → DataFrame.
    """
    mod = importlib.import_module("amazon_review_collector")
    if not hasattr(mod, "collect_reviews"):
        # Fallback: try an alternative name or explain how to adapt.
        raise RuntimeError("amazon_review_collector.collect_reviews(asins, max_reviews, marketplace) not found.")

    asins = df_asin['asin'].astype(str).dropna().unique().tolist()
    reviews_df = mod.collect_reviews(asins, max_reviews_per_asin, marketplace)  # expected DataFrame

    # Count per category for summary (best effort)
    per_cat = {}
    if 'category_path' in df_asin.columns:
        asin2cat = df_asin.set_index('asin')['category_path'].to_dict()
        if 'asin' in reviews_df.columns:
            for a, n in reviews_df['asin'].value_counts().items():
                cat = asin2cat.get(a, "Unknown")
                per_cat[cat] = per_cat.get(cat, 0) + int(n)
    else:
        per_cat = {"Total": int(len(reviews_df))}

    return reviews_df, per_cat

def review_dedupe_key(row) -> str:
    """Default dedupe key: (asin, review_id) if exists; else (asin, review_date, rating, hash(text))."""
    asin = str(row.get('asin', 'NA'))
    rid = row.get('review_id')
    if pd.notna(rid):
        return f"{asin}|{rid}"
    date = str(row.get('review_date', 'NA'))
    rating = str(row.get('rating', 'NA'))
    text = str(row.get('review_text', ''))
    return f"{asin}|{date}|{rating}|{hash(text)}"

def append_and_dedupe_reviews(out_dir_ts: Path, df_reviews: pd.DataFrame) -> Path:
    """Append reviews into Out/<ts>/all_reviews.csv with dedupe."""
    dest = out_dir_ts / "all_reviews.csv"
    append_csv_with_dedupe(dest, df_reviews, review_dedupe_key)
    return dest