# core/env_check.py

import os
from dotenv import load_dotenv
from pathlib import Path

# Load environment variables from conf.env
env_path = Path(__file__).parent.parent / "conf.env"
load_dotenv(dotenv_path=env_path)

REQUIRED_ENV_VARS = ["SCRAPINGDOG_API_KEY", "SERPAPI_API_KEY"]

def validate_environment():
    missing = [var for var in REQUIRED_ENV_VARS if not os.getenv(var)]
    if missing:
        print("[❌] Missing required environment variables:")
        for var in missing:
            print(f" - {var}")
        raise RuntimeError("Please set all required API keys as environment variables.")
    else:
        optional = ["CHROME_USER_DATA_DIR", "CHROME_PROFILE_DIR"]
        for var in optional:
            if not os.getenv(var):
                print(f"[⚠] Optional variable '{var}' is not set. Chrome login with profile may fail.")
        print("[✅] All required environment variables are set.")

def get_env_or_raise(var_name: str) -> str:
    value = os.getenv(var_name)
    if value is None:
        raise EnvironmentError(f"[❌] Environment variable '{var_name}' is not set.")
    return value