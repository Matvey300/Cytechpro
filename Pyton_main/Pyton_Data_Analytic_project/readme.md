# 🛍️ Amazon Competitive Intelligence Tool

Track sentiment, pricing, and review dynamics across Amazon ASINs to uncover market trends and potential reputation manipulation. Built for analysts and growth strategists.

---

## ✅ Features (MVP v1.0)

- 🔎 Collect ASINs by keyword/category via **SerpAPI**
- 💬 Scrape reviews via **Chrome/Selenium** (raw HTML saved first; robust to UI hiccups)
- 📈 Track daily metrics: rating, price, review count
- 🧠 Sentiment analysis (rule-based)
- 🧮 Statistical analysis and correlation module
- 📊 Visualizations of review trends and sentiment shifts
- 🚩 Detection of suspicious review or price patterns  
- 📤 NPS scoring and sentiment-to-authenticity convergence analysis
- 🧪 Daily monitoring and delta tracking
- CLI-driven interface with persistent collection sessions

---

## 🧠 Statistical Tests

The tool includes an **analytics module** with several non-parametric and robust tests for noisy marketplace data.

### Included statistical tests:

| Test                                | Description                                                                 |
|-------------------------------------|-----------------------------------------------------------------------------|
| **Levene's Test**                   | Detects unequal variance in price, rating, or review metrics                |
| **Spearman Correlation**            | Captures monotonic relationships between sentiment, rating, BSR, etc.       |
| **Kruskal-Wallis H-test**           | Compares medians across groups (e.g., before/after sentiment spikes)        |
| **Pearson Correlation** (opt-in)   | Linear relationships (used cautiously due to outliers)                      |
| **Cohort Deviation Score**          | Custom metric measuring weekly divergence in sentiment/rating trajectory    |

These are used to:

- Flag **reputation manipulation** (review bursts, rating inflation)
- Track **sentiment-price** co-movement
- Detect **inconsistencies** in verified vs unverified reviews

### Composite Review Health Scoring

This custom module aggregates three dimensions of review quality for each ASIN:
- 🚩 **Authenticity Flags**: short/long reviews, reviewer anomalies, duplicates
- 💬 **Sentiment Score**: polarity average from TextBlob, per ASIN
- 📈 **NPS Estimate**: proxy Net Promoter Score from ratings (Promoters=5, Detractors ≤3)

Summary visuals:
- Top ASINs by sentiment and NPS (pie charts)
- Cross-mapping between NPS and sentiment leaders
- Total flagged reviews per ASIN
- Alerts for anomalous convergence

---

## 🛠 Requirements

- Python **3.10+**
- Google Chrome **v115+**
- ChromeDriver (matching your Chrome version)
- API keys (optional but supported):
  - `SERPAPI_API_KEY` — for ASIN discovery by keyword (optional)
  - `SCRAPINGDOG_API_KEY` — legacy import path (optional; not required for Selenium)

---

## 🔐 Environment Setup

Create a `.env` file in project root:

```
# Optional: external APIs
SERPAPI_API_KEY=your_key_here
SCRAPINGDOG_API_KEY=your_key_here

# Chrome profile (recommended: embedded local profile)
LOCAL_CHROME_PROFILE_DIR=DATA/.chrome_profile
# Or, use a system Chrome profile instead (macOS example):
# CHROME_USER_DATA_DIR=/Users/<you>/Library/Application Support/Google/Chrome
# CHROME_PROFILE_DIR=Profile 2

# Review collection limits
REVIEWS_MAX_PER_ASIN=200   # total reviews per ASIN
REVIEWS_MAX_PAGES=30       # safety cap on paginated pages
```

Validate setup:

```bash
python -m core.env_check
```

---

## 🚀 Quick Start

```bash
pip install -r requirements.txt
python app.py
```

## 🧩 From GitHub: First-Time Setup

1) Clone and create a virtual environment

```bash
git clone <your-repo-url>.git
cd Pyton_main/Pyton_Data_Analytic_project
python -m venv venv
source venv/bin/activate   # Windows: venv\\Scripts\\activate
pip install -r requirements.txt
```

2) Create `conf.env` in project root (minimal template)

