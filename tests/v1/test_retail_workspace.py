"""Retail decisions must survive accounting, import and execution edge cases."""
import csv
from datetime import date, timedelta
from decimal import Decimal as D
from io import StringIO
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from src.application.advisor import consult, per_unit
from src.application.retail import analyze, workspace, details_for, consultation_input
from src.application.retail_import import preview, commit, number, inspect_csv
from src.application.service import load_demo
from src.domain.advisory import Consultation
from src.domain.models import Product, RetailDetails, Dataset, Observation
from src.domain.pricing import contribution_margin, price_for_margin
from src.domain.retail_import import ImportPreview, CSVInspection
from src.infrastructure.repository import SQLiteRepository, ConflictError
from src.web.app import create_app


def merchant(**changes):
    details = RetailDetails(variant='44 mm GPS black, new',gtin='4006381333931',purchase_cost_net='45',
        shipping_cost_net='3',packaging_cost_net='1',returns_allowance_net='1',
        customer_shipping_gross='4.90',costs_checked_on=date.today(),sales_period_end=date.today()-timedelta(days=1),
        baseline_representative=True,cost_scope_confirmed=True)
    values=dict(product_id='SHOP-1',name='Test watch',data_origin='merchant',current_price_gross='119',
        replacement_cost_net='50',variable_cost_net='5',fee_rate='.02',fee_basis='gross',
        inventory=100,sales_30d=30,retail=details)
    return Product(**(values|changes))


@pytest.fixture
def repo():
    r=SQLiteRepository();yield r;r.close()


def run(p,repo,**options):
    entry=repo.save_product(p)
    return analyze(entry,repo,**options)


@pytest.mark.parametrize('basis,expected',[('net','43.00'),('gross','42.62')])
def test_fee_basis_reconciles_all_accounting_engines(repo,basis,expected):
    p=merchant(fee_basis=basis); item=run(p,repo);c=Consultation.model_validate(item['report']['input'])
    assert per_unit(D('119'),c)==D(expected)
    assert D(item['economics']['current_contribution'])==D(expected)
    assert contribution_margin(D('119'),p,D('50'))==D(expected)/100
    floor=price_for_margin(p,D('50'),p.minimum_margin)
    assert floor==D(item['report']['economics']['minimum_price_gross'])
    assert contribution_margin(floor,p,D('50'))>=p.minimum_margin
    assert contribution_margin(floor-D('.01'),p,D('50'))<p.minimum_margin
    rows=item['waterfall'];assert D(rows[0]['amount'])-sum(D(r['amount']) for r in rows[1:-1])==D(rows[-1]['amount'])


def test_historical_purchase_does_not_drive_replenishment_price(repo):
    p=merchant();entry=repo.save_product(p);before=analyze(entry,repo,candidate=D('122'))
    updated=Product.model_validate(p.model_dump()|{'retail':p.retail.model_dump()|{'purchase_cost_net':'80'}})
    after=analyze(repo.save_product(updated,1),repo,candidate=D('122'))
    assert before['economics']['historical_contribution']!=after['economics']['historical_contribution']
    assert before['report']['test_price_gross']==after['report']['test_price_gross']
    assert before['report']['economics']==after['report']['economics']
    assert after['economics']['target_is_not_recommendation']
    assert not after['intelligence']['demand_forecast_used']
    assert after['report']['source_snapshot']['product']['retail']['purchase_cost_net']=='80'


@pytest.mark.parametrize('detail_change,expected',[
    ({'cost_scope_confirmed':False},'refresh_inputs'),
    ({'baseline_representative':False},'refresh_inputs'),
    ({'costs_checked_on':date.today()-timedelta(days=31)},'refresh_inputs'),
])
def test_unconfirmed_or_old_inputs_block_a_price_test(repo,detail_change,expected):
    p=merchant();d=RetailDetails.model_validate(p.retail.model_dump()|detail_change)
    result=run(merchant(retail=d),repo,candidate=D('122'))
    assert result['report']['action']==expected
    assert not result['report']['can_start_test']


def test_missing_details_are_not_invented_for_a_merchant(repo):
    result=run(merchant(retail=None),repo)
    assert result['details'] is None and result['detail_origin']=='missing'
    assert result['economics']['historical_purchase_net'] is None
    assert result['report']['action']=='refresh_inputs'


