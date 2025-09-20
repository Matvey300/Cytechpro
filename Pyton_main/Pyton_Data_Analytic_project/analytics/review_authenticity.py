from typing import Dict

import numpy as np
import pandas as pd
from core.collection_io import list_collections
from core.collection_io import load_collection as io_load_collection
from core.collection_io import parse_collection_dirname
from core.session_state import SessionState
from matplotlib.patches import Patch
from textblob import TextBlob


def _asin_title_map(session: SessionState) -> Dict[str, str]:
    """Best-effort map ASIN -> product title from snapshot (preferred) or collection list."""
    mapping: Dict[str, str] = {}
    try:
        snap = getattr(session, "df_snapshot", None)
        if (
            snap is not None
            and not snap.empty
            and "asin" in snap.columns
            and "title" in snap.columns
        ):
            for _, r in snap.dropna(subset=["asin", "title"]).iterrows():
                mapping[str(r["asin"])] = str(r["title"]).strip()
    except Exception:
        pass
    try:
        ca = getattr(session, "df_asins", None)
        if ca is not None and not ca.empty and "asin" in ca.columns and "title" in ca.columns:
            for _, r in ca.dropna(subset=["asin", "title"]).iterrows():
                mapping.setdefault(str(r["asin"]), str(r["title"]).strip())
    except Exception:
        pass
    return mapping


def _short_label(asin: str, title_map: Dict[str, str], max_len: int = 28) -> str:
    title = title_map.get(str(asin))
    if not title:
        return f"ASIN: {asin}"
    title = title.strip()
    return title if len(title) <= max_len else (title[: max_len - 3] + "...")


def main_menu():
    print("1) Analyze Review Authenticity (Trustworthiness)")
    print("2) View flagged reviews (auth_flag)")
    print("0) Exit")


def main():
    while True:
        main_menu()
        choice = input("Enter your choice: ").strip()

        if choice == "1":
            # Pick collection and run authenticity analysis
            cols = list_collections()
            if not cols:
                print("[!] No collections found.")
                continue
            for i, name in enumerate(cols, 1):
                print(f"{i}) {name}")
            selected = input("Select collection number: ").strip()
            try:
                idx = int(selected) - 1
                if not (0 <= idx < len(cols)):
                    print("[!] Invalid selection.")
                    continue
            except ValueError:
                print("[!] Invalid input.")
                continue
            parts = parse_collection_dirname(cols[idx])
            cid = parts["cid"]
            session = SessionState()
            io_load_collection(cid, session)
            session.load_reviews_and_snapshot()
            analyze_review_authenticity(session)

        elif choice == "2":
            # Pick collection and explore flagged reviews
            cols = list_collections()
            if not cols:
                print("[!] No collections found.")
                continue
            for i, name in enumerate(cols, 1):
                print(f"{i}) {name}")
            selected = input("Select collection number: ").strip()
            try:
                idx = int(selected) - 1
                if not (0 <= idx < len(cols)):
                    print("[!] Invalid selection.")
                    continue
            except ValueError:
                print("[!] Invalid input.")
                continue
            parts = parse_collection_dirname(cols[idx])
            cid = parts["cid"]
            session = SessionState()
            io_load_collection(cid, session)
            session.load_reviews_and_snapshot()
            explore_flagged_reviews(session)

        elif choice == "0":
            print("Exiting.")
            break
        else:
            print("Invalid choice. Please try again.")


