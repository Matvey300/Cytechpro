# Installation & Setup Guide

This guide walks you through installing, configuring, running, automating, and exporting data from the Amazon Review Intelligence Tool.

## 1) Prerequisites

- Python 3.10+
- Google Chrome v115+ (same channel as your ChromeDriver)
- ChromeDriver installed and allowed by your OS (see macOS note below)
- Optional for large exports (recommended): `pyarrow` for Parquet

## 2) Clone and virtual environment

```bash
git clone <your-repo-url>.git
cd Python_main/Python_Data_Analytic_project
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

## 3) Configuration (conf.env)

Create a file `conf.env` in the project root with at least:

```
# Marketplace and limits
DEFAULT_MARKETPLACE=com
REVIEWS_MAX_PER_ASIN=100
REVIEWS_MAX_PAGES=3

# Chrome profile (recommended: local persisted profile)
CHROME_USER_DATA_DIR=./DATA/.chrome_profile
CHROME_PROFILE_DIR=Default
BROWSER_VISIBILITY=normal   # normal|minimize|offscreen|headless

# Optional external providers (set to 1 to disable)
SERPAPI_API_KEY=
SCRAPINGDOG_API_KEY=
DISABLE_SCRAPINGDOG=0
DISABLE_SERPAPI=0

# Optional auto-login (or rely on your Chrome profile already logged in)
AMAZON_EMAIL=
AMAZON_PASSWORD=
```

## 4) macOS Gatekeeper (ChromeDriver)

If you installed `chromedriver` via Homebrew and see a security dialog:

```bash
xattr -dr com.apple.quarantine /opt/homebrew/bin/chromedriver || true
```

Or allow via System Settings → Privacy & Security → "Open Anyway".

## 5) First run

```bash
python app.py
```

- Menu 1 → Create new collection: enter keyword, select categories.
- If Scrapingdog/SerpAPI are unavailable/disabled, the tool falls back to Selenium search on Amazon.
- Menu 3 → Collect reviews & snapshot: if not logged in, the app will prompt you to log into Amazon (manual runs only).
- Menu 4 → Analyze and visualize: charts, flags, sentiment.

## 6) Autoscheduling

- Enable in app: Menu 6 → Enable for current collection (first `next_run` ~2 minutes after enabling)
- Orchestrator via cron (hourly):

```bash
bash scripts/setup_cron.sh
# or add manually:
# 5 * * * * cd <abs path>/Python_main/Python_Data_Analytic_project && ./venv/bin/python scripts/auto_runner.py >> logs/collector.log 2>&1
```

- Run now: `./venv/bin/python scripts/auto_runner.py`
- Logs: `tail -f logs/collector.log`

Non-interactive: auto-runs never prompt; if login is required and profile is not logged in, the run is skipped and logged.

## 7) Export for Power BI

- In the app: Menu 7 → Export data mart for Power BI
- Output folder: `DATA/<collection>/exports/latest/`
- Tables written (Parquet preferred, CSV fallback; install `pyarrow` for Parquet):
  - `asins_dim` (asin, title, category_path, country)
  - `reviews_fact` (asin, review_id, review_date, rating, sentiment, review_helpful_votes, captured_at)
  - `snapshot_fact` (asin, captured_at, price, rating, total_reviews, new_reviews, bsr, category_path, title)
  - `sentiment_daily` (asin, date, review_count, avg_sentiment, pos_cnt, neut_cnt, neg_cnt)
  - `nps_by_asin` (asin, n_reviews, promoter_pct, passive_pct, detractor_pct, nps)
  - `flags_detail` (asin, review_id, review_date, text_length, auth_flag)
  - `flags_summary_by_asin` (one row per asin with counts by flag)
  - `metrics_daily` (daily join: snapshot + sentiment; включает `avg_sentiment_3d`, `price_3d`, `rating_3d`, `bsr_3d`, `review_count_3d`, а также `new_reviews` — сумму per‑run инкрементов по дате)
  - `metrics_rolling_7d` / `metrics_rolling_28d` (скользящие средние по ключевым рядам)
  - `correlations_by_asin` (Spearman 7/28/90д по парам sentiment/rating vs price/BSR; `smoothing=raw|sm3d`, `*_sig` при p<0.05)
  - `correlations_alerts_7d` (сигналы сильной 7‑дневной связи; поля r, p, sig, stable, severity)
  - `snapshot_latest` (последний снапшот по каждому ASIN)

Power BI: Get Data → Folder → point to `exports/latest/` → Combine & Transform (or import individual files).

## 8) Where data is stored

`DATA/<YYYYMMDD>_<cid>_created<YYYYMMDD>/`
- `collection.csv` — the selected ASIN list
- `reviews.csv` — all collected reviews (incremental, deduped)
- `snapshot.csv` — product metrics snapshots (append-only)
- `Raw/` — raw HTML pages (audit only; not tracked by Git)
- `exports/<run_ts>/` and `exports/latest/` — BI-friendly tables

## 9) Troubleshooting

- ChromeDriver mismatch: update to match Chrome (e.g., `brew upgrade chromedriver`).
- Robot/captcha page:
  - Manual run: solve in Chrome; press Enter when prompted.
  - Auto run: skipped; ensure profile is logged in and visible (`BROWSER_VISIBILITY=normal|minimize`).
- "No review blocks found": page likely pre-loaded or login; the app retries and waits for `#cm_cr-review_list`.
- No refresh: check `logs/collector.log` and `DATA/.auto_collect.json` (`next_run` is UTC). Run orchestrator manually.
- Large datasets: keep small `REVIEWS_MAX_PAGES` for frequent runs; export to Parquet for Power BI performance.

---

For day-to-day usage, refer to the main README for quick commands and menu reference.
