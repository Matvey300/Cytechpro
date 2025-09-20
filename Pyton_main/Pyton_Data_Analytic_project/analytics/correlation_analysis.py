# === Module Status ===
# 📁 Module: analytics/correlation_analysis
# 📅 Last Reviewed: 2025-09-15
# 🔧 Status: 🟢 Complete
# 👤 Owner: Matvey
# 📝 Notes:
# - print_info integrated, fallback handling implemented, module finalized.
# =====================

import os

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns
from core.session_state import print_info


def compute_correlation_matrix(daily_snapshots: pd.DataFrame, output_dir: str):
    """
    Compute and plot a correlation matrix between numeric features in a cumulative snapshot DataFrame.

    Parameters:
        daily_snapshots (pd.DataFrame): DataFrame containing snapshot data with 'captured_at' timestamps.
        output_dir (str): Directory to save the output correlation matrix PNG.

    Output:
        correlation_matrix.csv and correlation_matrix.png
    """
    if len(daily_snapshots) < 10:
        print_info("[WARN] Not enough rows to perform correlation analysis (min 10 required).")
        return

    # Ensure captured_at is datetime for grouping
    if "captured_at" in daily_snapshots.columns:
        daily_snapshots["captured_at"] = pd.to_datetime(
            daily_snapshots["captured_at"], errors="coerce"
        )

    # Filter only numeric columns relevant to analysis
    columns_to_check = ["avg_rating", "review_count", "price", "bsr"]

    # Aggregate by day (mean values per asin/day or global average per day)
    if "captured_at" in daily_snapshots.columns:
        daily_snapshots["date"] = daily_snapshots["captured_at"].dt.date
        grouped = daily_snapshots.groupby("date")[columns_to_check].mean().reset_index()
    else:
        grouped = daily_snapshots[columns_to_check]
    numeric_df = grouped.dropna()

    if numeric_df.empty or len(numeric_df) < 10:
        print_info("[WARN] Not enough valid numeric data to compute correlation matrix.")
        return

    # Compute correlation
    corr_matrix = numeric_df.corr()

    # Save matrix as CSV
    csv_path = os.path.join(output_dir, "correlation_matrix.csv")
    try:
        corr_matrix.to_csv(csv_path)
        print_info(f"[INFO] Correlation matrix saved to {csv_path}")
    except Exception as e:
        print_info(f"[ERROR] Failed to save correlation matrix CSV: {e}")

    # Plot heatmap
    plt.figure(figsize=(8, 6))
    sns.heatmap(corr_matrix, annot=True, fmt=".2f", cmap="coolwarm", square=True)
    plt.title("Correlation Matrix (Rating / Price / Review Count / BSR)")
    plt.tight_layout()

    png_path = os.path.join(output_dir, "correlation_matrix.png")
    try:
        plt.savefig(png_path)
        print_info(f"[INFO] Correlation heatmap saved to {png_path}")
    except Exception as e:
        print_info(f"[ERROR] Failed to save correlation heatmap PNG: {e}")
    plt.close()