def test_unknown_seven_day_sales_are_not_reported_as_a_decline(repo):
    result=run(merchant(sales_7d=0),repo)
    assert not any(s['title']=='Recent sales slowed' for s in result['signals'])
    p=merchant(retail=merchant().retail.model_copy(update={'sales_7d_known':True}))
    result=analyze(repo.save_product(p,1),repo)
    assert any(s['title']=='Recent sales slowed' for s in result['signals'])


def test_shipping_cannot_consume_the_entire_candidate(repo):
    p=merchant(current_price_gross='100',replacement_cost_net='1',retail=merchant().retail.model_copy(update={'customer_shipping_gross':D('95')}))
    result=run(p,repo,candidate=D('94'))
    assert result['report']['action']=='unsafe_price'
    assert result['economics']['candidate_item_price_gross'] is None


@pytest.mark.parametrize('changes,action',[({'inventory':0},'capacity'),({'sales_30d':0},'learn'),({'inventory':1},'capacity')])
def test_empty_baseline_or_inadequate_stock_cannot_be_optimized_away(repo,changes,action):
    assert run(merchant(**changes),repo,candidate=D('122'))['report']['action']==action


def test_scenario_changes_replacement_cost_only_and_has_no_write(repo):
    p=merchant();entry=repo.save_product(p);before=repo.audit_log()
    item=analyze(entry,repo,candidate=D('122'),cost_change_pct=D('20'))
    assert item['economics']['replacement_cost_net']=='60.00'
    assert item['economics']['historical_purchase_net']=='45.00'
    assert item['report']['input']['unit_cost_net']=='65.00'
    assert item['report']['input']['hypothetical_costs'] and item['simulation']
    assert repo.snapshot()[0][0].product==p and repo.audit_log()==before


def test_demo_has_multiple_actions_and_an_explicit_replay_date(repo):
    repo.import_dataset(load_demo());w=workspace(repo)
    assert w['counts']['products']==24 and w['counts']['cost_attention']>0 and w['counts']['tests']>0
    entries=repo.snapshot()[0];p=next(e for e in entries if e.product.product_id=='DE-WEAR-001')
    r=analyze(p,repo)
    assert r['detail_origin']=='demo_decomposition' and r['report']['input']['demo_as_of']==str(load_demo().as_of)
    assert r['report']['fingerprint']==consult(Consultation.model_validate(r['report']['input']),repo)['fingerprint']


@pytest.mark.parametrize('values',[
    {'fee_rate':'.70','target_margin':'.20'},
    {'retail':merchant().retail.model_copy(update={'gtin':'4006381333932'})},
    {'variable_cost_net':'0'},
    {'replacement_cost_net':'9999999999.99'},
])
def test_invalid_financial_or_identity_contracts_are_rejected(values):
    # Revalidate nested JSON to exercise full boundary validation.
    data=merchant().model_dump(mode='json')|values
    if isinstance(data.get('retail'),RetailDetails):data['retail']=data['retail'].model_dump(mode='json')
    with pytest.raises(ValidationError):Product.model_validate(data)


HEADERS=['sku','name','variant','item_price_gross','purchase_cost_net','replacement_cost_net','stock','sales_30d',
         'customer_shipping_gross','shipping_cost_net','gtin']


def source(rows=None,**changes):
    rows=rows or [['SHOP-1','Watch','44 mm GPS new','114,10','45','50','100','30','4,90','5','04006381333931']]
    out=StringIO();writer=csv.writer(out,delimiter=';');writer.writerow(HEADERS);writer.writerows(rows)
    data=dict(csv_text=out.getvalue(),mapping={h:h for h in HEADERS},defaults=dict(costs_checked_on=str(date.today()),
        sales_period_end=str(date.today()-timedelta(days=1)),baseline_representative=True,cost_scope_confirmed=True))
    return ImportPreview.model_validate(data|changes)


