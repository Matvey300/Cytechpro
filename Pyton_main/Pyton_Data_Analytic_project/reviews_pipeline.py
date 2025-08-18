# All comments in English.

from __future__ import annotations

from pathlib import Path
from typing import Dict, Tuple

import pandas as pd

from amazon_review_collector import collect_reviews
from storage.io_utils import append_csv_with_dedupe


def _dedupe_key(row: pd.Series) -> str:
    """
    Dedupe key for reviews CSV:
      - primary: (asin, review_id)
      - fallback: (asin, review_date, rating, hash(review_text))
    """
    asin = str(row.get("asin", "NA"))
    rid = row.get("review_id")
    if pd.notna(rid) and str(rid).strip():
        return f"{asin}|{rid}"
    date = str(row.get("review_date", "NA"))
    rating = str(row.get("rating", "NA"))
    text = str(row.get("review_text", "") or "")
    return f"{asin}|{date}|{rating}|{hash(text)}"


def collect_reviews_for_asins(
    df_asin: pd.DataFrame,
    max_reviews_per_asin: int,
    marketplace: str
) -> Tuple[pd.DataFrame, Dict[str, int]]:
    """
    For a DataFrame of ASINs (requires column 'asin', optional 'category_path'),
    fetch up to N reviews per ASIN using Selenium collector, and return:
      - reviews_df: unified DataFrame with required columns
      - per_cat_counts: dict category_path -> number_of_reviews
    """
    if df_asin is None or df_asin.empty or "asin" not in df_asin.columns:
        return pd.DataFrame(), {}

    asins = df_asin["asin"].astype(str).dropna().tolist()
    reviews_df = collect_reviews(asins, max_reviews=max_reviews_per_asin, marketplace=marketplace)

    # Attach category_path to each review if we have mapping
    cat_map = {}
    if "category_path" in df_asin.columns:
        # take the first occurrence per ASIN
        cat_map = df_asin.dropna(subset=["asin"]).drop_duplicates(subset=["asin"]).set_index("asin")["category_path"].to_dict()

    if not reviews_df.empty:
        reviews_df["category_path"] = reviews_df["asin"].map(cat_map)

    # Per-category counts
    per_cat_counts: Dict[str, int] = {}
    if not reviews_df.empty:
        tmp = reviews_df.copy()
        tmp["category_path"] = tmp["category_path"].fillna("Unknown")
        per = tmp.groupby("category_path")["review_id"].count()
        per_cat_counts = per.to_dict()

    return reviews_df, per_cat_counts


def append_and_dedupe_reviews(out_dir_ts: Path, reviews_df: pd.DataFrame) -> Path:
    """
    Append reviews into Out/<collection_id>/reviews.csv with deduplication.
    Returns path to the file.
    """
    out_path = Path(out_dir_ts) / "reviews.csv"
    if reviews_df is None or reviews_df.empty:
        # Still make sure file exists (create if missing with headers)
        if not out_path.exists():
            pd.DataFrame(columns=[
                "asin","review_id","review_date","rating","review_text",
                "verified","helpful_votes","buybox_price","currency","bsr_rank","bsr_path","category_path"
            ]).to_csv(out_path, index=False, encoding="utf-8-sig")
        return out_path

    append_csv_with_dedupe(out_path, reviews_df, key_fn=_dedupe_key)
    return out_path