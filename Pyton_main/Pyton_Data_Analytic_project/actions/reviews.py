# actions/reviews.py

from pathlib import Path
from core.session_state import SessionState
from reviews_pipeline import collect_reviews_for_asins

def run_review_collection(session: SessionState):
    """
    Collect up to 500 reviews per ASIN via Scrapingdog and save to reviews.csv
    """
    if not session.has_asins():
        print("⚠️ No ASIN collection loaded.")
        return

    df_asins = session.df_asin
    if df_asins.empty:
        print("⚠️ ASIN list is empty.")
        return

    out_dir = session.collection_path
    if out_dir is None:
        print("❌ collection_path is not set in SessionState.")
        return

    marketplace = session.get_marketplace()
    collection_id = session.collection_id

    print(f"📦 Starting review collection for {len(df_asins)} ASINs via Scrapingdog...")
    df_reviews, stats = collect_reviews_for_asins(
        df_asin=df_asins,
        max_reviews_per_asin=500,
        marketplace=marketplace,
        out_dir=out_dir,
        collection_id=collection_id
    )

    print(f"\n[✓] Total reviews collected: {len(df_reviews)}")
    print(f"[📊] Reviews per category:")
    for cat, count in stats.items():
        print(f"   - {cat}: {count}")