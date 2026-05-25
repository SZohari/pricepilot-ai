# Copilot Instructions

You are working on a portfolio-grade data product called "Inflation-Aware Pricing Intelligence System".

Before making changes, always read:

- PROJECT_BRIEF.md
- ROADMAP.md
- README.md

## Main Goal

Build a lightweight pricing intelligence dashboard for volatile retail markets, initially focused on smartwatches in Iran.

This is an MVP, not a full SaaS product.

## Development Principles

- Keep the project simple and understandable.
- Prefer readable code over complex abstractions.
- Do not introduce heavy frameworks unless requested.
- Do not add LangGraph, PyTorch, Docker, or Next.js in the MVP unless explicitly asked.
- Start with Python, Pandas, Scikit-learn, Streamlit, and SQLite.
- Every pricing recommendation must be explainable.
- Business logic should be separated from UI code.
- Avoid hardcoding logic directly inside Streamlit components.
- Keep functions small and testable.

## Suggested Project Structure

```txt
src/
  data/
    load_data.py
    sample_data_generator.py
  pricing/
    rules.py
    recommendation.py
    risk.py
  features/
    feature_engineering.py
  dashboard/
    app.py
  utils/
    formatting.py

data/
  raw/
  processed/

notebooks/
docs/
tests/
Coding Style
Use type hints where useful.
Use clear function names.
Add docstrings for business-critical functions.
Avoid unnecessary comments.
Do not over-engineer.
Prefer deterministic rule-based logic before adding machine learning.
Pricing Logic Requirements

The recommendation engine should consider:

current price
cost price
target margin
inventory level
competitor median price
exchange-rate change
recent sales
conversion rate
Output Format

Each pricing recommendation should return:

product_id
product_name
current_price
recommended_price
action
risk_level
expected_margin
explanation
triggered_rules
Safety Rules

Do not implement automatic real-world price changes.
Do not scrape websites unless a specific task asks for it.
Do not store API keys or secrets in the repository.