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
        print("[✅] All required environment variables are set.")