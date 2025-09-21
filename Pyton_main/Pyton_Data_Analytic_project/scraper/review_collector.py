# === Module Status ===
# 📁 Module: scraper/review_collector
# 📅 Last Reviewed: 2025-09-18
# 🔧 Status: 🟢 Stable (Controller-aligned)
# 👤 Owner: Matvey
# 📝 Notes:
# - Interface aligned with actions/reviews_controller.run_review_pipeline
# - Uses open_reviews_page + _next_page_with_max_guard for pagination
# - Saves HTML under collection Raw/reviews/<run_ts>/<asin>
# - Persists via core.collection_io (dedup handled)
# =====================

import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Tuple

import pandas as pd
from bs4 import BeautifulSoup
from core.auth_amazon import (
    _manual_login_prompt_loop,
    get_amazon_credentials,
    is_logged_in,
    open_amazon_home,
    perform_amazon_login,
    resolve_amazon_interstitials,
)
from core.collection_io import reviews_csv, save_reviews, save_snapshot
from core.env_check import ENV_VARS
from core.log import print_error, print_info, print_success
from scraper.driver import init_driver
from scraper.html_saver import save_html
from scraper.navigator import _next_page_with_max_guard, navigate_to_reviews
from scraper.page_parser import extract_total_reviews
from scraper.product_info import extract_product_details
from scraper.review_parser import extract_reviews_from_html
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


def _get_row_for_asin(session, asin: str):
    try:
        if session is None or getattr(session, "df_asins", None) is None:
            return None
        df = session.df_asins
        if "asin" not in df.columns:
            return None
        sub = df[df["asin"].astype(str) == str(asin)]
        return sub.iloc[0] if not sub.empty else None
    except Exception:
        return None


