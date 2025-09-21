#!/usr/bin/env python3
import argparse
import json
import sys
import time
from datetime import datetime
from pathlib import Path


def project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser(description="Run review pipeline for a collection")
    parser.add_argument("--collection-id", required=True, help="Collection ID (folder id)")
    parser.add_argument("--max-reviews-per-asin", type=int, default=None)
    args = parser.parse_args()

    root = project_root()
    sys.path.append(str(root))

    from core.auto_collect import lock_path, runs_log_path
    from core.log import print_error, print_info, print_success

    # Lock
    lock = lock_path(args.collection_id)
    lock_dir = lock.parent
    lock_dir.mkdir(parents=True, exist_ok=True)
    if lock.exists():
        try:
            age = time.time() - lock.stat().st_mtime
        except Exception:
            age = 0
        if age < 2 * 60 * 60:
            print_info("[runner] Another run seems active; skipping")
            return 0
        else:
            try:
                lock.unlink(missing_ok=True)
            except Exception:
                pass
    try:
        lock.write_text(datetime.utcnow().isoformat())
    except Exception:
        pass

    start_ts = datetime.utcnow()
    try:
        from actions.reviews_controller import run_review_pipeline
        from core.session_state import SESSION

        SESSION.load_collection(args.collection_id)
        df, stats = run_review_pipeline(
            SESSION, max_reviews_per_asin=args.max_reviews_per_asin, interactive=False
        )
        print_success(
            f"[runner] completed: rows={len(df)} new={stats.get('new_reviews', 0)} dup={stats.get('duplicates_skipped', 0)} snaps={stats.get('snapshots', 0)}"
        )

        # Append JSONL run summary
        run_path = runs_log_path(args.collection_id)
        summary = {
            "collection_id": args.collection_id,
            "started_at": start_ts.isoformat(timespec="seconds"),
            "finished_at": datetime.utcnow().isoformat(timespec="seconds"),
            "rows": int(len(df)),
            "new_reviews": int(stats.get("new_reviews", 0)),
            "duplicates_skipped": int(stats.get("duplicates_skipped", 0)),
            "snapshots": int(stats.get("snapshots", 0)),
        }
        run_path.parent.mkdir(parents=True, exist_ok=True)
        with open(run_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(summary) + "\n")

        return 0
    except Exception as e:
        print_error(f"[runner] failed: {e}")
        return 1
    finally:
        try:
            lock.unlink(missing_ok=True)
        except Exception:
            pass


if __name__ == "__main__":
    raise SystemExit(main())
