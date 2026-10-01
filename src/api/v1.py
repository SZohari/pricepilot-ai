"""Stable contracts for a future web/mobile client. Writes require explicit configuration."""
from datetime import date
from functools import lru_cache
import hmac
import os
from typing import Annotated
from fastapi import APIRouter, Depends, Header, HTTPException, Query
from pydantic import Field
from src.application.service import PricingService, demo_service
from src.domain.models import CatalogEntry, Contract, Dataset, Observation, Product, Recommendation, Scenario
from src.domain.pricing import recommend
from src.infrastructure.repository import ConflictError, SQLiteRepository

router = APIRouter(prefix="/api/v1", tags=["Retail v1"])


@lru_cache
def get_service() -> PricingService:
    path = os.getenv("PRICEPILOT_DB_PATH")
    return PricingService(SQLiteRepository(path)) if path else demo_service()


def require_writer(x_api_key: Annotated[str | None, Header()] = None):
    expected = os.getenv("PRICEPILOT_API_KEY")
    if not expected:
        raise HTTPException(403, "Writes are disabled. Configure PRICEPILOT_API_KEY for a trusted local workspace.")
    if x_api_key is None or not hmac.compare_digest(x_api_key, expected):
        raise HTTPException(401, "Invalid API key.")


class ProductWrite(Contract):
    product: Product
    expected_version: int = Field(default=0, ge=0)


class PriceRequest(Contract):
    product: Product
    observations: list[Observation] = Field(max_length=1000)
    scenario: Scenario


class RecommendationBatch(Contract):
    count: int
    recommendations: list[Recommendation]


@router.get("/products", response_model=list[CatalogEntry])
def products(service: PricingService = Depends(get_service)):
    return service.repository.snapshot()[0]


@router.post("/recommendations/preview", response_model=Recommendation)
def preview(payload: PriceRequest):
    if any(o.product_id != payload.product.product_id for o in payload.observations):
        raise HTTPException(422, "All observations must belong to the requested product.")
    return recommend(payload.product, payload.observations, payload.scenario)


@router.post("/recommendations", response_model=RecommendationBatch)
def recommendations(scenario: Scenario, service: PricingService = Depends(get_service)):
    results = service.recommendations(scenario)
    return RecommendationBatch(count=len(results), recommendations=results)


@router.put("/products/{product_id}", response_model=CatalogEntry, dependencies=[Depends(require_writer)])
def save_product(product_id: str, payload: ProductWrite, service: PricingService = Depends(get_service)):
    if product_id != payload.product.product_id:
        raise HTTPException(422, "Path and body product IDs differ.")
    try:
        return service.repository.save_product(payload.product, payload.expected_version)
    except ConflictError as exc:
        raise HTTPException(409, str(exc)) from exc


@router.post("/observations", status_code=201, dependencies=[Depends(require_writer)])
def add_observation(payload: Observation, service: PricingService = Depends(get_service)):
    try:
        service.repository.add_observation(payload)
    except ConflictError as exc:
        raise HTTPException(409, str(exc)) from exc
    return {"status": "created", "observation_id": payload.observation_id}


@router.post("/datasets/import", status_code=201, dependencies=[Depends(require_writer)])
def import_dataset(payload: Dataset, service: PricingService = Depends(get_service)):
    try:
        service.repository.import_dataset(payload)
    except ConflictError as exc:
        raise HTTPException(409, str(exc)) from exc
    return {"status": "created", "product_count": len(payload.products)}


@router.get("/datasets/export", response_model=Dataset)
def export_dataset(as_of: date, service: PricingService = Depends(get_service)):
    if not service.repository.snapshot()[0]:
        raise HTTPException(404, "Workspace is empty.")
    return service.export_dataset(as_of)


@router.get("/audit")
def audit(limit: int = Query(default=100, ge=1, le=1000), service: PricingService = Depends(get_service)):
    return service.repository.audit_log(limit)
