"""Inspectable decision boundaries and learning contracts, not demand estimates.

The boundary is accounting under explicit inputs. It says what would have to
happen; it deliberately assigns no probability to that outcome.
"""
from datetime import date
from decimal import Decimal, ROUND_CEILING, ROUND_HALF_UP
from src.domain.models import fee_on_net

D = Decimal


def viability_boundary(c, current_unit, floor, chosen_price=None):
    baseline = D(c.baseline_units) / c.baseline_days * c.test_days
    volume_floor = (baseline * (1 - c.max_volume_loss_pct / 100)).to_integral_value(rounding=ROUND_CEILING)
    prices = {max(D(".01"), (c.current_price_gross * (1 + D(i) / 100)).quantize(D(".01"), rounding=ROUND_HALF_UP)) for i in range(-10, 11)}
    if c.proposed_price_gross is not None:
        prices.add(c.proposed_price_gross)
    if chosen_price is not None:
        prices.add(chosen_price)
    rows = []
    for price in sorted(prices):
        unit = price / (1 + c.vat_rate) * (1 - fee_on_net(c.fee_rate, c.vat_rate, c.fee_basis)) - c.unit_cost_net
        required = None
        financial = None
        if unit > 0:
            financial = max(D(0), (baseline * current_unit / unit).to_integral_value(rounding=ROUND_CEILING))
            required = max(financial, volume_floor)
        within_move = abs(price / c.current_price_gross - 1) <= D(".10")
        arithmetic_feasible = required is not None and required <= c.test_capacity and price >= floor and within_move
        reasons = []
        if unit <= 0: reasons.append("No positive contribution")
        if price < floor: reasons.append("Below your margin floor")
        if not within_move: reasons.append("Outside the ±10% trial limit")
        if required is not None and required > c.test_capacity: reasons.append("More sales required than capacity allows")
        rows.append(dict(price_gross=str(price), contribution_units=int(financial) if financial is not None else None,
                         volume_units=int(volume_floor), required_units=int(required) if required is not None else None,
                         feasible=arithmetic_feasible, reasons=reasons))
    return dict(kind="required_outcomes_not_demand", trial_days=c.test_days, capacity=c.test_capacity,
                baseline_units=str(baseline.quantize(D(".1"))), points=rows,
                available=c.baseline_units > 0 and c.baseline_representative,
                caveat="Feasible means the accounting and capacity constraints permit a test. It does not mean customers will buy.")


