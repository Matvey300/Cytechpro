# actions/snapshots.py
# Daily snapshot runner for price, rating, review count

from analytics.daily import run_daily_screening as run_snapshot_logic
from core.session_state import SessionState


def run_daily_screening(session: SessionState):
    """Trigger snapshot collection for current ASIN collection."""
    print("\n📸 Taking daily snapshot...")
    run_snapshot_logic(session.df_asin, session.collection_path)
    print("✅ Snapshot completed.")
