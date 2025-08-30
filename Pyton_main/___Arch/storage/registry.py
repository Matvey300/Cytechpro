# All comments in English.

import json
from pathlib import Path


def load_registry(path: Path) -> list[dict]:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        return []
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return []


def save_registry(path: Path, data: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
