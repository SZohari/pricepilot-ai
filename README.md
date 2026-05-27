# PricePilot AI

PricePilot AI is an explainable pricing decision-support dashboard for a smartwatch and wearable retailer operating in Iran's volatile retail market. It combines public market observations, internal store data, global USD price references, and exchange-rate snapshots to help a seller review competitive positioning and choose a pricing strategy.

This project is intentionally human-in-the-loop: it assists pricing decisions, but does not automatically change store prices.

## Portfolio Links

- [Case Study](docs/CASE_STUDY.md)
- [Screenshot Guide](docs/SCREENSHOT_GUIDE.md)
- [Phase 2 Design](docs/PHASE_2_DESIGN.md)
- [Real Data Plan](docs/PHASE_3_REAL_DATA_PLAN.md)

## Features

- Streamlit dashboard with recommendations, analytics, product detail views, and USD shock simulation
- Six explainable pricing strategies for different retail goals
- Readable Iranian toman entry with comma normalization, million-toman preview, and rial equivalent
- Market Update Console for manually recording daily competitor prices
- FX snapshot entry that recalculates theoretical toman prices after rebuilding
- Add New Product workflow for maintaining product, store, and global reference records
- Our Store Data workflow for updating current price, cost, inventory, sales, margin, and selected strategy
- Processed Real Market Dataset mode backed by a reproducible CSV build pipeline
- Lightweight FastAPI backend for recommendations, product lookup, and dataset builds
- Defensive validation and automated test coverage for the data and recommendation workflow

## Architecture

```text
data/raw/
  products_master.csv
  market_observations_template.csv
  daily_market_updates.csv
  retailer_internal_demo_template.csv
  global_usd_reference_template.csv
  fx_rate_snapshots.csv
          |
          v
src/data/build_pricing_dataset.py
          |
          v
data/processed/dashboard_pricing_data.csv
          |
          v
src/pricing/ (recommendation, strategy, and risk modules)
          |                         |
          v                         v
src/dashboard/app.py          src/api/main.py
```

Key modules:

| Path | Purpose |
| --- | --- |
| `src/dashboard/app.py` | Streamlit experience and assisted update forms |
| `src/data/manual_entry.py` | Validated product, store, market, and FX persistence helpers |
| `src/data/build_pricing_dataset.py` | Builds dashboard-ready product records |
| `src/data/market_aggregation.py` | Aggregates public market observations |
| `src/pricing/strategies.py` | Produces strategy-specific price candidates |
| `src/pricing/recommendation.py` | Combines price, action, risk, and explanation output |
| `src/api/main.py` | Thin FastAPI interface over dataset builds and recommendations |

## Pricing Strategies

| Strategy | Intent |
| --- | --- |
| Trust Builder | Stay close to the low end of the market to build confidence and volume |
| Balanced | Price near the market median while protecting margin |
| Profit Protection | Favor margin preservation and theoretical replacement-cost signals |
| Market Penetration | Compete aggressively to improve market share |
| Premium Positioning | Maintain a higher-price market position |
| Clearance / Cashflow | Support inventory reduction and cash recovery |

The strategies are deterministic and explainable. Price changes remain subject to seller review.

## How To Run

Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe scripts\build_pricing_dataset.py
.\.venv\Scripts\python.exe -m streamlit run src\dashboard\app.py
```

Open `http://localhost:8501` and select either sample data or **Processed Real Market Dataset** in the sidebar.

## FastAPI Backend

The Streamlit dashboard remains the user interface. A lightweight FastAPI service exposes the same existing dataset and recommendation functions for integration demos:

- `GET /health` checks service availability.
- `GET /products` returns product metadata from the processed dataset.
- `POST /recommend-price` evaluates one product payload.
- `POST /recommendations/batch` evaluates every processed dataset row.
- `POST /build-dataset` runs the existing processed dataset build workflow.

Run the API from the project root:

```powershell
.\.venv\Scripts\python.exe -m uvicorn src.api.main:app --reload
```

Interactive API documentation is available at `http://127.0.0.1:8000/docs`.

## Data Workflow

The **Market Update** tab supports the operational demo workflow:

1. Add a product, if it is not already in the catalog.
2. Update our store data: current price, cost, inventory, sales, target margin, and strategy.
3. Enter observed market prices for a selected product.
4. Record the latest FX rate in toman.
5. Click **Run Build Pipeline** or run the build script from PowerShell.
6. Select **Processed Real Market Dataset** to review updated recommendations.

Raw sources:

| File | Contents |
| --- | --- |
| `data/raw/products_master.csv` | Product catalog, URLs, status, and priority |
| `data/raw/market_observations_template.csv` | Detailed public observation baseline |
| `data/raw/daily_market_updates.csv` | Manually recorded latest market prices |
| `data/raw/retailer_internal_demo_template.csv` | Seller-owned price, cost, inventory, sales, and strategy data |
| `data/raw/global_usd_reference_template.csv` | Base USD references per product |
| `data/raw/fx_rate_snapshots.csv` | Saved exchange-rate snapshots |

Output:

```text
data/processed/dashboard_pricing_data.csv
```

Daily updates override observed market aggregates only where values are provided. Latest valid FX snapshots override the reference exchange rate and trigger recalculation of `theoretical_toman_price` and `iran_market_premium_pct`.

## No Scraping By Design

This version does not scrape retailer sites. The first portfolio release emphasizes traceable inputs, explicit seller review, stable schemas, and compliance-friendly manual observation. Automated collection can be introduced later only where source terms, quality controls, and operational ownership are clear.

## Testing

Run the complete test suite:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\ -v --tb=short
```

Run the project verification and dashboard import checks:

```powershell
.\.venv\Scripts\python.exe scripts\verify_project.py
.\.venv\Scripts\python.exe -c "from src.dashboard import app; print('dashboard import ok')"
```

The automated tests cover formatting and Persian-digit inputs, market and FX persistence, product/store updates, dataset building, aggregation, and recommendation behavior.

## Roadmap

- Move raw CSV persistence to a database with audit history
- Integrate a reliable live FX API
- Add compliant, source-approved market data collectors
- Package reproducible deployment with Docker
- Explore ML forecasting once enough trustworthy historical observations exist

## Scope

PricePilot AI is a portfolio MVP and decision-support tool, not an autonomous repricing system. Sample and manually entered values are intended for demonstration and analysis; a human seller remains responsible for any commercial price change.
