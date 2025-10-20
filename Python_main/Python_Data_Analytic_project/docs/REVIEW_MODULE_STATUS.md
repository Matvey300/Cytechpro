# 📦 Review Module Status Registry

This document tracks the QA and architectural status of all key modules involved in the Amazon Review Intelligence Tool as of **2025-09-15**.

---

- 2025‑09‑15: Planned fix for critical CLI boot error — misaligned import of `print_info` from outdated `session_state` in `review_collector` and other modules; migration to `core.session` required — Dora
- 2025‑09‑20: Updated `scraper/product_info.py` — broadened BSR regex variants and added `#SalesRank` fallback to restore snapshot BSR capture — Assistant
- 2025‑09‑20: Updated `scraper/review_collector.py` — computes TextBlob sentiment per review before persistence to `reviews.csv`; logs failures — Assistant
- 2025‑10‑06: Normalized analytics schema: use `rating` (was `avg_rating`) and `bsr` (was `bsr_rank` in daily); added compatibility bridges in `analytics/correlation_analysis.py`, `analytics/review_dynamics.py`, and `analytics/exporter.py`; ensured exporter maps `review_count/total_reviews` consistently — Assistant
- 2025‑10‑06: Added BI-ready dynamics and correlations in `analytics/exporter.py`: outputs `metrics_daily`, `metrics_rolling_7d`, `correlations_by_asin` (90‑day Spearman for sentiment/rating vs price/BSR) — Assistant
- 2025‑10‑06: Extended exporter with 3‑day smoothing and alerts: `metrics_daily` now includes `*_3d`; `correlations_by_asin` adds `smoothing=raw|sm3d` and windows 7/28/90; added `correlations_alerts_7d` (thresholds: |r|≥0.6, p<0.1, n_obs≥5, stability check) — Assistant
- 2025‑10‑13: Exporter now forcibly reloads session data from disk to prevent stale exports; added densification of `sentiment_daily` by `(asin,date)` grid from snapshots; coerced numerics for `snapshot_fact` and `metrics_daily` (incl. `new_reviews`) — Assistant
- 2025‑10‑13: `actions/reviews_controller` refreshes session in‑memory frames after collection to align with on‑disk state (prevents missing rows in `reviews_fact` and lagging flags) — Assistant
- 2025‑10‑13: Improved price capture: `scraper/product_info.py` scopes selectors to product header; `scraper/review_collector.py` now enriches from product DP page if price missing or shows “Click to see price” — Assistant
- 2025‑10‑13: Added broader DP price selectors and explicit Selenium waits for price blocks; reduced false positives from carousels; fallback limited to DP price containers — Assistant
- 2025‑10‑13: Strengthened DP review_count extraction: prefer `#acrCustomerReviewText` / `acr-total-review-count` selectors; fallback to robust "global ratings" regex over full page; avoid tiny spurious matches — Assistant
- 2025‑10‑13: Review collector now logs into Amazon (if creds set) before DP enrich; also saves DP HTML/PNG to `Raw/snapshots/<run_ts>/<asin>_dp.*` for audit and parser tuning — Assistant
## ✅ Legend

| Status | Meaning                          |
|--------|----------------------------------|
| 🟢     | Complete and locked              |
| 🟠     | In progress / partially reviewed |
| ⚠️     | Under suspicion / review needed  |
| 🔴     | Broken / disabled                |

---

## 🧩 Modules Overview

