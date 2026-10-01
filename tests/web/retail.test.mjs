import test from 'node:test';
import assert from 'node:assert/strict';
import {actionTone,retailRows,retailDecision,costBreakdown,editedProduct,bindRetail,disposeRetail} from '../../src/web/static/retail.js';
import {templateCSV,suggestedMapping,importPreviewHTML,bindRetailImport} from '../../src/web/static/retail-import.js';

function item(title='Try a small test'){
  return {product:{product_id:'W1',name:'Watch',brand:'Brand',data_origin:'merchant',current_price_gross:'119',fee_rate:'.02',fee_basis:'gross',minimum_margin:'.10',target_margin:'.25'},
    version:1,details:null,detail_origin:'missing',simulation:false,signals:[],risks:[],
    report:{action:'price_test',title,why:'Owner supplied a candidate',next_step:'Apply it and record sales',can_start_test:true,test_price_gross:'122',
      input:{current_price_gross:'119',signal:'unknown',test_days:14},economics:{minimum_units_with_volume_guardrail:14,minimum_price_gross:'74.70'},
      evidence:[],excluded_evidence:0,market_usable:false,market_median_gross:null},
    economics:{historical_purchase_net:null,replacement_cost_net:'50',target_price_gross:'90'},
    waterfall:[{label:'Customer pays',amount:'119',kind:'total'},{label:'VAT',amount:'19',kind:'cost'},{label:'Left before fixed costs',amount:'42.62',kind:'remaining'}],
    intelligence:{next_data:'Daily SKU history',model_gate:'Beat a baseline'}};
}

test('price tests, missing inputs and cost problems are distinct actions',()=>{
  assert.equal(actionTone({can_start_test:true}),'test');
  assert.equal(actionTone({priority:0}),'cost');
  assert.equal(actionTone({action:'refresh_inputs'}),'check');
  assert.equal(actionTone({action:'investigate'}),'hold');
});
test('a retail decision offers an action and required sales, never a forecast',()=>{
  const html=retailDecision(item());assert.match(html,/14 sales/);assert.match(html,/not a prediction/);
  assert.match(html,/including VAT and delivery/);
  const blocked=item();blocked.report.can_start_test=false;blocked.report.test_price_gross=null;
  assert.doesNotMatch(retailDecision(blocked),/retail-price-change|14 sales/);
  blocked.simulation=true;assert.match(retailDecision(blocked),/NOT READY TO APPLY/);
});
test('untrusted product, advice and CSV text are escaped',()=>{
  const row={product_id:'W1',name:'<script>bad</script>',brand:'<img src=x>',current_price_gross:'119',title:'<b>oops</b>'};
  const html=retailRows([row])+retailDecision(item('<script>bad</script>'));
  assert.doesNotMatch(html,/<script|<img src=x|<b>oops/);assert.match(html,/&lt;script/);
  const preview=importPreviewHTML({can_commit:false,valid_count:0,row_count:1,errors:[{line:2,sku:'<script>',field:'sku',message:'<img src=x>'}],preview:[],ignored_columns:['<svg>'],warnings:[]});
  assert.doesNotMatch(preview,/<script|<svg|<img src=x|data-import="commit"/);assert.match(preview,/Nothing has been saved/);
});
test('cost presentation distinguishes unknown purchase cost and fixed overhead',()=>{
  const html=costBreakdown(item());assert.match(html,/not net profit/);assert.match(html,/Detailed costs are missing/);
  assert.match(html,/Neither tells us what the customer is willing to pay/);
});
test('editor saves a reconciled delivered order without counting shipping as a cost twice',()=>{
  const original={...item().product,retail:{}};
  const f={product_id:'W1',name:'Watch',brand:'Brand',item_price_gross:'114.10',customer_shipping_gross:'4.90',
    replacement_cost_net:'50',purchase_cost_net:'45',shipping_cost_net:'3',packaging_cost_net:'1',returns_allowance_net:'1',
    inbound_cost_net:'0',other_cost_net:'0',fixed_fee_net:'0.30',fee_percent:'2',fee_basis:'gross',vat_percent:'19',
    minimum_margin_percent:'10',target_margin_percent:'25',inventory:'100',sales_30d:'30',sales_7d:'',variant:'44mm new',
    gtin:'04006381333931',costs_checked_on:'2026-09-26',sales_period_end:'2026-09-25',signal:'unknown',cost_scope_confirmed:true,baseline_representative:false};
  const p=editedProduct(f,original);assert.equal(p.current_price_gross,'119.00');assert.equal(p.variable_cost_net,'5.30');
  assert.equal(p.retail.gtin,'04006381333931');assert.equal(p.retail.sales_7d_known,false);assert.equal(p.retail.baseline_representative,false);
  assert.equal(p.retail.cost_scope_confirmed,true);assert.equal(p.fee_basis,'gross');assert.equal(p.fee_rate,'0.0200');
  assert.deepEqual(original.retail,{});
});
test('CSV template has required headers and does not plant fake business inputs',()=>{
  const text=templateCSV();assert.ok(text.startsWith('\ufeff'));assert.equal(text.trim().split('\r\n').length,1);
  for(const key of ['sku','variant','purchase_cost_net','replacement_cost_net','stock','sales_30d'])assert.ok(text.includes(key));
  assert.deepEqual(suggestedMapping([' SKU ','Product Name'],[{key:'sku'},{key:'name'}]),{sku:' SKU ',name:''});
});
test('valid preview still requires an explicit confirmation before commit',()=>{
  const html=importPreviewHTML({can_commit:true,row_count:1,valid_count:1,errors:[],preview:[],ignored_columns:[],warnings:[]});
  assert.match(html,/id="import-confirm" type="checkbox"/);assert.match(html,/data-import="commit" disabled/);assert.doesNotMatch(html,/<input[^>]*\schecked/);
});

