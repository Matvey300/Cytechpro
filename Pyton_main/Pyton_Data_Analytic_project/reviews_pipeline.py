# reviews_pipeline.py
# All comments in English.

from __future__ import annotations

import json
from hashlib import sha1
from pathlib import Path
from typing import Dict, Tuple, Optional, Callable

import pandas as pd

# Import the Selenium-based collector
from amazon_review_collector import collect_reviews

# -----------------------------
# CSV & checkpoint utilities
# -----------------------------

def _atomic_write_csv(path: Path, df: pd.DataFrame) -> None:
    """Atomic write to avoid partial files on crash."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    df.to_csv(tmp, index=False)
    tmp.replace(path)

def _canon_text(s: str) -> str:
    """Normalize text for hashing: lowercase, collapse whitespace."""
    if s is None:
        return ""
    return " ".join(str(s).lower().split())

def _floor_to_minute(dt_str: str) -> str:
    """
    Floor datetime string to minutes.
    If no time present → keep date only.
    We use pandas to parse robustly; NaT falls back to original string.
    """
    if not dt_str:
        return ""
    try:
        dt = pd.to_datetime(dt_str, errors="coerce", utc=False)
        if pd.isna(dt):
            return str(dt_str)
        # floor to minute to collapse 'second-only' manipulations
        return dt.floor("T").isoformat()
    except Exception:
        return str(dt_str)

def _stable_row_key(row: pd.Series) -> str:
    """
    Dedupe only *exact* technical duplicates:
      - Primary: (asin, review_id) if review_id present and not fallback.
      - Fallback (no review_id): SHA1 over FULL timestamp + content.
    NOTE: We do NOT floor timestamps here — we preserve near-duplicates that differ by seconds.
    """
    asin = str(row.get("asin", ""))
    review_id = str(row.get("review_id", "") or "")
    if review_id and not review_id.startswith("FALLBACK-"):
        return f"{asin}|{review_id}"

    # Keep full timestamp (no minute flooring) to avoid collapsing second-level differences
    date_full = str(row.get("review_date_raw", ""))
    rating = str(row.get("rating", ""))
    title = (str(row.get("title", "")) or "").strip()
    body  = (str(row.get("body", ""))  or "").strip()
    payload = f"{asin}|{date_full}|{rating}|{title}|{body}"
    return f"{asin}|SHA1-{sha1(payload.encode('utf-8', 'ignore')).hexdigest()}"

def _tag_near_duplicates(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add analysis tags for near-duplicates without dropping them:
      - near_dup_min_bucket: date floored to minute
      - content_hash_200: SHA1 of normalized title+body (first 200 chars)
    """
    if df is None or df.empty:
        return df
    def _canon(s): return " ".join(str(s or "").lower().split())
    def _h(s):    return sha1(_canon(s)[:200].encode("utf-8", "ignore")).hexdigest()

    # safe floor-to-minute (keep original intact)
    def _floor_min_safe(s):
        try:
            dt = pd.to_datetime(s, errors="coerce", utc=False)
            return None if pd.isna(dt) else dt.floor("T").isoformat()
        except Exception:
            return None

    df = df.copy()
    df["near_dup_min_bucket"] = df["review_date_raw"].map(_floor_min_safe)
    df["content_hash_200"] = (df["title"].fillna("") + " | " + df["body"].fillna("")).map(_h)
    return df

def _append_and_dedupe(out_csv: Path, batch: pd.DataFrame) -> int:
    """
    Append batch to CSV with stable dedupe. Returns the number of NEW unique rows added.
    Safe against second-only timestamp tweaks.
    """
    if batch is None or batch.empty:
        return 0

    if out_csv.exists():
        base = pd.read_csv(out_csv)
        df = pd.concat([base, batch], ignore_index=True)
    else:
        base = pd.DataFrame(columns=batch.columns)
        df = batch.copy()

    df["_k"] = df.apply(_stable_row_key, axis=1)
    df = df.drop_duplicates(subset="_k", keep="first").drop(columns=["_k"]).reset_index(drop=True)
    before = len(base)
    _atomic_write_csv(out_csv, df)
    return len(df) - before

