import importlib
import pandas as pd
from pathlib import Path

# ✅ новые утилиты
from storage.io_utils import save_df_csv, new_out_dir_for_collection, today_ymd


# asin_pipeline.py


def collect_asin_data(category_path: str, region: str, top_k: int = 100) -> pd.DataFrame:
    """
    Call user's ASIN collector from ASIN_data_import.py.
    Supports both function names:
      - Collect_ASIN_DATA(category, region)
      - collect_asins(category, region, top_k)
    Returns a normalized DataFrame with columns ['asin', 'region', 'category_path'].
    """
    mod = importlib.import_module("ASIN_data_import")

    df = None
    # 1) Preferred: Collect_ASIN_DATA(category, region) -> DataFrame
    if hasattr(mod, "Collect_ASIN_DATA"):
        df = mod.Collect_ASIN_DATA(category_path, region)
    # 2) Alt: collect_asins(category, region, top_k) -> DataFrame
    elif hasattr(mod, "collect_asins"):
        try:
            df = mod.collect_asins(category_path, region, top_k)
        except TypeError:
            # if legacy signature is (category, region)
            df = mod.collect_asins(category_path, region)

    if df is None or not isinstance(df, pd.DataFrame):
        raise RuntimeError("ASIN_data_import must provide Collect_ASIN_DATA(category, region) "
                           "or collect_asins(category, region[, top_k]) returning a pandas DataFrame.")

    # Normalize columns
    if "asin" not in df.columns:
        for c in df.columns:
            if c.lower() == "asin":
                df = df.rename(columns={c: "asin"})
                break
    if "asin" not in df.columns:
        raise RuntimeError("Returned DataFrame has no 'asin' column.")

    df["region"] = region
    df["category_path"] = category_path
    df = df.drop_duplicates(subset=["asin"]).head(top_k).reset_index(drop=True)
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