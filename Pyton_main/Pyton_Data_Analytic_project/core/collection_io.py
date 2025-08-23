from pathlib import Path
import pandas as pd
from core.session_state import SessionState

COLLECTIONS_DIR = Path("collections")
COLLECTIONS_DIR.mkdir(exist_ok=True)

def list_collections() -> list[str]:
    valid_collections = []
    for collection_dir in COLLECTIONS_DIR.iterdir():
        if not collection_dir.is_dir():
            continue
        review_files = list(collection_dir.glob(f"*__{collection_dir.name}__reviews.csv"))
        if review_files:
            valid_collections.append(collection_dir.name)
    return sorted(valid_collections)

def create_collection(session: SessionState) -> SessionState:
    name = input("Enter a name for the new ASIN collection: ").strip()
    if not name:
        print("[WARN] Collection name cannot be empty.")
        return create_collection(session)

    path = COLLECTIONS_DIR / name
    if path.exists():
        print("[WARN] Collection already exists.")
        return create_collection(session)

    path.mkdir(parents=True, exist_ok=True)
    df = pd.DataFrame(columns=["asin", "title", "rating", "review_count", "country", "category_path"])
    df.to_csv(path / f"{name}.csv", index=False)
    print(f"[✅] Created new collection: {name}")

    session.collection_id = name
    session.collection_path = path
    session.df_asin = df
    return session

def load_collection(name: str, session: SessionState) -> SessionState:
    session.load_collection(name)
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
    collection_path = COLLECTIONS_DIR / collection_id
    if collection_path.exists() and not collection_path.is_dir():
        collection_path.unlink()  # удалить файл, чтобы освободить путь для папки
    collection_path.mkdir(parents=True, exist_ok=True)
    df.to_csv(collection_path / f"{collection_id}.csv", index=False)
    session.collection_id = collection_id
    session.collection_path = collection_path
    session.df_asin = df