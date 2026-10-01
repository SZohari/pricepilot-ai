"""Business-level contracts: diagnosis, guardrails, evidence and action → outcome."""
from datetime import date, timedelta
from decimal import Decimal
import json
import sqlite3
from uuid import uuid4
import pytest
from fastapi.testclient import TestClient
from src.application.advisor import consult
from src.application.advisor_examples import examples
from src.application.service import demo_service
from src.domain.advisory import Consultation
from src.domain.models import Observation
from src.infrastructure.repository import ConflictError, SQLiteRepository
from src.web.app import create_app


def case(**changes):
    values = examples()[0]["input"].copy()
    values.update(changes)
    return Consultation.model_validate(values)


def advice(**changes):
    return consult(case(**changes), demo_service().repository)


def test_examples_have_distinct_business_diagnoses():
    results = [consult(Consultation.model_validate(e["input"]), demo_service().repository) for e in examples()]
    assert [r["action"] for r in results] == ["price_test", "investigate", "price_test"]
    assert "visibility" in results[1]["title"]
    assert all(r["forecast"] is False for r in results)


def test_cost_recovery_preserves_volume_as_well_as_contribution():
    r = advice()
    assert r["test_price_gross"] == "29.75"
    e = r["economics"]
    assert e["minimum_units_with_volume_guardrail"] == 40
    assert e["minimum_units_with_volume_guardrail"] > e["units_needed_for_contribution"]
    stricter = advice(max_volume_loss_pct="0")
    assert stricter["economics"]["minimum_units_with_volume_guardrail"] == 42


def test_discount_requires_extra_sales_and_capacity():
    r = advice(current_price_gross="40.00", unit_cost_net="20.00", proposed_price_gross="38.00")
    assert r["can_start_test"]
    assert r["economics"]["minimum_units_with_volume_guardrail"] > 42
    r = advice(current_price_gross="40.00", unit_cost_net="20.00", proposed_price_gross="38.00", test_capacity=42)
    assert r["action"] == "capacity" and not r["can_start_test"]


@pytest.mark.parametrize("changes,action", [
    ({"proposed_price_gross":"27.00"}, "unsafe_price"),
    ({"proposed_price_gross":"35.00"}, "rework_offer"),
    ({"unit_cost_net":"28.00"}, "rework_offer"),
    ({"test_capacity":0}, "capacity"),
    ({"baseline_units":0}, "learn"),
    ({"baseline_units":0,"baseline_representative":False}, "learn"),
    ({"baseline_representative":False}, "refresh_inputs"),
    ({"costs_checked_on":str(date.today()-timedelta(days=31))}, "refresh_inputs"),
    ({"baseline_end":str(date.today()-timedelta(days=46))}, "refresh_inputs"),
])
def test_does_not_force_every_problem_into_a_price_change(changes, action):
    r = advice(**changes)
    assert r["action"] == action
    assert r["test_price_gross"] is None and not r["can_start_test"]


def test_loss_recovery_with_zero_margin_has_a_volume_threshold():
    r = advice(current_price_gross="29.00", unit_cost_net="24.00", minimum_margin="0", proposed_price_gross="30.00")
    assert r["can_start_test"]
    assert r["economics"]["minimum_units_with_volume_guardrail"] == 40


def comparables():
    return [dict(seller=name, total_price_gross="37.00", observed_on=str(date.today()),
                 url="https://example.com/"+name, same_offer=True) for name in ("one", "two")]


def test_market_response_needs_a_matching_offer_and_customer_signal():
    values = dict(concern="slow_sales", signal="price_objections", current_price_gross="40.00", unit_cost_net="20.00", comparables=comparables())
    assert advice(**values)["can_start_test"]
    assert not advice(**{**values, "signal":"unknown"})["can_start_test"]
    assert not advice(**{**values, "positioning":"differentiated"})["can_start_test"]
    values["comparables"][0]["same_offer"] = False
    r = advice(**values)
    assert not r["can_start_test"] and r["excluded_evidence"] == 1


