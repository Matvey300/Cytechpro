import tempfile
from pathlib import Path

import pandas as pd


class DummySession:
    def __init__(self, base: Path, df_reviews: pd.DataFrame, df_snapshot: pd.DataFrame):
        self.collection_path = base
        self.df_reviews = df_reviews
        self.df_snapshot = df_snapshot
        self.df_asins = pd.DataFrame(
            {"asin": df_snapshot.get("asin", pd.Series(dtype=str)).drop_duplicates()}
        )

    def load_reviews_and_snapshot(self):
        # Exporter calls this, but our frames are already set
        return None


def test_exporter_emits_price_hidden_flag():
    from analytics.exporter import export_for_bi

    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp)

        # Build minimal inputs
        df_snapshot = pd.DataFrame(
            [
                {
                    "asin": "TESTASIN1",
                    "captured_at": "2025-10-13T12:00:00",
                    "price": "Price Hidden",
                    "rating": 4.5,
                    "total_reviews": 123,
                    "new_reviews": 2,
                    "bsr": 456,
                    "category_path": "cat",
                    "title": "sample",
                    "pages_visited": 1,
                    "stopped_reason": "done",
                }
            ]
        )
        df_reviews = pd.DataFrame(
            [
                {
                    "asin": "TESTASIN1",
                    "review_id": "R1",
                    "review_date": "2025-10-12",
                    "rating": 5,
                    "review_text": "ok",
                }
            ]
        )

        session = DummySession(base, df_reviews, df_snapshot)

        out_dir = export_for_bi(session, prefer_parquet=False)

        # Validate files exist
        snap_csv = out_dir / "snapshot_fact.csv"
        assert snap_csv.exists(), f"snapshot_fact not found: {snap_csv}"

        snap = pd.read_csv(snap_csv)
        # price_hidden should be present and True for our hidden price row
        assert "price_hidden" in snap.columns, "price_hidden column missing in snapshot_fact"
        assert bool(snap.loc[snap["asin"] == "TESTASIN1", "price_hidden"].iloc[0]) is True
