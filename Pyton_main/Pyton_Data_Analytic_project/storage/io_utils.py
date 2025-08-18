# All comments in English.

from pathlib import Path
from datetime import datetime
import pandas as pd

def now_ts_folder() -> str:
    """Return timestamp string suitable for folder names."""
    return datetime.now().strftime("%Y-%m-%d-%H%M%S")

def new_out_dir(root: Path) -> Path:
    """Create a new Out/<timestamp>/ directory and return its Path."""
    root.mkdir(parents=True, exist_ok=True)
    ts = now_ts_folder()
    d = root / ts
    d.mkdir(parents=True, exist_ok=True)
    return d

def ensure_dir(d: Path) -> None:
    """Ensure directory exists."""
    d.mkdir(parents=True, exist_ok=True)

def write_csv(df: pd.DataFrame, path: Path) -> None:
    """Write CSV with UTF-8 BOM for Excel compatibility."""
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False, encoding='utf-8-sig')

def append_csv_with_dedupe(path: Path, df_new: pd.DataFrame, key_fn) -> None:
    """Append df_new to CSV at path with row-level dedupe using key_fn(row)->str."""
    if path.exists():
        df_old = pd.read_csv(path)
        combined = pd.concat([df_old, df_new], ignore_index=True)
    else:
        combined = df_new.copy()
    # Build keys
    keys = combined.apply(key_fn, axis=1)
    # Drop duplicates keeping the first occurrence
    combined = combined[~keys.duplicated(keep='first')].reset_index(drop=True)
    combined.to_csv(path, index=False, encoding='utf-8-sig')

def info_msg(msg: str) -> None:
    """Simple console info."""
    print(f"[INFO] {msg}")