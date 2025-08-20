# actions/correlations.py

from analytics.correlation_analysis import analyze_review_price_bsr_correlations
from core.session_state import SessionState

def run_correlation_analysis(session: SessionState):
    """Run correlation analysis on available ASIN snapshots."""
    print("\n📊 Running correlation analysis...")
    analyze_review_price_bsr_correlations(session.collection_path)
    print("✅ Correlation analysis completed.")