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

## 🧠 Statistical Tests (by Dr. Volkova, Analytics)

The tool includes an experimental **analytics module** developed in collaboration with data scientist Dr. Volkova.

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

- Appends a new row per ASIN (at каждый запуск пункта 3)
- Содержит: `title`, `price`, `bsr`, `category_path`, `rating`, `review_count`, `total_reviews`, `snapshot_ts`, `captured_at`
- Хранится в едином `snapshot.csv` в папке коллекции (анализируется как временной ряд)

---

## 🤖 Auto-Collection (Scheduler)

Встроен режим автосбора 4–6 раз в сутки для регулярного пополнения `reviews.csv` и `snapshot.csv`.

Включение из CLI:

- Загрузите коллекцию (п.1 меню) — будет предложено включить авто‑сбор.
- Или откройте п.6 “Auto-collection settings”:
  - Enable/Disable для текущей коллекции
  - List всех включённых (частота, next_run, last_run)

Файлы состояния и логов:

- `DATA/.auto_collect.json` — список коллекций с `enabled`, `frequency_per_day`, `next_run`, `last_run` (первый `next_run` назначается ~через 2 минуты после включения)
- `DATA/.locks/<cid>.lock` — защита от параллельных запусков
- `DATA/runs/<cid>.jsonl` — JSONL‑сводки запусков (rows, new_reviews, duplicates_skipped, snapshots)

Неблокирующие скрипты:

- `scripts/run_pipeline.py --collection-id <cid>` — запускает сбор для одной коллекции (использует lock, пишет JSONL)
- `scripts/auto_runner.py` — запускает все коллекции, у которых наступил `next_run`, и перевычисляет `next_run`

Cron (пример):

```cron
# Ежечасно с логом
5 * * * * cd /path/to/Pyton_main/Pyton_Data_Analytic_project && ./venv/bin/python scripts/auto_runner.py >> logs/collector.log 2>&1
```

macOS launchd (идея): создайте plist с `ProgramArguments=[..., python, scripts/auto_runner.py]` и `StartCalendarInterval` на нужные часы.

Рекомендации:

- `BROWSER_VISIBILITY=minimize` (или normal) — headless может хуже работать на Amazon
- Профиль Chrome: `CHROME_USER_DATA_DIR`, `CHROME_PROFILE_DIR` в `conf.env`
- Авто‑логин: `AMAZON_EMAIL`/`AMAZON_PASSWORD` (или keychain через `keyring`)

### Отключение внешних провайдеров (опционально)

Если хотите полностью отказаться от внешних API при сборе ASIN:

- В `conf.env` установите:
  - `DISABLE_SCRAPINGDOG=1`
  - `DISABLE_SERPAPI=1`
- Поток создания коллекции автоматически перейдёт на Selenium‑поиск `https://amazon.<domain>/s?k=...`.

### Демон без cron (локально)

- Запуск: `./venv/bin/python scripts/auto_daemon.py`
- Интервал проверок: `AUTO_DAEMON_INTERVAL_SEC` (по умолчанию 900)
- Остановка: Ctrl+C или удаление `DATA/.locks/auto_daemon.lock`

### Вспомогательные скрипты

- `scripts/run_auto.sh` — запускает orchestrator с логом в `logs/collector.log`
- `scripts/setup_cron.sh` — устанавливает hourly cron для orchestrator

---

## 📒 Changelog (v1.2)

- Reviews pipeline: инкремент по `review_id` и по дате; ранний стоп при отсутствии новых отзывов; non‑interactive режим для авто‑запуска.
- Навигация: нормализация домена через `core/marketplaces.to_domain()` (пример: US → amazon.com).
- Создание коллекции: добавлен Selenium‑fallback, флаги `DISABLE_SCRAPINGDOG`/`DISABLE_SERPAPI`.
- Аналитика (UX):
  - Короткие названия продуктов на графиках вместо голых ASIN
  - Цветовые легенды для NPS/Sentiment/Flags
  - Флаги коротких/длинных отзывов по децилям длины (p10/p90)
- Авто‑сбор: добавлены `scripts/auto_runner.py`, `scripts/auto_daemon.py`, `scripts/run_auto.sh`, `scripts/setup_cron.sh`; первый запуск через ~2 минуты после включения.



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
