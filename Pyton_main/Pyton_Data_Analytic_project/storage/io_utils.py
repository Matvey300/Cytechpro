# storage/io_utils.py
"""
Utility functions for saving and loading collections and review data.
All file I/O helpers live here.
"""

from pathlib import Path
from datetime import datetime
import re
import pandas as pd


# ---------- Helpers for naming / directories ----------

def slugify(text: str, max_len: int = 40) -> str:
    """
    Make a safe ID string from category or free text.
    Example: "Headphones & Ear-Buds" -> "Headphones_Ear_Buds"
    """
    text = str(text or "").strip()
    text = re.sub(r"[^A-Za-z0-9]+", "_", text)
    text = re.sub(r"_+", "_", text).strip("_")
    return text[:max_len] if text else "collection"


def today_ymd() -> str:
    """
    Returns today's date in YYYYMMDD format.
    """
    return datetime.now().strftime("%Y%m%d")


def new_out_dir_for_collection(root: Path, collection_id: str) -> Path:
    """
    Create (if needed) a new directory under root for given collection_id.
    """
    root.mkdir(parents=True, exist_ok=True)
    d = root / collection_id
    d.mkdir(parents=True, exist_ok=True)
    return d


# ---------- Saving & loading DataFrames ----------

def save_df_csv(df: pd.DataFrame, path: Path) -> None:
    """
    Save DataFrame to CSV with UTF-8 BOM for Excel compatibility.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False, encoding="utf-8-sig")


def load_df_csv(path: Path) -> pd.DataFrame:
    """
    Load DataFrame from CSV if file exists.
    Returns empty DataFrame if not found.
    """
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path)


# ---------- Listing saved collections ----------

def list_saved_collections(root: Path) -> list[Path]:
    """
    Return list of collection directories inside root.
    """
    if not root.exists():
        return []
    return sorted([p for p in root.iterdir() if p.is_dir()])