def learning_contract(c, report, today=None):
    today = today or date.today()
    value = c.customer_value
    local = None
    if value:
        local = {**value.model_dump(mode="json"), "independently_verified":False,
                 "stale":(today - value.checked_on).days > 30,
                 "status":"owner_observation" if value.basis == "owner_observed" else "untested_belief"}
    market_role = "comparison" if report["market_usable"] else "context_only"
    knowledge = [
        dict(kind="owner_inputs" if c.origin == "merchant" else "simulated_inputs", title="What the economics can establish",
             statement="The minimum margin and required sales follow from the costs, VAT and fees supplied. They do not establish willingness to pay."),
        dict(kind="market_evidence" if report["evidence"] else "missing_evidence", title="What competitors can tell us",
             statement="Comparable listings are reference points. An asking price is not proof of a transaction or customer preference."),
        dict(kind="chosen_policy", title="What the owner has chosen",
             statement=f"The minimum contribution margin ({c.minimum_margin*100:g}%) and acceptable volume loss ({c.max_volume_loss_pct:g}%) are business choices, not facts discovered by the model."),
        dict(kind="unknown", title="What the market still has to reveal",
             statement="Customer response to a new price, repeat purchasing and competitors' reactions remain unknown."),
    ]
    if report["can_start_test"]:
        required = report["economics"]["minimum_units_with_volume_guardrail"]
        hypothesis = f"At EUR {report['test_price_gross']}, this offer can still achieve at least {required} sales over {c.test_days} days without sacrificing the agreed contribution or volume guardrails."
        reversal = "Reject this trial as a business choice if contribution, volume or unit margin misses its guardrail. A campaign, stockout or changing offer makes the price-effect interpretation inconclusive."
        question = "Will the same customer population still choose this offer at the new price, under conditions comparable to the baseline?"
        next_evidence = "Record the price offered, purchases, availability and reasons for declined quotes. Keep scope and acquisition conditions stable."
    elif report["action"] == "validate_value":
        hypothesis = "The stated difference matters enough to this customer group that a cheaper, different offer is not a like-for-like alternative."
        reversal = "Reconsider the positioning if customers do not recognise the difference, or decline the premium despite recognising it. Do not reinterpret every rejection as a failure to understand your offer."
        question = "What are customers trying to achieve, and what did they actually choose when shown both clearly described offers?"
        next_evidence = "Record a small set of comparable enquiries and choices, including lost sales. Treat conversations as exploratory evidence, not a representative willingness-to-pay estimate."
    else:
        hypothesis = "The current bottleneck must be understood before attributing a sales problem to price."
        reversal = "Change the diagnosis when the missing input is observed: confirmed costs, available capacity, customer objections or sufficient enquiries."
        question = "Which missing fact could change the next action?"
        next_evidence = report["next_step"]
    return dict(principle="A price is a hypothesis about a voluntary exchange.", local_knowledge=local,
                market_role=market_role, knowledge=knowledge, hypothesis=hypothesis,
                question=question, next_evidence=next_evidence, what_would_change_our_mind=reversal,
                open_questions=[observation_plan(n,today) for n in c.knowledge_notes],
                confidence_score=None, causal_identification=False,
                method_note="Economic inspiration informs the design. These rules and before/after checks do not empirically validate a school of economics.")


def observation_plan(note, today):
    plans = {
        'price': ('Are lost sales explicitly about the full price?', 'For seven days, record enquiries, purchases and the stated reason for each declined offer. Keep the displayed total and availability.', 'Price mentioned / all recorded declined offers. Missing reasons remain unknown; this is not price elasticity.'),
        'visibility': ('Are enough relevant people seeing the offer?', 'Use product-page views or qualified enquiries and purchases from the same source and period. Note campaign changes.', 'Purchases / visits or enquiries with the same definition. A low count alone does not explain why.'),
        'trust': ('Do doubts about the shop prevent a purchase?', 'Ask people who decline what was missing. Record mentions of warranty, returns or seller reliability, including other reasons and no answer.', 'Trust-related reasons / all recorded declined offers. This is a limited observation, not a trust score.'),
        'product_fit': ('Does this model meet the customer’s actual need?', 'Record requested features, the offered variant, the alternative chosen and reasons given. Include people who bought nothing.', 'Feature mismatch / recorded enquiries. Conversations reveal possible causes; they do not establish market-wide demand.'),
        'delivery': ('Does the delivery offer lose the sale?', 'Record promised delivery time, delivery charge and stated reasons for accepting or declining the same offer.', 'Delivery-related reasons / all recorded declined offers. Do not infer a willingness-to-pay premium from the count.'),
        'repeat_customers': ('Are returning customers changing their behaviour?', 'Use anonymous aggregate returning/new-customer orders from the shop system over comparable periods; record promotions and availability.', 'Returning-customer order share and counts. Order mix alone does not establish retention or a price effect.'),
        'other': ('What observable finding could change this decision?', 'Write down the event, the source, the date and an observation that would contradict the idea. Include missing answers.', 'Choose a consistent count and denominator only when meaningful. A qualitative finding can stay qualitative.'),
    }
    question, collect, interpret = plans[note.topic]
    return {**note.model_dump(mode='json'), 'question':question, 'collect':collect, 'interpret':interpret,
            'independently_verified':False,'stale':(today-note.checked_on).days>30,
            'numeric_score':None}
