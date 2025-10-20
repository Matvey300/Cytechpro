#!/usr/bin/env bash
#############################################
# === Module Header ===
# 📁 Module: scripts/setup_cron.sh
# 📅 Last Reviewed: 2025-10-15
# 🔧 Status: 🟢 Stable
# 👤 Owner: MatveyB
# 📝 Summary: Installs cron entry to run auto_runner every 6 hours.
# =====================
#############################################
# Configure a cron job to run the auto_runner orchestrator.
# Usage: bash scripts/setup_cron.sh

set -euo pipefail
PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
VENV_PY="$PROJECT_DIR/venv/bin/python"
# Run at minute 5 every 6 hours
RUN_LINE="5 */6 * * * cd $PROJECT_DIR && $VENV_PY scripts/auto_runner.py >> $PROJECT_DIR/logs/collector.log 2>&1"

TMP_CRON=$(mktemp)
# Drop any existing auto_runner lines to avoid duplicates, then add the new one
crontab -l 2>/dev/null | grep -v "scripts/auto_runner.py" > "$TMP_CRON" || true
echo "$RUN_LINE" >> "$TMP_CRON"
crontab "$TMP_CRON"
rm -f "$TMP_CRON"
echo "[OK] Cron installed (every 6 hours): $RUN_LINE"