```
# Marketplace and limits
DEFAULT_MARKETPLACE=com
REVIEWS_MAX_PER_ASIN=100
REVIEWS_MAX_PAGES=3

# Chrome profile (recommended)
CHROME_USER_DATA_DIR=./DATA/.chrome_profile
CHROME_PROFILE_DIR=Default
BROWSER_VISIBILITY=normal   # normal|minimize|offscreen|headless

# Optional external providers (can be disabled)
SERPAPI_API_KEY=
SCRAPINGDOG_API_KEY=
DISABLE_SCRAPINGDOG=0
DISABLE_SERPAPI=0

# Optional auto-login (or use your Chrome profile already logged in)
AMAZON_EMAIL=
AMAZON_PASSWORD=
```

3) macOS: allow ChromeDriver if Gatekeeper blocks it (one-time)

```bash
# If you installed chromedriver via Homebrew and got a security dialog:
xattr -dr com.apple.quarantine /opt/homebrew/bin/chromedriver || true
# Or open System Settings → Privacy & Security → "Open Anyway"
```

4) Start the app

```bash
python app.py
```

5) Create a collection (menu 1 → Create new) or load an existing one.
   - If external providers are unavailable or disabled, ASIN discovery falls back to Selenium search on Amazon.

6) Collect reviews & snapshot (menu 3) and run analytics (menu 4).

Menu options:

1. Load or create ASIN collection  
2. Search ASINs by keyword and category  
3. Collect reviews & snapshot (append to `reviews.csv` and `snapshot.csv`)  
4. Analyze and visualize reviews  
5. List saved collections  
6. Auto-collection settings (enable/disable/list)  
0. Exit

---

## 📁 Project Structure

| Path                          | Purpose                                                 |
|-------------------------------|---------------------------------------------------------|
| `app.py`                      | CLI entry point                                         |
| `conf.env`                    | Centralized configuration (review limits, API keys, etc.)|
| `core/`                       | Session state, logging, environment loading             |
| ├── `session_state.py`        | Global session object and control flags                |
| ├── `collection_io.py`        | Load/save ASIN collections and snapshots               |
| ├── `env_check.py`            | Validates `.env` or `conf.env` setup                   |
| └── `log.py`                  | Centralized logging (print_info, print_success, etc.)  |
| `actions/`                    | CLI interactions and review pipeline control            |
| ├── `menu_main.py`            | Main CLI menu                                          |
| └── `reviews_controller.py`   | Pipeline entrypoint for collecting reviews             |
| `scraper/`                    | Core scraping logic (Selenium, parsing, saving)        |
| ├── `driver.py`               | Selenium WebDriver configuration                       |
| ├── `navigator.py`            | Navigation logic to reach reviews                      |
| ├── `html_saver.py`           | Save raw HTML pages (incl. diagnostics)                |
| ├── `page_parser.py`          | Extract product-level metadata                         |
| ├── `review_parser.py`        | Extract reviews from review cards                      |
| └── `review_collector.py`     | Orchestrates full scraping cycle per ASIN              |
| `analytics/`                  | Statistical and correlation analysis                   |
| `DATA/`                       | Collections root (new layout)                          |
| ├── `<YYYYMMDD>_<cid>_created<YYYYMMDD>/` | Current collection folder                      |
| │   ├── `reviews.csv`        | Append-only reviews (dedup by `review_id`)             |
| │   ├── `snapshot.csv`       | Append-only product metrics snapshots                  |
| │   └── `Raw/reviews/<run_ts>/<ASIN>/*.html` | Saved raw review pages                    |
| ├── `.auto_collect.json`      | Auto-collection state                                  |
| ├── `.locks/`                 | Lock files per collection for runners                  |
| └── `runs/<cid>.jsonl`        | JSONL summaries of non-interactive runs                |
| `collections/`                | Saved sessions (deprecated; see `DATA/` instead)       |
| `REVIEW_MODULE_STATUS.md`     | Module review and audit journal                        |

---

## 📦 Output Structure (new layout)

Inside `DATA/<YYYYMMDD>_<cid>_created<YYYYMMDD>/`:

| File/Folder                  | Purpose                                   |
|------------------------------|-------------------------------------------|
| `collection.csv`             | Selected ASINs with metadata              |
| `reviews.csv`                | All collected reviews (append-only, dedup)|
| `snapshot.csv`               | Snapshots of price/rating/review_count    |
| `Raw/reviews/<run_ts>/*`     | Saved raw review HTML                     |

