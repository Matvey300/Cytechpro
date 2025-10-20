# -*- coding: utf-8 -*-
"""
Amazon Reviews & Sales – Weekly Analytics Pipeline
All comments are in English (per user request).

What this script does:
1) Build weekly review metrics per ASIN.
2) Estimate per-ASIN probability of distorted rating (heuristic score 0..1).
3) Compute contemporaneous and lagged correlations between reviews and sales (if sales exist).
4) Extra (proposal): volatility summary and optional simple KMeans clustering.
5) Write all outputs to a user-specified directory and exit.

Inputs (CSV):
- Reviews file: expected columns include:
    asin, review_date (or any date-like), rating (1..5); optional: verified_purchase, helpful_votes
- Synccentric/other sales file: expected columns include:
    asin, date/week, and possibly sales/price columns (auto-detected heuristically).

Outputs (CSV) in --outdir:
- master_weekly.csv
- distortion_prob_by_asin.csv
- impact_per_asin.csv
- impact_pooled.csv
- volatility_summary.csv
- (optional) clusters.csv
- run_status.json
"""

import argparse
import json
import os
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd


# ----------------------------- I/O helpers -----------------------------
def read_csv_safely(path: Optional[str]) -> Optional[pd.DataFrame]:
    """Read CSV with common encodings and return None if path missing or read fails."""
    if not path or not os.path.exists(path):
        return None
    for enc in ["utf-8", "utf-8-sig", "cp1251", "latin-1"]:
        try:
            return pd.read_csv(path, encoding=enc, low_memory=False)
        except Exception:
            continue
    return None


