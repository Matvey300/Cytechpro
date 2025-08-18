# All comments in English.

from pathlib import Path
import numpy as np
import pandas as pd

def _normalize_0_1(s: pd.Series) -> pd.Series:
    s = s.astype(float)
    mn, mx = s.min(), s.max()
    if pd.isna(mn) or pd.isna(mx) or mx == mn:
        return pd.Series(np.zeros(len(s)), index=s.index)
    return (s - mn) / (mx - mn)

def run_distortion_test(weekly_reviews: pd.DataFrame, out_dir_ts: Path) -> Path:
    """Compute heuristic distortion probability per ASIN and save CSV."""
    feats = []
    for asin, g in weekly_reviews.groupby('asin'):
        g = g.sort_values('week')
        if len(g) < 3:
            feats.append({'asin': asin, 'burstiness': np.nan, 'recent_shift': np.nan,
                          'extremeness': np.nan, 'drift_vs_cum': np.nan})
            continue
        # Burstiness
        counts = g['reviews_count_week'].fillna(0).astype(float)
        med = np.median(counts[counts > 0]) if (counts > 0).any() else np.nan
        burst = (counts.max() / med) if (med and not np.isnan(med) and med > 0) else np.nan
        # Recent shift (last 4 weeks vs prior)
        last4 = g.tail(4)
        prior = g.iloc[:-4] if len(g) > 4 else g.iloc[:0]
        recent_shift = abs((last4['avg_rating_week'].mean() - prior['avg_rating_week'].mean())) if len(prior) > 0 else np.nan
        # Extremeness: high p5 with low variance
        p5 = g['p5_share_week'].mean()
        var = g['rating_var_week'].mean()
        extremeness = (p5 - 0.6) * (0.5 - (0 if pd.isna(var) else min(var, 0.5)))
        # Drift vs cumulative
        drift_vs_cum = abs(g['avg_rating_week'].iloc[-1] - g['cum_avg_rating'].iloc[-1])

        feats.append({'asin': asin, 'burstiness': burst, 'recent_shift': recent_shift,
                      'extremeness': extremeness, 'drift_vs_cum': drift_vs_cum})

    feat_df = pd.DataFrame(feats)
    for c in ['burstiness', 'recent_shift', 'extremeness', 'drift_vs_cum']:
        feat_df[f'norm_{c}'] = _normalize_0_1(feat_df[c].fillna(feat_df[c].median()))
    norm_cols = [f'norm_{c}' for c in ['burstiness', 'recent_shift', 'extremeness', 'drift_vs_cum']]
    feat_df['distortion_prob'] = feat_df[norm_cols].mean(axis=1, skipna=True)

    dest = Path(out_dir_ts) / "distortion_prob_by_asin.csv"
    feat_df.to_csv(dest, index=False, encoding='utf-8-sig')
    print(f"[Integrity] Saved: {dest}")
    return dest