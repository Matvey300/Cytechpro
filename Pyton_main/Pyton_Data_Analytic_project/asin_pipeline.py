import importlib
import pandas as pd
from pathlib import Path

# ✅ новые утилиты
from storage.io_utils import save_df_csv, new_out_dir_for_collection, today_ymd


def collect_asin_data(category_path: str, region: str, top_k: int = 100) -> pd.DataFrame:
    """
    Collect ASINs for a given category and region using existing legacy script.
    """
    mod = importlib.import_module("ASIN_data_import")
    df = mod.collect_asins(category_path, region, top_k)
    return df


def save_asin_collection(df: pd.DataFrame, collection_id: str, out_root: Path = Path("Out")) -> Path:
    """
    Save ASIN DataFrame to CSV with proper folder structure.
    """
    out_dir = new_out_dir_for_collection(out_root, collection_id)
    csv_path = out_dir / f"asins_{today_ymd()}.csv"
    save_df_csv(df, csv_path)
    return csv_path


def list_saved_collections(out_root: Path = Path("Out")) -> list[str]:
    """
    List all saved ASIN collections by scanning Out/ directory.
    """
    if not out_root.exists():
        return []
    return [p.name for p in out_root.iterdir() if p.is_dir()]


def load_asin_collection_by_id(collection_id: str, out_root: Path = Path("Out")) -> pd.DataFrame:
    """
    Load a previously saved ASIN collection by its ID.
    """
    folder = out_root / collection_id
    if not folder.exists():
        raise FileNotFoundError(f"Collection {collection_id} not found under {out_root}")
    # load the newest csv in that folder
    csv_files = sorted(folder.glob("asins_*.csv"))
    if not csv_files:
        raise FileNotFoundError(f"No ASIN CSV found for {collection_id}")
    return pd.read_csv(csv_files[-1])