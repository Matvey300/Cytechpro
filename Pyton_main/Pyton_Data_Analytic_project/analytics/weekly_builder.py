# All comments in English.

from pathlib import Path
import pandas as pd
import numpy as np

def ensure_week_col(s: pd.Series) -> pd.Series:
    """Convert datetime series to Monday-start week start date."""
    d = pd.to_datetime(s, errors='coerce', utc=False)
    return d.dt.to_period('W-MON').dt.start_time

def build_weekly_master_from_reviews_only(out_dir_ts: Path) -> pd.DataFrame:
    """Load all_reviews.csv and build weekly aggregates per ASIN."""
    path = Path(out_dir_ts) / "all_reviews.csv"
    if not path.exists():
        raise FileNotFoundError(f"No reviews file at: {path}")
    df = pd.read_csv(path)

    # Normalize minimal columns
    if 'asin' not in df.columns:
        raise RuntimeError("Reviews file must contain 'asin'.")
    # Pick rating/date columns
    rating_col = 'rating' if 'rating' in df.columns else None
    date_col = 'review_date' if 'review_date' in df.columns else None
    if not rating_col or not date_col:
        raise RuntimeError("Reviews must contain 'rating' and 'review_date'.")

    df['week'] = ensure_week_col(df[date_col])
    df['rating'] = pd.to_numeric(df[rating_col], errors='coerce')

    # Weekly aggregates
    g = df.groupby(['asin', 'week'], as_index=False)
    weekly = g.agg(
        avg_rating_week=('rating', 'mean'),
        reviews_count_week=('rating', 'count'),
        rating_var_week=('rating', 'var')
    )

    # Shares of 5★ and 1★
    for star, colname in [(5, 'p5_share_week'), (1, 'p1_share_week')]:
        tmp = df.assign(is_star=(df['rating'] == star).astype(int)) \
                .groupby(['asin', 'week'], as_index=False)['is_star'].mean() \
                .rename(columns={'is_star': colname})
        weekly = weekly.merge(tmp, on=['asin', 'week'], how='left')

    # Cumulative stats per ASIN
    weekly = weekly.sort_values(['asin', 'week'])
    weekly['cum_reviews'] = weekly.groupby('asin')['reviews_count_week'].cumsum()
    weekly['cum_sum_rating'] = (weekly['avg_rating_week'] * weekly['reviews_count_week']).groupby(weekly['asin']).cumsum()
    weekly['cum_avg_rating'] = weekly['cum_sum_rating'] / weekly['cum_reviews'].replace(0, np.nan)
    weekly.drop(columns=['cum_sum_rating'], inplace=True)

    return weekly