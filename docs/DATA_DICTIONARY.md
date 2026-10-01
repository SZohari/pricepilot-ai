# Data dictionary â€” v1 EUR contract

The complete machine-readable specification is exposed in FastAPI OpenAPI. Unknown fields and nonfinite numeric values are rejected.

| Entity / field | Meaning |
| --- | --- |
| Product.product_id | Stable SKU/variant identifier, not a display name |
| name / category / brand | Product model metadata |
| reference_url / reference_checked_on | Official HTTPS model reference and verification date; not a price source |
| data_origin | demo, merchant or unspecified; bundled financials are demo |
| currency | EUR in this version |
| current_price_gross | Consumer price including configured VAT |
| replacement_cost_net | Current per-unit sourcing cost excluding recoverable VAT |
| variable_cost_net | Additional per-unit operating costs excluding recoverable VAT |
| vat_rate | Decimal fraction; demo assumes 0.19 |
| fee_rate | Percentage fee as a fraction; interpret using fee_basis |
| fee_basis | net: revenue excluding VAT; gross: full customer payment including VAT |
| retail | Optional validated single-item order profile: exact variant/GTIN, historical purchase cost, itemised fulfilment costs, customer shipping, dated input confirmations |
| minimum_margin | Hard minimum contribution / net revenue |
| target_margin | Desired contribution / net revenue, not a guaranteed outcome |
| inventory | Nonnegative integer available store units |
| sales_7d / sales_30d | Aggregate unit sales; 7-day total cannot exceed 30-day total |
| strategy | One of six canonical strategy keys |
| Observation.seller | Merchant identifier; normalized case-insensitively for aggregation |
| price_gross / shipping_gross | Listed gross price plus gross delivery cost |
| available | Whether a customer could buy the observed offer |
| observed_on | Observation date, separate from ingestion time |
| source | Provenance description; demo explicitly labels synthetic data |
| Observation.data_origin | demo, live or unspecified; live collection sets live |
| source_url / observed_at | Public listing URL and UTC collection timestamp for live evidence |
| Scenario.as_of | Date at which market evidence is evaluated |
| Scenario.evidence_mode | all, demo or live; selected origin is filtered before market aggregation |
| cost_change_pct | Percent stress on replacement cost only; market observations stay fixed |
| max_age_days | Maximum observation age relative to as_of |
| review_change_pct | Gross price-change threshold that triggers human review |

Money inputs use up to two decimal places. Prices and replacement cost must be positive. Variable cost and shipping may be zero. Margin and fee rates are fractions; target margin plus fee rate must be less than one.

## Quality and comparability
Use observations for the same SKU/variant, comparable condition and warranty. Currency conversion and product matching are not inferred. The delivered market median uses only fresh, available latest seller offers. Fewer than three sellers triggers review; no sellers blocks pricing. A large price spread triggers a comparability warning.

Quality counters distinguish future, stale, unavailable and superseded records. The last three refer to the selected latest seller state or historical duplicates; they are not interchangeable business concepts.

## Import/export
JSON Dataset version 1.0 contains name, as_of, products and observations. Imports validate all records, references and duplicate IDs before persistence. Conflicts against existing workspace IDs roll back the entire import. Export is a consistent snapshot; API monetary fields are decimal strings.

The demo is a separate synthetic snapshot. Its reference date is not evidence of live ingestion. No personal customer data is collected.
