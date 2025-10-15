"""
# === Module Header ===
# 📁 Module: app.py
# 📅 Last Reviewed: 2025-10-15
# 🔧 Status: 🟢 Stable
# 👤 Owner: MatveyB
# 📝 Summary: CLI entrypoint. Validates env and launches main menu.
# =====================
"""

from actions.menu_main import main_menu
from core.env_check import validate_environment


def main():
    print("=" * 50)
    print("🔍 Amazon Review Intelligence Tool")
    print("Track review sentiment, ratings and price trends")
    print("Across your fixed ASIN sets — over time")
    print("=" * 50)

    # Environment check
    try:
        validate_environment()
    except RuntimeError as e:
        print(f"\n[ERROR] {e}")
        print("→ Please check your .env file or environment variables.")
        print("→ Refer to README.md → Environment Setup section.\n")
        return

    try:
        main_menu()
    except KeyboardInterrupt:
        print("\n[Interrupted by user]")


if __name__ == "__main__":
    main()
