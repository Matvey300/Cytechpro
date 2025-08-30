# actions/plots.py

import pandas as pd

from analytics.review_dynamics import plot_review_dynamics
from core.session_state import SessionState


def run_plotting(session: SessionState):
    """Run plotting for review and sentiment dynamics."""
    if session.collection_id:
        print(f"[📁] Active collection: {session.collection_id}")
    else:
        print("[📁] No collection loaded.")
        session.list_available_collections()
        idx = input("Select collection number (or press Enter to cancel): ").strip()
        if not idx.isdigit():
            print("[✖] Operation cancelled.")
            return
        collection_names = session.list_available_collections()
        if int(idx) >= len(collection_names):
            print("[✖] Invalid selection.")
            return
        selected_id = collection_names[int(idx)]
        session.load_collection(selected_id)
        session.load_reviews_and_snapshot()
    print("\n📊 Plotting review dynamics...")

    if session.df_reviews is None or session.df_reviews.empty:
        print("[!] No review data available for plotting.")
        return

    plot_review_dynamics(
        df_asin=session.df_asin,
        df_reviews=session.df_reviews,
        collection_id=session.collection_id,
        data_dir=session.collection_path,
    )
    print("✅ Done.")
