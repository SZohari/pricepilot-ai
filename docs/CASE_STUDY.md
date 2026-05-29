# PricePilot AI: Case Study

## Problem

Iranian consumer-electronics retailers operate in a pricing environment shaped by currency volatility, imported-product replacement cost, fragmented marketplace listings, and the practical confusion between toman and rial amounts. A price that is reasonable in the morning may be materially out of position after an exchange-rate move or a competitor update.

PricePilot AI explores a focused question: how can a wearable retailer make faster, more explainable pricing decisions while retaining human control?

## Target Domain

The project focuses on smartwatches and wearables. This category is a useful pricing case because products commonly have:

- Globally visible USD reference prices
- Locally variable import and availability premiums
- Comparable listings across public marketplaces
- Inventory, margin, and positioning decisions that differ by model

## Data Sources

The dashboard brings together four distinct data types:

| Source | Role |
| --- | --- |
| Public market observations | Listing prices and availability observations used to form market benchmarks |
| Our store internal data | Current selling price, cost, inventory, recent sales, target margin, and preferred strategy |
| Global USD reference price | International reference price for each wearable model |
| FX snapshots | Manually recorded toman exchange-rate snapshots used to convert USD references into local theoretical prices |

Keeping these sources separate matters. Public observations describe the market; internal store data describes the seller's own commercial position.

The demo scenario uses realistic market assumptions and public product references, but does not claim to be live scraped Iranian market data.

## Pipeline

```text
Raw data
  products, market observations, daily updates, store data, USD references, FX snapshots
        |
        v
Processed dataset
  product-level market benchmarks and derived currency fields
        |
        v
Strategy engine
  explainable price candidates, action, risk, and reasoning
        |
        v
Streamlit dashboard
  seller review, updates, rebuilding, and scenario exploration
```

The processing pipeline aggregates detailed observations, applies the latest provided daily market update fields, uses the latest valid positive FX snapshot when available, and recalculates theoretical toman price and market premium. This yields a reproducible processed dataset for the dashboard.

## Assisted Workflow

The **Market Update** console enables a seller to:

1. Add a product to the product, internal-data, and USD-reference records.
2. Maintain store-owned values such as price, cost, inventory, sales, margin, and selected strategy.
3. Enter daily public market prices with readable toman and rial previews.
4. Record a new FX snapshot.
5. Rebuild the processed dataset and review updated recommendations.

Iranian price entry uses comma-separated text normalization and immediate toman/million-toman/rial previews to reduce errors with very large numeric inputs.

## Pricing Strategies

The recommendation engine presents six explainable strategies:

| Strategy | Decision Context |
| --- | --- |
| Trust Builder | Stay competitively close to the market floor to earn buyer confidence |
| Balanced | Balance margin and market alignment near the median |
| Profit Protection | Protect profitability when replacement cost or scarcity pressure matters |
| Market Penetration | Price aggressively to compete for volume or share |
| Premium Positioning | Maintain a deliberate higher-value position |
| Clearance / Cashflow | Reduce inventory pressure and recover working capital |

The system does not silently impose a price. It exposes alternatives and rationale for a human decision-maker.

## Why No Scraping Initially

Automating collection too early can create unreliable inputs and unclear compliance responsibilities. Retail listing pages change, availability signals may be ambiguous, and collection rules differ by source. For a first deployment-quality portfolio iteration, traceability and predictable behavior matter more than acquisition volume.

The current system therefore demonstrates the product and analytical workflow without relying on brittle or unauthorized data collection.

## Why Manual Assisted Updates

Manual entry is not simply a placeholder; it is a useful operational design for the MVP:

- Sellers can verify each observed price and source link.
- The stored data has clear provenance and review ownership.
- The UI reduces toman/rial and large-number entry mistakes.
- The pipeline and recommendation logic can be evaluated before investing in automation.
- The same data model can later accept approved automated feeds.

## Future Roadmap

- **Database:** replace CSV persistence with auditable, multi-user storage.
- **Live FX API:** automate reliable exchange-rate ingestion with validation and history.
- **Compliant collectors:** add source-approved market observation collection where feasible.
- **FastAPI:** provide service endpoints for data operations and recommendations.
- **Docker:** make deployment and environment reproduction straightforward.
- **ML forecasting:** evaluate forecasting only after building sufficient trustworthy historical data.

## Outcome

PricePilot AI demonstrates an end-to-end, human-reviewed pricing intelligence workflow: capture real inputs, build consistent product-level data, generate strategy-aware recommendations, and explain the decision context in an interactive dashboard.
