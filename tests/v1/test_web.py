"""Web workspace integration tests: isolation, writes, conflicts and evidence."""
import pytest
from fastapi.testclient import TestClient
from src.web.app import create_app
from src.application.service import load_demo
from src.domain.models import Product

@pytest.fixture
def web(monkeypatch):
    monkeypatch.delenv("PRICEPILOT_DB_PATH", raising=False)
    with TestClient(create_app()) as client:
        yield client

def workspace(web):
    return {"X-Workspace-Token":web.get("/api/workspace").json()["csrf_token"]}

def test_static_and_security(web):
    assert web.get("/health").json()["service"] == "PricePilot Web"
    page=web.get("/")
    assert page.status_code == 200
    assert "/static/app.js" in page.text
    assert "script-src 'self'" in page.headers["Content-Security-Policy"]
    assert web.get("/static/app.css").status_code == 200
    assert web.get("/",headers={"host":"evil.example"}).status_code == 400

def test_catalog_provenance_and_data_integrity(web):
    info=web.get("/api/workspace").json()
    assert info["can_write"] and info["mode"]=="demo"
    entries=web.get("/api/v1/products").json()
    assert len(entries)==24
    assert len({e["product"]["brand"] for e in entries})==10
    assert all(e["product"]["reference_url"].startswith("https://") for e in entries)
    assert all(e["product"]["data_origin"]=="demo" for e in entries)
    batch=web.post("/api/v1/recommendations",json={"as_of":info["as_of"]}).json()
    assert batch["count"]==24
    assert any(r["quality"]["status"]=="blocked" for r in batch["recommendations"])

def test_demo_writes_require_matching_session_and_preserve_versions(web):
    headers=workspace(web)
    entry=web.get("/api/v1/products").json()[0]
    entry["product"]["name"]="Changed in this browser"
    body={"product":entry["product"],"expected_version":entry["version"]}
    url="/api/v1/products/"+entry["product"]["product_id"]
    assert web.put(url,json=body).status_code==403
    assert web.put(url,json=body,headers={"X-Workspace-Token":"wrong"}).status_code==403
    assert web.put(url,json=body,headers=headers).json()["version"]==2
    assert web.put(url,json=body,headers=headers).status_code==409
    assert web.get("/api/v1/products").json()[0]["product"]["name"]=="Changed in this browser"
    with TestClient(create_app()) as separate:
        # Same application session registry tested below; fresh app also starts clean.
        assert separate.get("/api/v1/products").json()[0]["product"]["name"]!="Changed in this browser"
    with TestClient(web.app) as other:
        other_headers=workspace(other)
        assert other_headers!=headers
        assert other.get("/api/v1/products").json()[0]["product"]["name"]!="Changed in this browser"
        assert other.put(url,json=body,headers=headers).status_code==403

def test_product_observation_export_and_scenario(web):
    headers=workspace(web)
    product=load_demo().products[0].model_dump(mode="json")
    product.update(product_id="CUSTOM-TEST",name="My product")
    assert web.put("/api/v1/products/CUSTOM-TEST",headers=headers,json={"product":product}).status_code==200
    offer=dict(observation_id="TEST-OBS",product_id="CUSTOM-TEST",seller="Demo seller",
               price_gross="449.00",available=True,observed_on="2026-09-26",source="Test simulation")
    assert web.post("/api/v1/observations",headers=headers,json=offer).status_code==201
    assert web.post("/api/v1/observations",headers=headers,json=offer).status_code==409
    dataset=web.get("/api/v1/datasets/export?as_of=2026-09-26").json()
    assert len(dataset["products"])==25 and len(dataset["observations"])==97
    result=web.post("/api/v1/recommendations",json={"as_of":"2026-09-26","cost_change_pct":30})
    assert result.status_code==200
    assert result.json()["count"]==25
    # A simulation must never mutate saved financial inputs.
    assert web.get("/api/v1/datasets/export?as_of=2026-09-26").json()==dataset

def test_invalid_save_and_atomic_import(web):
    headers=workspace(web)
    dataset=web.get("/api/v1/datasets/export?as_of=2026-09-26").json()
    assert web.post("/api/v1/datasets/import",headers=headers,json=dataset).status_code==409
    p=dataset["products"][0].copy();p["sales_7d"]=p["sales_30d"]+1
    assert web.put("/api/v1/products/"+p["product_id"],headers=headers,json={"product":p,"expected_version":1}).status_code==422
    assert web.get("/api/v1/datasets/export?as_of=2026-09-26").json()==dataset

@pytest.mark.parametrize("url",["javascript:alert(1)","http://example.com","data:text/html,hello"])
def test_non_https_product_references_rejected(url):
    p=load_demo().products[0].model_dump();p["reference_url"]=url
    with pytest.raises(ValueError): Product.model_validate(p)
