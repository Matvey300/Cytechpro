#!/usr/bin/env bash
# Configure an hourly cron job to run the auto_runner orchestrator.
# Usage: bash scripts/setup_cron.sh

set -euo pipefail
PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
VENV_PY="$PROJECT_DIR/venv/bin/python"
RUN_LINE="5 * * * * cd $PROJECT_DIR && $VENV_PY scripts/auto_runner.py >> $PROJECT_DIR/logs/collector.log 2>&1"

TMP_CRON=$(mktemp)
crontab -l 2>/dev/null > "$TMP_CRON" || true
grep -F "$RUN_LINE" "$TMP_CRON" >/dev/null 2>&1 || echo "$RUN_LINE" >> "$TMP_CRON"
crontab "$TMP_CRON"
rm -f "$TMP_CRON"
echo "[OK] Cron installed: $RUN_LINE"

