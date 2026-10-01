import test from 'node:test';
import assert from 'node:assert/strict';
import {boundaryChart,discoveryWalkthrough,learningPanel,valueForm,methodPage} from '../../src/web/static/discovery.js';

const report={input:{current_price_gross:'119',proposed_price_gross:'122.57'},test_price_gross:'122.57',viability:{available:true,capacity:35,baseline_units:'28',trial_days:14,points:[{price_gross:'107.10',required_units:50,feasible:false,reasons:['More sales required than capacity allows']},{price_gross:'119',required_units:28,feasible:true,reasons:[]},{price_gross:'122.57',required_units:27,feasible:true,reasons:[]}]}};
test('trade-off chart labels requirements, capacity and clipping instead of predicted sales',()=>{
  const html=boundaryChart(report);
  assert.match(html,/not a demand forecast/);assert.match(html,/Capacity: 35/);
  assert.match(html,/clipped/);assert.match(html,/Exact requirements/);
  assert.match(html,/boundary-selected/);assert.doesNotMatch(html,/NaN|Infinity/);
});
test('chart handles collapsed price ranges and zero capacity',()=>{
  const html=boundaryChart({...report,viability:{...report.viability,capacity:0,points:[report.viability.points[1]]}});
  assert.doesNotMatch(html,/NaN|Infinity/);
});
test('no viable baseline means no decorative chart',()=>{
  assert.equal(boundaryChart({...report,viability:{...report.viability,available:false}}),'');
});
test('owner claims and learning contracts escape text and preserve uncertainty',()=>{
  const html=learningPanel({discovery:{question:'<img src=x>',hypothesis:'<script>bad</script>',what_would_change_our_mind:'A failed threshold',next_evidence:'Observe',local_knowledge:{basis:'hypothesis',customer_group:'<svg>',reason_to_choose:'Fast',checked_on:'2026-09-27'},knowledge:[]}});
  assert.doesNotMatch(html,/<img|<script|<svg/);assert.match(html,/YOUR UNTESTED BELIEF/);
  assert.match(html,/not independently verified/);assert.match(html,/WHAT WOULD CHANGE OUR MIND/);
});
test('value intake never calls an owner assertion verified data',()=>{
  const html=valueForm({costs_checked_on:'2026-09-27',customer_value:{customer_group:'" autofocus="',reason_to_choose:'<script>',basis:'owner_observed'}});
  assert.match(html,/cannot calculate/);assert.doesNotMatch(html,/<script|value="" autofocus/);
});
test('method provides primary sources and a clear limit on philosophical claims',()=>{
  const html=methodPage();
  assert.match(html,/econlib.org/);assert.match(html,/nobelprize.org/);
  assert.match(html,/not an empirical validation/);assert.match(html,/Inspect the ML evaluation/);
});
test('discovery walk-through attributes the change to local knowledge',()=>{
  const r={...report,input:{...report.input,unit_cost_net:'48',test_days:14},market_median_gross:'100',title:'Check value',economics:{minimum_units_with_volume_guardrail:27}};
  const d={steps:[0,1,2].map(i=>({label:'Step '+i,explanation:'<img>',report:r})),boundary:'The owner can be wrong.'};
  const html=discoveryWalkthrough(d,1);
  assert.match(html,/THE DECISION CHANGES/);assert.match(html,/does not establish a price premium/);
  assert.doesNotMatch(html,/<img/);assert.match(html,/aria-pressed="true"/);
});
