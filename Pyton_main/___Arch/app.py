# app.py
# All comments in English.

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import pandas as pd
import requests

# Reviews pipeline (incremental CSV append via per_page_sink)
from reviews_pipeline import collect_reviews_for_asins

# Optional: daily screening & 30-day correlation entrypoints
try:
    from screening.daily import has_30_days_of_snapshots, run_daily_screening
except Exception:
    # Fallbacks if the module is not present yet
    def run_daily_screening(df_asin: pd.DataFrame, out_dir: Path):
        raise RuntimeError("screening.daily.run_daily_screening is not available")

    def has_30_days_of_snapshots(collection_path: Path) -> bool:
        return False


# ---------------------------------------------------------------------------
# Console helpers
# ---------------------------------------------------------------------------


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
    """Make a filesystem-friendly slug."""
    import re

    s = (s or "").strip().lower()
    s = re.sub(r"[^a-z0-9]+", "-", s)
    return s.strip("-")


def today_ymd() -> str:
    """UTC YYYYMMDD for collection id."""
    from datetime import datetime, timezone

    return datetime.now(tz=timezone.utc).strftime("%Y%m%d")


def split_tokens(s: str) -> List[str]:
    """Split by comma/space and drop empties."""
    import re

    return [t for t in re.split(r"[,\s]+", (s or "")) if t]


# ---------------------------------------------------------------------------
# Storage helpers (collections listing / loading / saving)
# ---------------------------------------------------------------------------

OUT_BASE = Path("Out").resolve()


