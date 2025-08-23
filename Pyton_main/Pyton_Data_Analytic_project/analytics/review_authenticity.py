import pandas as pd
from core.collection_io import load_collection

def main_menu():
    print("1. Option One")
    print("2. Option Two")
    print("3. Option Three")
    print("4. Option Four")
    print("5. Option Five")
    print("6. Option Six")
    print("7. Analyze Review Authenticity (Trustworthiness)")
    print("8. View flagged reviews (authcheck)")

def main():
    while True:
        main_menu()
        choice = input("Enter your choice: ").strip()

        if choice == "1":
            # handle option 1
            pass
        elif choice == "2":
            # handle option 2
            pass
        elif choice == "3":
            # handle option 3
            pass
        elif choice == "4":
            # handle option 4
            pass
        elif choice == "5":
            # handle option 5
            pass
        elif choice == "6":
            # handle option 6
            pass
        elif choice == "7":
            from analytics.review_authenticity import analyze_review_authenticity
            from core.collection_io import list_collections
            print("\nAvailable collections:")
            collections = list_collections()
            for i, name in enumerate(collections, 1):
                print(f"{i}) {name}")
            selected = input("Select collection number: ").strip()
            try:
                index = int(selected) - 1
                if 0 <= index < len(collections):
                    collection_id = collections[index]
                    analyze_review_authenticity(collection_id)
                else:
                    print("[!] Invalid selection.")
            except ValueError:
                print("[!] Invalid input.")
        elif choice == "8":
            from core.collection_io import list_collections, load_collection
            print("\nAvailable flagged collections:")
            collections = [c for c in list_collections() if c.startswith("authcheck__") and c.endswith("__reviews.csv")]
            if not collections:
                print("[!] No flagged collections found.")
                continue
            for i, name in enumerate(collections, 1):
                print(f"{i}) {name}")
            selected = input("Select collection number: ").strip()
            try:
                index = int(selected) - 1
                if 0 <= index < len(collections):
                    collection_id = collections[index]
                    explore_flagged_reviews(collection_id)
                else:
                    print("[!] Invalid selection.")
            except ValueError:
                print("[!] Invalid input.")
        elif choice.lower() in ("q", "quit", "exit"):
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
    from core.collection_io import save_collection

    import matplotlib.pyplot as plt
    import seaborn as sns

    df = session.df_reviews
    if df is None or df.empty:
        print("[!] No review data found in session.")
        return

    collection_id = session.collection_id
    print(f"\n[🔍] Authenticity analysis for collection: {collection_id}")

    # Step 1: Length-based heuristics
    df["text_length"] = df["review_text"].astype(str).apply(len)
    too_short = df["text_length"] < 20
    too_long = df["text_length"] > 1000

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

    # --- Pie charts for top 5 ASINs with most flags ---
    asin_flag_counts = df[df["auth_flag"] != ""].copy()
    asin_flag_counts["auth_flag_list"] = asin_flag_counts["auth_flag"].str.split(",")
    exploded = asin_flag_counts.explode("auth_flag_list")

    top_asins = exploded["asin"].value_counts().nlargest(5).index
    fig, axes = plt.subplots(1, len(top_asins), figsize=(5 * len(top_asins), 5))

    flag_colors = {
        "short": "steelblue",
        "long": "orange",
        "high_volume": "red",
        "duplicate": "purple",
        "hyperactive_author": "green"
    }

    for ax, asin in zip(axes, top_asins):
        asin_flags = exploded[exploded["asin"] == asin]["auth_flag_list"].value_counts()
        labels = asin_flags.index
        sizes = asin_flags.values
        colors = [flag_colors.get(label, "gray") for label in labels]

        ax.pie(sizes, labels=labels, autopct="%1.1f%%", colors=colors, startangle=140)
        ax.set_title(f"ASIN: {asin}", fontsize=10)

    plt.suptitle("Flag Composition for Top 5 ASINs", fontsize=14)
    plt.tight_layout()
    plt.show()

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
        lambda row: "hyperactive_author"
        if (row["review_author"], row["review_date"]) in active_pairs
        else "",
        axis=1
    )

def explore_flagged_reviews(collection_id):
    """
    Позволяет пользователю просмотреть отзывы с флагами и отфильтровать их по типу.
    """
    df = load_collection(collection_id)
    if "auth_flag" not in df.columns:
        print("[!] No 'auth_flag' column found in dataset.")
        return

    print(f"\n[📂] Reviewing flagged collection: {collection_id}")
    all_flags = df["auth_flag"].str.split(",", expand=True).stack().value_counts()
    print("Available flags and counts:")
    for flag, count in all_flags.items():
        print(f" - {flag}: {count}")

    flag_filter = input("Enter flag to filter by (or press Enter to view all): ").strip()
    if flag_filter:
        filtered = df[df["auth_flag"].str.contains(flag_filter)]
        print(f"\nShowing {len(filtered)} reviews with flag '{flag_filter}':")
    else:
        filtered = df[df["auth_flag"] != ""]
        print(f"\nShowing all {len(filtered)} flagged reviews:")

    for i, row in filtered.iterrows():
        print(f"\nASIN: {row.get('asin', '')}")
        print(f"Date: {row.get('review_date', '')}")
        print(f"Flags: {row['auth_flag']}")
        print(f"Review: {row.get('review_text', '')[:300]}...")


# --- Wrapper function as requested ---
def detect_suspicious_reviews(session):
    return analyze_review_authenticity(session)