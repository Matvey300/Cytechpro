# core/collection_io.py

from pathlib import Path
import pandas as pd
from core.session_state import SessionState

COLLECTIONS_DIR = Path("collections")
COLLECTIONS_DIR.mkdir(exist_ok=True)

def list_collections() -> list[str]:
    return sorted([f.stem for f in COLLECTIONS_DIR.glob("*.csv")])

def create_collection() -> SessionState:
    name = input("Enter a name for the new ASIN collection: ").strip()
    if not name:
        print("[WARN] Collection name cannot be empty.")
        return create_collection()
    
    path = COLLECTIONS_DIR / f"{name}.csv"
    if path.exists():
        print("[WARN] Collection already exists.")
        return create_collection()
    
    df = pd.DataFrame(columns=["asin", "title", "rating", "review_count", "country", "category_path"])
    df.to_csv(path, index=False)
    print(f"[✅] Created new collection: {name}")
    return SessionState(df_asin=df, collection_name=name, collection_path=path)

def load_collection(name: str) -> SessionState:
    path = COLLECTIONS_DIR / f"{name}.csv"
    if not path.exists():
        raise FileNotFoundError(f"No such collection: {name}")
    
    df = pd.read_csv(path)
    return SessionState(df_asin=df, collection_name=name, collection_path=path)


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
            return load_collection(session, collections[idx])
    except Exception:
        pass

    print("Invalid selection.")
    return select_collection(session)