#!/usr/bin/env python3
import sys
from datetime import datetime
from pathlib import Path


def project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def due(entry) -> bool:
    if not entry.enabled:
        return False
    if not entry.next_run:
        return True
    try:
        next_dt = datetime.fromisoformat(entry.next_run)
    except Exception:
        return True
    return datetime.utcnow() >= next_dt


def main() -> int:
    root = project_root()
    sys.path.append(str(root))

    from actions.reviews_controller import run_review_pipeline
    from core.auto_collect import enabled_collections, save_state
    from core.log import print_error, print_info, print_success
    from core.session_state import SESSION

    entries = enabled_collections()
    if not entries:
        print_info("[auto] No enabled collections; exiting")
        return 0

    changed = False
    for entry in entries:
        if not due(entry):
            continue
        try:
            print_info(f"[auto] Running pipeline for '{entry.collection_id}'")
            SESSION.load_collection(entry.collection_id)
            df, stats = run_review_pipeline(SESSION, interactive=False)
            print_success(
                f"[auto] done '{entry.collection_id}': rows={len(df)} new={stats.get('new_reviews', 0)} dup={stats.get('duplicates_skipped', 0)} snaps={stats.get('snapshots', 0)}"
            )
            entry.mark_ran()
            changed = True
        except Exception as e:
            print_error(f"[auto] failed for '{entry.collection_id}': {e}")
    if changed:
        # Persist updated next_run/last_run
        state = [e for e in entries]
        save_state(state)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
