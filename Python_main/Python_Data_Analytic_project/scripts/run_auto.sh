#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
LOG_DIR="logs"
mkdir -p "$LOG_DIR"
./venv/bin/python scripts/auto_runner.py >> "$LOG_DIR/collector.log" 2>&1

