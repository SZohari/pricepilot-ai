import {esc,money} from './utils.js';

export const prompts=[
  ['Why this next step?','Why is this the next step for this product?',null],
  ['Could a 5% discount work?','What sales would a discount need to protect contribution?',-5],
  ['What are we missing?','What evidence is missing about customers, demand and retention?',null],
  ['What if my supplier charges more?','How does a higher replacement cost affect contribution?',null,10]
];

export function assistantContext(S,id){
  const entry=S.entries.find(e=>e.product.product_id===id);
  if(!entry)return null;
  const journey=S.journey?.id===id?S.journey:null;
  const request={product_id:id,expected_version:entry.version,...structuredClone(journey?.request||{})};
  // A draft must keep the version it was created against: the server rejects stale drafts.
  if(journey?.dirty&&journey.draft){request.product_draft=structuredClone(journey.draft);request.expected_version=journey.item.version;}
  return request;
}

export function assistantPage(){return `<section class="assistant" id="assistant-root" aria-labelledby="assistant-title"><p role="status">Opening your pricing assistant…</p></section>`;}
export function disposeAssistant(S){S.disposeAssistant?.();S.disposeAssistant=null;}

export function answerHTML(result){
  const c=result.calculation,d=result.decision;
  const requirement=c.required_units===null?'Not available':`${c.required_units} sales`;
  return `<div class="assistant-answer-head"><span class="assistant-label">${result.mode==='rag'?'AI EXPLANATION · CHECK THE SOURCES':'SOURCE-BASED ANSWER'}</span><span>${esc(result.product_name)} · ${esc(result.as_of)}</span></div>
    ${!result.matched?'<p class="assistant-empty">I could not find relevant evidence for that question. Try asking about this product’s costs, customers or competitor offers. The scenario calculation below is shown separately.</p>':''}
    ${result.fallback?`<p class="assistant-notice">${esc(result.fallback)}</p>`:''}
    ${result.explanation?`<div class="assistant-generated"><p>${esc(result.explanation.explanation)}</p><small>AI interpretation · check against the sources. Context sources: ${result.explanation.source_ids.map(id=>`<a href="#source-${esc(id)}" data-source-link="${esc(id)}">${esc(id)}</a>`).join(', ')}</small></div>`:''}
    ${!result.explanation&&result.sources.length?`<div class="assistant-generated"><span class="assistant-label">RELEVANT EXCERPT</span><p dir="auto">${esc(result.sources[0].text)}</p><small>${esc(result.sources[0].title)} · ${esc(result.sources[0].provenance)}</small></div>`:''}
    <section class="assistant-decision"><span class="assistant-label">PRICING ENGINE · CURRENT SCENARIO</span><h2>${esc(d.title)}</h2><p>${esc(d.why)}</p>
    <div class="assistant-comparison"><div><span>Total customer price</span><p>${money(c.current_price)} <b>→ ${money(c.candidate_price)}</b></p></div><div><span>Left per sale, before fixed costs</span><p>${money(c.current_contribution)} <b>→ ${money(c.candidate_contribution)}</b></p></div></div>
    <div class="assistant-requirement"><strong>${esc(requirement)}</strong><p>${c.required_units===null?'The engine cannot establish a useful sales requirement for this scenario.':`needed over ${c.test_days} days to preserve contribution and the sales limit. Recent pace: ${esc(c.baseline_units)} sales; stock: ${c.capacity}.`} <b>This is a requirement, not a forecast.</b></p></div>
    ${result.blockers.length?`<ul class="assistant-blockers">${result.blockers.map(b=>`<li>${esc(b)}</li>`).join('')}</ul>`:''}
    <p class="assistant-next"><span>Next step</span>${esc(d.next_step)}</p></section>
    ${result.sources.length?`<section class="assistant-sources"><h3>What the answer is based on</h3><p>These excerpts match your question. Owner notes remain claims to check.</p>${result.sources.map(s=>`<details id="source-${esc(s.id)}" ${s.id.startsWith('note-')?'open':''}><summary>${esc(s.title)}<small>${esc(s.provenance)}</small></summary><p dir="auto">${esc(s.text)}</p><small>Source ${esc(s.id)} · scenario as of ${esc(s.as_of)}</small></details>`).join('')}</section>`:''}
    <p class="assistant-footnote">${result.origin==='demo'?'Simulated business data. ':''}${result.draft?'Unsaved input preview. ':''}${esc(result.scenario_notice)} Nothing has been saved or published.</p>`;
}

