from datetime import date, datetime, timezone
import json
from decimal import Decimal
import pytest
from fastapi.testclient import TestClient
from src.application.service import load_demo, demo_service
from src.domain.models import Scenario
from src.infrastructure.price_sources import Source, parse_offer, CollectionError, Collector, public_addresses, load_sources
from src.web.app import create_app

GTIN="4006381333931"  # Valid test identifier, not asserted to be a real watch SKU.

def source(**changes):
    return Source.model_validate(dict(source_id="source-a",product_id="DE-WEAR-001",seller="Fixture retailer",
        url="https://retailer.example/product",expected_gtin=GTIN,shipping_gross="4.99",
        shipping_note="Test fixture delivery")|changes)

def page(**offer_changes):
    offer={"@type":"Offer","price":"349.00","priceCurrency":"EUR","availability":"https://schema.org/InStock",
           "itemCondition":"https://schema.org/NewCondition"}|offer_changes
    return '<script type="application/ld+json">'+json.dumps({"@context":"https://schema.org","@type":"Product","gtin13":GTIN,"offers":offer})+'</script>'

def events(response):
    return [json.loads(block[6:]) for block in response.text.split("\n\n") if block.startswith("data: ")]

def test_verified_offer_preserves_identity_provenance_and_shipping():
    stamp=datetime(2026,9,26,12,0,tzinfo=timezone.utc)
    offer=parse_offer(page(),source(),stamp)
    assert offer.data_origin=="live" and offer.observed_at==stamp
    assert offer.price_gross+offer.shipping_gross==Decimal("353.99")
    assert str(offer.source_url)=="https://retailer.example/product"
    assert offer.available
    assert not parse_offer(page(availability="https://schema.org/OutOfStock"),source()).available

@pytest.mark.parametrize("changes",[
    {"priceCurrency":"USD"},{"price":"NaN"},{"price":"10.001"},{"price":0},
    {"@type":"AggregateOffer","lowPrice":"100"},{"itemCondition":"UsedCondition"},
    {"itemCondition":""},{"availability":""},{"availability":"PreOrder"},{"priceValidUntil":"2020-01-01"},
])
def test_uncertain_or_incomparable_offers_are_rejected(changes):
    with pytest.raises(CollectionError): parse_offer(page(**changes),source())

def test_exact_gtin_and_unique_offer_required():
    with pytest.raises(CollectionError): parse_offer(page().replace(GTIN,"12345678"),source())
    with pytest.raises(CollectionError): parse_offer(page()+page(),source())

@pytest.mark.parametrize("gtin",["0000000000000","4006381333932","Galaxy Watch","۱۲۳۴۵۶۷۸"])
def test_invalid_gtin_config_fails(gtin):
    with pytest.raises(ValueError): source(expected_gtin=gtin)

@pytest.mark.parametrize("url",["http://retailer.example/x","https://user:pass@retailer.example/x","https://retailer.example:8080/x"])
def test_unsafe_config_fails(url):
    with pytest.raises(ValueError): source(url=url)

@pytest.mark.parametrize("address",["127.0.0.1","10.0.0.1","169.254.169.254","::1","192.168.1.1"])
def test_private_destinations_rejected(monkeypatch,address):
    monkeypatch.setattr("socket.getaddrinfo",lambda *a,**k:[(None,None,None,None,(address,443))])
    with pytest.raises(CollectionError): public_addresses("retailer.example")

def test_robot_policy_and_shared_cache(monkeypatch):
    monkeypatch.setattr("src.infrastructure.price_sources.time.sleep",lambda _:None)
    calls=[]
    def fetch(url):
        calls.append(url)
        return "User-agent: *\nDisallow: /" if url.endswith("robots.txt") else page()
    collector=Collector([source()],fetch)
    assert collector.collect(source())["status"]=="failed"
    assert collector.collect(source())["cached"]
    assert len(calls)==1  # No product fetch when robots denies collection.
    collector=Collector([source()],lambda url:"User-agent: *\nAllow: /" if url.endswith("robots.txt") else page())
    first=collector.collect(source());second=collector.collect(source())
    assert first["status"]=="collected" and second["cached"]
    assert first["observation"]["observation_id"]==second["observation"]["observation_id"]

def test_config_cannot_mix_variants_or_duplicate_sellers(tmp_path):
    items=[source().model_dump(mode="json"),source(source_id="other").model_dump(mode="json")]
    p=tmp_path/"sources.json";p.write_text(json.dumps(items))
    with pytest.raises(ValueError): load_sources(p)

