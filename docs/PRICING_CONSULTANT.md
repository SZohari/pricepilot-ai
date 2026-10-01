# Pricing consultant — implemented behavior and boundaries

The `consultation-2` policy adds attributed customer-value knowledge, learning contracts and a conditional price–sales boundary. The featured walkthrough shows how the same financial inputs can support different actions after the owner's knowledge changes the comparability judgment. [Economic foundations and limits](ECONOMIC_FOUNDATIONS.md) explains the design interpretation of selected Austrian insights. Customer-value claims cannot bypass financial or freshness gates and do not create a calculated premium.

## The business task

Choose the next action for one repeatable offer, then check what happened. The primary flow accepts a physical product or a service with a defined unit of sale. Germany/EUR is the presentation context. A shop, studio and repair workshop illustrate different diagnoses; all three businesses and their numbers are fictional.

The advisor is a rule-based application service, not a conversational language model. The separate supervised demand benchmark remains available as a research tool. Neither branch claims that price causes a forecast change in sales.

## From facts to action

`domain/advisory.py` defines immutable contracts. `application/advisor.py` is the single authority for the primary consultation; the browser calls it for initial answers and interactive changes.

Inputs include the business concern, customer signal, comparability/positioning, total customer price including delivery, net per-sale cost including attributable labour, sales fees, VAT, chosen minimum contribution margin, dated baseline, available test capacity, trial duration and maximum acceptable volume loss. Free text is retained as context for human review; it is not interpreted as a causal model.

Priority order:

1. Stale costs, stale sales or an unconfirmed baseline require refreshed inputs.
2. Zero availability requires a capacity action; zero sales requires baseline collection. A loss-making offer must not be pushed through a discount.
3. A price below the chosen minimum margin requires cost/offer review or a bounded recovery trial.
4. A user-supplied candidate is evaluated explicitly. Full-capacity offers can use a +3% exploratory trial. Reported price objections plus a fresh comparable benchmark can justify trying a reduction, bounded at -5% and the margin floor.
5. Low visibility prompts acquisition work. Unknown cause prompts collection of enquiries and lost-sale reasons. An existing adequate margin is not automatically a reason to increase price.

The ±10% maximum trial change, +3% capacity trial, 14-day competitor freshness, 30-day cost freshness, 45-day baseline recency, two-seller check and 40% spread exclusion are transparent MVP policies. They are not empirical optimum estimates. The customer signal and independent-seller identity are owner assertions and need verification in a pilot.

## What the sales threshold means

For gross price P, VAT v, fee fraction f and net variable cost C:

```text
unit contribution = P / (1 + v) * (1 - f) - C
minimum price = ceil_to_cent(C * (1 + v) / (1 - f - minimum_margin))
baseline units over trial = baseline_units / baseline_days * trial_days
contribution threshold = ceil(baseline units over trial * current_unit_contribution / trial_unit_contribution)
volume threshold = ceil(baseline units over trial * (1 - maximum_volume_loss))
required sales = max(contribution threshold, volume threshold)
```

Negative baseline contribution has a zero lower bound on its contribution threshold; a positive proposed contribution and the volume guardrail are still required. Trials below the minimum margin, outside the movement policy or requiring more units than available are not offered as executable tests.

**This is a break-even requirement, not a prediction.** It does not estimate price elasticity, a probability of success, customer retention, net business profit or lifetime value. Contribution excludes fixed overhead. A service's attributable labour must be included in per-sale cost.

## Plans and evidence

`api/advisor.py` exposes consultations, examples, plans, start records, outcomes and non-price action notes. A plan contains an immutable input/report snapshot and fingerprint. The server recomputes advice before saving; catalog-linked plans also recheck product version and observation IDs inside the SQLite write transaction. Request IDs make exact save retries idempotent. Status transitions reject duplicate or conflicting writes.

Plans move from `planned` to `active` to `completed`; a non-price action can move directly from planned to completed with an owner note. Recording a start requires an actual date after the baseline and the exact planned price. It never publishes a price to a shop. Outcome entry records actual per-sale cost, fees, VAT, units, availability, price stability and other changes. Comparison is per day; the baseline contribution uses consultation costs, not historical accounting profit. Short trials are incomplete; reported stockouts, different prices or confounders produce an inconclusive review. Passing both guardrails is a promising observation, never causal proof.

The demo-result endpoint invokes the same evaluator on clearly fictional outcomes. It makes no database transition. It is unavailable for merchant-origin cases.

## Competitors

Dated manual comparables require an HTTPS source and the owner's explicit confirmation of the same unit/scope, variant/condition and total customer charges. They are labelled owner-entered. Future, stale, unavailable and unconfirmed comparables are excluded. A differentiated service is not automatically benchmarked against a different service's price.

Local merchant product consultations can configure a source with an exact valid GTIN and explicit delivery assumptions. Configuration creates a linked merchant catalog entry if needed. Source URLs belong to that browser session. Collection uses the existing SSRF-resistant, robots-aware, bounded JSON-LD collector and reports each result through SSE. Cache keys include the entire source configuration so one session's source ID cannot alias another URL or SKU. New live observations are used when the merchant consultation refreshes. Demo evidence cannot enter a merchant consultation.

The public demo denies arbitrary URL configuration; its owner can preconfigure source files. No supported retailer is bundled. On 2026-09-27, the [Decathlon Forerunner 165 Music listing](https://www.decathlon.de/p/forerunner-165-music-schwarz-dunkelgrau/358996/m8916531) returned HTTP 403 to the collector after robots allowed the path. No price was imported and no access-control workaround was attempted. This is a coverage limitation, not live-data validation.

## Scope still requiring a pilot

- The broad abstraction is per-unit goods and services, not every business model. Mixed-VAT baskets, subscription churn, tiered contracts, cross-product substitution and multi-resource scheduling need separate contracts/models.
- Inflation and FX enter through verified costs or recorded context; ageing, campaigns and seasonality can invalidate the comparison. They are not silently assigned made-up coefficients.
- All owner evidence remains self-reported. The MVP lacks authenticated merchant identities, POS integration, transaction-level outcome reconciliation and an experiment/randomization engine.
- Default browser workspaces are temporary and isolated. Plans and datasets can be exported separately. Persistent local storage is available to authenticated API clients; the persistent browser UI is read-only. Do not treat the public demo as a place for confidential business records.
- Legacy retail tables, the sensitivity sandbox and the ML evaluation are secondary tools. Their outputs are not mixed into the consultation plan.

## Validation for this change

Automated coverage includes business diagnoses, contribution versus volume tradeoffs, capacity infeasibility, stale/unavailable/mismatched evidence, synthetic-data separation, Decimal margin floors, idempotent and stale-snapshot writes, session isolation, schema migration/reopening, actual-cost outcome evaluation, confounded/incomplete results, non-price follow-up, live collection integration with controlled fixtures and public URL-configuration denial. Browser visual QA remains unverified because the saved local-browser access preference blocks it.
