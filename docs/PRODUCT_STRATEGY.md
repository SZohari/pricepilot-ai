# PricePilot: commercial case and pilot boundaries

## A concrete customer and job
Initial customer hypothesis: an independent German electronics/wearables retailer with a modest catalog and a person manually checking competitor prices. The buyer is the owner or pricing/category manager. Validate this in interviews; no customer demand or willingness to pay has been established.

The job: **turn comparable market evidence and store economics into a short, reviewable pricing queue, with a record of why the operator accepted or rejected each suggestion.** Daily demand-model evaluation is an additional analytical capability, not a prerequisite for useful margin and evidence checks.

## What can be demonstrated now
1. Collect configured exact-variant offers or replay clearly labeled demo events.
2. Reject stale, unavailable and uncomparable evidence instead of inventing a benchmark.
3. Prioritize negative contribution, missing evidence and manual reviews; expose stock cover and inventory at cost.
4. Compare unit contribution at current and proposed prices, with independent minimum-margin rules.
5. Explore pricing/cost/demand assumptions without modifying store inputs.
6. Record accept/reject/defer, a commercial reason, the full input snapshot and policy version. Reject stale reviews and preserve journal history.
7. Evaluate learned demand prediction against naive and seasonal baselines, including an explicit failure case, with reproducible reports.

Potential differentiation is the combined decision workflow and evidence transparency. This is a **hypothesis**, not a claim that competitors lack these capabilities. Scraping alone and an attractive dashboard are not durable advantages. Better SKU matching, merchant integrations, permissioned longitudinal data and outcome-linked evaluation could become stronger assets if developed with real users.

## Offer to validate, not an invented SaaS business
The nearest honest offer is an assisted, fixed-scope shadow pilot. Agree the SKUs, rival pages, source permissions, refresh interval and review owner. Start with manual exports and a few verifiable sources. Deliver an evidence-health report, a ranked queue and a weekly review of decisions. Quote setup/integration effort separately from ongoing monitoring; test willingness to pay before choosing subscription tiers. Do not promise comprehensive competitor coverage or a percentage revenue increase.

Candidate future pricing dimensions are supported SKUs, verified source coverage and collection frequency. Choose after measuring maintenance cost, not token count or an AI label. A retailer should pay for less manual work and better-supported decisions; the estimator is one component.

## Proposed pilot scorecard
| Question | Measurement | Important qualification |
|---|---|---|
| Does it save time? | Median active review minutes per SKU before/after, using the same task definition | UI click count is not time saved; record a real baseline |
| Can the evidence be trusted? | Manually verified SKU matches, source success rate, fresh/comparable offer coverage | A successful HTTP response is not a valid offer |
| Do operators use the output? | Acceptance/defer/reject share plus coded reasons and follow-up | Acceptance does not prove a financially good decision |
| Is prediction useful? | MAE, WAPE where defined, bias and band coverage by SKU/window against simple baselines | Synthetic improvement is not real-data validation |
| Does business performance improve? | Net unit contribution, total contribution, units, stock availability and returns | Account for promotions, costs and seasonality; before/after correlation is not causal ROI |
| Are customers harmed? | Complaints, repeat purchase and conversion if lawfully available at aggregate level | Fewer units do not identify churn; no current retention prediction |

Start in shadow mode, then consider a merchant-approved controlled experiment. Pre-agree safety bounds and stop conditions, including invalid SKU matches, margin breaches, excessive prediction bias or poor source availability. No automatic price publishing is implemented.

## Where the MVP stops
- No configured real retailer sources yet; generic JSON-LD collection has restricted coverage and needs verified URLs/GTINs. It does not bypass anti-bot controls.
- No real daily sales data or measured customer/business results. The synthetic model is a demonstration of training/evaluation discipline.
- No enterprise identity, authenticated merchant read access, tenant administration, scheduled server-side jobs, alerting SLA or invoicing.
- SQLite schema v2 adds journal storage; a production migration and backup/restore program is still needed.
- The review journal is append-only through application routes, not tamper-proof and not a verified user-signature system.
- Public hosting remains a demo; persistent retailer deployment needs authenticated reads/writes, tenant isolation, monitoring, backup tests and scoped source access.

## Germany-specific product requirements
VAT/net-versus-gross conventions and comparable delivered prices are explicit inputs, not tax advice. Promotional claims require the retailer's own price history; competitor prices cannot supply it. The current workbench labels this evidence missing and never publishes a promotional percentage. The European Commission's guidance on price-reduction announcements discusses the prior-price rule and exceptions: [official Article 6a guidance](https://eur-lex.europa.eu/legal-content/EN/ALL/?uri=CELEX%3A52021XC1229%2806%29). Production behavior needs German-specific review and a proper price-history contract.

Prefer SKU/day aggregates over customer profiles. Source terms, permitted collection, GDPR roles/retention and merchant authorization require review for an actual deployment. These are concrete pilot dependencies, not a claim that this MVP is legally certified.
