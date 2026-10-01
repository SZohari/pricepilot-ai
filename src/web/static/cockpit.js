import {esc,money} from './utils.js';

export const defaults=()=>({price:0,cost:0,market:0,demand:0,elasticity:1.5});
// A transparent sensitivity model, not an estimated causal demand function.
export function simulate(p,a=defaults()) {
  const price=Number(p.current_price_gross)*(1+a.price/100);
  const cost=Number(p.replacement_cost_net)*(1+a.cost/100);
  const net=price/(1+Number(p.vat_rate));
  const fee=Number(p.fee_rate)*(p.fee_basis==='gross'?1+Number(p.vat_rate):1);
  const unit=net*(1-fee)-cost-Number(p.variable_cost_net);
  const demand=Number(p.sales_30d)*(1+a.demand/100)*Math.pow((1+a.price/100)/(1+a.market/100),-a.elasticity);
  const units=Math.min(Number(p.inventory),demand);
  const floor=(cost+Number(p.variable_cost_net))/(1-fee-Number(p.minimum_margin))*(1+Number(p.vat_rate));
  return {price,cost,unit,units,demand,contribution:units*unit,revenue:units*price,floor,margin:unit/net,limited:demand>Number(p.inventory)};
}
const controls=[['price','Selling price',-40,40,1,'%'],['cost','Replacement cost',-30,60,1,'%'],['market','Competitor price level',-30,30,1,'%'],['demand','Underlying demand',-80,40,5,'%'],['elasticity','Price sensitivity',0,4,.1,'×']];
export function cockpit(S) {
  S.cockpit??={id:S.entries[0]?.product.product_id,a:defaults(),saved:null};
  const c=S.cockpit;
  return `<div class="page-heading"><div><div class="eyebrow">KIEZ & CO. · INTERACTIVE WORKSPACE</div><h1>Make your next pricing move.</h1><p>Move a control. See the trade-off. Compare before you decide.</p></div><a class="button" href="#example">Explore the store story →</a></div><div class="cockpit-layout"><section class="panel cockpit-controls"><div class="panel-head"><h2>Your levers</h2><span class="pill violet">Instant preview</span></div><label class="field"><span>Product to explore</span><select id="cockpit-product">${S.entries.map(({product:p})=>`<option value="${esc(p.product_id)}" ${p.product_id===c.id?'selected':''}>${esc(p.name)}</option>`).join('')}</select></label><div class="preset-row"><button class="button" data-preset="pressure">Cost pressure</button><button class="button" data-preset="sale">Sale week</button><button class="button" data-preset="age">Ageing stock</button></div>${controls.map(([key,title,min,max,step,suffix])=>`<label class="cockpit-control"><span>${title}<output id="out-${key}">${c.a[key]}${suffix}</output></span><input aria-label="${title}" data-lever="${key}" type="range" min="${min}" max="${max}" step="${step}" value="${c.a[key]}"><small>${min}${suffix}<span>${max}${suffix}</span></small></label>`).join('')}<div class="preset-row"><button class="button" id="cockpit-reset">Reset levers</button><button class="button primary" id="cockpit-save">Pin comparison</button></div><p class="small muted">Cost can represent supplier inflation or exchange-rate exposure. Demand can represent seasonality or product ageing. These are independent assumptions, not measured effects.</p></section><div id="cockpit-results" class="cockpit-results"></div></div>`;
}
export function bindCockpit(S,root) {
  if(!root.querySelector('#cockpit-results'))return;
  const c=S.cockpit;
  const update=()=>{
    const p=S.entries.find(e=>e.product.product_id===c.id)?.product;
    if(!p)return;
    const r=simulate(p,c.a),base=simulate(p),comparison=c.saved?.id===c.id?c.saved:null,b=comparison?comparison.result:base;
    const metric=(title,value,delta)=>`<article class="metric"><div class="metric-title">${title}</div><div class="metric-value">${value}</div><div class="metric-sub">${delta}</div></article>`;
    const delta=(v,old,format=money)=>`${v-old>=0?'+':''}${format(v-old)} vs ${comparison?'pinned':'baseline'}`;
    const fmt=n=>n.toFixed(1);
    const samples=[-30,-20,-10,0,10,20,30].map(price=>({change:price,...simulate(p,{...c.a,price})}));
    const scale=Math.max(1,...samples.map(x=>Math.abs(x.contribution)));
    root.querySelector('#cockpit-results').innerHTML=`<div class="cockpit-summary"><span class="eyebrow">30-DAY ASSUMPTION MODEL · NO REPLENISHMENT</span><h2>${esc(p.name)}</h2><p>Current price ${money(p.current_price_gross)} · ${p.sales_30d} historical demo sales · ${p.inventory} units available</p></div><div class="metric-grid">${metric('Scenario selling price',money(r.price),delta(r.price,b.price))}${metric('Illustrative units sold',fmt(r.units),delta(r.units,b.units,fmt))}${metric('Unit contribution',money(r.unit),delta(r.unit,b.unit))}${metric('30-day contribution',money(r.contribution),delta(r.contribution,b.contribution))}</div><div class="notice ${r.price<r.floor?'cockpit-warning':''}" role="status">${r.price<r.floor?'⚠ Below margin floor. This price fails the product’s minimum margin.':'Margin guardrail met at this scenario price.'} Floor: ${money(r.floor)} · Contribution margin: ${(r.margin*100).toFixed(1)}%. ${r.limited?'Sales are capped by available stock.':''}</div><section class="panel cockpit-chart"><div class="panel-head"><div><h2>What does a different price change?</h2><p>30-day contribution at alternative prices · same current assumptions</p></div></div>${samples.map(x=>`<button class="sensitivity-row ${x.change===c.a.price?'selected':''}" data-price="${x.change}" aria-label="Try ${x.change}% price change"><span>${x.change>0?'+':''}${x.change}% <small>${money(x.price)}</small></span><span class="sensitivity-track"><span style="width:${Math.abs(x.contribution)/scale*100}%;background:${x.contribution<0?'#f7838d':'#9c8cff'}"></span></span><strong>${money(x.contribution)}<small>${fmt(x.units)} units</small></strong></button>`).join('')}<p class="small muted">Click a row to try that price. Purple = positive contribution; pink = loss. This is a sensitivity curve, not an optimal-price recommendation.</p></section><section class="panel cockpit-explain"><h3>${comparison?'Pinned scenario comparison':'Baseline comparison'}</h3><p>${comparison?'Pinned assumptions: '+controls.map(([key,title,,,,suffix])=>title+' '+comparison.a[key]+suffix).join(' · '):'Baseline uses the current price and cost, unchanged market and demand, and sensitivity 1.5.'}</p><p>Demand = demo sales × demand factor × (relative price change / market change)<sup>−sensitivity</sup>. Sales are capped at stock. Contribution excludes fixed overhead and tax on profit; it is not net profit.</p><p><strong>Assumption-based simulation, not trained ML.</strong> No customer retention is inferred. Competitor shifts here do not change collected evidence. <a href="#market">Open competitor monitor →</a></p></section>`;
    root.querySelectorAll('[data-price]').forEach(el=>el.onclick=()=>{c.a.price=Number(el.dataset.price);sync();});
  };
  const sync=()=>{controls.forEach(([key,,,,,suffix])=>{root.querySelector(`[data-lever="${key}"]`).value=c.a[key];root.querySelector('#out-'+key).textContent=c.a[key]+suffix;});update();};
  root.querySelectorAll('[data-lever]').forEach(el=>el.oninput=()=>{c.a[el.dataset.lever]=Number(el.value);root.querySelector('#out-'+el.dataset.lever).textContent=el.value+(el.dataset.lever==='elasticity'?'×':'%');update();});
  root.querySelector('#cockpit-product').onchange=e=>{c.id=e.target.value;c.a=defaults();c.saved=null;sync();};
  root.querySelector('#cockpit-reset').onclick=()=>{c.a=defaults();sync();};
  root.querySelector('#cockpit-save').onclick=()=>{const p=S.entries.find(e=>e.product.product_id===c.id).product;c.saved={id:c.id,a:{...c.a},result:simulate(p,c.a)};update();};
  root.querySelectorAll('[data-preset]').forEach(el=>el.onclick=()=>{c.a={...defaults(),...({pressure:{cost:20,price:10},sale:{price:-15,market:-10},age:{price:-20,demand:-40}}[el.dataset.preset])};sync();});
  update();
}
