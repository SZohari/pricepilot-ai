"""Explainable policy baseline; no learned demand or profit-uplift claims."""
from decimal import Decimal, ROUND_CEILING, ROUND_HALF_UP
from statistics import median
from src.domain.models import Observation, Product, Quality, Recommendation, Scenario, Strategy, fee_on_net

D = Decimal
CENT = D("0.01")


def contribution_margin(price_gross: Decimal, product: Product, cost: Decimal) -> Decimal:
    """Contribution / net revenue, preserving the declared fee charging basis."""
    net_revenue = price_gross / (1 + product.vat_rate)
    return (net_revenue * (1 - fee_on_net(product.fee_rate, product.vat_rate, product.fee_basis)) - cost - product.variable_cost_net) / net_revenue


def price_for_margin(product: Product, cost: Decimal, margin: Decimal) -> Decimal:
    return ((cost + product.variable_cost_net) / (1 - fee_on_net(product.fee_rate, product.vat_rate, product.fee_basis) - margin)
            * (1 + product.vat_rate)).quantize(CENT, rounding=ROUND_CEILING)


def market_snapshot(observations: list[Observation], scenario: Scenario) -> tuple[list[Decimal], Quality]:
    """Latest known offer per seller; newer unavailability invalidates older stock."""
    future = [o for o in observations if o.observed_on > scenario.as_of]
    ordered = sorted((o for o in observations if o.observed_on <= scenario.as_of),
                     key=lambda o: o.observed_on)
    latest = {o.seller.casefold(): o for o in ordered}
    stale = unavailable = 0
    prices = []
    for observation in latest.values():
        if (scenario.as_of - observation.observed_on).days > scenario.max_age_days:
            stale += 1
        elif not observation.available:
            unavailable += 1
        else:
            prices.append(observation.price_gross + observation.shipping_gross)
    warnings = []
    if not prices:
        warnings.append("No fresh, available market offers; collect observations before pricing.")
    elif len(prices) < 3:
        warnings.append("Fewer than three independent sellers; review the market benchmark.")
    if prices and (max(prices) - min(prices)) / median(prices) > D("0.40"):
        warnings.append("Market spread exceeds 40%; check product variants and listing comparability.")
    if future:
        warnings.append("Future-dated observations were excluded.")
    return prices, Quality(
        total_observations=len(observations), usable_sellers=len(prices), stale=stale,
        future=len(future), unavailable=unavailable, superseded=len(ordered) - len(latest),
        status="blocked" if not prices else "limited" if len(prices) < 3 else "ready",
        warnings=warnings,
    )


def recommend(product: Product, observations: list[Observation], scenario: Scenario) -> Recommendation:
    relevant = [o for o in observations if o.product_id == product.product_id
                and (scenario.evidence_mode == "all" or o.data_origin == scenario.evidence_mode)]
    prices, quality = market_snapshot(relevant, scenario)
    strategy = scenario.strategy or product.strategy
    cost = product.replacement_cost_net * (1 + scenario.cost_change_pct / 100)
    floor = price_for_margin(product, cost, product.minimum_margin)
    current_margin = contribution_margin(product.current_price_gross, product, cost)
    common = dict(product_id=product.product_id, product_name=product.name,
                  as_of=scenario.as_of, selected_strategy=strategy,
                  current_price_gross=product.current_price_gross, floor_price_gross=floor,
                  replacement_cost_net=cost, current_margin=current_margin, quality=quality)
    if not prices:
        return Recommendation(**common, recommended_price_gross=None, market_median_gross=None,
                              expected_margin=None, strategy_prices={}, action="urgent_review",
                              risk_level="high", requires_review=True, reasons=quality.warnings)

    market_min, market_mid, market_max = min(prices), median(prices), max(prices)
    discount = D("0.05") if product.inventory > 80 else D("0.03") if product.inventory > 50 else D("0")
    if product.inventory > 0 and (product.sales_30d == 0 or product.sales_7d * 8 < product.sales_30d):
        discount += D("0.03")
    candidates = {
        Strategy.TRUST.value: market_min * D("0.98"),
        Strategy.BALANCED.value: market_mid * D("0.99"),
        Strategy.PROFIT.value: max(market_mid * D("1.05"), price_for_margin(product, cost, product.target_margin)),
        Strategy.PENETRATION.value: market_min * D("0.97"),
        Strategy.PREMIUM.value: min(market_mid * D("1.12"), market_max * D("1.05")),
        Strategy.CLEARANCE.value: market_min * D("0.96") * (1 - min(discount, D("0.10"))),
    }
    candidates = {key: max(value.quantize(CENT, rounding=ROUND_HALF_UP), floor)
                  for key, value in candidates.items()}
    proposed = candidates[strategy.value]
    movement = (proposed - product.current_price_gross) / product.current_price_gross
    expected = contribution_margin(proposed, product, cost)
    reasons = [
        f"{strategy.value.replace('_', ' ').title()} policy with {len(prices)} fresh seller offers.",
        f"Delivered market median: EUR {market_mid:.2f}; minimum gross price: EUR {floor:.2f}.",
    ]
    review = bool(quality.warnings)
    if floor > market_max:
        reasons.append("Margin floor exceeds the market maximum; review sourcing costs and positioning.")
        review = True
    if abs(movement) * 100 >= scenario.review_change_pct:
        reasons.append(f"Price movement of {movement:+.1%} exceeds the review threshold.")
        review = True
    if scenario.cost_change_pct:
        reasons.append(f"Replacement-cost scenario: {scenario.cost_change_pct:+}% (not a demand forecast).")
    if product.inventory == 0:
        reasons.append("No store inventory; confirm replenishment before accepting a price.")
        review = True
    reasons.extend(quality.warnings)
    if not review and abs(movement) < D("0.02") and product.current_price_gross >= floor:
        proposed = product.current_price_gross
        expected = current_margin
        action = "hold_price"
        reasons.append("Movement is below 2%; keep the current price.")
    else:
        action = "urgent_review" if review else "increase_price" if movement > 0 else "decrease_price"
    reasons.append(f"Expected contribution margin: {expected:.1%}; target: {product.target_margin:.1%}.")
    if expected < product.target_margin:
        reasons.append("Target margin is not achieved; the minimum margin remains protected.")
    return Recommendation(**common, recommended_price_gross=proposed, market_median_gross=market_mid,
                          expected_margin=expected, strategy_prices=candidates, action=action,
                          requires_review=review, risk_level="high" if review else "medium" if expected < product.target_margin else "low",
                          reasons=reasons)
