# Architecture and extension points

## Modular monolith
```text
Browser ES modules -> FastAPI /api/v1
Optional Streamlit views
       \                            /
        application/PricingService
            |                 |
       domain policies    Repository protocol
       typed contracts         |
       Decimal money      SQLite adapter
```

The UI owns formatting and interaction. The API owns HTTP validation/status codes. Both call the same application service. The domain owns financial definitions, evidence selection, policy candidates and review decisions.

## Contracts
`src/domain/models.py` defines v1 schemas. Currency is explicitly EUR-only in this version: supporting another market requires an explicit policy/configuration change, not relabelling amounts. Monetary values cross JSON boundaries as decimal strings.

A product contains store-owned economics and a preferred strategy. An observation is an append-only, dated, seller-level delivered-price input. A scenario provides the analysis date, freshness horizon, cost stress and optional strategy override. A recommendation returns policy version, floor, selected price, alternative strategy candidates, quality counters and reasons.

The analysis date is required by the API to avoid accidental historical look-ahead. For each product/seller, the latest observation at or before this date wins. Same-date ties use input/insertion order. Seller names are trimmed and compared case-insensitively; production ingestion should resolve stable merchant IDs.

## Persistence
SQLite uses transactions, foreign keys and WAL. Product edits require an expected version. Duplicate imports roll back the entire batch. Observations are append-only; a newer unavailable offer supersedes an older available one. Audit payloads retain mutations; this is not a tamper-proof compliance audit system.

The repository protocol is the seam for PostgreSQL. Database schema version 3 adds advisory plans and action/outcome records while preserving earlier products, observations and decision reviews. Newer unknown versions are rejected. Reviews and catalog-linked plans store full decision/input snapshots and recheck product version and observation IDs inside a write transaction. Exact duplicate submissions are idempotent. Plan state transitions compare the expected prior status. A production migration runner is future work. JSON payload storage intentionally keeps this small project understandable; high-volume analytical queries will need relational columns and indexed read models.

Each browser demo session in src/web/app.py owns an in-memory repository, protected by a session-bound write token and an HttpOnly SameSite cookie. Demo state expires after two hours of inactivity or server restart. The optional Streamlit demo also owns its own repository. The standalone legacy API host defaults to a process-local demo repository. Set PRICEPILOT_DB_PATH for an explicitly persistent, shared local workspace; no implicit demo seeding occurs there.

## Scaling a future UX

The primary browser flow uses `api/advisor.py`, `application/advisor.py` and `domain/advisory.py`. It accepts unit-based goods and services without requiring a retail catalog. Optional catalog links attach live observations. The frontend performs no competing price optimization: all interactive consultation changes use the same server service. See `PRICING_CONSULTANT.md` for the operational boundary, required-outcome arithmetic and follow-up lifecycle.
A React/Next.js frontend can consume the versioned API with the same decision objects. No React dependency is needed now. Keep charting, filtering and locale formatting in presentation; keep money, quality gates and pricing rules in the service/domain.

Do not expose persistent mode to untrusted users yet. Read routes expose retailer economics; the API-key gate only controls mutations. Tenant isolation, authenticated reads, role-based authorization, rate/size limits, deployment observability and proper secret management are prerequisites for a public persistent product.

## Compatibility boundary
The original Iran MVP stays in src/pricing, src/data and src/dashboard/legacy.py. Its unversioned endpoints are retained for historical tests/integrations; /build-dataset requires a configured write key. New features must not import country-specific fields into the EUR domain.

The old margin fields mean cost markup. The new contribution-margin contract is deliberately versioned rather than silently changing historical data semantics. Existing CSVs are not automatically migrated because their currency, tax basis and economics are different.

Legacy CSV editing is historical single-user functionality, not the scalable persistence path. The default UI no longer exposes it. Legacy bootstrap never replaces existing raw inputs; new workspaces use SQLite transactions.

## Deliberate limits
One service process and a modest catalog are the current target. No scheduled server-side ingestion, production tenancy or automatic repricing. The demand lab (`domain/demand.py`) is a bounded, Numpy-based supervised benchmark exposed by `api/intelligence.py`, isolated from policy recommendations. Synthetic demo results are cached; uploaded histories are evaluated in memory under a two-slot concurrency bound. Changes to operational cost stress do not predict competitor reactions or demand. All pricing policies share the same minimum-margin guardrail.