def test_preview_is_read_only_and_commit_preserves_costs_identity_and_unknown_sales(repo):
    s=source();review,products=preview(s,repo)
    assert review['can_commit'] and repo.snapshot()[0]==[] and repo.audit_log()==[]
    p=products[0];assert p.current_price_gross==D('119') and p.variable_cost_net==D('5')
    assert p.retail.gtin=='04006381333931' and p.fee_basis=='gross' and not p.retail.sales_7d_known
    assert commit(s,repo,review['fingerprint'],True)['overwritten']==0
    assert repo.snapshot()[0][0].product==p


@pytest.mark.parametrize('text,style,value',[
    ('1.234,56','comma','1234.56'),('1,234.56','dot','1234.56'),('0','comma','0'),('0001,20','comma','1.20')])
def test_explicit_decimal_conventions(text,style,value):
    assert number(text,style)==D(value)


@pytest.mark.parametrize('text,style',[('12.50','comma'),('12,50','dot'),('1e3','dot'),('=1+2','dot'),('NaN','dot'),('-1','dot'),('12 €','comma'),('1,2345','comma')])
def test_ambiguous_or_non_numeric_amounts_are_rejected(text,style):
    with pytest.raises(ValueError):number(text,style)


def test_import_is_all_or_nothing_even_when_one_row_is_valid(repo):
    s=source();row=['BAD','Watch','44 mm','120','50','60','','30','0','0','4006381333932']
    text=s.csv_text+';'.join(row)+'\n';bad=source(csv_text=text)
    report,_=preview(bad,repo)
    assert report['valid_count']==1 and not report['can_commit']
    assert any(e['field']=='stock' and e['line']==3 for e in report['errors'])
    with pytest.raises(ValueError):commit(bad,repo,report['fingerprint'],True)
    assert repo.snapshot()[0]==[] and repo.audit_log()==[]


def test_no_overwrite_or_duplicate_case_variants(repo):
    s=source();report,_=preview(s,repo);commit(s,repo,report['fingerprint'],True)
    report,_=preview(source(csv_text=s.csv_text.replace('SHOP-1','shop-1')),repo)
    assert not report['can_commit'] and any('already exists' in e['message'] for e in report['errors'])
    r=SQLiteRepository()
    try:
        report,_=preview(source(csv_text=s.csv_text+s.csv_text.splitlines()[1].replace('SHOP-1','shop-1')),r)
        assert not report['can_commit'] and any('Duplicate SKU' in e['message'] for e in report['errors'])
    finally:r.close()


def test_changed_preview_or_missing_confirmation_cannot_commit(repo):
    s=source();r,_=preview(s,repo)
    with pytest.raises(ValueError,match='confirm'):commit(s,repo,r['fingerprint'],False)
    with pytest.raises(ValueError,match='changed'):commit(s,repo,'0'*64,True)
    repo.save_product(merchant())
    with pytest.raises(ValueError,match='existing'):commit(s,repo,r['fingerprint'],True)
    assert len(repo.snapshot()[0])==1


def test_case_conflicts_and_capacity_are_checked_inside_transaction(repo):
    repo.save_product(merchant());before=repo.audit_log()
    fresh=merchant(product_id='SECOND');duplicate=merchant(product_id='shop-1')
    for products,limit in [([fresh,duplicate],1000),([fresh],1)]:
        with pytest.raises(ConflictError):repo.import_dataset(Dataset(name='batch',as_of=date.today(),products=products,observations=[]),max_products=limit)
    assert len(repo.snapshot()[0])==1 and repo.audit_log()==before


@pytest.mark.parametrize('text',['a;a\n1;2','sku;name\n1','a\n"unclosed','a\n'])
def test_malformed_structural_csv_errors(text):
    with pytest.raises(ValueError):inspect_csv(CSVInspection(csv_text=text))


def test_tsv_empty_final_cell_is_preserved_by_contract_validation():
    source=CSVInspection(csv_text='sku\toptional\nS1\t',delimiter='\t')
    _,rows=inspect_csv(source)
    assert rows[0]['cells']=={'sku':'S1','optional':''}