def _state_path(out_dir: Path) -> Path:
    return out_dir / "checkpoint.json"

def load_checkpoint(out_dir: Path) -> Dict:
    """Load per-ASIN last-seen state."""
    p = _state_path(out_dir)
    if p.exists():
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}

def save_checkpoint(out_dir: Path, state: Dict) -> None:
    p = _state_path(out_dir)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")

# -----------------------------
# Public pipeline
# -----------------------------

def collect_reviews_for_asins(
    df_asin: pd.DataFrame,
    max_reviews_per_asin: int = 500,
    marketplace: str = "US",
    out_dir: Optional[Path] = None,
    collection_id: Optional[str] = None,
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    High-level pipeline:
      - Runs Selenium collector for given ASIN list.
      - Appends to CSV incrementally after EACH page (via per_page_sink).
      - Maintains a JSON checkpoint to skip ASINs without new content.
      - Returns (reviews_df, per_category_counts).

    Expected df_asin columns at minimum:
      - 'asin'
      - optional 'category_path' (for per-category counts)
    """
    if out_dir is None:
        # default Out/<collection_id> if provided, else Out/session
        base = Path("Out")
        if collection_id:
            out_dir = base / collection_id
        else:
            out_dir = base / "session"
    out_dir.mkdir(parents=True, exist_ok=True)

    reviews_csv = out_dir / "reviews.csv"
    state = load_checkpoint(out_dir)  # {asin: { "last_ids": [...], "last_date": "..." }}

    # Prepare 'last_seen' map for collector
    last_seen = {}
    for asin, meta in (state or {}).items():
        last_seen[asin] = {
            "ids": list(meta.get("last_ids", [])),
            "date": meta.get("last_date"),
        }

    def _per_page_sink(asin: str, page_idx: int, page_df: pd.DataFrame):
        """Called by the collector after EACH page is parsed."""
        page_df = _tag_near_duplicates(page_df)   # <-- mark, do not drop
        added = _append_and_dedupe(reviews_csv, page_df)
        print(f"[CSV] ASIN={asin} p{page_idx} -> +{added} unique rows (total so far: {sum(1 for _ in open(reviews_csv, 'r', encoding='utf-8'))-1 if reviews_csv.exists() else 0})")
        # update checkpoint
        if asin not in state:
            state[asin] = {}
        if not page_df.empty:
            # store top-50 review_ids and the top-most review date (as seen on pX)
            state[asin]["last_ids"] = list(page_df["review_id"].dropna().astype(str).head(50))
            # top-most row
            try:
                state[asin]["last_date"] = str(page_df["review_date_raw"].iloc[0])
            except Exception:
                pass
        save_checkpoint(out_dir, state)

    asins = list(dict.fromkeys(df_asin["asin"].astype(str).tolist()))  # unique, preserve order

    # Run Selenium collector (will call _per_page_sink on each page)
    full_df = collect_reviews(
        asins=asins,
        max_reviews_per_asin=max_reviews_per_asin,
        marketplace=marketplace,
        last_seen=last_seen,
        per_page_sink=_per_page_sink,
    )

    # Ensure CSV reflects all rows from this session too
    _append_and_dedupe(reviews_csv, full_df)

    # Per-category counts (if category present)
    if "category_path" in df_asin.columns:
        per_cat = df_asin.groupby("category_path", dropna=False).size().reset_index(name="asins")
    else:
        per_cat = pd.DataFrame(columns=["category_path", "asins"])

    return full_df, per_cat

def append_and_dedupe_reviews(out_csv: Path, batch: pd.DataFrame) -> int:
    """Kept for compatibility with older app.py imports."""
    return _append_and_dedupe(out_csv, batch)