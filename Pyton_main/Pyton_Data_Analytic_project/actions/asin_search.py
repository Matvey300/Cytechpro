import os

def validate_environment():
    required_vars = ["SCRAPINGDOG_API_KEY", "SERPAPI_API_KEY"]
    missing = [var for var in required_vars if not os.getenv(var)]

    if missing:
        print("[❌] Missing required environment variables:")
        for var in missing:
            print(f" - {var}")
        raise RuntimeError("Please set all required API keys as environment variables.")
    else:
        print("[✅] All required environment variables are set.")