# All comments in English.

from pathlib import Path

import numpy as np
import pandas as pd


def ensure_week_col(s: pd.Series) -> pd.Series:
    d = pd.to_datetime(s, errors="coerce", utc=False)
    return d.dt.to_period("W-MON").dt.start_time


def build_weekly_master_from_reviews_only(out_dir_ts: Path) -> pd.DataFrame:
    path = Path(out_dir_ts) / "all_reviews.csv"
    if not path.exists():
        raise FileNotFoundError(f"No reviews file at: {path}")
    df = pd.read_csv(path)
    if "asin" not in df.columns or "rating" not in df.columns or "review_date" not in df.columns:
        raise RuntimeError("Reviews must contain 'asin', 'rating', 'review_date'.")

    df["week"] = ensure_week_col(df["review_date"])
    df["rating"] = pd.to_numeric(df["rating"], errors="coerce")

    g = df.groupby(["asin", "week"], as_index=False)
    weekly = g.agg(
        avg_rating_week=("rating", "mean"),
        reviews_count_week=("rating", "count"),
        rating_var_week=("rating", "var"),
    )

    for star, colname in [(5, "p5_share_week"), (1, "p1_share_week")]:
        tmp = (
            df.assign(is_star=(df["rating"] == star).astype(int))
            .groupby(["asin", "week"], as_index=False)["is_star"]
            .mean()
            .rename(columns={"is_star": colname})
        )
        weekly = weekly.merge(tmp, on=["asin", "week"], how="left")

    weekly = weekly.sort_values(["asin", "week"])
    weekly["cum_reviews"] = weekly.groupby("asin")["reviews_count_week"].cumsum()
    weekly["cum_sum_rating"] = (
        (weekly["avg_rating_week"] * weekly["reviews_count_week"]).groupby(weekly["asin"]).cumsum()
    )
    weekly["cum_avg_rating"] = weekly["cum_sum_rating"] / weekly["cum_reviews"].replace(0, np.nan)
    weekly.drop(columns=["cum_sum_rating"], inplace=True)
    return weekly


def merge_daily_into_weekly(out_dir_ts: Path, weekly_reviews: pd.DataFrame) -> pd.DataFrame:
    """Merge daily snapshots (BSR/price) into weekly frame (proxy)."""
    p = Path(out_dir_ts) / "daily_snapshots.csv"
    if not p.exists():
        print("[Weekly] No daily_snapshots.csv found; returning reviews-only.")
        return weekly_reviews
    d = pd.read_csv(p)
    if "date" not in d.columns or "asin" not in d.columns:
        print("[Weekly] daily_snapshots.csv missing required columns; returning reviews-only.")
        return weekly_reviews
    d["week"] = ensure_week_col(d["date"])

    agg = d.groupby(["asin", "week"], as_index=False).agg(
        weekly_bsr_min=("bsr", "min"),
        weekly_bsr_mean=("bsr", "mean"),
        weekly_buybox_mean=("buybox_price", "mean"),
        weekly_new_reviews_sum=("new_reviews_count", "sum"),
    )
    m = weekly_reviews.merge(agg, on=["asin", "week"], how="left")
    return m
