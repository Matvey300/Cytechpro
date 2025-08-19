# app.py
# All comments in English.

from __future__ import annotations

import sys
import json
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import pandas as pd

# Pipelines
from reviews_pipeline import collect_reviews_for_asins

# -----------------------------------------------------------------------------
# Simple console helpers
# -----------------------------------------------------------------------------

def info(msg: str) -> None:
    print(f"[INFO] {msg}")

def warn(msg: str) -> None:
    print(f"[WARN] {msg}")

def err(msg: str) -> None:
    print(f"[ERROR] {msg}", file=sys.stderr)

def ask(prompt: str) -> str:
    try:
        return input(prompt)
    except KeyboardInterrupt:
        print()
        return ""

def slugify(s: str) -> str:
    import re
    s = s.strip().lower()
    s = re.sub(r"[^a-z0-9]+", "-", s)
    return s.strip("-")

def today_ymd() -> str:
    from datetime import datetime, timezone
    return datetime.now(tz=timezone.utc).strftime("%Y%m%d")


# -----------------------------------------------------------------------------
# Storage helpers (collections listing / loading / saving)
# -----------------------------------------------------------------------------

OUT_BASE = Path("Out").resolve()

def _is_collection_dir(p: Path) -> bool:
    """
    A valid collection directory:
      - is a directory;
      - does NOT start with '_' (skip service dirs like _raw_review_pages);
      - contains 'asins.csv'
    """
    if not p.is_dir():
        return False
    if p.name.startswith("_"):
        return False
    return (p / "asins.csv").exists()

def list_saved_collections() -> List[Tuple[str, Path]]:
    """
    Return list of (collection_id, path) for all valid collections under Out/.
    Sorted by mtime desc.
    """
    OUT_BASE.mkdir(parents=True, exist_ok=True)
    cols = []
    for child in OUT_BASE.iterdir():
        if _is_collection_dir(child):
            cols.append((child.name, child))
    # sort newest first
    cols.sort(key=lambda x: x[1].stat().st_mtime, reverse=True)
    return cols

def print_collections(cols: List[Tuple[str, Path]]) -> None:
    if not cols:
        print("No saved ASIN collections found under ./Out")
        return
    print("Saved collections:")
    for i, (cid, path) in enumerate(cols, start=1):
        mk = "-"
        try:
            meta_path = path / "meta.json"
            if meta_path.exists():
                meta = json.loads(meta_path.read_text(encoding="utf-8"))
                mk = meta.get("marketplace", "-")
        except Exception:
            pass
        # count asins
        asin_count = 0
        try:
            asin_df = pd.read_csv(path / "asins.csv")
            asin_count = len(asin_df)
        except Exception:
            pass
        print(f"{i}) ID={cid} | market={mk} | ASINs={asin_count}")

def load_asin_collection_by_selector(selector: str) -> Tuple[str, pd.DataFrame, Path]:
    """
    Load by (number in list) or by collection_id string. Returns (collection_id, df_asin, path).
    Raises ValueError if not found.
    """
    cols = list_saved_collections()
    if not cols:
        raise ValueError("No saved collections were found under ./Out")

    # number?
    if selector.isdigit():
        idx = int(selector)
        if idx < 1 or idx > len(cols):
            raise ValueError("Invalid number.")
        cid, path = cols[idx - 1]
    else:
        # by id
        matches = [x for x in cols if x[0] == selector]
        if not matches:
            raise ValueError(f"Collection '{selector}' not found.")
        cid, path = matches[0]

    asins_csv = path / "asins.csv"
    df = pd.read_csv(asins_csv)
    return cid, df, path


# -----------------------------------------------------------------------------
# Minimal ASIN collection utilities (save + meta)
# -----------------------------------------------------------------------------

