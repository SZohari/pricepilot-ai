"""Versioned, UI-independent contracts. Money is decimal EUR, never binary float."""
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Annotated, Literal
from pydantic import BaseModel, ConfigDict, Field, HttpUrl, UrlConstraints, model_validator, field_validator

Money = Annotated[Decimal, Field(gt=0, max_digits=12, decimal_places=2)]
Cost = Annotated[Decimal, Field(ge=0, max_digits=12, decimal_places=2)]
Rate = Annotated[Decimal, Field(ge=0, lt=1, max_digits=6, decimal_places=4)]
Identifier = Annotated[str, Field(min_length=1, max_length=80, pattern=r"^[A-Za-z0-9][A-Za-z0-9_.-]*$")]


class Contract(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, str_strip_whitespace=True, allow_inf_nan=False)


def fee_on_net(rate, vat, basis="net"):
    """Equivalent fraction of net revenue, without rounding intermediate amounts."""
    return rate * (1 + vat) if basis == "gross" else rate


def validate_gtin(value):
    if not value.isascii() or not value.isdigit() or not value.strip("0") or len(value) not in (8, 12, 13, 14):
        raise ValueError("Use an exact 8, 12, 13 or 14-digit GTIN, not a model name")
    total = sum(int(n) * (3 if i % 2 == 0 else 1) for i, n in enumerate(reversed(value[:-1])))
    if (10 - total % 10) % 10 != int(value[-1]):
        raise ValueError("GTIN check digit is invalid")
    return value


class RetailDetails(Contract):
    """Owner-confirmed single-unit order costs; historical cost is kept separate."""
    variant: str = Field(min_length=2, max_length=160)
    gtin: str | None = None
    purchase_cost_net: Money
    inbound_cost_net: Cost = Decimal("0")
    shipping_cost_net: Cost = Decimal("0")
    packaging_cost_net: Cost = Decimal("0")
    returns_allowance_net: Cost = Decimal("0")
    other_cost_net: Cost = Decimal("0")
    fixed_fee_net: Cost = Decimal("0")
    customer_shipping_gross: Cost = Decimal("0")
    costs_checked_on: date
    sales_period_end: date
    baseline_representative: bool = False
    sales_7d_known: bool = False
    signal: Literal["price_objections", "low_visibility", "at_capacity", "unknown"] = "unknown"
    cost_scope_confirmed: bool = False

    @field_validator("gtin")
    @classmethod
    def exact_identity(cls, value):
        return validate_gtin(value) if value is not None else None

    @model_validator(mode="after")
    def observed_dates(self):
        if self.costs_checked_on > date.today() or self.sales_period_end >= date.today():
            raise ValueError("Costs cannot be future-dated and sales must end before today")
        return self

    @property
    def variable_total(self):
        return sum((self.inbound_cost_net, self.shipping_cost_net, self.packaging_cost_net,
                    self.returns_allowance_net, self.other_cost_net, self.fixed_fee_net), Decimal("0"))


class Strategy(str, Enum):
    TRUST = "trust_builder"
    BALANCED = "balanced"
    PROFIT = "profit_protection"
    PENETRATION = "market_penetration"
    PREMIUM = "premium_positioning"
    CLEARANCE = "clearance_cashflow"


