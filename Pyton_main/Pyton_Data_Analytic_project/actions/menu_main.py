from pathlib import Path
from core.env_check import validate_environment
from core.session_state import SessionState
from core.collection_io import select_collection
from actions.reviews import run_review_collection
from actions.snapshots import run_daily_screening
from actions.plots import run_plotting
from actions.correlations import run_correlation_analysis
from actions.asin_search import run_asin_search

def run_main_menu(session):
    while True:
        print("\n=== Amazon Intelligence Tool ===")
        if session.collection_id:
            print(f"[Active collection: {session.collection_id}]")
        else:
            print("No ASIN collection loaded.")

        print("1) Load or create ASIN collection")
        print("2) Collect reviews (max 500 per ASIN)")
        print("3) Search ASINs by keyword and category")
        print("4) Take daily snapshot (price, rating, BSR)")
        print("5) Plot review / rating / price dynamics")
        print("6) Run correlation analysis")
        print("7) List saved collections")
        print("0) Exit")

        choice = input(" > Enter choice: ").strip()

        if choice == "1":
            session.load_collection()
        elif choice == "2":
            if session.is_collection_loaded():
                run_review_collection(session)
            else:
                print("[!] Please load a valid collection first.")
        elif choice == "3":
            run_asin_search(session)
        elif choice == "4":
            if session.is_collection_loaded():
                run_daily_screening(session)
            else:
                print("[!] Please load a collection first.")
        elif choice == "5":
            if session.is_collection_loaded():
                run_plotting(session)
            else:
                print("[!] Please load a collection first.")
        elif choice == "6":
            if session.is_collection_loaded():
                run_correlation_analysis(session)
            else:
                print("[!] Please load a collection first.")
        elif choice == "7":
            session.list_available_collections()
        elif choice == "0":
            print("Exiting...")
            break
        else:
            print("[!] Invalid choice.")

def main_menu():
    from core.session_state import SESSION
    validate_environment()
    run_main_menu(SESSION)