def test_replay_stream_changes_decisions_without_applying_prices(monkeypatch):
    monkeypatch.delenv("PRICEPILOT_DB_PATH",raising=False)
    monkeypatch.delenv("PRICEPILOT_SOURCES_PATH",raising=False)
    with TestClient(create_app()) as web:
        workspace=web.get("/api/workspace").json();headers={"X-Workspace-Token":workspace["csrf_token"]}
        original=web.get("/api/v1/products").json()
        scenario={"as_of":workspace["as_of"],"evidence_mode":"demo"}
        before=web.post("/api/v1/recommendations",json=scenario).json()["recommendations"]
        response=web.post("/api/demo/replay",headers=headers)
        assert response.headers["content-type"].startswith("text/event-stream")
        received=events(response)
        assert received[-1]["type"]=="complete"
        assert sum(e["type"]=="offer" for e in received)==12
        after=web.post("/api/v1/recommendations",json=scenario).json()["recommendations"]
        assert before[4]["recommended_price_gross"] is None
        assert after[4]["recommended_price_gross"] is not None
        assert before[0]["recommended_price_gross"]!=after[0]["recommended_price_gross"]
        assert web.get("/api/v1/products").json()==original
        assert web.post("/api/demo/reset",headers=headers).status_code==200
        assert len(web.get("/api/evidence").json())==96
        assert web.post("/api/sources/collect",headers=headers).status_code==409

def test_live_stream_deduplicates_cached_offers_and_never_uses_demo(monkeypatch):
    monkeypatch.delenv("PRICEPILOT_DB_PATH",raising=False)
    app=create_app();s=source()
    collector=app.state.collector;collector.sources=[s]
    fixture=parse_offer(page(),s).model_dump(mode="json")
    monkeypatch.setattr(collector,"collect",lambda _:dict(status="collected",source_id=s.source_id,observation=fixture,cached=True))
    with TestClient(app) as web:
        info=web.get("/api/workspace").json();headers={"X-Workspace-Token":info["csrf_token"]}
        for _ in range(2): assert events(web.post("/api/sources/collect",headers=headers))[-1]["type"]=="complete"
        assert len(web.get("/api/evidence").json())==97
        recs=web.post("/api/v1/recommendations",json={"as_of":date.today().isoformat(),"evidence_mode":"live"}).json()["recommendations"]
        assert recs[0]["quality"]["usable_sellers"]==1
        assert all(r["quality"]["usable_sellers"]==0 for r in recs[1:])

def test_no_write_token_no_collection(monkeypatch):
    monkeypatch.delenv("PRICEPILOT_DB_PATH",raising=False)
    with TestClient(create_app()) as web:
        assert web.post("/api/demo/replay").status_code==403
        assert web.post("/api/demo/reset").status_code==403

def test_public_mode_protects_host_cookie_and_private_database(monkeypatch):
    monkeypatch.setenv("PRICEPILOT_PUBLIC_DEMO","1")
    monkeypatch.setenv("RENDER_EXTERNAL_HOSTNAME","pricepilot.example")
    monkeypatch.delenv("PRICEPILOT_DB_PATH",raising=False)
    with TestClient(create_app(),base_url="https://pricepilot.example") as web:
        response=web.get("/api/workspace")
        assert response.status_code==200 and "Secure" in response.headers["set-cookie"]
        assert web.get("/",headers={"host":"evil.example"}).status_code==400
        assert web.post("/api/demo/replay",content=b"x"*2_000_001).status_code==413
    monkeypatch.setenv("PRICEPILOT_DB_PATH","private.sqlite3")
    with pytest.raises(ValueError): create_app()

def test_store_example_has_distinct_business_decisions():
    service=demo_service()
    recs=service.recommendations(Scenario(as_of=load_demo().as_of,evidence_mode="demo"))
    assert [r.action for r in recs[:4]]==["decrease_price","increase_price","hold_price","urgent_review"]
    assert recs[4].recommended_price_gross is None
    service.repository.close()


def connection_payload():
    from src.application.advisor_examples import examples
    c=examples()[0]["input"].copy();c["origin"]="merchant"
    return dict(input=c,source=source(product_id="MY-OFFER").model_dump(mode="json"),exact_variant_confirmed=True)