export async function bindAssistant(S,main,api,toast){
  const root=main.querySelector('#assistant-root');if(!root)return;
  const a=S.assistant??={id:null,notes:{},question:'',mode:'evidence'};
  a.id=S.journey?.id||a.id||S.entries[0]?.product.product_id;
  if(!S.entries.some(e=>e.product.product_id===a.id))a.id=S.entries[0]?.product.product_id;
  let disposed=false,generation=0,pending=false;
  const valid=()=>!disposed&&root.isConnected;
  S.disposeAssistant=()=>{disposed=true;++generation;};
  const context=()=>assistantContext(S,a.id);
  const product=()=>context()?.product_draft||S.entries.find(e=>e.product.product_id===a.id)?.product;
  const controls=()=>root.querySelector('#assistant-form');
  const status=text=>{if(valid())root.querySelector('#assistant-status').textContent=text;};
  function draw(){
    const ctx=context(),p=product();
    if(!p){root.innerHTML='<h1>No products yet</h1><p>Import a product before asking about its pricing.</p><a href="#onboarding">Import products →</a>';return;}
    const note=a.notes[a.id]||{title:'Customer and shop context',text:''};
    root.innerHTML=`<div class="assistant-top"><a href="#shop/${(S.journey?.step??0)+1}">← Back to pricing setup</a><span>${p.data_origin==='demo'?'WATCH SHOP DEMO':'YOUR PRODUCT'} · ${a.capabilities?.rag_configured?'AI + SOURCES':'NO MODEL REQUIRED'}</span></div>
      <header class="assistant-intro"><div class="assistant-label">ASK PRICEPILOT</div><h1 id="assistant-title">A question.<br><em>A clearer next move.</em></h1><p>Bring your question to the numbers and the knowledge behind them.</p></header>
      <div class="assistant-layout"><div class="assistant-inputs"><form id="assistant-form">
        <label class="field"><span>Your product</span><select name="product">${S.entries.map(e=>`<option value="${esc(e.product.product_id)}" ${e.product.product_id===a.id?'selected':''}>${esc(e.product.name)}</option>`).join('')}</select></label>
        ${ctx.product_draft?'<p class="assistant-notice">Includes your unsaved cost preview from the pricing setup.</p>':''}
        <div class="assistant-presets">${prompts.map(([label],i)=>`<button type="button" data-prompt="${i}">${esc(label)}</button>`).join('')}</div>
        <label class="field"><span>What would you like to understand?</span><textarea name="question" rows="3" minlength="3" maxlength="600" required placeholder="For example: what would make this discount a bad idea?" dir="auto">${esc(a.question)}</textarea></label>
        <details class="assistant-assumptions" open><summary>The scenario to check</summary><div class="assistant-control-pair"><label class="field"><span>Candidate total price · EUR</span><input name="candidate" type="number" min="0.01" max="9999999999" step="0.01" required value="${esc(ctx.candidate_price??p.current_price_gross)}"></label><label class="field"><span>Replacement cost change · %</span><input name="cost_change" type="number" min="-20" max="50" step="1" required value="${esc(ctx.cost_change_pct??0)}"></label></div><p>Includes VAT and customer delivery charges. The engine uses these controls, not numbers typed into a question.</p></details>
        <details class="assistant-notes" ${note.text?'open':''}><summary>Add what your shop knows <span>optional</span></summary><p>Paste observations or a short note. This text supports an answer; it does not change costs or approve a price test.</p><label class="field"><span>Note title</span><input name="note_title" maxlength="100" value="${esc(note.title)}"></label><label class="field"><span>Background note</span><textarea name="note" rows="5" maxlength="6000" dir="auto" placeholder="Customers ask whether the watch works with their phone. We have not yet recorded how often this stops a purchase.">${esc(note.text)}</textarea></label><label class="assistant-file">Or read a .txt / .md file<input name="note_file" type="file" accept=".txt,.md,text/plain,text/markdown"></label><p>Kept only while this workspace is open. Sent to this server when you ask; not saved to a database. No customer names or personal details are needed.</p></details>
        ${a.capabilities?.rag_configured?'<label class="field"><span>Answer mode</span><select name="mode"><option value="evidence">Source excerpts + calculations</option><option value="rag">AI explanation + sources + calculations</option></select></label><p class="assistant-privacy">The model runs on this server. It receives your question and relevant excerpts; nothing is sent to a cloud AI provider.</p>':'<p class="assistant-mode"><i></i>Evidence mode · no generative model connected</p>'}
        <button class="button primary assistant-submit" type="submit">Find a clearer next step <span>↗</span></button><p id="assistant-status" role="status" aria-live="polite"></p>
      </form></div><div class="assistant-output" id="assistant-output" aria-live="polite"><div class="assistant-placeholder"><div class="assistant-orbit">↗</div><h2>Let’s connect the dots.</h2><p>Choose a question on the left. You’ll see the business trade-off, the calculation and the source behind it.</p><ol><li>Check the current inputs</li><li>Calculate the price scenario</li><li>Find relevant evidence</li><li>Make the next step clear</li></ol><small>Read-only advice. Your pricing setup still controls every approval.</small></div></div></div>`;
    if(a.capabilities?.rag_configured)controls().elements.mode.value=a.mode;
  }
  function invalidate(){
    ++generation;
    const output=root.querySelector('#assistant-output');
    output.innerHTML='<div class="assistant-placeholder"><h2>Ready for a fresh answer.</h2><p>Your inputs changed. Ask again to check this scenario.</p></div>';
  }
  function remember(){
    const f=controls();a.question=f.elements.question.value;
    a.notes[a.id]={title:f.elements.note_title.value,text:f.elements.note.value};
    a.mode=f.elements.mode?.value||'evidence';
  }
  try{a.capabilities=await api('/api/v1/assistant/capabilities');if(!valid())return;if(!a.modeChosen)a.mode=a.capabilities.default_mode||'evidence';}
  catch{if(!valid())return;a.capabilities={rag_configured:false};a.mode='evidence';}
  draw();if(!a.id)return;
  root.addEventListener('input',e=>{if(e.target.name==='note_file')return;remember();invalidate();});
  root.addEventListener('change',async e=>{
    if(e.target.name==='mode')a.modeChosen=true;
    if(e.target.name==='product'){a.id=e.target.value;++generation;draw();controls().querySelector('button[type=submit]').disabled=pending;}
    if(e.target.name==='note_file'){
      const file=e.target.files?.[0];if(!file)return;
      const id=a.id,token=++generation;
      if(!/\.(txt|md)$/i.test(file.name)||file.size>24000){status('Choose a .txt or .md file under 24 KB.');return;}
      try{const text=await file.text();if(!valid()||token!==generation||id!==a.id)return;
        if(text.length>6000||text.includes('\u0000')){status('Use a text excerpt of at most 6,000 characters.');return;}
        controls().elements.note.value=text;controls().elements.note_title.value=file.name.slice(0,100);remember();invalidate();status('Note loaded. Ask again to include it.');
      }catch{status('Could not read this file. Paste the note instead.');}
    }
  });
  root.addEventListener('click',e=>{
    const source=e.target.closest('[data-source-link]');if(source){e.preventDefault();const target=root.querySelector(`#source-${source.dataset.sourceLink}`);if(target){target.open=true;target.scrollIntoView({behavior:'smooth',block:'center'});}return;}
    const button=e.target.closest('[data-prompt]');if(!button)return;
    const [,question,change,cost]=prompts[Number(button.dataset.prompt)],f=controls();
    f.elements.question.value=question;
    if(change!==null)f.elements.candidate.value=(Number(product().current_price_gross)*(1+change/100)).toFixed(2);
    if(cost!==undefined)f.elements.cost_change.value=String(cost);
    remember();invalidate();f.elements.question.focus();
  });
  root.addEventListener('submit',async e=>{
    if(e.target.id!=='assistant-form')return;e.preventDefault();if(pending)return;
    const f=controls();if(!f.reportValidity())return;remember();
    const note=a.notes[a.id],documents=note.text.trim()?[{title:note.title,text:note.text}]:[];
    if(documents.length&&(note.title.trim().length<2||note.text.trim().length<10)){status('Give your note a title and at least 10 characters of context.');return;}
    const body={question:a.question,mode:a.mode,documents,analysis:{...context(),candidate_price:Number(f.elements.candidate.value).toFixed(2),cost_change_pct:f.elements.cost_change.value}};
    const token=++generation;pending=true;f.querySelector('button[type=submit]').disabled=true;
    status(a.mode==='rag'?'Checking the scenario and asking the model… This may take a moment.':'Checking the scenario and finding relevant sources…');
    root.querySelector('#assistant-output').setAttribute('aria-busy','true');
    root.querySelector('#assistant-output').innerHTML='<div class="assistant-placeholder"><h2>Following the evidence…</h2><p>Checking this scenario and finding the sources behind the answer.</p></div>';
    try{const result=await api('/api/v1/assistant/ask',{method:'POST',body});if(!valid()||token!==generation)return;
      root.querySelector('#assistant-output').innerHTML=answerHTML(result);status('Answer ready. No price has been changed.');
    }catch(error){if(valid()&&token===generation){status(error.message);toast(error.message);}}
    finally{pending=false;if(valid()){controls().querySelector('button[type=submit]').disabled=false;root.querySelector('#assistant-output').setAttribute('aria-busy','false');if(token!==generation)status('Inputs changed while the answer was loading. Ask again.');}}
  });
}