def test_stale_future_and_unavailable_comparables_cannot_drive_discount():
    for change in ({"observed_on":str(date.today()-timedelta(days=15))},
                   {"observed_on":str(date.today()+timedelta(days=1))}, {"available":False}):
        items = comparables()
        items[0].update(change)
        assert not advice(concern="slow_sales", signal="price_objections", current_price_gross="40.00", unit_cost_net="20.00", comparables=items)["market_usable"]


def test_real_case_cannot_launder_simulated_catalog_evidence():
    product_id = demo_service().repository.snapshot()[0][0].product.product_id
    with pytest.raises(ValueError, match="simulated"):
        advice(origin="merchant", linked_product_id=product_id)


@pytest.fixture
def web(monkeypatch):
    monkeypatch.delenv("PRICEPILOT_DB_PATH", raising=False)
    monkeypatch.delenv("PRICEPILOT_PUBLIC_DEMO", raising=False)
    with TestClient(create_app()) as client:
        client.headers["X-Workspace-Token"] = client.get("/api/workspace").json()["csrf_token"]
        yield client


def saved(web, input=None):
    c = input or case().model_dump(mode="json")
    r = web.post("/api/v1/advisor/consult", json=c)
    assert r.status_code == 200, r.text
    body = {"request_id":str(uuid4()), "input":c, "fingerprint":r.json()["fingerprint"]}
    p = web.post("/api/v1/advisor/plans", json=body)
    assert p.status_code == 200, p.text
    return p.json(), body


def start(web, plan):
    return web.post(f"/api/v1/advisor/plans/{plan['id']}/start", json=dict(
        started_on=str(date.today()-timedelta(days=13)), actual_price_gross=plan["report"]["test_price_gross"],
        note="Applied manually in the shop"))


def outcome(**changes):
    return {"ended_on":str(date.today()), "units":41, "actual_unit_cost_net":"22.00",
            "actual_fee_rate":"0.02", "actual_vat_rate":"0.19", "fully_available":True,
            "price_unchanged":True,"other_changes":"No other known changes", "confounded":False, **changes}


def test_complete_action_loop_is_server_persisted_and_does_not_publish(web):
    plan, _ = saved(web)
    assert not plan["published"] and plan["status"] == "planned"
    started = start(web, plan)
    assert started.status_code == 200 and started.json()["status"] == "active"
    url = f"/api/v1/advisor/plans/{plan['id']}/outcome"
    result = web.post(url, json=outcome())
    assert result.status_code == 200, result.text
    assert result.json()["result"]["verdict"] == "promising"
    assert result.json()["result"]["causal_claim"] is False
    assert web.post(url, json=outcome()).status_code == 409
    assert web.get("/api/v1/advisor/plans").json()[0] == result.json()


@pytest.mark.parametrize("changes,verdict", [
    ({"units":30}, "review"),
    ({"actual_unit_cost_net":"27.00"}, "review"),
    ({"confounded":True}, "inconclusive"),
    ({"fully_available":False}, "inconclusive"),
    ({"price_unchanged":False}, "inconclusive"),
    ({"ended_on":str(date.today()-timedelta(days=5))}, "early"),
    ({"ended_on":str(date.today()-timedelta(days=5)),"actual_unit_cost_net":"27.00"}, "review"),
])
def test_outcome_uses_actual_costs_volume_period_and_confounders(web, changes, verdict):
    p, _ = saved(web)
    assert start(web, p).status_code == 200
    r = web.post(f"/api/v1/advisor/plans/{p['id']}/outcome", json=outcome(**changes))
    assert r.status_code == 200, r.text
    assert r.json()["result"]["verdict"] == verdict
    if verdict == "early":
        assert r.json()["status"] == "active"
        final = web.post(f"/api/v1/advisor/plans/{p['id']}/outcome", json=outcome())
        assert final.status_code == 200 and final.json()["status"] == "completed"


