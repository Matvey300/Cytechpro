# storage/io_utils.py
"""
Utility functions for saving and loading collections and review data.
All file I/O helpers live here.
"""

import re
from datetime import datetime
from pathlib import Path

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


def append_csv_with_dedupe(path: Path, df_new: pd.DataFrame, key_fn) -> None:
    """
    Append rows to CSV and drop duplicates using a custom row-level key function.
    - path: target CSV path
    - df_new: new rows as DataFrame
    - key_fn: callable(row) -> str, used to compute unique keys
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        try:
            df_old = pd.read_csv(path)
        except Exception:
            df_old = pd.DataFrame()
        combined = pd.concat([df_old, df_new], ignore_index=True)
    else:
        combined = df_new.copy()

    # Build unique keys for all rows
    keys = combined.apply(key_fn, axis=1)
    combined = combined.loc[~keys.duplicated(keep="first")].reset_index(drop=True)
    combined.to_csv(path, index=False, encoding="utf-8-sig")


def append_csv_with_upsert_keys(path: Path, df_new: pd.DataFrame, keys: list[str]) -> None:
    """
    Upsert rows into CSV by composite keys (e.g., ['asin','date']).
    - If a row with the same key exists, the NEW row overwrites it.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        try:
            df_old = pd.read_csv(path)
        except Exception:
            df_old = pd.DataFrame()
        combined = pd.concat([df_old, df_new], ignore_index=True)
    else:
        combined = df_new.copy()

    # Build composite key column
    combined["__key__"] = combined[keys].astype(str).agg("|".join, axis=1)
    combined = combined.drop_duplicates(subset=["__key__"], keep="last").drop(columns="__key__")
    combined.to_csv(path, index=False, encoding="utf-8-sig")
