import test from 'node:test';
import assert from 'node:assert/strict';
import {newJourney,progressHTML,bindJourney,disposeJourney,decisionInsight,costInsight} from '../../src/web/static/journey.js';

function item(){
  const details={variant:'44 mm new',gtin:'',purchase_cost_net:'45',shipping_cost_net:'3',packaging_cost_net:'1',returns_allowance_net:'1',customer_shipping_gross:'4.90',costs_checked_on:'2026-09-26',sales_period_end:'2026-09-25',baseline_representative:true,cost_scope_confirmed:true,signal:'unknown'};
  return {product:{product_id:'W1',name:'Watch',brand:'Brand',data_origin:'demo',current_price_gross:'119',replacement_cost_net:'50',variable_cost_net:'5',vat_rate:'.19',fee_rate:'.02',fee_basis:'gross',minimum_margin:'.10',target_margin:'.25',inventory:100,sales_30d:30,sales_7d:7,retail:details},
    version:1,details,draft:false,waterfall:[],economics:{current_contribution:'42.62',candidate_item_price_gross:'117.10',customer_shipping_gross:'4.90'},
    report:{title:'Try a small test',why:'Check the trade-off',next_step:'Record the outcome',action:'price_test',can_start_test:true,test_price_gross:'122',as_of:'2026-09-26',fingerprint:'one',market_usable:false,evidence:[],input:{signal:'unknown',positioning:'comparable',test_days:14},economics:{minimum_price_gross:'74.70',minimum_units_with_volume_guardrail:14}},
    insight:{current_price:'119',considered_price:'122',current_per_sale:'42.62',considered_per_sale:'45.08',message:'More per sale, with a sales limit.',required_units:14,baseline_units:'14.0',extra_units:0}};
}
const deferred=()=>{let resolve,reject;const promise=new Promise((a,b)=>{resolve=a;reject=b;});return {promise,resolve,reject};};
const attrs=text=>Object.fromEntries([...text.matchAll(/([\w-]+)="([^"]*)"/g)].map(m=>[m[1],m[2]]));

// Lightweight form/event fixture: no browser, layout or rendering assertion.
async function fixture({merchant=false,sources=[],followup=null}={}){
  const original={window:globalThis.window,FormData:globalThis.FormData,location:globalThis.location};
  globalThis.window={scrollTo(){}};globalThis.location={hash:''};
  globalThis.FormData=class {constructor(form){this.form=form;}*[Symbol.iterator](){for(const [k,e] of Object.entries(this.form.elements)){if(e.type!=='checkbox'||e.checked)yield [k,e.value];}}};
  const events=new Map(),requests=[],messages=[],elements=new Map();let html='',handler=null;
  const state={workspace:{can_write:true},entries:[],sources:{configured:sources.length,sources,can_configure:true},journeyFollowup:followup};
  const root={isConnected:true,contains:()=>true,setAttribute(){},addEventListener:(k,f)=>events.set(k,f),querySelector:s=>elements.get(s)||null,
    querySelectorAll:s=>s.includes('[data-journey=')?[...elements.values()].filter(x=>x.dataset?.journey&&['next','confirm-costs','save'].includes(x.dataset.journey)):[]};
  Object.defineProperty(root,'innerHTML',{get:()=>html,set(value){html=value;elements.clear();
    for(const selector of ['.journey-error','.journey-status','.journey-steps','#journey-cost-insight','#journey-market-insight','#journey-market-offers','#journey-decision-insight'])elements.set(selector,{textContent:'',innerHTML:'',setAttribute(){}});
    for(const m of value.matchAll(/<form id="([^"]+)"[^>]*>([\s\S]*?)<\/form>/g)){
      const error={textContent:''};const form={id:m[1],elements:{},checkValidity:()=>true,reportValidity:()=>true,querySelector:s=>s==='.journey-error'?error:{disabled:false,isConnected:true},querySelectorAll:()=>[]};
      for(const i of m[2].matchAll(/<input\b([^>]+)>/g)){const a=attrs(i[1]);if(a.name)form.elements[a.name]={...a,value:a.value||'',checked:/\schecked\b/.test(i[1]),setAttribute(){},removeAttribute(){},closest:()=>form};}
      for(const i of m[2].matchAll(/<textarea\b([^>]+)>([\s\S]*?)<\/textarea>/g)){const a=attrs(i[1]);form.elements[a.name]={...a,value:i[2],closest:()=>form};}
      for(const i of m[2].matchAll(/<select\b([^>]+)>([\s\S]*?)<\/select>/g)){const a=attrs(i[1]),options=[...i[2].matchAll(/<option([^>]+)>/g)],selected=options.find(x=>/\sselected\b/.test(x[1]))||options[0];form.elements[a.name]={name:a.name,value:attrs(selected[1]).value,closest:()=>form};}
      elements.set('#'+form.id,form);
    }
    for(const m of value.matchAll(/<button\b([^>]+)>/g)){const a=attrs(m[1]);if(a['data-journey']){const b={dataset:{journey:a['data-journey'],step:a['data-step'],goal:a['data-goal'],index:a['data-index']},disabled:/\sdisabled\b/.test(m[1]),isConnected:true};elements.set(`[data-journey="${b.dataset.journey}"]${a['data-step']??a['data-goal']??''}`,b);}}
  }});
  const api=async(path,options={})=>{requests.push({path,...structuredClone(options)});if(handler)return handler(path,options);if(path==='/api/sources')return state.sources;if(path.endsWith('/workspace'))return {rows:[{product_id:'W1',name:'Watch',origin:merchant?'merchant':'demo',version:1}]};if(path.endsWith('/product'))return {product:options.body.product,version:2};if(path.endsWith('/plans'))return {id:'plan-1'};const result=item();if(merchant)result.product.data_origin='merchant';if(options.body?.knowledge_notes)result.report.discovery={open_questions:options.body.knowledge_notes.map(n=>({...n,collect:'Ask about the concern',interpret:'No score inferred'}))};if(options.body?.product_draft){result.draft=true;result.product=options.body.product_draft;}return result;};
  if(merchant){state.journey=newJourney();state.journey.mode='merchant';}
  const main={querySelector:()=>root};await bindJourney(state,main,api,m=>messages.push(m));
  return {state,root,main,api,events,requests,messages,get:selector=>elements.get(selector),setHandler:h=>{handler=h;},
    click:async(action,extra={})=>{const b=elements.get(`[data-journey="${action}"]${extra.step??extra.goal??''}`)||{dataset:{journey:action,...extra},disabled:false};return events.get('click')({preventDefault(){},target:{closest:()=>b}});},
    input:(form,name,value)=>{const f=elements.get('#'+form),e=f.elements[name];e.value=value;events.get('input')({target:e});},
    submit:id=>events.get('submit')({preventDefault(){},target:elements.get('#'+id)}),
    cleanup(){disposeJourney(state);Object.assign(globalThis,original);}};
}

