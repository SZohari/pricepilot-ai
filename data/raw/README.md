# Real Data Template

This directory contains templates and examples for importing real smartwatch pricing data.

## How to Use

1. **Start with the template:** Use `smartwatch_real_data_template.csv` as a starting point.
2. **Collect your data:** Fill in the columns with your actual product and pricing data.
3. **Upload to dashboard:** Use the "Upload Custom Data" feature in the Streamlit dashboard.

## Data Collection Guidelines

### Price Data
- **current_price**: Your current selling price (in Toman)
- **cost_price**: Your acquisition cost (in Toman)
- **competitor_min_price**: Lowest competitor price observed
- **competitor_median_price**: Most common competitor price
- **competitor_max_price**: Highest competitor price observed

### Market Data
- **inventory**: Current stock level (units)
- **sales_7d**: Units sold in last 7 days
- **sales_30d**: Units sold in last 30 days
- **views_30d**: Product page views in last 30 days
- **conversion_rate**: Sales / Views (or estimate from your data)

### Exchange Rate
- **usd_rate**: Current USD to Toman exchange rate
- **usd_change_7d**: Percentage change in USD rate over last 7 days

### Configuration
- **target_margin**: Your desired profit margin (0.25 = 25%)
- **supplier_lead_time_days**: Days to receive new stock

## No Scraping

This MVP does not include web scraping. All data must be:
- Manually entered
- Imported from your store system
- Exported from your analytics platform
- Observed from market research

## Example CSV Format

```
product_id,product_name,brand,model,category,current_price,cost_price,inventory,competitor_min_price,competitor_median_price,competitor_max_price,usd_rate,usd_change_7d,sales_7d,sales_30d,views_30d,conversion_rate,target_margin,supplier_lead_time_days
SW001,Fitbit Inspire 3,Fitbit,Inspire 3,Mid-Range,3500000,1800000,45,3400000,3600000,3800000,45100,1.5,12,35,520,0.067,0.35,14
SW002,Samsung Galaxy Watch 6,Samsung,Galaxy Watch 6,Premium,8500000,4200000,28,8200000,8600000,9000000,45100,1.5,8,25,380,0.066,0.35,10
```

## Validation

The dashboard will automatically validate your CSV:
- Checks for all required columns
- Detects invalid data (negative prices, out-of-range margins)
- Shows clear error messages
- Does not crash on bad data

## Questions?

See the PROJECT_BRIEF.md and README.md for more information about the pricing engine logic.
