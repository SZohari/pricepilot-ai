# PricePilot: pricing as disciplined discovery

## The product thesis

A useful pricing tool helps a business discover which exchange can work under incomplete knowledge. It makes financial conditions explicit, lets the owner contribute local knowledge, separates claims from observations, and records what could overturn a decision.

The primary demonstration now follows one online watch shop from product intake to a recorded decision; see [Retail decision system](RETAIL_DECISION_SYSTEM.md). A separate methodological example holds prices, costs, baseline sales and capacity constant. An apparent competitor match initially supports a bounded reduction. The owner then reveals a difference in delivery timing. The system changes the next action to testing whether that difference matters to the stated customer group. It does not assign a premium to the story. A third step evaluates an explicitly proposed price as a hypothesis.

This is an implemented design argument, not a declaration that one school of economics has been proved correct. The underlying ideas are not all exclusive to Austrian economics or novel in pricing research. The project contribution is their explicit translation into contracts, decision behavior, a falsifiable business plan and a usable demonstration.

## Intellectual sources and the design interpretation

**Dispersed knowledge.** Hayek distinguishes knowledge of particular circumstances from information available to a central decision maker. PricePilot therefore accepts dated owner observations alongside market listings, without assuming that either is complete. Adding local knowledge can change the comparability judgment. This is an analogy for a decision-support tool, not a literal implementation of Hayek's account of an entire economy. Primary source: F. A. Hayek, [The Use of Knowledge in Society (1945)](https://www.econlib.org/library/Essays/hykKnw.html).

**Subjective value.** Menger locates value in the significance people attach to goods for satisfying needs. The design implication is modest: a business's cost or claimed advantage cannot establish what a particular customer will pay. The tool computes contribution constraints and records a customer-value hypothesis. It neither assigns numerical utility nor derives a demand curve from that hypothesis. Primary source: Carl Menger, [Principles of Economics, chapter III (1871)](https://mises.de/en/werke/menger-grundsaetze-der-volkswirthschaftslehre-en/lesen/iii-the-theory-of-value).

**Discovery through competition.** Hayek treats competition as a process that can reveal previously unknown facts. The product interpretation is a sequence of inspectable decisions and observations, with an explicit reason to revise a belief. A bounded merchant trial is our implementation choice; it is not a test of that economy-wide thesis. Primary source: F. A. Hayek, [Competition as a Discovery Procedure (1968; English translation 2002)](https://cdn.mises.org/qjae5_3_3.pdf).

**Limits of knowledge.** Hayek warns against treating partial quantitative knowledge as complete mastery of complex phenomena. In PricePilot, precise accounting is kept distinct from uncertain customer response. Empirical modelling remains useful: the supervised demand lab must beat baselines on a time-separated holdout, and its shock failure is shown. Primary source: F. A. Hayek, [The Pretence of Knowledge (1974)](https://www.nobelprize.org/prizes/economic-sciences/1974/hayek/lecture/).

These selected insights are combined with contemporary statistical evaluation and observational business monitoring. PricePilot does not adopt every methodological or political position associated with the Austrian school. It does not equate empirical uncertainty with an inability to learn from data.

## Four categories that must not be conflated

| Category | Example | Treatment |
|---|---|---|
| Reported or collected inputs | Costs, dated listings, past units | Retain source, date and known limitations; owner input is not independently verified |
| Conditional calculation | Required sales to preserve contribution | Decimal arithmetic under explicit assumptions, with integer and capacity constraints |
| Chosen objective or policy | Minimum margin, acceptable volume loss, trial bound | Label as the owner's choices or MVP policy, not facts learned from data |
| Uncertain proposition | Customers will pay for same-day delivery | Record the claim, its basis and what would change the decision; infer no premium |

The interface exposes these distinctions through “What would change this advice?”, the dated local-knowledge form and the conditional price–sales boundary. They are also exported in a saved plan's fingerprinted report.

## The boundary is not a demand curve

Let `u(p)` be per-sale contribution at gross customer price `p`, `b` the baseline unit count normalized to the trial length, `l` the chosen maximum volume-loss fraction, and `K` capacity:

```text
effective_net_fee = fee_rate * (1 + VAT) [gross basis], otherwise fee_rate
u(p) = p / (1 + VAT) * (1 - effective_net_fee) - variable_cost
n_contribution(p) = max(0, ceil(b * u(current_price) / u(p)))  [only if u(p) > 0]
n_volume = ceil(b * (1 - l))
n_required(p) = max(n_contribution(p), n_volume)
```

A point clears the accounting checks only if contribution is positive, price clears the margin floor and movement policy, and `n_required(p) <= K`. This describes an outcome the trial would need to achieve. It gives no probability of achieving that outcome. Below-floor and capacity-infeasible points remain visible. Rounded candidate prices are checked again against the actual movement bound. The automatically proposed price is included explicitly in the curve's points.

This boundary is exact only conditional on the inputs, stable per-unit fees/costs, a homogeneous unit and the chosen baseline. It does not account for cross-product substitution, customer churn, differentiated resource requirements, opportunity cost across offers, step costs or strategic competitor responses. A cost floor is an accounting constraint, not a welfare calculation or proof that the offer should exist.

## The learning contract

Every consultation now returns:

- A hypothesis attached to the specific offer and proposed action.
- The next observation that would help decide.
- Conditions that would lead the owner to revise or reject the action.
- A distinction between owner-reported evidence and untested belief.
- No fabricated confidence score, inferred willingness-to-pay figure or causal label.

For a price test, the report's contribution, unit-margin and volume checks are agreed before outcome entry. Matching them is a business observation, not a statistically identified treatment effect. An unchanged price, stable availability and no known campaign do not eliminate all confounding. They only rule out some obvious invalid comparisons. A different customer segment needs a corresponding baseline; entering a segment name does not filter the sales data automatically.

The owner can be wrong. A claim that customers value speed must be allowed to fail. The system must not rescue it by asserting that every rejecting customer misunderstood the value proposition. A cheaper listing can also be an imperfect signal of actual transactions. Both objections are kept visible.

## What the portfolio demonstrates

The intended impression is an ability to turn an economic question into explicit software behavior: define the decision, separate facts from choices and assumptions, implement constraints, preserve provenance, expose uncertainty, test failure cases, and make the result understandable. This is a more concrete claim than “AI finds the optimal price.”

Current executable evidence lives in `tests/v1/test_discovery.py` and `tests/web/discovery.test.mjs`: identical financial facts with changed local context, no premium invented from a claim, no override of cost/capacity gates, minimal integer sales thresholds, dated evidence, stale-plan rejection and clear chart semantics.

Success in a merchant pilot, a hiring decision or an admission process is not established by these tests. Those require real users and external evaluation.

## Questions to be ready to answer

**Why not just match the cheapest listing?** Its scope and customer job may differ; it may not represent a completed sale. Comparable prices are evidence, not a complete valuation model.

**Why not let the owner's story set a higher price?** A story supplies a hypothesis. It does not identify willingness to pay. The tool asks for evidence that could support or contradict it.

**Is this AI?** The consultation is explicit rules and accounting; the demand lab fits a supervised model. The distinction is deliberate. Neither a language model nor a fitted coefficient is passed off as a causal price optimizer.

**What would be needed for causal pricing claims?** An appropriate experiment or defensible identification design, consistent treatment and comparison groups, adequate data and a treatment of interference and changing market conditions. None is supplied by the current before/after review.

**What would make the project commercially credible?** A scoped merchant pilot showing better decisions or saved work on real inputs, independent of the synthetic demonstration. Retention, realized profit and operational integration still need evidence.
