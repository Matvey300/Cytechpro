from actions.asin_search import run_asin_search
from actions.correlations import run_correlation_analysis
from actions.reviews import run_review_collection
from actions.snapshots import run_daily_screening
from core.collection_io import select_collection
from core.env_check import validate_environment
from core.session_state import SessionState


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
        print("4) Take regular snapshot (price, rating, BSR)")
        print("5) Analyze and visualize reviews")
        print(
            "6) Run correlation analysis (price, rating, BSR) after accumulation of 30 days of regular snapshots"
        )
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
            if not session.is_collection_loaded():
                session.load_collection()
            if session.is_collection_loaded():
                run_daily_screening(session)
            else:
                print("[!] Failed to load a collection.")
        elif choice == "5":
            if not session.collection_path:
                session.load_collection()
            if not session.collection_path:
                print("[!] No collection loaded. Skipping analysis.")
                continue

            session.load_reviews_and_snapshot()
            if not session.has_reviews():
                print("[!] Reviews not loaded or empty. Skipping analysis.")
                continue

            from analytics.reaction_pulse import run_sentiment_analysis
            from analytics.review_authenticity import detect_suspicious_reviews

            detect_suspicious_reviews(session)
            run_sentiment_analysis(session.df_reviews)
        elif choice == "6":
            if not session.is_collection_loaded():
                print("[ℹ] No collection loaded. Select from saved collections:")
                session.load_collection()
            if not session.is_collection_loaded():
                print("[!] No collection selected. Returning to main menu.")
                continue
            session.load_reviews_and_snapshot()
            run_correlation_analysis(session)
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
