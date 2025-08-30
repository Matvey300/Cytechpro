# app.py

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
