# 🛍️ Amazon Competitive Intelligence Tool

Track sentiment, pricing, and review dynamics across Amazon ASINs to uncover market trends and potential reputation manipulation. Built for analysts and growth strategists.

---

## ✅ Features (MVP v1.0)

- 🔎 Collect ASINs by keyword/category via **SerpAPI**
- 💬 Scrape reviews via **Scrapingdog API** (up to 500 reviews/ASIN)
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
- API keys:
  - `SCRAPINGDOG_API_KEY`
  - `SERPAPI_KEY`
- Packages in `requirements.txt`

---

## 🔐 Environment Setup

Create a `.env` file in project root:

```env
SCRAPINGDOG_API_KEY=your_key_here
SERPAPI_KEY=your_key_here
CHROME_USER_DATA_DIR=/path/to/profile
CHROME_PROFILE_DIR=Profile 2
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
2. Collect reviews (via Scrapingdog)  
3. Take daily snapshot (price, rating, review count)  
4. Plot review, rating, and sentiment dynamics  
5. Run correlation/statistical analysis  
6. List saved collections  
0. Exit

---

## 📁 Project Structure

| Path                      | Purpose                                         |
|---------------------------|-------------------------------------------------|
| `core/`                   | Session handling, auth, environment tools       |
| `actions/`                | CLI interactions: reviews, snapshots, plots     |
| `api/`                    | SerpAPI and marketplace integrations            |
| `analytics/`              | Statistical and correlation analysis            |
| `DATA/`                   | Input collections                              |
| `collections/`            | Outputs and saved sessions                      |
| `reviews_pipeline.py`     | Review scraping pipeline using Selenium         |
| `ASIN_data_import.py`     | Import ASINs from keyword/category              |
| `app.py`                  | CLI entry point                                 |

---

## 📦 Output Structure

Inside `collections/<collection_id>/`:

| File/Folder              | Purpose                                     |
|--------------------------|---------------------------------------------|
| `asins.csv`              | Selected ASINs with metadata                |
| `reviews.csv`            | All collected reviews                       |
| `daily_snapshots.csv`    | Daily rating, price, review count           |
| `RawData/*.html`         | Saved raw HTML pages for reproducibility    |
| `plots/*.png`            | Graphs: sentiment, price, ratings, etc.     |
| `reputation_flags.csv`   | Flagged ASINs with suspicious behavior      |
| `review_sentiments.csv`   | Sentiment and NPS scores per ASIN            |

---

## 📊 Review Collection Logic

- Uses **Selenium with persistent Chrome profile**
- Follows `Next` pagination up to 500 reviews or until new pages stop loading
- Verifies each page by detecting review blocks (`li[data-hook="review"]`)
- Saves HTML locally before parsing (ensures resilience and debug)
- Computes and persists sentiment scores using TextBlob

---

## 📈 Snapshot Logic

- Once per day (manual trigger)
- Pulls:
  - `buybox_price`
  - `avg_rating`
  - `total_reviews`
- Appends to `daily_snapshots.csv`

---

## 🧪 Correlation / Reputation Analysis

Use option 6 in the CLI:

- Runs all statistical tests from `analytics/` using merged `daily_snapshots.csv` and `review_sentiments.csv`
- Flags products with:
  - Sudden sentiment spikes
  - Review bursts unrelated to price
  - Highly correlated sentiment/price shifts

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