import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ENTRYPOINT_HINTS = {"menu_main.py", "app.py", "pipeline.py", "reviews_pipeline.py", "__init__.py"}
import_re = re.compile(r"^\s*(?:from\s+([\w\.]+)\s+import|import\s+([\w\.]+))", re.M)


def all_py(root: Path):
    skip = {"venv", ".venv", ".git", "site-packages", "archive"}
    return [p for p in root.rglob("*.py") if not any(s in p.parts for s in skip)]


def mod_name(root: Path, file: Path) -> str:
    rel = file.relative_to(root).as_posix()[:-3]
    return rel.replace("/", ".")


def parse_imports(text: str):
    mods = set()
    for m in import_re.finditer(text):
        g = m.group(1) or m.group(2)
        if g:
            mods.add(g.split(".")[0])
    return mods


def main():
    files = all_py(ROOT)
    name_by_file = {f: mod_name(ROOT, f) for f in files}
    file_by_topname = {n.split(".")[0]: f for f, n in name_by_file.items()}
    graph = {name_by_file[f]: set() for f in files}

    for f in files:
        try:
            text = f.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        imps = parse_imports(text)
        me = name_by_file[f]
        for imp in imps:
            if imp in file_by_topname:
                graph[me].add(imp)

    incoming = {n: 0 for n in graph}
    for src, outs in graph.items():
        for dst in outs:
            if dst in incoming:
                incoming[dst] += 1

    orphans = []
    for f, n in name_by_file.items():
        top = n.split(".")[0]
        if f.name in ENTRYPOINT_HINTS:
            continue
        if incoming.get(top, 0) == 0:
            orphans.append(f)

    print("# Candidate orphan modules:")
    for f in sorted(orphans):
        print(f)
    print("\n# Total:", len(orphans))
    return 0


if __name__ == "__main__":
    sys.exit(main())
PY