def test_existing_evidence_locks_variant_across_all_product_endpoints(repo):
    p=merchant();repo.save_product(p)
    repo.add_observation(Observation(observation_id='O1',product_id=p.product_id,seller='seller',price_gross='119',
        available=True,observed_on=date.today(),source='owner example',data_origin='demo'))
    changed=Product.model_validate(p.model_dump()|{'retail':p.retail.model_dump()|{'variant':'LTE different model'}})
    with pytest.raises(ConflictError,match='variant'):repo.save_product(changed,1)
    with pytest.raises(ConflictError,match='detail'):repo.save_product(merchant(retail=None),1)
    assert repo.snapshot()[0][0].product==p


@pytest.fixture
def web(monkeypatch):
    monkeypatch.delenv('PRICEPILOT_DB_PATH',raising=False)
    with TestClient(create_app()) as client:yield client


def test_import_decide_plan_export_apply_review_whole_http_journey(web):
    headers={'X-Workspace-Token':web.get('/api/workspace').json()['csrf_token']}
    s=source().model_dump(mode='json')
    assert web.post('/api/v1/retail/import/inspect',json={k:s[k] for k in ('csv_text','delimiter')}).json()['row_count']==1
    review=web.post('/api/v1/retail/import/preview',json=s).json()
    body=dict(source=s,fingerprint=review['fingerprint'],confirmed=True)
    assert web.post('/api/v1/retail/import/commit',json=body).status_code==403
    assert web.post('/api/v1/retail/import/commit',json=body,headers=headers).status_code==201
    r=web.post('/api/v1/retail/analyze',json={'product_id':'SHOP-1','candidate_price':'122'}).json()['report']
    assert r['can_start_test'] and not r['forecast']
    saved=web.post('/api/v1/advisor/plans',headers=headers,json=dict(request_id=str(uuid4()),input=r['input'],fingerprint=r['fingerprint']))
    assert saved.status_code==200,saved.text
    p=saved.json();assert not p['published'];path='/api/v1/advisor/plans/'+p['id']
    response=web.get(path+'/price-sheet');assert response.status_code==200
    row=list(csv.DictReader(StringIO(response.text.lstrip('\ufeff'))))[0]
    assert row['sku']=='SHOP-1' and D(row['item_price_incl_vat'])==D('117.10')
    assert D(row['delivery_incl_vat'])==D('4.90') and row['published']=='false'
    assert row['input_fingerprint']==r['fingerprint']
    start=web.post(path+'/start',headers=headers,json=dict(started_on=str(date.today()),actual_price_gross='122',note='Applied manually to single item'))
    assert start.status_code==200,start.text
    outcome=web.post(path+'/outcome',headers=headers,json=dict(ended_on=str(date.today()),units=1,
        actual_unit_cost_net='55',actual_fee_rate='.02',actual_fee_basis='gross',actual_vat_rate='.19',
        fully_available=True,price_unchanged=True,other_changes='No other changes observed',confounded=False))
    assert outcome.status_code==200,outcome.text
    result=outcome.json()['result'];assert result['verdict']=='early' and not result['causal_claim']
    assert outcome.json()['status']=='active'
    with TestClient(web.app) as other:
        assert other.get(path+'/price-sheet').status_code==404
        assert other.post('/api/v1/retail/analyze',json={'product_id':'SHOP-1'}).status_code==404


def test_hypothetical_cost_scenario_rejected_server_side(web):
    headers={'X-Workspace-Token':web.get('/api/workspace').json()['csrf_token']}
    r=web.post('/api/v1/retail/analyze',json={'product_id':'DE-WEAR-001','cost_change_pct':10}).json()['report']
    response=web.post('/api/v1/advisor/plans',headers=headers,json=dict(request_id=str(uuid4()),input=r['input'],fingerprint=r['fingerprint']))
    assert response.status_code==422 and 'what-if' in response.text


def test_edit_is_versioned_and_rejects_provenance_changes(web):
    headers={'X-Workspace-Token':web.get('/api/workspace').json()['csrf_token']}
    p=merchant().model_dump(mode='json');body=dict(product=p,expected_version=0)
    assert web.put('/api/v1/retail/product',json=body,headers=headers).json()['version']==1
    assert web.put('/api/v1/retail/product',json=body,headers=headers).status_code==409
    body['expected_version']=1;p['data_origin']='demo'
    assert web.put('/api/v1/retail/product',json=body,headers=headers).status_code==422


