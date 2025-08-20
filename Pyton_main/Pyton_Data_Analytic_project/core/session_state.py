# core/session_state.py

from pathlib import Path
import pandas as pd
from typing import Optional


class SessionState:
    def __init__(self):
        self.collection_id: Optional[str] = None
        self.collection_path: Optional[Path] = None
        self.df_asin: Optional[pd.DataFrame] = None
        self.marketplace: str = "US"

    def is_ready_for_reviews(self) -> bool:
        return self.df_asin is not None and not self.df_asin.empty

    def is_ready_for_snapshots(self) -> bool:
        return self.collection_path is not None and self.is_ready_for_reviews()

    def reset(self):
        self.__init__()


# Singleton-style instance for global use
SESSION = SessionState()