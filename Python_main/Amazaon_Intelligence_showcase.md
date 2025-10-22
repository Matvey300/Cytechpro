# Amazon Market Intelligence Toolkit

**Turn raw Amazon product signals into board-ready insights — automatically, reliably, and at scale.**

---

## Quick Facts
- Built for category managers, marketplace analysts, and growth leaders who need trustworthy read-outs on Amazon performance without stitching together multiple tools.
- Automates Selenium-based review and product snapshot collection, deduplicates results, and enriches them with TextBlob sentiment scoring and business-ready metrics.
- Ships a curated analytics layer (Parquet/CSV) that feeds Power BI dashboards, anomaly alerts, and correlation studies across dozens of ASINs per run.
- Designed for always-on use: per-collection auto-scheduling, lock-protected runners, and raw HTML/PNG evidence for every datapoint gathered.

---

## The Problem We Solve
Amazon’s marketplace moves faster than manual research. Prices shift hourly, review sentiment can be gamed, and Best Seller Rank (BSR) swings hint at looming wins or risks. Teams lose days copying tables, exporting CSVs, and guessing at causality — often missing the moment to respond.  
**The Amazon Market Intelligence Toolkit compresses that entire loop into a single automated pipeline.**

---

## What You Get
### 1. Enterprise-Grade Data Collection & Quality
- Selenium + Chrome profile automation that respects your logged-in Amazon session, persists cookies, and stores every HTML page for audit.
- Dual capture: fresh review pulls (with duplicate/date guards) and dynamic product “snapshots” covering price, rating, total reviews, BSR, and category breadcrumbs.
- Price quality safeguards (`price_clean`, `price_hidden`, optional cart-price recovery) and screenshot capture to validate hidden or gated listings.

### 2. Decision Intelligence Layer
- TextBlob-powered sentiment tagging on every review, with daily densification for smooth trend lines.
- Authenticity heuristics (volume spikes, suspicious authors, duplicate content, hyperactivity) to spotlight reputation manipulation.
- Rolling 7/28/90-day correlations that surface leading indicators between sentiment, price, and BSR — including weekly alerts for significant movements.

### 3. Automation & Operations
- Switch-on auto-collection per ASIN bundle: configurable frequency, jittered scheduling, and lock files so cron or daemon runners never collide.
- Conditional daily DP screening that reruns snapshots when quality thresholds slip or fresh reviews land.
- End-to-end export pipeline that refreshes `exports/latest` for BI tools the moment a run completes.

---

## How the Workflow Runs
1. **Load or build a collection** of ASINs via the CLI assistant (keyword + category search included).  
2. **Configure** environment keys (`conf.env`) — Chrome profile, SerpAPI/Scrapingdog, optional Amazon credential helpers.  
3. **Launch** `app.py` for guided runs or hand off to `scripts/auto_runner.py` / `scripts/auto_daemon.py` for 24/7 coverage.  
4. **Capture** reviews and product snapshots with dedupe logic, review sentiment, and Raw HTML/PNG stored in `DATA/<collection>/Raw`.  
5. **Deliver** curated tables — `asins_dim`, `reviews_fact`, `snapshot_fact`, `metrics_daily`, `metrics_rolling_7d|28d`, authenticity flags, NPS splits, correlation matrices — ready for BI or downstream models.

---

## Data Products & Deliverables
- **BI-Ready Exports:** Parquet-first data mart with CSV fallbacks for compatibility.  
- **Analyst Dashboards:** Power BI connects directly to `DATA/<collection>/exports/latest`, enabling dynamic pricing, sentiment, and BSR visuals anchored to the most recent run.  
- **Human-Readable Evidence:** Raw HTML, optional PNG captures, and JSONL run logs for compliance or QA reviews.  
- **Insight Hooks:** Weekly correlation alerts, variance tests (Levene, Kruskal-Wallis), and review authenticity summaries to guide merchandising and CX decisions.

---

## Technical Architecture
- **Language & Core Stack:** Python 3.10+, Pandas, NumPy, SciPy, TextBlob, Selenium WebDriver, BeautifulSoup.  
- **Automation Layer:** Custom auto-run daemon, lock-managed pipeline runner, and configurable frequencies per collection.  
- **Data Persistence:** Append-only CSV for raw capture, deduplicated facts in Parquet/CSV, and raw evidence in structured directories.  
- **Deployment Ease:** One-command environment validation (`python -m core.env_check`) and virtualenv bootstrap (`setup.sh`).  
- **Observability:** Rich logging to `logs/collector.log`, per-run JSONL stats, and console telemetry for interactive runs.

---

## Impact Highlights
- Tracks 60+ ASINs per collection with configurable limits (default 200 reviews / 30 pages per ASIN).  
- Cuts manual data preparation from days to minutes by automating collection, QA, and export in a single run.  
- Surfaces anomalies (price spikes, hidden pricing, BSR gaps) immediately via daily screening triggers and correlation alerts.  
- Enables consistent executive reporting: smoothed daily metrics (`*_3d`, `*_7d`, `*_28d`), NPS ladders, and authenticity flags that plug straight into BI.

---

## Roadmap & Vision
- Variant-level pricing comparison (color/size level) with discount recognition.
- Keepa integration to enrich historical BSR backfills.
- Transformer-based sentiment upgrade for nuanced tone detection.
- Streamlit-powered lightweight UI for non-technical stakeholders.

---

## Explore the Code
Dive into the full project, including source, analytics notebooks, and automation scripts:  
➡️ **GitHub Repository:** [https://github.com/Matvey300/CyberPro/tree/main/Python_main/Python_Data_Analytic_project](https://github.com/Matvey300/CyberPro/tree/main/Python_main/Python_Data_Analytic_project)

Want a guided walkthrough, live dashboard, or a tailored deployment?  
**Let’s connect via LinkedIn or email — this showcase is built to open the conversation.**