def test_draft_cost_edits_update_insight_without_writing_and_cannot_be_saved_as_a_plan(web):
    headers={'X-Workspace-Token':web.get('/api/workspace').json()['csrf_token']}
    before=web.post('/api/v1/retail/analyze',json={'product_id':'DE-WEAR-001'}).json()
    draft=before['product'] | {'replacement_cost_net':str(D(before['product']['replacement_cost_net'])+10)}
    audit=web.get('/api/v1/audit').json()
    body=dict(product_id=draft['product_id'],expected_version=before['version'],product_draft=draft)
    response=web.post('/api/v1/retail/analyze',json=body)
    assert response.status_code==200,response.text
    preview=response.json()
    assert D(preview['economics']['current_contribution']) == D(before['economics']['current_contribution'])-10
    assert D(preview['report']['economics']['minimum_price_gross']) > D(before['report']['economics']['minimum_price_gross'])
    assert preview['draft'] and preview['report']['input']['hypothetical_costs']
    assert web.get('/api/v1/audit').json()==audit
    assert web.post('/api/v1/retail/analyze',json={'product_id':draft['product_id']}).json()['product']==before['product']
    r=preview['report']
    rejected=web.post('/api/v1/advisor/plans',headers=headers,json=dict(request_id=str(uuid4()),input=r['input'],fingerprint=r['fingerprint']))
    assert rejected.status_code==422 and 'what-if' in rejected.text
    body.pop('expected_version')
    assert web.post('/api/v1/retail/analyze',json=body).status_code==422
    body['expected_version']=before['version']+1
    assert web.post('/api/v1/retail/analyze',json=body).status_code==409
    body['expected_version']=before['version'];body['product_draft']=draft | {'data_origin':'merchant'}
    assert web.post('/api/v1/retail/analyze',json=body).status_code==422


def test_candidate_insights_show_conditional_tradeoff_and_volume_guardrail(repo):
    entry=repo.save_product(merchant())
    low=analyze(entry,repo,candidate=D('116'))
    high=analyze(entry,repo,candidate=D('122'),max_loss=D(0))
    assert low['insight']['current_per_sale']=='42.62'
    assert low['insight']['considered_per_sale']=='40.16'
    assert low['insight']['difference_per_sale']=='-2.46'
    assert 'extra sales' in low['insight']['message']
    assert low['insight']['required_units'] > high['insight']['required_units']
    assert high['insight']['required_units']==14
    assert high['insight']['considered_per_sale']=='45.08'
    assert not high['insight']['forecast']
    unsafe=analyze(entry,repo,candidate=D('50'))
    assert not unsafe['insight']['allowed'] and unsafe['insight']['required_units'] is None
    assert unsafe['insight']['message']==unsafe['report']['why']


def test_context_changes_the_next_action_and_owner_offers_are_attributed(repo):
    from src.domain.advisory import Comparable
    entry=repo.save_product(merchant())
    low_visibility=analyze(entry,repo,signal='low_visibility')
    capacity=analyze(entry,repo,signal='at_capacity')
    assert not low_visibility['report']['can_start_test']
    assert capacity['report']['can_start_test']
    assert 'new orders' in capacity['report']['title']
    assert 'bookings' not in capacity['report']['title']
    offers=[Comparable(seller=s,url=f'https://example.com/watch-{i}',total_price_gross='110',observed_on=date.today(),same_offer=True,available=True) for i,s in enumerate(['Shop A','Shop B'])]
    item=analyze(entry,repo,comparables=offers,signal='price_objections')
    assert item['report']['market_usable']
    assert item['insight']['market_gap_pct']=='8.2'
    assert {e['origin'] for e in item['report']['evidence']}=={'owner_entered'}
    changed=analyze(entry,repo,comparables=offers,positioning='differentiated')
    assert changed['report']['input']['positioning']=='differentiated'
    assert not changed['report']['market_usable']


