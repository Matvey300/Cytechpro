# core/session_state.py
# Global session state shared between CLI actions

from typing import Optional
from pathlib import Path
import pandas as pd

# Shared in-memory session state
SESSION = {
    "collection_id": None,       # type: Optional[str]
    "collection_path": None,     # type: Optional[Path]
    "df_asin": None,             # type: Optional[pd.DataFrame]
}

def reset_session():
    """Reset all session values to None (used during reinitialization or cleanup)."""
    for key in SESSION:
        SESSION[key] = None