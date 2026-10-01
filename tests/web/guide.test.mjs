import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {priceOptions,decisionMessage} from '../../src/web/static/price-options.js';
import {guide,resultView} from '../../src/web/static/guide.js';
const p={product_id:'p1',name:'Watch',current_price_gross:119,replacement_cost_net:60,variable_cost_net:5,vat_rate:.19,fee_rate:.02,minimum_margin:.1,sales_30d:20,inventory:100};
const rec={recommended_price_gross:115,market_median_gross:120,quality:{status:'ready',usable_sellers:3}};

test('the priorities expose a genuine sales/contribution trade-off',()=>{
  const balance=priceOptions(p,rec),volume=priceOptions(p,rec,{goal:'volume'}),earnings=priceOptions(p,rec,{goal:'earnings'});
  assert.ok(volume.selected.units.low>=balance.baseline.units.mid);
  assert.ok(volume.selected.contribution.low<balance.baseline.contribution.mid);
  assert.ok(earnings.selected.contribution.low>balance.baseline.contribution.mid);
  assert.ok(earnings.selected.units.low<balance.baseline.units.mid);
  assert.ok(balance.selected.units.low>=balance.baseline.units.mid*.95);
  assert.notEqual(balance.selected.price,volume.selected.price);
});

test('a zero sales-loss tolerance never quietly sacrifices units',()=>{
  const r=priceOptions(p,rec,{tolerance:0});
  assert.equal(r.state,'ready');assert.ok(r.selected.units.low>=r.baseline.units.mid);
  assert.equal(r.selected.price,r.baseline.price);
});

test('volume priority respects the operator contribution limit',()=>{
  for(const tolerance of [0,5,10,20,30]){
    const r=priceOptions(p,rec,{goal:'volume',tolerance});
    assert.ok(r.selected.contribution.low>=r.baseline.contribution.mid*(1-tolerance/100)-.00001);
    assert.ok(r.selected.units.low>=r.baseline.units.mid);
  }
});

test('no stock, no sales or no market evidence yields an action instead of invented outcomes',()=>{
  for(const [product,r,state] of [[{...p,inventory:0},rec,'no_stock'],[{...p,sales_30d:0},rec,'no_sales'],[p,{...rec,recommended_price_gross:null},'no_market'],[p,{...rec,market_median_gross:null},'no_market']]){
    const result=priceOptions(product,r);assert.equal(result.state,state);
    const html=resultView(product,r,result);assert.ok(!html.includes('id="guide-save"'));
    assert.ok(!html.includes('Possible units sold'));assert.match(html,/RESOLVE THIS FIRST/);
  }
});

test('a prohibitive margin floor never becomes an endorsed current price',()=>{
  const product={...p,replacement_cost_net:120};const r=priceOptions(product,rec);
  assert.equal(r.state,'no_safe_option');assert.match(decisionMessage(product,r).title,/Review costs/);
  assert.ok(!resultView(product,rec,r).includes('id="guide-save"'));
});

test('scenario comparison uses the same cost assumptions on both sides',()=>{
  const r=priceOptions(p,rec,{cost:10});
  assert.equal(r.baseline.unit,27);assert.equal(r.baseline.units.mid,20);
  assert.ok(r.baseline.floor>priceOptions(p,rec).baseline.floor);
});

test('all suggested demo prices obey floors, movement bounds, stock and chosen tolerance',()=>{
  const dataset=JSON.parse(readFileSync(new URL('../../data/scenarios/germany_wearables/demo.json',import.meta.url),'utf8'));
  for(const product of dataset.products)for(const goal of ['balanced','earnings','volume'])for(const cost of [-30,0,30,100]){
    const fakeRec={...rec,market_median_gross:product.current_price_gross};
    const r=priceOptions(product,fakeRec,{goal,cost});
    if(r.state!=='ready')continue;
    assert.ok(r.selected.price>=r.selected.floor);
    assert.ok(Math.abs(r.selected.change)<=10.01);
    assert.ok(r.selected.units.high<=product.inventory);
    assert.ok(r.options.length<=3);
    assert.ok(r.options.some(o=>o.price===r.selected.price));
    if(goal==='volume')assert.ok(r.selected.contribution.low>=Math.max(0,r.baseline.contribution.mid*(1-r.tolerance/100))-.00001);
    else assert.ok(r.selected.units.low>=r.baseline.units.mid*(1-r.tolerance/100)-.00001);
  }
});

test('ranges contain their middle and options use distinct prices',()=>{
  const r=priceOptions(p,rec);
  assert.equal(new Set(r.options.map(o=>o.price)).size,r.options.length);
  for(const o of r.options)for(const k of ['units','contribution'])assert.ok(o[k].low<=o[k].mid&&o[k].mid<=o[k].high);
});

test('changing the sensitivity changes the recommendation but never claims certainty',()=>{
  const a=priceOptions(p,rec,{sensitivity:'low'}),b=priceOptions(p,rec,{sensitivity:'high'});
  assert.notEqual(a.selected.price,b.selected.price);
  assert.match(resultView(p,rec,a),/scenario ranges, not forecasts/);
  assert.match(resultView(p,rec,a),/does not approve or publish/);
});

test('guided entry has a clear task, three priorities and optional advanced controls',()=>{
  const S={entries:[{product:p}]};const html=guide(S);
  assert.match(html,/Which product/);assert.equal((html.match(/data-goal=/g)||[]).length,3);
  assert.match(html,/guide-tolerance/);assert.match(html,/<details class="guide-advanced/);
  assert.ok(!html.includes('data-lever='));
});

test('empty and changed catalogs are handled without stale product pointers',()=>{
  assert.match(guide({entries:[]}),/Add a product/);
  const S={entries:[{product:p}],guide:{id:'removed',goal:'balanced',sensitivity:'medium',tolerance:5}};
  guide(S);assert.equal(S.guide.id,'p1');
});

test('imported names cannot inject markup into guided controls',()=>{
  assert.ok(!guide({entries:[{product:{...p,name:'<script>alert(1)</script>'}}]}).includes('<script>alert'));
});