| Module                           | Status | Last Patched                                      | Owner |
|----------------------------------|--------|--------------------------------------------------|-------|
| `analytics/review_authenticity` | 🟢     | 2025‑09‑15                                       | Dora  |
| `analytics/reaction_pulse`      | 🟢     | 2025‑09‑15                                       | Dora  |
| `analytics/correlation_analysis`| 🟢     | 2025‑10‑06 (schema normalization rating/total_reviews) | Matvey |
| `analytics/daily`               | 🟢     | 2025‑10‑06 (BSR key unified: `bsr` instead of `bsr_rank`) | Matvey |
| `analytics/review_dynamics`     | 🟢     | 2025‑10‑06 (fallbacks: avg_rating→rating, total_reviews→review_count, bsr_rank→bsr) | Dora  |
| `core/collection_io`            | 🟢     | 2025‑09‑17 (print_info validated, structure reviewed, CLI-confirmed) | Dora |
| `core/session_state`            | 🟢     | 2025‑09‑15 (print_info relocated from analytics) | Dora  |
| `core/env_check`                | 🟢     | 2025‑09‑17 (env var MAX_REVIEWS_PER_ASIN fallback added, CLI warning logged)                 | Dora  |
| `actions/menu_main`             | 🟢     | 2025‑09‑15                                       | Dora  |
| `actions/reviews_controller`   | 🟢     | 2025‑09‑17 (import of get_reviews_max_per_asin() applied, print_info validated, CLI OK) | Dora  |
| `scraper/page_parser`           | 🟢     | 2025‑09‑17 (finalized, full structural review, CLI-ready, Dora) | Dora  |
| `scraper/html_saver`            | 🟢     | 2025‑09‑17 (revalidated after import error, function `save_review_pages` confirmed, CLI-tested) | Dora  |
| `scraper/product_info`          | 🟢     | 2025‑09‑20 (BSR patterns expanded; SalesRank fallback) | Matvey |
| `scraper/review_parser`         | 🟢     | 2025‑09‑16 (None check added, print_info used, finalized, CLI-verified) | Matvey |
| `scraper/review_parser`         | 🟢     | 2025‑09‑18 (selector widened: [data-hook='review'] li/div + cmps-review fallback) | Matvey |
| `scraper/review_collector.py`  | 🟢     | 2025‑09‑20 (sentiment persisted to reviews; TextBlob integration) | Matvey |
| `scraper/navigator`             | 🟢     | 2025‑09‑17 (function `open_reviews_page` restored, interface normalized, CLI-tested) | Matvey |
| `core/marketplaces`             | 🟢     | 2025‑09‑19 (added to_domain() normalizer to map US/com/amazon.com → full domain) | Kot |
| `scraper/driver`                | 🟢     | 2025‑09‑17 (get_driver renamed to init_driver)  | Matvey |
| `scraper/driver`                | 🟢     | 2025‑09‑18 (BROWSER_VISIBILITY respected; profile from env; minimize mode) | Matvey |
| `app.py`                        | 🟢     | 2025‑09‑14                                       | Dora  |
| `core/session.py`               | 🟢     | 2025‑09‑17 (function print_info validated, imports checked, CLI integrity confirmed) | Dora  |
| `core/log.py`                  | 🟢     | 2025‑09‑17 (new module created for centralized logging, used project-wide) | Dora |
| `core/collection_io`          | 🟢     | 2025‑09‑19 (added create_collection/save_collection; new-format only) | Kot |
| `core/env_check`              | 🟢     | 2025‑09‑19 (added get_env helper for actions/asin_search) | Kot |
| `core/auto_collect.py`        | 🟢     | 2025‑09‑19 (autoscheduling state, enable/disable, next_run handling) | Kot |
| `scripts/run_pipeline.py`     | 🟢     | 2025‑09‑19 (non-interactive runner with lock + JSONL runs log) | Kot |
| `scripts/auto_runner.py`      | 🟢     | 2025‑09‑19 (hourly orchestrator: runs due collections, updates next_run) | Kot |

---

- 2025‑09‑17: Finalized `actions/reviews_controller.py` — replaced import of `REVIEWS_MAX_PER_ASIN` with function call `get_reviews_max_per_asin()`, logging via `print_info` confirmed, CLI tested — Dora
- 2025‑09‑17: Updated `actions/menu_main.py` to call run_review_pipeline() with explicit argument max_reviews_per_asin=get_reviews_max_per_asin(). Validated import, CLI run successful — Dora

