"""Evidence for ML isolation, temporal evaluation and review integrity."""
from copy import deepcopy
from datetime import timedelta, date
from decimal import Decimal
import json
import numpy as np
import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from src.application.demand_demo import synthetic_history, demo_benchmark
from src.application.decision_brief import portfolio
from src.application.service import demo_service, load_demo
from src.domain.demand import DemandHistory, evaluate, features, fit, predict, metrics
from src.domain.models import Scenario
from src.infrastructure.repository import ConflictError, SQLiteRepository
from src.web.app import create_app


def test_model_learns_signal_and_fails_honestly_under_shift():
    normal, shock = demo_benchmark(), demo_benchmark(True)
    assert normal['beats_both_baselines']
    assert not shock['beats_both_baselines']
    assert normal['empirical_interval']['observed_test_coverage'] > shock['empirical_interval']['observed_test_coverage']
    assert not normal['live_pricing_allowed'] and normal['status'] == 'research_only'
    assert normal['origin'] == 'synthetic'
    json.dumps(normal, allow_nan=False)


def test_final_holdout_cannot_change_selection_scaling_or_fit():
    original = synthetic_history()
    changed = original.model_dump(mode='json')
    for row in changed['rows'][-28:]: row['units'] += 100
    a, b = evaluate(original), evaluate(DemandHistory.model_validate(changed))
    for key in ('selected_alpha', 'selection_trials', 'standardized_coefficients'):
        assert a[key] == b[key]
    assert a['empirical_interval']['radius_units'] == b['empirical_interval']['radius_units']
    assert a['holdout'][0]['predicted'] == b['holdout'][0]['predicted']
    assert a['dataset_sha256'] != b['dataset_sha256']
    assert a['metrics'] != b['metrics']


def test_calibration_never_refits_model():
    original = synthetic_history()
    changed = original.model_dump(mode='json')
    for row in changed['rows'][-56:-28]: row['units'] += 100
    a, b = evaluate(original), evaluate(DemandHistory.model_validate(changed))
    assert a['standardized_coefficients'] == b['standardized_coefficients']
    assert a['selected_alpha'] == b['selected_alpha']
    assert b['empirical_interval']['radius_units'] > a['empirical_interval']['radius_units']


def test_day_target_is_not_a_feature():
    rows = synthetic_history().rows
    current = rows[8].model_copy(update={'units': 9999})
    assert features(rows[8], rows[:8], rows[0].day) == features(current, rows[:8], rows[0].day)


def test_splits_are_chronological_and_nonoverlapping():
    report = demo_benchmark()
    blocks = list(report['split'].values())
    assert all(a['end'] < b['start'] for a, b in zip(blocks, blocks[1:]))
    assert report['holdout'][0]['day'] >= blocks[-1]['start']
    assert report['holdout'][-1]['day'] <= blocks[-1]['end']


@pytest.mark.parametrize('kind', ['duplicate','gap','future','negative','extra','too_short','infinity'])
def test_bad_history_is_rejected(kind):
    data = synthetic_history().model_dump(mode='json')
    if kind == 'duplicate': data['rows'][1]['day'] = data['rows'][0]['day']
    if kind == 'gap': data['rows'].pop(30)
    if kind == 'future': data['rows'][-1]['day'] = str(date.today()+timedelta(days=1))
    if kind == 'negative': data['rows'][0]['units'] = -1
    if kind == 'extra': data['rows'][0]['customer_email'] = 'not-accepted@example.test'
    if kind == 'too_short': data['rows'] = data['rows'][:179]
    if kind == 'infinity': data['rows'][0]['price_gross'] = 'Infinity'
    with pytest.raises(ValidationError): DemandHistory.model_validate(data)


def test_stockouts_are_not_treated_as_observed_zero_demand():
    data = synthetic_history().model_dump(mode='json')
    for row in data['rows'][-28:]: row['fully_in_stock'] = False
    with pytest.raises(ValueError, match='in-stock'): evaluate(DemandHistory.model_validate(data))


def test_zero_sales_metric_is_defined_and_empty_training_abstains():
    assert metrics([0,0],[1,0])['wape'] is None
    data = synthetic_history().model_dump(mode='json')
    for row in data['rows']: row['units'] = 0
    with pytest.raises(ValueError, match='no observed sales'): evaluate(DemandHistory.model_validate(data))


def test_constant_features_are_numerically_safe():
    x = np.ones((80,7))
    model = fit(x, [9]*80, .1)
    assert predict(model, x) == pytest.approx([9]*80)


def test_history_order_does_not_change_results():
    data = synthetic_history().model_dump(mode='json')
    a = evaluate(DemandHistory.model_validate(data))
    data['rows'].reverse()
    assert evaluate(DemandHistory.model_validate(data)) == a


def test_portfolio_reconciles_unit_economics_and_tracks_input_fingerprint():
    service = demo_service()
    scenario = Scenario(as_of=load_demo().as_of, evidence_mode='demo')
    a = portfolio(service, scenario)
    for b in a['briefs']:
        p = b['snapshot']['product']
        expected = (Decimal(p['current_price_gross'])/(1+Decimal(p['vat_rate']))*(1-Decimal(p['fee_rate']))
                    -Decimal(p['replacement_cost_net'])-Decimal(p['variable_cost_net']))
        assert Decimal(b['current_unit_contribution']) == expected.quantize(Decimal('.01'))
    changed = portfolio(service, scenario.model_copy(update={'cost_change_pct': Decimal(10)}))
    fingerprints = {b['product_id']:b['fingerprint'] for b in a['briefs']}
    assert all(fingerprints[b['product_id']] != b['fingerprint'] for b in changed['briefs'])
    assert a['briefs'][0]['priority'] <= a['briefs'][-1]['priority']
    service.repository.close()