# --- Authenticity analysis function ---
def analyze_review_authenticity(session):
    """
    Unified Review Authenticity Test based on 3 heuristics:
    1. Suspicious review length (too short or too long).
    2. High frequency of reviews per ASIN per day.
    3. Duplicate review content across the dataset.
    """
    from collections import defaultdict

    import matplotlib.pyplot as plt

    df = session.df_reviews
    if df is None or len(getattr(df, "columns", [])) == 0:
        session.load_reviews_and_snapshot()
        df = session.df_reviews
    df = compute_sentiment(df)
    df = df.rename(columns={"review_rating": "rating"})
    if df is None or df.empty:
        print("[!] No review data found in session.")
        return

    collection_id = session.collection_id
    print(f"\n[🔍] Authenticity analysis for collection: {collection_id}")

    print(f"[DEBUG] ASINs in dataset: {df['asin'].nunique()}")
    print(f"[DEBUG] Length thresholds: short<= {q10:.0f} | long>= {q90:.0f} chars")

    # Step 1: Length-based heuristics (deciles on non-empty reviews)
    df["text_length"] = df["review_text"].astype(str).str.strip().str.len()
    nonzero = df.loc[df["text_length"] > 0, "text_length"]
    if not nonzero.empty:
        q10 = np.nanpercentile(nonzero, 10)
        q90 = np.nanpercentile(nonzero, 90)
        if not np.isfinite(q10):
            q10 = 20
        if not np.isfinite(q90):
            q90 = max(100, float(nonzero.max()))
    else:
        q10, q90 = 20, 1000
    too_short = df["text_length"] <= q10
    too_long = df["text_length"] >= q90

    # Step 2: High review frequency per ASIN per day
    df["review_date"] = pd.to_datetime(df["review_date"], errors="coerce")
    freq_counts = df.groupby(["asin", "review_date"]).size()
    high_volume_pairs = freq_counts[freq_counts > 10].index

    # Step 3: Duplicate review texts
    duplicates = df["review_text"].duplicated(keep=False)

    # Flagging logic
    flags = defaultdict(list)
    for i, row in df.iterrows():
        if too_short[i]:
            flags[i].append("short")
        if too_long[i]:
            flags[i].append("long")
        if (row["asin"], row["review_date"]) in high_volume_pairs:
            flags[i].append("high_volume")
        if duplicates[i]:
            flags[i].append("duplicate")

    hyperactive_flags = flag_hyperactive_reviewers(df)

    df["auth_flag"] = df.index.map(lambda i: ",".join(flags[i]) if flags[i] else "")
    df.loc[hyperactive_flags != "", "auth_flag"] += "," + hyperactive_flags
    df["auth_flag"] = df["auth_flag"].str.strip(",")  # cleanup leading/trailing commas

    print(f" - Reviews too short: {too_short.sum()}")
    print(f" - Reviews too long: {too_long.sum()}")
    print(f" - High-volume days: {len(high_volume_pairs)}")
    print(f" - Duplicated reviews: {duplicates.sum()}")
    print(f" - Hyperactive reviewers: {(hyperactive_flags != '').sum()}")
    print(f"\n[ℹ️] Total flagged reviews: {(df['auth_flag'] != '').sum()}")

    print("\n[✅] Authenticity check completed.")

    print("\n[📊] Running sentiment-based NPS analysis...")
    nps_df = compute_nps_per_asin(df)
    print(f"[DEBUG] ASINs in NPS analysis: {nps_df['asin'].nunique()}")
    if nps_df.empty:
        print("[⚠] NPS analysis could not be performed.")
    else:
        top_asins_nps = (
            nps_df[nps_df["n_reviews"] >= 5].sort_values(by="nps", ascending=False).head(5)
        )
        if len(top_asins_nps) < 5:
            print(f"[⚠] Only {len(top_asins_nps)} ASINs qualified for NPS analysis.")
        print(nps_df[["asin", "nps"]].to_string(index=False))

        # Pie charts for NPS composition
        print("\n[🧪] Top ASINs by NPS:\n", top_asins_nps[["asin", "n_reviews", "nps"]])

        fig, axes = plt.subplots(1, len(top_asins_nps), figsize=(6 * len(top_asins_nps), 6))
        if len(top_asins_nps) == 1:
            axes = [axes]

        title_map = _asin_title_map(session)
        for ax, (_, row) in zip(axes, top_asins_nps.iterrows()):
            asin = row["asin"]
            sizes = [row["promoter_pct"], row["passive_pct"], row["detractor_pct"]]
            labels = ["Promoter", "Passive", "Detractor"]
            colors = ["mediumseagreen", "gold", "tomato"]
            ax.pie(sizes, labels=labels, autopct="%1.1f%%", colors=colors, startangle=140)
            ax.set_title(
                f"{_short_label(asin, title_map)}\n({int(row['n_reviews'])} reviews)", fontsize=12
            )

        plt.suptitle("NPS Composition for Top 5 ASINs (≥10 reviews)", fontsize=16)
        plt.tight_layout(rect=[0, 0.03, 1, 0.95])
        legend_elems = [
            Patch(facecolor="mediumseagreen", label="Promoter"),
            Patch(facecolor="gold", label="Passive"),
            Patch(facecolor="tomato", label="Detractor"),
        ]
        fig.legend(handles=legend_elems, loc="upper right")
        plt.show()

    # --- Sentiment analysis and visualization ---
    df["sentiment_label"] = df["sentiment"].apply(
        lambda x: "positive" if x > 0.3 else "negative" if x < -0.3 else "neutral"
    )

    sentiment_summary = df.groupby("asin")["sentiment"].mean().reset_index()
    print(f"[DEBUG] ASINs in sentiment analysis: {sentiment_summary['asin'].nunique()}")
    sentiment_summary = sentiment_summary.sort_values(by="sentiment", ascending=False)
    top_sentiment_asins = sentiment_summary.head(5)

    sentiment_dist = df[df["asin"].isin(top_sentiment_asins["asin"])]
    sentiment_dist = (
        sentiment_dist.groupby(["asin", "sentiment_label"]).size().unstack(fill_value=0)
    )

    fig, axes = plt.subplots(1, len(top_sentiment_asins), figsize=(6 * len(top_sentiment_asins), 6))
    if len(top_sentiment_asins) == 1:
        axes = [axes]

    title_map = _asin_title_map(session)
    for ax, asin in zip(axes, top_sentiment_asins["asin"]):
        sizes = sentiment_dist.loc[asin].values
        labels = sentiment_dist.columns.tolist()
        colors = ["mediumseagreen", "gold", "tomato"]
        ax.pie(sizes, labels=labels, autopct="%1.1f%%", colors=colors, startangle=140)
        ax.set_title(_short_label(asin, title_map), fontsize=12)

    plt.suptitle("Sentiment Composition for Top 5 ASINs (>=10 reviews)", fontsize=16)
    plt.tight_layout(rect=[0, 0.03, 1, 0.95])
    legend_elems = [
        Patch(facecolor="mediumseagreen", label="positive"),
        Patch(facecolor="gold", label="neutral"),
        Patch(facecolor="tomato", label="negative"),
    ]
    plt.legend(handles=legend_elems, loc="upper right")
    plt.show()

    # --- Pie charts for top 5 ASINs with most flags ---
    asin_flag_counts = df[df["auth_flag"] != ""].copy()
    asin_flag_counts["auth_flag_list"] = asin_flag_counts["auth_flag"].str.split(",")
    exploded = asin_flag_counts.explode("auth_flag_list")
    print(f"[DEBUG] ASINs with flags: {exploded['asin'].nunique()}")

    top_asins = exploded.groupby("asin").size().sort_values(ascending=False).head(5).index
    flag_colors = {
        "short": "steelblue",
        "long": "orange",
        "high_volume": "red",
        "duplicate": "purple",
        "hyperactive_author": "green",
    }

    fig, axes = plt.subplots(1, len(top_asins), figsize=(6 * len(top_asins), 6))
    if len(top_asins) == 1:
        axes = [axes]  # Ensure iterable if only one ASIN

    title_map = _asin_title_map(session)
    for ax, asin in zip(axes, top_asins):
        asin_flags = exploded[exploded["asin"] == asin]["auth_flag_list"].value_counts()
        labels = asin_flags.index
        sizes = asin_flags.values
        colors = [flag_colors.get(label, "gray") for label in labels]

        ax.pie(sizes, labels=labels, autopct="%1.1f%%", colors=colors, startangle=140)
        total_flags = asin_flags.sum()
        ax.set_title(f"{_short_label(asin, title_map)} ({total_flags} flags)", fontsize=12)

    plt.suptitle("Flag Composition for Top 5 ASINs", fontsize=16)
    plt.tight_layout(rect=[0, 0.03, 1, 0.95])
    legend_elems = [Patch(facecolor=c, label=k) for k, c in flag_colors.items()]
    plt.legend(handles=legend_elems, loc="upper right")
    plt.show()

    # --- Comparison summary ---
    nps_asins = set(top_asins_nps["asin"])
    sentiment_asins = set(top_sentiment_asins["asin"])

    print(f"\n[📊] Shared ASINs in Top-5 NPS & Sentiment: {nps_asins & sentiment_asins}")
    print(f"[📊] NPS-only Top: {nps_asins - sentiment_asins}")
    print(f"[📊] Sentiment-only Top: {sentiment_asins - nps_asins}")