- 2025‑09‑17: Finalized `scraper/review_collector.py` — replaced deprecated `open_reviews_page` with `navigate_to_reviews`, imports validated, CLI-tested — Dora
- 2025‑09‑17: Finalized module `scraper/navigator.py` — removed wrapper `next_page_with_max_guard`, restored `open_reviews_page`, validated import path, CLI-tested — Matvey
- 2025‑09‑17: Revalidated module `scraper/html_saver.py` after import failure in `review_collector.py`. Function `save_review_pages` verified, module marked CLI-ready — Dora
- 2025‑09‑17: Final validation of `scraper/html_saver.py` — CLI test passed, function `save_review_pages()` confirmed operational across all call sites — Dora
- 2025‑09‑17: Introduced module `core/log.py` with centralized logging helpers: `print_info`, `print_success`, `print_error`. Updated imports across all modules — Dora
- 2025‑09‑17: Removed all uses of print_info from `core/session_state.py`. Confirmed migration to `core/log.py` complete — Dora
- 2025‑09‑15: Finalized `scraper/navigator.py` — logging validated, retry logic inspected, owner updated to Matvey — Dora
- 2025‑09‑15: Finalized module `scraper/driver.py` — visibility flag centralized in ENV, print_info logging normalized — Dora
- 2025‑09‑15: Finalized module `scraper/review_parser.py` — added None protection and unified logging, ownership updated to Matvey — Dora
- 2025‑09‑15: Finalized module `scraper/product_info.py` — full review completed, ownership updated to Matvey — Matvey
- 2025‑09‑17: Final verification of `scraper/product_info.py` — print_info validated, CLI-tested, status 🟢 reaffirmed — Matvey
- 2025‑09‑15: Final cleanup of `analytics/correlation_analysis.py`, added docstrings, confirmed compliance with architectural rules — Matvey
- 2025‑09‑15: Brought `analytics/reaction_pulse.py` to compliance — import normalization, structural review completed — Dora
- 2025‑09‑15: Moved `print_info()` logging helper from `analytics/review_dynamics.py` to `core/session_state.py` to restore pipeline and ensure centralized infra functions — Dora
- 2025‑09‑15: Finalized module `analytics/correlation_analysis.py`, updated header notes, confirmed no further patches needed — Matvey
- 2025‑09‑15: Finalized module `analytics/daily.py` — snapshot path made injectable for testability, `print_info` applied, full structural review completed — Matvey
- 2025‑09‑17: Finalized module `scraper/page_parser.py` — full structural review complete, imports validated, CLI-ready — Dora
- 2025‑09‑15: Finalized module `scraper/product_info.py` — full review completed, ownership updated to Matvey — Matvey
- 2025‑09‑15: Finalized `scraper/review_collector.py` — centralized entrypoint, restored pipeline compatibility, logging routed via print_info, ownership assigned — Matvey
- 2025‑09‑15: Revalidated `core/env_check.py` — confirmed no further action required, removed from refactoring plan — Dora
- 2025‑09‑15: Fixed CLI boot failure by correcting print_info import in scraper/review_collector.py (migrated to core/session), discipline breach acknowledged and process rule reinforced — Dora
- 2025‑09‑15: Fixed legacy import in `scraper/driver.py` (print_info now imported from core/session) — Dora
- 2025‑09‑17: Renamed `get_driver` to `init_driver` in `scraper/driver.py`, verified all call sites, CLI now operational — Dora
- 2025‑09‑17: Verified `scraper/review_parser.py` — imports validated, print_info confirmed, CLI operational, status 🟢 maintained — Dora
- 2025‑09‑18: Updated `scraper/review_parser.py` — now selects generic `[data-hook='review']` (li or div) and falls back to `[data-hook='cmps-review']`. Fixes missed blocks on compact templates — Kot
- 2025‑09‑17: Confirmed `scraper/review_parser.py` integrity — import of `print_info` valid, CLI tested again, status 🟢 reaffirmed — Dora
- 2025‑09‑17: Detected broken import in `scraper/review_collector.py` — `open_reviews_page` missing from `navigator.py`. Status 🔴 assigned. CLI boot failed — Dora
- 2025‑09‑17: Began refactoring `scraper/review_collector.py` to explicitly pass `marketplace` into `open_reviews_page()` instead of relying on global session. Status set to 🟠 for in-progress interface normalization — Dora
- 2025‑09‑17: Finalized `core/session.py` — `print_info` confirmed present, module fully validated, status reaffirmed — Dora
- 2025‑09‑17: Начат аудит модуля `core/collection_io.py` — проверяется структура и использование логгера `print_info` — Dora
- 2025‑09‑17: Финализирован модуль `core/collection_io.py` — структура и поведение функций подтверждены, логгеры проверены, CLI протестирован — Dora
- 2025‑09‑17: Проведена ревизия `RULES.md`, подтверждена непротиворечивость. Выявлены потенциальные зоны ослабления дисциплины: (1) обход CLI-проверок после ручных правок, (2) замены переменных через fallback-значения без логирования, (3) ошибки повторного импорта уже проверенных функций. Установлено: правовая база проекта зрелая, требует только точечного усиления по журналу логирования переменных окружения — Dora
- 2025‑09‑17: Updated core/env_check.py to define MAX_REVIEWS_PER_ASIN from conf.env with fallback and logging. Ensures proper CLI warnings and fallback behavior — Dora