def test_start_cannot_publish_different_price_or_backdate_into_baseline(web):
    p, _ = saved(web)
    url = f"/api/v1/advisor/plans/{p['id']}/start"
    body = dict(started_on=str(date.today()), actual_price_gross="29.75", note="Applied in shop")
    for changes in ({"actual_price_gross":"20.00"}, {"started_on":p["report"]["input"]["baseline_end"]},
                    {"started_on":str(date.today()+timedelta(days=1))}):
        assert web.post(url, json={**body, **changes}).status_code == 422
    assert web.post(url, json=body).status_code == 200
    assert web.post(url, json=body).status_code == 409


def test_plans_are_idempotent_csrf_protected_and_isolated(web):
    p, body = saved(web)
    assert web.post("/api/v1/advisor/plans", json=body).json()["id"] == p["id"]
    changed = json.loads(json.dumps(body))
    changed["input"]["unit_cost_net"] = "23.00"
    assert web.post("/api/v1/advisor/plans",json=changed).status_code == 409
    with TestClient(web.app) as other:
        assert other.get("/api/v1/advisor/plans").json() == []
        assert other.post("/api/v1/advisor/plans",json=body).status_code == 403
        other.headers["X-Workspace-Token"] = other.get("/api/workspace").json()["csrf_token"]
        assert other.post(f"/api/v1/advisor/plans/{p['id']}/outcome",json=outcome()).status_code == 404


def test_non_price_action_has_its_own_follow_up(web):
    p, _ = saved(web, examples()[1]["input"])
    assert start(web, p).status_code == 422  # null price fails contract, still no transition
    r = web.post(f"/api/v1/advisor/plans/{p['id']}/complete-action", json={"note":"Reviewed traffic; only 20 visitors this week"})
    assert r.status_code == 200 and r.json()["status"] == "completed"


def test_demo_result_exercises_evaluator_without_recording_fake_outcomes(web):
    p, _ = saved(web)
    path = f"/api/v1/advisor/plans/{p['id']}/demo-result"
    for situation, verdict in (("meets_threshold","promising"),("sales_fall","review"),("other_changes","inconclusive")):
        r = web.post(path,json={"situation":situation})
        assert r.status_code == 200 and r.json()["result"]["verdict"] == verdict
        assert r.json()["saved"] is False and r.json()["origin"] == "simulated"
    assert web.get("/api/v1/advisor/plans").json()[0]["status"] == "planned"
    merchant, _ = saved(web,case(origin="merchant").model_dump(mode="json"))
    assert web.post(f"/api/v1/advisor/plans/{merchant['id']}/demo-result",json={"situation":"meets_threshold"}).status_code == 422


def test_save_checks_snapshot_atomically_and_reopens_after_migration(tmp_path):
    path = str(tmp_path / "workspace.sqlite3")
    db = sqlite3.connect(path)
    db.execute("PRAGMA user_version=2")
    db.close()
    repo = SQLiteRepository(path)
    dataset = demo_service().export_dataset(date.today())
    repo.import_dataset(dataset)
    product_id = dataset.products[0].product_id
    c = case(linked_product_id=product_id)
    r = consult(c, repo)
    obs = Observation(observation_id="NEW",product_id=product_id,seller="New evidence",price_gross="29.00",
                      available=True,observed_on=date.today(),source="Simulated",data_origin="demo")
    repo.add_observation(obs)
    with pytest.raises(ConflictError, match="Evidence changed"):
        repo.save_advisory_plan(str(uuid4()), r)
    r = consult(c, repo)
    p = repo.save_advisory_plan(str(uuid4()), r)
    repo.close()
    reopened = SQLiteRepository(path)
    assert reopened.advisory_plan(p["id"]) == p
    reopened.close()