def test_local_owner_can_connect_collect_and_use_real_evidence(monkeypatch):
    monkeypatch.delenv("PRICEPILOT_DB_PATH",raising=False)
    monkeypatch.delenv("PRICEPILOT_PUBLIC_DEMO",raising=False)
    monkeypatch.delenv("PRICEPILOT_SOURCES_PATH",raising=False)
    app=create_app()
    app.state.collector.fetch=lambda url:"User-agent: *\nAllow: /" if url.endswith("robots.txt") else page()
    monkeypatch.setattr("src.infrastructure.price_sources.time.sleep",lambda _:None)
    with TestClient(app) as web:
        headers={"X-Workspace-Token":web.get("/api/workspace").json()["csrf_token"]}
        payload=connection_payload()
        url="/api/sources/connect-offer"
        assert web.post(url,json=payload).status_code==403
        connected=web.post(url,json=payload,headers=headers)
        assert connected.status_code==200,connected.text
        assert not connected.json()["collected"]
        assert web.get("/api/sources").json()["configured"]==1
        assert web.post(url,json=payload,headers=headers).status_code==409
        results=events(web.post("/api/sources/collect",headers=headers))
        assert any(r.get("status")=="collected" for r in results)
        payload["input"]["linked_product_id"]="MY-OFFER"
        advice=web.post("/api/v1/advisor/consult",json=payload["input"]).json()
        assert len(advice["evidence"])==1
        assert advice["evidence"][0]["origin"]=="live"
        assert advice["evidence"][0]["price"]=="353.99"
        # Another visitor cannot see this owner's configured URLs or merchant offer.
        with TestClient(app) as other:
            assert other.get("/api/sources").json()["configured"]==0
            assert not any(e["product"]["product_id"]=="MY-OFFER" for e in other.get("/api/v1/products").json())


def test_product_refresh_is_scoped_authenticated_and_reports_partial_failure(monkeypatch):
    monkeypatch.delenv('PRICEPILOT_DB_PATH',raising=False)
    monkeypatch.delenv('PRICEPILOT_PUBLIC_DEMO',raising=False)
    monkeypatch.delenv('PRICEPILOT_SOURCES_PATH',raising=False)
    app=create_app();calls=[]
    def collect(s):
        calls.append(s.source_id)
        if s.source_id=='second':
            return dict(status='failed',source_id=s.source_id,message='Unsupported page',cached=False)
        return dict(status='collected',source_id=s.source_id,observation=parse_offer(page(),s,datetime(2026,9,26,12,tzinfo=timezone.utc)).model_dump(mode='json'),cached=True)
    monkeypatch.setattr(app.state.collector,'collect',collect)
    with TestClient(app) as web:
        headers={'X-Workspace-Token':web.get('/api/workspace').json()['csrf_token']}
        payload=connection_payload()
        assert web.post('/api/sources/connect-offer',json=payload,headers=headers).status_code==200
        payload['input']['linked_product_id']='MY-OFFER'
        payload['source'].update(source_id='second',seller='Other seller',url='https://retailer.example/second')
        assert web.post('/api/sources/connect-offer',json=payload,headers=headers).status_code==200
        payload['input']['linked_product_id']=None
        payload['source'].update(source_id='unrelated',product_id='ANOTHER-OFFER',seller='Unrelated seller')
        assert web.post('/api/sources/connect-offer',json=payload,headers=headers).status_code==200
        path='/api/sources/refresh-product';body={'product_id':'MY-OFFER'}
        assert web.post(path,json=body).status_code==403
        before=len(web.get('/api/evidence').json())
        for _ in range(2):
            result=web.post(path,json=body,headers=headers)
            assert result.status_code==200,result.text
            assert result.json()['collected']==1 and result.json()['failed']==1
            assert result.json()['results'][1]['message']=='Unsupported page'
        assert calls==['source-a','second','source-a','second']
        assert len(web.get('/api/evidence').json())==before+1
        assert web.post(path,json={'product_id':'DE-WEAR-001'},headers=headers).status_code==422
        assert web.post(path,json={'product_id':'MISSING'},headers=headers).status_code==404
        with TestClient(app) as other:
            own={'X-Workspace-Token':other.get('/api/workspace').json()['csrf_token']}
            assert other.post(path,json=body,headers=own).status_code==404


def test_public_demo_cannot_become_a_user_controlled_fetch_proxy(monkeypatch):
    monkeypatch.setenv("PRICEPILOT_PUBLIC_DEMO","1")
    monkeypatch.delenv("PRICEPILOT_DB_PATH",raising=False)
    with TestClient(create_app(),base_url="https://localhost") as web:
        headers={"X-Workspace-Token":web.get("/api/workspace").json()["csrf_token"]}
        assert not web.get("/api/sources").json()["can_configure"]
        assert web.post("/api/sources/connect-offer",json=connection_payload(),headers=headers).status_code==403


def test_collection_cache_does_not_confuse_same_id_across_different_sources(monkeypatch):
    monkeypatch.setattr("src.infrastructure.price_sources.time.sleep",lambda _:None)
    collector=Collector([],lambda url:"User-agent: *\nAllow: /" if url.endswith("robots.txt") else page())
    first=collector.collect(source())
    second=collector.collect(source(url="https://other.example/product",product_id="OTHER-PRODUCT"))
    assert first["observation"]["product_id"]=="DE-WEAR-001"
    assert second["observation"]["product_id"]=="OTHER-PRODUCT"
    assert not second["cached"]
