# === Module Status ===
# 📁 Module: analytics/review_dynamics
# 📅 Last Reviewed: 2025-09-15
# ✅ Status: ✅ Refactored (Complete)
# 👤 Owner: Matvey
# 📝 Notes:
# - Modularized: load_snapshot_df(), load_sentiment_df(), plot_dynamics_for_asin()
# - Logging standardized via print_info()
# - Ready for integration & testing
# =====================


import os

import matplotlib.pyplot as plt
import pandas as pd


# Helper logging function
def print_info(msg: str):
    print(f"[INFO] {msg}")


def load_snapshot_df(session):
    df = session.df_snapshot.copy()
    if "captured_at" in df.columns:
        df["captured_at"] = pd.to_datetime(df["captured_at"], errors="coerce")
        df = df.dropna(subset=["captured_at"])
        df["date"] = df["captured_at"].dt.date
    return df


def load_sentiment_df(session):
    sentiment_file = session.collection_path / "review_sentiments.csv"
    try:
        df = pd.read_csv(sentiment_file)
        if "captured_at" in df.columns:
            df["captured_at"] = pd.to_datetime(df["captured_at"], errors="coerce")
            df = df.dropna(subset=["captured_at"])
            df["date"] = df["captured_at"].dt.date
        return df
    except FileNotFoundError:
        print_info("No sentiment data available.")
        return None


def plot_dynamics_for_asin(asin, df_snapshot, df_sentiments, output_dir):
    df_asin = df_snapshot[df_snapshot["asin"] == asin].sort_values("date")
    if len(df_asin) < 2:
        return

    plt.figure(figsize=(10, 6))
    plt.plot(df_asin["date"], df_asin["avg_rating"], marker="o", label="Average Rating")
    plt.plot(df_asin["date"], df_asin["review_count"], marker="s", label="Review Count")

    if "price" in df_asin.columns:
        plt.plot(df_asin["date"], df_asin["price"], marker="^", label="Price")

    if df_sentiments is not None:
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

    plot_path = output_dir / f"{asin}_dynamics.png"
    plt.savefig(plot_path)
    plt.close()
    print_info(f"Saved dynamics plot for ASIN {asin} → {plot_path}")


# -*- coding: utf-8 -*-
def plot_review_dynamics(session):
    """
    Plots dynamics of rating, review count, price, and sentiment for a given ASIN collection.

    Parameters:
        session (SessionState): active session with df_snapshot and df_reviews loaded.

    Output:
        Saves line plots to <collection_path>/plots/
    """
    coll_dir = session.collection_path
    output_dir = coll_dir / "plots"
    os.makedirs(output_dir, exist_ok=True)
    df_snapshot = load_snapshot_df(session)

    df_sentiments = load_sentiment_df(session)
    df_sentiments is not None

    asin_list = df_snapshot["asin"].unique()

    for asin in asin_list:
        plot_dynamics_for_asin(asin, df_snapshot, df_sentiments, output_dir)
