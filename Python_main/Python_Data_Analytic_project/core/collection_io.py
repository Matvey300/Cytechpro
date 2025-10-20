"""
# === Module Header ===
# 📁 Module: core/collection_io.py
# 📅 Last Reviewed: 2025-10-15
# 🔧 Status: 🟢 Stable
# 👤 Owner: MatveyB
# 📝 Summary: IO helpers for collections: save/load snapshots, reviews, and folders.
# =====================
"""

import re
from pathlib import Path

import pandas as pd


def _append_and_dedup(
    new_df: pd.DataFrame, file_path: Path, key_columns: list[str]
) -> pd.DataFrame:
    """Helper to append new_df to file_path and deduplicate using key_columns."""
    if file_path.exists():
        try:
            old_df = pd.read_csv(file_path)
        except Exception:
            old_df = pd.DataFrame(columns=new_df.columns)
        combined = pd.concat([old_df, new_df], ignore_index=True)
    else:
        combined = new_df

    if all(col in combined.columns for col in key_columns):
        combined = combined.drop_duplicates(subset=key_columns, keep="first")
    else:
        combined = combined.drop_duplicates(keep="first")

    return combined


# Root for collections DATA directory (new layout)
COLLECTIONS_DIR = Path(__file__).resolve().parents[1] / "DATA"

# New-style directory regex: YYYYMMDD_<collection_id>_createdYYYYMMDD
_NEW_DIR_RE = r"^(?P<snap>\d{8})_(?P<cid>.+)_created(?P<created>\d{8})$"


def _today_yyyymmdd() -> str:
    import datetime

    return datetime.datetime.now().strftime("%Y%m%d")


def make_collection_dirname(last_snapshot_date: str, collection_id: str, created_date: str) -> str:
    return f"{last_snapshot_date}_{collection_id}_created{created_date}"


def parse_collection_dirname(dirname: str) -> dict:
    m = re.match(_NEW_DIR_RE, dirname)
    if not m:
        raise ValueError(f"Invalid collection dirname: {dirname}")
    return m.groupdict()


def collection_dir(base: Path, last_snapshot: str, collection_id: str, created: str) -> Path:
    return base / make_collection_dirname(last_snapshot, collection_id, created)


def collection_csv(dir_path: Path) -> Path:
    return dir_path / "collection.csv"


def snapshot_csv(dir_path: Path, date: str | None = None) -> Path:
    """Return path to the single, cumulative snapshot file (date ignored)."""
    return dir_path / "snapshot.csv"


def reviews_csv(dir_path: Path, date: str | None = None) -> Path:
    """Return path to the single, cumulative reviews file (date ignored)."""
    return dir_path / "reviews.csv"


def save_snapshot(session, df_snapshot: pd.DataFrame, overwrite_today: bool = True):
    """Append snapshot rows into snapshot.csv (single file). Rename folder if date changes.
    If the file doesn't exist yet, it will be created. A `captured_at` timestamp column is ensured.
    Deduplication key: (asin, captured_at) when both columns exist; otherwise full-row dedup.
    """
    # Parameter kept for backward compatibility; logic always overwrites per-day rows via dedup.
    # Reference to appease linters since behavior is intentional.
    _ = overwrite_today
    snap_date = _today_yyyymmdd()
    cur_dir = getattr(session, "collection_path", None)
    if cur_dir is None:
        cur_dir = COLLECTIONS_DIR / getattr(session, "collection_id", "UNKNOWN_COLLECTION")
        cur_dir.mkdir(parents=True, exist_ok=True)
    out_file = snapshot_csv(cur_dir)

    # Ensure captured_at exists
    if "captured_at" not in df_snapshot.columns:
        df_snapshot = df_snapshot.copy()
        df_snapshot["captured_at"] = pd.Timestamp.now().isoformat(timespec="seconds")

    combined = _append_and_dedup(df_snapshot, out_file, ["asin", "captured_at"])

    combined.to_csv(out_file, index=False)

    # Rename collection folder if calendar date changed
    prev_snap = getattr(session, "last_snapshot_date", None)
    created_date = getattr(session, "created_date", snap_date)
    collection_id = getattr(session, "collection_id", "UNKNOWN_COLLECTION")
    if prev_snap != snap_date:
        new_dir = collection_dir(COLLECTIONS_DIR, snap_date, collection_id, created_date)
        new_dir.parent.mkdir(parents=True, exist_ok=True)
        if cur_dir.resolve() != new_dir.resolve():
            if new_dir.exists():
                raise FileExistsError(f"Target collection folder already exists: {new_dir}")
            cur_dir.rename(new_dir)
            cur_dir = new_dir
        if hasattr(session, "last_snapshot_date"):
            session.last_snapshot_date = snap_date
        if hasattr(session, "collection_path"):
            session.collection_path = cur_dir
    if hasattr(session, "latest_snapshot_file"):
        session.latest_snapshot_file = cur_dir / out_file.name
    return session


def save_reviews(
    session, df_reviews: pd.DataFrame, use_snapshot_date_by_default: bool = True
) -> Path:
    """Append review rows into reviews.csv (single file). If absent, create it.
    Ensures a `captured_at` column; performs best-effort dedup.
    Primary dedup key preference order: review_id, else (asin, review_date, rating, title, body), else full-row.
    """
    # Parameter retained for compatibility; current pipeline sets captured_at explicitly.
    _ = use_snapshot_date_by_default
    # Ensures captured_at, deduplicates reviews and appends to reviews.csv
    cur_dir = getattr(session, "collection_path", None)
    if cur_dir is None:
        cur_dir = COLLECTIONS_DIR / getattr(session, "collection_id", "UNKNOWN_COLLECTION")
        cur_dir.mkdir(parents=True, exist_ok=True)
    out_file = reviews_csv(cur_dir)

    # Ensure captured_at exists
    if "captured_at" not in df_reviews.columns:
        df_reviews = df_reviews.copy()
        df_reviews["captured_at"] = pd.Timestamp.now().isoformat(timespec="seconds")

    if "review_id" in df_reviews.columns:
        dedup_keys = ["review_id"]
    elif {"asin", "review_date", "rating"}.issubset(df_reviews.columns):
        dedup_keys = [
            c for c in ["asin", "review_date", "rating", "title", "body"] if c in df_reviews.columns
        ]
    else:
        dedup_keys = []

    combined = _append_and_dedup(df_reviews, out_file, dedup_keys)

    combined.to_csv(out_file, index=False)

    if hasattr(session, "latest_reviews_file"):
        session.latest_reviews_file = out_file
    return out_file