test('future stages are locked and product choice starts at costs, never the final advice',async()=>{
  const f=await fixture();try{
    assert.equal((progressHTML(newJourney()).match(/ disabled/g)||[]).length,4);
    await f.click('step',{step:'4'});assert.equal(f.state.journey.step,0);
    await f.click('next');assert.equal(f.state.journey.step,1);assert.match(f.root.innerHTML,/Make sure each sale supports/);
    assert.doesNotMatch(f.root.innerHTML,/Save my plan/);
  }finally{f.cleanup();}
});

test('cost edits preview without a write, invalidate later stages and clear a price baseline',async()=>{
  const f=await fixture();try{
    await f.click('next');f.state.journey.unlocked=4;
    f.input('journey-cost-form','replacement_cost_net','60');await f.submit('journey-cost-form');
    assert.equal(f.requests.at(-1).body.product_draft.replacement_cost_net,'60');
    assert.equal(f.requests.at(-1).body.expected_version,1);assert.equal(f.state.journey.unlocked,1);
    assert.equal(f.requests.filter(x=>x.method==='PUT').length,0);
    f.input('journey-cost-form','item_price_gross','120');await f.submit('journey-cost-form');
    assert.equal(f.requests.at(-1).body.product_draft.retail.baseline_representative,false);
    await f.click('step',{step:'4'});assert.equal(f.state.journey.step,1);
  }finally{f.cleanup();}
});

