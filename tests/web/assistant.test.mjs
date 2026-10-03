import test from 'node:test';
import assert from 'node:assert/strict';
import {assistantContext,answerHTML,bindAssistant,disposeAssistant} from '../../src/web/static/assistant.js';

const state=()=>({workspace:{can_write:true},entries:[
  {product:{product_id:'W1',name:'Watch one',data_origin:'demo',current_price_gross:'200'},version:2},
  {product:{product_id:'W2',name:'Watch two',data_origin:'merchant',current_price_gross:'100'},version:1}
]});
const response=()=>({product_id:'W1',product_name:'Watch one',as_of:'2026-09-26',mode:'evidence',matched:true,origin:'demo',draft:false,
  sources:[{id:'costs',title:'Costs',text:'Test source',provenance:'Simulated'}],blockers:[],scenario_notice:'Uses the explicit controls.',
  decision:{title:'Review this price',why:'Check contribution',next_step:'Run a bounded test'},
  calculation:{current_price:'200',candidate_price:'190',current_contribution:'40',candidate_contribution:'32',required_units:13,baseline_units:10,test_days:14,capacity:20}});
const deferred=()=>{let resolve;const promise=new Promise(r=>resolve=r);return {resolve,promise};};

test('inherits the active customer context and draft version without mutating the journey',()=>{
  const S=state();S.journey={id:'W1',dirty:true,item:{version:1},draft:{product_id:'W1',replacement_cost_net:'70'},request:{candidate_price:'180',knowledge_notes:[{statement:'Check customer trust'}]}};
  const context=assistantContext(S,'W1');
  assert.equal(context.expected_version,1);assert.equal(context.candidate_price,'180');
  context.knowledge_notes[0].statement='changed';assert.equal(S.journey.request.knowledge_notes[0].statement,'Check customer trust');
  assert.equal(assistantContext(S,'W2').product_draft,undefined);
  assert.equal(assistantContext(S,'missing'),null);
});

test('notes and model prose cannot inject HTML; absence of evidence and forecasts stays explicit',()=>{
  const r=response();r.sources[0].text='<img src=x onerror=alert(1)>';r.decision.title='<script>bad</script>';
  let html=answerHTML(r);assert.ok(!html.includes('<img'));assert.ok(!html.includes('<script>'));
  assert.match(html,/not a forecast/);assert.match(html,/Simulated business data/);
  r.matched=false;r.sources=[];r.calculation.required_units=null;
  html=answerHTML(r);assert.match(html,/could not find relevant evidence/);assert.match(html,/Not available/);
  r.explanation={explanation:'<svg onload=bad()>',source_ids:['costs']};
  assert.ok(!answerHTML(r).includes('<svg'));
});

test('AI-selected excerpts are labelled as quotations, with their provenance',()=>{
  const r=response();r.mode='rag';r.sources[0].provenance='Unverified background note';
  r.explanation={explanation:'Test source',source_ids:['costs'],style:'selected_excerpt'};
  const html=answerHTML(r);
  assert.match(html,/AI-SELECTED EVIDENCE/);assert.match(html,/Unverified background note/);
  assert.match(html,/did not write it/);assert.ok(!html.includes('AI interpretation'));
});

// Event fixture checks input/state races, not browser layout or accessibility rendering.
async function fixture(){
  const S=state(),events=new Map(),elements=new Map(),requests=[];let html='',handler=null;
  const root={isConnected:true,addEventListener:(name,fn)=>events.set(name,fn),querySelector:s=>elements.get(s)};
  Object.defineProperty(root,'innerHTML',{get:()=>html,set:value=>{
    html=value;elements.clear();const form={elements:{},reportValidity:()=>true,querySelector:()=>submit},submit={disabled:false};
    for(const m of value.matchAll(/<input\b([^>]+)>/g)){const name=m[1].match(/name="([^"]+)"/),v=m[1].match(/value="([^"]*)"/);if(name)form.elements[name[1]]={name:name[1],value:v?.[1]||'',focus(){}};}
    for(const m of value.matchAll(/<textarea\b[^>]*name="([^"]+)"[^>]*>([\s\S]*?)<\/textarea>/g))form.elements[m[1]]={name:m[1],value:m[2],focus(){}};
    form.elements.product={name:'product',value:S.assistant.id};
    elements.set('#assistant-form',form);elements.set('#assistant-status',{textContent:''});elements.set('#assistant-output',{innerHTML:'',setAttribute(){}});
  }});
  const api=async(path,options)=>{if(path.endsWith('capabilities'))return {rag_configured:false};requests.push(structuredClone(options.body));return handler?handler():response();};
  await bindAssistant(S,{querySelector:()=>root},api,()=>{});
  return {S,root,requests,get form(){return elements.get('#assistant-form');},get output(){return elements.get('#assistant-output').innerHTML;},get status(){return elements.get('#assistant-status').textContent;},
    input(name,value){const e=this.form.elements[name];e.value=value;events.get('input')({target:e});},
    change(name,value){const e=this.form.elements[name];e.value=value;return events.get('change')({target:e});},
    preset(index){return events.get('click')({target:{closest:selector=>selector==='[data-prompt]'?{dataset:{prompt:String(index)}}:null}});},
    ask(){return events.get('submit')({target:{id:'assistant-form'},preventDefault(){}});},setHandler(h){handler=h;}};
}

test('the discount shortcut sends the changed scenario and does not save a product',async()=>{
  const f=await fixture();f.preset(1);await f.ask();
  assert.equal(f.requests.length,1);assert.equal(f.requests[0].analysis.candidate_price,'190.00');
  assert.match(f.output,/Review this price/);
  f.input('candidate','180');assert.ok(!f.output.includes('Review this price'));await f.ask();
  assert.equal(f.requests.at(-1).analysis.candidate_price,'180.00');
});

test('a late reply cannot overwrite changed assumptions or detached views',async()=>{
  const f=await fixture(),d=deferred();f.input('question','What about costs?');f.setHandler(()=>d.promise);
  const work=f.ask();f.input('candidate','170');d.resolve(response());await work;
  assert.ok(!f.output.includes('Review this price'));assert.match(f.status,/Inputs changed/);
  const later=deferred();f.setHandler(()=>later.promise);const detached=f.ask();disposeAssistant(f.S);later.resolve(response());await detached;
  assert.ok(!f.output.includes('Review this price'));
});

test('background notes stay with their product and model failures leave a usable retry',async()=>{
  const f=await fixture();f.input('question','What about compatibility?');f.input('note','Customers ask about compatibility.');
  await f.change('product','W2');assert.equal(f.form.elements.note.value,'');
  await f.ask();assert.deepEqual(f.requests.at(-1).documents,[]);assert.equal(f.requests.at(-1).analysis.product_id,'W2');
  await f.change('product','W1');assert.equal(f.form.elements.note.value,'Customers ask about compatibility.');
  f.setHandler(()=>{throw Error('Please retry');});await f.ask();assert.equal(f.form.querySelector().disabled,false);assert.equal(f.status,'Please retry');
});
