# menu_main.py
# Main CLI menu interface for Amazon Intelligence Tool

from actions.reviews import run_review_collection
from actions.snapshots import run_daily_screening
from actions.plots import run_plotting
from actions.correlations import run_correlation_analysis
from core.session_state import SessionState
from actions.collections import select_collection
from core.env_check import ensure_env_ready

def main_menu():
    """Display the main menu and route user actions."""
    ensure_env_ready()

    session = SessionState()
    session.load_last_or_prompt()

    while True:
        print("\n=== Amazon Intelligence Tool ===")

        has_asins = session.has_asins()
        has_reviews = session.has_reviews()
        has_snapshots = session.has_snapshots(min_required=3)

        options = {}

        # Menu depends on current session state
        if not has_asins:
            print("No ASIN collection loaded.")
            print("1) Load or create ASIN collection")
            print("0) Exit")
        else:
            print(f"[Active collection: {session.collection_id}]")
            print("1) Load or create another ASIN collection")
            options["1"] = "Load or create ASIN collection"

            options["2"] = "Collect reviews (max 500 per ASIN)"
            print("2) Collect reviews (max 500 per ASIN)")

            if has_reviews:
                options["3"] = "Take snapshot: rating, price, review count"
                print("3) Take snapshot: rating, price, review count")

                options["4"] = "Plot review, rating, and sentiment dynamics"
                print("4) Plot review, rating, and sentiment dynamics")

            if has_snapshots:
                options["5"] = "Run correlation analysis"
                print("5) Run correlation analysis")

            options["6"] = "List saved collections"
            print("6) List saved collections")

            print("0) Exit")

        choice = input("> Enter choice: ").strip()

        if choice == "0":
            print("Goodbye!")
            break
        elif choice == "1":
            session = select_collection()
        elif choice == "2" and has_asins:
            run_review_collection(session)
        elif choice == "3" and has_reviews:
            run_daily_screening(session)
        elif choice == "4" and has_reviews:
            run_plotting(session)
        elif choice == "5" and has_snapshots:
            run_correlation_analysis(session)
        elif choice == "6":
            session.list_saved_collections()
        else:
            print("Invalid choice or unavailable option.")