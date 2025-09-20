from actions.asin_search import run_asin_search as _run
from core.session_state import SessionState


def run_asin_search(session: SessionState):
    """Wrapper to the actual flow in actions/asin_search.py (keyword→categories→ASIN→save)."""
    return _run(session)
