# actions/menu_main.py
# Main CLI menu interface for Amazon Intelligence Tool

from actions.reviews import run_review_collection
from actions.snapshots import run_daily_screening
from actions.plots import run_plotting
from actions.correlations import run_correlation_analysis
from actions.collections import select_collection
from actions.asin_search import run_asin_search
from core.session_state import SessionState
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

        print(f"[Active collection: {session.collection_id or 'None'}]")
        if session.df_asin is not None:
            print(f"[ASINs loaded: {len(session.df_asin)}]")

        print("\nChoose an option:")
        print("1) 🔍 Search and import ASINs by keyword")
        print("2) 📂 Load or switch ASIN collection")
        if has_asins:
            print("3) 📝 Collect reviews (max 500 per ASIN)")
        if has_reviews:
            print("4) 📸 Take snapshot: rating, price, review count")
            print("5) 📈 Plot review, rating, and sentiment dynamics")
        if has_snapshots:
            print("6) 🧠 Run correlation analysis")
        print("7) 📋 List saved collections")
        print("0) ❌ Exit")

        choice = input("> Enter choice: ").strip()

        if choice == "0":
            print("Goodbye!")
            break
        elif choice == "1":
            session = run_asin_search()
        elif choice == "2":
            session = select_collection()
        elif choice == "3" and has_asins:
            run_review_collection(session)
        elif choice == "4" and has_reviews:
            run_daily_screening(session)
        elif choice == "5" and has_reviews:
            run_plotting(session)
        elif choice == "6" and has_snapshots:
            run_correlation_analysis(session)
        elif choice == "7":
            session.list_saved_collections()
        else:
            print("Invalid choice or unavailable option.")