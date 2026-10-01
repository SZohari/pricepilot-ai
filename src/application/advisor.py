"""A single, inspectable pricing consultation, followed by an observational review.

No demand curve is invented. Price tests are bounded hypotheses and the only sales
numbers calculated here are break-even requirements, never predicted outcomes.
"""
from datetime import date, timedelta
from decimal import Decimal, ROUND_CEILING, ROUND_HALF_UP
from hashlib import sha256
import json
from statistics import median
from src.domain.advisory import Consultation, OutcomeRecord
from src.domain.models import Scenario, fee_on_net
from src.domain.pricing import market_snapshot
from src.application.discovery import learning_contract, viability_boundary

D = Decimal
CENT = D(".01")
VERSION = "consultation-4"


def cash(value):
    return str(value.quantize(CENT, rounding=ROUND_HALF_UP))


def per_unit(price, c):
    return price / (1 + c.vat_rate) * (1 - fee_on_net(c.fee_rate, c.vat_rate, c.fee_basis)) - c.unit_cost_net


def consult(c: Consultation, repository, today=None):
    today = today or c.demo_as_of or date.today()
    entries, observations = repository.snapshot()
    linked = next((e for e in entries if e.product.product_id == c.linked_product_id), None)
    if c.linked_product_id and not linked:
        raise ValueError("Linked catalog product no longer exists")
    if linked and c.origin == "merchant" and linked.product.data_origin != "merchant":
        raise ValueError("A merchant consultation cannot use a simulated catalog product")
    linked_obs = [o for o in observations if o.product_id == c.linked_product_id]
    origin = "demo" if c.origin == "demo" else "live"
    selected = [o for o in linked_obs if o.data_origin == origin]
    prices, quality = market_snapshot(selected, Scenario(as_of=today, max_age_days=14))
    # Pick the newest seller record first, including unavailable observations.
    latest = {o.seller.casefold(): o for o in sorted(selected, key=lambda o: o.observed_on) if o.observed_on <= today}
    evidence = [dict(seller=o.seller, price=cash(o.price_gross + o.shipping_gross),
                     observed_on=str(o.observed_on), url=str(o.source_url) if o.source_url else None,
                     origin=origin) for o in latest.values()
                if o.available and (today - o.observed_on).days <= 14]
    excluded = quality.stale + quality.future + quality.unavailable
    for item in c.comparables:
        if not item.same_offer or not item.available or not 0 <= (today - item.observed_on).days <= 14:
            excluded += 1
            continue
        # A manual record cannot override a collected seller observation.
        if item.seller.casefold() in latest:
            continue
        evidence.append(dict(seller=item.seller, price=cash(item.total_price_gross),
                             observed_on=str(item.observed_on), url=str(item.url), origin="demo" if c.origin == "demo" else "owner_entered"))
    market = median([D(e["price"]) for e in evidence]) if evidence else None
    market_usable = len(evidence) >= 2 and c.positioning == "comparable"
    if market and (max(D(e["price"]) for e in evidence) - min(D(e["price"]) for e in evidence)) / market > D(".4"):
        market_usable = False
    current = c.current_price_gross
    unit = per_unit(current, c)
    floor = (c.unit_cost_net * (1 + c.vat_rate) / (1 - fee_on_net(c.fee_rate, c.vat_rate, c.fee_basis) - c.minimum_margin)).quantize(CENT, rounding=ROUND_CEILING)
    floor = max(CENT, floor)
    daily = D(c.baseline_units) / c.baseline_days
    expected_baseline = daily * c.test_days
    blockers = []
    if not c.cost_scope_confirmed:
        blockers.append("Confirm all per-order costs, including delivery, returns losses and fixed transaction fees.")
    if (today - c.costs_checked_on).days > 30:
        blockers.append("Refresh your per-sale cost: it was checked more than 30 days ago.")
    if (today - c.baseline_end).days > 45:
        blockers.append("Bring a recent sales period; this baseline ended more than 45 days ago.")
    if not c.baseline_representative and c.baseline_units > 0:
        blockers.append("Confirm a baseline at this price, without stockouts or an unusual campaign.")
    action, title, why, step = "investigate", "Keep the price while you find the cause", "Sales alone do not tell us whether the price is the problem.", "Record visits or enquiries and reasons for five lost sales before changing price."
    target = current
    if blockers:
        action, title, why, step = "refresh_inputs", "Update the inputs before choosing a price", blockers[0], "Correct the dated inputs below, then ask for a new consultation."
    elif c.test_capacity == 0:
        action, title, why, step = "capacity", "Make the offer available first", "There are no units or service slots available for a price test.", "Confirm replenishment or bookable capacity, then revisit the price."
    elif c.baseline_units == 0:
        action, title, why, step = "learn", "Get a first sales baseline", "With no sales, there is no reliable run rate to protect.", "Keep a cost-covering price and record enquiries, purchases and availability for at least seven days."
        if unit <= 0:
            title, why, step = "Fix the loss before seeking more sales", "Each sale currently loses contribution, even before fixed overhead.", "Review unit costs or the offer scope; do not launch a discount."
    elif current < floor and c.proposed_price_gross is None:
        target = floor
        action, title, why, step = "price_test", "Recover the margin with a controlled price test", "Your current price does not cover the minimum contribution margin you set.", "Apply the test price yourself to a defined offer; track daily units and contribution."
        if floor > current * D("1.10") or (market_usable and floor > market * D("1.05")):
            action, title, why, step = "rework_offer", "Fix the cost or the offer before chasing volume", "Recovering your minimum margin would require a large price jump or exceed the comparable market.", "Request a supplier quote or reduce the per-sale cost/scope. Recheck this case with the confirmed cost."
            target = current
    elif c.proposed_price_gross is not None:
        action, target = "price_test", c.proposed_price_gross
        title, why, step = "Test your price with a clear stopping rule", "This is your candidate price. The sales threshold below is what it must achieve to protect contribution.", "Change only the price for the test period and record the result, including anything else that changed."
    elif c.concern == "capacity" and c.signal == "at_capacity":
        action, target = "price_test", (current * D("1.03")).quantize(CENT)
        title, why, step = "Test a small increase on new bookings", "You report full capacity. A 3% trial is a cautious policy choice, not an estimated optimum.", "Use the new price for new bookings only. Track declined quotes as well as completed sales."
        if c.kind == "goods":
            title, step = "Try a small increase on new orders", "Use the new price for new orders only. Track price objections as well as completed sales."
    elif c.concern == "slow_sales" and c.signal == "low_visibility":
        title, why, step = "Work on visibility before discounting", "You report too few visits or enquiries. A lower price may reduce your margin without bringing more people.", "Improve one acquisition channel and track enquiries for seven days at the current price."
    elif c.positioning == "differentiated" and c.customer_value is not None:
        action, title = "validate_value", "Find out whether customers value the difference"
        why = "You report a different scope or benefit. A cheaper listing alone cannot tell us whether your offer is overpriced."
        step = "Show the full offer and its price to the customer group you described. Record what people choose and why before matching a different offer's price."
        if (today - c.customer_value.checked_on).days > 30:
            step = "Refresh the customer observation first; it is more than 30 days old. Then compare choices between clearly described alternatives."
    elif c.concern == "slow_sales" and market_usable and c.signal == "price_objections" and current > market * D("1.03"):
        action, target = "price_test", max(floor, current * D(".95"), market).quantize(CENT, rounding=ROUND_CEILING)
        title, why, step = "Try a small, measured reduction", "Customers report price objections and comparable offers are cheaper. A reduction is worth testing, not assuming.", "Keep availability and promotion stable. Stop if the required extra sales do not arrive."
    elif c.concern == "margin" and unit > 0:
        title, why, step = "Protect the margin you already have", "Your current price clears your minimum contribution margin. There is no evidence yet that an increase would improve total contribution.", "Review supplier, payment and delivery costs first, or enter a candidate price to evaluate a controlled test."

    new_unit = per_unit(target, c)
    required = None
    contribution_required = None
    volume_required = (expected_baseline * (1 - c.max_volume_loss_pct / 100)).to_integral_value(rounding=ROUND_CEILING)
    if new_unit > 0:
        contribution_required = max(D(0), (expected_baseline * unit / new_unit).to_integral_value(rounding=ROUND_CEILING))
        required = max(contribution_required, volume_required)
    if action == "price_test":
        if target <= c.customer_shipping_gross:
            action, title, why, step = "unsafe_price", "Keep a positive item price", "The customer total does not exceed the delivery charge.", "Review the item price and delivery charge separately."
        elif target < floor or new_unit <= 0:
            action, title, why, step = "unsafe_price", "Do not use this price", "The candidate is below your chosen margin floor.", "Increase the candidate or reduce the confirmed per-sale cost."
        elif abs(target / current - 1) > D(".10"):
            action, title, why, step = "rework_offer", "This change needs a separate offer review", "A change above 10% is outside this MVP's small-test policy.", "Validate the offer and customer response before making a large price change."
        elif target == current:
            action, title, why, step = "hold", "Keep this price for now", "The candidate equals your current price.", "Track sales and lost-sale reasons before starting a price experiment."
        elif required is not None and required > c.test_capacity:
            action, title, why, step = "capacity", "This price cannot meet your guardrails with current capacity", "The sales needed to preserve contribution or your volume limit exceed the units or slots available.", "Keep the current price; revisit the trial after increasing capacity or changing its terms."
    unresolved = [n for n in c.knowledge_notes if n.resolve_first]
    if action == 'price_test' and unresolved:
        action, title = 'learn', 'Resolve the open question before a price test'
        why = 'You marked this question as a prerequisite: ' + unresolved[0].statement
        step = 'Use the observation plan below. Update the finding and clear its prerequisite only after reviewing what you learned.'
        if current < floor:
            why += ' Your current price also misses the margin floor; address the cost or offer while investigating.'
    economics = dict(current_unit_contribution=cash(unit), proposed_unit_contribution=cash(new_unit),
                     minimum_price_gross=cash(floor), baseline_units_over_test=str(expected_baseline.quantize(D(".1"))),
                     units_needed_for_contribution=int(contribution_required) if contribution_required is not None else None,
                     minimum_units_with_volume_guardrail=int(required) if required is not None else None,
                     volume_floor_units=int(volume_required), capacity=c.test_capacity,
                     contribution_is_not_profit=True)
    report = dict(method_version=VERSION, as_of=str(today), input=c.model_dump(mode="json"),
                  action=action, title=title, why=why, next_step=step,
                  considered_price_gross=cash(target),
                  test_price_gross=cash(target) if action == "price_test" else None,
                  can_start_test=action == "price_test", economics=economics, evidence=evidence,
                  excluded_evidence=excluded, market_usable=market_usable,
                  market_median_gross=cash(market) if market else None,
                  blockers=blockers, forecast=False,
                  monitoring=["Record units sold, net per-sale costs and available stock or slots each day.",
                              "Pause if unit contribution falls below the agreed margin floor.",
                              "Review at the end of the test against BOTH the contribution and volume thresholds.",
                              "Note campaigns, seasonal changes and customer objections; do not infer causality from a before/after comparison."],
                  limitations=["Policy thresholds are configurable business guardrails, not a fitted demand model.",
                               "Contribution excludes fixed overhead. Sales counts do not measure customer retention.",
                               "A comparable requires the same unit, scope, condition and total customer charges."])
    report["source_snapshot"] = dict(product_id=c.linked_product_id,
        product_version=linked.version if linked else None, observation_ids=sorted(o.observation_id for o in linked_obs),
        product=linked.product.model_dump(mode="json") if linked else None)
    report["discovery"] = learning_contract(c, report, today)
    report["viability"] = viability_boundary(c, unit, floor, target if action == "price_test" else None)
    report["fingerprint"] = sha256(json.dumps(report, sort_keys=True).encode()).hexdigest()
    return report


