from pathlib import Path
import pandas as pd
from datetime import datetime

class SessionState:
    def __init__(self):
        self.df_asin = None
        self.collection_id = None
        self.collection_path = None

    def load_collection(self, collection_id: str = None):
        from core.collection_io import list_collections  # Импортировать здесь, чтобы избежать циклического импорта

        if collection_id is None:
            print("[ℹ] No collection loaded. Select from saved collections:")
            collections = list_collections()
            if not collections:
                print("[!] No available collections.")
                return
            for idx, name in enumerate(collections, 1):
                print(f"{idx}) {name}")
            choice = input("Enter collection number (or press Enter to cancel): ").strip()
            if not choice.isdigit() or not (1 <= int(choice) <= len(collections)):
                print("[✖] Invalid selection.")
                return
            collection_id = collections[int(choice) - 1]

        collection_id = collection_id.replace(".csv", "")
        path = Path("collections") / collection_id
        if path.exists() and not path.is_dir():
            path.unlink()
        if not path.exists():
            path.mkdir(parents=True, exist_ok=True)
        asin_file = path / "asins.csv"
        print(f"[DEBUG] Looking for ASIN file at: {asin_file}")
        if asin_file.exists():
            print(f"[DEBUG] ASIN file found. Loading collection: {collection_id}")
            self.df_asin = pd.read_csv(asin_file)
            self.collection_id = collection_id
            self.collection_path = path
        else:
            print(f"[DEBUG] ASIN file not found at: {asin_file}")
            print(f"[!] ASIN file not found for collection: {collection_id}")

    def load_full_context(self, collection_id: str):
        self.load_collection(collection_id)
        self.load_reviews_and_snapshot()

    def load_reviews_and_snapshot(self):
        if not self.collection_path:
            print("[!] No collection path set.")
            return
        reviews_file = max(self.collection_path.glob("*__reviews.csv"), default=None)
        snapshot_file = max(self.collection_path.glob("*__snapshot.csv"), default=None)
        if reviews_file and reviews_file.exists():
            self.df_reviews = pd.read_csv(reviews_file)
            print(f"[+] Loaded reviews: {reviews_file.name}")
        else:
            print("[!] Reviews file not found.")
        if snapshot_file and snapshot_file.exists():
            self.df_snapshot = pd.read_csv(snapshot_file)
            print(f"[+] Loaded snapshot: {snapshot_file.name}")
        else:
            print("[!] Snapshot file not found.")

    def has_reviews(self):
        return hasattr(self, 'df_reviews') and self.df_reviews is not None

    def has_snapshot(self):
        return hasattr(self, 'df_snapshot') and self.df_snapshot is not None

    def is_collection_loaded(self):
        return (
            self.df_asin is not None and
            self.collection_path is not None and
            self.collection_path.exists() and
            self.collection_path.is_dir()
        )

    def ensure_collection_dir(self):
        if self.collection_path and self.collection_path.exists() and not self.collection_path.is_dir():
            raise NotADirectoryError(f"[ERR] Path exists but is not a directory: {self.collection_path}")
        if self.collection_path and not self.collection_path.exists():
            self.collection_path.mkdir(parents=True, exist_ok=True)

    def list_available_collections(self):
        data_dir = Path("collections")
        if not data_dir.exists():
            print("[No collections found]")
        else:
            collections = [
                d.name for d in data_dir.iterdir()
                if d.is_dir() and (d / "asins.csv").exists()
            ]
            if not collections:
                print("[No valid collections found]")
            else:
                for idx, name in enumerate(collections, 1):
                    print(f"{idx}) {name}")

    def get_marketplace(self):
        if self.df_asin is not None and "country" in self.df_asin.columns:
            return self.df_asin["country"].iloc[0]
        else:
            return "com"

    def save(self):
        if self.df_asin is not None:
            asin_path = self.collection_path / "asins.csv"
            self.df_asin.to_csv(asin_path, index=False)
        if hasattr(self, 'df_reviews') and self.df_reviews is not None:
            timestamp = datetime.now().strftime("%y%m%d_%H%M")
            reviews_filename = f"{timestamp}__{self.collection_id}__reviews.csv"
            reviews_path = self.collection_path / reviews_filename
            self.df_reviews.to_csv(reviews_path, index=False)
        if hasattr(self, 'df_snapshot') and self.df_snapshot is not None:
            timestamp = datetime.now().strftime("%y%m%d_%H%M")
            snapshot_filename = f"{timestamp}__{self.collection_id}__snapshot.csv"
            snapshot_path = self.collection_path / snapshot_filename
            self.df_snapshot.to_csv(snapshot_path, index=False)

    def __str__(self):
        return f"Session(collection_id={self.collection_id}, " \
               f"has_asins={self.df_asin is not None}, " \
               f"has_reviews={self.has_reviews()}, " \
               f"has_snapshot={self.has_snapshot()})"

SESSION = SessionState()