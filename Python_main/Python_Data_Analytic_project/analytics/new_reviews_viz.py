from datetime import timedelta
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns
from core.session_state import print_info


def _ensure_snapshot_df(session) -> pd.DataFrame | None:
    df = getattr(session, "df_snapshot", None)
    if df is None or df.empty:
        try:
            session.load_reviews_and_snapshot()
            df = getattr(session, "df_snapshot", None)
        except Exception as e:
            print_info(f"[new_reviews] Failed to load snapshot: {e}")
            return None
    return df


def _prep_daily_new_reviews(df_snap: pd.DataFrame) -> pd.DataFrame:
    df = df_snap.copy()
    if "captured_at" not in df.columns:
        return pd.DataFrame(columns=["asin", "date", "new_reviews"])  # nothing to do
    df["captured_at"] = pd.to_datetime(df["captured_at"], errors="coerce")
    df = df.dropna(subset=["captured_at"])  # keep valid timestamps
    if "new_reviews" not in df.columns:
        df["new_reviews"] = 0
    # coerce numeric just in case
    df["new_reviews"] = pd.to_numeric(df["new_reviews"], errors="coerce").fillna(0)
    df["date"] = df["captured_at"].dt.date
    daily = df.groupby(["asin", "date"], as_index=False)["new_reviews"].sum()
    return daily


def plot_new_reviews(
    session, *, days: int = 60, min_points: int = 3, spike_multiplier: float = 3.0
) -> None:
    """
    Plot daily new_reviews per ASIN over the recent window and save PNGs.

    - Per-ASIN line charts with spikes (threshold = median * spike_multiplier)
    - Total-by-day overview chart
    Outputs are saved under <collection_path>/plots/
    """
    df_snap = _ensure_snapshot_df(session)
    if df_snap is None or df_snap.empty:
        print_info("[new_reviews] Snapshot is empty. Skipping plots.")
        return

    coll_dir: Path = Path(session.collection_path)
    out_dir = coll_dir / "plots"
    out_dir.mkdir(parents=True, exist_ok=True)

    daily = _prep_daily_new_reviews(df_snap)
    if daily.empty:
        print_info("[new_reviews] No daily new_reviews data to plot.")
        return

    # Filter to recent window
    try:
        max_date = pd.to_datetime(daily["date"]).max().date()
        start_date = max_date - timedelta(days=days)
        daily = daily[pd.to_datetime(daily["date"]).dt.date >= start_date]
    except Exception:
        pass

    # Per-ASIN plots
    asins = daily["asin"].unique()
    plotted = 0
    for asin in asins:
        dfa = daily[daily["asin"] == asin].sort_values("date")
        if dfa["new_reviews"].sum() <= 0 or len(dfa) < min_points:
            continue
        med = dfa["new_reviews"].median()
        thr = med * spike_multiplier
        dfa["is_spike"] = dfa["new_reviews"] > thr

        plt.figure(figsize=(10, 5))
        sns.lineplot(data=dfa, x="date", y="new_reviews", marker="o", label="new_reviews")
        if (dfa["is_spike"].sum()) > 0:
            sp = dfa[dfa["is_spike"]]
            plt.scatter(sp["date"], sp["new_reviews"], color="red", s=50, label="spike")
        plt.title(f"ASIN {asin} — Daily new reviews (last {days}d)")
        plt.xlabel("Date")
        plt.ylabel("New reviews")
        plt.grid(True, alpha=0.3)
        plt.tight_layout()
        path = out_dir / f"new_reviews_{asin}.png"
        plt.savefig(path)
        plt.close()
        plotted += 1

    # Overview: total by day across ASINs
    if not daily.empty:
        tot = daily.groupby("date")["new_reviews"].sum().reset_index()
        tot = tot.sort_values("date")
        plt.figure(figsize=(10, 5))
        sns.barplot(data=tot, x="date", y="new_reviews", color="#4e79a7")
        plt.title(f"Total new reviews per day (last {days}d)")
        plt.xlabel("Date")
        plt.ylabel("New reviews")
        plt.xticks(rotation=45, ha="right")
        plt.tight_layout()
        path = out_dir / "new_reviews_total_by_day.png"
        plt.savefig(path)
        plt.close()

    print_info(f"[INFO] New reviews plots saved: per‑ASIN={plotted}, overview=1 → {out_dir}")
