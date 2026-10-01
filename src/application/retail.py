"""A retailer's route from a catalog to inspectable, bounded price experiments.

Purchase cost records money already committed. Replacement cost sets the chosen
replenishment constraint. Neither establishes customers' willingness to pay.
"""
from datetime import date, timedelta
from decimal import Decimal, ROUND_CEILING
from functools import lru_cache
from src.application.advisor import cash, consult, per_unit, VERSION
from src.application.service import load_demo
from src.domain.advisory import Consultation
from src.domain.models import RetailDetails, fee_on_net

D = Decimal


@lru_cache(maxsize=1)
def demo_day():
    return load_demo().as_of


class Snapshot:
    def __init__(self, repository):
        self.data = repository.snapshot()

    def snapshot(self):
        return self.data


def details_for(product):
    if product.retail:
        return product.retail, "edited_demo" if product.data_origin == "demo" else "owner_entered"
    if product.data_origin != "demo":
        return None, "missing"
    # Explicit illustrative decomposition, never inferred merchant expenses.
    variable = product.variable_cost_net
    shipping = (variable / 2).quantize(D(".01"))
    packaging = (variable / 4).quantize(D(".01"))
    day = demo_day()
    return RetailDetails(variant="Illustrative new-condition variant; confirm exact size, connectivity and strap",
        purchase_cost_net=(product.replacement_cost_net * D(".94")).quantize(D(".01")),
        shipping_cost_net=shipping, packaging_cost_net=packaging,
        returns_allowance_net=variable-shipping-packaging, costs_checked_on=day,
        sales_period_end=day-timedelta(days=1), baseline_representative=True, sales_7d_known=True,
        cost_scope_confirmed=True,
        signal="price_objections" if product.product_id == "DE-WEAR-001" else "unknown"), "demo_decomposition"


def consultation_input(p, details, *, candidate=None, cost_change_pct=D(0), max_loss=D(5), test_days=14, signal=None):
    day = demo_day() if p.data_origin == "demo" else date.today()
    replacement = (p.replacement_cost_net * (1 + cost_change_pct / 100)).quantize(D(".01"))
    observed_signal = signal or (details.signal if details else "unknown")
    concern = "slow_sales" if observed_signal in ("price_objections", "low_visibility") else "margin"
    if observed_signal == "at_capacity":
        concern = "capacity"
    if candidate is not None:
        concern = "test_price"
    if p.inventory > 0 and p.sales_30d <= 10 and concern == "margin":
        concern = "slow_sales"
    return Consultation(business_name="Kiez & Co · fictional online shop" if p.data_origin == "demo" else "My online shop",
        offer_name=p.name, kind="goods", unit="single-item order", origin="demo" if p.data_origin == "demo" else "merchant",
        concern=concern, signal=observed_signal, current_price_gross=p.current_price_gross,
        unit_cost_net=replacement+p.variable_cost_net, vat_rate=p.vat_rate, fee_rate=p.fee_rate, fee_basis=p.fee_basis,
        minimum_margin=p.minimum_margin,
        costs_checked_on=details.costs_checked_on if details else date(2000, 1, 1),
        cost_scope_confirmed=bool(details and details.cost_scope_confirmed),
        customer_shipping_gross=details.customer_shipping_gross if details else D(0),
        hypothetical_costs=bool(cost_change_pct),
        demo_as_of=day if p.data_origin == "demo" else None,
        baseline_end=details.sales_period_end if details else date(2000, 1, 1), baseline_days=30,
        baseline_units=p.sales_30d, baseline_representative=bool(details and details.baseline_representative),
        test_capacity=p.inventory, test_days=test_days, max_volume_loss_pct=max_loss,
        proposed_price_gross=candidate, linked_product_id=p.product_id,
        context_note=("Single-unit order. Current replacement cost protects the next replenishment. "
                      "Past purchase cost is shown separately; fixed overhead and customer retention are not estimated. "
                      + (f"Hypothetical supplier cost change: {cost_change_pct}%. " if cost_change_pct else "")
                      + ("Demo snapshot dated " + str(day) if p.data_origin == "demo" else "Owner-entered costs and sales.")))


