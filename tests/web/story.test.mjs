import {test} from 'node:test';
import assert from 'node:assert/strict';
import {decisionMeta,storeOverview,marketView,eventList} from '../../src/web/static/story.js';
const rec=(action,changes={})=>({action,product_id:'p1',product_name:'Watch',recommended_price_gross:'100',current_price_gross:'120',market_median_gross:'100',requires_review:false,selected_strategy:'balanced',...changes});
test('business decisions have distinct semantic labels and tones',()=>{
  const cases=[
    [rec('decrease_price'),{},'blue','Reduce price'],
    [rec('increase_price'),{},'violet','Raise price'],
    [rec('hold_price'),{},'neutral','Hold price'],
    [rec('urgent_review',{requires_review:true}),{},'amber','Review required'],
    [rec('urgent_review',{recommended_price_gross:null}),{},'red','Wait for data'],
    [rec('decrease_price',{selected_strategy:'clearance_cashflow'}),{inventory:95},'orange','Clear stock']
  ];
  for(const [r,p,tone,title] of cases){assert.equal(decisionMeta(r,p).tone,tone);assert.equal(decisionMeta(r,p).title,title);}
});
test('no evidence takes precedence over a review flag',()=>{
  assert.equal(decisionMeta(rec('urgent_review',{requires_review:true,recommended_price_gross:null})).title,'Wait for data');
});
const state=()=>({workspace:{store:{name:'Kiez & Co.',cases:[]}},scenario:{evidence_mode:'demo'},entries:[{product:{product_id:'p1',brand:'Test',inventory:10,replacement_cost_net:'50'}}],recs:[rec('decrease_price')],sources:{sources:[]},events:[]});
test('market gap chart calculates a percentage and labels both prices',()=>{
  const html=storeOverview(state(),()=>'',()=> '');
  assert.ok(html.includes('+20.0%'));assert.ok(html.includes('Store 120,00'));
  assert.ok(html.includes('market 100,00'));assert.ok(html.includes('do not predict demand'));
});
test('empty live evidence cannot show invented benchmark bars',()=>{
  const s=state();s.scenario.evidence_mode='live';s.recs=[rec('urgent_review',{market_median_gross:null,recommended_price_gross:null})];
  const html=storeOverview(s,()=>'',()=> '');
  assert.ok(html.includes('Collect comparable offers'));assert.ok(!html.includes('gap-bar '));
});
test('unconfigured collector clearly reports missing source setup',()=>{
  const html=marketView(state(),()=> '');
  assert.ok(html.includes('No competitor URLs have been selected yet'));assert.ok(html.includes('0 source URLs connected'));
});
test('collected text is escaped in the activity stream',()=>{
  const html=eventList([{seller:'<img src=x onerror=alert(1)>',type:'offer',price:99,mode:'demo'}]);
  assert.ok(!html.includes('<img'));assert.ok(html.includes('&lt;img'));assert.ok(html.includes('DEMO'));
});
test('store and product metadata are escaped in generated views',()=>{
  const s=state();s.workspace.store.name='<script>alert(1)</script>';s.recs[0].product_name='<img src=x>';
  const html=storeOverview(s,()=>'',()=> '');
  assert.ok(!html.includes('<script>'));assert.ok(!html.includes('<img'));
});
