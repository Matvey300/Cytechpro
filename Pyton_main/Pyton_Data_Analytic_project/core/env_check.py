# core/env_check.py

import os
import sys

REQUIRED_ENV_VARS = [
    "SCRAPINGDOG_API_KEY",
    "SERPAPI_KEY"
]

def check_required_env_vars() -> None:
    """Print warnings and stop execution if env vars are missing (used in modules)."""
    missing = []
    for var in REQUIRED_ENV_VARS:
        if not os.getenv(var):
            print(f"[❌] Missing environment variable: {var}")
            missing.append(var)

    if missing:
        print("\n[⚠️] Set the missing environment variables before continuing.")
        print("You can define them via terminal export, or in a .env file.")
        sys.exit(1)  # Stop the app immediately
    else:
        print("[✅] All required environment variables are set.")


def validate_environment() -> None:
    """Raise exception if env vars are missing (used in app startup)."""
    missing = [var for var in REQUIRED_ENV_VARS if not os.getenv(var)]
    if missing:
        raise RuntimeError(
            f"Missing required environment variables: {', '.join(missing)}"
        )