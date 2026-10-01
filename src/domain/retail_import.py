"""Explicit import choices: currency, decimal convention, costs and dated sales."""
from datetime import date
from decimal import Decimal
from typing import Literal
from pydantic import ConfigDict, Field, model_validator
from src.domain.models import Contract, Identifier, Money, Product
from src.domain.advisory import Comparable, KnowledgeNote, CustomerValue


class ImportDefaults(Contract):
    currency: Literal["EUR"] = "EUR"
    vat_percent: Decimal = Field(default=Decimal("19"),ge=0,lt=100,decimal_places=2)
    fee_percent: Decimal = Field(default=Decimal("2"),ge=0,lt=100,decimal_places=2)
    fee_basis: Literal["net", "gross"] = "gross"
    minimum_margin_percent: Decimal = Field(default=Decimal("10"),ge=0,lt=100,decimal_places=2)
    target_margin_percent: Decimal = Field(default=Decimal("25"),ge=0,lt=100,decimal_places=2)
    costs_checked_on: date
    sales_period_end: date
    baseline_representative: bool = False
    cost_scope_confirmed: bool = False

    @model_validator(mode="after")
    def policy(self):
        if self.minimum_margin_percent > self.target_margin_percent:
            raise ValueError("Minimum margin cannot exceed the target margin")
        if self.costs_checked_on > date.today() or self.sales_period_end >= date.today():
            raise ValueError("Costs cannot be future-dated; use a completed sales period")
        return self


class CSVInspection(Contract):
    # CSV is structured text: stripping a terminal tab would remove an empty cell.
    model_config = ConfigDict(str_strip_whitespace=False)
    csv_text: str = Field(min_length=1,max_length=500_000)
    delimiter: Literal[",", ";", "\t"] = ";"


class ImportPreview(CSVInspection):
    mapping: dict[str,str] = Field(max_length=40)
    decimal_style: Literal["dot", "comma"] = "comma"
    defaults: ImportDefaults


class ImportCommit(Contract):
    source: ImportPreview
    fingerprint: str = Field(pattern=r"^[a-f0-9]{64}$")
    confirmed: bool = False


class RetailAnalysis(Contract):
    product_id: Identifier
    candidate_price: Money | None = None
    cost_change_pct: Decimal = Field(default=Decimal(0),ge=-20,le=50)
    max_loss: Decimal = Field(default=Decimal(5),ge=0,le=30)
    test_days: int = Field(default=14,ge=7,le=30)
    signal: Literal["price_objections","low_visibility","at_capacity","unknown"] | None = None
    comparables: list[Comparable] = Field(default_factory=list,max_length=10)
    positioning: Literal["comparable","differentiated"] = "comparable"
    product_draft: Product | None = None
    expected_version: int | None = Field(default=None,ge=1)
    knowledge_notes: list[KnowledgeNote] = Field(default_factory=list,max_length=8)
    customer_value: CustomerValue | None = None
