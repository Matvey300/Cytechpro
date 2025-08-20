# actions/menu_main.py

from typing import Dict, Any
from actions.reviews import collect_reviews
from actions.snapshots import snapshot_daily_metrics
from actions.plotting import plot_dynamics
from actions.correlation import run_correlation_tests
from actions.collections import list_saved_collections
from session_state import session
from utils.console import ask, info, warn


def get_menu_options(session: Dict[str, Any]) -> Dict[str, str]:
    """Returns available menu options based on current session state."""
    has_collection = session.get("df_asin") is not None
    has_reviews = has_collection and (session.get("review_count", 0) > 0)
    has_snapshots = session.get("snapshot_count", 0) >= 3

    options = {
        "1": "Collect reviews (up to 500 per ASIN)"
    }

    if has_reviews:
        options["2"] = "Take snapshot: rating, price, review count"
        options["3"] = "Plot review, rating, and sentiment dynamics"
    if has_snapshots:
        options["4"] = "Run correlation tests (requires ≥3 snapshots)"
    if has_collection:
        options["5"] = "List saved ASIN collections"

    options["0"] = "Exit"
    return options


def run_main_menu(session: Dict[str, Any]) -> None:
    """
    Entry point for main CLI menu.
    Adjusts visible options based on current session state.
    """
    while True:
        collection_id = session.get("collection_id") or "None"
        print(f"\n--- Amazon Review Monitor | Active Collection: {collection_id} ---")

        menu = get_menu_options(session)
        for key, label in menu.items():
            print(f"{key}) {label}")

        choice = ask("> Enter your choice: ").strip()

        if choice == "1":
            collect_reviews(session)
        elif choice == "2":
            snapshot_daily_metrics(session)
        elif choice == "3":
            plot_dynamics(session)
        elif choice == "4":
            run_correlation_tests(session)
        elif choice == "5":
            list_saved_collections(session)
        elif choice == "0":
            info("Goodbye!")
            return
        else:
            warn("Invalid or unavailable option. Please try again.")