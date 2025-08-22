import os
import pandas as pd
from pathlib import Path
from reviews_pipeline import collect_reviews_for_asins

def run_review_collection(session):
    """Run the review collection process using Scrapingdog API."""
    if session.df_asin is None or session.collection_path is None:
        print("❌ No ASIN collection loaded or active session not initialized.")
        return

    df_asins = session.df_asin
    collection_id = session.collection_id
    marketplace = session.get_marketplace()
    out_dir = Path("collections") / collection_id

    df_reviews, stats = collect_reviews_for_asins(
        df_asin=df_asins,
        max_reviews_per_asin=500,
        marketplace=marketplace,
        out_dir=out_dir,
        collection_id=collection_id
    )

    print(f"\n[✅] Review collection complete. Saved to: {(out_dir / 'reviews.csv')}")
    print(f"[📊] Review count by category:")
    for cat, count in stats.items():
        print(f" - {cat}: {count} reviews")