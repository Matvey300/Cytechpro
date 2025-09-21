# analytics/review_authenticity.py

import os

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns


def analyze_review_authenticity(collection_id: str, data_dir: str = "Out"):
    """
    Flags suspicious ASINs based on review behavior patterns such as:
    - Abnormal text length distribution
    - High frequency of identical length reviews
    - Timing anomalies (burst patterns)
    - Imbalance of verified/unverified purchases
    - Sentiment-rating mismatch

    Outputs:
        - trustworthiness_scores.csv
        - trustworthiness_curve.png
    """
    base_path = os.path.join(data_dir, collection_id)
    reviews_file = os.path.join(base_path, "reviews.csv")
    sentiments_file = os.path.join(base_path, "review_sentiments.csv")
    output_path = os.path.join(base_path, "plots")
    os.makedirs(output_path, exist_ok=True)

    try:
        df = pd.read_csv(reviews_file)
    except FileNotFoundError:
        print(f"[ERROR] Reviews file not found: {reviews_file}")
        return

    try:
        sentiment_df = pd.read_csv(sentiments_file)
        has_sentiment = True
    except FileNotFoundError:
        has_sentiment = False

    results = []

    for asin in df["asin"].unique():
        df_asin = df[df["asin"] == asin]
        if len(df_asin) < 10:
            continue

        score = 0

        # Rule 1: Abnormally high % of short reviews
        short_ratio = (df_asin["review_text"].fillna("").str.len() < 20).mean()
        if short_ratio > 0.4:
            score += 1

        # Rule 2: High % of reviews with same length (possible duplication)
        lengths = df_asin["review_text"].fillna("").str.len()
        mode_len = lengths.mode().iloc[0]
        same_len_ratio = (lengths == mode_len).mean()
        if same_len_ratio > 0.3:
            score += 1

        # Rule 3: Timing bursts (many reviews in few days)
        df_asin["date"] = pd.to_datetime(df_asin["date"], errors="coerce")
        date_counts = df_asin["date"].value_counts()
        if date_counts.max() > len(df_asin) * 0.25:
            score += 1

        # Rule 4: Abnormally low % of verified purchases
        if "verified" in df_asin.columns:
            verified_ratio = df_asin["verified"].astype(str).str.lower().eq("true").mean()
            if verified_ratio < 0.5:
                score += 1

        # Rule 5: Sentiment mismatch (if sentiment available)
        if has_sentiment:
            df_sent = sentiment_df[sentiment_df["asin"] == asin]
            merged = df_sent.merge(df_asin[["review_id", "rating"]], on="review_id", how="inner")
            if not merged.empty:
                merged["diff"] = abs(merged["sentiment_score"] - merged["rating"])
                mismatch_ratio = (merged["diff"] > 2).mean()
                if mismatch_ratio > 0.3:
                    score += 1

        results.append({"asin": asin, "suspicion_score": score})

    df_score = pd.DataFrame(results)
    df_score.to_csv(os.path.join(base_path, "trustworthiness_scores.csv"), index=False)

    # Visualize
    plt.figure(figsize=(10, 6))
    sns.barplot(
        data=df_score.sort_values("suspicion_score", ascending=False),
        x="asin",
        y="suspicion_score",
        palette="Reds_d",
    )
    plt.title("Review Authenticity Risk Score (0 = High Trust, 5 = Highly Suspicious)")
    plt.ylabel("Suspicion Score")
    plt.xticks(rotation=45, ha="right")
    plt.tight_layout()

    out_path = os.path.join(output_path, "trustworthiness_curve.png")
    plt.savefig(out_path)
    plt.close()

    print(f"[INFO] Trustworthiness analysis completed. Plot saved to: {out_path}")
