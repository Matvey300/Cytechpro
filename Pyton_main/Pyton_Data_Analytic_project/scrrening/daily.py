# All comments in English.

from pathlib import Path
import pandas as pd
from datetime import datetime
from storage.io_utils import append_csv_with_upsert_keys

def run_daily_screening(df_asin: pd.DataFrame, marketplace: str, out_dir_ts: Path) -> Path:
    """Daily snapshot stub: records (asin, date) with new_reviews_count.
    NOTE: buybox_price and bsr are left as NaN in MVP (to be filled later).
    """
    today = datetime.now().date().isoformat()
    dest = Path(out_dir_ts) / "daily_snapshots.csv"

    # Compute today's new reviews count per ASIN from all_reviews.csv (best effort)
    reviews_path = Path(out_dir_ts) / "all_reviews.csv"
    if reviews_path.exists():
        rv = pd.read_csv(reviews_path)
        rv["review_date"] = pd.to_datetime(rv["review_date"], errors="coerce").dt.date.astype(str)
        today_cnt = rv[rv["review_date"] == today].groupby("asin").size().reindex(df_asin["asin"].unique(), fill_value=0)
    else:
        today_cnt = pd.Series(0, index=df_asin["asin"].unique())

    snap = pd.DataFrame({
        "asin": list(today_cnt.index),
        "date": today,
        "buybox_price": None,
        "currency": None,
        "bsr": None,
        "category_path_primary": None,
        "new_reviews_count": list(today_cnt.values),
        "avg_new_rating": None,
        "snapshot_ts": datetime.now().isoformat(timespec="seconds"),
        "marketplace": marketplace
    })

    append_csv_with_upsert_keys(dest, snap, keys=["asin", "date"])
    print(f"[Daily] Snapshot saved/updated: {dest}")
    return dest

def has_30_days_of_snapshots(out_dir_ts: Path) -> bool:
    """Checks presence of >=30 distinct dates in daily_snapshots.csv."""
    p = Path(out_dir_ts) / "daily_snapshots.csv"
    if not p.exists():
        return False
    df = pd.read_csv(p)
    if "date" not in df.columns:
        return False
    return df["date"].nunique() >= 30