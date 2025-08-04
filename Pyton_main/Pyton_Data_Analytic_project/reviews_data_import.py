import requests
import pandas as pd
import time
from datetime import datetime, timedelta

# API key for Scrapingdog
SCRAPINGDOG_API_KEY = '6888b22c09c987d9f10c066e'

# List of top 100 ASINs
ASIN_LIST = [...]  # Replace with your actual ASIN list

# Amazon regional domain (e.g., 'us', 'uk', 'de')
COUNTRY = "us"

# Output file path
OUTPUT_FILE = "reviews_data.csv"

# Cutoff date: 24 months from today
CUTOFF_DATE = datetime.now() - timedelta(days=730)

# Function to request reviews from Scrapingdog
def fetch_reviews(asin):
    url = f"https://api.scrapingdog.com/amazon/reviews?api_key={SCRAPINGDOG_API_KEY}&type=review&asin={asin}&country={COUNTRY}"
    response = requests.get(url)

    if response.status_code != 200:
        print(f"Error while requesting ASIN {asin}: status code {response.status_code}")
        return []

    reviews = response.json().get("reviews", [])

    # Filter reviews by date
    filtered_reviews = [
        {
            "asin": asin,
            "review_date": r.get("review_date"),
            "rating": r.get("rating"),
            "title": r.get("title"),
            "content": r.get("content"),
            "author": r.get("author")
        }
        for r in reviews
        if r.get("review_date") and parse_date(r.get("review_date")) >= CUTOFF_DATE
    ]

    return filtered_reviews

# Function to parse various date formats
def parse_date(date_str):
    formats = ["%B %d, %Y", "%d %B %Y", "%Y-%m-%d"]
    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt)
        except:
            continue
    return datetime.min

# Main function to collect reviews
def collect_all_reviews():
    all_reviews = []

    for i, asin in enumerate(ASIN_LIST):
        print(f"[{i+1}/{len(ASIN_LIST)}] Fetching reviews for ASIN: {asin}")
        reviews = fetch_reviews(asin)
        all_reviews.extend(reviews)
        time.sleep(1.5)  # Delay between requests to respect API limits

    # Save results to CSV
    df = pd.DataFrame(all_reviews)
    df.to_csv(OUTPUT_FILE, index=False)
    print(f"Saved {len(df)} reviews to {OUTPUT_FILE}")

# Entry point
if __name__ == "__main__":
    collect_all_reviews()
