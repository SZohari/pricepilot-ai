from pathlib import Path
import pandas as pd
import pytest
from scripts.load_demo_scenario import copy_demo_scenario
from src.dashboard.legacy import prepare_demo_dataset
from src.data.manual_entry import validate_daily_market_update
from src.data.market_aggregation import aggregate_market_observations, validate_market_observations
from src.pricing.rules import determine_action
from src.pricing.strategies import calculate_strategy_prices
from src.pricing.recommendation import recommend_price

SCENARIO = Path("data/scenarios/iran_smartwatch_demo_20")


def test_existing_raw_data_survives_missing_processed_file(tmp_path):
    raw = tmp_path / "raw"
    copy_demo_scenario(SCENARIO, raw)
    file = raw / "retailer_internal_demo_template.csv"
    data = pd.read_csv(file)
    data.loc[0, "our_inventory"] = 123
    data.to_csv(file, index=False)
    before = {p.name: p.read_bytes() for p in raw.iterdir()}
    prepare_demo_dataset(tmp_path / "built.csv", SCENARIO, raw)
    assert before == {p.name: p.read_bytes() for p in raw.iterdir()}


def test_copy_demo_refuses_to_replace_even_partial_existing_data(tmp_path):
    (tmp_path / "daily_market_updates.csv").write_text("sentinel")
    with pytest.raises(ValueError):
        copy_demo_scenario(SCENARIO, tmp_path)
    assert (tmp_path / "daily_market_updates.csv").read_text() == "sentinel"


def test_legacy_floor_exact_boundary_and_strategy_label():
    row = dict(our_current_price=2_000_000, our_cost_price=2_000_000, our_target_margin=.3,
               market_min_price=900_000, market_median_price=1_000_000, market_max_price=1_100_000,
               our_strategy="Premium Positioning")
    prices = calculate_strategy_prices(row)
    assert min(prices.values()) >= 2_300_000
    assert recommend_price(row)["selected_strategy"] == "premium_positioning"
    assert recommend_price(row, usd_shock=30)["recommended_price"] > prices["premium_positioning"]
    assert determine_action(1_000_000, 1_020_000, "low") == "increase_price"


@pytest.mark.parametrize("value", [-1, 0, float("nan"), float("inf")])
def test_manual_prices_must_be_finite_positive(value):
    assert not validate_daily_market_update({"product_id": "P", "torob_min_price": value})[0]


def test_missing_product_id_returns_validation_issues():
    valid, issues = validate_market_observations(pd.DataFrame({"listed_price": [1]}))
    assert not valid
    assert any("product_id" in issue for issue in issues)


def test_unavailable_legacy_offer_does_not_lower_market_minimum():
    data = pd.DataFrame({"product_id": ["P", "P"], "listed_price": [1, 100],
                         "seller_name": ["A", "B"], "availability_status": ["unavailable", "available"]})
    assert aggregate_market_observations(data).iloc[0].market_min_price == 100