def save_asin_collection(df_asin: pd.DataFrame, collection_id: str, marketplace: str) -> Path:
    """
    Save ASIN DataFrame and a tiny meta.json. Return collection path.
    """
    path = OUT_BASE / collection_id
    path.mkdir(parents=True, exist_ok=True)
    df_asin.to_csv(path / "asins.csv", index=False)
    meta = {"collection_id": collection_id, "marketplace": marketplace, "saved_at": int(time.time())}
    (path / "meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    return path


# -----------------------------------------------------------------------------
# Session
# -----------------------------------------------------------------------------

SESSION: Dict[str, object] = {
    "marketplace": "US",         # or "UK"
    "collection_id": None,       # current working collection id
    "collection_path": None,     # Path
    "df_asin": None,             # pandas DataFrame with 'asin' (and optional 'category_path')
}


# -----------------------------------------------------------------------------
# Menu actions
# -----------------------------------------------------------------------------

def action_set_marketplace():
    print("Choose marketplace: 1) US   2) UK")
    ch = ask("> Enter 1 or 2: ").strip()
    if ch == "2":
        SESSION["marketplace"] = "UK"
    else:
        SESSION["marketplace"] = "US"
    info(f"Marketplace set to {SESSION['marketplace']}")

def action_collect_asin_list():
    """
    Placeholder for your ASIN collector UI (category selection, etc.).
    For now we just ask user to type a collection name and a few ASINs.
    Replace this with your existing ASIN collection flow when ready.
    """
    base = ask("Collection base name (e.g., 'headphones'): ").strip() or "asin-collection"
    suffix = "-" + ask("Optional suffix (Enter to skip): ").strip() if ask else ""
    market = str(SESSION["marketplace"])
    collection_id = f"{slugify(base)}{suffix}_{market}_{today_ymd()}"

    # Simple input for demo; replace with your real category-driven collector:
    print("Enter ASINs (comma or space separated):")
    raw = ask("> ").strip()
    asins = [a.strip().upper() for a in re_split_tokens(raw) if a.strip()]
    if not asins:
        warn("No ASINs provided, aborting.")
        return

    df = pd.DataFrame({"asin": asins})
    path = save_asin_collection(df, collection_id, market)
    SESSION["collection_id"] = collection_id
    SESSION["collection_path"] = path
    SESSION["df_asin"] = df
    info(f"ASIN collection saved: {collection_id} (ASINs={len(df)})")

def re_split_tokens(s: str) -> List[str]:
    import re
    return re.split(r"[,\s]+", s)

def action_load_saved_collection_and_collect_reviews():
    """
    Load an existing ASIN collection and immediately run review collection on it.
    This action is allowed at any time (no prerequisite steps).
    """
    cols = list_saved_collections()
    if not cols:
        warn("No saved ASIN collections under ./Out. Create one first.")
        return
    print_collections(cols)
    sel = ask("> Enter number OR collection ID to load: ").strip()
    try:
        cid, df, path = load_asin_collection_by_selector(sel)
    except ValueError as e:
        err(str(e))
        return

    SESSION["collection_id"] = cid
    SESSION["collection_path"] = path
    SESSION["df_asin"] = df
    info(f"Loaded collection '{cid}' (ASINs={len(df)})")

    # Run reviews collection immediately
    out_dir = path
    try:
        reviews_df, per_cat_counts = collect_reviews_for_asins(
            df_asin=df,
            max_reviews_per_asin=500,
            marketplace=str(SESSION["marketplace"]),
            out_dir=out_dir,
            collection_id=cid,
        )
        info(f"Collected {len(reviews_df)} rows (incremental CSV is under {out_dir}/reviews.csv)")
    except Exception as e:
        err(f"Review collection failed: {e}")

def action_collect_reviews_for_current_collection():
    """
    Collect reviews for the ASIN list already in SESSION (if present).
    If not present — guide user to load an existing collection.
    """
    df = SESSION.get("df_asin")
    cid = SESSION.get("collection_id")
    path = SESSION.get("collection_path")
    if df is None or cid is None or path is None:
        warn("No active ASIN collection. Please use menu 'Load saved ASIN collection & collect reviews'.")
        return

    try:
        reviews_df, per_cat_counts = collect_reviews_for_asins(
            df_asin=df,
            max_reviews_per_asin=500,
            marketplace=str(SESSION["marketplace"]),
            out_dir=path,
            collection_id=str(cid),
        )
        info(f"Collected {len(reviews_df)} rows (incremental CSV is under {path}/reviews.csv)")
    except Exception as e:
        err(f"Review collection failed: {e}")

def action_list_saved_collections():
    cols = list_saved_collections()
    print_collections(cols)


# -----------------------------------------------------------------------------
# Menu loop
# -----------------------------------------------------------------------------

def main_menu():
    while True:
        print("\n--- Amazon Reviews Tool ---")
        print(f"Market: {SESSION['marketplace']}")
        print("0) Exit")
        print("1) Set marketplace (US/UK)")
        print("2) Create & save new ASIN collection (simple input)")
        print("3) Collect reviews for CURRENT loaded collection")
        print("4) Load saved ASIN collection & collect reviews (can be used immediately)")
        print("5) List saved ASIN collections")
        choice = ask("> Enter choice [0-5]: ").strip()

        if choice == "0":
            print("Bye!")
            return
        elif choice == "1":
            action_set_marketplace()
        elif choice == "2":
            action_collect_asin_list()
        elif choice == "3":
            action_collect_reviews_for_current_collection()
        elif choice == "4":
            action_load_saved_collection_and_collect_reviews()
        elif choice == "5":
            action_list_saved_collections()
        else:
            print("Unknown choice.")


if __name__ == "__main__":
    try:
        main_menu()
    except KeyboardInterrupt:
        print("\nInterrupted.")