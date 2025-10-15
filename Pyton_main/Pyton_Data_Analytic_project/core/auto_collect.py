"""
# === Module Header ===
# 📁 Module: core/auto_collect.py
# 📅 Last Reviewed: 2025-10-15
# 🔧 Status: 🟢 Stable
# 👤 Owner: MatveyB
# 📝 Summary: Auto-collection state management and scheduling helpers.
# =====================
"""

from __future__ import annotations

import json
import random
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional

from core.log import print_error, print_info, print_success

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "DATA"
LOCKS_DIR = DATA_DIR / ".locks"
RUNS_DIR = DATA_DIR / "runs"
STATE_FILE = DATA_DIR / ".auto_collect.json"


def _now() -> datetime:
    return datetime.utcnow()


def _jitter(seconds: int = 600) -> int:
    """Return random jitter in seconds (default up to 10 minutes)."""
    return random.randint(0, max(1, seconds))


def ensure_dirs() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    LOCKS_DIR.mkdir(parents=True, exist_ok=True)
    RUNS_DIR.mkdir(parents=True, exist_ok=True)


@dataclass
class AutoEntry:
    collection_id: str
    enabled: bool = True
    frequency_per_day: int = 6  # default: ~every 4 hours
    last_run: Optional[str] = None  # ISO 8601 UTC
    next_run: Optional[str] = None  # ISO 8601 UTC

    def schedule_next(self, now: Optional[datetime] = None) -> None:
        now = now or _now()
        per_day = max(1, int(self.frequency_per_day or 6))
        interval_hours = 24 / per_day
        delta = timedelta(hours=interval_hours, seconds=_jitter(600))
        self.next_run = (now + delta).isoformat(timespec="seconds")

    def mark_ran(self, now: Optional[datetime] = None) -> None:
        now = now or _now()
        self.last_run = now.isoformat(timespec="seconds")
        self.schedule_next(now)


def load_state() -> List[AutoEntry]:
    ensure_dirs()
    if not STATE_FILE.exists():
        return []
    try:
        data = json.loads(STATE_FILE.read_text())
        entries = [AutoEntry(**e) for e in data.get("entries", [])]
        return entries
    except Exception as e:
        print_error(f"[auto] Failed to load state: {e}")
        return []


def save_state(entries: List[AutoEntry]) -> None:
    ensure_dirs()
    payload = {"version": 1, "entries": [asdict(e) for e in entries]}
    STATE_FILE.write_text(json.dumps(payload, indent=2))


def list_entries() -> List[AutoEntry]:
    return load_state()


def get_entry(collection_id: str) -> Optional[AutoEntry]:
    for e in load_state():
        if e.collection_id == collection_id:
            return e
    return None


def enable(collection_id: str, frequency_per_day: int = 6) -> AutoEntry:
    entries = load_state()
    existing = None
    for e in entries:
        if e.collection_id == collection_id:
            existing = e
            break
    if existing:
        existing.enabled = True
        existing.frequency_per_day = frequency_per_day
        # First run: 2 minutes after enabling
        existing.next_run = (_now() + timedelta(minutes=2)).isoformat(timespec="seconds")
        print_success(
            f"[auto] Enabled auto-collection for '{collection_id}' ({frequency_per_day}/day); first run in ~2 min"
        )
        save_state(entries)
        return existing
    entry = AutoEntry(
        collection_id=collection_id, enabled=True, frequency_per_day=frequency_per_day
    )
    # First run: 2 minutes after enabling
    entry.next_run = (_now() + timedelta(minutes=2)).isoformat(timespec="seconds")
    entries.append(entry)
    save_state(entries)
    print_success(
        f"[auto] Enabled auto-collection for '{collection_id}' ({frequency_per_day}/day); first run in ~2 min"
    )
    return entry


def disable(collection_id: str) -> bool:
    entries = load_state()
    changed = False
    for e in entries:
        if e.collection_id == collection_id:
            e.enabled = False
            changed = True
            break
    if changed:
        save_state(entries)
        print_info(f"[auto] Disabled auto-collection for '{collection_id}'")
    else:
        print_info(f"[auto] No auto-collection entry for '{collection_id}'")
    return changed


def enabled_collections() -> List[AutoEntry]:
    return [e for e in load_state() if e.enabled]


def lock_path(collection_id: str) -> Path:
    ensure_dirs()
    return LOCKS_DIR / f"{collection_id}.lock"


def runs_log_path(collection_id: str) -> Path:
    ensure_dirs()
    return RUNS_DIR / f"{collection_id}.jsonl"
