from datetime import date
from decimal import Decimal as D
import pytest
from pydantic import ValidationError
from src.domain.models import Dataset, Observation, Product, Scenario, Strategy
from src.domain.pricing import contribution_margin, market_snapshot, price_for_margin, recommend

DAY = date(2026, 9, 26)


def product(**kwargs):
    values = dict(product_id="P1", name="Test watch", current_price_gross="149.00",
                  replacement_cost_net="80.00", variable_cost_net="4.50",
                  fee_rate="0.02", inventory=20, sales_7d=2, sales_30d=8)
    return Product(**(values | kwargs))


def offer(identifier="O1", **kwargs):
    values = dict(observation_id=identifier, product_id="P1", seller=identifier,
                  price_gross="149.00", available=True, observed_on=DAY, source="test")
    return Observation(**(values | kwargs))


def offers():
    return [offer("A", price_gross="145.00"), offer("B"), offer("C", price_gross="153.00")]


@pytest.mark.parametrize("field,value", [
    ("current_price_gross", "-1"), ("replacement_cost_net", "NaN"),
    ("replacement_cost_net", "Infinity"), ("current_price_gross", "10.001"),
    ("inventory", -1), ("inventory", 1.5), ("target_margin", "1"),
    ("fee_rate", ".9"), ("minimum_margin", ".5"),
    ("sales_7d", 10), ("currency", "USD"), ("name", "  "),
])
def test_invalid_products_rejected(field, value):
    with pytest.raises(ValidationError):
        product(**{field: value})


def test_margin_uses_net_revenue_and_variable_costs():
    p = product(current_price_gross="119.00", replacement_cost_net="60.00",
                variable_cost_net="5.00", fee_rate="0.02")
    assert contribution_margin(D("119.00"), p, p.replacement_cost_net) == D(".33")


@pytest.mark.parametrize("cost", ["1.01", "80.13", "200.00", "999.99"])
@pytest.mark.parametrize("strategy", list(Strategy))
@pytest.mark.parametrize("shock", [-50, 0, 30, 100])
def test_every_strategy_preserves_floor_after_cent_rounding(cost, strategy, shock):
    p = product(replacement_cost_net=cost, strategy=strategy)
    result = recommend(p, offers(), Scenario(as_of=DAY, cost_change_pct=shock))
    assert result.recommended_price_gross >= result.floor_price_gross
    for value in result.strategy_prices.values():
        assert value >= result.floor_price_gross
        assert value.as_tuple().exponent == -2
        assert contribution_margin(value, p, result.replacement_cost_net) >= p.minimum_margin - D("1e-25")


def test_cost_shock_changes_floor_and_profit_protection():
    p = product(strategy=Strategy.PROFIT)
    a = recommend(p, offers(), Scenario(as_of=DAY))
    b = recommend(p, offers(), Scenario(as_of=DAY, cost_change_pct=50))
    assert b.floor_price_gross > a.floor_price_gross
    assert b.recommended_price_gross > a.recommended_price_gross
    assert any("scenario" in r for r in b.reasons)


def test_exact_two_percent_increase_is_not_decrease_or_hold():
    p = product(current_price_gross="100.00", replacement_cost_net="40.00", strategy=Strategy.BALANCED)
    observations = [offer(str(i), price_gross="103.03") for i in range(3)]
    result = recommend(p, observations, Scenario(as_of=DAY))
    assert result.recommended_price_gross == D("102.00")
    assert result.action == "increase_price"


def test_hold_returns_actual_current_price():
    p = product()
    result = recommend(p, offers(), Scenario(as_of=DAY))
    assert result.action == "hold_price"
    assert result.recommended_price_gross == p.current_price_gross
    assert result.expected_margin == result.current_margin


def test_new_unavailable_offer_invalidates_old_seller_offer():
    observations = [
        offer("old", seller="Store", observed_on=date(2026, 9, 24)),
        offer("new", seller="STORE", available=False),
    ]
    prices, quality = market_snapshot(observations, Scenario(as_of=DAY))
    assert prices == []
    assert quality.unavailable == 1
    assert quality.superseded == 1


def test_stale_future_and_delivery_are_accounted_for():
    observations = [
        offer("old", observed_on=date(2026, 8, 1)),
        offer("future", observed_on=date(2026, 10, 1)),
        offer("ok", price_gross="100.00", shipping_gross="4.90"),
    ]
    prices, quality = market_snapshot(observations, Scenario(as_of=DAY))
    assert prices == [D("104.90")]
    assert quality.stale == quality.future == 1
    assert quality.status == "limited"


def test_no_market_evidence_blocks_pricing_without_dropping_product():
    result = recommend(product(), [], Scenario(as_of=DAY))
    assert result.product_id == "P1"
    assert result.recommended_price_gross is None
    assert result.action == "urgent_review"


def test_dataset_cannot_reference_unknown_product():
    with pytest.raises(ValidationError):
        Dataset(name="test", as_of=DAY, products=[product()],
                observations=[offer(product_id="missing")])


def test_same_day_updates_follow_input_order_not_random_id():
    prices, _ = market_snapshot([offer("Z", seller="same"), offer("A", seller="same", available=False)],
                               Scenario(as_of=DAY))
    assert not prices