def list_collections() -> list[str]:
    """
    List ONLY new-format collections under COLLECTIONS_DIR:
      YYYYMMDD_<cid>_createdYYYYMMDD  (must contain collection.csv)
    Sorted by snapshot date (desc), then by collection id.
    """
    # This function lists valid new-format collection directories that contain collection.csv
    base = COLLECTIONS_DIR
    if not base.exists():
        return []
    found: list[tuple[str, str, str]] = []
    for p in base.iterdir():
        if not p.is_dir():
            continue
        m = re.match(_NEW_DIR_RE, p.name)
        if not m:
            continue
        has_collection = (p / "collection.csv").exists()
        # temporary migration aid: show folders that still have a legacy *_ASIN.csv inside
        has_legacy = any(
            child.is_file() and child.name.endswith("_ASIN.csv") for child in p.iterdir()
        )
        if not (has_collection or has_legacy):
            continue
        found.append((m.group("snap"), m.group("cid"), p.name))
    found.sort(key=lambda t: (t[0], t[1]), reverse=True)
    return [name for _snap, _cid, name in found]


def load_collection(name: str, session):
    """
    Load collection from new-format folders. If a legacy `<cid>_ASIN.csv` is present
    inside the new-format folder, rename it to `collection.csv` on first load.
    """
    # This function loads a collection from disk into the session object
    base = COLLECTIONS_DIR

    # 1) Prefer new-style folders
    candidates = []
    try:
        for p in base.iterdir():
            if p.is_dir() and re.match(_NEW_DIR_RE, p.name):
                parts = parse_collection_dirname(p.name)
                if parts.get("cid") == name:
                    candidates.append((parts.get("snap"), parts.get("created"), p))
    except FileNotFoundError:
        pass

    if candidates:
        candidates.sort(key=lambda x: x[0], reverse=True)
        _, _, dirp = candidates[0]
        csvp = collection_csv(dirp)
        # Auto-migrate single legacy file inside the new-format folder
        if not csvp.exists():
            legacy_candidate = dirp / f"{name}_ASIN.csv"
            if legacy_candidate.exists():
                legacy_candidate.rename(csvp)
                print(
                    f"[migrate] Renamed legacy file to new layout: {legacy_candidate.name} -> {csvp.name}"
                )
        if csvp.exists():
            df = pd.read_csv(csvp)
            session.collection_id = name
            session.collection_path = dirp
            session.df_asins = df
            parts = parse_collection_dirname(dirp.name)
            if hasattr(session, "created_date"):
                session.created_date = parts.get("created")
            if hasattr(session, "last_snapshot_date"):
                session.last_snapshot_date = parts.get("snap")
            return session

    raise FileNotFoundError(
        f"Collection '{name}' not found in new-format folders under {base} "
        f"(expected directories like YYYYMMDD_{name}_createdYYYYMMDD with collection.csv)"
    )


# -----------------------------
# Creation & saving (new-format only)
# -----------------------------


def _sanitize_cid(name: str) -> str:
    cid = re.sub(r"\s+", "_", name.strip())
    cid = re.sub(r"[^A-Za-z0-9_\-]+", "", cid)
    return cid or "collection"


def create_collection(session, name: str):
    """Create a new-format collection folder and initialize empty collection.csv.

    - Folder name: YYYYMMDD_<cid>_createdYYYYMMDD
    - Initializes session.collection_id/path and session.df_asins (empty with expected columns)
    """
    today = _today_yyyymmdd()
    cid = _sanitize_cid(name)
    dirp = collection_dir(COLLECTIONS_DIR, today, cid, today)
    dirp.mkdir(parents=True, exist_ok=True)

    # Initialize collection.csv with expected schema
    cols = ["asin", "title", "rating", "review_count", "country", "category_path"]
    df = pd.DataFrame(columns=cols)
    collection_csv(dirp).write_text(",".join(cols) + "\n", encoding="utf-8")

    # Update session
    session.collection_id = cid
    session.collection_path = dirp
    if hasattr(session, "df_asins"):
        session.df_asins = df
    if hasattr(session, "created_date"):
        session.created_date = today
    if hasattr(session, "last_snapshot_date"):
        session.last_snapshot_date = today
    return session


def save_collection(session, collection_id: str, df: pd.DataFrame):
    """Persist provided ASIN DataFrame into collection.csv of the given/new collection.
    If the session doesn't point to a collection with this id, creates it.
    """
    cid = _sanitize_cid(collection_id)
    if (
        getattr(session, "collection_id", None) != cid
        or getattr(session, "collection_path", None) is None
    ):
        create_collection(session, cid)

    # Ensure expected columns (add missing as empty)
    expected = ["asin", "title", "rating", "review_count", "country", "category_path"]
    for col in expected:
        if col not in df.columns:
            df[col] = None
    df = df[expected]

    out = collection_csv(session.collection_path)
    df.to_csv(out, index=False)
    if hasattr(session, "df_asins"):
        session.df_asins = df
    return out
