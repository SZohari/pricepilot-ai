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
from src.api.schemas import (
    BatchRecommendationResponse,
    BuildDatasetResponse,
    ErrorResponse,
    HealthResponse,
    ProductSummary,
    RecommendationRequest,
    RecommendationResponse,
)
from src.pricing.recommendation import recommend_price


app = FastAPI(
    title="PricePilot AI API",
    description="Market-aware pricing operations API for volatile retail markets.",
    version="0.1.0",
    openapi_tags=[
        {"name": "Health", "description": "Service availability checks."},
        {"name": "Products", "description": "Processed product catalog access."},
        {"name": "Recommendations", "description": "Explainable pricing recommendations."},
        {"name": "Dataset", "description": "Processed dataset build operations."},
    ],
)


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


@app.get(
    "/health",
    response_model=HealthResponse,
    tags=["Health"],
    summary="Check API health",
)
def health() -> HealthResponse:
    """Return service availability status."""
    return HealthResponse(status="ok", service="PricePilot AI API", version=app.version)


@app.get(
    "/products",
    response_model=list[ProductSummary],
    tags=["Products"],
    summary="List processed products",
    responses={500: {"model": ErrorResponse}},
)
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


@app.post(
    "/recommend-price",
    response_model=RecommendationResponse,
    tags=["Recommendations"],
    summary="Recommend a price for one product",
    responses={400: {"model": ErrorResponse}},
)
def recommendation(payload: RecommendationRequest) -> Dict[str, Any]:
    """Produce one recommendation using the existing pricing engine."""
    try:
        return recommend_price(payload.model_dump(exclude_none=True))
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post(
    "/recommendations/batch",
    response_model=BatchRecommendationResponse,
    tags=["Recommendations"],
    summary="Recommend prices for all processed products",
    responses={404: {"model": ErrorResponse}, 500: {"model": ErrorResponse}},
)
def batch_recommendations() -> Dict[str, Any]:
    """Produce recommendations for every product in the processed dataset."""
    try:
        dataset = load_processed_pricing_data()
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    recommendations = [recommend_price(row) for row in _records_for_recommendation(dataset)]
    return {"count": len(recommendations), "recommendations": recommendations}


@app.post(
    "/build-dataset",
    response_model=BuildDatasetResponse,
    tags=["Dataset"],
    summary="Build the processed pricing dataset",
    responses={400: {"model": ErrorResponse}},
)
def build_dataset() -> Dict[str, Any]:
    """Build and persist the processed dashboard dataset."""
    try:
        output_path, dataset = _build_and_save_processed_dataset()
    except (FileNotFoundError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return {
        "status": "success",
        "output_path": str(output_path),
        "product_count": len(dataset),
        "columns": list(dataset.columns),
    }
