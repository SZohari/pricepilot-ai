# Inflation-Aware Pricing Intelligence System

## Project Goal

This project is a data-driven pricing intelligence system designed for volatile retail markets, with a focus on the Iranian smartwatch market.

The system helps small and medium retailers make better pricing decisions by combining product cost, competitor prices, inventory level, exchange-rate movement, sales history, and target margin.

The first version is not an automatic price-changing system. It is a decision-support dashboard that recommends price actions and explains the reasoning behind each recommendation.

## Target Market

Initial focus: smartwatches and wearable devices in Iran.

Reason for choosing this category:

- Prices are sensitive to exchange-rate changes.
- Products are actively sold online.
- Competitor prices are visible and comparable.
- The category is commercially attractive but less legally complicated than mobile phones.
- It contains enough SKUs for meaningful analysis while remaining manageable for an MVP.

## Main User

The primary user is a small or medium retailer who sells smartwatches online or offline and needs help deciding when to increase, decrease, or hold prices.

## Core Business Questions

1. Is the current selling price still profitable?
2. Is our price too low compared to competitors?
3. Is our price too high and hurting sales?
4. Should we increase the price because replacement cost or exchange rate has increased?
5. Should we reduce the price because inventory is high and demand is weak?
6. What will happen if the USD rate increases by 5%, 10%, or 15%?
7. Which products are at risk because of low margin, low inventory, or high market volatility?

## MVP Scope

The MVP includes:

- Product dataset
- Competitor price fields
- Inventory level
- Cost price
- Exchange-rate movement
- Rule-based pricing recommendation engine
- Risk scoring
- Streamlit dashboard
- Scenario simulator
- Explanation for every price recommendation

## Out of Scope for MVP

The MVP will not include:

- Automatic price updates on real stores
- Real-time scraping at scale
- Complex deep learning models
- Multi-agent LangGraph system
- Full SaaS authentication and billing
- Direct POS integration
- Enterprise-level deployment

These features may be added in later phases.

## Recommended Tech Stack for MVP

- Python
- Pandas
- NumPy
- Scikit-learn
- Streamlit
- SQLite
- Plotly

## Later Tech Stack

- FastAPI
- PostgreSQL
- Next.js
- Docker
- LangGraph
- MLflow

## Initial Dataset Columns

- product_id
- product_name
- brand
- model
- category
- current_price
- cost_price
- inventory
- competitor_min_price
- competitor_median_price
- competitor_max_price
- usd_rate
- usd_change_7d
- sales_7d
- sales_30d
- views_30d
- conversion_rate
- target_margin
- supplier_lead_time_days

## Pricing Decision Types

The system can recommend one of the following actions:

- increase_price
- decrease_price
- hold_price
- urgent_review
- stop_selling_temporarily

## Explanation Requirement

Every recommendation must include a human-readable explanation.

Example:

"Price increase is recommended because inventory is low, USD increased by 6% in the last 7 days, competitor median price is higher, and the current profit margin is below the target margin."

## Success Criteria

The project is successful if it can:

1. Load a structured retail pricing dataset.
2. Calculate current margin and market position.
3. Recommend price actions for each product.
4. Explain each recommendation clearly.
5. Simulate exchange-rate changes.
6. Show results in a clean dashboard.
7. Be presented as a portfolio project for Data Analyst, Data Engineer, or AI/Data Engineer roles.