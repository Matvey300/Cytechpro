# analytics/review_dynamics.py

import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import os

# -*- coding: utf-8 -*-
def plot_review_dynamics(df_snapshot: pd.DataFrame, collection_id: str, data_dir: str = "collections"):
    """
    Plots dynamics of rating, review count, price, and sentiment for a given ASIN collection.

    Parameters:
        df_snapshot (pd.DataFrame): DataFrame containing snapshot data
        collection_id (str): ID of the ASIN collection
        data_dir (str): Base directory for data (default = "Out")

    Output:
        Saves line plots to Out/<collection_id>/plots/
    """
    sentiment_file = os.path.join(data_dir, collection_id, "review_sentiments.csv")
    output_dir = os.path.join(data_dir, collection_id, "plots")
    os.makedirs(output_dir, exist_ok=True)

    asin_list = df_snapshot['asin'].unique()

    # Attempt to load sentiment data if available
    try:
        df_sentiments = pd.read_csv(sentiment_file, parse_dates=["date"])
        has_sentiment = True
    except FileNotFoundError:
        print("[INFO] No sentiment data available.")
        has_sentiment = False

    for asin in asin_list:
        # Skip ASINs with insufficient data
        df_asin = df_snapshot[df_snapshot['asin'] == asin].sort_values("date")

        if len(df_asin) < 2:
            continue

        plt.figure(figsize=(10, 6))
        plt.plot(df_asin["date"], df_asin["avg_rating"], marker="o", label="Average Rating")
        plt.plot(df_asin["date"], df_asin["review_count"], marker="s", label="Review Count")
        if "price" in df_asin.columns:
            plt.plot(df_asin["date"], df_asin["price"], marker="^", label="Price")

        # Check if sentiment data is available
        if has_sentiment:
            df_sent_asin = df_sentiments[df_sentiments["asin"] == asin].sort_values("date")
            if not df_sent_asin.empty:
                plt.plot(df_sent_asin["date"], df_sent_asin["sentiment_score"], marker="x", label="Sentiment")

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