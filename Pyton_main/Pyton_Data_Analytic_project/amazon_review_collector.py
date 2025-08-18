# All comments in English.

from __future__ import annotations

import inspect
import traceback
from datetime import datetime
from typing import Any, Callable, Dict, Iterable, List

import pandas as pd

# We expect the user's original scraper to be renamed to:
#   amazon_review_collector_legacy.py  (same folder)
# This wrapper adapts any of its functions to a unified interface:
#   collect_reviews(asins, max_reviews, marketplace) -> DataFrame
try:
    import amazon_review_collector_legacy as legacy  # your original module
except Exception as e:
    legacy = None
    _legacy_import_error = e


# ---------- Helpers to call legacy per-ASIN function ----------

_CANDIDATE_FN_NAMES = [
    # most specific names first
    "collect_reviews_for_asin",
    "get_reviews_for_asin",
    "scrape_reviews_for_asin",
    # generic names
    "collect_reviews",
    "get_reviews",
    "scrape_reviews",
]

def _pick_legacy_function(mod) -> Callable[..., Any] | None:
    """Pick a single-ASIN function from the legacy module by best guess."""
    if mod is None:
        return None
    for name in _CANDIDATE_FN_NAMES:
        fn = getattr(mod, name, None)
        if callable(fn):
            return fn
    return None


def _call_legacy_for_asin(
    fn: Callable[..., Any],
    asin: str,
    max_reviews: int,
    marketplace: str,
) -> List[Dict[str, Any]]:
    """
    Call the legacy function for a single ASIN with a robust signature adapter.
    Accepts common legacy signatures, e.g.:
      fn(asin), fn(asin, max_reviews), fn(asin, max_reviews, marketplace), ...
    Returns: list of dict-like review rows (flexible).
    """
    sig = inspect.signature(fn)
    params = list(sig.parameters.keys())

    # Build args dynamically
    kwargs: Dict[str, Any] = {}
    args: List[Any] = []

    # Common patterns:
    # 1) (asin)
    # 2) (asin, max_reviews)
    # 3) (asin, marketplace)
    # 4) (asin, max_reviews, marketplace)
    # 5) keyword-only variants

    if len(params) == 1:
        args = [asin]
    elif len(params) == 2:
        # Decide by parameter names
        p1, p2 = params
        if "max" in p2 or "count" in p2 or "limit" in p2:
            args = [asin, max_reviews]
        else:
            args = [asin, marketplace]
    elif len(params) >= 3:
        args = [asin, max_reviews, marketplace][:len(params)]
    else:
        # Fallback: try the simplest
        args = [asin]

    # Final safety: if names expose obvious keywords, pass as kwargs too
    ba = {}
    if "asin" in params and len(params) == 1:
        kwargs = {"asin": asin}
        args = []
    if "max_reviews" in params:
        kwargs["max_reviews"] = max_reviews
    if "marketplace" in params:
        kwargs["marketplace"] = marketplace

    try:
        res = fn(*args, **kwargs)
    except TypeError:
        # Retry with only the ASIN when signature mismatch happens
        res = fn(asin)

    # Normalize to list[dict]
    if res is None:
        return []
    if isinstance(res, pd.DataFrame):
        return res.to_dict(orient="records")
    if isinstance(res, dict):
        return [res]
    if isinstance(res, (list, tuple)):
        # try to ensure dict-like rows
        out: List[Dict[str, Any]] = []
        for r in res:
            if isinstance(r, dict):
                out.append(r)
            elif isinstance(r, (list, tuple)) and len(r) >= 4:
                # naive tuple mapping: asin, date, rating, text
                out.append({
                    "asin": asin,
                    "review_date": r[0],
                    "rating": r[1],
                    "review_text": r[2] if len(r) > 2 else None,
                    "review_id": r[3] if len(r) > 3 else None,
                })
            else:
                out.append({"asin": asin, "raw": str(r)})
        return out
    # anything else -> wrap
    return [{"asin": asin, "raw": str(res)}]


# ---------- Normalization ----------

REQUIRED_COLS = [
    "asin",
    "review_id",
    "review_date",
    "rating",
    "review_text",
    "verified",
    "helpful_votes",
]

