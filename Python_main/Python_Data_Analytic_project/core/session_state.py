"""
# === Module Header ===
# 📁 Module: core/session_state.py
# 📅 Last Reviewed: 2025-10-15
# 🔧 Status: 🟢 Stable
# 👤 Owner: MatveyB
# 📝 Summary: In-memory session, loading of collections, reviews, and snapshots.
# =====================
"""

import pandas as pd
from core.collection_io import collection_csv
from core.log import print_error, print_info, print_success


class SessionState:
    def __init__(self):
        self.df_asin = None
        self.df_asins = None
        self.df_reviews = None
        self.df_snapshot = None
        self.collection_id = None
        self.collection_path = None
        self.created_date = None
        self.last_snapshot_date = None
        self.latest_snapshot_file = None
        self.latest_reviews_file = None
        self.marketplace = None

    def load_collection(self, collection_id: str = None):
        from core.collection_io import list_collections
        from core.collection_io import load_collection as io_load_collection
        from core.collection_io import parse_collection_dirname

        # Interactive selection if not provided
        if collection_id is None:
            print_info("No collection loaded. Select from saved collections:")
            collections = list_collections()
            if not collections:
                print_error("No available collections.")
                return
            for idx, name in enumerate(collections, 1):
                print(f"{idx}) {name}")
            choice = input("Enter collection number (or press Enter to cancel): ").strip()
            if not choice.isdigit() or not (1 <= int(choice) <= len(collections)):
                print_error("Invalid selection.")
                return
            selected = collections[int(choice) - 1]
            # selected is a folder name in new format; extract cid
            try:
                parts = parse_collection_dirname(selected)
                collection_id = parts["cid"]
            except Exception:
                # fallback: assume provided is the cid
                collection_id = selected

        # Delegate to IO (new format only)
        io_load_collection(collection_id, self)

        collection_file = collection_csv(self.collection_path)
        if collection_file.exists():
            self.df_asins = pd.read_csv(collection_file)
            self.marketplace = self.get_marketplace()
            print_success(f"Loaded ASINs: {collection_file.name} ({len(self.df_asins)} rows)")
        else:
            print_error("ASIN file not found.")

    def load_full_context(self, collection_id: str):
        self.load_collection(collection_id)
        self.load_reviews_and_snapshot()

    def load_reviews_and_snapshot(self):
        if not self.collection_path:
            print_error("No collection path set.")
            return
        from core.collection_io import reviews_csv, snapshot_csv

        reviews_file = reviews_csv(self.collection_path)
        snapshot_file = snapshot_csv(self.collection_path)

        if reviews_file.exists():
            self.df_reviews = pd.read_csv(reviews_file)
            self.latest_reviews_file = reviews_file
            print_success(f"Loaded reviews: {reviews_file.name} ({len(self.df_reviews)} rows)")
        else:
            print_error("Reviews file not found.")

        if snapshot_file.exists():
            self.df_snapshot = pd.read_csv(snapshot_file)
            self.latest_snapshot_file = snapshot_file
            print_success(f"Loaded snapshot: {snapshot_file.name} ({len(self.df_snapshot)} rows)")
            if "captured_at" in self.df_snapshot.columns:
                try:
                    self.last_snapshot_date = max(
                        pd.to_datetime(self.df_snapshot["captured_at"]).dt.strftime("%Y%m%d")
                    )
                except Exception:
                    self.last_snapshot_date = None
        else:
            print_error("Snapshot file not found.")

    def has_reviews(self):
        return hasattr(self, "df_reviews") and self.df_reviews is not None

    def has_snapshot(self):
        return hasattr(self, "df_snapshot") and self.df_snapshot is not None

    def is_collection_loaded(self):
        return (
            self.df_asins is not None
            and self.collection_path is not None
            and self.collection_path.exists()
            and self.collection_path.is_dir()
        )

    def ensure_collection_dir(self):
        if (
            self.collection_path
            and self.collection_path.exists()
            and not self.collection_path.is_dir()
        ):
            raise NotADirectoryError(
                f"[ERR] Path exists but is not a directory: {self.collection_path}"
            )
        if self.collection_path and not self.collection_path.exists():
            self.collection_path.mkdir(parents=True, exist_ok=True)

    def list_available_collections(self):
        from core.collection_io import list_collections

        cols = list_collections()
        if not cols:
            print_info("No collections found")
            return
        for idx, name in enumerate(cols, 1):
            print(f"{idx}) {name}")

    def get_marketplace(self):
        if self.df_asins is not None and "country" in self.df_asins.columns:
            return self.df_asins["country"].iloc[0]
        else:
            return "com"

    def save(self):
        from core.collection_io import save_snapshot

        if self.df_asins is not None and self.collection_path:
            out = collection_csv(self.collection_path)
            self.df_asins.to_csv(out, index=False)
        if getattr(self, "df_snapshot", None) is not None and self.collection_path is not None:
            save_snapshot(self, self.df_snapshot, overwrite_today=True)

    def __str__(self):
        return (
            f"Session(collection_id={self.collection_id}, "
            f"has_asins={self.df_asins is not None}, "
            f"has_reviews={self.has_reviews()}, "
            f"has_snapshot={self.has_snapshot()})"
        )


SESSION = SessionState()
