import os
import time

import pandas as pd
import requests

API_KEY = "6888b22c09c987d9f10c066e"
REVIEWS_PER_ASIN = 20
INPUT_FILE = "DATA/search_results.csv"
OUTPUT_FILE = "DATA/reviews_test.csv"

# Ensure DATA directory exists
os.makedirs("DATA", exist_ok=True)


def fetch_reviews(asin, country="us", max_reviews=20):
    url = (
        f"https://api.scrapingdog.com/amazon/reviews"
        f"?api_key={API_KEY}&asin={asin}&country={country}"
    )
    response = requests.get(url)
    if response.status_code != 200:
        print(f"Error fetching reviews for ASIN {asin}: {response.status_code}")
        return []

    data = response.json().get("reviews", [])
    reviews = []

    for review in data[:max_reviews]:
        reviews.append(
            {
                "asin": asin,
                "review_date": review.get("review_date"),
                "rating": review.get("rating"),
                "title": review.get("title"),
                "content": review.get("content"),
                "author": review.get("author"),
            }
        )

    return reviews


# Load 2 ASINs (US only)
df_asins = pd.read_csv(INPUT_FILE)
df_asins = df_asins[df_asins["country"] == "com"]
test_asins = ["B08WM3LMJF", "B09FT58QQP"]


# Collect reviews
all_reviews = []

for i, asin in enumerate(test_asins):
    print(f"[{i+1}/2] Fetching reviews for ASIN: {asin}")
    try:
        reviews = fetch_reviews(asin, country="us", max_reviews=REVIEWS_PER_ASIN)
        all_reviews.extend(reviews)
    except Exception as e:
        print(f"Exception for ASIN {asin}: {e}")
    time.sleep(1.5)

# Save test results
df_reviews = pd.DataFrame(all_reviews)
df_reviews.to_csv(OUTPUT_FILE, index=False)
print(f"✅ Saved {len(df_reviews)} reviews to {OUTPUT_FILE}")
