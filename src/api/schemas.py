"""Pydantic request and response contracts for the PricePilot API."""

import math
from pydantic import BaseModel, ConfigDict, model_validator


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
        allow_inf_nan=False,
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


    @model_validator(mode="after")
    def validate_pricing_inputs(self):
        data = self.model_dump(exclude_none=True)
        if "our_current_price" in data:
            required = ["our_current_price", "our_cost_price", "market_min_price",
                        "market_median_price", "market_max_price"]
            price_fields = required
            low, mid, high = "market_min_price", "market_median_price", "market_max_price"
        else:
            required = ["current_price", "cost_price", "inventory", "target_margin",
                        "competitor_min_price", "competitor_median_price", "competitor_max_price",
                        "usd_change_7d", "sales_7d", "sales_30d", "conversion_rate"]
            price_fields = ["current_price", "cost_price", "competitor_min_price",
                            "competitor_median_price", "competitor_max_price"]
            low, mid, high = "competitor_min_price", "competitor_median_price", "competitor_max_price"
        missing = [key for key in required if key not in data]
        if missing:
            raise ValueError("Missing pricing fields: " + ", ".join(missing))
        for key in price_fields:
            value = data[key]
            if isinstance(value, bool) or not isinstance(value, (float, int)) or not math.isfinite(value) or value <= 0:
                raise ValueError(key + " must be a finite positive number")
        if not data[low] <= data[mid] <= data[high]:
            raise ValueError("Market prices must satisfy min <= median <= max")
        for key in ["inventory", "sales_7d", "sales_30d", "our_inventory", "our_sales_7d", "our_sales_30d"]:
            if key in data and (not math.isfinite(float(data[key])) or float(data[key]) < 0 or not float(data[key]).is_integer()):
                raise ValueError(key + " must be a nonnegative integer")
        for key in ["target_margin", "our_target_margin", "conversion_rate"]:
            if key in data and not 0 <= float(data[key]) <= 1:
                raise ValueError(key + " must be between zero and one")
        for key in ["base_usd_price", "usd_rate", "theoretical_toman_price"]:
            if key in data and (not math.isfinite(float(data[key])) or float(data[key]) <= 0):
                raise ValueError(key + " must be positive and finite")
        return self


class RecommendationResponse(BaseModel):
    """Key output fields from an explainable pricing recommendation."""

    product_id: str | None = None
    product_name: str | None = None
    recommended_price: float | int | None = None
    current_price: float | int | None = None
    action: str | None = None
    risk_level: str | None = None
    brand: str | None = None
    model: str | None = None
    category: str | None = None
    current_margin: float | None = None
    expected_margin: float | None = None
    margin_basis: str = "legacy_cost_markup"
    competitor_position: str | None = None
    theoretical_toman_price: float | None = None
    iran_market_premium_pct: float | None = None
    strategy_prices: dict[str, float] | None = None
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
