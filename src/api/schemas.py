"""Pydantic request and response contracts for the PricePilot API."""

from pydantic import BaseModel, ConfigDict


RECOMMENDATION_EXAMPLE = {
    "product_id": "APPLE-WATCH-ULTRA-2",
    "product_name": "Apple Watch Ultra 2",
    "brand": "Apple",
    "model": "Watch Ultra 2",
    "our_current_price": 320000000,
    "our_cost_price": 280000000,
    "market_min_price": 300000000,
    "market_median_price": 330000000,
    "market_max_price": 360000000,
    "base_usd_price": 799,
    "usd_rate": 170000,
    "our_inventory": 4,
    "our_sales_7d": 2,
    "our_sales_30d": 9,
    "our_target_margin": 0.18,
    "our_strategy": "balanced",
}


class HealthResponse(BaseModel):
    """API availability information."""

    status: str
    service: str
    version: str


class ProductSummary(BaseModel):
    """Catalog fields exposed by the products endpoint."""

    product_id: str
    product_name: str | None = None
    brand: str | None = None
    model: str | None = None


class BuildDatasetResponse(BaseModel):
    """Result details after rebuilding the processed dataset."""

    status: str
    output_path: str
    product_count: int
    columns: list[str]


class RecommendationRequest(BaseModel):
    """Pricing inputs passed through to the existing recommendation engine."""

    model_config = ConfigDict(
        extra="allow",
        json_schema_extra={"example": RECOMMENDATION_EXAMPLE},
    )

    product_id: str | None = None
    product_name: str | None = None
    brand: str | None = None
    model: str | None = None
    our_current_price: float | int | None = None
    our_cost_price: float | int | None = None
    market_min_price: float | int | None = None
    market_median_price: float | int | None = None
    market_max_price: float | int | None = None
    base_usd_price: float | int | None = None
    usd_rate: float | int | None = None
    our_inventory: float | int | None = None
    our_sales_7d: float | int | None = None
    our_sales_30d: float | int | None = None
    our_target_margin: float | None = None
    our_strategy: str | None = None


class RecommendationResponse(BaseModel):
    """Key output fields from an explainable pricing recommendation."""

    product_id: str | None = None
    product_name: str | None = None
    recommended_price: float | int | None = None
    current_price: float | int | None = None
    action: str | None = None
    risk_level: str | None = None
    selected_strategy: str | None = None
    selected_strategy_price: float | int | None = None
    strategy_explanation: str | None = None
    explanation: str | None = None
    triggered_rules: list[str] | None = None


class BatchRecommendationResponse(BaseModel):
    """Recommendations returned for all processed products."""

    count: int
    recommendations: list[RecommendationResponse]


class ErrorResponse(BaseModel):
    """Documented API error response."""

    detail: str
