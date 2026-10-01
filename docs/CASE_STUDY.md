# PricePilot case study

## Problem
A small wearable retailer must reconcile market prices with its own sourcing costs, stock and contribution targets. A low competitor offer is not useful if it is unavailable or old, and a plausible recommendation is unsafe if it violates unit economics.

## Design
The Germany-focused scenario models EUR consumer prices, net replacement/operating costs and configurable VAT. Delivered seller offers are deduplicated and filtered by freshness. Six deterministic policies propose prices under a shared margin floor; missing evidence blocks pricing and large changes require review.

The interface and HTTP API share an application service. SQLite provides transactions and optimistic edits. Demo workspaces are separate from persistent data so experimentation cannot overwrite a merchant's catalog.

## Data and evidence
The bundled scenario contains 24 real-model references and 96 synthetic competitor observations, with simulated costs, prices, inventory and sales. It deliberately includes weak/stale evidence and cost pressure. The separate demand lab generates 365 daily synthetic records and trains an interpretable regression model; this is not real German sales history.

The evaluation script compares policy constraints and decisions across cost scenarios. See EVALUATION.md for methods and limitations. No revenue uplift or merchant adoption is claimed.

## Engineering lessons
The original Iran prototype exposed several useful failure modes: a premium-market cap could override a margin floor; nearest rounding could undercut a floor; invalid API requests could produce server errors; a missing processed file could trigger destructive demo seeding. The current work adds regression checks and introduces a clean EUR domain rather than silently relabelling historical amounts.

## Next validation
The browser now includes an interactive cockpit, an evidence-based review journal and temporal demand-model evaluation. The next validation is permissioned real sales/source data, user workflow testing and a controlled shadow pilot. See PRODUCT_STRATEGY.md and MODEL_CARD.md for boundaries and evidence.