@pytest.fixture
def client(monkeypatch):
    monkeypatch.delenv('PRICEPILOT_DB_PATH', raising=False)
    monkeypatch.delenv('PRICEPILOT_PUBLIC_DEMO', raising=False)
    with TestClient(create_app()) as client:
        yield client


def context(client):
    workspace = client.get('/api/workspace').json()
    headers = {'X-Workspace-Token':workspace['csrf_token']}
    scenario = {'as_of':workspace['as_of'],'evidence_mode':'demo'}
    report = client.post('/api/v1/intelligence/portfolio',json=scenario).json()
    b = next(b for b in report['briefs'] if b['checks']['market_evidence'] == 'ready' and b['checks']['inventory'] == 'pass')
    payload = {'product_id':b['product_id'],'fingerprint':b['fingerprint'],'scenario':scenario,
               'outcome':'accepted','reason':'Checked unit economics and current market evidence.'}
    return headers, report, payload


def test_endpoints_and_uploaded_data_are_evaluated_without_persistence(client):
    headers, _, _ = context(client)
    before = client.get('/api/v1/audit').json()
    report = client.get('/api/v1/intelligence/benchmark').json()
    assert report['model_version'] == 'daily-ridge-1'
    history = client.get('/api/v1/intelligence/demo-history').json()
    assert client.post('/api/v1/intelligence/evaluate',json=history).status_code == 403
    result = client.post('/api/v1/intelligence/evaluate',json=history,headers=headers)
    assert result.status_code == 200 and result.json() == report
    assert client.get('/api/v1/audit').json() == before
    assert client.get('/static/intelligence.js').status_code == 200


def test_review_records_snapshot_is_idempotent_and_does_not_publish(client):
    headers, _, payload = context(client)
    before = client.get('/api/v1/products').json()
    assert client.post('/api/v1/intelligence/reviews',json=payload).status_code == 403
    one = client.post('/api/v1/intelligence/reviews',json=payload,headers=headers)
    two = client.post('/api/v1/intelligence/reviews',json=payload,headers=headers)
    assert one.status_code == 200 and one.json() == two.json()
    assert one.json()['published'] is False
    records = client.get('/api/v1/intelligence/reviews').json()
    assert len(records) == 1 and records[0]['brief']['fingerprint'] == payload['fingerprint']
    assert records[0]['brief']['snapshot']['observations']
    assert client.get('/api/v1/products').json() == before
    payload['outcome'] = 'deferred'
    assert client.post('/api/v1/intelligence/reviews',json=payload,headers=headers).status_code == 200
    assert len(client.get('/api/v1/intelligence/reviews').json()) == 2


def test_stale_review_is_rejected_after_product_edit(client):
    headers, _, payload = context(client)
    entry = next(e for e in client.get('/api/v1/products').json() if e['product']['product_id'] == payload['product_id'])
    entry['product']['name'] += ' edited'
    client.put('/api/v1/products/'+payload['product_id'],headers=headers,json={'product':entry['product'],'expected_version':entry['version']})
    assert client.post('/api/v1/intelligence/reviews',json=payload,headers=headers).status_code == 409


def test_blocked_price_cannot_be_accepted_but_can_be_deferred(client):
    headers, report, payload = context(client)
    blocked = next(b for b in report['briefs'] if b['checks']['market_evidence'] == 'blocked')
    payload.update(product_id=blocked['product_id'],fingerprint=blocked['fingerprint'])
    assert client.post('/api/v1/intelligence/reviews',json=payload,headers=headers).status_code == 422
    payload['outcome'] = 'deferred'
    assert client.post('/api/v1/intelligence/reviews',json=payload,headers=headers).status_code == 200


def test_reviews_are_session_isolated(client):
    headers, _, payload = context(client)
    assert client.post('/api/v1/intelligence/reviews',headers=headers,json=payload).status_code == 200
    with TestClient(client.app) as other:
        assert other.get('/api/v1/intelligence/reviews').json() == []


def test_repository_rechecks_observations_inside_transaction():
    service = demo_service()
    report = portfolio(service, Scenario(as_of=load_demo().as_of))
    b = report['briefs'][0]
    obs = next(o for o in load_demo().observations if o.product_id == b['product_id'])
    service.repository.add_observation(obs.model_copy(update={'observation_id':'NEW-AT-COMMIT'}))
    with pytest.raises(ConflictError, match='during review'):
        service.repository.save_review(b,'deferred','Concurrent source update')
    assert service.repository.reviews() == []
    service.repository.close()


def test_journal_survives_database_reopen(tmp_path):
    from src.application.service import PricingService
    path = str(tmp_path/'reviews.sqlite3')
    service = PricingService(SQLiteRepository(path))
    service.repository.import_dataset(load_demo())
    b = portfolio(service, Scenario(as_of=load_demo().as_of))['briefs'][0]
    service.repository.save_review(b,'deferred','Need commercial review')
    service.repository.close()
    repository = SQLiteRepository(path)
    assert repository.reviews()[0]['brief'] == b
    repository.close()
