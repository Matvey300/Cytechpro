# core/collection_io.py

from pathlib import Path
import pandas as pd
from core.session_state import SessionState

COLLECTIONS_DIR = Path("collections")
COLLECTIONS_DIR.mkdir(exist_ok=True)

def list_collections() -> list[str]:
    return sorted([f.stem for f in COLLECTIONS_DIR.glob("*.csv")])

def create_collection(session: SessionState) -> None:
    name = input("Enter a name for the new ASIN collection: ").strip()
    if not name:
        print("[WARN] Collection name cannot be empty.")
        return create_collection(session)

    path = COLLECTIONS_DIR / f"{name}.csv"
    if path.exists():
        print("[WARN] Collection already exists.")
        return create_collection(session)

    df = pd.DataFrame(columns=["asin", "title", "rating", "review_count", "country", "category_path"])
    df.to_csv(path, index=False)
    print(f"[✅] Created new collection: {name}")

    session.df_asin = df
    session.collection_name = name
    session.collection_path = path

def load_collection(name: str, session: SessionState) -> None:
    path = COLLECTIONS_DIR / f"{name}.csv"
    if not path.exists():
        raise FileNotFoundError(f"No such collection: {name}")

    df = pd.read_csv(path)
    session.df_asin = df
    session.collection_name = name
    session.collection_path = path

def select_collection(session: SessionState) -> None:
    collections = list_collections()
    if collections:
        print("Available collections:")
        for i, name in enumerate(collections, 1):
            print(f"{i}) {name}")
    else:
        print("No collections found.")

    print("0) Create new collection")
    choice = input("Select collection by number: ").strip()

    if choice == "0":
        return create_collection(session)

    try:
        idx = int(choice) - 1
        if 0 <= idx < len(collections):
            return load_collection(collections[idx], session)
    except Exception:
        pass

    print("Invalid selection.")
    return select_collection(session)