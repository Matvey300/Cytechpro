# actions/plots.py

from analytics.review_dynamics import plot_review_dynamics
from core.session_state import SessionState

def run_plotting(session: SessionState):
    """Run plotting for review and sentiment dynamics."""
    print("\n📊 Plotting review dynamics...")
    plot_review_dynamics(session.collection_id, data_dir="collections")
    print("✅ Done.")