function deferred(){let resolve;const promise=new Promise(r=>resolve=r);return {promise,resolve};}
async function controlsFixture(){
  const listeners=new Map(),pending=[];const state={workspace:{can_write:true},retail:{filter:'all',search:'',requestedId:'W1',view:'inbox'}};
  const form={id:'retail-scenario',reportValidity:()=>true,elements:{signal:{value:'unknown'},max_loss:{value:'5'},test_days:{value:'14'},cost_change_pct:{value:'0'},candidate_price:{value:'122'},price_range:{value:'122'}},querySelector:()=>({textContent:''})};
  const plan={disabled:false,textContent:''},status={textContent:''},view={innerHTML:'',querySelectorAll:()=>[]};
  const root={isConnected:true,innerHTML:'',contains:()=>true,addEventListener:(key,fn)=>listeners.set(key,fn),
    querySelector:key=>({'#retail-scenario':form,'[data-retail="plan"]':plan,'#retail-analysis-status':status,'#retail-result':view,'#retail-cost-output':{textContent:''},'h1':null}[key]||null)};
  let count=0;const api=async path=>{if(path.endsWith('/workspace'))return {rows:[],counts:{products:1}};if(count++===0)return item();const next=deferred();pending.push(next);return next.promise;};
  const previous=globalThis.window;globalThis.window={scrollTo(){}};
  await bindRetail(state,{querySelector:()=>root},api,()=>{},()=>{});
  return {state,root,form,plan,view,listeners,pending,cleanup(){disposeRetail(state);globalThis.window=previous;}};
}
test('newer scenario replies win; stale calculations cannot overwrite them',async()=>{
  const f=await controlsFixture();try{
    const first=f.listeners.get('submit')({preventDefault(){},target:f.form});
    f.form.elements.max_loss.value='8';const second=f.listeners.get('submit')({preventDefault(){},target:f.form});
    assert.equal(f.plan.disabled,true);
    f.pending[1].resolve(item('Latest decision'));await second;
    f.pending[0].resolve(item('Obsolete decision'));await first;
    assert.match(f.view.innerHTML,/Latest decision/);assert.doesNotMatch(f.view.innerHTML,/Obsolete decision/);
    assert.equal(f.state.retail.request.max_loss,'8');assert.equal(f.plan.disabled,false);
  }finally{f.cleanup();}
});
test('a detached workspace discards a late scenario and leaves the saved analysis unchanged',async()=>{
  const f=await controlsFixture();try{
    const work=f.listeners.get('submit')({preventDefault(){},target:f.form});
    f.root.isConnected=false;f.pending[0].resolve(item('Must not display'));await work;
    assert.equal(f.state.retail.analysis.report.title,'Try a small test');assert.equal(f.view.innerHTML,'');
  }finally{f.cleanup();}
});
test('a hypothetical supplier result leaves plan saving disabled',async()=>{
  const f=await controlsFixture();try{
    f.form.elements.cost_change_pct.value='10';const work=f.listeners.get('submit')({preventDefault(){},target:f.form});
    f.pending[0].resolve({...item(),simulation:true});await work;
    assert.equal(f.plan.disabled,true);assert.match(f.view.innerHTML,/hypothetical/);
  }finally{f.cleanup();}
});

test('a slow file read cannot overwrite a more recently selected import',async()=>{
  const state={workspace:{can_write:true}},events=new Map(),old=deferred(),fresh=deferred(),requests=[];
  const root={isConnected:true,innerHTML:'',querySelector:()=>({replaceChildren(){}}),addEventListener:(k,fn)=>events.set(k,fn)};
  const api=async(path,{body})=>{requests.push(body.csv_text);return {headers:['sku'],fields:[{key:'sku',label:'SKU',required:true}],row_count:1,sample:[]};};
  bindRetailImport(state,{querySelector:()=>root},api,()=>{},()=>{});
  const select=(name,read)=>events.get('change')({target:{id:'retail-csv-file',files:[{name,size:100,text:()=>read.promise}]}});
  const one=select('old.csv',old),two=select('new.csv',fresh);
  fresh.resolve('sku\nNEW');await two;old.resolve('sku\nOLD');await one;
  assert.deepEqual(requests,['sku\nNEW']);assert.equal(state.retailImport.filename,'new.csv');
});