def review_outcome(plan, outcome: OutcomeRecord):
    c = Consultation.model_validate(plan["report"]["input"])
    start = plan["start"]
    started = date.fromisoformat(start["started_on"])
    if not started <= outcome.ended_on <= date.today():
        raise ValueError("End date must be between the recorded start and today")
    days = (outcome.ended_on - started).days + 1
    if days > 90:
        raise ValueError("A trial outcome must cover no more than 90 days")
    base_unit = per_unit(c.current_price_gross, c)
    actual_unit = D(start["actual_price_gross"]) / (1 + outcome.actual_vat_rate) * (1 - fee_on_net(outcome.actual_fee_rate, outcome.actual_vat_rate, outcome.actual_fee_basis)) - outcome.actual_unit_cost_net
    baseline_daily = D(c.baseline_units) / c.baseline_days
    actual_daily = D(outcome.units) / days
    baseline_contribution = baseline_daily * base_unit
    actual_contribution = actual_daily * actual_unit
    volume_ok = actual_daily >= baseline_daily * (1 - c.max_volume_loss_pct / 100)
    contribution_ok = actual_contribution >= baseline_contribution
    current_margin = actual_unit / (D(start["actual_price_gross"]) / (1 + outcome.actual_vat_rate))
    margin_ok = current_margin >= c.minimum_margin
    complete = days >= c.test_days
    comparable = outcome.fully_available and outcome.price_unchanged and not outcome.confounded
    if outcome.price_unchanged and not margin_ok:
        verdict, title = "review", "Pause the trial: the observed unit margin misses your minimum"
    elif not comparable:
        verdict, title = "inconclusive", "The comparison is affected by other changes"
    elif not complete:
        verdict, title = "early", "Keep collecting: the planned period is not complete"
    elif not contribution_ok or not volume_ok or not margin_ok:
        verdict, title = "review", "Review or stop the trial: a guardrail was missed"
    else:
        verdict, title = "promising", "Both guardrails were met in the observed period"
    return dict(verdict=verdict, title=title, observed_days=days,
                baseline_units_per_day=str(baseline_daily.quantize(D(".01"))),
                actual_units_per_day=str(actual_daily.quantize(D(".01"))),
                baseline_contribution_per_day=cash(baseline_contribution),
                actual_contribution_per_day=cash(actual_contribution),
                contribution_guardrail_met=contribution_ok, volume_guardrail_met=volume_ok,
                margin_guardrail_met=margin_ok, causal_claim=False,
                note="Observed comparison only. The baseline contribution uses the costs recorded in the consultation, not historical accounting profit. Repeat across comparable periods before adopting permanently; this does not establish a price effect or customer retention.")
