# actions/snapshots.py
# Daily snapshot runner for price, rating, review count

from analytics.daily import take_daily_snapshot
from core.session_state import SessionState

def run_daily_screening(session: SessionState):
    """Trigger snapshot collection for current ASIN collection."""
    print("\n📸 Taking daily snapshot...")
    take_daily_snapshot(session)
    print("✅ Snapshot completed.")