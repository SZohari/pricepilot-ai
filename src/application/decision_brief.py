"""Financial triage and reproducible decision evidence; no invented ROI score."""
from collections import Counter, defaultdict
from decimal import Decimal
import hashlib
import json
from src.domain.pricing import recommend
from src.domain.models import fee_on_net


def brief(entry, observations, scenario):
    p = entry.product
    relevant = [o for o in observations if o.product_id == p.product_id]
    rec = recommend(p, relevant, scenario)
    cost = rec.replacement_cost_net
    net = p.current_price_gross/(1+p.vat_rate)
    effective_fee = fee_on_net(p.fee_rate, p.vat_rate, p.fee_basis)
    current_unit = net*(1-effective_fee)-cost-p.variable_cost_net
    proposed_unit = None if rec.recommended_price_gross is None else (
        rec.recommended_price_gross/(1+p.vat_rate)*(1-effective_fee)-cost-p.variable_cost_net)
    current_coverage = None if not p.sales_30d else Decimal(p.inventory)*30/p.sales_30d
    payload = {"product": p.model_dump(mode="json"), "product_version": entry.version,
               "scenario": scenario.model_dump(mode="json"), "policy_version": rec.policy_version,
               "observations": [o.model_dump(mode="json") for o in relevant]}
    fingerprint = hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    origin_counts = dict(Counter(o.data_origin for o in relevant
                                if scenario.evidence_mode == "all" or o.data_origin == scenario.evidence_mode))
    tasks = []
    if rec.quality.status == "blocked": tasks.append("Refresh comparable competitor evidence before making a pricing decision.")
    elif rec.quality.status == "limited": tasks.append("Add at least three distinct comparable sellers before trusting the benchmark.")
    if current_unit < 0: tasks.append("Current price loses contribution per unit; inspect sourcing, fees and selling price.")
    elif rec.current_margin < p.minimum_margin: tasks.append("Current price is below the minimum-margin policy.")
    if not p.inventory: tasks.append("Confirm replenishment; no units are currently available to sell.")
    elif current_coverage is None or current_coverage > 90: tasks.append("Investigate slow stock and a clearance plan before buying more inventory.")
    if not tasks: tasks.append("Review the suggested price against service positioning and commercial constraints.")
    checks = {"market_evidence": rec.quality.status,
              "minimum_margin": "pass" if rec.expected_margin is not None and rec.expected_margin >= p.minimum_margin else "blocked",
              "inventory": "pass" if p.inventory else "blocked",
              "demand_model": "missing_daily_history",
              "promotion_reference": "missing_own_price_history"}
    priority = 0 if current_unit < 0 else 1 if rec.quality.status == "blocked" else 2 if rec.requires_review else 3
    money = lambda v: None if v is None else str(v.quantize(Decimal(".01")))
    return {"product_id": p.product_id, "product_name": p.name, "product_version": entry.version,
            "fingerprint": fingerprint, "priority": priority,
            "inventory_at_cost": money(cost*p.inventory), "current_unit_contribution": money(current_unit),
            "proposed_unit_contribution": money(proposed_unit),
            "unit_contribution_change": money(None if proposed_unit is None else proposed_unit-current_unit),
            "stock_cover_days": None if current_coverage is None else round(float(current_coverage), 1),
            "checks": checks, "evidence_origins": origin_counts, "next_actions": tasks,
            "recommendation": rec.model_dump(mode="json"), "snapshot": payload,
            "limitations": ["Unit contribution changes do not imply higher total profit or preserved customers.",
                            "Stock cover extrapolates the last 30 days; it is not a demand forecast.",
                            "Price-policy approval is internal review only; no retailer price is published."]}


def portfolio(service, scenario):
    entries, observations = service.repository.snapshot()
    grouped = defaultdict(list)
    for observation in observations:
        grouped[observation.product_id].append(observation)
    briefs = [brief(e, grouped[e.product.product_id], scenario) for e in entries]
    briefs.sort(key=lambda b: (b["priority"], -Decimal(b["inventory_at_cost"]), b["product_id"]))
    return {"scenario": scenario.model_dump(mode="json"), "count": len(briefs),
            "ready_evidence": sum(b["checks"]["market_evidence"] == "ready" for b in briefs),
            "blocked_evidence": sum(b["checks"]["market_evidence"] == "blocked" for b in briefs),
            "negative_unit_contribution": sum(Decimal(b["current_unit_contribution"]) < 0 for b in briefs),
            "inventory_at_cost": str(sum((Decimal(b["inventory_at_cost"]) for b in briefs), Decimal(0))),
            "briefs": briefs}
