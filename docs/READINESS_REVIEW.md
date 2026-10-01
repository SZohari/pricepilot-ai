# PricePilot: business logic and MVP readiness review

Reviewed on **2026-10-01**, against the deployed v1.7.0 implementation. Scope: the guided consultation, accounting boundary, local-knowledge treatment, outcome review, demand evaluation and their public presentation. This is a focused product/code review, not a security certification or merchant validation.

## Assessment

PricePilot is a defensible portfolio MVP for work that connects data engineering, machine learning and business decisions. Its strongest contribution is the complete decision routine: explicit inputs, a conditional recommendation, financial and sales constraints, an evidence snapshot and a follow-up that can reject the initial idea.

Its current commercial proposition is a **scoped decision-support pilot**. Merchant value, acquisition demand and willingness to pay have not been established. A generally reliable autonomous pricing product would require substantially more evidence and operational work.

## Where the business complexity is implemented

| Dimension | Implemented behaviour | Remaining boundary |
| --- | --- | --- |
| Sales versus contribution | Required sales satisfy both contribution preservation and the owner's volume-loss limit | Unit counts do not measure customer retention; fixed overhead is excluded |
| Discount versus capacity | A candidate is blocked when the required sales exceed available units/slots | No replenishment scheduling or allocation across products |
| Changing costs | Replacement cost, variable order costs, VAT and fee basis affect the price floor | Historical purchase cost is retained separately; this is not a full accounting-profit model |
| Market evidence | Delivered prices, dated evidence, availability and comparability affect the advice | Listings are asking prices; variant matching and source coverage still need merchant validation |
| Local knowledge | An attributed observation can change the diagnosis; an unresolved prerequisite can pause a trial | A customer's willingness to pay cannot be inferred from the owner's story |
| Feedback | Actual sales/costs, period length and reported confounders affect the follow-up verdict | Before/after comparisons do not identify a causal price effect |
| Model failure | Chronological holdouts, two baselines and an explicit demand-shock example | Synthetic performance is not evidence of real demand accuracy |

Evidence: [consultation](../src/application/advisor.py), [learning contract and boundary](../src/application/discovery.py), [validated inputs](../src/domain/advisory.py), [demand model](../src/domain/demand.py).

## What “nonlinear” means here

Per-sale contribution is affine in price when VAT, fees and per-unit costs are fixed. The **required sales boundary** is nonlinear because it divides the contribution to preserve by the contribution available at the candidate price. Integer rounding, a sales-volume floor and capacity introduce additional thresholds.

For a simplified illustrative offer with zero VAT/fees, price €100, variable cost €80 and 100 baseline sales over 30 days:

| Candidate | Contribution per sale | Sales required in 30 days | Capacity: 150 |
| --- | ---: | ---: | --- |
| €100 · current | €20 | 100 | Reference |
| €95 · 5% reduction | €15 | 134 | Permitted accounting boundary |
| €90 · 10% reduction | €10 | 200 | Trial blocked |

These results were reproduced by calling the actual consultation service with a 10% minimum contribution margin and a 5% maximum volume loss. Doubling the discount from 5% to 10% more than doubles the additional sales required. Neither calculation predicts that the additional customers will arrive.

The learned model uses logarithmic features/target and nonlinear retransformation, but remains ridge regression in its transformed feature space. It is not a learned model of the whole business. Cross-product substitution, customer segments and retention, strategic competitor feedback, step costs and multi-period inventory/cash constraints are absent. Inflation or currency changes can be reflected in confirmed replacement costs or scenarios; they are not macroeconomic forecasts.

## What should improve next

1. **Obtain one usable merchant history and an agreed decision.** Define the SKU, sales/availability records, cost scope, comparable offers and review objective. Measure review time and decision usefulness before claiming financial uplift. This is the largest missing source of credibility.
2. **Validate policy choices.** The automatic 3% increase, bounded reduction, ±10% trial limit, evidence ages and comparability thresholds are explicit heuristics. They need sensitivity checks and merchant feedback; they are not estimated optimal settings. [Policy implementation](../src/application/advisor.py)
3. **Make the two working modes visually consistent.** The guided shop has a coherent five-step experience, while secondary tools expose the older, denser workspace. Narrow the default tool menu and keep advanced research/policy pages visibly secondary. The captured [decision](screenshots/pricing-decision.jpg) and [model lab](screenshots/demand-evaluation.jpg) show the transition.
4. **Clarify learning horizons.** Low-visibility advice asks for seven days of enquiries, while the selectable review period defaults to fourteen days. These can be separate checkpoints, but that distinction should be explicit in the plan. [Advice text](../src/application/advisor.py)
5. **Add interactions when evidence justifies them.** Start with an observed promotion/availability interaction or a specific replenishment constraint. Evaluate whether it improves the decision over the current simpler method before adding a larger model.
6. **Prepare the operational pilot.** Authenticate merchant workspaces, persist and back up records, configure supported collection sources and own the refresh/review process. The current free public demo deliberately uses temporary sessions and does not publish store prices.

## Verification for this review

- **40 passing tests** across consultation and discovery: financial/volume constraints, capacity, evidence eligibility, local knowledge, stale snapshots and observed outcomes. A local pytest-cache permission warning did not affect execution.
- **24 passing intelligence tests** covering the evaluation and decision-workbench contracts.
- Public browser walkthrough of cost confirmation, market review, recommendation and a newly executed demand benchmark. Screenshots are actual UI captures, with simulated-data labels retained.
- Default watch case verified on screen: €449.00 → €426.55, contribution €125.26 → €106.78, at least 10 sales over fourteen days.
- Saved five-seed evaluation inspected: ridge beats both baselines in all five stable synthetic cases and loses to the best baseline in all five shock cases. See the [reproducible report](demand-evaluation.json).
- Earlier deployment checks, including isolated visitor edits, navigation, saved plans and CSV export, are recorded in [online demo verification](ONLINE_DEMO.md).

The present evidence supports a claim of thoughtful, tested decision-support engineering. Claims of optimal pricing, causal elasticity, retention protection or merchant profit improvement remain unestablished.
