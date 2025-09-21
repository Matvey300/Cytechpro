# analytics/reaction_pulse.py

# === Module Status ===
# 📁 Module: analytics/reaction_pulse
# 📅 Last Reviewed: 2025-09-15
# 🔧 Status: 🟠 Under Refactor
# 👤 Owner: Matvey
# 📝 Notes:
# - Replace print with print_info
# - Standardize fallback/error outputs
# - Consider extracting plotting logic
# =====================

# analytics/reaction_pulse.py

import os

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns
from core.session_state import print_info
from textblob import TextBlob


def detect_review_spikes(
    collection_id: str, data_dir: str = "Out", min_spike_multiplier: float = 3.0
):
    """
    Identifies ASINs with sharp review activity bursts (sudden spikes).

    Parameters:
        - min_spike_multiplier: threshold multiplier over median daily volume to be considered a spike

    Outputs:
        - review_spikes.csv
        - plots/review_spikes_curve.png
    """
    base_path = os.path.join(data_dir, collection_id)
    reviews_file = os.path.join(base_path, "reviews.csv")
    output_dir = os.path.join(base_path, "plots")
    os.makedirs(output_dir, exist_ok=True)

    try:
        df = pd.read_csv(reviews_file)
    except FileNotFoundError:
        print_info(f"[ERROR] Reviews file not found: {reviews_file}")
        return

    # Use captured_at if available
    if "captured_at" in df.columns:
        df["captured_at"] = pd.to_datetime(df["captured_at"], errors="coerce")
        df = df.dropna(subset=["captured_at"])
        df["date"] = df["captured_at"].dt.date
    elif "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
        df = df.dropna(subset=["date"])
    else:
        print_info("[ERROR] No captured_at or date column available in reviews.csv")
        return

    result_rows = []
    spike_plot_data = []

    for asin in df["asin"].unique():
        df_asin = df[df["asin"] == asin]
        daily_counts = df_asin.groupby("date").size().reset_index(name="review_count")

        if len(daily_counts) < 10:
            continue  # Not enough data to evaluate

        median_reviews = daily_counts["review_count"].median()
        spike_threshold = median_reviews * min_spike_multiplier

        spikes = daily_counts[daily_counts["review_count"] > spike_threshold]

        for _, row in spikes.iterrows():
            result_rows.append(
                {
                    "asin": asin,
                    "date": row["date"],
                    "review_count": row["review_count"],
                    "median_baseline": median_reviews,
                    "multiplier": (
                        row["review_count"] / median_reviews if median_reviews > 0 else None
                    ),
                }
            )

        if not spikes.empty:
            daily_counts["is_spike"] = daily_counts["review_count"] > spike_threshold
            daily_counts["asin"] = asin
            spike_plot_data.append(daily_counts)

    # Save CSV of spikes
    df_spikes = pd.DataFrame(result_rows)
    df_spikes.to_csv(os.path.join(base_path, "review_spikes.csv"), index=False)

    # Plot if any spikes found
    if spike_plot_data:
        all_data = pd.concat(spike_plot_data)
        plt.figure(figsize=(12, 6))
        sns.lineplot(data=all_data, x="date", y="review_count", hue="asin", alpha=0.5)
        spike_points = all_data[all_data["is_spike"]]
        plt.scatter(
            spike_points["date"], spike_points["review_count"], color="red", s=50, label="Spike"
        )
        plt.title("Detected Review Activity Spikes")
        plt.xlabel("Date")
        plt.ylabel("Review Count")
        plt.legend()
        plt.tight_layout()
        plt.savefig(os.path.join(output_dir, "review_spikes_curve.png"))
        plt.close()
        print_info("[INFO] Spike analysis complete. Plot and spike CSV saved.")
    else:
        print_info("[INFO] No spikes detected across ASINs.")


def run_sentiment_analysis(df_reviews):
    def compute_sentiment(text):
        try:
            return TextBlob(str(text)).sentiment.polarity
        except Exception as e:
            print_info(f"[!] Sentiment analysis error: {e}")
            return 0.0

    if "review_text" not in df_reviews.columns:
        print_info("[!] Missing 'review_text' column. Cannot compute sentiment.")
        return df_reviews

    print_info("[DEBUG] Количество отзывов по ASIN (до анализа):")
    print_info(df_reviews["asin"].value_counts())

    df_reviews["sentiment"] = df_reviews["review_text"].apply(compute_sentiment)
    print_info(f"[+] Sentiment scores computed for {len(df_reviews)} reviews.")
    print_info("[DEBUG] Пропуски по sentiment:", df_reviews["sentiment"].isna().sum())
    print_info("[DEBUG] Примеры значений sentiment:")
    print_info(df_reviews["sentiment"].describe())
    return df_reviews
