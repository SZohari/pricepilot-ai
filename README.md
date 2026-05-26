# Inflation-Aware Pricing Intelligence System

A lightweight MVP dashboard for pricing smartwatches in volatile retail markets (Iran).

## Phase 2 Design

See [docs/PHASE_2_DESIGN.md](docs/PHASE_2_DESIGN.md) for the next version design and project direction.

## Features

- **Rule-based pricing recommendations** with explainable logic
- **Risk scoring** for high-volatility products
- **Scenario simulator** to test USD exchange rate shocks
- **Interactive dashboard** with KPIs, filters, and charts
- **Sample data generator** for testing and demo

## Quick Start (Windows PowerShell)

### 1. Create and activate virtual environment

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### 2. Upgrade pip and install dependencies

```powershell
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### 3. Run tests

```powershell
pytest
```

### 4. Run the Streamlit dashboard

```powershell
streamlit run src/dashboard/app.py
```

The dashboard will open at `http://localhost:8501`

## Building Dashboard Data from Raw Market Inputs

To convert raw market observations into dashboard-ready pricing data:

```powershell
python scripts/build_pricing_dataset.py
```

This pipeline:
1. Loads market observations from `data/raw/market_observations_template.csv`
2. Loads retailer internal data from `data/raw/retailer_internal_demo_template.csv`
3. Loads USD reference prices from `data/raw/global_usd_reference_template.csv`
4. Aggregates market data by product
5. Calculates `theoretical_toman_price` and `iran_market_premium_pct`
6. Outputs to `data/processed/dashboard_pricing_data.csv`

The output is ready for the dashboard or further analysis.

## Project Structure

```
src/
  data/
    sample_data_generator.py    # Generate smartwatch dataset
  pricing/
    rules.py                     # Pricing rules engine
    risk.py                      # Risk scoring
    recommendation.py            # Main recommendation engine
  dashboard/
    app.py                       # Streamlit dashboard

data/
  processed/                     # Generated datasets

tests/
  test_pricing_engine.py         # Unit tests

docs/
```

## How It Works

1. **Load data** from sample generator or CSV
2. **Apply pricing rules** based on cost, margin, competitor prices, and market conditions
3. **Score risk** for each product (low/medium/high/critical)
4. **Generate recommendations** with explanations
5. **Simulate scenarios** (e.g., USD rate changes)

## Key Concepts

- **Target Margin**: Desired profit margin for products
- **Competitor Median Price**: Market benchmark
- **USD Change**: Exchange rate volatility indicator
- **Risk Level**: Composite risk metric (inventory, margin, volatility, lead time)
- **Action**: Recommended price change (increase/decrease/hold/urgent_review)

## Real Market Data Foundation (Phase 3)

Phase 3 introduces a data architecture that separates **public market observations** from **retailer internal data**. See [docs/PHASE_3_REAL_DATA_PLAN.md](docs/PHASE_3_REAL_DATA_PLAN.md) for detailed strategy.

### Data Templates

**Public Market Observations** → `data/raw/market_observations_template.csv`
- Price listings from Torob, Digikala, and online stores
- Seller names, availability status, warranty info
- No scraping yet; manual collection is first step

**Retailer Internal Data** → `data/raw/retailer_internal_demo_template.csv`
- Our current prices, costs, inventory, sales history
- Confidential to our store (demo/fictional data)
- Never mixed with public market data

**Global USD Reference** → `data/raw/global_usd_reference_template.csv`
- Base USD prices for products (anchors for currency adjustments)
- From official retailers, industry reports (no scraping)

**Market Aggregation Utilities** → `src/data/market_aggregation.py`
- Pure functions to aggregate market observations
- Calculates: min/median/max prices, seller counts, price spreads
- Output feeds into Phase 2 recommendation engine

### Using Real Data

The dashboard supports two data modes:

### 1. Sample Data (Default)
- Use pre-generated smartwatch dataset for testing and exploration
- Deterministic data (same dataset every time with same seed)
- Good for understanding the system before importing real data

### 2. Upload Custom CSV
- Click **"Upload CSV"** in the sidebar to import your own data
- CSV must include all required columns (see template below)
- Dashboard validates data and shows clear error messages
- No data is saved to the server

## CSV Data Template

A template CSV file is provided in `data/raw/smartwatch_real_data_template.csv`

### Required Columns

```
product_id              Product identifier (string)
product_name            Product name (string)
brand                   Brand name (string)
model                   Model name (string)
category                Category: Budget/Mid-Range/Premium (string)
current_price           Current selling price in Toman (float)
cost_price              Acquisition cost in Toman (float)
inventory               Current stock level (integer)
competitor_min_price    Lowest competitor price (float)
competitor_median_price Most common competitor price (float)
competitor_max_price    Highest competitor price (float)
usd_rate                Current USD to Toman rate (float)
usd_change_7d           USD rate change in last 7 days (%) (float)
sales_7d                Units sold in last 7 days (integer)
sales_30d               Units sold in last 30 days (integer)
views_30d               Product page views in last 30 days (integer)
conversion_rate         Sales / Views ratio (0-1) (float)
target_margin           Desired profit margin (0-1) (float, e.g., 0.35 = 35%)
supplier_lead_time_days Days to receive new stock (integer)
```

### Data Collection Tips

- **Prices**: Export from your store system or POS
- **Inventory**: Current stock from inventory management system
- **Competitor Prices**: Manual observation or market research data
- **Sales**: Aggregate from store analytics
- **USD Rate**: Historical rate from exchange data providers

### No Scraping

This MVP does **not** include web scraping. All data must be:
- Manually entered into the CSV
- Exported from your store system
- Imported from your analytics platform
- Based on manual market observations

See `data/raw/README.md` for more details and examples.

## Formatting and Display

The dashboard automatically formats all prices and metrics for readability:

- **Prices**: Formatted with comma separators + "تومان" suffix (e.g., "7,800,000 تومان")
- **Margins**: Displayed as signed percentages (e.g., "+35.0%")
- **Actions**: Labeled with icons (📈 Increase, 📉 Decrease, etc.)
- **Risk Levels**: Color-coded and labeled (✅ Low, ⚠️ Medium, 🔴 High, 🚨 Critical)

## Dependencies

- Python 3.8+
- pandas - Data manipulation
- numpy - Numerical computing
- streamlit - Interactive dashboard
- plotly - Data visualization
- pytest - Testing

All dependencies are installed by `pip install -r requirements.txt`

## Notes

This is an MVP for decision support, not an automatic pricing system. All price changes must be reviewed by a human decision-maker before implementation.
