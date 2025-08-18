# All comments in English.

from pathlib import Path
import numpy as np
import pandas as pd
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

def run_volatility_profile(weekly_reviews: pd.DataFrame, sales_df: pd.DataFrame | None, out_dir_ts: Path) -> Path:
    """Compute simple volatility/means for rating/price/sales (if sales available)."""
    df = weekly_reviews.copy()
    if sales_df is not None and not sales_df.empty:
        df = df.merge(sales_df[['asin','week','weekly_sales','avg_price_week']], on=['asin','week'], how='left')
    vol = df.groupby('asin').agg(
        weeks=('week','nunique'),
        rating_var=('avg_rating_week','var'),
        mean_rating=('avg_rating_week','mean'),
        price_var=('avg_price_week','var'),
        mean_price=('avg_price_week','mean'),
        sales_var=('weekly_sales','var'),
        mean_sales=('weekly_sales','mean'),
    ).reset_index()
    dest = Path(out_dir_ts) / "volatility_summary.csv"
    vol.to_csv(dest, index=False, encoding='utf-8-sig')
    print(f"[Extras] Saved: {dest}")
    return dest

def run_sentiment_vs_rating_drift(out_dir_ts: Path, marketplaces: list[str]) -> Path:
    """Compute simple sentiment (VADER) for English reviews and compare to rating drift."""
    path = Path(out_dir_ts) / "all_reviews.csv"
    df = pd.read_csv(path)

    # Assume English only: US/UK
    analyzer = SentimentIntensityAnalyzer()
    if 'review_text' not in df.columns:
        print("[Extras] No 'review_text' column; skipping sentiment.")
        dest = Path(out_dir_ts) / "sentiment_vs_rating.csv"
        pd.DataFrame().to_csv(dest, index=False)
        return dest

    df['compound'] = df['review_text'].fillna("").astype(str).apply(lambda t: analyzer.polarity_scores(t)['compound'])
    if 'review_date' not in df.columns:
        print("[Extras] No 'review_date' column; skipping sentiment aggregation.")
        dest = Path(out_dir_ts) / "sentiment_vs_rating.csv"
        pd.DataFrame().to_csv(dest, index=False)
        return dest

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
    """Compute simple correlations as 'top drivers' of sales (if sales available)."""
    if sales_df is None or sales_df.empty:
        print("[Extras] No sales data; skipping top drivers.")
        dest = Path(out_dir_ts) / "top_drivers.csv"
        pd.DataFrame().to_csv(dest, index=False)
        return dest
    m = weekly_reviews.merge(sales_df[['asin','week','weekly_sales','avg_price_week']], on=['asin','week'], how='inner')
    metrics = ['avg_rating_week','reviews_count_week','p5_share_week','avg_price_week']
    rows = []
    for met in metrics:
        s = m[[met,'weekly_sales']].dropna()
        if len(s) >= 8:
            r = np.corrcoef(s[met].astype(float), s['weekly_sales'].astype(float))[0,1]
            rows.append({'metric': met, 'corr_with_sales': r})
    dest = Path(out_dir_ts) / "top_drivers.csv"
    pd.DataFrame(rows).to_csv(dest, index=False, encoding='utf-8-sig')
    print(f"[Extras] Saved: {dest}")
    return dest