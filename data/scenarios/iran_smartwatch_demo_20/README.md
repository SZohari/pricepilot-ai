# Iranian Smartwatch Market Demo Scenario

This folder contains a portfolio/demo dataset for PricePilot AI. It is not live scraped Iranian market data and should not be presented as real-time market intelligence.

The scenario includes 20 smartwatch and wearable products with plausible global reference prices, a fixed demo exchange rate of 170,000 toman per USD, retailer inventory/cost data, and 80 fictional market observations from sources such as Torob, Digikala, Emalls, and small online stores.

Use it to demonstrate the full workflow:

```bash
python scripts/load_demo_scenario.py
python scripts/build_pricing_dataset.py
streamlit run src/dashboard/app.py
```
