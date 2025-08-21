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

    if session.df_asin is None or session.df_asin.empty:
        print("⚠️ ASIN list is empty or not loaded.")
        return

    collection_dir = session.get_collection_dir()
    if collection_dir is None:
        print("⚠️ Collection directory not set.")
        return

    out_dir = Path(collection_dir)
    marketplace = session.get_marketplace()
    collection_id = session.collection_id

    print(f"[DEBUG] Output directory: {out_dir}")
    print(f"📦 Starting review collection for {len(session.df_asin)} ASINs via Scrapingdog...")

    # Optional debug: save df_asin to disk
    # session.df_asin.to_csv("DEBUG_collected_asins.csv", index=False)

    df_reviews, stats = collect_reviews_for_asins(
        df_asin=session.df_asin,
        max_reviews_per_asin=500,
        marketplace=marketplace,
        out_dir=out_dir,
        collection_id=collection_id
    )

    print(f"\n[✓] Total reviews collected: {len(df_reviews)}")
    print(f"[📊] Reviews per category:")
    for cat, count in stats.items():
        print(f"   - {cat}: {count}")