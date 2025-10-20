# core/session.py

from pathlib import Path
from typing import Optional

import pandas as pd


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


# --------------------------------------------------------------------
# Helpers for loading data in the new DATA/ collection structure
# --------------------------------------------------------------------


def load_asins(collection_id: str) -> pd.DataFrame:
    """Load ASIN list from <collection_id>_ASIN.csv"""
    path = Path("DATA") / collection_id / f"{collection_id}_ASIN.csv"
    if not path.exists():
        raise FileNotFoundError(f"ASIN file not found: {path}")
    return pd.read_csv(path)


def load_master_reviews(collection_id: str) -> pd.DataFrame:
    """Load master reviews (append-only) from <collection_id>__reviews.csv"""
    path = Path("DATA") / collection_id / f"{collection_id}__reviews.csv"
    if not path.exists():
        raise FileNotFoundError(f"Master reviews file not found: {path}")
    return pd.read_csv(path)


def load_latest_snapshot(collection_id: str) -> pd.DataFrame:
    """Load snapshot by reading LATEST.txt and returning that file"""
    base = Path("DATA") / collection_id
    latest_file = base / "LATEST.txt"
    if not latest_file.exists():
        raise FileNotFoundError(f"LATEST.txt not found in {base}")
    ts = latest_file.read_text().strip()
    snap_path = base / f"{ts}__{collection_id}__snapshot.csv"
    if not snap_path.exists():
        raise FileNotFoundError(f"Snapshot file not found: {snap_path}")
    return pd.read_csv(snap_path)


# --------------------------------------------------------------------
# Logging helper
# --------------------------------------------------------------------


def print_info(msg: str):
    print(f"[ℹ] {msg}")


"""
# === Module Header ===
# 📁 Module: core/session.py
# 📅 Last Reviewed: 2025-10-15
# 🔧 Status: 🟢 Stable
# 👤 Owner: MatveyB
# 📝 Summary: Session wrapper utilities and compatibility shims.
# =====================
"""
