from pathlib import Path
import pandas as pd
from core.session_state import SessionState

COLLECTIONS_DIR = Path("collections")
COLLECTIONS_DIR.mkdir(exist_ok=True)

def list_collections() -> list[str]:
    return sorted([f.stem for f in COLLECTIONS_DIR.glob("*.csv")])

def create_collection(session: SessionState) -> SessionState:
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

    session.collection_id = name
    session.collection_path = path
    session.df_asin = df
    return session

def load_collection(name: str, session: SessionState) -> SessionState:
    path = COLLECTIONS_DIR / f"{name}.csv"
    if not path.exists():
        raise FileNotFoundError(f"No such collection: {name}")

    df = pd.read_csv(path)
    session.collection_id = name
    session.collection_path = path
    session.df_asin = df
    return session

def select_collection(session: SessionState) -> SessionState:
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

def save_collection(session: SessionState, collection_id: str, df: pd.DataFrame):
    collection_path = COLLECTIONS_DIR / f"{collection_id}.csv"
    collection_path.parent.mkdir(parents=True, exist_ok=True)  # Ensure directory exists
    df.to_csv(collection_path, index=False)
    session.collection_id = collection_id
    session.collection_path = collection_path
    session.df_asin = df