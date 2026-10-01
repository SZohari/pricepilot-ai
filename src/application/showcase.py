"""A fictional retailer with reproducible events, separate from live collection."""
from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4
from src.domain.models import Observation

STORE = {
    "name": "Kiez & Co.", "location": "Berlin, Germany", "kind": "Fictional independent wearable retailer",
    "brief": "Store pricing review: stay competitive, protect contribution and clear slow-moving stock.",
    "cases": [
        {"id": "DE-WEAR-001", "title": "Win back price competitiveness", "problem": "Our Series 12 is priced above four comparable demo offers. Reprice within the margin floor."},
        {"id": "DE-WEAR-002", "title": "Protect unit economics", "problem": "The Ultra 4 has a high replacement cost. A competitive price alone does not meet the store's contribution target."},
        {"id": "DE-WEAR-003", "title": "Avoid unnecessary price changes", "problem": "Watch SE 3 is already close to the benchmark. Hold the price rather than reacting to small differences."},
        {"id": "DE-WEAR-004", "title": "Escalate a sourcing problem", "problem": "Watch9 cannot match the market while protecting minimum margin. Review buying costs; do not blindly undercut."},
        {"id": "DE-WEAR-005", "title": "Wait for fresh evidence", "problem": "Watch Ultra2 has only stale offers. The engine must withhold a recommendation until evidence arrives."},
        {"id": "DE-WEAR-006", "title": "Release slow-moving inventory", "problem": "95 Watch8 Classic units remain, with only eight demo sales in 30 days. Test a controlled clearance price."},
    ],
}


def replay_offers(as_of):
    """A fixed market event; no web requests and no invented real retailer quotes."""
    batch=uuid4().hex[:10]
    for index,(pid,prices) in enumerate([
        ("DE-WEAR-001", [363,367,371,375]),
        ("DE-WEAR-005", [611,619,625,631]),
        ("DE-WEAR-006", [413,417,423,427]),
    ]):
        for seller_index,price in enumerate(prices):
            seller=["Spree Electronics", "Nord Technik", "Rhein Digital", "Alpine Retail"][seller_index]+" (demo)"
            yield Observation(observation_id=f"REPLAY-{batch}-{index}-{seller_index}", product_id=pid,
                seller=seller,price_gross=Decimal(price),shipping_gross=Decimal("0"),available=True,
                observed_on=as_of, observed_at=datetime.now(timezone.utc),data_origin="demo",
                source="Simulated case-study replay; not collected from the internet")
