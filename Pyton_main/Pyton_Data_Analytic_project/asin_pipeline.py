# All comments in English.

from pathlib import Path
from typing import Tuple
import importlib
import pandas as pd

from storage.io_utils import write_csv, ensure_dir, now_ts_folder
from storage.registry import load_registry, save_registry

def collect_asin_data(category_path: str, region: str, top_k: int = 100) -> pd.DataFrame:
    """Calls user's Collect_ASIN_DATA(category, region) and normalizes output."""
    mod = importlib.import_module("ASIN_data_import")
    if not hasattr(mod, "Collect_ASIN_DATA"):
        raise RuntimeError("ASIN_data_import.Collect_ASIN_DATA not found.")
    df = mod.Collect_ASIN_DATA(category_path, region)
    if not isinstance(df, pd.DataFrame):
        raise RuntimeError("Collect_ASIN_DATA must return a pandas DataFrame.")
    # Normalize columns
    if "asin" not in df.columns:
        for c in df.columns:
            if c.lower() == "asin":
                df = df.rename(columns={c: "asin"})
                break
    df["region"] = region
    df["category_path"] = category_path
    df = df.drop_duplicates(subset=["asin"]).head(top_k).reset_index(drop=True)
    return df

def save_asin_collection(df_asin: pd.DataFrame, registry_path: Path, out_dir_ts: Path) -> Path:
    """Saves asin_list.csv to out_dir_ts and updates registry."""
    ensure_dir(out_dir_ts)
    dest = out_dir_ts / "asin_list.csv"
    write_csv(df_asin, dest)
    reg = load_registry(registry_path)
    entry = {
        "id": now_ts_folder(),
        "timestamp": now_ts_folder(),
        "region": df_asin["region"].iloc[0] if ("region" in df_asin.columns and not df_asin.empty) else "NA",
        "categories": sorted(df_asin["category_path"].dropna().unique().tolist()) if "category_path" in df_asin.columns else [],
        "asin_count": int(df_asin["asin"].nunique()) if "asin" in df_asin.columns else 0,
        "out_dir_ts": str(out_dir_ts),
    }
    reg.append(entry)
    save_registry(registry_path, reg)
    return dest

def list_saved_collections(registry_path: Path):
    return load_registry(registry_path)

def load_asin_collection_by_id(registry_path: Path, coll_id: str) -> Tuple[pd.DataFrame, Path]:
    reg = load_registry(registry_path)
    for item in reg:
        if item.get("id") == coll_id:
            out_dir_ts = Path(item["out_dir_ts"])
            df = pd.read_csv(out_dir_ts / "asin_list.csv")
            return df, out_dir_ts
    raise FileNotFoundError(f"Collection id {coll_id} not found.")