def flag_hyperactive_reviewers(df: pd.DataFrame, threshold_per_day: int = 3) -> pd.Series:
    """
    Flags reviews written by authors who post more than `threshold_per_day` reviews in a day.
    Returns a Series with same index as df, containing 'hyperactive_author' where applicable.
    """
    if "review_author" not in df.columns or "review_date" not in df.columns:
        print("[!] Missing 'review_author' or 'review_date' in dataset.")
        return pd.Series([""] * len(df), index=df.index)

    df["review_date"] = pd.to_datetime(df["review_date"], errors="coerce")
    counts = df.groupby(["review_author", "review_date"]).size()
    active_pairs = counts[counts > threshold_per_day].index

    return df.apply(
        lambda row: (
            "hyperactive_author"
            if (row["review_author"], row["review_date"]) in active_pairs
            else ""
        ),
        axis=1,
    )


def explore_flagged_reviews(session: SessionState):
    """Interactive view of flagged reviews (auth_flag) for the loaded session."""
    if getattr(session, "df_reviews", None) is None:
        session.load_reviews_and_snapshot()
    df = session.df_reviews
    if df is None or df.empty:
        print("[!] No reviews loaded for this collection.")
        return
    if "auth_flag" not in df.columns:
        print("[!] No 'auth_flag' column found in reviews.")
        return

    print(f"\n[📂] Reviewing flagged reviews for: {session.collection_id}")
    all_flags = df["auth_flag"].str.split(",", expand=True).stack().value_counts()
    if all_flags.empty:
        print("[i] No flags present.")
        return
    print("Available flags and counts:")
    for flag, count in all_flags.items():
        print(f" - {flag}: {count}")

    flag_filter = input("Enter flag to filter by (or press Enter to view all): ").strip()
    if flag_filter:
        filtered = df[df["auth_flag"].str.contains(flag_filter, na=False)]
        print(f"\nShowing {len(filtered)} reviews with flag '{flag_filter}':")
    else:
        filtered = df[df["auth_flag"].astype(str) != ""]
        print(f"\nShowing all {len(filtered)} flagged reviews:")

    for _, row in filtered.iterrows():
        print(f"\nASIN: {row.get('asin', '')}")
        print(f"Date: {row.get('review_date', '')}")
        print(f"Flags: {row.get('auth_flag', '')}")
        print(f"Review: {str(row.get('review_text', ''))[:300]}...")