def _coerce_to_df(rows: List[Dict[str, Any]]) -> pd.DataFrame:
    """Coerce a list of dicts to DataFrame with required columns."""
    df = pd.DataFrame(rows)

    # Ensure presence of required columns
    for col in REQUIRED_COLS:
        if col not in df.columns:
            df[col] = None

    # Coerce types
    # date
    if "review_date" in df.columns:
        df["review_date"] = pd.to_datetime(df["review_date"], errors="coerce").dt.date.astype("string")
    # rating
    if "rating" in df.columns:
        df["rating"] = pd.to_numeric(df["rating"], errors="coerce")
    # helpful votes
    if "helpful_votes" in df.columns:
        df["helpful_votes"] = pd.to_numeric(df["helpful_votes"], errors="coerce").fillna(0).astype("Int64")
    # verified → bool
    if "verified" in df.columns:
        df["verified"] = df["verified"].astype("boolean")

    # Trim whitespace in text-ish fields
    for c in ["review_text", "review_id"]:
        if c in df.columns:
            df[c] = df[c].astype("string").str.strip()

    # Keep only relevant + any extra original columns (if needed later)
    base = df[REQUIRED_COLS].copy()
    # Drop rows without ASIN
    base = base[base["asin"].astype("string").str.len() > 0]
    return base.reset_index(drop=True)


def _dedupe(df: pd.DataFrame) -> pd.DataFrame:
    """Dedupe strategy: prefer (asin, review_id); fallback (asin, review_date, rating, hash(text))."""
    def _key(row) -> str:
        asin = str(row.get("asin", "NA"))
        rid = row.get("review_id")
        if pd.notna(rid) and str(rid).strip():
            return f"{asin}|{rid}"
        date = str(row.get("review_date", "NA"))
        rating = str(row.get("rating", "NA"))
        text = str(row.get("review_text", ""))
        return f"{asin}|{date}|{rating}|{hash(text)}"

    keys = df.apply(_key, axis=1)
    return df.loc[~keys.duplicated(keep="first")].reset_index(drop=True)


# ---------- Public entry point ----------

def collect_reviews(asins: Iterable[str], max_reviews: int, marketplace: str) -> pd.DataFrame:
    """
    Unified public function consumed by the app.
    - asins: list of ASIN strings
    - max_reviews: up to N reviews per ASIN
    - marketplace: "US" / "UK" (passed to legacy if supported)
    Returns a normalized DataFrame with at least columns REQUIRED_COLS.
    """
    if legacy is None:
        raise ImportError(
            "Failed to import amazon_review_collector_legacy. "
            f"Original error: {getattr(globals(),'_legacy_import_error', 'unknown')}\n"
            "Please rename your original file to 'amazon_review_collector_legacy.py' "
            "and keep this wrapper as 'amazon_review_collector.py'."
        )

    per_asin_fn = _pick_legacy_function(legacy)
    if per_asin_fn is None:
        raise RuntimeError(
            "Could not find a per-ASIN function in amazon_review_collector_legacy.py.\n"
            f"Tried names: {', '.join(_CANDIDATE_FN_NAMES)}.\n"
            "Please expose one of these functions (taking at least 'asin' argument)."
        )

    all_rows: List[Dict[str, Any]] = []
    seen = set()

    for asin in map(str, asins):
        try:
            rows = _call_legacy_for_asin(per_asin_fn, asin, max_reviews, marketplace)
        except Exception:
            # Continue collecting other ASINs on failure
            traceback.print_exc()
            rows = []

        # Cap to max_reviews per ASIN if legacy returned more
        if max_reviews and isinstance(max_reviews, int) and max_reviews > 0:
            # Keep only first N rows for this ASIN
            cnt = 0
            pruned = []
            for r in rows:
                if str(r.get("asin", asin)) != asin:
                    r["asin"] = asin
                pruned.append(r)
                cnt += 1
                if cnt >= max_reviews:
                    break
            rows = pruned

        for r in rows:
            # ASIN safety
            if str(r.get("asin", "")).strip() == "":
                r["asin"] = asin
            all_rows.append(r)

    # Normalize + dedupe
    df = _coerce_to_df(all_rows)
    df = _dedupe(df)
    return df