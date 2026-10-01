"""Consult, record an owner action, and measure its observed result."""
from datetime import date, timedelta
from typing import Literal
from decimal import Decimal
import csv
from io import StringIO
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from pydantic import Field
from src.api.v1 import get_service, require_writer
from src.application.advisor import consult, review_outcome
from src.application.advisor_examples import examples
from src.application.discovery_demo import discovery_demo
from src.application.service import PricingService
from src.domain.advisory import Consultation, OutcomeRecord, PlanRequest, StartRecord
from src.domain.models import Contract
from src.infrastructure.repository import ConflictError

router = APIRouter(prefix="/api/v1/advisor", tags=["Pricing consultant"])


@router.get("/examples")
def example_cases():
    return examples()


@router.get("/discovery-demo")
def discovery_walkthrough(service: PricingService = Depends(get_service)):
    return discovery_demo(service.repository)


@router.post("/consult")
def consultation(payload: Consultation, service: PricingService = Depends(get_service)):
    try:
        return consult(payload, service.repository)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc


@router.post("/plans", dependencies=[Depends(require_writer)])
def save(payload: PlanRequest, service: PricingService = Depends(get_service)):
    if payload.input.hypothetical_costs:
        raise HTTPException(422, "Confirm actual supplier costs before saving a plan; this is a what-if scenario")
    report = consultation(payload.input, service)
    if report["fingerprint"] != payload.fingerprint:
        raise HTTPException(409, "The consultation changed; review the latest advice before saving")
    try:
        return service.repository.save_advisory_plan(payload.request_id, report)
    except ConflictError as exc:
        raise HTTPException(409, str(exc)) from exc


@router.get("/plans")
def plans(service: PricingService = Depends(get_service)):
    return service.repository.advisory_plans()


def get_plan(service, plan_id):
    plan = service.repository.advisory_plan(plan_id)
    if plan is None:
        raise HTTPException(404, "Plan not found in this workspace")
    return plan


@router.get("/plans/{plan_id}/price-sheet")
def price_sheet(plan_id: str, service: PricingService = Depends(get_service)):
    """A review sheet, not a platform-specific bulk update or publication."""
    plan = get_plan(service, plan_id)
    r = plan["report"]
    c = Consultation.model_validate(r["input"])
    if not r["can_start_test"] or not c.linked_product_id or c.hypothetical_costs:
        raise HTTPException(422, "A price sheet needs a confirmed, linked product price test")
    total = Decimal(r["test_price_gross"])
    stream = StringIO(newline="")
    writer = csv.writer(stream)
    writer.writerow(["sku","currency","item_price_incl_vat","delivery_incl_vat","customer_total_incl_vat",
                     "review_after_days","minimum_sales","plan_id","input_fingerprint","published"])
    writer.writerow([c.linked_product_id,"EUR",str(total-c.customer_shipping_gross),str(c.customer_shipping_gross),
                     str(total),c.test_days,r["economics"]["minimum_units_with_volume_guardrail"],
                     plan["id"],r["fingerprint"],"false"])
    return Response("\ufeff"+stream.getvalue(),media_type="text/csv",
                    headers={"Content-Disposition":'attachment; filename="pricepilot-price-review.csv"'})


def transition(service, *args, **kwargs):
    try:
        return service.repository.transition_advisory(*args, **kwargs)
    except ConflictError as exc:
        raise HTTPException(409, str(exc)) from exc


@router.post("/plans/{plan_id}/start", dependencies=[Depends(require_writer)])
def start(plan_id: str, payload: StartRecord, service: PricingService = Depends(get_service)):
    plan = get_plan(service, plan_id)
    if not plan["report"]["can_start_test"]:
        raise HTTPException(422, "This plan is a business action, not a price test")
    c = plan["report"]["input"]
    if not date.fromisoformat(c["baseline_end"]) < payload.started_on <= date.today():
        raise HTTPException(422, "Start must follow the baseline period and cannot be in the future")
    if Decimal(plan["report"]["test_price_gross"]) != payload.actual_price_gross:
        raise HTTPException(422, "The applied price differs from the plan; create a new consultation")
    # Newly started trials cannot rely on expired inputs, even if saved weeks ago.
    if (payload.started_on - date.fromisoformat(c["costs_checked_on"])).days > 30 or (payload.started_on - date.fromisoformat(c["baseline_end"])).days > 45:
        raise HTTPException(422, "Inputs are too old for this start date; create an updated consultation")
    return transition(service, plan_id, "planned", "active", start=payload.model_dump(mode="json"))


@router.post("/plans/{plan_id}/outcome", dependencies=[Depends(require_writer)])
def outcome(plan_id: str, payload: OutcomeRecord, service: PricingService = Depends(get_service)):
    plan = get_plan(service, plan_id)
    if plan["status"] != "active":
        raise HTTPException(409, "Record the start of this trial before its outcome")
    try:
        result = review_outcome(plan, payload)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    # An early check-in must not close the trial or prevent the final observation.
    status = "active" if result["verdict"] == "early" else "completed"
    return transition(service, plan_id, "active", status, outcome=payload.model_dump(mode="json"), result=result)


class ActionNote(Contract):
    note: str = Field(min_length=5, max_length=1000)


@router.post("/plans/{plan_id}/complete-action", dependencies=[Depends(require_writer)])
def complete_action(plan_id: str, payload: ActionNote, service: PricingService = Depends(get_service)):
    plan = get_plan(service, plan_id)
    if plan["report"]["can_start_test"]:
        raise HTTPException(422, "Price tests need a dated start and measured outcome")
    return transition(service, plan_id, "planned", "completed", result={"title":"Action recorded", "note":payload.note, "causal_claim":False})


class DemoResult(Contract):
    situation: Literal["meets_threshold", "sales_fall", "other_changes"]


@router.post("/plans/{plan_id}/demo-result")
def demo_result(plan_id: str, payload: DemoResult, service: PricingService = Depends(get_service)):
    """Exercise the real outcome evaluator without inventing a recorded action."""
    plan = get_plan(service, plan_id)
    c = Consultation.model_validate(plan["report"]["input"])
    if c.origin != "demo" or not plan["report"]["can_start_test"]:
        raise HTTPException(422,"Simulated results are only available for fictional price-test cases")
    start_date = date.today() - timedelta(days=c.test_days-1)
    minimum = plan["report"]["economics"]["minimum_units_with_volume_guardrail"]
    units = minimum if payload.situation != "sales_fall" else max(0, minimum - max(3, minimum // 4))
    sample = OutcomeRecord(ended_on=date.today(),units=units,actual_unit_cost_net=c.unit_cost_net,
        actual_fee_rate=c.fee_rate,actual_fee_basis=c.fee_basis,actual_vat_rate=c.vat_rate,fully_available=True,price_unchanged=True,
        confounded=payload.situation=="other_changes",other_changes="Fictional trial outcome for walkthrough")
    simulated_plan = {**plan,"start":{"started_on":str(start_date),"actual_price_gross":plan["report"]["test_price_gross"]}}
    return {"origin":"simulated", "saved":False,"units":units,"days":c.test_days,
            "result":review_outcome(simulated_plan,sample)}
