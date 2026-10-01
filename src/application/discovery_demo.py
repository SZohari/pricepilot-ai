"""Same financial facts, new local knowledge: a reproducible fictional walkthrough."""
from datetime import date, timedelta
from src.domain.advisory import Consultation
from src.application.advisor import consult


def discovery_demo(repository):
    today = date.today()
    base = dict(business_name="Studio Elbe · fictional", offer_name="Business portrait session", kind="service",
        unit="portrait session", origin="demo", concern="slow_sales", signal="price_objections", positioning="comparable",
        current_price_gross="119.00", unit_cost_net="48.00", vat_rate="0.19", fee_rate="0.02", minimum_margin="0.10",
        baseline_end=str(today-timedelta(days=15)), costs_checked_on=str(today), baseline_days=30, baseline_units=60,
        baseline_representative=True, test_days=14, test_capacity=35, max_volume_loss_pct="5",
        comparables=[dict(seller="Fictional studio A", total_price_gross="99.00", observed_on=str(today),
                         url="https://example.com/fictional-studio-a",same_offer=True),
                     dict(seller="Fictional studio B", total_price_gross="101.00", observed_on=str(today),
                         url="https://example.com/fictional-studio-b",same_offer=True)])
    local = {**base,"positioning":"differentiated","customer_value":dict(customer_group="Applicants with a near-term deadline",
        reason_to_choose="Same-day edited portraits; the cheaper listings deliver next week.",basis="owner_observed",
        evidence_note="Fictional owner note: five recent enquiries mentioned a deadline within 48 hours. This does not prove willingness to pay.",checked_on=str(today))}
    trial = {**local,"proposed_price_gross":"122.57","concern":"test_price"}
    steps = [
        ("price_data","Start with price data","The listings appear comparable. Customers report price objections. A small reduction is a candidate to test.",base),
        ("local_knowledge","Reveal the missing fact","The owner knows the delivery times differ. The same costs and prices now support a different next action.",local),
        ("market_test","Put a belief to the test","Suppose the owner proposes EUR 122.57. The system checks what would have to happen; it does not infer a premium from the story.",trial),
    ]
    return dict(title="The spreadsheet says discount. What is it missing?",origin="demo",
        financial_facts_unchanged=True,
        steps=[dict(id=i,label=label,explanation=explanation,report=consult(Consultation.model_validate(c),repository))
               for i,label,explanation,c in steps],
        boundary="The owner can also be wrong. A useful tool exposes the claim and what would contradict it.")
