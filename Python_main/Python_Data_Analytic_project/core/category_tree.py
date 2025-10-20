# core/category_tree.py

"""
Loads the static Amazon category tree from a local JSON file.
Used for keyword-to-category mapping without calling SerpAPI.
"""

import json
from pathlib import Path

CATEGORY_FILE = Path(__file__).parent / "amazon_categories_us.json"

try:
    with open(CATEGORY_FILE, "r", encoding="utf-8") as f:
        CATEGORY_TREE = json.load(f)
except Exception as e:
    print(f"[ERROR] Failed to load category tree: {e}")
    CATEGORY_TREE = {}
"""
# === Module Header ===
# 📁 Module: core/category_tree.py
# 📅 Last Reviewed: 2025-10-15
# 🔧 Status: 🟢 Stable
# 👤 Owner: MatveyB
# 📝 Summary: Utilities to handle category paths and hierarchy operations.
# =====================
"""
