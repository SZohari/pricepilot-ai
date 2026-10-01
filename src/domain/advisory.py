"""Dated business inputs and experiment records, independent of a retail catalog."""
from datetime import date
from decimal import Decimal
from typing import Annotated, Literal
from pydantic import Field, HttpUrl, UrlConstraints, model_validator
from src.domain.models import Contract, Cost, Identifier, Money, Rate, fee_on_net


class Comparable(Contract):
    seller: str = Field(min_length=1, max_length=120)
    total_price_gross: Money
    observed_on: date
    url: Annotated[HttpUrl, UrlConstraints(allowed_schemes=["https"])]
    same_offer: bool = False
    available: bool = True


class CustomerValue(Contract):
    """Local knowledge is an attributed claim, never an inferred willingness to pay."""
    customer_group: str = Field(min_length=2, max_length=120)
    reason_to_choose: str = Field(min_length=5, max_length=300)
    basis: Literal["hypothesis", "owner_observed"] = "hypothesis"
    evidence_note: str = Field(default="", max_length=500)
    checked_on: date

    @model_validator(mode="after")
    def dated_attributed_claim(self):
        if self.checked_on > date.today():
            raise ValueError("A customer-value claim cannot be future-dated")
        if self.basis == "owner_observed" and len(self.evidence_note) < 10:
            raise ValueError("Describe the observation supporting this claim, without personal customer details")
        return self


class KnowledgeNote(Contract):
    """A decision-relevant unknown or owner observation, never a scored latent trait."""
    topic: Literal['price','visibility','trust','product_fit','delivery','repeat_customers','other']
    statement: str = Field(min_length=5,max_length=500)
    basis: Literal['question','hypothesis','observed'] = 'question'
    evidence_note: str = Field(default='',max_length=500)
    checked_on: date
    resolve_first: bool = True

    @model_validator(mode='after')
    def attributable(self):
        if self.checked_on > date.today():
            raise ValueError('A business observation cannot be future-dated')
        if self.basis == 'observed' and len(self.evidence_note) < 10:
            raise ValueError('Describe the observation behind this claim, without customer names or contact details')
        return self


class Consultation(Contract):
    business_name: str = Field(min_length=1, max_length=120)
    offer_name: str = Field(min_length=1, max_length=160)
    kind: Literal["goods", "service"] = "goods"
    unit: str = Field(default="item", min_length=1, max_length=40)
    origin: Literal["merchant", "demo"] = "merchant"
    concern: Literal["margin", "slow_sales", "capacity", "test_price"]
    signal: Literal["price_objections", "low_visibility", "at_capacity", "unknown"] = "unknown"
    positioning: Literal["comparable", "differentiated"] = "comparable"
    current_price_gross: Money
    unit_cost_net: Cost
    vat_rate: Rate = Decimal("0.19")
    fee_rate: Rate = Decimal("0")
    fee_basis: Literal["net", "gross"] = "net"
    minimum_margin: Rate = Decimal("0.10")
    costs_checked_on: date
    cost_scope_confirmed: bool = True
    customer_shipping_gross: Cost = Decimal("0")
    hypothetical_costs: bool = False
    demo_as_of: date | None = None
    baseline_end: date
    baseline_days: int = Field(default=30, ge=7, le=90)
    baseline_units: int = Field(ge=0, le=1_000_000)
    baseline_representative: bool = False
    # Additional stock or service slots available during the proposed test, not past stock.
    test_capacity: int = Field(ge=0, le=1_000_000)
    test_days: int = Field(default=14, ge=7, le=30)
    max_volume_loss_pct: Decimal = Field(default=Decimal("5"), ge=0, le=30)
    proposed_price_gross: Money | None = None
    linked_product_id: Identifier | None = None
    comparables: list[Comparable] = Field(default_factory=list, max_length=10)
    context_note: str = Field(default="", max_length=1000)
    customer_value: CustomerValue | None = None
    knowledge_notes: list[KnowledgeNote] = Field(default_factory=list,max_length=8)

    @model_validator(mode="after")
    def consistent(self):
        if self.demo_as_of and (self.origin != "demo" or self.demo_as_of > date.today()):
            raise ValueError("A fixed demo date is only allowed for a labelled, non-future demo")
        if self.customer_shipping_gross >= self.current_price_gross:
            raise ValueError("Delivery must be less than the total customer price")
        if self.minimum_margin + fee_on_net(self.fee_rate, self.vat_rate, self.fee_basis) >= 1:
            raise ValueError("Minimum margin and sales fee must sum to less than 100%")
        if self.costs_checked_on > date.today() or self.baseline_end > date.today():
            raise ValueError("Business inputs must describe an observed, non-future period")
        if len({c.seller.casefold() for c in self.comparables}) != len(self.comparables):
            raise ValueError("Use one current comparable per seller")
        if self.demo_as_of and any(n.checked_on > self.demo_as_of for n in self.knowledge_notes):
            raise ValueError('For the replay, date the illustrative note no later than the demo snapshot')
        return self


class PlanRequest(Contract):
    request_id: str = Field(pattern=r"^[a-f0-9-]{36}$")
    input: Consultation
    fingerprint: str = Field(pattern=r"^[a-f0-9]{64}$")


class StartRecord(Contract):
    started_on: date
    actual_price_gross: Money
    note: str = Field(min_length=3, max_length=1000)


class OutcomeRecord(Contract):
    ended_on: date
    units: int = Field(ge=0, le=1_000_000)
    actual_unit_cost_net: Cost
    actual_fee_rate: Rate
    actual_fee_basis: Literal["net", "gross"] = "net"
    actual_vat_rate: Rate
    fully_available: bool
    price_unchanged: bool
    other_changes: str = Field(min_length=3, max_length=1000)
    confounded: bool = True
    # Aggregate period sales only; no personal customer information is needed.
