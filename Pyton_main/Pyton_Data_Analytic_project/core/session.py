# core/session.py

from pathlib import Path
import pandas as pd
from typing import Optional

class Session:
    """
    Holds the current working state:
    - collection ID
    - collection path
    - ASIN DataFrame
    """
    def __init__(self):
        self.collection_id: Optional[str] = None
        self.collection_path: Optional[Path] = None
        self.df_asin: Optional[pd.DataFrame] = None

    def is_active(self) -> bool:
        """Check if a session is loaded and valid."""
        return (
            self.collection_id is not None
            and self.collection_path is not None
            and self.df_asin is not None
            and not self.df_asin.empty
        )

    def reset(self):
        """Clear the current session."""
        self.collection_id = None
        self.collection_path = None
        self.df_asin = None

    def set(self, collection_id: str, collection_path: Path, df_asin: pd.DataFrame):
        """Set session values explicitly."""
        self.collection_id = collection_id
        self.collection_path = collection_path
        self.df_asin = df_asin

    def __str__(self):
        return f"Session(collection_id={self.collection_id}, ASINs={len(self.df_asin) if self.df_asin is not None else 0})"
