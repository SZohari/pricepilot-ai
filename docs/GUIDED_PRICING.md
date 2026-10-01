# Historical prototype

This document describes the superseded guided comparison prototype. It is no longer the homepage. The current primary flow is documented in [PRICING_CONSULTANT.md](PRICING_CONSULTANT.md); it uses server-side consultation rules and recorded outcomes, without assumed elasticity ranges.

# Guided pricing flow — 2026-09-27

The default screen now answers one commercial question: **which price should I review, given the trade-off I am prepared to consider?**

1. Pick a product and a priority: balance, contribution protection, or more units.
2. Set the maximum downside to consider (sales loss, or contribution loss for the volume priority).
3. Read a suggested next step and a short comparison against the current price.
4. Export the comparison as a review plan. No approval or shop-price publication occurs.

Navigation has three primary destinations. Model evaluation, the free-form sandbox, cost scenarios, data tools and the store story remain available under an expandable section. This keeps the portfolio's engineering evidence available without presenting every technical tool as an equally important starting point.

## Decision logic and limits
The guided comparison is an assumption-based sensitivity analysis, separate from both the learned demand benchmark and the deterministic market-policy recommendation. It uses the cockpit's same VAT/cost/fee arithmetic and stock cap.

Candidate prices range from −10% to +10% around the current price at half-percentage-point increments, rounded to cents. Prices below the minimum-margin floor are excluded. The upper bound is also constrained to the larger of the current price and 105% of the competitor median; this is an explicit MVP heuristic, not a learned optimum. The UI shows at most three distinct price options, always including the current price and the selected option.

For balance and contribution protection, rank candidates by their lowest contribution across the assumed sensitivity responses, subject to the user's maximum unit-sales loss. Their default limits are 5% and 10%, and can be changed. For volume, maximize the lowest unit-sales outcome while preserving at least the selected proportion of baseline contribution (default: permit at most 20% contribution loss), with no unit-sales reduction. These are review preferences, not guaranteed business outcomes.

Sensitivity intervals are low 0.5–1.5, medium 0.8–2.5 and high 2–4. Endpoints and the midpoint are evaluated. Neither these assumed intervals nor the candidate grid establish a causal response or a globally optimal price. The same cost scenario, unchanged market demand, 30-day horizon and no-replenishment assumption apply to both the reference and alternatives. Zero inventory, zero sales history or unavailable competitor evidence prevents a numerical suggestion. A floor outside the acceptable test range prompts a cost review instead of endorsing the current price.

The output distinguishes total contribution from net profit and shows uncertainty as ranges next to the action. If keeping the price is the best eligible option, it says so. No promise of simultaneously increasing sales and earnings is made.

## Verification
29 JavaScript model/presentation tests passed, including 12 new tests for goal trade-offs, adjustable downside limits, blocked states, cost consistency, price floors and movement bounds across the demo catalog, stock caps, sensitivity effects, distinct comparisons, empty catalogs and escaping. Existing web integration tests verify serving and security. Visual interaction QA is still unverified because browser access to localhost remains blocked by the saved permission setting; no alternate browser route was used.
# Historical prototype

This document describes the superseded guided comparison prototype. It is no longer the homepage. The current primary flow is documented in [PRICING_CONSULTANT.md](PRICING_CONSULTANT.md); it uses server-side consultation rules and recorded outcomes, without assumed elasticity ranges.
