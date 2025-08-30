from core.session_state import SessionState

try:
    from actions.asin_search import run_asin_search
except Exception:
    run_asin_search = None
try:
    from actions.correlations import run_correlation_analysis
except Exception:
    run_correlation_analysis = None
try:
    from actions.reviews import run_review_collection
except Exception:
    run_review_collection = None
try:
    from actions.snapshots import run_daily_screening
except Exception:
    run_daily_screening = None
try:
    from core.collection_io import select_collection
except Exception:
    select_collection = None
try:
    from core.env_check import validate_environment
except Exception:
    def validate_environment():
        print("[!] Environment validation unavailable")


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
            if run_review_collection is None:
                print("[!] Reviews module is temporarily unavailable (archived). Skipping.")
            else:
                if session.is_collection_loaded():
                    run_review_collection(session)
                else:
                    print("[!] Please load a valid collection first.")
        elif choice == "3":
            if run_asin_search is None:
                print("[!] ASIN search module is temporarily unavailable (archived). Skipping.")
            else:
                run_asin_search(session)
        elif choice == "4":
            if run_daily_screening is None:
                print("[!] Snapshot module is temporarily unavailable (archived). Skipping.")
            else:
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

            try:
                from analytics.reaction_pulse import run_sentiment_analysis
                from analytics.review_authenticity import detect_suspicious_reviews
            except Exception:
                print("[!] Analytics modules are temporarily unavailable (archived). Skipping.")
                continue

            try:
                detect_suspicious_reviews(session)
                run_sentiment_analysis(session.df_reviews)
            except Exception as e:
                print(f"[!] Analytics failed: {e}")
        elif choice == "6":
            if not session.is_collection_loaded():
                print("[ℹ] No collection loaded. Select from saved collections:")
                session.load_collection()
            if not session.is_collection_loaded():
                print("[!] No collection selected. Returning to main menu.")
                continue
            session.load_reviews_and_snapshot()
            if run_correlation_analysis is None:
                print("[!] Correlation analysis module is temporarily unavailable (archived). Skipping.")
            else:
                run_correlation_analysis(session)
        elif choice == "7":
            session.list_available_collections()
        elif choice == "0":
            print("Exiting...")
            break
        else:
            print("[!] Invalid choice.")


def main_menu():
    try:
        from core.session_state import SESSION
    except Exception:
        print("[!] SESSION object unavailable: cannot start main menu.")
        return

    try:
        validate_environment()
    except Exception:
        print("[!] Environment validation failed/skipped.")

    run_main_menu(SESSION)
