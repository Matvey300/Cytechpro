# Amazon Competitive Intelligence Tool

Track sentiment and review dynamics across fixed ASIN sets over time.

---

## ✅ Features (MVP v1.0)

- Collect ASINs from keyword (via SerpAPI) or manual entry
- Collect reviews using Scrapingdog API
- Track daily review count, rating, and price
- Visualize sentiment and review/rating trends
- Detect reputation manipulation patterns
- Run correlation analysis (price, sentiment, BSR)
- CLI-driven workflow with persistent collections

---

## 🛠 Requirements

- Python 3.10+
- Google Chrome version ≥ 115
- ChromeDriver matching your installed Chrome version
- `pip` packages listed in `requirements.txt`
- A **Scrapingdog API key** (env var: `SCRAPINGDOG_API_KEY`)
- A **SerpAPI key** (env var: `SERPAPI_KEY`)

---

## 🔐 Environment Setup

Set environment variables in a `.env` file (or via terminal export):

```env
SCRAPINGDOG_API_KEY=your_key_here
SERPAPI_KEY=your_key_here
```

You can verify your setup via:

```bash
python -m core.env_check
```

---

## 🚀 Quick Start

```bash
pip install -r requirements.txt
python app.py
```

Use the CLI to:

1. Load or create an ASIN collection
2. Collect reviews (via Scrapingdog, up to 500 per ASIN)
3. Capture daily snapshots: price, rating, review count
4. Plot review, rating, and sentiment dynamics
5. Run correlation and reputation analysis

---

## 📁 Project Structure

| Path                      | Purpose                                       |
|---------------------------|-----------------------------------------------|
| `core/`                   | Session state, auth, env checks               |
| `api/`                    | SerpAPI and marketplace integrations          |
| `actions/`                | CLI handlers for reviews, snapshots, plots    |
| `analytics/`              | Correlation, plotting, sentiment analysis     |
| `Out/`                    | Stored collections and results                |
| `ASIN_data_import.py`     | Category/keyword-based ASIN importer          |
| `reviews_pipeline.py`     | Low-level Scrapingdog review collector        |
| `app.py`                  | CLI entry point                               |
| `menu_main.py`            | Main user interaction menu logic              |

---

## 📦 Output Files

Outputs are saved in the `/Out/<collection_id>/` folder:

- `asins.csv` — the selected ASINs
- `reviews.csv` — collected reviews
- `daily_snapshots.csv` — periodic price, rating, and review count
- `review_sentiments.csv` — sentiment scores per review
- `plots/*.png` — graphs for trend and sentiment visualization
- `reputation_flags.csv` — flags for suspected manipulation

---

## 📊 Menu Structure (CLI)

Menu options adapt to session state:

```
1) Load or create ASIN collection
2) Collect reviews (max 500 per ASIN)
3) Take snapshot: rating, price, review count
4) Plot review, rating, and sentiment dynamics
5) Run correlation & reputation analysis
6) List saved collections
0) Exit
```

Only valid actions for your current collection state are shown.

---

## 🔍 Detection Capabilities

We calculate:

- Review growth rate anomalies
- Suspicious review patterns (length, timing, verified status)
- Correlation between sentiment shifts and price or BSR
- Potential ASINs with manipulated reputation

---

## 🧪 Known Limitations

- No Keepa integration — we build our own BSR history
- CLI-only interface (no web UI)
- Sentiment analysis is rule-based for MVP
- No date-based filtering in reviews (currently collects all)

---

## 📅 MVP Deadline

📅 Presentation Date: **August 24, 2025**

---

## 📘 License

MIT — see LICENSE file.