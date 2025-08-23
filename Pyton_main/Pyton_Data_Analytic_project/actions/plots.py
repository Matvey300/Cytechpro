# actions/plots.py

from analytics.review_dynamics import plot_review_dynamics
from core.session_state import SessionState
import os
import pandas as pd

def run_plotting(session: SessionState):
    """Run plotting for review and sentiment dynamics."""
    print("\n📊 Plotting review dynamics...")

    collection_dir = os.path.join("collections", session.collection_id)

    if session.df_asin is None:
        asin_path = os.path.join(collection_dir, f"{session.collection_id}.csv")
        if os.path.exists(asin_path):
            session.df_asin = pd.read_csv(asin_path)
            print(f"[INFO] Loaded ASIN data from {asin_path}")
        else:
            print(f"[ERROR] ASIN file not found: {asin_path}")
            return

    if session.df_reviews is None:
        review_files = [f for f in os.listdir(collection_dir) if f.endswith("__reviews.csv")]
        if not review_files:
            print("[ERROR] No review files found in collection directory.")
            return
        elif len(review_files) == 1:
            review_file = review_files[0]
        else:
            print("Multiple review files found:")
            for idx, fname in enumerate(review_files, 1):
                print(f"{idx}) {fname}")
            choice = input("Select review file by number: ").strip()
            try:
                review_file = review_files[int(choice)-1]
            except (IndexError, ValueError):
                print("[ERROR] Invalid selection.")
                return
        review_path = os.path.join(collection_dir, review_file)
        session.df_reviews = pd.read_csv(review_path)
        print(f"[INFO] Loaded reviews from {review_path}")

    plot_review_dynamics(session.df_asin, session.df_reviews)
    print("✅ Done.")