# Phase 2 Design: Market-Aware Retail Pricing Strategy Dashboard

## Project Direction

The next version of the product will transform the MVP from a simple pricing simulator into a Market-Aware Retail Pricing Strategy Dashboard for a fictional smartwatch retailer in Iran. The focus will shift from generic pricing recommendations to actionable, strategy-driven pricing tailored for a retailer operating in a volatile, competitive market.

## Key Concepts

### 1. Fictional Retailer Perspective
We are a fictional smartwatch retailer. Our dashboard will distinguish between:
- **Internal Retailer Data**: Data only we know (e.g., our cost, inventory, sales)
- **Market Data**: Data observed from public sources (e.g., Torob, Digikala, other online stores, manual CSV collection)

### 2. Data Provenance and Defensibility
- We do **not** claim to know competitors' inventory, sales, cost price, or conversion rate.
- Fields like `views_30d`, `conversion_rate`, `shipping_fee`, and `shipping_eta` will be removed or de-emphasized, as they are not defensible from public data.

### 3. Global/Base USD Price Concept
A new concept of `base_usd_price` is introduced:
- **base_usd_price**: The global reference price for a product (e.g., MSRP, Amazon, or other global sources)
- **base_usd_price_source**: The source of the global price (e.g., "Amazon", "Official MSRP", "Manual Reference")
- **usd_rate**: The current exchange rate (USD to toman)
- **theoretical_toman_price**: `base_usd_price * usd_rate`
- **iran_market_premium_pct**: `(market_median_price - theoretical_toman_price) / theoretical_toman_price`

The `base_usd_price` is not necessarily the retailer's actual purchase cost, but a reference for market comparison.

### 4. Data Schema (Phase 2)

| Field                     | Description                                                      |
|--------------------------|------------------------------------------------------------------|
| product_id               | Unique product identifier                                        |
| product_name             | Name of the product                                              |
| brand                    | Brand                                                            |
| model                    | Model                                                            |
| category                 | Category (e.g., Budget, Premium)                                 |
| base_usd_price           | Global reference price in USD                                     |
| base_usd_price_source    | Source of the global price (Amazon, MSRP, etc.)                  |
| usd_rate                 | USD to toman exchange rate                                       |
| theoretical_toman_price  | Calculated: base_usd_price * usd_rate                            |
| market_min_price         | Minimum observed market price (toman)                            |
| market_median_price      | Median observed market price (toman)                             |
| market_max_price         | Maximum observed market price (toman)                            |
| market_avg_price         | Average observed market price (toman)                            |
| seller_count             | Total number of sellers observed                                 |
| available_seller_count   | Sellers with product in stock                                    |
| torob_min_price          | Minimum price observed on Torob                                  |
| torob_median_price       | Median price observed on Torob                                   |
| digikala_price           | Price observed on Digikala                                       |
| our_current_price        | Our current retail price                                         |
| our_cost_price           | Our internal cost price                                          |
| our_inventory            | Our inventory count                                              |
| our_sales_7d             | Our sales in the last 7 days                                     |
| our_sales_30d            | Our sales in the last 30 days                                    |
| our_target_margin        | Our target margin                                                |
| our_strategy             | Our selected pricing strategy                                    |
| observed_at              | Timestamp of data observation                                    |

### 5. Pricing Strategies

The dashboard will support multiple pricing strategies, each with a business rationale:

1. **Trust Builder**: Price at or below market median to build customer trust and drive volume.
2. **Balanced**: Price near market median, balancing margin and competitiveness.
3. **Profit Protection**: Prioritize margin, price above market median if possible.
4. **Market Penetration**: Aggressively price below market to gain share or clear new inventory.
5. **Premium Positioning**: Price above market to signal quality or exclusivity.
6. **Clearance / Cashflow**: Price at or below cost to clear inventory and generate cash quickly.

Each strategy will have a clear explanation in the dashboard, and the user can see the recommended price for each strategy.

### 6. Recommendation Output (Phase 2)

Instead of a single recommended price, the output will include:
- `trust_builder_price`
- `balanced_price`
- `profit_protection_price`
- `market_penetration_price`
- `premium_positioning_price`
- `clearance_price`
- `selected_strategy_price`
- `strategy_explanation`

This allows the retailer to compare and select the most appropriate strategy for each product.

### 7. Data Types: Real vs. Demo
- **Real Market Data**: Prices, seller counts, and availability observed from public sources (Torob, Digikala, etc.) or manual CSV collection.
- **Demo Retailer Internal Data**: Our own cost, inventory, and sales, which are fictional for demo purposes.

### 8. Out of Scope
- No scraping or automated data collection is included yet; all market data is assumed to be collected manually (e.g., via CSV).
- No machine learning, FastAPI, Docker, Next.js, or LangGraph will be added at this stage.
- No claims are made about competitors' internal data (inventory, cost, sales, conversion rate).

### 9. Future Directions
- Scraping and automated data collection can be added in the future to replace manual CSVs.
- The dashboard can evolve into a real SaaS product with API integrations and advanced analytics.

---

# Summary
Phase 2 will make the dashboard a more realistic, market-aware tool for a fictional retailer, with clear separation between internal and market data, defensible data provenance, and actionable, strategy-driven pricing recommendations.
