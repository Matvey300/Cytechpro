from actions.reviews_controller import run_review_pipeline

try:
    from core.env_check import validate_environment
except Exception as e:
    import traceback

    print(f"[!] Failed to import validate_environment: {e}")
    traceback.print_exc()

    def validate_environment():
        print("[!] Environment validation unavailable")


def _ensure_collection(session) -> bool:
    """Try to ensure a collection is loaded. Returns True if loaded, else False."""
    try:
        if not session.is_collection_loaded():
            session.load_collection()
        return session.is_collection_loaded()
    except Exception:
        # Fallback for older SessionState without is_collection_loaded
        return bool(getattr(session, "collection_path", None))


def run_main_menu(session):
    while True:
        print("\n=== Amazon Intelligence Tool ===")
        if _ensure_collection(session):
            print("[Collection]")
            print(
                f"ID: {getattr(session, 'collection_id', None)} | Created: {getattr(session, 'created_date', None)} | Last snapshot: {getattr(session, 'last_snapshot_date', None)}"
            )
            print(f"Folder: {getattr(session, 'collection_path', None)}")
            # Show auto-collect status
            try:
                from core.auto_collect import get_entry

                e = get_entry(getattr(session, "collection_id", ""))
                if e and e.enabled:
                    print(
                        f"Auto-collection: ENABLED ({e.frequency_per_day}/day) | next: {e.next_run}"
                    )
                else:
                    print("Auto-collection: disabled")
            except Exception:
                pass
        else:
            print("No ASIN collection loaded.")

        print("1) Load or create ASIN collection")
        print("2) Search ASINs by keyword and category")
        print("3) Collect reviews & snapshot (creates or appends to reviews.csv and snapshot.csv)")
        print("4) Analyze and visualize reviews")
        print("5) List saved collections")
        print("6) Auto-collection settings")
        print("0) Exit")

        choice = input(" > Enter choice: ").strip()

        if choice == "1":
            # Numeric sub-menu to avoid ambiguous letters
            while True:
                print("\n[1] Load existing collection")
                print("[2] Create new collection (keyword → categories → ASIN)")
                print("[0] Back")
                sub = input(" > Enter choice: ").strip()
                if sub == "1":
                    session.load_collection()
                    # Offer enabling auto-collection immediately after loading
                    try:
                        if session.is_collection_loaded():
                            from core.auto_collect import enable, get_entry

                            cid = getattr(session, "collection_id", None)
                            e = get_entry(cid) if cid else None
                            if cid and (not e or not e.enabled):
                                ans = (
                                    input("Enable auto-collection for this collection now? [y/N]: ")
                                    .strip()
                                    .lower()
                                )
                                if ans in ("y", "yes"):
                                    enable(cid)
                    except Exception:
                        pass
                    break
                elif sub == "2":
                    try:
                        from actions.asin_controller import run_asin_search as create_flow

                        create_flow(session)
                    except Exception as e:
                        print(f"[!] Create flow failed: {e}")
                    break
                elif sub == "0":
                    break
                else:
                    print("[!] Invalid choice.")
        elif choice == "2":
            # Search ASINs by keyword and category (can create or update collection)
            try:
                from actions.asin_controller import run_asin_search

                run_asin_search(session)
            except Exception as e:
                print(f"[!] ASIN search failed: {e}")
        elif choice == "3":
            # Collect reviews & snapshot
            if not _ensure_collection(session):
                print("[!] Please load a valid collection first.")
            else:
                try:
                    from core.env_check import get_reviews_max_per_asin

                    df_reviews, stats = run_review_pipeline(
                        session, max_reviews_per_asin=get_reviews_max_per_asin()
                    )
                    print(
                        "[✓] Review collection completed. "
                        f"rows_collected={len(df_reviews)}; new_reviews={stats.get('new_reviews', 0)}; "
                        f"duplicates_skipped={stats.get('duplicates_skipped', 0)}; snapshots={stats.get('snapshots', 0)}"
                    )
                except Exception as e:
                    print(f"[!] Failed to run review pipeline: {e}")
        elif choice == "4":
            # Analyze and visualize reviews
            if not _ensure_collection(session):
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
                print("[!] Analytics modules are unavailable. Skipping.")
                continue

            try:
                detect_suspicious_reviews(session)
                run_sentiment_analysis(session.df_reviews)
            except Exception as e:
                print(f"[!] Analytics failed: {e}")
        elif choice == "5":
            session.list_available_collections()
        elif choice == "6":
            auto_menu(session)
        elif choice == "0":
            print("Exiting...")
            break
        else:
            print("[!] Invalid choice.")


def main_menu():
    try:
        from core.session_state import SESSION
    except Exception as e:
        import traceback

        print(f"[!] SESSION object unavailable: {e}")
        traceback.print_exc()
        return

    try:
        validate_environment()
    except Exception:
        print("[!] Environment validation failed/skipped.")

    run_main_menu(SESSION)


def auto_menu(session):
    from core.auto_collect import disable, enable, get_entry, list_entries

    while True:
        print("\n=== Auto-collection ===")
        cid = getattr(session, "collection_id", None)
        if cid:
            e = get_entry(cid)
            status = "ENABLED" if (e and e.enabled) else "disabled"
            print(f"Current collection: {cid} | auto: {status}")
        else:
            print("Current collection: none loaded")
        print("1) Enable for current collection (default 6/day)")
        print("2) Disable for current collection")
        print("3) List all enabled collections")
        print("4) Run now for current collection")
        print("0) Back")
        sel = input(" > Enter choice: ").strip()
        if sel == "1":
            if not cid:
                print("[!] Load a collection first.")
                continue
            freq = input("Frequency per day [6]: ").strip()
            try:
                f = int(freq) if freq else 6
            except Exception:
                f = 6
            enable(cid, f)
        elif sel == "2":
            if not cid:
                print("[!] Load a collection first.")
                continue
            disable(cid)
        elif sel == "3":
            entries = [e for e in list_entries() if e.enabled]
            if not entries:
                print("[i] No enabled collections.")
            else:
                for i, e in enumerate(entries, 1):
                    print(
                        f"{i}) {e.collection_id} | {e.frequency_per_day}/day | next: {e.next_run} | last: {e.last_run}"
                    )
        elif sel == "4":
            if not cid:
                print("[!] Load a collection first.")
                continue
            try:
                from actions.reviews_controller import run_review_pipeline
                from core.env_check import get_reviews_max_per_asin

                df, stats = run_review_pipeline(
                    session, max_reviews_per_asin=get_reviews_max_per_asin()
                )
                print(
                    "[✓] Manual run completed. "
                    f"rows_collected={len(df)}; new_reviews={stats.get('new_reviews', 0)}; "
                    f"duplicates_skipped={stats.get('duplicates_skipped', 0)}; snapshots={stats.get('snapshots', 0)}"
                )
            except Exception as e:
                print(f"[!] Manual run failed: {e}")
        elif sel == "0":
            break
        else:
            print("[!] Invalid choice.")
