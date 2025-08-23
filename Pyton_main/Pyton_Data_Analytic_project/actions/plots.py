# actions/plots.py

from analytics.review_dynamics import plot_review_dynamics
from core.session_state import SessionState
import os
import pandas as pd

def run_plotting(session: SessionState):
    """Run plotting for review and sentiment dynamics."""
    print(f"Current ASIN collection: {session.collection_id}")
    if not session.collection_id:
        print("[ERROR] No ASIN collection selected. Please load a collection first.")
        return
    print("\n📊 Plotting review dynamics...")

    session.load_reviews_and_snapshot()

    if session.df_asin is None or session.df_reviews is None:
        print("[ERROR] Required data not loaded.")
        return

    plot_review_dynamics(session.df_asin, session.df_reviews)
    print("✅ Done.")