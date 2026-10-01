from datetime import date
from decimal import Decimal
import pytest
from fastapi.testclient import TestClient
from src.api.main import app
from src.api.v1 import get_service
from src.application.service import PricingService, demo_service, load_demo
from src.domain.models import Dataset, Product
from src.infrastructure.repository import ConflictError, SQLiteRepository


def changed(product, **fields):
    return Product.model_validate(product.model_dump() | fields)


def test_import_conflict_rolls_back_every_insert_and_audit():
    repo = SQLiteRepository()
    data = load_demo()
    repo.import_dataset(data)
    before = repo.audit_log()
    fresh = changed(data.products[0], product_id="NEW")
    conflicting = Dataset(name="conflict", as_of=data.as_of,
                          products=[fresh, data.products[0]], observations=[])
    with pytest.raises(ConflictError):
        repo.import_dataset(conflicting)
    entries, _ = repo.snapshot()
    assert len(entries) == len(load_demo().products)
    assert "NEW" not in [e.product.product_id for e in entries]
    assert repo.audit_log() == before
    repo.close()


def test_concurrent_edit_is_rejected_and_data_survives_reopen(tmp_path):
    path = str(tmp_path / "store.sqlite3")
    a, b = SQLiteRepository(path), SQLiteRepository(path)
    p = load_demo().products[0]
    a.save_product(p)
    b.save_product(changed(p, inventory=99), expected_version=1)
    with pytest.raises(ConflictError):
        a.save_product(changed(p, inventory=1), expected_version=1)
    a.close()
    b.close()
    reopened = SQLiteRepository(path)
    entry = reopened.snapshot()[0][0]
    assert entry.version == 2
    assert entry.product.inventory == 99
    assert len(reopened.audit_log()) == 2
    reopened.close()


def test_demo_sessions_are_isolated():
    a, b = demo_service(), demo_service()
    entry = a.repository.snapshot()[0][0]
    a.repository.save_product(changed(entry.product, inventory=123), entry.version)
    assert b.repository.snapshot()[0][0].product.inventory != 123
    a.repository.close()
    b.repository.close()


def test_collected_offer_commit_rechecks_product_version_and_deduplicates_exact_cache_hits():
    repo=SQLiteRepository();demo=load_demo()
    p=demo.products[0];repo.save_product(p)
    offer=next(o for o in demo.observations if o.product_id==p.product_id)
    try:
        repo.save_product(changed(p,inventory=99),1)
        before=repo.audit_log()
        with pytest.raises(ConflictError,match='changed during collection'):
            repo.add_observation(offer,expected_product_version=1,allow_existing=True)
        assert repo.snapshot()[1]==[] and repo.audit_log()==before
        repo.add_observation(offer,expected_product_version=2,allow_existing=True)
        after=repo.audit_log()
        repo.add_observation(offer,expected_product_version=2,allow_existing=True)
        assert repo.audit_log()==after and len(repo.snapshot()[1])==1
        with pytest.raises(ConflictError):
            repo.add_observation(offer.model_copy(update={'price_gross':offer.price_gross+1}),expected_product_version=2,allow_existing=True)
    finally:
        repo.close()


@pytest.fixture
def client(monkeypatch):
    service = demo_service()
    app.dependency_overrides[get_service] = lambda: service
    monkeypatch.delenv("PRICEPILOT_API_KEY", raising=False)
    with TestClient(app, raise_server_exceptions=False) as client:
        yield client
    app.dependency_overrides.clear()
    service.repository.close()


def test_api_returns_full_decimal_contract(client):
    response = client.post("/api/v1/recommendations", json={"as_of": "2026-09-26"})
    assert response.status_code == 200
    body = response.json()
    assert body["count"] == len(load_demo().products)
    first = body["recommendations"][0]
    assert first["currency"] == "EUR"
    assert isinstance(first["floor_price_gross"], str)
    assert {"quality", "reasons", "strategy_prices", "expected_margin", "policy_version"} <= first.keys()


@pytest.mark.parametrize("body", [{}, {"as_of": "invalid"}, {"as_of": "2026-09-26", "strategy": "fake"},
                                  {"as_of": "2026-09-26", "cost_change_pct": 101}])
def test_invalid_scenarios_are_client_errors(client, body):
    assert client.post("/api/v1/recommendations", json=body).status_code == 422


def test_api_mutations_disabled_until_configured(client):
    p = load_demo().products[0]
    response = client.put(f"/api/v1/products/{p.product_id}",
                          json={"product": p.model_dump(mode="json"), "expected_version": 1})
    assert response.status_code == 403
    assert client.post("/build-dataset").status_code == 403


def test_api_authorized_edit_and_stale_version(client, monkeypatch):
    monkeypatch.setenv("PRICEPILOT_API_KEY", "test-key")
    p = load_demo().products[0]
    body = {"product": changed(p, inventory=45).model_dump(mode="json"), "expected_version": 1}
    endpoint = f"/api/v1/products/{p.product_id}"
    assert client.put(endpoint, json=body, headers={"X-API-Key": "wrong"}).status_code == 401
    response = client.put(endpoint, json=body, headers={"X-API-Key": "test-key"})
    assert response.status_code == 200
    assert response.json()["version"] == 2
    assert client.put(endpoint, json=body, headers={"X-API-Key": "test-key"}).status_code == 409


def test_api_export_round_trips_validated_dataset(client):
    result = client.get("/api/v1/datasets/export?as_of=2026-09-26")
    dataset = Dataset.model_validate(result.json())
    repo = SQLiteRepository()
    repo.import_dataset(dataset)
    assert len(repo.snapshot()[0]) == len(load_demo().products)
    repo.close()


def test_legacy_api_rejects_empty_negative_and_keeps_output_fields(client):
    assert client.post("/recommend-price", json={}).status_code == 422
    assert client.post("/recommend-price", json={"our_current_price": -1}).status_code == 422
    from src.api.schemas import RECOMMENDATION_EXAMPLE
    response = client.post("/recommend-price", json=RECOMMENDATION_EXAMPLE)
    assert response.status_code == 200
    assert {"current_margin", "expected_margin", "strategy_prices", "theoretical_toman_price"} <= response.json().keys()