# --- Wrapper function as requested ---
def detect_suspicious_reviews(session):
    try:
        if not callable(analyze_review_authenticity):
            raise TypeError
        analyze_review_authenticity(session)
    except Exception as e:
        print(f"[ERROR] Failed to call 'analyze_review_authenticity': {e}")


def compute_nps_per_asin(df_reviews: pd.DataFrame) -> pd.DataFrame:
    """
    Compute Net Promoter Score (NPS) per ASIN.
    NPS = %Promoters (5 stars) - %Detractors (1-3 stars)
    """
    if "rating" not in df_reviews.columns or "asin" not in df_reviews.columns:
        print("[!] Missing required columns in reviews dataset.")
        return pd.DataFrame()

    df = df_reviews.copy()
    df = df[df["rating"].notnull()]
    df = df[df["rating"].apply(lambda x: isinstance(x, (int, float)))]

    def classify_nps_group(rating):
        if rating == 5:
            return "promoter"
        elif rating == 4:
            return "passive"
        elif 1 <= rating <= 3:
            return "detractor"
        else:
            return "unknown"

    df["nps_group"] = df["rating"].apply(classify_nps_group)
    summary = df.groupby("asin")["nps_group"].value_counts().unstack(fill_value=0)

    summary["n_reviews"] = summary.sum(axis=1)
    summary["promoter_pct"] = (summary.get("promoter", 0) / summary["n_reviews"]) * 100
    summary["detractor_pct"] = (summary.get("detractor", 0) / summary["n_reviews"]) * 100
    summary["passive_pct"] = (summary.get("passive", 0) / summary["n_reviews"]) * 100
    summary["nps"] = summary["promoter_pct"] - summary["detractor_pct"]

    result = summary[
        ["n_reviews", "promoter_pct", "passive_pct", "detractor_pct", "nps"]
    ].reset_index()
    result = result.sort_values(by="nps", ascending=False)
    result = result[result["n_reviews"] >= 10]

    return result


def compute_sentiment(df: pd.DataFrame) -> pd.DataFrame:
    df["sentiment"] = (
        df["review_text"]
        .astype(str)
        .apply(lambda x: round(TextBlob(x).sentiment.polarity, 3) if x.strip() else 0.0)
    )
    return df
