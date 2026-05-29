"""Tests for Streamlit demo dataset bootstrap behavior."""

from pathlib import Path
import sys

import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.dashboard import app as dashboard_app


SCENARIO_DIR = Path("data/scenarios/iran_smartwatch_demo_20")


def test_prepare_demo_dataset_creates_missing_processed_dataset(tmp_path):
    raw_dir = tmp_path / "raw"
    processed_path = tmp_path / "processed" / "dashboard_pricing_data.csv"

    result = dashboard_app.prepare_demo_dataset(
        processed_path=processed_path,
        scenario_dir=SCENARIO_DIR,
        raw_dir=raw_dir,
    )

    assert processed_path.exists()
    assert len(result) == 20
    assert pd.read_csv(processed_path)["product_id"].nunique() == 20


def test_prepare_demo_dataset_returns_existing_readable_processed_dataset(tmp_path):
    raw_dir = tmp_path / "raw"
    processed_path = tmp_path / "processed" / "dashboard_pricing_data.csv"
    first = dashboard_app.prepare_demo_dataset(
        processed_path=processed_path,
        scenario_dir=SCENARIO_DIR,
        raw_dir=raw_dir,
    )

    second = dashboard_app.prepare_demo_dataset(
        processed_path=processed_path,
        scenario_dir=SCENARIO_DIR,
        raw_dir=raw_dir,
    )

    assert len(first) == 20
    assert len(second) == 20


def test_processed_dataset_missing_is_not_ready(tmp_path):
    processed_path = tmp_path / "missing" / "dashboard_pricing_data.csv"

    assert dashboard_app.processed_dataset_is_ready(processed_path) is False


def test_processed_dataset_empty_file_is_not_ready(tmp_path):
    processed_path = tmp_path / "processed" / "dashboard_pricing_data.csv"
    processed_path.parent.mkdir(parents=True)
    processed_path.write_text("", encoding="utf-8")

    assert dashboard_app.processed_dataset_is_ready(processed_path) is False


def test_public_data_source_defaults_to_demo_scenario():
    assert dashboard_app.DEFAULT_PUBLIC_DATA_SOURCE == "Demo Scenario (20 Products)"
    assert dashboard_app.PUBLIC_DATA_SOURCE_OPTIONS[0] == "Demo Scenario (20 Products)"
    assert "Sample Data (Generated)" not in dashboard_app.PUBLIC_DATA_SOURCE_OPTIONS


def test_dashboard_import_exposes_main():
    assert callable(dashboard_app.main)