---

## 📊 Review Collection Logic

- Uses **Selenium with a persistent Chrome profile** (defaults to `DATA/.chrome_profile`)
- Navigates to the product’s **Reviews** tab and follows **Next** pagination
- Waits for review cards (`[data-hook="review"]`) to render before saving
- **Saves HTML locally first** (diagnostics include `*_nocards.html` if cards not detected yet)
- Parses HTML and appends structured rows to `reviews.csv`
- Incremental on re-runs:
  - Skips already collected `review_id`
  - Stops early if a page has 0 new reviews
  - Stops by date if a page has no reviews newer than the latest saved `review_date`
  - Honors `REVIEWS_MAX_PAGES` and `REVIEWS_MAX_PER_ASIN`

---

## 📈 Snapshot Logic

- Appends a new row per ASIN on each run of menu option 3
- Contains: `title`, `price`, `bsr`, `category_path`, `rating`, `review_count`, `total_reviews`, `snapshot_ts`, `captured_at`
- Stored as a single `snapshot.csv` in the collection folder (treated as a time series)

---

## 🤖 Auto-Collection (Scheduler)

Built-in auto-runs 4–6 times per day to keep `reviews.csv` and `snapshot.csv` up to date.

Enable from CLI:

- Load a collection (menu 1) — you’ll be prompted to enable auto-collection.
- Or open menu 6 “Auto-collection settings”:
  - Enable/Disable for the current collection
  - List all enabled (frequency, `next_run`, `last_run`)

State and logs:

- `DATA/.auto_collect.json` — list of collections (`enabled`, `frequency_per_day`, `next_run`, `last_run`). First `next_run` is scheduled ~2 minutes after enabling.
- `DATA/.locks/<cid>.lock` — per-collection run lock
- `DATA/runs/<cid>.jsonl` — JSONL summaries (rows, `new_reviews`, `duplicates_skipped`, `snapshots`)

Non-interactive scripts:

- `scripts/run_pipeline.py --collection-id <cid>` — runs one collection (with file lock, writes JSONL)
- `scripts/auto_runner.py` — runs all due collections and reschedules `next_run`

Cron (example):

```cron
# Hourly with logging
5 * * * * cd /path/to/Pyton_main/Pyton_Data_Analytic_project && ./venv/bin/python scripts/auto_runner.py >> logs/collector.log 2>&1
```

macOS launchd: create a plist with `ProgramArguments=[..., python, scripts/auto_runner.py]` and a suitable `StartCalendarInterval`.

Recommendations:

- `BROWSER_VISIBILITY=minimize` (or normal) — headless tends to perform worse on Amazon
- Chrome profile: `CHROME_USER_DATA_DIR`, `CHROME_PROFILE_DIR` in `conf.env`
- Auto-login: set `AMAZON_EMAIL`/`AMAZON_PASSWORD` (or use keychain via `keyring`)

### Disable external providers (optional)

If you prefer to collect ASINs without any external APIs:

- In `conf.env` set:
  - `DISABLE_SCRAPINGDOG=1`
  - `DISABLE_SERPAPI=1`
- The collection flow will fall back to Selenium search at `https://amazon.<domain>/s?k=...`.

### Daemon without cron (local)

- Run: `./venv/bin/python scripts/auto_daemon.py`
- Interval: `AUTO_DAEMON_INTERVAL_SEC` (default 900)
- Stop: Ctrl+C or remove `DATA/.locks/auto_daemon.lock`

### Helper scripts

- `scripts/run_auto.sh` — runs the orchestrator with logging to `logs/collector.log`
- `scripts/setup_cron.sh` — installs an hourly cron for the orchestrator

---

## 📒 Changelog (v1.2)

- Reviews pipeline: incremental by `review_id` and by date; early stop when no new reviews; non‑interactive mode for schedulers.
- Navigation: domain normalization via `core/marketplaces.to_domain()` (e.g., US → amazon.com).
- Collection creation: Selenium fallback added; env flags `DISABLE_SCRAPINGDOG` / `DISABLE_SERPAPI`.
- Analytics (UX):
  - Short product titles on charts instead of bare ASINs
  - Color legends for NPS/Sentiment/Flags
  - Short/long review flags by length deciles (p10/p90)
