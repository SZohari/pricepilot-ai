import {esc,money} from './utils.js';
import {priceOptions,priorities,decisionMessage} from './price-options.js';
import {download} from './intelligence.js';

const qty=n=>new Intl.NumberFormat('en-GB',{maximumFractionDigits:1}).format(n);
const span=(range,format)=>Math.abs(range.high-range.low)<.05?format(range.mid):format(range.low)+' – '+format(range.high);
const direction=n=>n>0?'increase':n<0?'decrease':'unchanged';
function stateFor(S){
  S.guide??={id:S.entries[0]?.product.product_id,goal:'balanced',sensitivity:'medium',tolerance:5};
  if(!S.entries.some(e=>e.product.product_id===S.guide.id))S.guide.id=S.entries[0]?.product.product_id;
  return S.guide;
}
export function guide(S){
  if(!S.entries.length)return '<div class="empty-state"><h1>Add a product to get started</h1><a class="button" href="#data">Open your data workspace</a></div>';
  const c=stateFor(S);
  return `<div class="guide-heading"><div><div class="eyebrow">YOUR PRICING ASSISTANT</div><h1>Choose a price with a clear trade-off.</h1><p>Start with one product. Compare sales and earnings. Decide what to test.</p></div><span class="pill">Demo store · simulated financials</span></div><div class="guide-steps" aria-label="Decision process"><span><b>1</b> Choose product & priority</span><span><b>2</b> Compare the outcomes</span><span><b>3</b> Save a review plan</span></div><section class="panel guide-controls"><label class="field"><span>Which product are you pricing?</span><select id="guide-product">${S.entries.map(({product:p})=>`<option value="${esc(p.product_id)}" ${p.product_id===c.id?'selected':''}>${esc(p.name)}</option>`).join('')}</select></label><fieldset class="guide-priorities"><legend>What matters most right now?</legend>${Object.entries(priorities).map(([id,g])=>`<button type="button" data-goal="${id}" aria-pressed="${id===c.goal}">${g.label}</button>`).join('')}</fieldset><label class="guide-tolerance"><span id="guide-tolerance-label">Maximum sales drop to consider</span><output id="guide-tolerance-value">${c.tolerance}%</output><input id="guide-tolerance" aria-labelledby="guide-tolerance-label" type="range" min="0" max="30" step="1" value="${c.tolerance}"><small>Your limit guides the choice; simulated outcomes are not guaranteed.</small></label></section><div id="guide-result"></div><details class="guide-advanced panel"><summary>Adjust assumptions or explore further</summary><div class="guide-advanced-body"><label class="field"><span>How sensitive are customers to price? (assumed)</span><select id="guide-sensitivity"><option value="low" ${c.sensitivity==='low'?'selected':''}>Lower sensitivity</option><option value="medium" ${c.sensitivity==='medium'?'selected':''}>Uncertain / medium sensitivity</option><option value="high" ${c.sensitivity==='high'?'selected':''}>Higher sensitivity</option></select></label><p>Changing this assumption immediately updates the comparison. It has not been estimated from customer behavior.</p><div class="learning-toolbar"><a class="button" href="#sandbox">Explore cost & demand changes</a><a class="button" href="#scenarios">Change cost scenario</a><a class="button" href="#learning">Inspect the separate ML evaluation</a></div></div></details>`;
}

