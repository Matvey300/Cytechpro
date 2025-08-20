# menu_main.py

def display_main_menu(context):
    """
    Show the main menu options based on available data in session context.
    """
    print("\n=== Amazon Competitive Intelligence Tool ===")
    print(f"Current collection: {context.get('collection_id', 'None')}")
    print("---------------------------------------------")

    # Always available
    print("1) Collect reviews for ASINs (up to 500 per ASIN)")

    if context.get("collection_ready"):  # if asin list exists
        print("2) Run daily snapshot (track rating, price, review count)")

        if context.get("has_reviews"):
            print("3) Visualize review and rating dynamics over time")
            print("4) Reputation & price/BSR correlation analysis (requires 20+ snapshots)")
            print("5) Review authenticity audit (text length, verification, etc.)")
            print("6) Detect abnormal spikes in review activity")

        print("7) Show saved ASIN collections")

    print("0) Exit")

def get_menu_action():
    try:
        return input("\nEnter your choice: ").strip()
    except KeyboardInterrupt:
        return "0"