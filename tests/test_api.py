"""Tests for the lightweight FastAPI interface."""

from pathlib import Path

import pandas as pd
from fastapi.testclient import TestClient

from src.api import main


client = TestClient(main.app)


def _phase2_product() -> dict:
    return {
        "product_id": "TEST-WATCH",
        "product_name": "Test Watch",
        "brand": "Test",
        "model": "One",
        "category": "Wearable",
        "base_usd_price": 100.0,
        "usd_rate": 170_000,
        "theoretical_toman_price": 17_000_000,
        "market_min_price": 18_000_000,
        "market_median_price": 19_000_000,
        "market_max_price": 20_000_000,
        "our_current_price": 18_500_000,
        "our_cost_price": 14_000_000,
        "our_inventory": 20,
        "our_sales_7d": 4,
        "our_sales_30d": 15,
        "our_target_margin": 0.25,
        "our_strategy": "balanced",
    }


def test_health_works():
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "PricePilot AI API",
        "version": "0.1.0",
    }


def test_products_returns_documented_product_fields(monkeypatch):
    monkeypatch.setattr(
        main,
        "load_processed_pricing_data",
        lambda: pd.DataFrame([_phase2_product()]),
    )

    response = client.get("/products")

    assert response.status_code == 200
    assert response.json() == [{
        "product_id": "TEST-WATCH",
        "product_name": "Test Watch",
        "brand": "Test",
        "model": "One",
    }]


def test_recommend_price_returns_recommended_price():
    response = client.post("/recommend-price", json=_phase2_product())

    assert response.status_code == 200
    result = response.json()
    assert result["recommended_price"] is not None
    assert result["action"] is not None
    assert result["risk_level"] is not None


def test_recommendations_batch_returns_documented_envelope(monkeypatch):
    monkeypatch.setattr(
        main,
        "load_processed_pricing_data",
        lambda: pd.DataFrame([_phase2_product()]),
    )

    response = client.post("/recommendations/batch")

    assert response.status_code == 200
    assert response.json()["count"] == 1
    assert response.json()["recommendations"][0]["product_id"] == "TEST-WATCH"


def test_build_dataset_returns_controlled_success(monkeypatch):
    dataset = pd.DataFrame([_phase2_product()])
    monkeypatch.setattr(
        main,
        "_build_and_save_processed_dataset",
        lambda: (Path("data/processed/dashboard_pricing_data.csv"), dataset),
    )

    response = client.post("/build-dataset")

    assert response.status_code == 200
    assert response.json() == {
        "status": "success",
        "output_path": str(Path("data/processed/dashboard_pricing_data.csv")),
        "product_count": 1,
        "columns": list(dataset.columns),
    }
