"""Bounded analytical endpoints; trained research models cannot publish prices."""
from threading import BoundedSemaphore
from typing import Literal
from fastapi import APIRouter, Depends, HTTPException
from pydantic import Field
from src.api.v1 import get_service, require_writer
from src.application.decision_brief import portfolio
from src.application.demand_demo import demo_benchmark, synthetic_history
from src.application.service import PricingService
from src.domain.demand import DemandHistory, evaluate
from src.domain.models import Contract, Identifier, Scenario
from src.infrastructure.repository import ConflictError

router = APIRouter(prefix="/api/v1/intelligence", tags=["Decision intelligence"])
training_slots = BoundedSemaphore(2)


@router.get("/demo-history")
def demo_history():
    return synthetic_history()


@router.get("/benchmark")
def benchmark(shock: bool = False):
    return demo_benchmark(shock)


@router.post("/evaluate", dependencies=[Depends(require_writer)])
def evaluate_history(history: DemandHistory):
    if not training_slots.acquire(blocking=False):
        raise HTTPException(429, "Two evaluations are already running; please try again shortly")
    try:
        return evaluate(history)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    finally:
        training_slots.release()


@router.post("/portfolio")
def portfolio_brief(scenario: Scenario, service: PricingService = Depends(get_service)):
    return portfolio(service, scenario)


class DecisionReview(Contract):
    product_id: Identifier
    fingerprint: str = Field(pattern=r"^[a-f0-9]{64}$")
    scenario: Scenario
    outcome: Literal["accepted", "rejected", "deferred"]
    reason: str = Field(min_length=5, max_length=1000)


@router.post("/reviews", dependencies=[Depends(require_writer)])
def review(payload: DecisionReview, service: PricingService = Depends(get_service)):
    item = next((b for b in portfolio(service, payload.scenario)["briefs"] if b["product_id"] == payload.product_id), None)
    if item is None:
        raise HTTPException(404, "Product no longer exists")
    if item["fingerprint"] != payload.fingerprint:
        raise HTTPException(409, "Inputs have changed; refresh the decision brief before recording a review")
    if payload.outcome == "accepted" and (item["checks"]["market_evidence"] == "blocked" or item["checks"]["inventory"] == "blocked"):
        raise HTTPException(422, "A price with no usable evidence or no inventory cannot be accepted")
    try:
        return service.repository.save_review(item, payload.outcome, payload.reason)
    except ConflictError as exc:
        raise HTTPException(409, str(exc)) from exc


@router.get("/reviews")
def reviews(service: PricingService = Depends(get_service)):
    return service.repository.reviews()