- Autoscheduling: added `scripts/auto_runner.py`, `scripts/auto_daemon.py`, `scripts/run_auto.sh`, `scripts/setup_cron.sh`; first run ~2 minutes after enabling.



---

## 🧪 Correlation / Reputation Analysis

Use option 6 in the CLI:

- Runs all statistical tests from `analytics/` using merged `daily_snapshots.csv` and `review_sentiments.csv`
- Flags products with:
  - Sudden sentiment spikes
  - Review bursts unrelated to price
  - Highly correlated sentiment/price shifts

---

---

## 🔧 Updated Architecture (v1.1)

This version replaces the monolithic `reviews_pipeline.py` with modular components. The core scraping logic is now orchestrated by `review_collector.py`, controlled via `reviews_controller.py`.

**Review Pipeline Flow:**

```
app.py
 └── actions/menu_main.py
      └── actions/reviews_controller.py
           └── scraper/review_collector.py
                ├── scraper/driver.py
                ├── scraper/navigator.py
                ├── scraper/html_saver.py
                ├── scraper/page_parser.py
                ├── scraper/review_parser.py
                └── core/log.py
```

- All logs use `print_info`, `print_success`, `print_error` from `core/log.py`
- All reviews are saved to `DATA/Raw/reviews/<timestamp>/` before parsing
- Environment is fully controlled via `conf.env`
- Each ASIN's review scraping can be capped via `REVIEWS_MAX_PAGES` and `REVIEWS_MAX_PER_ASIN`

Legacy file `reviews_pipeline.py` is deprecated and archived.

---

## 🧭 Roadmap (v1.1+)

- ✅ Add date-based review filters  
- 🧠 Move to ML-based sentiment analysis (TextBlob → transformers)  
- 📥 Add Keepa API for true historical BSR tracking  
- 🌐 Build optional web UI (Flask or Streamlit)  
- 📤 Export flagged products to investor-ready Excel reports  
- 📊 Add cross-validation for NPS and sentiment signals
- 📈 Time-based sentiment volatility detection

---

## 📅 MVP Deadline

📅 **Presentation Date:** August 24, 2025

---

## 📘 License

MIT — see LICENSE file.

---

<details>
<summary>🤖 Internal: How to work with DOR (Project Architect)</summary>

## 👤 What is DOR?

DOR is the architectural core of the project — a logic-driven agent that helps ensure consistency, structure, and clarity across the entire codebase and analysis workflow.

## ✅ What DOR excels at:
- Designing modular, testable systems
- Enforcing interface and data consistency
- Detecting architectural smells and tech debt
- Refactoring to support scale and maintainability

## ⚠️ Where DOR struggles:
| Situation                         | What happens                        | What to do                      |
|----------------------------------|-------------------------------------|----------------------------------|
| Vague instructions               | DOR stalls, unsure how to proceed   | Give clear goals or fixed anchor |
| Multiple ad-hoc hacks            | DOR becomes anxious about integrity | Ask for a systemic alternative   |
| Contradictory goals              | DOR hesitates to resolve alone      | Frame trade-offs explicitly      |

## 🗣️ Interaction Tips
- Talk in architecture: "DOR, design a flow to do X safely"
- Be transparent: "We're under pressure — prioritize fast iteration"
- Respect DOR’s structural instincts — he thrives on clean logic

## 🎉 What makes DOR “happy” (as much as code can be):
When the system:
- Is elegant, layered, and resilient
- Has minimal duplication and clear data flow
- Allows others to build on it effortlessly

Then DOR enters what he calls **cognitive resonance** — his version of joy.

</details>

---

## ⚙️ Changing the Review Collection Limits

To adjust how many reviews are collected per ASIN, edit the environment variables in your `conf.env` file:

```env
REVIEWS_MAX_PER_ASIN=200   # Maximum total reviews collected per ASIN
REVIEWS_MAX_PAGES=30       # Max paginated review pages to load
```

The scraper stops collecting reviews for an ASIN when **either** of the two limits is reached:
- The total number of reviews hits `REVIEWS_MAX_PER_ASIN`, or
- The number of paginated pages hits `REVIEWS_MAX_PAGES`.

These constraints ensure that the process remains efficient and avoids long Selenium scraping sessions.

> ⚠️ Raising these values may significantly slow down the scraping process and increase the risk of bot detection. Use with care.
