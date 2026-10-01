# Evaluation and AI development plan

## Implemented baseline
Run:

```bash
python -m scripts.evaluate --output evaluation.json
```

A generated reference report is committed as [evaluation-baseline.json](evaluation-baseline.json).

This evaluates all six deterministic policies under 0%, 10% and 30% replacement-cost stress on the frozen Germany demo. The reference date and policy version are recorded.

Metrics: evidence coverage, blocked products, required reviews, current/proposed floor violations, target contribution-margin attainment, mean modeled margin and absolute price movement. The proposed-floor violation count must be zero. Current-price breaches are a diagnostic baseline, not proof that recommendations improve business outcomes.

The default dataset intentionally contains stale observations, one-seller evidence, zero stock and a cost/market conflict. The report is deterministic and reproducible. It cannot establish actual sales volume, revenue, conversion or profit uplift.

## Data needed for real-market validation
Collect permissioned daily SKU observations: timestamped offers, actual price, availability, stockouts, sales units, promotions, returns and calendar effects. Preserve provenance and distinguish observation time from ingestion time.

The demand lab trains on a separate synthetic daily history and can evaluate uploaded single-product histories. Do not present its bundled synthetic results as real-world performance.

## Predictive evaluation
Implemented: ridge regression versus the prior seven-day mean and same-weekday-last-week unit-sales baselines, with chronological training/validation/calibration/test blocks, train-only scaling, stock-constrained target exclusion, MAE/RMSE/WAPE/bias and empirical interval coverage. Run `python -m scripts.evaluate_demand` for five fixed seeds under stable and demand-shock conditions. The report records exact predictions, hashes and versions. See [MODEL_CARD.md](MODEL_CARD.md).

Still needed: rolling real-data windows, SKU/store segments, richer availability/returns handling and prospective shadow evaluation. The current fixed test window is not evidence that performance persists across time or merchants.

Price elasticity is causal, not simply the coefficient of a price/sales correlation. Stockouts, promotion and selection effects need explicit treatment. Offline forecast accuracy alone does not justify autonomous pricing.

## Human/business evaluation
Measure time to review a product, recommendation acceptance, override reasons and explanation comprehension. A merchant pilot could measure realized contribution and sell-through using an agreed comparison design. No such study has been performed.

## Model integration seam
A future model may propose candidate prices and calibrated uncertainty through a policy adapter. The deterministic margin floor, quality gate, price-change review and human control remain independent. Version model, features, training window and evaluation evidence alongside every decision.

An LLM explanation layer is optional future work and must remain grounded in structured reasons; it should not invent market facts or replace the money calculation.