def write_csv(df: pd.DataFrame, path: str) -> None:
    """Write DataFrame to CSV creating parent dirs if needed."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    df.to_csv(path, index=False)


def find_date_column(df: pd.DataFrame, candidates: List[str]) -> Optional[str]:
    """Return the first date-like column matching candidates or heuristics."""
    for c in candidates:
        if c in df.columns:
            return c
    for c in df.columns:
        lc = c.lower()
        if "date" in lc or "week" in lc or "timestamp" in lc:
            return c
    return None


def ensure_week_col(df: pd.DataFrame, date_col: str) -> pd.Series:
    """Convert date column to weekly period (Monday-based start date)."""
    s = pd.to_datetime(df[date_col], errors="coerce", utc=False)
    return s.dt.to_period("W-MON").dt.start_time


def find_column(df: pd.DataFrame, candidates: List[str]) -> Optional[str]:
    """Find the first existing column by case-insensitive candidate names."""
    lc = {c.lower(): c for c in df.columns}
    for cand in candidates:
        if cand.lower() in lc:
            return lc[cand.lower()]
    return None


def normalize_series(s: pd.Series) -> pd.Series:
    """Min-max normalize safely to [0,1]."""
    s = s.astype(float)
    mn, mx = s.min(), s.max()
    if pd.isna(mn) or pd.isna(mx) or mx == mn:
        return pd.Series(np.zeros(len(s)), index=s.index)
    return (s - mn) / (mx - mn)


def safe_zscore(s: pd.Series) -> pd.Series:
    """Z-score with protection against zero std and NaNs."""
    s = s.astype(float)
    m, st = s.mean(), s.std(ddof=0)
    if st == 0 or pd.isna(st):
        return pd.Series(np.zeros(len(s)), index=s.index)
    return (s - m) / st


# ----------------------------- Reviews weekly -----------------------------
def week_agg_reviews(df_reviews: pd.DataFrame) -> pd.DataFrame:
    """
    Build weekly aggregates from per-review rows:
      - avg_rating_week
      - reviews_count_week
      - p5_share_week
      - p1_share_week
      - rating_var_week
      - cum_avg_rating (cumulative mean over weeks)
      - cum_reviews (cumulative review count)
    """
    grp = df_reviews.groupby(["asin", "week"], as_index=False)
    weekly = grp.agg(
        avg_rating_week=("rating", "mean"),
        reviews_count_week=("rating", "count"),
        rating_var_week=("rating", "var"),
    )
    # Star shares (5★ and 1★)
    for star, colname in [(5, "p5_share_week"), (1, "p1_share_week")]:
        tmp = (
            df_reviews.assign(is_star=(df_reviews["rating"] == star).astype(int))
            .groupby(["asin", "week"], as_index=False)["is_star"]
            .mean()
            .rename(columns={"is_star": colname})
        )
        weekly = weekly.merge(tmp, on=["asin", "week"], how="left")

    # Cumulative stats per ASIN
    weekly = weekly.sort_values(["asin", "week"])
    weekly["cum_reviews"] = weekly.groupby("asin")["reviews_count_week"].cumsum()
    weekly["cum_sum_rating"] = (
        (weekly["avg_rating_week"] * weekly["reviews_count_week"]).groupby(weekly["asin"]).cumsum()
    )
    weekly["cum_avg_rating"] = weekly["cum_sum_rating"] / weekly["cum_reviews"].replace(0, np.nan)
    weekly.drop(columns=["cum_sum_rating"], inplace=True)
    return weekly


def bayesian_adjusted_rating(row, prior_mean=4.1, prior_strength=20):
    """
    Bayesian adjusted rating:
      (prior_mean * prior_strength + sum_ratings) / (prior_strength + n)
    sum_ratings approximated by avg_rating_week * reviews_count_week.
    """
    n = row.get("reviews_count_week", 0)
    avg = row.get("avg_rating_week", np.nan)
    if pd.isna(avg) or n <= 0:
        return np.nan
    sum_ratings = avg * n
    return (prior_mean * prior_strength + sum_ratings) / (prior_strength + n)


# ----------------------------- Synccentric weekly -----------------------------
def detect_sales_column(df: pd.DataFrame) -> Optional[str]:
    """Detect a likely sales column name."""
    return find_column(
        df,
        [
            "weekly_sales",
            "units_sold",
            "units_week",
            "sales_units",
            "sales",
            "sold",
            "qty",
            "quantity",
            "units",
        ],
    )


def detect_price_column(df: pd.DataFrame) -> Optional[str]:
    """Detect a likely price column name."""
    return find_column(
        df,
        [
            "price",
            "avg_price",
            "bb_new_landed_price",
            "bb_new_landed_price_avg_3mo",
            "bb_new_landed_price_avg_1mo",
            "price_avg",
            "buy_box_price",
        ],
    )


def weekly_synccentric(df_sync: pd.DataFrame) -> Tuple[pd.DataFrame, Dict[str, Optional[str]]]:
    """
    Build weekly sales/price table from a synccentric-like dataset.
    Heuristics for date/week, sales, price detection.
    """
    meta = dict(date_col=None, sales_col=None, price_col=None)
    if df_sync is None or df_sync.empty:
        return pd.DataFrame(), meta

    date_col = find_date_column(df_sync, ["date", "week_start", "week", "timestamp"])
    if date_col is None:
        return pd.DataFrame(), meta
    meta["date_col"] = date_col

    sales_col = detect_sales_column(df_sync)
    price_col = detect_price_column(df_sync)
    meta["sales_col"] = sales_col
    meta["price_col"] = price_col

    dfw = df_sync.copy()
    dfw["week"] = ensure_week_col(dfw, date_col)

    if "asin" not in dfw.columns:
        for c in dfw.columns:
            if "asin" in c.lower():
                dfw = dfw.rename(columns={c: "asin"})
                break
    if "asin" not in dfw.columns:
        return pd.DataFrame(), meta

    agg_dict = {"week": "first"}
    if sales_col:
        dfw[sales_col] = pd.to_numeric(dfw[sales_col], errors="coerce")
        agg_dict[sales_col] = "sum"
    if price_col:
        dfw[price_col] = pd.to_numeric(dfw[price_col], errors="coerce")
        agg_dict[price_col] = "mean"

    weekly = dfw.groupby(["asin", "week"], as_index=False).agg(agg_dict)
    if sales_col:
        weekly = weekly.rename(columns={sales_col: "weekly_sales"})
    if price_col:
        weekly = weekly.rename(columns={price_col: "avg_price_week"})
    if "avg_price_week" in weekly.columns:
        weekly = weekly.sort_values(["asin", "week"])
        weekly["price_change_weekly"] = weekly.groupby("asin")["avg_price_week"].diff()

    return weekly, meta


# ----------------------------- Master weekly & analytics -----------------------------
def build_master_weekly(
    df_reviews: Optional[pd.DataFrame], df_sync: Optional[pd.DataFrame]
) -> Tuple[pd.DataFrame, Dict]:
    """Merge weekly review aggregates with weekly sales/price table."""
    info = {
        "reviews_loaded": df_reviews is not None and not df_reviews.empty,
        "sync_loaded": df_sync is not None and not df_sync.empty,
    }

    weekly_reviews = pd.DataFrame()
    if df_reviews is not None and not df_reviews.empty:
        date_col = find_date_column(df_reviews, ["review_date", "date"])
        if date_col:
            df = df_reviews.copy()
            rating_col = find_column(df, ["rating", "stars", "star_rating"])
            if rating_col and rating_col != "rating":
                df = df.rename(columns={rating_col: "rating"})
            if "asin" not in df.columns:
                for c in df.columns:
                    if "asin" in c.lower():
                        df = df.rename(columns={c: "asin"})
                        break
            if "asin" in df.columns and "rating" in df.columns:
                df["week"] = ensure_week_col(df, date_col)
                df["rating"] = pd.to_numeric(df["rating"], errors="coerce")
                weekly_reviews = week_agg_reviews(df.dropna(subset=["rating"]))
                weekly_reviews["bayes_rating_week"] = weekly_reviews.apply(
                    bayesian_adjusted_rating, axis=1
                )

    info["weekly_reviews_rows"] = int(weekly_reviews.shape[0]) if not weekly_reviews.empty else 0

    weekly_sales, meta = weekly_synccentric(df_sync if df_sync is not None else pd.DataFrame())
    info.update(
        {
            "sync_meta": meta,
            "weekly_sales_rows": int(weekly_sales.shape[0]) if not weekly_sales.empty else 0,
        }
    )

    if weekly_reviews.empty and weekly_sales.empty:
        return pd.DataFrame(), info

    if not weekly_reviews.empty and not weekly_sales.empty:
        master = pd.merge(weekly_reviews, weekly_sales, on=["asin", "week"], how="outer")
    else:
        master = weekly_reviews if not weekly_reviews.empty else weekly_sales

    master = master.sort_values(["asin", "week"]).reset_index(drop=True)
    if "weekly_sales" not in master.columns:
        master["weekly_sales"] = np.nan
    if "avg_price_week" not in master.columns:
        master["avg_price_week"] = np.nan
    if "price_change_weekly" not in master.columns:
        master["price_change_weekly"] = master.groupby("asin")["avg_price_week"].diff()
    return master, info


def compute_distortion_score(weekly_reviews: pd.DataFrame) -> pd.DataFrame:
    """
    Heuristic 'distortion probability' per ASIN based on:
      - Burstiness: max(weekly_reviews) / median(weekly_reviews>0)
      - Recent shift: |last 4w avg rating - prior avg rating|
      - Extremeness: high mean 5★ share with low mean variance
      - Drift vs cumulative: |last week avg rating - last cumulative avg|
    Returns a DataFrame with one row per ASIN and a final normalized score.
    """
    df = weekly_reviews.copy()
    feats = []
    for asin, g in df.groupby("asin"):
        g = g.sort_values("week")
        if len(g) < 3:
            feats.append(
                {
                    "asin": asin,
                    "burstiness": np.nan,
                    "recent_shift": np.nan,
                    "extremeness": np.nan,
                    "drift_vs_cum": np.nan,
                    "obs_weeks": len(g),
                }
            )
            continue
        counts = g["reviews_count_week"].fillna(0).astype(float)
        med = np.median(counts[counts > 0]) if (counts > 0).any() else np.nan
        burst = (counts.max() / med) if (med and not np.isnan(med) and med > 0) else np.nan

        last4 = g.tail(4)
        prior = g.iloc[:-4] if len(g) > 4 else g.iloc[:0]
        recent_shift = (
            (last4["avg_rating_week"].mean() - prior["avg_rating_week"].mean())
            if len(prior) > 0
            else np.nan
        )
        recent_shift = abs(recent_shift) if not pd.isna(recent_shift) else np.nan

        p5 = g["p5_share_week"].mean()
        var = g["rating_var_week"].mean()
        extremeness = (p5 - 0.6) * (0.5 - (0 if pd.isna(var) else min(var, 0.5)))

        drift_vs_cum = abs(g["avg_rating_week"].iloc[-1] - g["cum_avg_rating"].iloc[-1])

        feats.append(
            {
                "asin": asin,
                "burstiness": burst,
                "recent_shift": recent_shift,
                "extremeness": extremeness,
                "drift_vs_cum": drift_vs_cum,
                "obs_weeks": len(g),
            }
        )
    feat_df = pd.DataFrame(feats)
    for c in ["burstiness", "recent_shift", "extremeness", "drift_vs_cum"]:
        col = feat_df[c].fillna(feat_df[c].median())
        feat_df[f"norm_{c}"] = normalize_series(col)
    norm_cols = [f"norm_{c}" for c in ["burstiness", "recent_shift", "extremeness", "drift_vs_cum"]]
    feat_df["distortion_prob"] = feat_df[norm_cols].mean(axis=1, skipna=True)
    return feat_df[["asin", "distortion_prob"] + norm_cols + ["obs_weeks"]]


def compute_review_sales_impact(
    master: pd.DataFrame, min_weeks: int = 8
) -> Dict[str, pd.DataFrame]:
    """
    Compute per-ASIN contemporaneous and lag-1 correlations with sales (if sales present).
    Also compute pooled (within-ASIN demeaned) correlations.
    """
    results = {"per_asin": pd.DataFrame(), "pooled": pd.DataFrame()}
    if "weekly_sales" not in master.columns or master["weekly_sales"].isna().all():
        return results

    metrics = [
        "avg_rating_week",
        "reviews_count_week",
        "p5_share_week",
        "bayes_rating_week",
        "price_change_weekly",
        "avg_price_week",
    ]
    per_rows = []
    for asin, g in master.groupby("asin"):
        g = g.sort_values("week")
        if g["weekly_sales"].notna().sum() < min_weeks:
            continue
        g["weekly_sales"].astype(float)

        # contemporaneous correlations
        for m in metrics:
            if m in g.columns and g[m].notna().sum() >= min_weeks:
                aligned = g[["weekly_sales", m]].dropna()
                if aligned.shape[0] >= min_weeks:
                    r = np.corrcoef(
                        aligned["weekly_sales"].astype(float), aligned[m].astype(float)
                    )[0, 1]
                    per_rows.append(
                        {"asin": asin, "metric": m, "type": "contemporaneous", "corr": r}
                    )

        # lag-1: reviews (t-1) vs sales (t)
        g_lag = g.copy()
        for m in metrics:
            if m in g.columns:
                g_lag[f"{m}_lag1"] = g[m].shift(1)
                aligned = g_lag[[f"{m}_lag1", "weekly_sales"]].dropna()
                if aligned.shape[0] >= min_weeks:
                    r = np.corrcoef(
                        aligned["weekly_sales"].astype(float), aligned[f"{m}_lag1"].astype(float)
                    )[0, 1]
                    per_rows.append(
                        {"asin": asin, "metric": f"{m}_lag1", "type": "lag1", "corr": r}
                    )

    results["per_asin"] = pd.DataFrame(per_rows)

    # pooled (demeaned within ASIN)
    pooled = master.copy()
    pooled = pooled.dropna(subset=["weekly_sales"])
    if not pooled.empty:
        pooled = pooled.sort_values(["asin", "week"])
        for m in metrics:
            if m in pooled.columns:
                pooled[m] = pd.to_numeric(pooled[m], errors="coerce")
        pooled = (
            pooled.groupby("asin")
            .apply(
                lambda g: g.assign(
                    sales_dm=g["weekly_sales"] - g["weekly_sales"].mean(),
                    **{f"{m}_dm": (g[m] - g[m].mean()) for m in metrics if m in g.columns},
                )
            )
            .reset_index(drop=True)
        )

        pooled_rows = []
        for m in metrics:
            col = f"{m}_dm"
            if col in pooled.columns:
                aligned = pooled[["sales_dm", col]].dropna()
                if aligned.shape[0] >= min_weeks:
                    r = np.corrcoef(aligned["sales_dm"].astype(float), aligned[col].astype(float))[
                        0, 1
                    ]
                    pooled_rows.append({"metric": m, "corr_sales_dm": r})
        results["pooled"] = pd.DataFrame(pooled_rows)

    return results


def build_volatility(master: pd.DataFrame) -> pd.DataFrame:
    """Build per-ASIN volatility summary for sales, price, and ratings."""
    return (
        master.groupby("asin")
        .agg(
            weeks=("week", "nunique"),
            sales_var=("weekly_sales", "var"),
            price_var=("avg_price_week", "var"),
            rating_var=("avg_rating_week", "var"),
            mean_sales=("weekly_sales", "mean"),
            mean_price=("avg_price_week", "mean"),
            mean_rating=("avg_rating_week", "mean"),
        )
        .reset_index()
    )


# ----------------------------- Optional clustering -----------------------------
def try_kmeans_clustering(df: pd.DataFrame, k: int) -> pd.DataFrame:
    """
    Optional simple KMeans clustering on selected per-ASIN features.
    Requires scikit-learn installed; otherwise returns empty DataFrame.
    """
    try:
        from sklearn.cluster import KMeans
    except Exception:
        return pd.DataFrame()

    feats = df.copy()
    # Select features (customize as needed)
    keep = ["sales_var", "price_var", "rating_var", "mean_sales", "mean_price", "mean_rating"]
    keep = [c for c in keep if c in feats.columns]
    if not keep:
        return pd.DataFrame()

    X = feats[keep].fillna(0.0).astype(float).values
    km = KMeans(n_clusters=k, n_init="auto", random_state=42)
    feats["cluster"] = km.fit_predict(X)
    feats["cluster"] = feats["cluster"].astype(int)
    return feats[["asin", "cluster"] + keep]


# ----------------------------- Main CLI -----------------------------
def main():
    parser = argparse.ArgumentParser(
        description="Amazon Reviews & Sales – Weekly Analytics Pipeline (comments in English only)."
    )
    parser.add_argument(
        "--reviews", type=str, required=True, help="Path to reviews CSV (e.g., all_reviews.csv)."
    )
    parser.add_argument(
        "--synccentric",
        type=str,
        required=False,
        default=None,
        help="Path to sales/price CSV (e.g., output total synccentric.csv).",
    )
    parser.add_argument(
        "--outdir", type=str, required=True, help="Output directory to write results."
    )
    parser.add_argument(
        "--do-cluster", type=int, default=0, help="If >0, run simple KMeans with k clusters."
    )
    args = parser.parse_args()

    os.makedirs(args.outdir, exist_ok=True)

    # Load inputs
    df_reviews = read_csv_safely(args.reviews)
    df_sync = read_csv_safely(args.synccentric) if args.synccentric else None

    status = {
        "reviews_path": args.reviews,
        "synccentric_path": args.synccentric,
        "outdir": args.outdir,
        "reviews_found": df_reviews is not None,
        "synccentric_found": df_sync is not None,
        "reviews_shape": None if df_reviews is None else list(df_reviews.shape),
        "synccentric_shape": None if df_sync is None else list(df_sync.shape),
    }

    # Build master weekly
    master, info = build_master_weekly(
        df_reviews if df_reviews is not None else pd.DataFrame(),
        df_sync if df_sync is not None else pd.DataFrame(),
    )
    status.update(info)

    # If we have weekly reviews at least, proceed
    if master.empty:
        # write status and exit
        write_csv(pd.DataFrame(), os.path.join(args.outdir, "master_weekly.csv"))
        with open(os.path.join(args.outdir, "run_status.json"), "w") as f:
            json.dump(status, f, indent=2, default=str)
        print("No weekly data could be constructed. Check input files/columns.")
        return

    # Distortion probability uses only review metrics
    weekly_reviews_only = master.dropna(subset=["avg_rating_week", "reviews_count_week"], how="all")
    if not weekly_reviews_only.empty:
        dist = compute_distortion_score(
            weekly_reviews_only[
                [
                    "asin",
                    "week",
                    "avg_rating_week",
                    "reviews_count_week",
                    "p5_share_week",
                    "rating_var_week",
                    "cum_avg_rating",
                ]
            ].dropna(how="all")
        )
    else:
        dist = pd.DataFrame(columns=["asin", "distortion_prob"])

    # Review–sales impact
    impact = compute_review_sales_impact(master)

    # Volatility summary
    volatility = build_volatility(master)

    # Optional clustering
    clusters = pd.DataFrame()
    if args.do_cluster and args.do_cluster > 0:
        clusters = try_kmeans_clustering(volatility, k=args.do_cluster)

    # Write outputs (to user-specified path)
    write_csv(master, os.path.join(args.outdir, "master_weekly.csv"))
    write_csv(dist, os.path.join(args.outdir, "distortion_prob_by_asin.csv"))
    write_csv(impact["per_asin"], os.path.join(args.outdir, "impact_per_asin.csv"))
    write_csv(impact["pooled"], os.path.join(args.outdir, "impact_pooled.csv"))
    write_csv(volatility, os.path.join(args.outdir, "volatility_summary.csv"))
    if not clusters.empty:
        write_csv(clusters, os.path.join(args.outdir, "clusters.csv"))

    with open(os.path.join(args.outdir, "run_status.json"), "w") as f:
        json.dump(status, f, indent=2, default=str)

    print("Done. Results saved to:", args.outdir)


if __name__ == "__main__":
    main()