- 2025‑09‑18: Refactored `scraper/review_collector.py` — aligned signature with `actions/reviews_controller.run_review_pipeline`, fixed Chrome driver init args, switched to `open_reviews_page` + `_next_page_with_max_guard`, implemented multi-page scrape with dedup, and persisted via `core.collection_io` (snapshots + reviews). Import sanity OK — Kot
- 2025‑09‑18: Updated `scraper/review_collector.py` — added login normalization: auto-login via env creds (AMAZON_EMAIL/AMAZON_PASSWORD) and fallback to interactive prompt (press Enter after manual login). Fixes authportal redirects blocking review pages — Kot
- 2025‑09‑18: Improved `scraper/review_collector.py` Raw path resolution — recompute `Raw/reviews/<run_ts>` on every page save to avoid split outputs when `save_snapshot()` renames the collection folder mid-run. Prevents mixed pages across old/new dirs — Kot
- 2025‑09‑18: Hardened `scraper/review_collector.py` loading: added explicit waits for `#cm_cr-review_list`/`div[data-hook='review']`, and captcha/robot checks with interactive prompt. Fixes false warnings “No review divs found …” when content loads slowly — Kot
- 2025‑09‑18: Optimized `scraper/review_collector.py` for incremental runs — preloads existing review_id per ASIN from reviews.csv, skips duplicates during crawl and stops when a page yields 0 new reviews (recent sort). Respects `REVIEWS_MAX_PAGES` from env. Cuts repeat work on re-runs — Kot
- 2025‑09‑18: Added date-based early stop in `scraper/review_collector.py` — computes latest collected `review_date` per ASIN and stops when a page has no items newer than that. Also returns `new_reviews` and `duplicates_skipped` in stats. Menu prints these counters — Kot
- 2025‑09‑19: Added autoscheduling: `core/auto_collect.py`, CLI menu item for enabling/disabling & listing, non-interactive `scripts/run_pipeline.py`, and hourly `scripts/auto_runner.py` for due runs — Kot
- 2025‑09‑19: Tweaked `auto_collect.enable()` — first run is scheduled ~2 minutes after enabling (explicit), subsequent runs follow frequency with jitter — Kot
- 2025‑09‑19: Restored ASIN collection creation flow — option 1 now supports “Load existing / Create new (keyword→categories→ASIN)”. Fixed `actions/asin_controller` wrapper. Implemented `create_collection`/`save_collection` in `core/collection_io`. Added `get_env` in `core/env_check`. Limited initial ASIN set to top 100 by review_count — Kot
- 2025‑09‑19: Fixed SerpAPI fallback in `actions/asin_search.py` — use correct param `k` (not `q`), added result container fallback and link parsing for ASIN. Resolves 0‑result issue — Kot
- 2025‑09‑19: Fixed wrong review URL domain (.us) — `navigator` now uses `core.marketplaces.to_domain()` to build https://amazon.<domain>/product-reviews/... from country code or TLD. Example: US → amazon.com — Kot
- 2025‑09‑18: Updated `scraper/driver.py` — fixed headless logic to honor `BROWSER_VISIBILITY` (normal/minimize/offscreen/headless), use `get_chrome_profile_env()` for profile selection, kept `init_driver(session_dir)` signature. Improves visible window startup with user profile — Kot

---

- 2025‑09‑16: Установлено жёсткое правило: перед любой правкой модуля обязательно просматривать и фиксировать `REVIEW_MODULE_STATUS.md`. Последовательность фиксирована: (1) просмотреть и отметить исходный статус, (2) внести правку, (3) обновить статус и описание изменений. Нарушение последовательности запрещено — Dora

## 📌 Outstanding Refactoring Plan

The following modules remain under structural refactoring plan. All actions must adhere to the Ironclad Rule for Module Reviews.

| Module                           | Planned Work                                                  | Owner  |
|----------------------------------|----------------------------------------------------------------|--------|
| `conf.env`                       | Validate all keys in use, inject sample section               | Dora   |
| `core/session.py`               | Relocate `print_info()` here from session_state               | Dora   |
| `core/session_state.py`         | Remove print_info usage (migrated to core/log.py)             | Dora ✅ |
| `scraper/review_collector.py`   | ✅ Fixed: print_info import path updated to core/session       | Dora   |
| `analytics/reaction_pulse.py`   | Structural review finalized, mark as complete                 | Dora   |
| `core/log.py`                 | ✅ Created new centralized logging helpers (print_info, print_success, print_error) | Dora |

## ⚙ Architectural Standards

🔒 **Ironclad Rule for Module Reviews and Edits**

❗ No local, line-by-line edits are allowed. All work on a module begins with full structural inspection.

### Mandatory Procedure:

1. **Full top-to-bottom review of the module**, including:
   - headers and docstrings
   - all import statements
   - global constants or session state
   - all function definitions and bodies
   - tail logic (`if __name__ == "__main__"` etc.)

2. **Any architectural violations (even legacy ones)** must be immediately corrected:
   - 💥 imports placed at the bottom
   - 🧩 stubbed or placeholder code
   - 🧹 stray print/debug/TODO/pass/exit calls

3. **Every change must be logged in `REVIEW_MODULE_STATUS.md`**:
   - status
   - date
   - brief rationale and resolution

4. **Never allow micro-edits** such as:
   - ❌ "just add an import"
   - ❌ "quickly swap one print"
   - ❌ "drop a new function at the end"

📌 This rule applies to **all modules without exception**. Compliance is mandatory.

---

## 🧪 Pending Validation: Related Modules

### Mandatory Procedure for Cross-Module Validation

1. Просмотреть весь модуль сверху донизу, включая imports, структуру, все функции.
2. Проверить вызовы и импорты функции, которая была затронута в другой модуль (напр., save_review_pages()).
3. Отметить статус в журнале — до и после правки.
4. Не вносить микроправки без обновления REVIEW_MODULE_STATUS.md.
