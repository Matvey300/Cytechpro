# Amazon Reviews CLI (MVP)

## What it does
- Choose marketplace (US/UK), find categories by keyword (multi-select).
- Collect TOP-100 ASIN per chosen category, de-dup across categories.
- Collect up to 500 reviews per ASIN (sequential).
- Run tests:
  - Distortion probability (rating integrity).
  - Reviews → Sales impact (requires `sales.csv` in `Out/<ts>/`).
  - Extras: Volatility profile, Sentiment vs rating drift (VADER, English only), Top drivers.

## Run
```bash
cd Pyton_Data_Analytic_project
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python app.py