"""
# === Module Header ===
# 📁 Module: analytics/exporter.py
# 📅 Last Reviewed: 2025-10-15
# 🔧 Status: 🟠 Under Refactor
# 👤 Owner: MatveyB
# 📝 Summary: Builds curated BI exports (dimensions, facts, and derived timeseries).
# =====================
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd


def _ensure_loaded(session) -> None:
    """Always refresh reviews and snapshot from disk for export.

    Previously this only loaded when in-memory frames were None, which could
    lead to stale exports after a collection run (session held old DataFrames).
    """
    try:
        session.load_reviews_and_snapshot()
    except Exception:
        pass


def _sentiment(df: pd.DataFrame) -> pd.DataFrame:
    if "sentiment" in df.columns:
        return df
    # Lazy import to avoid heavy deps at import time
    try:
        from analytics.review_authenticity import compute_sentiment

        return compute_sentiment(df.copy())
    except Exception:
        d = df.copy()
        d["sentiment"] = 0.0
        return d


def _write(df: pd.DataFrame, out_dir: Path, name: str, prefer_parquet: bool = True) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    if prefer_parquet:
        try:
            # Prefer pyarrow engine when available; fall back to CSV on any error
            path = out_dir / f"{name}.parquet"
            df.to_parquet(path, index=False, engine="pyarrow")
            return path
        except Exception:
            pass
    path = out_dir / f"{name}.csv"
    df.to_csv(path, index=False)
    return path


def export_for_bi(session, *, prefer_parquet: bool = True) -> Path:
    """Materialize clean tables for Power BI under exports/<run_ts> and exports/latest.

    Returns the path to exports/latest.
    """
    _ensure_loaded(session)

    base: Path = Path(getattr(session, "collection_path", "DATA"))
    run_ts = pd.Timestamp.utcnow().strftime("%Y%m%d_%H%M%S")
    out_ver = base / "exports" / run_ts
    out_latest = base / "exports" / "latest"
    out_ver.mkdir(parents=True, exist_ok=True)

    # 1) asins_dim
    asins = getattr(session, "df_asins", pd.DataFrame()).copy()
    if not asins.empty:
        if "category" in asins.columns and "category_path" not in asins.columns:
            asins = asins.rename(columns={"category": "category_path"})
        for col in ["title", "category_path", "country"]:
            if col not in asins.columns:
                asins[col] = None
        asins_dim = asins[
            [c for c in ["asin", "title", "category_path", "country"] if c in asins.columns]
        ].dropna(subset=["asin"])
    else:
        asins_dim = pd.DataFrame(columns=["asin", "title", "category_path", "country"])
    _write(asins_dim, out_ver, "asins_dim", prefer_parquet)

    # 2) reviews_fact (ensure sentiment, helpful votes, schema)
    rev = getattr(session, "df_reviews", pd.DataFrame()).copy()
    if not rev.empty:
        # Normalize columns
        if "review_rating" in rev.columns and "rating" not in rev.columns:
            rev["rating"] = rev["review_rating"]
        if "review_helpful_votes" not in rev.columns:
            rev["review_helpful_votes"] = 0
        # Dates
        if "review_date" in rev.columns:
            rev["review_date"] = pd.to_datetime(rev["review_date"], errors="coerce").dt.date
        rev = _sentiment(rev)
        keep = [
            c
            for c in [
                "asin",
                "review_id",
                "review_date",
                "rating",
                "sentiment",
                "review_helpful_votes",
                "captured_at",
            ]
            if c in rev.columns
        ]
        reviews_fact = rev[keep].dropna(subset=["asin"]).copy()
    else:
        reviews_fact = pd.DataFrame(
            columns=[
                "asin",
                "review_id",
                "review_date",
                "rating",
                "sentiment",
                "review_helpful_votes",
                "captured_at",
            ]
        )
    _write(reviews_fact, out_ver, "reviews_fact", prefer_parquet)

    # 3) snapshot_fact
    snap = getattr(session, "df_snapshot", pd.DataFrame()).copy()
    if not snap.empty:
        # Normalize schema from various producers (daily snapshot vs collector)
        if "rating" not in snap.columns and "avg_rating" in snap.columns:
            snap["rating"] = snap["avg_rating"]
        if "total_reviews" not in snap.columns and "review_count" in snap.columns:
            snap["total_reviews"] = snap["review_count"]
        if "bsr" not in snap.columns and "bsr_rank" in snap.columns:
            snap["bsr"] = snap["bsr_rank"]
        # Ensure per-run increment column exists
        if "new_reviews" not in snap.columns:
            snap["new_reviews"] = 0
        # Optional diagnostics
        if "pages_visited" not in snap.columns:
            snap["pages_visited"] = None
        if "stopped_reason" not in snap.columns:
            snap["stopped_reason"] = None

        for col in [
            "captured_at",
            "price",
            "rating",
            "total_reviews",
            "new_reviews",
            "bsr",
            "category_path",
            "title",
            "pages_visited",
            "stopped_reason",
        ]:
            if col not in snap.columns:
                snap[col] = None
        # Hidden price flag (before coercion): detect textual placeholders like 'Price Hidden' / 'See price'
        try:
            snap["price_hidden"] = (
                snap["price"]
                .astype(str)
                .str.lower()
                .str.contains("price hidden|see price|click to see price", regex=True, na=False)
                if "price" in snap.columns
                else False
            )
        except Exception:
            snap["price_hidden"] = False
        # Coerce numerics where applicable for consistency downstream
        # Price often contains currency symbols; strip non-numeric before cast
        if "price" in snap.columns:
            snap["price"] = (
                snap["price"]
                .astype(str)
                .str.replace(r"[^0-9\.,-]", "", regex=True)
                .str.replace(",", "")
            )
        for num_col in ("price", "rating", "total_reviews", "new_reviews", "bsr"):
            if num_col in snap.columns:
                snap[num_col] = pd.to_numeric(snap[num_col], errors="coerce")

        snapshot_fact = snap[
            [
                "asin",
                "captured_at",
                "price",
                "price_hidden",
                "rating",
                "total_reviews",
                "new_reviews",
                "bsr",
                "category_path",
                "title",
                "pages_visited",
                "stopped_reason",
            ]
        ].dropna(subset=["asin"])
    else:
        snapshot_fact = pd.DataFrame(
            columns=[
                "asin",
                "captured_at",
                "price",
                "rating",
                "total_reviews",
                "new_reviews",
                "bsr",
                "category_path",
                "title",
                "pages_visited",
                "stopped_reason",
            ]
        )
    _write(snapshot_fact, out_ver, "snapshot_fact", prefer_parquet)

    # 4) sentiment_daily
    if not reviews_fact.empty:
        tmp = reviews_fact.copy()
        # Derive sentiment label
        tmp["sentiment_label"] = tmp["sentiment"].apply(
            lambda x: "positive" if x > 0.3 else ("negative" if x < -0.3 else "neutral")
        )
        tmp["date"] = pd.to_datetime(tmp["review_date"], errors="coerce").dt.date
        grp = tmp.dropna(subset=["date"]).groupby(["asin", "date"])
        sentiment_daily = grp.agg(
            review_count=("sentiment", "size"),
            avg_sentiment=("sentiment", "mean"),
            pos_cnt=("sentiment_label", lambda s: (s == "positive").sum()),
            neut_cnt=("sentiment_label", lambda s: (s == "neutral").sum()),
            neg_cnt=("sentiment_label", lambda s: (s == "negative").sum()),
        ).reset_index()
    else:
        sentiment_daily = pd.DataFrame(
            columns=[
                "asin",
                "date",
                "review_count",
                "avg_sentiment",
                "pos_cnt",
                "neut_cnt",
                "neg_cnt",
            ]
        )

    # Optional densification: ensure a row per (asin, date) present in snapshot
    # to facilitate continuous time-series even when no reviews on that date.
    try:
        if not snap.empty and "captured_at" in snap.columns:
            s = snap.copy()
            s["captured_at"] = pd.to_datetime(s["captured_at"], errors="coerce")
            s = s.dropna(subset=["captured_at"]).copy()
            s["date"] = s["captured_at"].dt.date
            grid = s[["asin", "date"]].dropna().drop_duplicates()
            if not grid.empty:
                sd = sentiment_daily.copy()
                sentiment_daily = grid.merge(sd, on=["asin", "date"], how="left").assign(
                    review_count=lambda d: pd.to_numeric(d.get("review_count"), errors="coerce")
                    .fillna(0)
                    .astype(int),
                    pos_cnt=lambda d: pd.to_numeric(d.get("pos_cnt"), errors="coerce")
                    .fillna(0)
                    .astype(int),
                    neut_cnt=lambda d: pd.to_numeric(d.get("neut_cnt"), errors="coerce")
                    .fillna(0)
                    .astype(int),
                    neg_cnt=lambda d: pd.to_numeric(d.get("neg_cnt"), errors="coerce")
                    .fillna(0)
                    .astype(int),
                )
    except Exception:
        pass

    _write(sentiment_daily, out_ver, "sentiment_daily", prefer_parquet)

    # 4.1) nps_daily and nps_rolling (7d/28d): daily NPS components and rolling NPS per ASIN
    try:
        nps_daily = pd.DataFrame()
        if not rev.empty and "rating" in rev.columns:
            rv = rev.copy()
            # Coerce types
            if "review_date" in rv.columns:
                rv["review_date"] = pd.to_datetime(rv["review_date"], errors="coerce").dt.date
            rv["rating"] = pd.to_numeric(rv["rating"], errors="coerce")
            rv = rv.dropna(subset=["asin", "review_date", "rating"]).copy()

            # Prepare daily classification counts
            rv["promoter"] = (rv["rating"] == 5).astype(int)
            rv["passive"] = (rv["rating"] == 4).astype(int)
            rv["detractor"] = rv["rating"].between(1, 3).astype(int)

            g = (
                rv.groupby(["asin", "review_date"], dropna=False)[
                    ["promoter", "passive", "detractor"]
                ]
                .sum()
                .reset_index()
                .rename(
                    columns={
                        "review_date": "date",
                        "promoter": "promoter_cnt",
                        "passive": "passive_cnt",
                        "detractor": "detractor_cnt",
                    }
                )
            )
            g["n_reviews"] = (
                pd.to_numeric(g["promoter_cnt"], errors="coerce").fillna(0)
                + pd.to_numeric(g["passive_cnt"], errors="coerce").fillna(0)
                + pd.to_numeric(g["detractor_cnt"], errors="coerce").fillna(0)
            )
            # Densify by reviews capture_date range (requested): use reviews' captured_at → date
            try:
                if "captured_at" in rv.columns:
                    rcap = rv.copy()
                    rcap["captured_at"] = pd.to_datetime(rcap["captured_at"], errors="coerce")
                    rcap = rcap.dropna(subset=["captured_at"]).copy()
                    rcap["date"] = rcap["captured_at"].dt.date
                    # Grid of (asin, date) for every captured day per ASIN
                    grid = rcap[["asin", "date"]].dropna().drop_duplicates()
                    if not grid.empty:
                        g = grid.merge(g, on=["asin", "date"], how="left")
                        for c in ("promoter_cnt", "passive_cnt", "detractor_cnt", "n_reviews"):
                            if c in g.columns:
                                g[c] = (
                                    pd.to_numeric(g.get(c), errors="coerce").fillna(0).astype(int)
                                )
            except Exception:
                pass

            # Compute daily NPS (leave blank when n_reviews==0)
            g["nps_daily"] = (
                (g["promoter_cnt"].astype(float) - g["detractor_cnt"].astype(float))
                / g["n_reviews"].replace({0: pd.NA})
            ) * 100.0
            nps_daily = g[
                [
                    "asin",
                    "date",
                    "promoter_cnt",
                    "passive_cnt",
                    "detractor_cnt",
                    "n_reviews",
                    "nps_daily",
                ]
            ]
        _write(nps_daily, out_ver, "nps_daily", prefer_parquet)

        # Rolling 7d/28d per ASIN (calendar-based rolling since we densified)
        nps_roll = pd.DataFrame()
        if not nps_daily.empty:
            nd = nps_daily.copy()
            nd["date"] = pd.to_datetime(nd["date"], errors="coerce")
            nd = nd.dropna(subset=["date"]).sort_values(["asin", "date"]).copy()

            def _roll_nps(gdf: pd.DataFrame) -> pd.DataFrame:
                gdf = gdf.set_index("date").sort_index()
                for c in ("promoter_cnt", "detractor_cnt", "n_reviews"):
                    gdf[c] = pd.to_numeric(gdf.get(c), errors="coerce").fillna(0)
                r7_prom = gdf["promoter_cnt"].rolling(window=7, min_periods=3).sum()
                r7_detr = gdf["detractor_cnt"].rolling(window=7, min_periods=3).sum()
                r7_den = gdf["n_reviews"].rolling(window=7, min_periods=3).sum()
                r28_prom = gdf["promoter_cnt"].rolling(window=28, min_periods=7).sum()
                r28_detr = gdf["detractor_cnt"].rolling(window=28, min_periods=7).sum()
                r28_den = gdf["n_reviews"].rolling(window=28, min_periods=7).sum()

                out = gdf[["promoter_cnt", "passive_cnt", "detractor_cnt", "n_reviews"]].copy()
                out["nps_7d"] = ((r7_prom - r7_detr) / r7_den.replace({0: pd.NA})) * 100.0
                out["nps_28d"] = ((r28_prom - r28_detr) / r28_den.replace({0: pd.NA})) * 100.0
                return out.reset_index()

            nps_roll = nd.groupby("asin", group_keys=False).apply(_roll_nps)
        _write(nps_roll, out_ver, "nps_rolling_7d", prefer_parquet)
        _write(nps_roll, out_ver, "nps_rolling_28d", prefer_parquet)
    except Exception:
        pass

    # 5) nps_by_asin
    try:
        from analytics.review_authenticity import compute_nps_per_asin

        nps_by_asin = compute_nps_per_asin(
            rev if not rev.empty else pd.DataFrame(columns=["asin", "rating"])
        )
        # Add capture date for model anchoring (max review_date per ASIN)
        try:
            last_dates = pd.DataFrame(columns=["asin", "date_captured"])
            if not rev.empty and "review_date" in rev.columns:
                r2 = rev.copy()
                r2["review_date"] = pd.to_datetime(r2["review_date"], errors="coerce").dt.date
                last_dates = (
                    r2.dropna(subset=["asin", "review_date"])
                    .groupby("asin")["review_date"]
                    .max()
                    .reset_index()
                    .rename(columns={"review_date": "date_captured"})
                )
            nps_by_asin = nps_by_asin.merge(last_dates, on="asin", how="left")
        except Exception:
            # Ensure column exists even if computation failed
            if "date_captured" not in nps_by_asin.columns:
                nps_by_asin["date_captured"] = pd.NaT
    except Exception:
        nps_by_asin = pd.DataFrame(
            columns=[
                "asin",
                "n_reviews",
                "promoter_pct",
                "passive_pct",
                "detractor_pct",
                "nps",
                "date_captured",
            ]
        )
    _write(nps_by_asin, out_ver, "nps_by_asin", prefer_parquet)

    # 6) flags_detail and flags_summary_by_asin (best-effort)
    try:
        # Reuse heuristics from authenticity module
        import numpy as np

        df_flags = rev.copy()
        if df_flags.empty:
            flags_detail = pd.DataFrame(
                columns=["asin", "review_id", "review_date", "text_length", "auth_flag"]
            )
        else:
            df_flags["text_length"] = df_flags["review_text"].astype(str).str.strip().str.len()
            nonzero = df_flags.loc[df_flags["text_length"] > 0, "text_length"]
            if not nonzero.empty:
                q10 = np.nanpercentile(nonzero, 10)
                q90 = np.nanpercentile(nonzero, 90)
            else:
                q10, q90 = 20, 1000
            too_short = df_flags["text_length"] <= q10
            too_long = df_flags["text_length"] >= q90
            # Duplicates
            dup = df_flags["review_text"].duplicated(keep=False)
            # High-volume per day
            df_flags["review_date"] = pd.to_datetime(
                df_flags["review_date"], errors="coerce"
            ).dt.date
            freq = df_flags.groupby(["asin", "review_date"]).size()
            hv_pairs = set(freq[freq > 10].index)

            def _flags_row(row):
                f = []
                i = row.name
                if too_short.iloc[i]:
                    f.append("short")
                if too_long.iloc[i]:
                    f.append("long")
                if dup.iloc[i]:
                    f.append("duplicate")
                if (row.get("asin"), row.get("review_date")) in hv_pairs:
                    f.append("high_volume")
                return ",".join(f)

            df_flags = df_flags.reset_index(drop=True)
            df_flags["auth_flag"] = df_flags.apply(_flags_row, axis=1)
            flags_detail = df_flags[
                [
                    c
                    for c in ["asin", "review_id", "review_date", "text_length", "auth_flag"]
                    if c in df_flags.columns
                ]
            ]
        _write(flags_detail, out_ver, "flags_detail", prefer_parquet)

        if not flags_detail.empty:
            exploded = flags_detail.assign(
                auth_flag_list=flags_detail["auth_flag"].str.split(",")
            ).explode("auth_flag_list")
            exploded = exploded[exploded["auth_flag_list"].astype(str) != ""]
            flags_summary = (
                exploded.groupby(["asin", "auth_flag_list"])
                .size()
                .unstack(fill_value=0)
                .reset_index()
            )
        else:
            flags_summary = pd.DataFrame(
                columns=["asin", "short", "long", "duplicate", "high_volume", "hyperactive_author"]
            )
        _write(flags_summary, out_ver, "flags_summary_by_asin", prefer_parquet)
    except Exception:
        pass

    # 6.1) snapshot_latest: last snapshot row per ASIN
    try:
        snap_latest = pd.DataFrame()
        if not snap.empty:
            s = snap.copy()
            if "captured_at" in s.columns:
                s["captured_at"] = pd.to_datetime(s["captured_at"], errors="coerce")
                s = s.dropna(subset=["captured_at"]).copy()
                s = s.sort_values(["asin", "captured_at"]).drop_duplicates(
                    subset=["asin"], keep="last"
                )
            keep_cols = [
                c
                for c in [
                    "asin",
                    "captured_at",
                    "price",
                    "price_hidden",
                    "rating",
                    "total_reviews",
                    "new_reviews",
                    "bsr",
                    "category_path",
                    "title",
                ]
                if c in s.columns
            ]
            snap_latest = s[keep_cols]
        _write(snap_latest, out_ver, "snapshot_latest", prefer_parquet)
    except Exception:
        pass

    # 7) metrics_daily: join latest-per-day snapshot with sentiment_daily (+3d smoothing)
    try:
        # Build daily snapshot as last capture per day
        snap_daily = pd.DataFrame()
        if not snap.empty:
            s = snap.copy()
            if "captured_at" in s.columns:
                s["captured_at"] = pd.to_datetime(s["captured_at"], errors="coerce")
                s = s.dropna(subset=["captured_at"]).copy()
                s["date"] = s["captured_at"].dt.date
                s = s.sort_values(["asin", "captured_at"]).drop_duplicates(
                    subset=["asin", "date"], keep="last"
                )
            else:
                s["date"] = pd.NaT
            # Coerce numerics
            if "price" in s.columns:
                s["price"] = (
                    s["price"]
                    .astype(str)
                    .str.replace(r"[^0-9\.,-]", "", regex=True)
                    .str.replace(",", "")
                )
            for num_col in ("price", "rating", "total_reviews", "bsr"):
                if num_col in s.columns:
                    s[num_col] = pd.to_numeric(s[num_col], errors="coerce")
            keep_cols = [
                c
                for c in ["asin", "date", "price", "rating", "total_reviews", "bsr"]
                if c in s.columns
            ]
            snap_daily = s[keep_cols].copy()
            # Merge per-run new reviews aggregated by day (sum across runs in day)
            try:
                t = snap.copy()
                if "captured_at" in t.columns:
                    t["captured_at"] = pd.to_datetime(t["captured_at"], errors="coerce")
                    t = t.dropna(subset=["captured_at"]).copy()
                    t["date"] = t["captured_at"].dt.date
                    # Coerce 'new_reviews' to numeric before aggregation
                    if "new_reviews" in t.columns:
                        t["new_reviews"] = pd.to_numeric(t["new_reviews"], errors="coerce")
                    nr = (
                        t.groupby(["asin", "date"])
                        .agg(new_reviews=("new_reviews", "sum"))
                        .reset_index()
                    )
                    snap_daily = snap_daily.merge(nr, on=["asin", "date"], how="left")
            except Exception:
                pass

        sd = sentiment_daily.copy() if "sentiment_daily" in locals() else pd.DataFrame()
        if not sd.empty and "date" in sd.columns:
            # ensure date type alignment
            sd["date"] = pd.to_datetime(sd["date"], errors="coerce").dt.date

        if not snap_daily.empty or not sd.empty:
            metrics_daily = pd.merge(
                snap_daily,
                sd,
                on=["asin", "date"],
                how="outer",
                suffixes=("", ""),
            )
        else:
            metrics_daily = pd.DataFrame(
                columns=[
                    "asin",
                    "date",
                    "price",
                    "rating",
                    "total_reviews",
                    "bsr",
                    "review_count",
                    "avg_sentiment",
                    "pos_cnt",
                    "neut_cnt",
                    "neg_cnt",
                ]
            )

        # Add 3-day smoothing columns per ASIN (rolling on calendar days)
        if not metrics_daily.empty:
            md = metrics_daily.copy()
            md["date"] = pd.to_datetime(md["date"], errors="coerce")
            md = md.dropna(subset=["date"]).sort_values(["asin", "date"]).copy()
            cols = [
                c
                for c in ["avg_sentiment", "price", "rating", "bsr", "review_count"]
                if c in md.columns
            ]

            def _roll3(g: pd.DataFrame) -> pd.DataFrame:
                g = g.set_index("date").sort_index()
                for c in cols:
                    g[c] = pd.to_numeric(g[c], errors="coerce")
                r3 = g[cols].rolling(window=3, min_periods=2).mean()
                r3.columns = [f"{c}_3d" for c in r3.columns]
                out = pd.concat([g, r3], axis=1).reset_index()
                return out

            md = md.groupby("asin", group_keys=False).apply(_roll3)
            metrics_daily = md
        _write(metrics_daily, out_ver, "metrics_daily", prefer_parquet)
    except Exception:
        pass

    # 8) metrics_rolling_7d / 28d: rolling averages per ASIN
    try:
        mr = pd.DataFrame()
        if not metrics_daily.empty:
            md = metrics_daily.copy()
            md["date"] = pd.to_datetime(md["date"], errors="coerce")
            md = md.dropna(subset=["date"])  # keep valid dates
            md = md.sort_values(["asin", "date"])  # ensure order

            def _roll(g: pd.DataFrame) -> pd.DataFrame:
                g = g.set_index("date").sort_index()
                cols = [
                    c
                    for c in ["avg_sentiment", "price", "rating", "bsr", "review_count"]
                    if c in g.columns
                ]
                # Coerce numeric
                for c in cols:
                    g[c] = pd.to_numeric(g[c], errors="coerce")
                r7 = g[cols].rolling(window=7, min_periods=3).mean()
                r7.columns = [f"{c}_7d" for c in r7.columns]
                r28 = g[cols].rolling(window=28, min_periods=7).mean()
                r28.columns = [f"{c}_28d" for c in r28.columns]
                out = pd.concat([g, r7, r28], axis=1).reset_index()
                return out

            mr = md.groupby("asin", group_keys=False).apply(_roll)
        _write(mr, out_ver, "metrics_rolling_7d", prefer_parquet)
        _write(mr, out_ver, "metrics_rolling_28d", prefer_parquet)
    except Exception:
        pass

    # 9) correlations_by_asin: 7/28/90-day Spearman correlations (raw and 3d-smoothed)
    try:
        from datetime import timedelta

        try:
            from scipy.stats import spearmanr  # type: ignore

            _has_scipy = True
        except Exception:
            _has_scipy = False

        def _corr(a, b):
            a = pd.to_numeric(pd.Series(a), errors="coerce")
            b = pd.to_numeric(pd.Series(b), errors="coerce")
            mask = a.notna() & b.notna()
            if mask.sum() < 5:
                return None, None
            if _has_scipy:
                try:
                    r, p = spearmanr(a[mask], b[mask], nan_policy="omit")  # type: ignore
                    return float(r), float(p)
                except Exception:
                    pass
            # Fallback: pandas corr, no p-value
            try:
                r = a[mask].corr(b[mask], method="spearman")
                return float(r), None
            except Exception:
                return None, None

        cb_rows = []
        base = metrics_daily.copy()
        if not base.empty:
            base["date"] = pd.to_datetime(base["date"], errors="coerce")
            for asin, g in base.groupby("asin"):
                g = g.dropna(subset=["date"]).sort_values("date")
                if g.empty:
                    continue
                last = g["date"].max()
                for smoothing in ("raw", "sm3d"):
                    # pick column names for smoothing mode
                    s_col = "avg_sentiment_3d" if smoothing == "sm3d" else "avg_sentiment"
                    p_col = "price_3d" if smoothing == "sm3d" else "price"
                    r_col = "rating_3d" if smoothing == "sm3d" else "rating"
                    b_col = "bsr_3d" if smoothing == "sm3d" else "bsr"
                    for win in (7, 28, 90):
                        start = last - timedelta(days=win)
                        w = g[(g["date"] >= start) & (g["date"] <= last)].copy()
                        if len(w) < 5:
                            continue
                        s = w.get(s_col)
                        pr = w.get(p_col)
                        rt = w.get(r_col)
                        bsr_num = (
                            pd.to_numeric(w.get(b_col), errors="coerce")
                            if b_col in w.columns
                            else None
                        )
                        bsr_inv = (-bsr_num) if bsr_num is not None else None

                        sent_price_r, sent_price_p = _corr(s, pr)
                        sent_bsr_r, sent_bsr_p = _corr(s, bsr_inv)
                        rating_price_r, rating_price_p = _corr(rt, pr)
                        rating_bsr_r, rating_bsr_p = _corr(rt, bsr_inv)

                        row = {
                            "asin": asin,
                            "smoothing": smoothing,
                            "window_days": win,
                            "n_obs": int(len(w)),
                            "last_date": last.date().isoformat(),
                            "sent_price_r": sent_price_r,
                            "sent_price_p": sent_price_p,
                            "sent_bsr_r": sent_bsr_r,
                            "sent_bsr_p": sent_bsr_p,
                            "rating_price_r": rating_price_r,
                            "rating_price_p": rating_price_p,
                            "rating_bsr_r": rating_bsr_r,
                            "rating_bsr_p": rating_bsr_p,
                        }
                        for k in ("sent_price", "sent_bsr", "rating_price", "rating_bsr"):
                            p = row.get(f"{k}_p")
                            row[f"{k}_sig"] = (p is not None) and (p < 0.05)
                        cb_rows.append(row)
        correlations_by_asin = pd.DataFrame(cb_rows)
        _write(correlations_by_asin, out_ver, "correlations_by_asin", prefer_parquet)
    except Exception:
        pass

    # 9.1) correlations_alerts_7d: strong 7d signals per ASIN (raw & sm3d)
    try:
        from datetime import timedelta

        # thresholds (could be moved to env)
        MIN_ABS_R = 0.6
        MAX_P = 0.1
        MIN_OBS = 5

        alerts = []
        if not base.empty:
            base["date"] = pd.to_datetime(base["date"], errors="coerce")
            for asin, g in base.groupby("asin"):
                g = g.dropna(subset=["date"]).sort_values("date")
                if g.empty:
                    continue
                last = g["date"].max()
                prev = last - timedelta(days=1)

                def _corr_at(end: pd.Timestamp, smoothing: str):
                    start = end - timedelta(days=7)
                    w = g[(g["date"] >= start) & (g["date"] <= end)].copy()
                    if len(w) < MIN_OBS:
                        return None
                    s_col = "avg_sentiment_3d" if smoothing == "sm3d" else "avg_sentiment"
                    p_col = "price_3d" if smoothing == "sm3d" else "price"
                    r_col = "rating_3d" if smoothing == "sm3d" else "rating"
                    b_col = "bsr_3d" if smoothing == "sm3d" else "bsr"
                    s = w.get(s_col)
                    pr = w.get(p_col)
                    rt = w.get(r_col)
                    bsr_num = (
                        pd.to_numeric(w.get(b_col), errors="coerce") if b_col in w.columns else None
                    )
                    bsr_inv = (-bsr_num) if bsr_num is not None else None
                    res = {}
                    res["sent_price_r"], res["sent_price_p"] = _corr(s, pr)
                    res["sent_bsr_r"], res["sent_bsr_p"] = _corr(s, bsr_inv)
                    res["rating_price_r"], res["rating_price_p"] = _corr(rt, pr)
                    res["rating_bsr_r"], res["rating_bsr_p"] = _corr(rt, bsr_inv)
                    res["n_obs"] = int(len(w))
                    return res

                for smoothing in ("raw", "sm3d"):
                    cur = _corr_at(last, smoothing)
                    prev_res = _corr_at(prev, smoothing)
                    if not cur:
                        continue
                    for k in ("sent_price", "sent_bsr", "rating_price", "rating_bsr"):
                        r = cur.get(f"{k}_r")
                        p = cur.get(f"{k}_p")
                        n = cur.get("n_obs", 0)
                        if r is None or abs(r) < MIN_ABS_R or n < MIN_OBS:
                            continue
                        sig = (p is not None) and (p < MAX_P)
                        stable = False
                        if prev_res and prev_res.get(f"{k}_r") is not None:
                            stable = (prev_res.get(f"{k}_r") >= 0) == (r >= 0)
                        severity = abs(r) * (1.0 if sig else 0.8) * (1.1 if stable else 1.0)
                        alerts.append(
                            {
                                "asin": asin,
                                "date": last.date().isoformat(),
                                "smoothing": smoothing,
                                "pair": k,
                                "r": r,
                                "p": p,
                                "n_obs": n,
                                "sig": sig,
                                "stable": stable,
                                "severity": severity,
                            }
                        )
        alerts_df = pd.DataFrame(alerts)
        # Ensure schema even when no alerts detected
        if alerts_df.empty:
            alerts_df = pd.DataFrame(
                columns=[
                    "asin",
                    "date",
                    "smoothing",
                    "pair",
                    "r",
                    "p",
                    "n_obs",
                    "sig",
                    "stable",
                    "severity",
                ]
            )
        _write(alerts_df, out_ver, "correlations_alerts_7d", prefer_parquet)
    except Exception:
        pass

    # Copy version → latest (overwrite files)
    out_latest.mkdir(parents=True, exist_ok=True)
    for f in out_ver.iterdir():
        if f.is_file():
            (out_latest / f.name).write_bytes(f.read_bytes())

    return out_latest
