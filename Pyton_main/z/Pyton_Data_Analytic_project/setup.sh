#!/usr/bin/env bash
# Robust venv setup for Pyton_Data_Analytic_project
# - Uses Homebrew Python if available, otherwise falls back to python3 on PATH
# - Installs pinned dependencies from requirements.txt (creates one if missing)
# - Verifies imports with clear errors (no raw tracebacks)

set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$PROJECT_ROOT"

echo "==> Detecting Python..."
if [ -x /opt/homebrew/bin/python3 ]; then
  PYTHON=/opt/homebrew/bin/python3
else
  PYTHON=$(command -v python3 || true)
fi

if [ -z "${PYTHON:-}" ]; then
  echo "ERROR: python3 not found. Please install Python 3 (e.g., 'brew install python')."
  exit 1
fi

echo "Using Python at: $PYTHON"
echo "Python version: $($PYTHON -V)"

VENV_DIR="venv"

echo "==> Removing existing venv (if any)..."
rm -rf "$VENV_DIR"

echo "==> Creating fresh venv..."
"$PYTHON" -m venv "$VENV_DIR"

# shellcheck disable=SC1091
source "$VENV_DIR/bin/activate"

echo "==> Upgrading base tooling (pip, wheel, setuptools)..."
python -m pip install -U pip wheel setuptools

REQ_FILE="requirements.txt"
if [ ! -f "$REQ_FILE" ]; then
  echo "==> requirements.txt not found. Creating a default one..."
  cat > "$REQ_FILE" <<'REQS'
numpy>=2.2
pandas>=2.2,<3.0
matplotlib
scikit-learn
requests
beautifulsoup4
vaderSentiment
serpapi
REQS
fi

echo "==> Installing project dependencies from requirements.txt..."
PYTHONNOUSERSITE=1 python -m pip install --no-cache-dir -r "$REQ_FILE"

echo "==> Verifying imports (with clear messages)..."
python - <<'PY'
import sys, importlib

mods = [
    ("numpy", "numpy"),
    ("pandas", "pandas"),
    ("VADER", "vaderSentiment"),
    ("requests", "requests"),
    ("matplotlib", "matplotlib"),
    ("scikit-learn", "sklearn"),
    ("BeautifulSoup (bs4)", "bs4"),
    ("serpapi", "serpapi"),
]

missing = []
print("Python:", sys.executable)
for label, name in mods:
    try:
        importlib.import_module(name)
        print(f"{label}: OK")
    except Exception as e:
        missing.append((label, name, str(e)))

if missing:
    print("\nERROR: Some modules failed to import:")
    for label, name, err in missing:
        print(f"  - {label} [{name}]: {err}")
    print("\nTry re-installing dependencies:")
    print("  PYTHONNOUSERSITE=1 python -m pip install --no-cache-dir -r requirements.txt")
    sys.exit(1)
else:
    print("All imports OK.")
PY

echo
echo "✅ Virtual environment is ready."
echo "Next steps:"
echo "  1) Activate venv:   source venv/bin/activate"
echo "  2) Run the app:     python app.py"
echo