class Product(Contract):
    product_id: Identifier
    name: str = Field(min_length=1, max_length=160)
    category: str = Field(default="Wearables", min_length=1, max_length=80)
    brand: str = Field(default="Independent", min_length=1, max_length=80)
    reference_url: Annotated[HttpUrl, UrlConstraints(allowed_schemes=["https"])] | None = None
    reference_checked_on: date | None = None
    data_origin: Literal["demo", "merchant", "unspecified"] = "unspecified"
    currency: Literal["EUR"] = "EUR"
    current_price_gross: Money
    replacement_cost_net: Money
    variable_cost_net: Cost = Decimal("0.00")
    vat_rate: Rate = Decimal("0.19")
    fee_rate: Rate = Decimal("0.00")
    fee_basis: Literal["net", "gross"] = "net"
    target_margin: Rate = Decimal("0.25")
    minimum_margin: Rate = Decimal("0.10")
    inventory: int = Field(ge=0, le=1_000_000)
    sales_7d: int = Field(default=0, ge=0, le=1_000_000)
    sales_30d: int = Field(default=0, ge=0, le=1_000_000)
    strategy: Strategy = Strategy.BALANCED
    retail: RetailDetails | None = None

    @model_validator(mode="after")
    def consistent_policy(self):
        if self.replacement_cost_net + self.variable_cost_net >= Decimal("10000000000"):
            raise ValueError("Combined per-order cost exceeds the supported EUR amount")
        if self.minimum_margin > self.target_margin:
            raise ValueError("minimum_margin must not exceed target_margin")
        if self.target_margin + fee_on_net(self.fee_rate, self.vat_rate, self.fee_basis) >= 1:
            raise ValueError("target_margin + fee_rate must be below one")
        if self.sales_7d > self.sales_30d:
            raise ValueError("sales_7d must not exceed sales_30d")
        if self.retail:
            if self.retail.variable_total != self.variable_cost_net:
                raise ValueError("The detailed order costs must equal variable_cost_net")
            if self.retail.customer_shipping_gross >= self.current_price_gross:
                raise ValueError("Delivery charges must be less than the total customer price")
        return self


class Observation(Contract):
    observation_id: Identifier
    product_id: Identifier
    seller: str = Field(min_length=1, max_length=120)
    price_gross: Money
    shipping_gross: Cost = Decimal("0.00")
    currency: Literal["EUR"] = "EUR"
    available: bool
    observed_on: date
    source: str = Field(min_length=1, max_length=160)
    data_origin: Literal["demo", "live", "unspecified"] = "unspecified"
    source_url: Annotated[HttpUrl, UrlConstraints(allowed_schemes=["https"])] | None = None
    observed_at: datetime | None = None


class Scenario(Contract):
    as_of: date
    evidence_mode: Literal["all", "demo", "live"] = "all"
    cost_change_pct: Decimal = Field(default=Decimal("0"), ge=-50, le=100)
    strategy: Strategy | None = None
    max_age_days: int = Field(default=14, ge=0, le=365)
    review_change_pct: Decimal = Field(default=Decimal("20"), gt=0, le=100)


class Quality(Contract):
    total_observations: int
    usable_sellers: int
    stale: int
    future: int
    unavailable: int
    superseded: int
    status: Literal["ready", "limited", "blocked"]
    warnings: list[str]


class Recommendation(Contract):
    schema_version: Literal["1.0"] = "1.0"
    policy_version: Literal["eur-retail-1"] = "eur-retail-1"
    product_id: str
    product_name: str
    currency: Literal["EUR"] = "EUR"
    as_of: date
    selected_strategy: Strategy
    current_price_gross: Decimal
    recommended_price_gross: Decimal | None
    floor_price_gross: Decimal
    market_median_gross: Decimal | None
    current_margin: Decimal
    expected_margin: Decimal | None
    replacement_cost_net: Decimal
    strategy_prices: dict[str, Decimal]
    action: Literal["increase_price", "decrease_price", "hold_price", "urgent_review"]
    risk_level: Literal["low", "medium", "high"]
    requires_review: bool
    quality: Quality
    reasons: list[str]


class CatalogEntry(Contract):
    product: Product
    version: int = Field(ge=1)


class Dataset(Contract):
    schema_version: Literal["1.0"] = "1.0"
    name: str = Field(min_length=1, max_length=160)
    as_of: date
    products: list[Product] = Field(min_length=1, max_length=10000)
    observations: list[Observation] = Field(max_length=100000)

    @model_validator(mode="after")
    def unique_and_linked(self):
        ids = [p.product_id for p in self.products]
        obs_ids = [o.observation_id for o in self.observations]
        if len(ids) != len(set(ids)) or len(obs_ids) != len(set(obs_ids)):
            raise ValueError("Product and observation IDs must be unique")
        unknown = {o.product_id for o in self.observations} - set(ids)
        if unknown:
            raise ValueError(f"Observations reference unknown products: {sorted(unknown)}")
        return self