test('cost confirmation is versioned, prevents navigation races and proceeds to market',async()=>{
  const f=await fixture();try{
    await f.click('next');f.input('journey-cost-form','replacement_cost_net','60');await f.submit('journey-cost-form');
    const save=deferred();f.setHandler((path,options)=>path.endsWith('/product')?save.promise:Promise.resolve({...item(),version:2,product:{...item().product,replacement_cost_net:'60'}}));
    const confirmation=f.click('confirm-costs');assert.equal(f.root.inert,true);
    await f.click('back');assert.equal(f.state.journey.step,1);
    save.resolve({product:{...item().product,replacement_cost_net:'60'},version:2});await confirmation;
    assert.equal(f.state.journey.step,2);assert.equal(f.state.journey.item.version,2);assert.equal(f.root.inert,false);
    assert.equal(f.state.journey.dirty,false);assert.equal(f.requests.at(-1).body.product_draft,undefined);
    assert.equal(f.requests.at(-1).body.expected_version,2);
  }finally{f.cleanup();}
});

test('candidate inputs are transmitted together and late replies cannot overwrite new advice',async()=>{
  const f=await fixture();try{
    await f.click('next');await f.click('confirm-costs');await f.click('next');assert.equal(f.state.journey.step,3);
    const older=deferred(),newer=deferred();let calls=0;f.setHandler(()=>++calls===1?older.promise:newer.promise);
    f.input('journey-price-form','candidate_price','125');const one=f.submit('journey-price-form');
    f.input('journey-price-form','price_range','121');f.input('journey-price-form','max_loss','0');f.input('journey-price-form','test_days','7');const two=f.submit('journey-price-form');
    const body=f.requests.at(-1).body;assert.equal(body.candidate_price,'121');assert.equal(body.max_loss,'0');assert.equal(body.test_days,7);
    const fresh=item();fresh.report.title='Fresh result';newer.resolve(fresh);await two;older.resolve(item());await one;
    assert.match(f.get('#journey-decision-insight').innerHTML,/Fresh result/);
    assert.equal(f.state.journey.item.report.title,'Fresh result');
  }finally{f.cleanup();}
});

test('failed calculations keep the next stage locked and successful retry restores it',async()=>{
  const f=await fixture();try{
    await f.click('next');await f.click('confirm-costs');
    f.setHandler(()=>Promise.reject(Error('Connection lost')));await f.submit('journey-market-form');
    assert.equal(f.get('[data-journey="next"]').disabled,true);
    assert.match(f.get('#journey-market-form').querySelector('.journey-error').textContent,/Connection lost/);
    f.setHandler(()=>Promise.resolve(item()));await f.submit('journey-market-form');
    assert.equal(f.get('[data-journey="next"]').disabled,false);
  }finally{f.cleanup();}
});

test('saved plans use the reviewed fingerprint and resuming refreshes external market changes',async()=>{
  const f=await fixture();try{
    await f.click('next');await f.click('confirm-costs');await f.click('next');await f.click('next');await f.click('save');
    assert.equal(f.state.journey.step,4);assert.equal(f.state.journey.plan.id,'plan-1');
    assert.equal(f.requests.at(-1).body.fingerprint,'one');assert.match(f.root.innerHTML,/Automatic store publishing is not connected/);
    disposeJourney(f.state);const changed=item();changed.report.fingerprint='new-evidence';
    f.setHandler(path=>Promise.resolve(path.endsWith('/workspace')?{rows:[{product_id:'W1',version:1}]}:changed));
    await bindJourney(f.state,f.main,f.api,()=>{});
    assert.equal(f.state.journey.step,3);assert.equal(f.state.journey.plan,null);
  }finally{f.cleanup();}
});

test('insights escape external text and show a changed amount beside its original',()=>{
  const old=item(),updated=item();updated.economics.current_contribution='32.62';
  assert.match(costInsight(updated,old),/42,62.*→.*32,62/);
  updated.report.title='<script>bad</script>';updated.insight.message='<img src=x>';
  const html=decisionInsight(updated);assert.doesNotMatch(html,/<script|<img/);assert.match(html,/&lt;script/);
});