def analyze(entry, repository, *, candidate=None, cost_change_pct=D(0), max_loss=D(5), test_days=14, signal=None,
            comparables=None,positioning="comparable",draft=False,knowledge_notes=None,customer_value=None):
    p = entry.product
    details, provenance = details_for(p)
    c = consultation_input(p, details, candidate=candidate, cost_change_pct=cost_change_pct,
                           max_loss=max_loss, test_days=test_days, signal=signal)
    c=Consultation.model_validate(c.model_dump() | dict(comparables=comparables or [],positioning=positioning,
                                  hypothetical_costs=bool(cost_change_pct) or draft,
                                  knowledge_notes=knowledge_notes or [],customer_value=customer_value))
    report = consult(c, repository)
    net = c.current_price_gross / (1 + c.vat_rate)
    fee = net * fee_on_net(c.fee_rate, c.vat_rate, c.fee_basis)
    replacement = c.unit_cost_net-p.variable_cost_net
    contribution = per_unit(c.current_price_gross, c)
    target = ((replacement+p.variable_cost_net)*(1+c.vat_rate) /
              (1-fee_on_net(c.fee_rate,c.vat_rate,c.fee_basis)-p.target_margin)).quantize(D(".01"), rounding=ROUND_CEILING)
    purchase = details.purchase_cost_net if details else None
    shipping = details.customer_shipping_gross if details else D(0)
    # Round displayed waterfall parts, then reconcile the final residual exactly.
    tax_display = D(cash(c.current_price_gross-net))
    fee_display = D(cash(fee))
    displayed_left = c.current_price_gross-tax_display-fee_display-replacement-p.variable_cost_net
    waterfall = [dict(label="Customer pays",amount=cash(c.current_price_gross),kind="total"),
        dict(label="VAT",amount=cash(tax_display),kind="cost"),
        dict(label="Payment / marketplace fee",amount=cash(fee_display),kind="cost"),
        dict(label="Buy the next unit",amount=cash(replacement),kind="cost"),
        dict(label="Deliver and support this order",amount=cash(p.variable_cost_net),kind="cost"),
        dict(label="Left before fixed costs",amount=cash(displayed_left),kind="remaining")]
    signals = []
    if not details or not details.cost_scope_confirmed:
        signals.append(dict(kind="missing",title="Confirm the costs",note="Itemise the order costs and confirm that no variable expense is missing."))
    if not report["market_usable"]:
        signals.append(dict(kind="missing",title="Check comparable offers",note="Use the exact model, variant, condition, delivery and availability. A listed price is not a completed sale."))
    if p.inventory == 0:
        signals.append(dict(kind="stock",title="No sellable stock",note="A price test cannot run without available stock."))
    elif p.sales_30d and D(p.inventory) < D(p.sales_30d)/30*test_days:
        signals.append(dict(kind="stock",title="Stock may run out",note="Available units are below the recent sales pace for this test period. Check replenishment first."))
    if p.sales_30d == 0 or p.inventory > p.sales_30d*3:
        signals.append(dict(kind="stock",title="Slow-moving stock",note="Check product age, a successor model and cash tied up. A separate clearance decision may accept different limits."))
    if details and details.sales_7d_known and p.sales_7d*30 < p.sales_30d*7*D(".65") and p.sales_30d:
        signals.append(dict(kind="change",title="Recent sales slowed",note="The last seven days are below the 30-day pace. Check availability, campaigns and model ageing before blaming price."))
    if c.current_price_gross < D(report["economics"]["minimum_price_gross"]):
        signals.insert(0,dict(kind="margin",title="Below your chosen minimum",note="Your price does not cover the margin you chose using the current replacement cost."))
    if details and not details.gtin:
        signals.append(dict(kind="identity",title="Exact variant needs an ID",note="Automatic matching needs the exact GTIN / EAN. Model names alone are not enough."))
    risks = [
        dict(title="Supplier / FX change",status="scenario",note="Use the cost-change control or enter a confirmed EUR supplier quote. No exchange-rate forecast is assumed."),
        dict(title="Returns and fulfilment",status="entered" if details else "missing",note="The per-order reserve is an owner estimate of unrecovered losses. It is not a returns model."),
        dict(title="Season, promotion and new models",status="owner_check",note="Record these before a test; they can change demand and invalidate a simple before/after comparison."),
        dict(title="Customer retention",status="not_measured",note="A sales-count limit does not establish whether loyal or price-sensitive customers are retained."),
    ]
    priority = 0 if any(s["kind"]=="margin" for s in signals) else 1 if report["can_start_test"] else 2 if report["blockers"] else 3
    return dict(product=p.model_dump(mode="json"),version=entry.version,details=details.model_dump(mode="json") if details else None,
        detail_origin=provenance,report=report,simulation=bool(cost_change_pct),draft=draft,priority=priority,
        insight=decision_insight(c,report),
        waterfall=waterfall,signals=signals,risks=risks,
        economics=dict(replacement_cost_net=cash(replacement),historical_purchase_net=cash(purchase) if purchase is not None else None,
            historical_contribution=cash(net-fee-purchase-p.variable_cost_net) if purchase is not None else None,
            current_contribution=cash(contribution),current_margin=str(contribution/net),target_margin=str(p.target_margin),
            target_price_gross=cash(target),target_is_not_recommendation=True,customer_shipping_gross=cash(shipping),
            current_item_price_gross=cash(c.current_price_gross-shipping),
            candidate_item_price_gross=cash(D(report['test_price_gross'])-shipping) if report['can_start_test'] else None,
            stock_cover_days=cash(D(p.inventory)*30/p.sales_30d) if p.sales_30d else None),
        intelligence=dict(policy=VERSION,numeric_engine="Decimal accounting and explicit business rules",
            demand_forecast_used=False,causal_price_effect_known=False,
            next_data="Daily SKU price, sold units, stock availability, promotion flags and dated competitor offers.",
            model_gate="A forecast must beat a simple baseline on later, unseen data. That alone does not identify a causal price effect."))


