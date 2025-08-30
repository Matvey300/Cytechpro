# All comments in English.

from pathlib import Path

import numpy as np
import pandas as pd


def run_review_sales_impact(
    weekly_reviews: pd.DataFrame, sales_df: pd.DataFrame | None, out_dir_ts: Path
):
    """For MVP we treat weekly_bsr_mean as sales proxy (lower is better).
    Computes simple contemporaneous correlations.
    """
    if "weekly_bsr_mean" not in weekly_reviews.columns:
        print("[Impact] No BSR proxy in weekly data; skip.")
        per_path = Path(out_dir_ts) / "impact_per_asin.csv"
        pooled_path = Path(out_dir_ts) / "impact_pooled.csv"
        pd.DataFrame().to_csv(per_path, index=False)
        pd.DataFrame().to_csv(pooled_path, index=False)
        return per_path, pooled_path

    df = weekly_reviews.copy()
    # Invert BSR so that higher proxy means better sales
    df["sales_proxy"] = -df["weekly_bsr_mean"].astype(float)
    metrics = ["avg_rating_week", "reviews_count_week", "p5_share_week"]

    per_rows = []
    for asin, g in df.groupby("asin"):
        if g["sales_proxy"].notna().sum() < 8:
            continue
        for met in metrics:
            if met in g.columns and g[met].notna().sum() >= 8:
                a = g[["sales_proxy", met]].dropna()
                if len(a) >= 8:
                    r = np.corrcoef(a["sales_proxy"], a[met])[0, 1]
                    per_rows.append(
                        {"asin": asin, "metric": met, "type": "contemporaneous", "corr": r}
                    )

    per_df = pd.DataFrame(per_rows)
    per_path = Path(out_dir_ts) / "impact_per_asin.csv"
    pooled_path = Path(out_dir_ts) / "impact_pooled.csv"
    per_df.to_csv(per_path, index=False, encoding="utf-8-sig")
    pd.DataFrame().to_csv(pooled_path, index=False, encoding="utf-8-sig")
    print(f"[Impact] Saved: {per_path}")
    return per_path, pooled_path
