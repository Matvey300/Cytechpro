#!/usr/bin/env python3
"""
Lightweight daemon loop for auto-collection without cron/launchd.

- Reads DATA/.auto_collect.json
- Runs due collections via actions.reviews_controller.run_review_pipeline(interactive=False)
- Sleeps interval (default 900s) between checks

Stop by removing the lock file DATA/.locks/auto_daemon.lock or Ctrl+C in foreground.
"""
import sys
import time
from datetime import datetime
from pathlib import Path


def project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def main() -> int:
    root = project_root()
    sys.path.append(str(root))

    from actions.reviews_controller import run_review_pipeline
    from core.auto_collect import enabled_collections, lock_path, save_state
    from core.env_check import get_env
    from core.log import print_error, print_info, print_success
    from core.session_state import SESSION

    # Lock for daemon
    dlock = lock_path("auto_daemon")
    dlock.parent.mkdir(parents=True, exist_ok=True)
    if dlock.exists():
        print_info("[daemon] Already running (lock exists); exit")
        return 0
    dlock.write_text(datetime.utcnow().isoformat())

    interval = int(get_env("AUTO_DAEMON_INTERVAL_SEC", "900") or "900")
    print_info(f"[daemon] started; interval={interval}s")
    try:
        while True:
            try:
                entries = enabled_collections()
                changed = False
                for e in entries:
                    if not e.enabled:
                        continue
                    # due check
                    if not e.next_run:
                        due = True
                    else:
                        try:
                            due = datetime.utcnow() >= datetime.fromisoformat(e.next_run)
                        except Exception:
                            due = True
                    if not due:
                        continue
                    print_info(f"[daemon] running '{e.collection_id}'")
                    try:
                        SESSION.load_collection(e.collection_id)
                        df, stats = run_review_pipeline(SESSION, interactive=False)
                        print_success(
                            f"[daemon] done '{e.collection_id}': rows={len(df)} new={stats.get('new_reviews',0)} dup={stats.get('duplicates_skipped',0)} snaps={stats.get('snapshots',0)}"
                        )
                        e.mark_ran()
                        changed = True
                    except Exception as ex:
                        print_error(f"[daemon] failed '{e.collection_id}': {ex}")
                if changed:
                    save_state(entries)
            except Exception as loop_err:
                print_error(f"[daemon] loop error: {loop_err}")
            time.sleep(interval)
    finally:
        try:
            dlock.unlink(missing_ok=True)
        except Exception:
            pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
