# Core product upgrade — 2026-09-27

## Delivered
- A learned daily-demand benchmark with explicit input contracts, regularized regression, train-only preprocessing and time-ordered model selection, calibration and test. It compares against two baselines and exposes failure under a demand shift.
- Five-seed, two-regime reproducible evaluation with exact predictions, metrics, hashes and model version.
- A decision workbench that prioritizes negative unit contribution, missing evidence and review needs, then inventory exposure. Financial changes are per-unit economics, not a profit forecast.
- Accept/reject/defer notes with complete evidence/scenario/policy snapshots. Stale input checks run again inside the SQLite transaction. Duplicate submission is idempotent; decisions do not update product prices.
- Browser pages for model validation, JSON history upload, reports, decision review and journal export. No external AI subscription.
- Updated product positioning, commercial pilot scorecard, model card, application narrative and architecture documentation.

## Verification
The full Python suite passed 452 tests with one optional legacy Streamlit/PyArrow skip. All 17 browser-module tests passed. The policy report checks 18 strategy/cost combinations with zero proposed-margin-floor breaches. New tests include train/test leakage isolation, calibration isolation, stockout handling, zero-sales behavior, numerical stability, bad upload contracts, stale decision review, concurrent evidence change, journal persistence and session isolation.

Five fixed synthetic seeds (11, 29, 47, 73, 101) beat both simple baselines in the stable regime and fail to beat the best baseline after the deliberately unseen shock. These outcomes support the demonstration's evaluation discipline only. They do not establish merchant accuracy, a causal price response or commercial return.

Visual browser QA remains unverified because the existing saved browser permission blocks localhost. No browser workaround was used. Hosting is still not published; the previously attempted Render connection failed. UI template/module tests and HTTP integration tests do not substitute for visual interaction testing.

## Commercial readiness judgment
Ready to demonstrate a coherent workflow and propose a narrowly scoped, assisted shadow pilot. Not ready to sell as a finished autonomous repricing SaaS or guarantee business impact. The main gaps are verified real sources, permissioned daily merchant data, measured workflow value, authenticated persistent multi-tenant operation, production monitoring and legal/source-contract review.

The ML lab intentionally remains separate from operational price recommendations. Joining them requires real history, prediction-time feature availability, better drift evaluation and causal or controlled evidence for interventions. Adding an LLM label would not resolve those requirements.

## Demo sequence
1. Open **Pricing cockpit** and compare the sale-week and cost-pressure presets.
2. Open **Decision workbench**, inspect a contribution problem or stale-evidence case, and record a reasoned defer/accept decision. Export its evidence.
3. Open **Demand model lab**, run the normal synthetic benchmark, then the shock test. Compare MAE, bias and interval coverage.
4. Download the daily-history template to show exactly what merchant data would be needed.
5. Open **Competitor monitor** and explain the configured-source requirement and demo/live separation.
