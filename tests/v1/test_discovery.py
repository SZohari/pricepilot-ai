"""A philosophy must change behavior, not just copy: executable design claims."""
from datetime import date, timedelta
from decimal import Decimal
import pytest
from fastapi.testclient import TestClient
from src.application.advisor import consult, per_unit
from src.application.advisor_examples import examples
from src.application.discovery_demo import discovery_demo
from src.application.service import demo_service
from src.domain.advisory import Consultation, CustomerValue
from src.web.app import create_app


def value(**changes):
    return dict(customer_group="Time-constrained applicants",reason_to_choose="Same-day delivery instead of next week",
                basis="hypothesis",checked_on=str(date.today()),**changes)


def test_local_knowledge_changes_decision_with_identical_financial_facts():
    story=discovery_demo(demo_service().repository)
    reports=[s["report"] for s in story["steps"]]
    assert [r["action"] for r in reports]==["price_test","validate_value","price_test"]
    assert reports[0]["test_price_gross"]=="113.05"
    assert reports[1]["test_price_gross"] is None
    assert reports[2]["test_price_gross"]=="122.57"
    for key in ("current_price_gross","unit_cost_net","baseline_units","baseline_days","test_capacity","vat_rate","fee_rate"):
        assert len({str(r["input"][key]) for r in reports})==1
    assert {r["market_median_gross"] for r in reports}=={"100.00"}
    assert reports[0]["market_usable"] and not reports[1]["market_usable"]
    assert reports[1]["discovery"]["local_knowledge"]["independently_verified"] is False


def test_value_claim_never_manufactures_a_price_premium_or_demand_forecast():
    c=Consultation.model_validate(discovery_demo(demo_service().repository)["steps"][1]["report"]["input"])
    repo=demo_service().repository
    for basis,note in (("hypothesis",""),("owner_observed","Five enquiries mentioned urgent delivery")):
        changed=c.model_copy(update={"customer_value":CustomerValue.model_validate({**value(),"basis":basis,"evidence_note":note})})
        r=consult(changed,repo)
        assert r["action"]=="validate_value" and not r["can_start_test"]
        assert r["test_price_gross"] is None and r["forecast"] is False
        assert r["discovery"]["confidence_score"] is None
        assert r["discovery"]["causal_identification"] is False


def test_local_claim_cannot_override_financial_or_evidence_blockers():
    c=Consultation.model_validate(discovery_demo(demo_service().repository)["steps"][1]["report"]["input"])
    for changes,action in (({"unit_cost_net":Decimal("120.00")},"rework_offer"),
                           ({"test_capacity":0},"capacity"),
                           ({"baseline_representative":False},"refresh_inputs"),
                           ({"proposed_price_gross":Decimal("50.00")},"unsafe_price")):
        r=consult(c.model_copy(update=changes),demo_service().repository)
        assert r["action"]==action


def test_a_story_does_not_overrule_the_stated_low_visibility_signal():
    c=examples()[1]["input"] | {"customer_value":value()}
    r=consult(Consultation.model_validate(c),demo_service().repository)
    assert r["action"]=="investigate" and "visibility" in r["title"]


def test_stale_owner_observation_is_visible_and_needs_refresh():
    c=discovery_demo(demo_service().repository)["steps"][1]["report"]["input"]
    c["customer_value"]["checked_on"]=str(date.today()-timedelta(days=31))
    r=consult(Consultation.model_validate(c),demo_service().repository)
    assert r["discovery"]["local_knowledge"]["stale"]
    assert "Refresh" in r["next_step"]


def test_observation_requires_a_basis_and_cannot_be_future_dated():
    with pytest.raises(ValueError): CustomerValue.model_validate({**value(),"basis":"owner_observed"})
    with pytest.raises(ValueError): CustomerValue.model_validate({**value(),"checked_on":str(date.today()+timedelta(days=1))})


def test_boundary_is_accounting_and_each_integer_threshold_is_minimal():
    repo=demo_service().repository
    r=discovery_demo(repo)["steps"][2]["report"]
    c=Consultation.model_validate(r["input"])
    baseline=Decimal(c.baseline_units)/c.baseline_days*c.test_days
    base_total=baseline*per_unit(c.current_price_gross,c)
    volume_min=baseline*(1-c.max_volume_loss_pct/100)
    assert r["viability"]["kind"]=="required_outcomes_not_demand"
    for point in r["viability"]["points"]:
        price=Decimal(point["price_gross"])
        unit=per_unit(price,c)
        n=point["required_units"]
        assert n*unit>=base_total and n>=volume_min
        assert (n-1)*unit<base_total or n-1<volume_min
        if point["feasible"]:
            assert n<=c.test_capacity
            assert price>=Decimal(r["economics"]["minimum_price_gross"])


def test_selected_automatically_derived_price_is_on_the_boundary():
    c=Consultation.model_validate(examples()[0]["input"])
    r=consult(c,demo_service().repository)
    point=next(p for p in r["viability"]["points"] if p["price_gross"]==r["test_price_gross"])
    assert point["required_units"]==r["economics"]["minimum_units_with_volume_guardrail"]


def test_boundary_marks_capacity_and_margin_violations_without_hiding_them():
    c=Consultation.model_validate(examples()[0]["input"]|{"test_capacity":1})
    r=consult(c,demo_service().repository)
    assert not any(p["feasible"] for p in r["viability"]["points"])
    assert any("Below your margin floor" in p["reasons"] for p in r["viability"]["points"])
    assert any("More sales required than capacity allows" in p["reasons"] for p in r["viability"]["points"])


def test_boundary_not_available_for_unconfirmed_or_zero_baselines():
    for changes in ({"baseline_units":0},{"baseline_representative":False}):
        r=consult(Consultation.model_validate(examples()[0]["input"]|changes),demo_service().repository)
        assert r["viability"]["available"] is False


def test_discovery_api_and_fingerprints_include_local_knowledge(monkeypatch):
    monkeypatch.delenv("PRICEPILOT_DB_PATH",raising=False)
    monkeypatch.delenv("PRICEPILOT_PUBLIC_DEMO",raising=False)
    with TestClient(create_app()) as web:
        token=web.get("/api/workspace").json()["csrf_token"]
        r=web.get("/api/v1/advisor/discovery-demo")
        assert r.status_code==200
        steps=r.json()["steps"]
        assert len({s["report"]["fingerprint"] for s in steps})==3
        c=steps[1]["report"]["input"]
        c["customer_value"]["reason_to_choose"]="A new claim requiring a new consultation"
        payload={"request_id":"aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa","input":c,"fingerprint":steps[1]["report"]["fingerprint"]}
        assert web.post("/api/v1/advisor/plans",json=payload,headers={"X-Workspace-Token":token}).status_code==409
