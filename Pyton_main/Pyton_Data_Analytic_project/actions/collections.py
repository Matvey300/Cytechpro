# actions/collections.py
# Logic for selecting or creating ASIN collections

import os
import pandas as pd
from pathlib import Path
from core.session_state import SessionState, SESSION

COLLECTIONS_DIR = Path("collections")
COLLECTIONS_DIR.mkdir(exist_ok=True)

def list_collections():
    return sorted([f.stem for f in COLLECTIONS_DIR.glob("*.csv")])

def load_collection(collection_id: str) -> SessionState:
    path = COLLECTIONS_DIR / f"{collection_id}.csv"
    if not path.exists():
        raise FileNotFoundError(f"Collection '{collection_id}' not found.")
    df = pd.read_csv(path)
    SESSION["collection_id"] = collection_id
    SESSION["collection_path"] = path.parent
    SESSION["df_asin"] = df
    return SessionState()

def create_collection() -> SessionState:
    name = input("Enter a name for the new ASIN collection: ").strip()
    path = COLLECTIONS_DIR / f"{name}.csv"

    asins = []
    while True:
        asin = input("Enter ASIN (or press Enter to finish): ").strip()
        if not asin:
            break
        asins.append({"asin": asin})

    df = pd.DataFrame(asins)
    df.to_csv(path, index=False)

    SESSION["collection_id"] = name
    SESSION["collection_path"] = path.parent
    SESSION["df_asin"] = df
    return SessionState()

def select_collection(session: SessionState = None) -> SessionState:
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
        new_session = create_collection()
        return new_session
    else:
        try:
            idx = int(choice) - 1
            if 0 <= idx < len(collections):
                selected = load_collection(collections[idx])
                return selected
        except Exception:
            pass

    print("Invalid selection.")
    return select_collection(session)