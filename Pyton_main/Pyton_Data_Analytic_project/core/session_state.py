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


class SessionState:
    """Wrapper around the global SESSION dict with helper methods."""

    def __init__(self):
        self._state = SESSION

    def load_last_or_prompt(self):
        # Placeholder: logic to load last session or create new one
        print("⚠️  [Stub] load_last_or_prompt not yet implemented")

    def has_asins(self) -> bool:
        return self._state["df_asin"] is not None

    def has_reviews(self) -> bool:
        path = self._state["collection_path"]
        return path and (path / "reviews.csv").exists()

    def has_snapshots(self, min_required: int = 3) -> bool:
        path = self._state["collection_path"]
        if not path or not (path / "daily_snapshots.csv").exists():
            return False
        try:
            df = pd.read_csv(path / "daily_snapshots.csv")
            return df["asin"].nunique() > 0 and df["date"].nunique() >= min_required
        except Exception:
            return False

    def list_saved_collections(self):
        print("⚠️  [Stub] list_saved_collections not yet implemented")

    @property
    def collection_id(self) -> Optional[str]:
        return self._state["collection_id"]

    @collection_id.setter
    def collection_id(self, value: str):
        self._state["collection_id"] = value

    @property
    def collection_path(self) -> Optional[Path]:
        return self._state["collection_path"]

    @collection_path.setter
    def collection_path(self, value: Path):
        self._state["collection_path"] = value

    @property
    def df_asin(self) -> Optional[pd.DataFrame]:
        return self._state["df_asin"]

    @df_asin.setter
    def df_asin(self, value: pd.DataFrame):
        self._state["df_asin"] = value
