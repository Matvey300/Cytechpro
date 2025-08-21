# actions/correlations.py

from analytics.correlation_analysis import compute_correlation_matrix
from core.session_state import SessionState

def run_correlation_analysis(session: SessionState):
    """Run correlation analysis on available ASIN snapshots."""
    print("\n📊 Running correlation analysis...")
    df = pd.read_csv(session.collection_path / "daily_snapshots.csv")
    compute_correlation_matrix(df, str(session.collection_path))
    print("✅ Correlation analysis completed.")