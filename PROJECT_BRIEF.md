# PricePilot project brief

## Purpose
A personal portfolio product at the intersection of **Data, AI and Business**, intended to support applications for a practice-oriented master's pathway in Germany.

## User and decision
A small German wearable retailer needs a reviewable answer to: "Which products need a pricing decision today, what evidence supports the proposal, and what constraints prevent a safe change?"

## Product position
Retail Decision Intelligence. The initial domain is wearables, the supported runtime currency is EUR, and the UI/documentation language is English. Germany is the first configurable business context, not a claim of live market access or commercial validation.

## Current scope
- Real-model 24-product catalog with synthetic financials, isolated by browser workspace.
- Typed product and observation contracts; explicit gross/net money.
- Source freshness, seller deduplication and availability-aware aggregation.
- Six deterministic policies, margin floors, cost scenarios and explanations.
- Shared application service, transactional SQLite, append-only observations and mutation history.
- FastAPI and interactive browser UI; optional legacy Streamlit adapter.
- Supervised daily demand benchmark with chronological splits, naive/seasonal baselines, error bands and a shock failure case.
- Ranked decision workbench, reasoned accept/reject/defer journal and exportable versioned evidence snapshots.

## Three competency threads
**Data:** schema design, source provenance, quality gates, transaction safety, versioned contracts.
**AI:** trained ridge demand prediction, time-ordered validation and holdouts, baseline comparison, uncertainty diagnostics, reproducibility and model-failure reporting. Deterministic operational price guardrails remain independent.
**Business:** contribution economics, inventory pressure, market positioning, human review and measurable workflow outcomes.

## Honest evidence
The operational price engine is deterministic; the separate demand lab contains trained ML. Synthetic evaluation does not establish merchant accuracy or revenue uplift. A generic collector exists but has no configured real retailer sources. Production tenancy, automated repricing and legally complete tax/promotion implementation are not claimed.

## Engineering principles
Keep decision logic independent of frameworks; keep a single computation path for API and UI; use Decimal for money; validate at boundaries; preserve historical source data; prefer a modular monolith before distributed services.

## Success criteria
The demo must run from documented commands, show why it abstains or requests review, preserve margin constraints under cost shocks, reject invalid data, and provide a clear path to evaluating real outcomes.