export function resultView(p,r,result){
  const message=decisionMessage(p,result),b=result.baseline,s=result.selected;
  const ready=result.state==='ready';
  const hold=ready&&s.price===b.price;
  const why=result.state!=='ready'?message.body:hold?message.body:
    `At the middle of the assumed range, sales ${direction(s.units.mid-b.units.mid)} and contribution ${direction(s.contribution.mid-b.contribution.mid)}. Your limit allows up to ${result.tolerance}% less ${result.goal==='volume'?'total contribution':'unit sales'} across the assumed responses.`;
  const table=result.state==='ready'||result.state==='no_safe_option';
  return `<section class="guide-context"><div><span>Current price</span><strong>${money(p.current_price_gross)}</strong></div><div><span>Competitor median</span><strong>${money(r?.market_median_gross)}</strong></div><div><span>Sales · last 30 days</span><strong>${p.sales_30d} units</strong></div><div><span>Available stock</span><strong>${p.inventory} units</strong></div></section><section class="guide-advice ${ready?'':'needs-data'}"><div><span class="eyebrow">${ready?'SUGGESTED NEXT STEP · ASSUMPTION-BASED':'RESOLVE THIS FIRST'}</span><h2>${message.title}</h2><p>${esc(why)}</p>${ready?`<p class="guide-evidence">${r.quality.usable_sellers} usable seller labels · minimum price ${money(b.floor)}${result.evidenceLimited?' · Evidence or policy needs manual review':''}</p>`:''}</div>${ready?`<div class="guide-price"><small>${hold?'Continue at':'Price to review'}</small><strong>${money(s.price)}</strong><span>${s.change>=0?'+':''}${s.change.toFixed(1)}% from current price</span></div>`:''}</section>${table?`<section class="guide-comparison"><div class="guide-section-title"><div><h2>What could change over 30 days?</h2><p>Read sales and earnings together. More units do not automatically mean more earnings.</p></div></div><div class="guide-option-grid">${result.options.map(o=>`<article class="panel guide-option ${ready&&o.price===s.price?'chosen':''}"><div class="guide-option-top"><span>${esc(o.title)}</span>${ready&&o.price===s.price?'<span class="pill">Selected for your priority</span>':''}</div><h3>${money(o.price)}</h3><dl><div><dt>Possible units sold</dt><dd>${span(o.units,qty)}</dd></div><div><dt>Total contribution*</dt><dd>${span(o.contribution,money)}</dd></div><div><dt>Contribution per unit</dt><dd>${money(o.unit)}</dd></div></dl><p class="guide-option-note">${o.price<b.floor?'Below minimum margin — do not approve':o.price===b.price?'Reference for every comparison':o.price<b.price?'More units may come with lower earnings':'Higher unit earnings may come with fewer sales'}</p></article>`).join('')}</div><p class="guide-assumption"><strong>These are scenario ranges, not forecasts.</strong> They use the last 30 days’ demo sales, assumed price sensitivity ${result.band[0]}–${result.band[1]}, unchanged market demand and current stock without replenishment.${result.cost?' Replacement cost scenario: '+result.cost+'%.':''} *Contribution is sales after VAT, sourcing cost, variable costs and fees; fixed overhead and profit taxes are excluded.</p></section>`:''}<section class="panel guide-next"><div><h3>${ready?'Your next move':'What to do now'}</h3><p>${ready?(hold?'Keep monitoring comparable prices and record sales. Revisit this decision when costs, demand or competitor evidence change.':'Choose a review date for a small, monitored test. Track units and total contribution against comparable days; stop if the trade-off is unacceptable. Low sales volume may require a longer observation period.'):message.body}</p><small>${ready?'Saving exports a review plan. It does not approve or publish a shop price.':'A sales/profit estimate will appear once the missing inputs are available.'}</small></div><div class="guide-next-actions">${ready?'<button class="button primary" id="guide-save">'+message.action+' ↓</button>':result.state==='no_market'?'<a class="button primary" href="#market">Check competitor evidence →</a>':`<button class="button primary" data-action="edit" data-id="${esc(p.product_id)}">${message.action} →</button>`}<a class="button" href="#market">Review competitor sources</a></div></section>`;
}

export function bindGuide(S,root,toast){
  const target=root.querySelector('#guide-result');if(!target)return;
  const c=stateFor(S);
  const update=()=>{
    const p=S.entries.find(e=>e.product.product_id===c.id).product,r=S.recs.find(r=>r.product_id===c.id);
    const result=priceOptions(p,r,{...c,cost:Number(S.scenario.cost_change_pct)});
    target.innerHTML=resultView(p,r,result);
    if(!S.workspace.can_write)target.querySelectorAll('[data-action=edit]').forEach(b=>b.disabled=true);
    root.querySelector('#guide-tolerance-label').textContent=c.goal==='volume'?'Maximum contribution drop to consider':'Maximum sales drop to consider';
    root.querySelector('#guide-tolerance-value').textContent=c.tolerance+'%';
    root.querySelector('#guide-tolerance').value=c.tolerance;
    const save=target.querySelector('#guide-save');
    if(save)save.onclick=()=>{
      download('pricepilot-review-plan-'+p.product_id+'.json',{
        schema_version:'guided-comparison-1',created_at:new Date().toISOString(),product:p,
        evidence_policy:r,scenario:S.scenario,priority:c.goal,assumptions:{sensitivity:c.sensitivity,range:result.band,market_demand:'unchanged',replenishment:false},
        comparison:result,published:false,approved:false,
        notice:'Assumption-based review plan, not a learned forecast or causal profit claim. No price has been applied.'
      });toast('Review plan exported. No price was changed.');
    };
  };
  root.querySelector('#guide-product').onchange=e=>{c.id=e.target.value;update();};
  root.querySelectorAll('[data-goal]').forEach(button=>button.onclick=()=>{c.goal=button.dataset.goal;c.tolerance=priorities[c.goal].tolerance;root.querySelectorAll('[data-goal]').forEach(b=>b.setAttribute('aria-pressed',b.dataset.goal===c.goal));update();});
  root.querySelector('#guide-tolerance').oninput=e=>{c.tolerance=Number(e.target.value);update();};
  root.querySelector('#guide-sensitivity').onchange=e=>{c.sensitivity=e.target.value;update();};
  update();
}
