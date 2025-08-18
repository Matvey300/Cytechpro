# All comments in English.

from pathlib import Path
from typing import Dict, Tuple
import importlib
import pandas as pd

from storage.io_utils import append_csv_with_dedupe

def collect_reviews_for_asins(df_asin: pd.DataFrame, max_reviews_per_asin: int, marketplace: str) -> Tuple[pd.DataFrame, Dict[str, int]]:
    """Calls user's amazon_review_collector.collect_reviews(asins, max_reviews, marketplace)."""
    mod = importlib.import_module("amazon_review_collector")
    if not hasattr(mod, "collect_reviews"):
        raise RuntimeError("amazon_review_collector.collect_reviews(asins, max_reviews, marketplace) not found.")

    asins = df_asin["asin"].astype(str).dropna().unique().tolist()
    reviews_df = mod.collect_reviews(asins, max_reviews_per_asin, marketplace)

    per_cat = {}
    if "category_path" in df_asin.columns and "asin" in reviews_df.columns:
        asin2cat = df_asin.set_index("asin")["category_path"].to_dict()
        for a, n in reviews_df["asin"].value_counts().items():
            cat = asin2cat.get(a, "Unknown")
            per_cat[cat] = per_cat.get(cat, 0) + int(n)
    else:
        per_cat = {"Total": int(len(reviews_df))}

    return reviews_df, per_cat

def review_dedupe_key(row) -> str:
    asin = str(row.get("asin", "NA"))
    rid = row.get("review_id")
    if pd.notna(rid):
        return f"{asin}|{rid}"
    date = str(row.get("review_date", "NA"))
    rating = str(row.get("rating", "NA"))
    text = str(row.get("review_text", ""))
    return f"{asin}|{date}|{rating}|{hash(text)}"

def append_and_dedupe_reviews(out_dir_ts: Path, df_reviews: pd.DataFrame) -> Path:
    dest = out_dir_ts / "all_reviews.csv"
    append_csv_with_dedupe(dest, df_reviews, review_dedupe_key)
    return dest