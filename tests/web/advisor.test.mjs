import test from 'node:test';
import assert from 'node:assert/strict';
import {adviceCard,blankCase,caseFromProduct} from '../../src/web/static/advisor.js';

const report={can_start_test:true,title:'Try a controlled change',why:'A reason',next_step:'Track the result',test_price_gross:'29.75',input:{current_price_gross:'29.00',unit:'item',test_days:14,max_volume_loss_pct:'5'},economics:{minimum_units_with_volume_guardrail:40}};
test('advice presents a required outcome rather than an invented forecast',()=>{
  const html=adviceCard(report);
  assert.match(html,/At least 40 sales in 14 days/);
  assert.match(html,/not a sales forecast/);
  assert.match(html,/money left after sales costs/);
  assert.match(html,/lost sales within your 5% limit/);
});
test('non-price diagnosis has an action, no misleading price or threshold',()=>{
  const html=adviceCard({...report,can_start_test:false,test_price_gross:null});
  assert.match(html,/Your next business action/);
  assert.doesNotMatch(html,/At least|advice-price/);
});
test('merchant input and all visible advice text are treated as untrusted',()=>{
  const html=adviceCard({...report,title:'<script>alert(1)</script>',why:'<img src=x>',next_step:'<svg onload=x>'});
  assert.doesNotMatch(html,/<script|<img|<svg/);
  assert.match(html,/&lt;script/);
});
test('new cases require baseline confirmation and do not pretend to have sales',()=>{
  const c=blankCase();
  assert.equal(c.origin,'merchant');assert.equal(c.baseline_representative,false);
  assert.equal(c.baseline_units,'');assert.equal(c.proposed_price_gross,null);
});
test('catalog import preserves synthetic provenance and requires input confirmation',()=>{
  const c=caseFromProduct({product_id:'D1',name:'Demo',data_origin:'demo',current_price_gross:'119',replacement_cost_net:'50',variable_cost_net:'5',vat_rate:'0.19',fee_rate:'0.02',minimum_margin:'0.1',sales_30d:10,inventory:20},'2026-09-26');
  assert.equal(c.unit_cost_net,'55.00');assert.equal(c.linked_product_id,'D1');
  assert.equal(c.origin,'demo');assert.equal(c.baseline_representative,false);
});
