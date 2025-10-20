import os
import time

import pandas as pd
import requests

# Scrapingdog API Key
API_KEY = "6888b22c09c987d9f10c066e"

# Search configuration
SEARCH_TERM = "bluetooth headphones"
COUNTRY_DOMAINS = {"us": "com", "uk": "co.uk", "de": "de"}
PAGES_PER_COUNTRY = 5

# Output configuration
OUTPUT_FOLDER = "DATA"
os.makedirs(OUTPUT_FOLDER, exist_ok=True)
OUTPUT_FILE = os.path.join(OUTPUT_FOLDER, "search_results.csv")


def extract_asin_from_url(url):
    try:
        parts = url.split("/dp/")
        if len(parts) > 1:
            return parts[1].split("/")[0]
    except:
        return None


def fetch_search_results(search_term, domain, page):
    query = search_term.replace(" ", "+")
    url = (
        f"https://api.scrapingdog.com/amazon/search?"
        f"api_key={API_KEY}&query={query}&domain={domain}&page={page}"
    )
    response = requests.get(url)
    print(f"Fetching domain={domain} page={page} — status: {response.status_code}")

    if response.status_code != 200:
        print("Error:", response.text)
        return []

    data = response.json().get("results", [])
    items = []

    for product in data:
        if product.get("type") != "search_product":
            continue

        asin = extract_asin_from_url(product.get("url", ""))
        if asin:
            items.append(
                {
                    "asin": asin,
                    "title": product.get("title"),
                    "rating": product.get("stars"),
                    "review_count": product.get("total_reviews"),
                    "country": domain,
                }
            )

    return items


# Main scraping loop
all_results = []

for country, domain in COUNTRY_DOMAINS.items():
    for page in range(1, PAGES_PER_COUNTRY + 1):
        try:
            results = fetch_search_results(SEARCH_TERM, domain, page)
            all_results.extend(results)
        except Exception as e:
            print(f"Error in {country.upper()} page {page}: {e}")
        time.sleep(1.5)

# Convert to DataFrame
df = pd.DataFrame(all_results)

# Exit if no data
if df.empty:
    print("⚠️ No data collected. Exiting.")
    exit()

# Clean and sort
df = df.drop_duplicates(subset="asin")
df["review_count"] = pd.to_numeric(df["review_count"].str.replace(",", ""), errors="coerce")
df = df.sort_values(by="review_count", ascending=False)

# Save top 100 to file
top_100 = df.head(100)
top_100.to_csv(OUTPUT_FILE, index=False)
print(f"✅ Saved {len(top_100)} ASINs to {OUTPUT_FILE}")
