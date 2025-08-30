# analytics/correlation_analysis.py

import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
import os

def compute_correlation_matrix(daily_snapshots: pd.DataFrame, output_dir: str):
    """
    Compute and plot a correlation matrix between numeric features in daily snapshots.
    
    Parameters:
        daily_snapshots (pd.DataFrame): DataFrame with at least 20 daily snapshots.
        output_dir (str): Directory to save the output correlation matrix PNG.
    
    Output:
        correlation_matrix.csv and correlation_matrix.png
    """
    if len(daily_snapshots) < 20:
        print("[WARN] Not enough snapshots to perform correlation analysis (min 20 required).")
        return

    # Filter only numeric columns relevant to analysis
    columns_to_check = ['avg_rating', 'review_count', 'price', 'bsr']
    numeric_df = daily_snapshots[columns_to_check].dropna()

    if numeric_df.empty or len(numeric_df) < 20:
        print("[WARN] Not enough valid numeric data to compute correlation matrix.")
        return

    # Compute correlation
    corr_matrix = numeric_df.corr()

    # Save matrix as CSV
    csv_path = os.path.join(output_dir, 'correlation_matrix.csv')
    corr_matrix.to_csv(csv_path)
    print(f"[INFO] Correlation matrix saved to {csv_path}")

    # Plot heatmap
    plt.figure(figsize=(8, 6))
    sns.heatmap(corr_matrix, annot=True, fmt=".2f", cmap='coolwarm', square=True)
    plt.title("Correlation Matrix (Rating / Price / Review Count / BSR)")
    plt.tight_layout()

    png_path = os.path.join(output_dir, 'correlation_matrix.png')
    plt.savefig(png_path)
    plt.close()
    print(f"[INFO] Correlation heatmap saved to {png_path}")