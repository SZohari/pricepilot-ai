"""Tests for the Iranian smartwatch demo scenario."""

from pathlib import Path
import sys

import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.load_demo_scenario import build_from_raw_dir, copy_demo_scenario
from src.utils.formatting import parse_price_input


SCENARIO_DIR = Path("data/scenarios/iran_smartwatch_demo_20")
REQUIRED_FILES = [
    "products_master.csv",
    "retailer_internal_demo_template.csv",
    "global_usd_reference_template.csv",
    "market_observations_template.csv",
    "fx_rate_snapshots.csv",
    "README.md",
]


def test_scenario_files_exist():
    for file_name in REQUIRED_FILES:
        assert (SCENARIO_DIR / file_name).exists()


def test_scenario_products_count_is_20():
    products = pd.read_csv(SCENARIO_DIR / "products_master.csv")
    assert len(products) == 20


def test_market_observations_count_is_80_and_at_least_three_per_product():
    observations = pd.read_csv(SCENARIO_DIR / "market_observations_template.csv")
    counts = observations.groupby("product_id").size()
    assert len(observations) == 80
    assert counts.min() >= 3
    assert len(counts) == 20


def test_scenario_product_ids_align():
    products = pd.read_csv(SCENARIO_DIR / "products_master.csv")
    retailer = pd.read_csv(SCENARIO_DIR / "retailer_internal_demo_template.csv")
    usd = pd.read_csv(SCENARIO_DIR / "global_usd_reference_template.csv")

    product_ids = set(products["product_id"])
    assert set(retailer["product_id"]) == product_ids
    assert set(usd["product_id"]) == product_ids


def test_load_demo_scenario_copies_to_temp_raw_dir(tmp_path):
    raw_dir = tmp_path / "raw"
    copied = copy_demo_scenario(SCENARIO_DIR, raw_dir)

    for file_name in [
        "products_master.csv",
        "retailer_internal_demo_template.csv",
        "global_usd_reference_template.csv",
        "market_observations_template.csv",
        "fx_rate_snapshots.csv",
        "daily_market_updates.csv",
    ]:
        assert copied[file_name].exists()
        assert (raw_dir / file_name).exists()


def test_build_pipeline_produces_20_products_from_scenario(tmp_path):
    raw_dir = tmp_path / "raw"
    output_path = tmp_path / "processed" / "dashboard_pricing_data.csv"
    copy_demo_scenario(SCENARIO_DIR, raw_dir)

    result = build_from_raw_dir(raw_dir, output_path)

    assert len(result) == 20
    assert output_path.exists()


def test_processed_scenario_output_has_no_nan_in_required_pricing_fields(tmp_path):
    raw_dir = tmp_path / "raw"
    output_path = tmp_path / "processed" / "dashboard_pricing_data.csv"
    copy_demo_scenario(SCENARIO_DIR, raw_dir)

    result = build_from_raw_dir(raw_dir, output_path)
    required_fields = [
        "usd_rate",
        "theoretical_toman_price",
        "market_min_price",
        "market_median_price",
        "market_max_price",
        "our_current_price",
        "our_cost_price",
    ]

    assert not result[required_fields].isna().any().any()


def test_manual_usd_rate_parser_accepts_commas_and_persian_digits():
    assert parse_price_input("170000") == 170000
    assert parse_price_input("170,000") == 170000
    assert parse_price_input("\u06f1\u06f7\u06f0,\u06f0\u06f0\u06f0") == 170000
