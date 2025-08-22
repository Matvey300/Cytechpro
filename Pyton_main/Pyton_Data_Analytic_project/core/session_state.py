from pathlib import Path
import pandas as pd

class SessionState:
    def __init__(self):
        self.df_asin = None
        self.collection_id = None
        self.collection_path = None

    def load_collection(self, collection_id: str):
        collection_id = collection_id.replace(".csv", "")
        path = Path("collections") / collection_id
        if path.exists() and not path.is_dir():
            path.unlink()
        if not path.exists():
            path.mkdir(parents=True, exist_ok=True)
        asin_file = path / "asins.csv"
        if asin_file.exists():
            self.df_asin = pd.read_csv(asin_file)
            self.collection_id = collection_id
            self.collection_path = path
        else:
            print(f"[!] ASIN file not found for collection: {collection_id}")

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
            collections = [d.name for d in data_dir.iterdir() if d.is_dir()]
            for idx, name in enumerate(collections, 1):
                print(f"{idx}) {name}")

SESSION = SessionState()