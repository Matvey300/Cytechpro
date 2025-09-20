# === Module Status ===
# 📁 Module: actions/reviews_controller
# 📅 Last Reviewed: 2025-09-15
# 🔧 Status: 🛠️ Under Refactor (Planned)
# 👤 Owner: Matvey
# 📝 Notes:
# - Ensure collect_reviews_for_asins is imported and callable
# - Improve debug logging
# - Harmonize return values (df, stats) across project
# =====================

from pathlib import Path

import pandas as pd
from core.env_check import get_reviews_max_per_asin
from core.log import print_error, print_success
from core.session_state import print_info
from scraper.review_collector import collect_reviews_for_asins


def run_review_pipeline(session, max_reviews_per_asin=None, *, interactive: bool = True):
    max_reviews_per_asin = max_reviews_per_asin or get_reviews_max_per_asin()

    df_asin = session.df_asins
    marketplace = session.marketplace or "com"
    out_dir = Path(session.collection_path)

    if df_asin is None or df_asin.empty:
        print_info("[!] No ASINs loaded in session. Skipping review collection.")
        print_error("[LOG] Review pipeline aborted: no ASINs in session.")
        return pd.DataFrame(), {}

    print_info(f"[→] Collecting reviews for {len(df_asin)} ASINs in {marketplace}...")

    if not callable(collect_reviews_for_asins):
        print_info("[ERROR] collect_reviews_for_asins is not callable. Check import.")
        print_error("[LOG] Pipeline halted: collect_reviews_for_asins is not callable.")
        return pd.DataFrame(), {}

    df_reviews, stats = collect_reviews_for_asins(
        asins=df_asin["asin"].tolist(),
        max_reviews_per_asin=max_reviews_per_asin,
        marketplace=marketplace,
        out_dir=out_dir,
        collection_id=session.collection_id,
        session=session,
        interactive=interactive,
    )

    print_info(f"[✓] Collected {len(df_reviews)} reviews.")
    print_success(f"[LOG] Reviews collected and saved for {len(df_reviews)} entries")

    return df_reviews, stats
