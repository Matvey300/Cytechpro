# analytics/review_dynamics.py

import os

import matplotlib.pyplot as plt
import pandas as pd


def plot_review_dynamics(collection_id: str, data_dir: str = "Out"):
    """
    Plots dynamics of rating, review count, price, and sentiment for a given ASIN collection.

    Parameters:
        collection_id (str): ID of the ASIN collection
        data_dir (str): Base directory for data (default = "Out")

    Outputs:
        Saves line plots to Out/<collection_id>/plots/
    """
    base_path = os.path.join(data_dir, collection_id)
    snapshots_file = os.path.join(base_path, "daily_snapshots.csv")
    sentiment_file = os.path.join(base_path, "review_sentiments.csv")
    output_dir = os.path.join(base_path, "plots")
    os.makedirs(output_dir, exist_ok=True)

    try:
        df_snapshots = pd.read_csv(snapshots_file, parse_dates=["date"])
    except FileNotFoundError:
        print(f"[ERROR] File not found: {snapshots_file}")
        return

    if df_snapshots.empty:
        print("[WARN] No snapshot data found.")
        return

    asin_list = df_snapshots["asin"].unique()

    # Load sentiment data if available
    try:
        df_sentiments = pd.read_csv(sentiment_file, parse_dates=["date"])
        has_sentiment = True
    except FileNotFoundError:
        print("[INFO] No sentiment data available.")
        has_sentiment = False

    for asin in asin_list:
        df_asin = df_snapshots[df_snapshots["asin"] == asin].sort_values("date")

        if len(df_asin) < 2:
            continue

        plt.figure(figsize=(10, 6))
        plt.plot(df_asin["date"], df_asin["avg_rating"], marker="o", label="Average Rating")
        plt.plot(df_asin["date"], df_asin["review_count"], marker="s", label="Review Count")
        if "price" in df_asin.columns:
            plt.plot(df_asin["date"], df_asin["price"], marker="^", label="Price")

        if has_sentiment:
            df_sent_asin = df_sentiments[df_sentiments["asin"] == asin].sort_values("date")
            if not df_sent_asin.empty:
                plt.plot(
                    df_sent_asin["date"],
                    df_sent_asin["sentiment_score"],
                    marker="x",
                    label="Sentiment",
                )

        plt.title(f"ASIN: {asin} — Review Dynamics")
        plt.xlabel("Date")
        plt.ylabel("Value")
        plt.legend()
        plt.grid(True)
        plt.tight_layout()

        plot_path = os.path.join(output_dir, f"{asin}_dynamics.png")
        plt.savefig(plot_path)
        plt.close()

        print(f"[INFO] Saved dynamics plot for ASIN {asin} → {plot_path}")
