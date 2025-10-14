# 🛍️ Amazon Market Intelligence Toolkit

Track sentiment, pricing, BSR and review dynamics across Amazon ASINs to reveal market trends, price moves and potential reputation manipulation. Built for analysts, category managers and growth teams.

---

## What’s Included (2025‑10‑13)

- Collection and parsing
  - Selenium + Chrome profile with raw HTML persisted for audit
  - Review collection with date/duplicate early‑stop; TextBlob sentiment per review; helpful‑votes defaulting to 0
  - Snapshot enrichment from DP pages (saved HTML/PNG). Price fallback when hidden: DP selectors → hidden base price → optional cart price
- Data quality and safety
  - `price_clean` (parsed and sanitized), `price_hidden` flag, currency symbol stripping, numeric coercion
  - DP HTML/PNG and review pages stored under `DATA/<collection>/Raw/...`
- Automation
  - Auto‑run scheduler (per collection) with conditional daily DP screening: runs if new reviews, data‑quality issues, or once per day
  - End‑to‑end export after each run
- BI‑ready exports (Parquet preferred, CSV fallback)
  - `asins_dim`: asin, title, category_path, country
  - `reviews_fact`: asin, review_id, review_date, rating, sentiment, review_helpful_votes, captured_at
  - `snapshot_fact`: asin, captured_at, price, price_hidden, rating, total_reviews, new_reviews, bsr, category_path, title, pages_visited, stopped_reason
  - `snapshot_latest`: last snapshot per asin
  - `sentiment_daily`: per‑asin/day counts and average sentiment; densified on the (asin, date) grid from snapshots
  - `metrics_daily`: daily join of snapshots + sentiment with 3‑day smoothing (`*_3d`) and aggregated `new_reviews`
  - `metrics_rolling_7d` / `metrics_rolling_28d`: rolling averages per asin
  - `flags_detail` / `flags_summary_by_asin`: authenticity heuristics (short/long/duplicate/high_volume/hyperactive_author)
  - `nps_by_asin`: promoter/passive/detractor shares and NPS
  - `correlations_by_asin`: 7/28/90‑day Spearman (raw/sm3d) for sentiment/rating vs price/BSR
  - `correlations_alerts_7d`: strong weekly signals with stability and severity

---

## Requirements

- Python 3.10+
- Google Chrome v115+
- ChromeDriver (matching your Chrome version)
- Optional keys:
  - `SERPAPI_API_KEY` (ASIN discovery)
  - `SCRAPINGDOG_API_KEY` (legacy paths)

---

## Environment

Create `conf.env` at project root:

```env
# API keys (optional)
SERPAPI_API_KEY=your_key
SCRAPINGDOG_API_KEY=your_key

# Chrome user data (recommended)
CHROME_USER_DATA_DIR=./DATA/.chrome_profile
CHROME_PROFILE_DIR=Default

# Amazon account (optional; enables price for hidden listings)
AMAZON_EMAIL=you@example.com
AMAZON_PASSWORD=your_password

# Collection limits
REVIEWS_MAX_PER_ASIN=200
REVIEWS_MAX_PAGES=30

# Window behavior
BROWSER_VISIBILITY=offscreen
SNAPSHOT_VISIBILITY=offscreen

# Price resolution
ENABLE_CART_PRICE=1
SAVE_PRODUCT_PNG=1
```

Validate:

```bash
python -m core.env_check
```

---

## Quick Start

```bash
pip install -r requirements.txt
python app.py
```

Menu highlights:
- Load/Create ASIN collection
- Search ASINs by keyword/category
- Collect reviews & snapshot (saves reviews.csv / snapshot.csv)
- Analytics (authenticity, sentiment, dynamics)
- Auto‑collection settings
- Export data mart for Power BI (exports/<ts> and exports/latest)

Automation:

```bash
python Pyton_main/Pyton_Data_Analytic_project/scripts/auto_runner.py
```

---

## Power BI Integration

- Connect Folder to `DATA/<collection>/exports/latest/`
- Prefer Parquet; CSV fallback is emitted when pyarrow is unavailable
- Use a Date table and anchor measures to the last data date (avoid BLANKs at calendar edges)
- Recommended fields
  - Pricing: use `snapshot_fact[price_clean]` and `price_hidden` for quality filters
  - Operational new reviews: `metrics_daily[new_reviews]` (captured date)
  - Smoothed series: `*_3d`, `*_7d`, `*_28d`
  - BSR correlations: invert BSR (negative rank) if computing additional correlations

Example anchored 7‑day price (semicolon separators):

```
Last Data Date (Captured) :=
VAR SelMax = MAX ( 'Date'[date] )
RETURN CALCULATE ( MAX ( 'metrics_daily'[date] ); FILTER ( ALL ( 'metrics_daily'[date] ); 'metrics_daily'[date] <= SelMax ) )

Price 7d (Clean) :=
VAR EndDt = [Last Data Date (Captured)]
RETURN CALCULATE ( AVERAGE ( 'snapshot_fact'[price_clean] ); DATESINPERIOD ( 'Date'[date]; EndDt; -7; DAY ) )
```

---

## Analytics

- Non‑parametric tests for noisy marketplace data
  - Levene’s variance, Kruskal‑Wallis, Spearman/Pearson
- Review authenticity heuristics and NPS per ASIN
- Correlation matrices and rolling correlations (7/28/90d) for sentiment/rating vs price/BSR, plus weekly alerting

---

## Data Model (canonical columns)

- Reviews fact: `asin, review_id, review_date, rating, sentiment, review_helpful_votes, captured_at, review_text`
- Snapshot fact: `asin, captured_at, price, price_hidden, rating, total_reviews, new_reviews, bsr, category_path, title, pages_visited, stopped_reason`
- Daily metrics: `asin, date, price, rating, total_reviews, bsr, new_reviews, review_count, avg_sentiment` + `*_3d`
- Rolling metrics: `*_7d`, `*_28d`
- Flags detail/summary, NPS per ASIN, correlations (by asin and alerts)

Notes
- `review_count` is per‑day observed count; `total_reviews` is product‑level total when available
- `price_clean` is numeric and parsed from raw strings (currency symbols removed)
- `sentiment_daily` is densified on snapshot dates for smooth time‑series

---

## Roadmap

- Variant‑level pricing (color swatches) with discount detection
- Keepa integration for historical BSR
- Transformer‑based sentiment (upgrade from TextBlob)
- Optional web UI (Streamlit/Flask)

---

## License

MIT — see LICENSE

