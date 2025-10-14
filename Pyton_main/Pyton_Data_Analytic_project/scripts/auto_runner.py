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

    # Lazy imports after sys.path update
    from actions.reviews_controller import run_review_pipeline
    from analytics.daily import run_daily_screening
    from analytics.exporter import export_for_bi
    from core.auto_collect import RUNS_DIR, enabled_collections, save_state
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
            # Conditional daily screening (DP pages) before export
            try:
                # 1) If new reviews captured in this run
                new_cnt = int(stats.get("new_reviews", 0) or 0)
                # 2) If we have suspicious/missing price/bsr in latest snapshot
                bad_quality = False
                try:
                    snap = getattr(SESSION, "df_snapshot", None)
                    if snap is not None and len(getattr(snap, "columns", [])):
                        # Missing or placeholder price; or extreme outliers
                        def _price_bad(v) -> bool:
                            try:
                                if v is None:
                                    return True
                                s = str(v).strip()
                                if (
                                    not s
                                    or s.lower().find("click to see price") != -1
                                    or s.lower().find("see price") != -1
                                ):
                                    return True
                                # numeric sanity check
                                import re

                                num = re.sub(r"[^0-9\.,-]", "", s).replace(",", "")
                                if not num:
                                    return True
                                val = float(num)
                                return val <= 0 or val > 10000
                            except Exception:
                                return True

                        if "price" in snap.columns:
                            bad_quality = bad_quality or bool(snap["price"].apply(_price_bad).any())
                        if "bsr" in snap.columns:
                            try:
                                import pandas as pd

                                bsr_num = pd.to_numeric(snap["bsr"], errors="coerce")
                                bad_quality = bad_quality or bool(bsr_num.isna().any())
                            except Exception:
                                bad_quality = True
                except Exception:
                    bad_quality = True
                # 3) Once per calendar day marker
                marker = RUNS_DIR / f"daily_{entry.collection_id}.txt"
                today = datetime.utcnow().strftime("%Y-%m-%d")
                ran_today = False
                try:
                    if marker.exists():
                        ran_today = today in marker.read_text()
                except Exception:
                    ran_today = False

                need_daily = (new_cnt > 0) or bad_quality or (not ran_today)
                if need_daily:
                    print_info(
                        f"[auto] daily_screening due: new={new_cnt} bad_quality={bad_quality} ran_today={ran_today}"
                    )
                    try:
                        run_daily_screening(SESSION)
                        marker.parent.mkdir(parents=True, exist_ok=True)
                        marker.write_text(today)
                        print_success("[auto] daily_screening completed")
                    except Exception as dlex:
                        print_error(f"[auto] daily_screening failed: {dlex}")
            except Exception as ex_cond:
                print_error(f"[auto] daily_screening condition eval failed: {ex_cond}")
            try:
                out = export_for_bi(SESSION, prefer_parquet=True)
                print_success(f"[auto] export refreshed: {out}")
            except Exception as ex:
                print_error(f"[auto] export failed: {ex}")
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
