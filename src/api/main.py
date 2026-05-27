"""FastAPI endpoints for PricePilot pricing recommendations and dataset builds."""

from pathlib import Path
from typing import Any, Dict, List

import pandas as pd
from fastapi import FastAPI, HTTPException

from src.data.build_pricing_dataset import (
    build_dashboard_pricing_dataset,
    load_global_usd_reference,
    load_market_observations,
    load_processed_pricing_data,
    load_retailer_internal_data,
    save_dashboard_pricing_dataset,
)
from src.data.manual_entry import (
    load_daily_market_updates,
    load_fx_rate_snapshots,
    load_products_master,
)
from src.pricing.recommendation import recommend_price


app = FastAPI(title="PricePilot AI API", version="0.1.0")


def _records_for_recommendation(df: pd.DataFrame) -> List[Dict[str, Any]]:
    """Convert dataset rows to dictionaries without passing pandas NaN values."""
    clean_df = df.where(pd.notna(df), None)
    return clean_df.to_dict(orient="records")


def _build_and_save_processed_dataset() -> tuple[Path, pd.DataFrame]:
    """Run the existing raw-to-processed dataset build workflow."""
    dataset = build_dashboard_pricing_dataset(
        load_market_observations("data/raw/market_observations_template.csv"),
        load_retailer_internal_data("data/raw/retailer_internal_demo_template.csv"),
        load_global_usd_reference("data/raw/global_usd_reference_template.csv"),
        daily_updates_df=load_daily_market_updates("data/raw/daily_market_updates.csv"),
        fx_snapshots_df=load_fx_rate_snapshots("data/raw/fx_rate_snapshots.csv"),
        products_df=load_products_master("data/raw/products_master.csv"),
    )
    output_path = save_dashboard_pricing_dataset(dataset)
    return output_path, dataset


@app.get("/health")
def health() -> Dict[str, str]:
    """Return service availability status."""
    return {"status": "ok", "service": "PricePilot AI API"}


@app.get("/products")
def products() -> List[Dict[str, Any]]:
    """Return processed product catalog metadata when a built dataset exists."""
    try:
        dataset = load_processed_pricing_data()
    except FileNotFoundError:
        return []
    except ValueError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    fields = ["product_id", "product_name", "brand", "model"]
    return dataset.reindex(columns=fields).fillna("").to_dict(orient="records")


@app.post("/recommend-price")
def recommendation(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Produce one recommendation using the existing pricing engine."""
    try:
        return recommend_price(payload)
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/recommendations/batch")
def batch_recommendations() -> List[Dict[str, Any]]:
    """Produce recommendations for every product in the processed dataset."""
    try:
        dataset = load_processed_pricing_data()
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return [recommend_price(row) for row in _records_for_recommendation(dataset)]


@app.post("/build-dataset")
def build_dataset() -> Dict[str, Any]:
    """Build and persist the processed dashboard dataset."""
    try:
        output_path, dataset = _build_and_save_processed_dataset()
    except (FileNotFoundError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return {"output_path": str(output_path), "product_count": len(dataset)}