def _is_collection_dir(p: Path) -> bool:
    """
    A valid collection directory:
      - is a directory;
      - name does NOT start with '_' (skip service dirs like _raw_review_pages);
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
    cols: List[Tuple[str, Path]] = []
    for child in OUT_BASE.iterdir():
        if _is_collection_dir(child):
            cols.append((child.name, child))
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

    if selector.isdigit():
        idx = int(selector)
        if idx < 1 or idx > len(cols):
            raise ValueError("Invalid number.")
        cid, path = cols[idx - 1]
    else:
        matches = [x for x in cols if x[0] == selector]
        if not matches:
            raise ValueError(f"Collection '{selector}' not found.")
        cid, path = matches[0]

    asins_csv = path / "asins.csv"
    df = pd.read_csv(asins_csv)
    return cid, df, path


def save_asin_collection(
    df_asin: pd.DataFrame, collection_id: str, marketplace: str, meta_extra: Optional[Dict] = None
) -> Path:
    """
    Save ASIN DataFrame and meta.json. Return collection path.
    """
    path = OUT_BASE / collection_id
    path.mkdir(parents=True, exist_ok=True)
    df_asin.to_csv(path / "asins.csv", index=False)
    meta = {
        "collection_id": collection_id,
        "marketplace": marketplace,
        "saved_at": int(time.time()),
    }
    if meta_extra:
        meta.update(meta_extra)
    (path / "meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    return path


# ---------------------------------------------------------------------------
# SerpApi helpers (keyword → categories; strict filtering)
# ---------------------------------------------------------------------------

AMZ_DOMAIN = {"US": "amazon.com", "UK": "amazon.co.uk"}


def serpapi_key() -> Optional[str]:
    """Fetch SerpApi key from environment."""
    key = os.getenv("SERPAPI_KEY") or os.getenv("SERP_API_KEY")
    return key.strip() if key else None


def _amazon_domain(marketplace: str) -> str:
    return AMZ_DOMAIN.get((marketplace or "US").upper(), AMZ_DOMAIN["US"])


def serpapi_search_categories_strict(keyword: str, marketplace: str) -> List[str]:
    """
    Query SerpApi (Amazon engine) and return ONLY categories/paths
    that contain the keyword (or its synonyms) case-insensitively.
    This avoids noisy departments like 'Gift Cards', 'Sell', etc.
    """
    key = serpapi_key()
    if not key:
        warn("SerpApi key not found in environment.")
        return []

    url = "https://serpapi.com/search.json"
    params = {
        "engine": "amazon",
        "amazon_domain": _amazon_domain(marketplace),
        "keyword": keyword,  # ✅ Correct param name
        "api_key": key,
        "page": 1,
    }

    try:
        r = requests.get(url, params=params, timeout=15)
        if r.status_code != 200:
            warn(f"SerpApi responded with status {r.status_code}")
            print(f"[DEBUG] URL: {r.url}")
            print(f"[DEBUG] Response snippet: {r.text[:500]}")
            return []
        data = r.json()
    except Exception as e:
        err(f"SerpApi request failed: {e}")
        return []

    # Define synonyms to improve matching
    kw = (keyword or "").strip().lower()
    SYNONYMS = {
        "headphones": [
            "headphones",
            "earbuds",
            "earbud",
            "earphone",
            "earphones",
            "headset",
            "over-ear",
            "in-ear",
        ],
    }
    tokens = set([kw] + SYNONYMS.get(kw, []))

    def _match(s: str) -> bool:
        s_norm = (s or "").lower()
        return any(tok in s_norm for tok in tokens)

    candidates: List[str] = []

    # Try common category fields
    for k in ("categories", "category_results", "category_information"):
        items = data.get(k)
        if isinstance(items, list):
            for it in items:
                name = (it.get("name") or it.get("title") or it.get("category") or "").strip()
                if name and _match(name):
                    candidates.append(name)

    # Parse breadcrumbs from search results
    for res in data.get("organic_results") or []:
        breadcrumbs = res.get("breadcrumbs") or res.get("category_browse_nodes")
        if isinstance(breadcrumbs, list) and breadcrumbs:
            trail = " > ".join([str(b).strip() for b in breadcrumbs if str(b).strip()])
            if trail and _match(trail):
                candidates.append(trail)

    # Deduplicate while preserving order
    seen = set()
    out: List[str] = []
    for c in candidates:
        if c not in seen:
            seen.add(c)
            out.append(c)

    if not out:
        warn("No matching categories found in SerpApi response.")

    return out


# ---------------------------------------------------------------------------
# Create collection flows (submenu)
# ---------------------------------------------------------------------------


def prompt_marketplace_inside() -> str:
    print("Select marketplace: 1) US   2) UK")
    ch = ask("> Enter 1 or 2: ").strip()
    return "UK" if ch == "2" else "US"


def create_collection_by_keyword_flow() -> None:
    """
    Keyword → categories (multi-select) → collect top-100 ASIN per category (via ASIN_data_import).
    Marketplace is chosen INSIDE this flow.
    """
    marketplace = prompt_marketplace_inside()
    keyword = ask("Enter keyword to search categories (e.g., 'headphones'): ").strip()
    if not keyword:
        warn("Empty keyword. Aborting.")
        return

    # Strict SerpApi categories
    cats = serpapi_search_categories_strict(keyword, marketplace)
    if not cats:
        warn("Could not fetch categories via SerpApi (no key, rate-limit, or empty result).")
        print("You may type category paths manually (e.g., 'Electronics > Headphones > Earbuds').")
        manual = ask("Enter categories (comma-separated): ").strip()
        cats = split_tokens(manual)

    if not cats:
        warn("No categories to select from. Aborting.")
        return

    # Show choices
    print("\nMatched categories:")
    for i, c in enumerate(cats, start=1):
        print(f"{i}) {c}")

    sel = ask("Select categories by numbers (comma-separated, e.g., '1,3,5'): ").strip()
    idxs: List[int] = []
    for tok in split_tokens(sel):
        if tok.isdigit():
            k = int(tok)
            if 1 <= k <= len(cats):
                idxs.append(k - 1)
    if not idxs:
        warn("No valid selections. Aborting.")
        return

    selected_cats = [cats[i] for i in idxs]

    # Use your ASIN_data_import.collect_asins(category_path, region, top_k)
    try:
        import importlib

        mod = importlib.import_module("ASIN_data_import")
    except Exception as e:
        err(f"ASIN_data_import module is missing: {e}")
        return

    all_rows: List[pd.DataFrame] = []
    for cat in selected_cats:
        try:
            df_cat = mod.collect_asins(category_path=cat, region=marketplace, top_k=100)
            df_cat = df_cat.copy()
            if "category_path" not in df_cat.columns:
                df_cat["category_path"] = cat
            all_rows.append(df_cat)
            info(f"Collected {len(df_cat)} ASIN for: {cat}")
        except Exception as e:
            warn(f"Failed to collect ASINs for '{cat}': {e}")

    if not all_rows:
        warn("No ASINs collected. Aborting.")
        return

    df_all = pd.concat(all_rows, ignore_index=True)
    df_all = df_all.drop_duplicates(subset=["asin"], keep="first")

    # Save collection
    base = slugify(keyword) or "asin-collection"
    collection_id = f"{base}_kw_{marketplace}_{today_ymd()}"
    path = save_asin_collection(
        df_all,
        collection_id,
        marketplace,
        meta_extra={"keyword": keyword, "categories": selected_cats},
    )
    SESSION["collection_id"] = collection_id
    SESSION["collection_path"] = path
    SESSION["df_asin"] = df_all
    info(f"ASIN collection saved: {collection_id} (ASINs={len(df_all)})")


def create_collection_manual_flow() -> None:
    """
    Manual ASIN input. Marketplace is chosen INSIDE this flow.
    """
    marketplace = prompt_marketplace_inside()
    base = ask("Collection base name (e.g., 'headphones'): ").strip() or "asin-collection"
    suf = ask("Optional suffix (e.g., '_test'; Enter to skip): ").strip()
    suffix = f"-{suf}" if suf else ""
    collection_id = f"{slugify(base)}{suffix}_{marketplace}_{today_ymd()}"

    print("Enter ASINs (comma or space separated):")
    raw = ask("> ").strip()
    asins = [a.strip().upper() for a in split_tokens(raw)]
    if not asins:
        warn("No ASINs provided, aborting.")
        return

    df = pd.DataFrame({"asin": asins})
    path = save_asin_collection(df, collection_id, marketplace)
    SESSION["collection_id"] = collection_id
    SESSION["collection_path"] = path
    SESSION["df_asin"] = df
    info(f"ASIN collection saved: {collection_id} (ASINs={len(df)})")


def action_create_collection_menu() -> None:
    """
    Unified entry: Create & save new ASIN collection
      1) marketplace is selected INSIDE this submenu
      2) choose between keyword→categories→top100 or manual input
    """
    while True:
        print("\nCreate & save new ASIN collection")
        print("1) Keyword → categories → top‑100 ASIN (SerpApi)")
        print("2) Manual ASIN input")
        print("0) Back")
        ch = ask("> Enter choice [0-2]: ").strip()
        if ch == "1":
            create_collection_by_keyword_flow()
        elif ch == "2":
            create_collection_manual_flow()
        elif ch == "0":
            return
        else:
            print("Unknown choice.")


# ---------------------------------------------------------------------------
# Reviews & collections actions
# ---------------------------------------------------------------------------

SESSION: Dict[str, object] = {
    "collection_id": None,  # current working collection id
    "collection_path": None,  # Path
    "df_asin": None,  # pandas DataFrame with 'asin' (and optional 'category_path')
}


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

    # Derive marketplace from meta.json (fallback to US)
    mk = "US"
    try:
        meta = json.loads((path / "meta.json").read_text(encoding="utf-8"))
        mk = meta.get("marketplace", "US")
    except Exception:
        pass

    SESSION["collection_id"] = cid
    SESSION["collection_path"] = path
    SESSION["df_asin"] = df
    info(f"Loaded collection '{cid}' (market={mk}, ASINs={len(df)})")

    # Run reviews collection immediately
    try:
        reviews_df, per_cat_counts = collect_reviews_for_asins(
            df_asin=df,
            max_reviews_per_asin=500,
            marketplace=str(mk),
            out_dir=path,
            collection_id=cid,
        )
        info(f"Collected {len(reviews_df)} rows (incremental CSV is under {path}/reviews.csv)")
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
        warn(
            "No active ASIN collection. Please use 'Load saved ASIN collection & collect reviews'."
        )
        return

    # derive marketplace from meta.json
    mk = "US"
    try:
        meta = json.loads((path / "meta.json").read_text(encoding="utf-8"))
        mk = meta.get("marketplace", "US")
    except Exception:
        pass

    try:
        reviews_df, per_cat_counts = collect_reviews_for_asins(
            df_asin=df,
            max_reviews_per_asin=500,
            marketplace=str(mk),
            out_dir=path,
            collection_id=str(cid),
        )
        info(f"Collected {len(reviews_df)} rows (incremental CSV is under {path}/reviews.csv)")
    except Exception as e:
        err(f"Review collection failed: {e}")


def action_list_saved_collections():
    cols = list_saved_collections()
    print_collections(cols)


# ---------------------------------------------------------------------------
# Daily screening & correlations
# ---------------------------------------------------------------------------


def action_run_daily_screening():
    """
    Run daily screening (BSR/Price/Reviews count snapshots) for the CURRENT collection.
    """
    df = SESSION.get("df_asin")
    path = SESSION.get("collection_path")
    if df is None or path is None:
        warn("No active ASIN collection. Load a saved collection first (menu option 2).")
        return
    try:
        run_daily_screening(df_asin=df, out_dir=path)
        info("Daily screening completed.")
    except Exception as e:
        err(f"Daily screening failed: {e}")


def action_run_correlation_tests():
    """
    Run reputation–sales correlation tests if at least 30 daily snapshots exist.
    """
    path = SESSION.get("collection_path")
    if path is None:
        warn("No active ASIN collection. Load a saved collection first (menu option 2).")
        return
    try:
        if not has_30_days_of_snapshots(path):
            warn("Not enough daily snapshots yet. Wait until 30 days of data collected.")
            return
        info("Running reputation–sales correlation tests…")
        # TODO: plug your analytics entrypoint here
        info("Correlation tests finished (placeholder).")
    except Exception as e:
        err(f"Correlation tests failed: {e}")


# ---------------------------------------------------------------------------
# Menu loop
# ---------------------------------------------------------------------------


def main_menu():
    while True:
        print("\n--- Amazon Reviews Tool ---")
        print("0) Exit")
        print("1) Create & save new ASIN collection  [marketplace is selected inside]")
        print("2) Load saved ASIN collection & collect reviews")
        print("3) Collect reviews for CURRENT loaded collection")
        print("4) List saved ASIN collections")
        print("5) Run daily screening for current ASIN collection")
        print("6) Run Reputation–Sales correlation tests (available after 30 days)")
        choice = ask("> Enter choice [0-6]: ").strip()

        if choice == "0":
            print("Bye!")
            return
        elif choice == "1":
            action_create_collection_menu()
        elif choice == "2":
            action_load_saved_collection_and_collect_reviews()
        elif choice == "3":
            action_collect_reviews_for_current_collection()
        elif choice == "4":
            action_list_saved_collections()
        elif choice == "5":
            action_run_daily_screening()
        elif choice == "6":
            action_run_correlation_tests()
        else:
            print("Unknown choice.")


if __name__ == "__main__":
    try:
        main_menu()
    except KeyboardInterrupt:
        print("\nInterrupted.")