def collect_reviews_for_asins(
    asins: list,
    max_reviews_per_asin: int,
    marketplace: str | None = None,
    out_dir: Path | None = None,
    collection_id: str | None = None,
    session=None,
    interactive: bool = True,
) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """Collect reviews and snapshot data for a list of ASINs.

    Args:
        asins: List of ASINs to collect reviews for.
        max_reviews_per_asin: Maximum reviews to extract per ASIN.
        marketplace: Marketplace TLD (e.g., "com"). If None, tries session.marketplace.
        out_dir: Base output directory (falls back to session.collection_path).
        collection_id: Optional collection identifier (fallback path helper).
        session: SessionState with df_asins and collection_path for persistence.

    Returns:
        (df_reviews, stats_dict)
    """

    # Resolve marketplace and directories
    mp = (marketplace or getattr(session, "marketplace", None) or "com").strip()
    run_ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")

    def _current_raw_root() -> Path:
        """Resolve Raw/reviews/<run_ts> against the current collection path.
        This guards against mid-run folder renames performed by save_snapshot().
        """
        base = (
            (
                Path(getattr(session, "collection_path", ""))
                if getattr(session, "collection_path", None)
                else None
            )
            or (Path(out_dir) if out_dir else None)
            or (
                Path("Pyton_main/Pyton_Data_Analytic_project/DATA")
                / (collection_id or "UNKNOWN_COLLECTION")
            )
        )
        base.mkdir(parents=True, exist_ok=True)
        return base / "Raw" / "reviews" / run_ts

    def _wait_for_reviews(driver, timeout: int = 12) -> bool:
        """Wait until the reviews container or review blocks are present.
        Returns True if found, False otherwise.
        """
        try:
            WebDriverWait(driver, timeout).until(
                EC.presence_of_element_located(
                    (By.CSS_SELECTOR, "#cm_cr-review_list, div[data-hook='review']")
                )
            )
            return True
        except Exception:
            return False

    # Start browser (user data dir optional)
    user_data_dir = ENV_VARS.get("CHROME_USER_DATA_DIR")
    driver = init_driver(user_data_dir)

    # Ensure we are logged into Amazon (auto-login if creds, else prompt user)
    try:
        open_amazon_home(driver)
        resolve_amazon_interstitials(driver)
        if not is_logged_in(driver):
            email, pwd = get_amazon_credentials()
            if email and pwd:
                print_info(f"[auth] Attempting auto-login for {email}…")
                if not perform_amazon_login(driver, email, pwd):
                    print_error("[auth] Auto-login failed.")
                resolve_amazon_interstitials(driver)
            if not is_logged_in(driver):
                if interactive:
                    print_info(
                        "[auth] Not logged in. Please login in the opened Chrome window, then press Enter here to continue."
                    )
                    _manual_login_prompt_loop(driver)
                else:
                    print_error("[auth] Not logged in and interactive=False; aborting this run.")
                    try:
                        driver.quit()
                    except Exception:
                        pass
                    return pd.DataFrame(), {
                        "snapshots": 0,
                        "reviews": 0,
                        "asins": len(asins),
                        "new_reviews": 0,
                        "duplicates_skipped": 0,
                    }
    except Exception as e:
        print_error(f"[auth] Login normalization failed: {e}")

    snapshot_records: list[dict] = []
    review_records: list[dict] = []
    total_new_reviews = 0
    total_duplicates_skipped = 0

    # Load existing review_ids to support incremental collection
    existing_ids_by_asin: dict[str, set[str]] = {}
    latest_dt_by_asin: dict[str, pd.Timestamp] = {}
    try:
        if session is not None and getattr(session, "collection_path", None):
            rfile = reviews_csv(Path(session.collection_path))
            if rfile.exists():
                try:
                    cols = ["asin", "review_id", "review_date"]
                    usecols = [c for c in cols if c in pd.read_csv(rfile, nrows=0).columns]
                    old = pd.read_csv(rfile, usecols=usecols) if rfile.stat().st_size > 0 else None
                except Exception:
                    old = None
                if old is not None and not old.empty:
                    if "review_id" in old.columns:
                        for a, grp in old.groupby("asin"):
                            existing_ids_by_asin[str(a)] = set(
                                str(x) for x in grp["review_id"].dropna().astype(str).tolist()
                            )
                    if "review_date" in old.columns:
                        tmp = old.copy()
                        tmp["_dt"] = pd.to_datetime(tmp["review_date"], errors="coerce")
                        tmp = tmp.dropna(subset=["_dt"])  # keep only valid dates
                        if not tmp.empty:
                            g = tmp.groupby("asin")["_dt"].max()
                            for a, ts in g.items():
                                latest_dt_by_asin[str(a)] = pd.Timestamp(ts)
    except Exception:
        pass

    try:
        for asin in asins:
            print_info(f"[collector] {asin}: starting (market={mp})")

            try:
                row = _get_row_for_asin(session, asin)
                # Fallbacks for category path: prefer explicit column, then 'category'
                if row is not None:
                    if "category_path" in row and pd.notna(row["category_path"]):
                        category_path = str(row["category_path"])
                    elif "category" in row and pd.notna(row["category"]):
                        category_path = str(row["category"])
                    else:
                        category_path = "unknown"
                else:
                    category_path = "unknown"

                ok = navigate_to_reviews(driver, asin, mp)
                # After navigation, check if we hit login/auth portal and recover
                try:
                    page_lower = driver.page_source.lower()
                except Exception:
                    page_lower = ""
                if ("authportal-center-section" in page_lower) or ("ap_email" in page_lower):
                    if interactive:
                        print_info(
                            "[auth] Reviews page requires login. Please login in Chrome, then press Enter here…"
                        )
                        _manual_login_prompt_loop(driver, max_checks=None)
                        # Re-open target page after login
                        navigate_to_reviews(driver, asin, mp)
                    else:
                        print_error(
                            f"[auth] {asin}: login required and interactive=False; skipping ASIN"
                        )
                        continue
                # Wait for review content to load; if captcha/robot detected, prompt
                if not _wait_for_reviews(driver, timeout=15):
                    try:
                        page_lower = driver.page_source.lower()
                    except Exception:
                        page_lower = ""
                    if ("captchacharacters" in page_lower) or ("robot check" in page_lower):
                        if interactive:
                            print_info(
                                "[auth] Robot check detected. Solve captcha in Chrome, then press Enter…"
                            )
                            _manual_login_prompt_loop(driver, max_checks=None)
                            navigate_to_reviews(driver, asin, mp)
                            _wait_for_reviews(driver, timeout=15)
                        else:
                            print_error(
                                f"[auth] {asin}: robot check and interactive=False; skipping ASIN"
                            )
                            continue
                if not ok:
                    print_error(f"[collector] {asin}: failed to open reviews page")
                    continue

                page = 1
                known_ids: set[str] = set(existing_ids_by_asin.get(str(asin), set()))
                asin_reviews: list[dict] = []
                details: dict[str, Any] | None = None
                total_reviews_on_page: int | None = None
                pages_visited = 0

                max_pages_env = 0
                try:
                    max_pages_env = int(ENV_VARS.get("REVIEWS_MAX_PAGES", "0") or "0")
                except Exception:
                    max_pages_env = 0
                latest_cut = latest_dt_by_asin.get(str(asin))

                while len(asin_reviews) < max_reviews_per_asin:
                    # Ensure page content is loaded before sampling HTML
                    _wait_for_reviews(driver, timeout=10)
                    html = driver.page_source
                    asin_dir = _current_raw_root() / asin
                    save_html(asin_dir, asin, page, html)

                    soup = BeautifulSoup(html, "html.parser")
                    try:
                        blocks = len(soup.select("div[data-hook='review']"))
                        print_info(f"[collector] {asin}: page {page} review blocks: {blocks}")
                    except Exception:
                        pass

                    if details is None:
                        try:
                            details = extract_product_details(
                                soup, row if row is not None else pd.Series()
                            )
                        except Exception:
                            details = {
                                "category_path": category_path,
                                "price": None,
                                "bsr": None,
                                "review_count": None,
                            }
                        try:
                            total_reviews_on_page = extract_total_reviews(soup)
                        except Exception:
                            total_reviews_on_page = None
                        # ensure category_path fallback
                        if not details.get("category_path"):
                            details["category_path"] = category_path
                        category_path = details.get("category_path") or category_path

                    # Extract reviews from current page
                    try:
                        page_reviews = extract_reviews_from_html(soup, asin, mp, category_path)
                    except Exception as e:
                        print_error(f"[collector] {asin}: parse error on page {page}: {e}")
                        page_reviews = []

                    new_on_page = 0
                    newer_by_date_on_page = False
                    for r in page_reviews:
                        rid = str(r.get("review_id") or "").strip()
                        # Early signal by date
                        if latest_cut is not None:
                            try:
                                dt = pd.to_datetime(r.get("review_date"), errors="coerce")
                                if pd.notna(dt) and dt > latest_cut:
                                    newer_by_date_on_page = True
                                # else keep as-is
                            except Exception:
                                pass
                        if rid and rid in known_ids:
                            total_duplicates_skipped += 1
                            continue
                        known_ids.add(rid)
                        asin_reviews.append(r)
                        new_on_page += 1
                        if len(asin_reviews) >= max_reviews_per_asin:
                            break

                    pages_visited += 1
                    # Incremental stop: if current page added no new reviews, break (pages are sorted by recent)
                    if new_on_page == 0:
                        print_info(
                            f"[collector] {asin}: no new reviews on page {page}; stopping early"
                        )
                        break
                    # Date-based early stop: no items on this page newer than latest_cut
                    if latest_cut is not None and not newer_by_date_on_page:
                        print_info(
                            f"[collector] {asin}: page {page} has no reviews newer than {latest_cut.date()}; stopping by date"
                        )
                        break

                    # Try to go next page
                    if len(asin_reviews) >= max_reviews_per_asin:
                        break
                    if max_pages_env and page >= max_pages_env:
                        print_info(
                            f"[collector] {asin}: reached REVIEWS_MAX_PAGES={max_pages_env}; stopping"
                        )
                        break
                    nxt = _next_page_with_max_guard(driver, asin, page)
                    if nxt == -1:
                        break
                    page = nxt
                    # Wait for next page reviews to appear
                    _wait_for_reviews(driver, timeout=10)
                    time.sleep(0.5)

                # Snapshot entry
                snapshot_records.append(
                    {
                        "asin": asin,
                        "snapshot_ts": run_ts,
                        "total_reviews": (
                            total_reviews_on_page
                            if total_reviews_on_page is not None
                            else len(asin_reviews)
                        ),
                        "title": (
                            str(row["title"])
                            if row is not None and "title" in row and pd.notna(row["title"])
                            else ""
                        ),
                        "price": (
                            details.get("price")
                            if details
                            else (
                                str(row["price"])
                                if row is not None and "price" in row and pd.notna(row["price"])
                                else ""
                            )
                        ),
                        "bsr": (
                            details.get("bsr")
                            if details
                            else (
                                str(row["best_sellers_rank"])
                                if row is not None
                                and "best_sellers_rank" in row
                                and pd.notna(row["best_sellers_rank"])
                                else ""
                            )
                        ),
                        "category_path": category_path,
                        "rating": (
                            str(row["rating"])
                            if row is not None and "rating" in row and pd.notna(row["rating"])
                            else ""
                        ),
                        "review_count": (
                            details.get("review_count")
                            if details
                            else (
                                str(row["total_review_count"])
                                if row is not None
                                and "total_review_count" in row
                                and pd.notna(row["total_review_count"])
                                else ""
                            )
                        ),
                    }
                )

                review_records.extend(asin_reviews)
                total_new_reviews += len(asin_reviews)
                print_success(
                    f"[collector] {asin}: collected {len(asin_reviews)} reviews (pages visited: {pages_visited})"
                )

            except Exception as e:
                print_error(f"[collector] {asin}: unexpected error: {e}")
                continue

    finally:
        try:
            driver.quit()
        except Exception:
            pass

    # Persist results if session provided
    df_reviews = pd.DataFrame(review_records) if review_records else pd.DataFrame()

    if session is not None:
        if snapshot_records:
            try:
                df_snapshot = pd.DataFrame(snapshot_records)
                save_snapshot(session, df_snapshot, overwrite_today=True)
                print_success(f"[collector] snapshots saved: {len(df_snapshot)}")
            except Exception as e:
                print_error(f"[collector] failed to save snapshots: {e}")
        if not df_reviews.empty:
            try:
                save_reviews(session, df_reviews)
                print_success(f"[collector] reviews saved: {len(df_reviews)}")
            except Exception as e:
                print_error(f"[collector] failed to save reviews: {e}")

    stats = {
        "snapshots": len(snapshot_records),
        "reviews": len(df_reviews),
        "asins": len(asins),
        "new_reviews": total_new_reviews,
        "duplicates_skipped": total_duplicates_skipped,
    }
    return df_reviews, stats