def test_unmeasured_factor_can_pause_a_price_trial_without_inventing_a_score(web):
    token={'X-Workspace-Token':web.get('/api/workspace').json()['csrf_token']}
    base=web.post('/api/v1/retail/analyze',json={'product_id':'DE-WEAR-001'}).json()
    note=dict(topic='trust',statement='Do unclear warranty terms lose sales?',basis='question',
              evidence_note='',checked_on=base['report']['as_of'],resolve_first=True)
    request=dict(product_id='DE-WEAR-001',candidate_price='435.53',knowledge_notes=[note])
    r=web.post('/api/v1/retail/analyze',json=request).json()['report']
    assert r['action']=='learn' and not r['can_start_test']
    finding=r['discovery']['open_questions'][0]
    assert finding['numeric_score'] is None and not finding['independently_verified']
    assert 'warranty' in finding['collect'] and 'not a trust score' in finding['interpret']
    response=web.post('/api/v1/advisor/plans',headers=token,json=dict(request_id=str(uuid4()),input=r['input'],fingerprint=r['fingerprint']))
    assert response.status_code==200,response.text
    assert response.json()['report']['discovery']['open_questions'][0]['statement']==note['statement']
    note['resolve_first']=False
    assert web.post('/api/v1/retail/analyze',json=request).json()['report']['can_start_test']
    request['candidate_price']='1'
    note['resolve_first']=True
    assert web.post('/api/v1/retail/analyze',json=request).json()['report']['action']=='unsafe_price'
    note['basis']='observed'
    assert web.post('/api/v1/retail/analyze',json=request).status_code==422


def test_unconfirmed_costs_are_not_overruled_by_customer_questions(repo):
    p=merchant(retail=merchant().retail.model_copy(update={'cost_scope_confirmed':False}))
    note=dict(topic='delivery',statement='Customers may want faster delivery',basis='hypothesis',checked_on=date.today(),resolve_first=True)
    r=run(p,repo,candidate=D('122'),knowledge_notes=[note])['report']
    assert r['action']=='refresh_inputs' and not r['can_start_test']


def test_paused_automatic_candidate_has_consistent_accounting(repo):
    note=dict(topic='trust',statement='Check the warranty concern first',basis='question',checked_on=date.today(),resolve_first=True)
    item=run(merchant(),repo,signal='at_capacity',knowledge_notes=[note])
    assert item['report']['action']=='learn' and not item['report']['can_start_test']
    assert item['report']['test_price_gross'] is None
    assert item['insight']['considered_price']==item['report']['considered_price_gross']
    assert item['insight']['considered_per_sale']==item['report']['economics']['proposed_unit_contribution']


def test_catalog_gtin_must_match_collector_gtin(web):
    headers={'X-Workspace-Token':web.get('/api/workspace').json()['csrf_token']}
    web.put('/api/v1/retail/product',json=dict(product=merchant().model_dump(mode='json')),headers=headers)
    r=web.post('/api/v1/retail/analyze',json={'product_id':'SHOP-1'}).json()['report']
    response=web.post('/api/sources/connect-offer',headers=headers,json=dict(input=r['input'],exact_variant_confirmed=True,
        source=dict(source_id='S1',product_id='SHOP-1',seller='Competitor',url='https://example.com/watch',
                    expected_gtin='012345678905',shipping_gross='0',shipping_note='Germany delivery')))
    assert response.status_code==422 and 'GTIN must match' in response.text


def test_start_rechecks_the_saved_product_version_atomically(repo):
    p=merchant();entry=repo.save_product(p)
    report=analyze(entry,repo,candidate=D('122'))['report']
    plan_id=str(uuid4());repo.save_advisory_plan(plan_id,report)
    repo.save_product(merchant(replacement_cost_net='60'),1)
    with pytest.raises(ConflictError,match='changed after planning'):
        repo.transition_advisory(plan_id,'planned','active',start=dict(started_on=str(date.today()),actual_price_gross='122',note='Applied'))
    assert repo.advisory_plan(plan_id)['status']=='planned'


def test_two_linked_trials_cannot_run_at_once(repo):
    entry=repo.save_product(merchant());report=analyze(entry,repo,candidate=D('122'))['report']
    ids=[str(uuid4()),str(uuid4())]
    for pid in ids:repo.save_advisory_plan(pid,report)
    repo.transition_advisory(ids[0],'planned','active',start={'started_on':str(date.today())})
    with pytest.raises(ConflictError,match='already has an active trial'):
        repo.transition_advisory(ids[1],'planned','active',start={'started_on':str(date.today())})
