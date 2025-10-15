"""
# === Module Header ===
# 📁 Module: actions/asin_controller.py
# 📅 Last Reviewed: 2025-10-15
# 🔧 Status: 🟢 Stable
# 👤 Owner: MatveyB
# 📝 Summary: Wrapper controller for ASIN search flow.
# =====================
"""

from actions.asin_search import run_asin_search as _run
from core.session_state import SessionState


def run_asin_search(session: SessionState):
    """Wrapper to the actual flow in actions/asin_search.py (keyword→categories→ASIN→save)."""
    return _run(session)
