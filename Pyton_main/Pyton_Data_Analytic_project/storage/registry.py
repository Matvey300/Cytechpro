# All comments in English.

from pathlib import Path
import json

def load_registry(path: Path) -> list[dict]:
    """Load registry.json or return empty list."""
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        return []
    try:
        return json.loads(path.read_text(encoding='utf-8'))
    except Exception:
        return []

def save_registry(path: Path, data: list[dict]) -> None:
    """Persist registry.json."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')