# core/env_check.py
from __future__ import annotations

import os
from pathlib import Path
from typing import Dict, List

from dotenv import load_dotenv

# ------------------------------
# Load .env files (do not override OS env)
# ------------------------------
PROJECT_ROOT = Path(__file__).resolve().parents[1]
ENV_CANDIDATES = [
    PROJECT_ROOT / "conf.env",  # project-local env (preferred)
    PROJECT_ROOT / ".env",  # optional local env
]

_loaded_files: List[str] = []
for f in ENV_CANDIDATES:
    if f.exists():
        load_dotenv(dotenv_path=f, override=False)
        _loaded_files.append(str(f))

# ------------------------------
# Export all environment variables at import time
# ------------------------------
ENV_VARS: Dict[str, str] = dict(os.environ)

# ------------------------------
# Modes & required variables
# ------------------------------
APP_MODE = os.getenv("APP_MODE", "prod").lower()
if APP_MODE == "test":
    REQUIRED_ENV_VARS = ["SCRAPINGDOG_API_KEY", "SERPAPI_API_KEY_TEST"]
else:  # prod & others
    REQUIRED_ENV_VARS = ["SCRAPINGDOG_API_KEY", "SERPAPI_API_KEY"]

OPTIONAL_ENV_VARS = [
    "CHROME_USER_DATA_DIR",
    "CHROME_PROFILE_DIR",
    "AMAZON_EMAIL",
    "REVIEWS_MAX_PAGES",
    "REVIEWS_MAX_PER_ASIN",
    "SAVE_RAW_HTML",
    "SAVE_PRODUCT_PNG",
    "CHROME_PROFILE",
]


def get_chrome_profile_env() -> str:
    """
    Returns the Chrome profile directory name from environment variables.
    Checks 'CHROME_PROFILE_DIR', then 'CHROME_PROFILE' (for backward compatibility), defaults to 'Default'.
    """
    return os.getenv("CHROME_PROFILE_DIR") or os.getenv("CHROME_PROFILE") or "Default"


def _mask(value: str | None, keep: int = 4) -> str:
    if not value:
        return ""
    if len(value) <= keep:
        return "*" * len(value)
    return value[:keep] + "…" + ("*" * max(0, len(value) - keep - 1))


def env_debug_report() -> None:
    """Print a short report where env was loaded from and what seems set (masked)."""
    print(f"[i] APP_MODE={APP_MODE}")
    if _loaded_files:
        print("[i] Loaded .env files:")
        for p in _loaded_files:
            print(f"   - {p}")
    else:
        print("[i] No .env files found next to project (looked for: conf.env, .env)")

    for var in ("SCRAPINGDOG_API_KEY", "SERPAPI_API_KEY", "SERPAPI_API_KEY_TEST"):
        val = os.getenv(var)
        status = "set" if val else "missing"
        masked = _mask(val) if val else ""
        print(f"[i] {var}: {status} {masked}")


def validate_environment() -> None:
    """Validate required environment variables for the current APP_MODE."""
    missing = [var for var in REQUIRED_ENV_VARS if not os.getenv(var)]
    if missing:
        print(f"[❌] Missing required environment variables (mode={APP_MODE}):")
        for var in missing:
            print(f" - {var}")
        print("[i] Looked for env files:")
        for cand in ENV_CANDIDATES:
            print(f"   - {cand}")
        print("[i] You can create 'conf.env' in project root with lines like:")
        if APP_MODE == "test":
            print("    SERPAPI_API_KEY_TEST=your_test_key_here")
        else:
            print("    SERPAPI_API_KEY=your_key_here")
        print("    SCRAPINGDOG_API_KEY=your_key_here")
        if APP_MODE == "prod":
            raise EnvironmentError("Required API keys are not configured")
        else:
            print("[⚠] Continuing in limited test mode (no hard failure).")
    else:
        for var in OPTIONAL_ENV_VARS:
            if not os.getenv(var):
                print_info(f"[⚠] Optional variable '{var}' is not set.")
        print(f"[✅] Environment OK (mode={APP_MODE})")


from core.log import print_error, print_info


def get_reviews_max_per_asin(default: int = 100) -> int:
    """
    Returns REVIEWS_MAX_PER_ASIN from environment, or fallback to default.
    """
    value = os.getenv("REVIEWS_MAX_PER_ASIN")
    if value is None:
        print_info("REVIEWS_MAX_PER_ASIN is not set. Using default: {}".format(default))
    try:
        return int(value)
    except (TypeError, ValueError):
        print_error(f"REVIEWS_MAX_PER_ASIN value '{value}' is invalid. Using default: {default}")
        return default


def get_env(key: str, default: str | None = None) -> str | None:
    """Convenience accessor for environment variables with default.
    Returns string or default if missing.
    """
    from os import getenv

    val = getenv(key)
    if val is None:
        return default
    return val


def get_env_bool(key: str, default: bool = False) -> bool:
    """Return boolean env (supports 1/0, true/false/yes/no)."""
    val = os.getenv(key)
    if val is None:
        return default
    s = val.strip().lower()
    if s in ("1", "true", "yes", "on"):  # enable
        return True
    if s in ("0", "false", "no", "off"):  # disable
        return False
    return default


__all__ = [
    "APP_MODE",
    "env_debug_report",
    "validate_environment",
    "get_chrome_profile_env",
    "ENV_VARS",
    "get_reviews_max_per_asin",
    "get_env",
    "get_env_bool",
    "print_info",
    "print_error",
]
