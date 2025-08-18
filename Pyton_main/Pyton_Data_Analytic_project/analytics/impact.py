# All comments in English.

from pathlib import Path
import numpy as np
import pandas as pd

def run_review_sales_impact(weekly_reviews: pd.DataFrame, sales_df: pd.DataFrame | None, out_dir_ts: Path) -> tuple[Path, Path]:
    """Compute reviews→sales correlations (per-ASIN contemporaneous & lag-1, and pooled demeaned)."""
    if sales_df is None or sales_df.empty:
        print("[Impact] No sales data provided. Skipping.")
        return Path(out_dir_ts) / "impact_per_asin.csv", Path(out_dir_ts) / "impact_pooled.csv"

    # Expect columns: asin, week, weekly_sales, avg_price_week
    m = pd.merge(
        weekly_reviews,
        sales_df[['asin', 'week', 'weekly_sales', 'avg_price_week']].copy(),
        on=['asin', 'week'],
        how='inner'
    ).sort_values(['asin', 'week'])

    metrics = ['avg_rating_week', 'reviews_count_week', 'p5_share_week']
    per_rows = []
    for asin, g in m.groupby('asin'):
        if g['weekly_sales'].notna().sum() < 8:
            continue
        y = g['weekly_sales'].astype(float)
        for met in metrics + ['avg_price_week']:
            if met in g.columns and g[met].notna().sum() >= 8:
                aligned = g[['weekly_sales', met]].dropna()
                if len(aligned) >= 8:
                    r = np.corrcoef(aligned['weekly_sales'], aligned[met])[0, 1]
                    per_rows.append({'asin': asin, 'metric': met, 'type': 'contemporaneous', 'corr': r})
            # Lag-1
            if met in g.columns:
                lag = g[[met, 'weekly_sales']].copy()
                lag[met] = lag[met].shift(1)
                aligned = lag.dropna()
                if len(aligned) >= 8:
                    r = np.corrcoef(aligned['weekly_sales'], aligned[met])[0, 1]
                    per_rows.append({'asin': asin, 'metric': f'{met}_lag1', 'type': 'lag1', 'corr': r})

    per_df = pd.DataFrame(per_rows)

    # Pooled (demeaned within ASIN)
    pooled = m.copy()
    pooled = pooled.dropna(subset=['weekly_sales'])
    pooled = pooled.groupby('asin').apply(
        lambda g: g.assign(
            sales_dm=g['weekly_sales'] - g['weekly_sales'].mean(),
            avg_rating_week_dm=g['avg_rating_week'] - g['avg_rating_week'].mean(),
            reviews_count_week_dm=g['reviews_count_week'] - g['reviews_count_week'].mean(),
            p5_share_week_dm=g['p5_share_week'] - g['p5_share_week'].mean(),
            avg_price_week_dm=g['avg_price_week'] - g['avg_price_week'].mean(),
        )
    ).reset_index(drop=True)

    pooled_rows = []
    for met in ['avg_rating_week_dm', 'reviews_count_week_dm', 'p5_share_week_dm', 'avg_price_week_dm']:
        aligned = pooled[['sales_dm', met]].dropna()
        if len(aligned) >= 8:
            r = np.corrcoef(aligned['sales_dm'], aligned[met])[0, 1]
            pooled_rows.append({'metric': met, 'corr_sales_dm': r})

    per_path = Path(out_dir_ts) / "impact_per_asin.csv"
    pooled_path = Path(out_dir_ts) / "impact_pooled.csv"
    per_df.to_csv(per_path, index=False, encoding='utf-8-sig')
    pd.DataFrame(pooled_rows).to_csv(pooled_path, index=False, encoding='utf-8-sig')

    print(f"[Impact] Saved: {per_path}, {pooled_path}")
    return per_path, pooled_path