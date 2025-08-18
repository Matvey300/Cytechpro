# All comments in English.

from pathlib import Path
from datetime import datetime
import pandas as pd
import re

def now_ts_folder() -> str:
    return datetime.now().strftime("%Y-%m-%d-%H%M%S")

def new_out_dir(root: Path) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    d = root / now_ts_folder()
    d.mkdir(parents=True, exist_ok=True)
    return d

def ensure_dir(d: Path) -> None:
    d.mkdir(parents=True, exist_ok=True)

def write_csv(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False, encoding='utf-8-sig')

def append_csv_with_dedupe(path: Path, df_new: pd.DataFrame, key_fn) -> None:
    if path.exists():
        df_old = pd.read_csv(path)
        combined = pd.concat([df_old, df_new], ignore_index=True)
    else:
        combined = df_new.copy()
    keys = combined.apply(key_fn, axis=1)
    combined = combined[~keys.duplicated(keep='first')].reset_index(drop=True)
    combined.to_csv(path, index=False, encoding='utf-8-sig')

def append_csv_with_upsert_keys(path: Path, df_new: pd.DataFrame, keys: list[str]) -> None:
    """Upsert by keys list (e.g., ['asin','date'])."""
    if path.exists():
        df_old = pd.read_csv(path)
        combined = pd.concat([df_old, df_new], ignore_index=True)
    else:
        combined = df_new.copy()
    combined['__key__'] = combined[keys].astype(str).agg('|'.join, axis=1)
    combined = combined.drop_duplicates(subset=['__key__'], keep='last').drop(columns='__key__')
    combined.to_csv(path, index=False, encoding='utf-8-sig')

def slugify(text: str, max_len: int = 40) -> str:
    """Make a filesystem-friendly slug (ASCII-ish) from any text."""
    text = str(text or "").strip()
    text = re.sub(r"[^A-Za-z0-9]+", "_", text)
    text = re.sub(r"_+", "_", text).strip("_")
    return text[:max_len] if text else "collection"

def today_ymd() -> str:
    return datetime.now().strftime("%Y%m%d")

def new_out_dir_for_collection(root: Path, collection_id: str) -> Path:
    """Create Out/<collection_id> directory; if exists, keep it (we append files)."""
    root.mkdir(parents=True, exist_ok=True)
    d = root / collection_id
    d.mkdir(parents=True, exist_ok=True)
    return d

def info_msg(msg: str) -> None:
    print(f"[INFO] {msg}")