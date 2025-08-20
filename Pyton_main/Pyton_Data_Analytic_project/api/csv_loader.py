# All comments in English.

from pathlib import Path
import pandas as pd

def load_sales_csv_or_none(out_dir_ts: Path) -> pd.DataFrame | None:
    """Stub loader: looks for a sales.csv in the same Out/<ts>/ directory.
       Expected columns: asin, week, weekly_sales, avg_price_week.
       Returns None if not found.
    """
    p = Path(out_dir_ts) / "sales.csv"
    if not p.exists():
        print("[Sales] sales.csv not found; returning None.")
        return None
    df = pd.read_csv(p)
    # Ensure date types
    df['week'] = pd.to_datetime(df['week'], errors='coerce')
    # Optional: compute price_change_weekly or max deviation later in analytics
    return df