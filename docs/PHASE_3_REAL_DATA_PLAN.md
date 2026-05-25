# Phase 3: Real Market Data Foundation

## Overview

Phase 3 establishes a data architecture that separates **public market observations** from **retailer internal data**, creating a realistic foundation for pricing intelligence in volatile markets without relying on scraping or ML.

---

## Core Principles

### 1. Public vs. Internal Data Separation

**Public Market Observations** (collected, aggregated, shared):
- Price listings from Torob, Digikala, smaller online stores
- Seller names and availability status
- Warranty information (public)
- No claimed knowledge of competitor:
  - Inventory levels
  - Sales volumes
  - Conversion rates
  - Cost prices
  - Pricing strategies

**Retailer Internal Data** (confidential, demo/fictional):
- Our current retail prices
- Our cost prices
- Our inventory levels
- Our sales history (7d, 30d)
- Our target margins
- Our pricing strategy selection
- Our conversion metrics (if applicable)

### 2. Global Reference Data

**USD Base Prices** (external reference, collected manually or via compliant channels):
- Product: Apple Watch Ultra, Model: GPS+Cellular, Base USD: $799
- These prices act as anchors for currency-adjusted pricing
- Sourced from official retail sites or industry reports (no scraping)

---

## Data Architecture

```
data/
├── raw/
│   ├── market_observations_template.csv      ← Public market data
│   ├── retailer_internal_demo_template.csv   ← Demo internal data
│   └── global_usd_reference_template.csv     ← USD anchors
├── processed/
│   └── market_aggregates.csv                 ← Aggregated market stats
└── README.md                                 ← Data collection guides
```

### Market Observations Template
**Source:** Manual collection from public websites (Phase 3+)

| Column | Purpose |
|--------|---------|
| `observation_id` | Unique timestamp-based ID for each observation |
| `observed_at` | When the data was collected |
| `product_id` | Internal product ID (links to USD reference) |
| `product_query` | Search term used (e.g., "Apple Watch Ultra GPS") |
| `normalized_product_name` | Standardized product name |
| `brand` | Brand name |
| `model` | Model name |
| `source` | Website name (e.g., "Torob", "Digikala", "TechStore1") |
| `source_url` | URL or page reference |
| `seller_name` | Merchant/seller name |
| `listed_price` | Price in Toman (local currency) |
| `availability_status` | "available", "low_stock", "unavailable" |
| `warranty` | Warranty type (if visible) |
| `notes` | Any additional observations |

**Use Case:**
- 100s of observations per day from multiple sources
- Aggregated to calculate `market_min_price`, `market_median_price`, `market_max_price`
- Provides context for competitor positioning

### Retailer Internal Demo Template
**Source:** Our fictional smartwatch store's operational data

| Column | Purpose |
|--------|---------|
| `product_id` | Links to global USD reference |
| `our_current_price` | What we're selling at (Toman) |
| `our_cost_price` | What we paid for stock (Toman) |
| `our_inventory` | Units in stock |
| `our_sales_7d` | Units sold in last 7 days |
| `our_sales_30d` | Units sold in last 30 days |
| `our_target_margin` | Target profit margin % |
| `our_strategy` | Pricing strategy (balanced, trust_builder, etc.) |

**Use Case:**
- Single row per product
- Updated daily or weekly
- Never shared publicly (confidential)
- Inputs to `recommend_price()` for Phase 2 schema

### Global USD Reference Template
**Source:** External reference (official retailers, industry reports)

| Column | Purpose |
|--------|---------|
| `product_id` | Unique product identifier |
| `brand` | Brand name |
| `model` | Model name |
| `base_usd_price` | Official or retail USD price |
| `base_usd_price_source` | Source (e.g., "official_site", "best_buy", "report") |
| `source_url` | Reference URL or note |
| `observed_at` | When the reference was set |
| `notes` | Version, region, or other context |

**Use Case:**
- Anchors for currency-based pricing
- Multiply by `usd_rate` to get `theoretical_toman_price`
- Compare against `market_median_price` to calculate `iran_market_premium_pct`

---

## Data Collection Pipeline (Phase 3+)

### Stage 1: Manual Collection (MVP - Current)
```
1. Team manually visits Torob.com, Digikala.com, online stores
2. Records observations in market_observations_template.csv
3. Combines with USD reference and internal data
4. Runs market_aggregation.py to produce market_aggregates.csv
5. Dashboard loads aggregates + internal data → recommendations
```

### Stage 2: Compliant Collection (Future)
- Explore public APIs (Digikala may provide limited market data)
- Verify compliance with ToS before automated collection
- Use respectful polling rates (not aggressive scraping)
- Cache data to minimize requests

### Stage 3: Real-Time Integration (Post-MVP)
- Establish data partnerships with market platforms
- Automate data flows with proper attribution
- Monitor data freshness and quality

---

## Aggregation Logic

**Input:** `market_observations_template.csv` with 100s of rows

**Output:** `market_aggregates.csv` with product-level summaries

```python
def aggregate_market_observations(df):
    """
    Group market observations by product_id and calculate aggregates:
    - market_min_price: Lowest listed price
    - market_median_price: Middle price
    - market_max_price: Highest listed price
    - market_avg_price: Average price
    - seller_count: Total unique sellers
    - available_seller_count: Sellers with "available" status
    - price_spread_percent: (max - min) / median as %
    """
```

Example aggregated output:
```
product_id  | market_min   | market_median | market_max | seller_count | available_count | spread %
APUL-GPS-1  | 32,500,000   | 35,200,000    | 38,900,000 | 12           | 10              | 19.3%
```

---

## Design Constraints

✅ **What Phase 3 Includes:**
- Manual CSV templates for real data
- Aggregation functions (no ML, pure logic)
- Separation of public and internal data
- USD reference anchors
- Test coverage for aggregation
- Documentation

❌ **What Phase 3 Excludes:**
- Scraping of any kind
- Machine learning models
- External APIs (until compliance verified)
- Additional dependencies
- Automatic price fetching
- Competitor intelligence beyond public listings

---

## Next Steps

1. **Data Collection Dry-Run:**
   - Manually collect 50-100 observations for 5 test products
   - Verify data quality and consistency

2. **Aggregation Validation:**
   - Run aggregation on test data
   - Verify min/median/max calculations
   - Check seller count accuracy

3. **Integration Testing:**
   - Load market aggregates into Phase 2 schema
   - Verify recommendation engine still works
   - Test dashboard with real (but demo) market data

4. **Compliance Review (Before Scaling):**
   - Review Torob.com, Digikala.com ToS
   - Identify if public API exists
   - Plan ethical collection strategy

---

## FAQ

**Q: Will we scrape websites?**
A: No. Phase 3 uses manual collection. Future phases may use compliant APIs, but only after ToS review.

**Q: Do we have access to competitor data?**
A: Only public listings (price, availability, warranty). We don't claim to know their inventory, sales, costs, or strategies.

**Q: How is internal data kept confidential?**
A: It's stored separately, never exposed in market observations, and only used for our recommendation logic.

**Q: Can we validate market aggregates?**
A: Yes, with manual spot-checks against the websites. Tests verify min/median/max calculations.

**Q: What if market data is missing for a product?**
A: Fallback to the product's `our_current_price` as a proxy until more observations accumulate.

---

## Success Criteria

- ✅ Market observations template created and documented
- ✅ Aggregation functions tested and working
- ✅ Internal data template provides realistic demo inputs
- ✅ USD reference template anchors pricing
- ✅ Recommendation engine uses aggregated market data
- ✅ Dashboard displays market insights without claiming knowledge we don't have
- ✅ All tests pass, no new dependencies added