test('an owner question can become an attributed finding without losing or duplicating it',async()=>{
  const f=await fixture();try{
    await f.click('next');await f.click('confirm-costs');
    f.input('journey-knowledge-form','topic','trust');f.input('journey-knowledge-form','statement','Does the warranty cause hesitation?');
    await f.submit('journey-knowledge-form');
    assert.equal(f.state.journey.request.knowledge_notes.length,1);
    assert.equal(f.state.journey.request.knowledge_notes[0].resolve_first,true);
    await f.click('knowledge-edit',{index:'0'});
    assert.equal(f.get('#journey-knowledge-form').elements.statement.value,'Does the warranty cause hesitation?');
    f.input('journey-knowledge-form','basis','observed');f.input('journey-knowledge-form','evidence_note','Three of eight recorded enquiries mentioned warranty.');
    f.get('#journey-knowledge-form').elements.resolve_first.checked=false;
    await f.submit('journey-knowledge-form');
    const notes=f.requests.at(-1).body.knowledge_notes;
    assert.equal(notes.length,1);assert.equal(notes[0].basis,'observed');assert.equal(notes[0].resolve_first,false);
    assert.equal(f.state.journey.unlocked,2);assert.equal(f.state.journey.editingKnowledge,null);
    f.setHandler(()=>Promise.reject(Error('Connection lost')));
    await f.click('knowledge-toggle',{index:'0'});
    assert.equal(f.state.journey.request.knowledge_notes[0].resolve_first,false);
    assert.equal(f.get('[data-journey="next"]').disabled,false);
  }finally{f.cleanup();}
});

test('a revised linked plan restores its questions but requires current costs to be reviewed',async()=>{
  const note={topic:'trust',statement:'Check warranty wording',basis:'question',evidence_note:'',checked_on:'2026-09-26',resolve_first:true};
  const f=await fixture({followup:{linked_product_id:'W1',knowledge_notes:[note],signal:'unknown',positioning:'comparable',max_volume_loss_pct:'5',test_days:14}});
  try{
    assert.equal(f.state.journey.step,1);assert.equal(f.state.journey.unlocked,1);
    assert.deepEqual(f.state.journey.request.knowledge_notes,[note]);assert.equal(f.state.journeyFollowup,null);
    assert.equal(f.state.journey.request.candidate_price,null);
  }finally{f.cleanup();}
});

test('configured merchant sources refresh on entering market, only for that SKU, with bounded re-entry',async()=>{
  const f=await fixture({merchant:true,sources:[{product_id:'W1'},{product_id:'UNRELATED'}]});try{
    f.setHandler((path,options)=>{
      if(path==='/api/sources/refresh-product')return {results:[{seller:'Shop',status:'failed',message:'Unsupported page'}]};
      if(path.endsWith('/product'))return {product:options.body.product,version:2};
      const result=item();result.product.data_origin='merchant';result.version=2;return result;
    });
    await f.click('next');await f.click('confirm-costs');
    const collects=()=>f.requests.filter(r=>r.path==='/api/sources/refresh-product');
    assert.equal(f.state.journey.sourceCount,1);assert.equal(collects().length,1);
    assert.deepEqual(collects()[0].body,{product_id:'W1'});
    assert.match(f.root.innerHTML,/Not updated: Unsupported page/);assert.equal(f.root.inert,false);
    await f.click('next');await f.click('back');assert.equal(collects().length,1);
    await f.click('collect');assert.equal(collects().length,2);
  }finally{f.cleanup();}
});

test('returning from welcome resumes the reviewed stage; browser step routes stay bounded',async()=>{
  const f=await fixture();try{
    await f.click('next');await f.click('confirm-costs');await f.click('next');
    disposeJourney(f.state);await bindJourney(f.state,f.main,f.api,()=>{});
    assert.equal(f.state.journey.step,3);
    disposeJourney(f.state);f.state.journeyRouteStep=1;await bindJourney(f.state,f.main,f.api,()=>{});
    assert.equal(f.state.journey.step,1);
    f.input('journey-cost-form','replacement_cost_net','60');await f.submit('journey-cost-form');
    disposeJourney(f.state);f.state.journeyRouteStep=4;await bindJourney(f.state,f.main,f.api,()=>{});
    assert.equal(f.state.journey.step,1);assert.equal(f.state.journey.fields.replacement_cost_net,'60');
  }finally{f.cleanup();}
});

test('unconfirmed costs are described as provisional, never a complete margin assessment',()=>{
  const draft=item();draft.details.cost_scope_confirmed=false;
  assert.match(costInsight(draft),/Confirm the full cost picture first/);
  assert.match(costInsight(draft),/Based only on the entered costs/);
});
