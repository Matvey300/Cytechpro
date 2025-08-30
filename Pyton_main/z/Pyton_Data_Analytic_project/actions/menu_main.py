# actions/menu_main.py

from actions.asin_search import run_asin_search
from actions.correlations import run_correlation_analysis
from actions.plots import run_plotting
from actions.reviews import run_review_collection
from actions.snapshots import run_daily_screening
from core.collection_io import select_collection
from core.env_check import validate_environment
from core.session_state import SessionState


def main_menu():
    validate_environment()
    session = SessionState()

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
            select_collection(session)
        elif choice == "2":
            if session.df_asin is not None:
                run_review_collection(session)
            else:
                print("[!] Please load a collection first.")
        elif choice == "3":
            run_asin_search(session)
        elif choice == "4":
            if session.df_asin is not None:
                run_daily_screening(session)
            else:
                print("[!] Please load a collection first.")
        elif choice == "5":
            if session.df_asin is not None:
                run_plotting(session)
            else:
                print("[!] Please load a collection first.")
        elif choice == "6":
            if session.df_asin is not None:
                run_correlation_analysis(session)
            else:
                print("[!] Please load a collection first.")
        elif choice == "7":
            print("Available collections:")
            data_dir = Path("DATA")
            if not data_dir.exists():
                print("[No collections found]")
            else:
                collections = [d.name for d in data_dir.iterdir() if d.is_dir()]
                for idx, name in enumerate(collections, 1):
                    print(f"{idx}) {name}")
        elif choice == "0":
            print("Exiting...")
            break
        else:
            print("[!] Invalid choice.")