def decision_insight(c,report):
    """Translate a changed input into conditional consequences, never a forecast."""
    current=per_unit(c.current_price_gross,c)
    considered=c.proposed_price_gross or D(report['considered_price_gross'])
    after=per_unit(considered,c)
    difference=after-current
    baseline=D(c.baseline_units)*c.test_days/c.baseline_days
    required=report['economics']['minimum_units_with_volume_guardrail']
    if not report['can_start_test']:
        message=report['why']
    elif difference<0:
        message=f"You keep EUR {cash(-difference)} less per sale. This price only makes sense if extra sales make up that difference."
    else:
        message=f"You keep EUR {cash(difference)} more per sale. The test still has to meet your sales-loss limit."
    gap=(c.current_price_gross/D(report['market_median_gross'])-1)*100 if report['market_usable'] else None
    return dict(current_price=cash(c.current_price_gross),considered_price=cash(considered),
        current_per_sale=cash(current),considered_per_sale=cash(after),difference_per_sale=cash(difference),
        current_margin=str(current/(c.current_price_gross/(1+c.vat_rate))),
        considered_margin=str(after/(considered/(1+c.vat_rate))),
        baseline_units=str(baseline.quantize(D('.1'))),required_units=required,
        extra_units=max(0,int(D(required)-baseline.to_integral_value(rounding=ROUND_CEILING))) if required is not None else None,
        market_gap_pct=str(gap.quantize(D('.1'))) if gap is not None else None,
        message=message,allowed=report['can_start_test'],forecast=False)


def workspace(repository):
    snapshot = Snapshot(repository)
    rows = []
    for entry in snapshot.data[0]:
        item = analyze(entry, snapshot)
        r=item['report'];p=entry.product
        rows.append(dict(product_id=p.product_id,name=p.name,brand=p.brand,origin=p.data_origin,version=entry.version,
            current_price_gross=cash(p.current_price_gross),action=r['action'],title=r['title'],can_start_test=r['can_start_test'],
            price_to_test=r['test_price_gross'],floor=r['economics']['minimum_price_gross'],contribution=item['economics']['current_contribution'],
            stock=p.inventory,sales_30d=p.sales_30d,market_count=len(r['evidence']),priority=item['priority'],
            needs_setup=not p.retail and p.data_origin!='demo',signals=item['signals']))
    rows.sort(key=lambda r:(r['priority'],r['product_id']))
    return dict(name="Kiez & Co",demo_snapshot=str(demo_day()),rows=rows,
        counts=dict(products=len(rows),tests=sum(r['can_start_test'] for r in rows),
                    cost_attention=sum(r['priority']==0 for r in rows),setup=sum(r['needs_setup'] for r in rows)),
        journey=["Check your inputs","Choose one action","Apply it yourself","Review what happened"])
