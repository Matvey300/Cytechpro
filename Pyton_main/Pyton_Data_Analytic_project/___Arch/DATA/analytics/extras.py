# All comments in English.

from pathlib import Path
import numpy as np
import pandas as pd
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

def run_volatility_profile(weekly_reviews: pd.DataFrame, sales_df: pd.DataFrame | None, out_dir_ts: Path) -> Path:
    df = weekly_reviews.copy()
    vol = df.groupby('asin').agg(
        weeks=('week','nunique'),
        rating_var=('avg_rating_week','var'),
        mean_rating=('avg_rating_week','mean'),
        reviews_var=('reviews_count_week','var'),
        mean_reviews=('reviews_count_week','mean'),
    ).reset_index()
    dest = Path(out_dir_ts) / "volatility_summary.csv"
    vol.to_csv(dest, index=False, encoding='utf-8-sig')
    print(f"[Extras] Saved: {dest}")
    return dest

def run_sentiment_vs_rating_drift(out_dir_ts: Path, marketplaces: list[str]) -> Path:
    path = Path(out_dir_ts) / "all_reviews.csv"
    df = pd.read_csv(path)
    if 'review_text' not in df.columns or 'review_date' not in df.columns:
        dest = Path(out_dir_ts) / "sentiment_vs_rating.csv"
        pd.DataFrame().to_csv(dest, index=False)
        print("[Extras] Missing 'review_text' or 'review_date'; skipping.")
        return dest

    analyzer = SentimentIntensityAnalyzer()
    df['compound'] = df['review_text'].fillna("").astype(str).apply(lambda t: analyzer.polarity_scores(t)['compound'])
    df['week'] = pd.to_datetime(df['review_date'], errors='coerce').dt.to_period('W-MON').dt.start_time
    g = df.groupby(['asin','week'], as_index=False).agg(
        mean_compound=('compound','mean'),
        avg_rating_week=('rating','mean'),
        reviews_count_week=('rating','count'),
    )
    dest = Path(out_dir_ts) / "sentiment_vs_rating.csv"
    g.to_csv(dest, index=False, encoding='utf-8-sig')
    print(f"[Extras] Saved: {dest}")
    return dest

def run_top_drivers(weekly_reviews: pd.DataFrame, sales_df: pd.DataFrame | None, out_dir_ts: Path) -> Path:
    metrics = ['avg_rating_week','reviews_count_week','p5_share_week']
    rows = []
    for met in metrics:
        s = weekly_reviews[[met,'reviews_count_week']].dropna()
        if len(s) >= 8:
            r = np.corrcoef(s[met].astype(float), s['reviews_count_week'].astype(float))[0,1]
            rows.append({'metric': met, 'corr_with_reviews_count': r})
    dest = Path(out_dir_ts) / "top_drivers.csv"
    pd.DataFrame(rows).to_csv(dest, index=False, encoding='utf-8-sig')
    print(f"[Extras] Saved: {dest}")
    return dest