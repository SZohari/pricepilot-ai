import {esc,money,safeLink} from './utils.js';
import {editedProduct} from './retail.js';
import {recordJourneyStep} from './navigation.js';
import {collectionPanel,knowledgePanel,openQuestions} from './evidence.js';

export const steps=['Your shop','Costs & limits','Market & customers','Choose a move','Your plan'];
const goals=[['steady','Keep sales steady','No fall in the recent sales pace.',0],['balanced','Balance sales and margin','Allow up to 5% fewer units in a test.',5],['margin','Give margin more room','Allow up to 10% fewer units in a test.',10]];
const photo=name=>`<img src="/static/assets/images/${name}-960.webp" alt="Illustration of a fictional watch retailer" width="1536" height="1024" decoding="async">`;
const button=(action,text,primary=false,extra='')=>`<button type="button" class="journey-button ${primary?'journey-primary':''}" data-journey="${action}" ${extra}>${text}</button>`;
const field=(name,title,value,attrs='type="number" min="0" step=".01" required',hint='')=>`<label class="journey-field"><span>${title}</span><input name="${name}" value="${esc(value??'')}" ${attrs}>${hint?`<small>${hint}</small>`:''}</label>`;
const check=(name,text,on=false)=>`<label class="journey-check"><input type="checkbox" name="${name}" ${on?'checked':''}><span>${text}</span></label>`;
const select=(name,title,value,options)=>`<label class="journey-field"><span>${title}</span><select name="${name}">${options.map(([v,t])=>`<option value="${esc(v)}" ${String(value)===v?'selected':''}>${esc(t)}</option>`).join('')}</select></label>`;
const today=()=>{const d=new Date();return [d.getFullYear(),String(d.getMonth()+1).padStart(2,'0'),String(d.getDate()).padStart(2,'0')].join('-');};
const error='<p class="journey-error" role="alert"></p>';

export function newJourney(){return {step:0,unlocked:0,id:null,requestedId:null,goal:'balanced',mode:'demo',item:null,draft:null,dirty:false,plan:null,request:{max_loss:5,test_days:14,candidate_price:null,signal:'unknown',positioning:'comparable',comparables:[],knowledge_notes:[]}};}
export function journeyPage(){return '<div id="journey-root" class="pricing-journey"><p role="status" class="journey-loading">Opening your pricing setup…</p></div>';}
export function disposeJourney(S){S.disposeJourney?.();S.disposeJourney=null;}

export function progressHTML(a){return `<nav class="journey-steps" aria-label="Pricing setup steps">${steps.map((name,i)=>`<button type="button" data-journey="step" data-step="${i}" ${i>a.unlocked?'disabled':''} ${i===a.step?'aria-current="step"':''}><span>${i<a.step||a.plan?'✓':String(i+1).padStart(2,'0')}</span><strong>${name}</strong><small>${i===a.step?'You are here':i<a.step||a.plan?'Reviewed':i<=a.unlocked?'Revisit':'Up next'}</small></button>`).join('')}</nav>`;}

function shell(a){return `<header class="journey-top"><a href="#overview" class="journey-wordmark">← Welcome</a><span>${a.mode==='demo'?'WATCH SHOP DEMO · SIMULATED BUSINESS DATA':'YOUR PRODUCT DATA'}</span><div><a href="#assistant">Ask PricePilot ↗</a> · <a href="#plans">Saved plans ↗</a></div></header>${progressHTML(a)}<div class="journey-body">${[chooseShop,costsPage,marketPage,decisionPage,planPage][a.step](a)}</div>`;}
const heading=(step,title,text)=>`<div class="journey-heading"><span class="journey-kicker">STEP ${step} OF 5</span><h1>${title}</h1><p>${text}</p></div>`;
function footer(a,label,action='next'){return `<div class="journey-footer">${a.step?button('back','← Back'): '<a href="#overview">← Welcome</a>'}<span>${a.step<4?`Next: ${steps[a.step+1]}`:'You stay in control of publication'}</span>${button(action,label,true, a.pending?'disabled':'')}</div>`;}

function chooseShop(a){const rows=a.data.rows.filter(r=>r.origin===a.mode);return `${heading(1,'Let’s build your pricing routine.','One product first. We will check its costs, understand its market, then help you choose what to do.')}<div class="journey-start-layout"><section class="journey-panel"><div class="journey-mode" role="group" aria-label="Choose data source">${button('mode-demo','Explore the watch shop',a.mode==='demo')}${button('mode-merchant','Use my products',a.mode==='merchant')}</div><p class="journey-muted">${a.mode==='demo'?'Kiez & Co is a fictional online watch shop. The sample inputs are ready, and you can change them.':'Choose an imported product, or bring a catalog from your shop.'}</p>${rows.length?`${select('product','Which product shall we work on?',a.id,rows.map(r=>[r.product_id,r.name]))}<div id="journey-product-summary">${productSummary(a)}</div>`:'<div class="journey-empty"><h2>Your shop starts here.</h2><p>Bring a CSV or add one product. We will guide you through the costs after it arrives.</p><a class="journey-button journey-primary" href="#onboarding">Bring my products →</a></div>'}<h2 class="journey-subheading">What matters most in this first test?</h2><div class="journey-goals">${goals.map(([id,name,description])=>`<button type="button" data-journey="goal" data-goal="${id}" aria-pressed="${a.goal===id}"><span>${a.goal===id?'◉':'○'}</span><strong>${name}</strong><small>${description}</small></button>`).join('')}</div><p class="journey-muted">Every option also protects the money left after order costs. These are limits you choose, not promised outcomes.</p>${error}</section><aside class="journey-start-image">${photo('journey-stock')}<div><span class="journey-kicker">A ROUTINE YOU CAN REPEAT</span><h2>From a list of products<br>to a reasoned next move.</h2><ol><li>Check what each sale costs.</li><li>Understand the market and the customer.</li><li>Choose a price to test, then review it.</li></ol></div></aside></div>${rows.length?footer(a,'Start with this product →'):'<p class="journey-muted">Your existing demo is still available under “Explore the watch shop”.</p>'}`;}
function productSummary(a){if(!a.item)return '<p class="journey-muted" role="status">Loading the selected product…</p>';const p=a.item.product;return `<div class="journey-product-summary"><span class="journey-watch" aria-hidden="true">◷</span><div><strong>${esc(p.name)}</strong><small>${esc(p.product_id)} · ${a.mode==='demo'?'Demo inputs':'Owner inputs'}</small></div><div><strong>${money(p.current_price_gross)}</strong><small>current customer total</small></div></div>`;}

export function productFields(item){const p=item.product,d=item.details||{},day=today();return {
  product_id:p.product_id,name:p.name,brand:p.brand,variant:d.variant||'Confirm exact model, size and condition',gtin:d.gtin||'',
  item_price_gross:(Number(p.current_price_gross)-Number(d.customer_shipping_gross||0)).toFixed(2),customer_shipping_gross:d.customer_shipping_gross||'0',
  purchase_cost_net:d.purchase_cost_net??'',replacement_cost_net:p.replacement_cost_net,inbound_cost_net:d.inbound_cost_net||'0',
  shipping_cost_net:d.shipping_cost_net||'0',packaging_cost_net:d.packaging_cost_net||'0',returns_allowance_net:d.returns_allowance_net||'0',
  other_cost_net:d.other_cost_net??(item.details?'0':p.variable_cost_net),fixed_fee_net:d.fixed_fee_net||'0',
  vat_percent:(Number(p.vat_rate)*100).toFixed(2),fee_percent:(Number(p.fee_rate)*100).toFixed(2),fee_basis:p.fee_basis||'net',
  minimum_margin_percent:(Number(p.minimum_margin)*100).toFixed(2),target_margin_percent:(Number(p.target_margin)*100).toFixed(2),
  inventory:String(p.inventory),sales_30d:String(p.sales_30d),sales_7d:d.sales_7d_known?String(p.sales_7d):'',
  costs_checked_on:d.costs_checked_on||day,sales_period_end:d.sales_period_end||'',signal:d.signal||'unknown',
  baseline_representative:d.baseline_representative||false,cost_scope_confirmed:d.cost_scope_confirmed||false};}

export function costInsight(item,base=null){const r=item.report,remaining=item.economics.current_contribution,floor=r.economics.minimum_price_gross;
  const confirmed=!!item.details?.cost_scope_confirmed;
  const below=Number(item.product.current_price_gross)<Number(floor),changed=base&&Number(remaining)!==Number(base.economics.current_contribution);
  return `<span class="journey-kicker">WHAT THESE INPUTS MEAN</span><h2>${!confirmed?'Confirm the full cost picture first.':below?'This price misses your minimum.':'This sale has room above its costs.'}</h2><p>${confirmed?'At':'Based only on the entered costs, at'} ${money(item.product.current_price_gross)}, <strong>${money(remaining)}</strong> remains per order before rent, salaries and other fixed costs.</p><div class="journey-insight-number"><span>Minimum customer total for your chosen margin</span><strong>${money(floor)}</strong></div><p>${below?'Check the supplier cost, your margin requirement or the price before trying to sell more.':'This is a financial starting point. The market and your customers still decide whether a price works.'}</p>${changed?`<div class="journey-change-note">Your edit changed the amount left per sale: <strong>${money(base.economics.current_contribution)} → ${money(remaining)}</strong>.</div>`:''}<details class="journey-detail"><summary>See where the customer’s payment goes</summary>${item.waterfall.map(w=>`<div class="journey-money-row"><span>${esc(w.label)}</span><strong>${w.kind==='cost'?'− ':''}${money(w.amount)}</strong></div>`).join('')}</details>`;}

function costsPage(a){const f=a.fields;return `${heading(2,'Make sure each sale supports the shop.','Change an input and watch the explanation update. Confirm the costs when you are ready to continue.')}<div class="journey-work-layout"><form id="journey-cost-form" class="journey-panel"><div class="journey-section-title"><span>01</span><h2>The price and the next purchase</h2></div><div class="journey-fields">${field('item_price_gross','Item price, including VAT (€)',f.item_price_gross,'type="number" min=".01" step=".01" required')}${field('customer_shipping_gross','Delivery charged to the customer (€)',f.customer_shipping_gross)}${field('replacement_cost_net','Buy the next unit, excluding recoverable VAT (€)',f.replacement_cost_net,'type="number" min=".01" step=".01" required')}${field('purchase_cost_net','What you paid for the stocked unit (€)',f.purchase_cost_net,'type="number" min=".01" step=".01" required','Kept separately; the next purchase sets this replenishment check.')}</div><div class="journey-section-title"><span>02</span><h2>What it takes to fulfil an order</h2></div><div class="journey-fields">${field('shipping_cost_net','Delivery cost per order (€)',f.shipping_cost_net)}${field('packaging_cost_net','Packaging per order (€)',f.packaging_cost_net)}${field('returns_allowance_net','Expected unrecovered returns cost per sale (€)',f.returns_allowance_net)}${field('minimum_margin_percent','Minimum amount left, as % of net revenue',f.minimum_margin_percent,'type="number" min="0" max="90" step=".01" required','Your chosen margin, before fixed costs. It is not markup.')}</div>
  <details class="journey-detail"><summary>Tax, payment fees and other order costs</summary><div class="journey-fields">${field('vat_percent','VAT (%)',f.vat_percent,'type="number" min="0" max="99" step=".01" required')}${field('fee_percent','Percentage payment / marketplace fee (%)',f.fee_percent,'type="number" min="0" max="99" step=".01" required')}${select('fee_basis','Fee charged on',f.fee_basis,[['gross','Customer total including VAT'],['net','Revenue excluding VAT']])}${field('fixed_fee_net','Fixed transaction fee (€)',f.fixed_fee_net)}${field('inbound_cost_net','Inbound freight / duties per unit (€)',f.inbound_cost_net)}${field('other_cost_net','Other variable cost per order (€)',f.other_cost_net)}${field('target_margin_percent','Target margin (%)',f.target_margin_percent,'type="number" min="0" max="99" step=".01" required')}${field('costs_checked_on','These costs were checked on',f.costs_checked_on,`type="date" required max="${today()}"`)}</div><p class="journey-muted">Costs exclude recoverable VAT. Include nonrecoverable tax. Enter zero deliberately where a cost does not apply.</p></details>
  <details class="journey-detail"><summary>Recent sales and available stock</summary><div class="journey-fields">${field('inventory','Units available for this test',f.inventory,'type="number" min="0" max="1000000" step="1" required')}${field('sales_30d','Units sold in the completed 30 days',f.sales_30d,'type="number" min="0" max="1000000" step="1" required')}${field('sales_period_end','That sales period ended on',f.sales_period_end,`type="date" required max="${today()}"`)}</div>${check('baseline_representative','These sales used the current price, with full availability and no unusual campaign.',f.baseline_representative)}<p class="journey-muted">Changing the current price or sales period requires a fresh baseline confirmation. With no representative history, the next action is to collect it.</p></details>
  ${check('cost_scope_confirmed',a.mode==='demo'?'Use this complete set of illustrative costs for the demo.':'I have included all variable order costs and checked the fee and tax treatment.',f.cost_scope_confirmed)}${error}<p id="journey-cost-status" class="journey-status" role="status">${a.dirty?'Unsaved inputs. Confirm below to keep them.':'Inputs loaded. Try changing the supplier cost.'}</p><button type="submit" class="journey-button">Recheck these inputs</button></form><aside class="journey-insight" id="journey-cost-insight">${costInsight(a.item,a.baseItem)}</aside></div>${footer(a,a.mode==='demo'?'Use these inputs & check the market →':'Confirm inputs & check the market →','confirm-costs')}`;}

export function marketInsight(item){const r=item.report,gap=item.insight?.market_gap_pct;
  return `<span class="journey-kicker">WHAT THE MARKET TELLS US</span><h2>${r.market_usable?(Number(gap)>3?'Other comparable offers cost less.':Number(gap)<-3?'Your total is below these offers.':'Your price is close to these offers.'):'We still need a better comparison.'}</h2><p>${r.market_usable?`Your customer total is ${money(item.product.current_price_gross)}. The middle price among usable offers is ${money(r.market_median_gross)}. ${Math.abs(Number(gap)).toFixed(1)}% ${Number(gap)>=0?'above':'below'} that benchmark.`:'A name or one cheap listing is not enough. Confirm the exact product and the full delivery price, or continue with this gap clearly visible.'}</p><div class="journey-takeaway"><strong>${r.input.signal==='price_objections'?'Customers also object to the price.':r.input.signal==='low_visibility'?'The immediate problem may be visibility.':r.input.positioning==='differentiated'?'Your offer may need a different comparison.':'A listing is a clue, not a completed sale.'}</strong><p>${r.input.signal==='low_visibility'?'A discount cannot help people who never see your offer. That signal can change the next action.':'We combine this context with your costs before proposing any price test.'}</p></div>`;}

function marketPage(a){const r=a.item.report;return `${heading(3,'Understand the offer around the price.','We check the market automatically from available evidence. You add the customer context the numbers cannot supply.')}<div class="journey-work-layout"><section class="journey-panel">${collectionPanel(a)}<div class="journey-section-title"><span>01</span><h2>${r.evidence.length} recent offers to inspect</h2></div><p class="journey-muted">${a.mode==='demo'?'These competitor prices are simulated for the shop example.':'Collected and owner-entered offers are labelled separately.'} Same model, variant, condition, availability and delivered price matter.</p><div id="journey-market-offers">${offersHTML(r)}</div><form id="journey-market-form"><div class="journey-section-title"><span>02</span><h2>What do you know about the customer?</h2></div>${select('signal','What have you actually noticed?',a.request.signal,[['unknown','I do not know the reason yet'],['price_objections','People explicitly object to the price'],['low_visibility','Too few people see or enquire about the offer'],['at_capacity','We are selling at full capacity']])}${select('positioning','Is your offer comparable?',a.request.positioning,[['comparable','Same product and a comparable service'],['differentiated','Our service, delivery or scope is different']])}<p class="journey-muted">Your observation is an input, not independently verified evidence. A service difference does not automatically justify a price premium.</p>${error}<p id="journey-market-status" class="journey-status" role="status">${r.market_usable?'Market evidence can inform this decision.':'You can continue with limited evidence; it will stay visible in the advice.'}</p><button type="submit" class="journey-button">Recheck customer context</button></form>${knowledgePanel(a)}<details class="journey-detail"><summary>Add a competitor offer you checked</summary><form id="journey-offer-form"><div class="journey-fields">${field('seller','Seller name','','required maxlength="120"')}${field('total_price_gross','Total with VAT and delivery (€)','','type="number" min=".01" step=".01" required')}${field('url','Exact listing URL','','type="url" required placeholder="https://…"')}${field('observed_on','Date checked',a.item.report.as_of,`type="date" required max="${today()}"`)}</div>${check('same_offer','I checked the same variant, condition, availability and all customer charges.')}${error}<button class="journey-button" type="submit">Add offer & recheck</button></form></details><details class="journey-detail"><summary>How automatic competitor collection works</summary><p>Configured product URLs are checked for a matching GTIN and a usable EUR offer. Unsupported or blocked pages add no price. This product currently has ${a.sourceCount} configured source URLs.</p><a href="#market">Open source collection ↗</a><p class="journey-muted">Your progress stays here during this session. Public visitors can use owner-configured sources; URL setup is restricted to the local workspace.</p></details></section><aside class="journey-insight" id="journey-market-insight">${marketInsight(a.item)}</aside></div>${footer(a,'See what this means for my price →')}`;}
function offersHTML(r){return r.evidence.map(o=>`<div class="journey-offer"><div><strong>${esc(o.seller)}</strong><small>${esc(o.observed_on)} · ${o.origin==='demo'?'Simulated':o.origin==='live'?'Collected':'Owner-entered'}</small>${safeLink(o.url)?`<a href="${safeLink(o.url)}" target="_blank" rel="noopener noreferrer">View listing ↗</a>`:''}</div><strong>${money(o.price)}</strong></div>`).join('')||'<div class="journey-empty"><p>No comparable offers yet. Add checked listings below, or continue to a cost-based next action.</p></div>';}

export function decisionInsight(item){const r=item.report,i=item.insight;return `<div class="journey-decision-head" data-tone="${r.can_start_test?'test':['unsafe_price','rework_offer'].includes(r.action)?'stop':'check'}"><span class="journey-kicker">${r.can_start_test?'A TEST TO CONSIDER':'YOUR NEXT USEFUL ACTION'}</span><h2>${esc(r.title)}</h2><p>${esc(r.why)}</p></div><div class="journey-comparison"><div><span>Current customer total</span><strong>${money(i.current_price)}</strong><small>${money(i.current_per_sale)} left per sale</small></div><span aria-hidden="true">→</span><div><span>${r.can_start_test?'Price to test':'Price reviewed'}</span><strong>${money(i.considered_price)}</strong><small>${money(i.considered_per_sale)} left per sale</small></div></div><div class="journey-takeaway"><strong>${r.can_start_test?'The trade-off to understand':'What this means for your next step'}</strong><p>${esc(i.message)}</p></div>${r.can_start_test?`<div class="journey-sales-condition"><span>For this test to meet your limits</span><strong>${i.required_units} sales <em>in ${r.input.test_days} days</em></strong><p>Recent pace over the same length: about ${esc(i.baseline_units)} units. ${i.extra_units?`You need at least ${i.extra_units} more than that rounded-up pace.`:'Your allowed sales loss still limits the test.'}</p><small>This is a required result, not a prediction of sales.</small></div>`:''}<div class="journey-next-note"><span>THE ACTION</span><p>${esc(r.next_step)}</p></div><details class="journey-detail"><summary>Check the calculation and the unknowns</summary><div class="journey-money-row"><span>Your minimum customer total</span><strong>${money(r.economics.minimum_price_gross)}</strong></div><div class="journey-money-row"><span>Available units</span><strong>${r.economics.capacity}</strong></div><p>Money left means contribution before fixed costs, not net profit. This does not estimate retention or prove that changing price causes more sales. Supplier changes, promotions and stockouts can change the result.</p></details>`;}

function decisionPage(a){const r=a.item.report,p=a.item.product,current=Number(p.current_price_gross);return `${heading(4,'Choose a move you can explain.','Change the price or your limits. The comparison tells you what changes, what it requires and whether the test is usable.')}<div class="journey-work-layout journey-choice-layout"><section class="journey-panel journey-live-result" id="journey-decision-insight">${decisionInsight(a.item)}${openQuestions(a.item.report)}</section><form id="journey-price-form" class="journey-insight journey-price-controls"><span class="journey-kicker">YOU CHOOSE. WE RECHECK.</span><h2>Try a different price.</h2>${field('candidate_price','Total customer price to check (€)',a.item.insight.considered_price,'type="number" min=".01" step=".01" required')}<input type="range" name="price_range" aria-label="Change the candidate price" min="${(current*.9).toFixed(2)}" max="${(current*1.1).toFixed(2)}" value="${a.item.insight.considered_price}" step=".01"><div class="journey-presets">${button('lower','Try −3%')}${button('current','Current')}${button('higher','Try +3%')}</div>${button('advice','Use the advisor’s next step')}<div class="journey-control-divider"></div>${field('max_loss','Biggest sales drop you will accept (%)',a.request.max_loss,'type="number" min="0" max="30" step="1" required')}${select('test_days','Review after',String(a.request.test_days),[['7','7 days'],['14','14 days'],['21','21 days'],['30','30 days']])}<p class="journey-muted">Your starting choice: ${esc(goals.find(g=>g[0]===a.goal)?.[1])}. You can adjust the limit here.</p>${error}<p id="journey-price-status" class="journey-status" role="status">Calculated from the inputs you reviewed. No store price has changed.</p><button class="journey-button" type="submit">Recalculate now</button></form></div>${footer(a,'Turn this into a plan →')}`;}

function planPage(a){const r=a.item.report,p=a.item.product;return `${heading(5,a.plan?'Your next move is recorded.':'Put the decision into a routine.',a.plan?'Your evidence and chosen limits are saved together. The next step is yours to carry out.':'Review what is ready, what runs automatically and what still needs your approval.')}<div class="journey-work-layout"><section class="journey-panel"><span class="journey-kicker">${esc(p.product_id)} · ${a.mode==='demo'?'DEMO PLAN':'OWNER INPUTS'}</span><h2 class="journey-plan-title">${esc(r.title)}</h2>${r.can_start_test?`<div class="journey-plan-price"><span>Customer total to test</span><strong>${money(r.test_price_gross)}</strong><small>${money(a.item.economics.candidate_item_price_gross)} item + ${money(a.item.economics.customer_shipping_gross)} delivery</small></div><div class="journey-plan-terms"><div><strong>${r.economics.minimum_units_with_volume_guardrail} sales</strong><span>required to meet both limits</span></div><div><strong>${r.input.test_days} days</strong><span>before the full review</span></div></div>`:`<div class="journey-takeaway"><strong>Start with this action</strong><p>${esc(r.next_step)}</p></div>`}${openQuestions(r)}<ol class="journey-runbook"><li><span>01</span><div><strong>Save the decision and evidence</strong><p>${a.plan?'Recorded in your action plans. Export a copy to keep it.':'The plan keeps your inputs, comparison, limits and the reason for the action.'}</p></div></li><li><span>02</span><div><strong>${r.can_start_test?'Apply it in your shop, then record the date':'Carry out the next action'}</strong><p>${r.can_start_test?'Review the item price and delivery charge separately. PricePilot does not have a connector that publishes to your shop.':'Record what you changed or learned before choosing a price test.'}</p></div></li><li><span>03</span><div><strong>Bring back what actually happened</strong><p>Compare the money left and the units sold. Record stockouts, campaigns and other changes too.</p></div></li></ol>${error}<div class="journey-plan-buttons">${a.plan?`${button('open-plan',r.can_start_test?'Record execution or explore a demo outcome →':'Open the action and follow it up →',true)}${r.can_start_test?`<a class="journey-button" href="/api/v1/advisor/plans/${encodeURIComponent(a.plan.id)}/price-sheet" download>Download price review CSV</a>`:''}`:button('save','Save my plan →',true,a.canWrite?'':'disabled')}</div><p class="journey-muted">This browser workspace is temporary. Export your plans and product data to keep them.</p></section><aside class="journey-insight"><span class="journey-kicker">WHAT PRICEPILOT TAKES CARE OF</span><h2>More of the work.<br>Clear control.</h2><ul class="journey-automation"><li><span>✓</span><div><strong>Input checks</strong><p>Validate product data and flag missing or inconsistent inputs.</p></div></li><li><span>✓</span><div><strong>Cost and price calculations</strong><p>Recalculate fees, margins and required sales when inputs change.</p></div></li><li><span>${a.sourceCount?'◐':'○'}</span><div><strong>Competitor collection</strong><p>${a.sourceCount?`${a.sourceCount} source URLs configured. Collection support is checked per source.`:'No source URL configured in this workspace yet. Add supported competitors to enable collection.'}</p></div></li><li><span>↗</span><div><strong>You approve publication</strong><p>Use the price review sheet in your shop. Automatic store publishing is not connected.</p></div></li></ul></aside></div><div class="journey-footer">${button('back','← Review my choice')}<a href="#products">View my product library ↗</a>${button('restart','Work on another product')}</div>`;}

export async function bindJourney(S,main,api,toast){
  const root=main.querySelector('#journey-root');if(!root)return;
  const a=S.journey??=newJourney();if(S.journeyRequestedId){a.requestedId=S.journeyRequestedId;S.journeyRequestedId=null;}a.canWrite=S.workspace.can_write;a.sourceCount=0;a.canConfigure=!!S.sources?.can_configure;
  let disposed=false,generation=0,timer;
  const valid=()=>!disposed&&root.isConnected;
  let saving=false;
  const lock=on=>{saving=on;root.inert=on;root.setAttribute('aria-busy',String(on));if(on){++generation;clearTimeout(timer);}};
  S.disposeJourney=()=>{disposed=true;++generation;clearTimeout(timer);};
  a.renderedStep=undefined;
  const draw=()=>{if(valid()){a.sourceCount=(S.sources?.sources||[]).filter(s=>s.product_id===a.id).length;root.innerHTML=shell(a);recordJourneyStep(a);}};
  const focus=()=>{window.scrollTo({top:0,behavior:'instant'});const h=root.querySelector('h1');h?.setAttribute('tabindex','-1');h?.focus({preventScroll:true});};
  const fail=(e,form)=>{const el=(form||root).querySelector('.journey-error');if(el)el.textContent=e.message;else toast(e.message);};
  const busy=(on,message='Checking your changes…')=>{
    a.pending=on;root.querySelectorAll('[data-journey="next"],[data-journey="confirm-costs"],[data-journey="save"]').forEach(b=>b.disabled=on||!a.item);
    const el=root.querySelector('.journey-status');if(el)el.textContent=message;
    for(const id of ['#journey-cost-insight','#journey-market-insight','#journey-decision-insight']){
      const view=root.querySelector(id);view?.setAttribute('data-update',on?'Previous result · waiting for a valid update':'');view?.setAttribute('aria-busy',String(on));
    }
  };
  const invalidate=()=>{++generation;clearTimeout(timer);a.plan=null;a.unlocked=Math.min(a.unlocked,a.step);const progress=root.querySelector('.journey-steps');if(progress)progress.outerHTML=progressHTML(a);busy(true);};
  const request=extra=>({product_id:a.id,expected_version:a.item.version,...a.request,...extra});
  const showResult=()=>{
    if(a.step===1){root.querySelector('#journey-cost-insight').innerHTML=costInsight(a.item,a.baseItem);}
    if(a.step===2){root.querySelector('#journey-market-insight').innerHTML=marketInsight(a.item);root.querySelector('#journey-market-offers').innerHTML=offersHTML(a.item.report);const cards=root.querySelector('#journey-knowledge-cards');if(cards)cards.innerHTML=openQuestions(a.item.report,true);}
    if(a.step===3){root.querySelector('#journey-decision-insight').innerHTML=decisionInsight(a.item);const f=root.querySelector('#journey-price-form');if(a.request.candidate_price===null){f.elements.candidate_price.value=a.item.insight.considered_price;f.elements.price_range.value=a.item.insight.considered_price;}}
  };
  const loadProduct=async id=>{const token=++generation;busy(true,'Opening the product…');const item=await api('/api/v1/retail/analyze',{method:'POST',body:{product_id:id}});if(!valid()||token!==generation)return;
    a.id=id;a.item=item;a.baseItem=structuredClone(item);a.fields=productFields(item);a.draft=null;a.dirty=false;a.pending=false;a.plan=null;a.editingKnowledge=null;a.collectionResult=null;a.collectionError='';a.refreshCheckedAt=0;a.unlocked=0;a.step=0;a.mode=item.product.data_origin==='demo'?'demo':'merchant';a.request={max_loss:goals.find(g=>g[0]===a.goal)[3],test_days:14,candidate_price:null,signal:item.report.input.signal,positioning:'comparable',comparables:[],knowledge_notes:[]};draw();};
  const captureCosts=form=>{const f={...a.fields,...Object.fromEntries(new FormData(form))};f.cost_scope_confirmed=form.elements.cost_scope_confirmed.checked;f.baseline_representative=form.elements.baseline_representative.checked;a.fields=f;const base=structuredClone(a.item.product);base.retail??={};a.draft=editedProduct(f,base);return a.draft;};
  const recalc=async()=>{
    const form=root.querySelector(a.step===1?'#journey-cost-form':a.step===2?'#journey-market-form':'#journey-price-form');if(!form)return false;
    if(!form.checkValidity()){busy(true,'Complete the highlighted inputs to update the result.');form.querySelectorAll('input:invalid').forEach(el=>el.setAttribute('aria-invalid','true'));return false;}
    form.querySelectorAll('[aria-invalid]').forEach(el=>el.removeAttribute('aria-invalid'));let extra={};
    if(a.step===1)extra.product_draft=captureCosts(form);
    if(a.step===2){a.request.signal=form.elements.signal.value;a.request.positioning=form.elements.positioning.value;}
    if(a.step===3){a.request.max_loss=form.elements.max_loss.value;a.request.test_days=Number(form.elements.test_days.value);}
    const token=++generation;busy(true);form.querySelector('.journey-error').textContent='';
    try{const item=await api('/api/v1/retail/analyze',{method:'POST',body:request(extra)});if(!valid()||token!==generation)return false;a.item=item;a.requestId=crypto.randomUUID();showResult();busy(false,a.step===1?'Updated preview. Confirm below to save these inputs.':'Updated. The explanation reflects your latest choices.');return true;}
    catch(e){if(valid()&&token===generation){fail(e,form);busy(true,'Could not update. Check the message and try again.');}return false;}
  };
  const refreshPrices=async()=>{
    if(a.collecting||!a.sourceCount||a.mode!=='merchant'||!a.canWrite)return;
    lock(true);a.collecting=true;a.collectionError='';a.refreshCheckedAt=Date.now();draw();
    try{
      const result=await api('/api/sources/refresh-product',{method:'POST',body:{product_id:a.id}});if(!valid())return;
      a.collectionResult=result;
      const item=await api('/api/v1/retail/analyze',{method:'POST',body:request()});if(!valid())return;
      if(item.report.fingerprint!==a.item.report.fingerprint){a.plan=null;a.unlocked=Math.min(a.unlocked,2);}
      a.item=item;a.requestId=crypto.randomUUID();
    }catch(e){if(valid())a.collectionError=e.message;}
    finally{a.collecting=false;lock(false);if(valid()){a.pending=false;draw();}}
  };
  const maybeRefresh=async()=>{if(a.step===2&&a.autoRefresh!==false&&Date.now()-(a.refreshCheckedAt||0)>=300000)await refreshPrices();};
  const updateKnowledge=async notes=>{
    const token=++generation;clearTimeout(timer);busy(true);
    const item=await api('/api/v1/retail/analyze',{method:'POST',body:request({knowledge_notes:notes})});
    if(!valid()||token!==generation)return false;
    a.editingKnowledge=null;a.request.knowledge_notes=notes;a.item=item;a.plan=null;a.unlocked=2;a.pending=false;a.requestId=crypto.randomUUID();draw();return true;
  };
  try{
    [a.data,S.sources]=await Promise.all([api('/api/v1/retail/workspace'),api('/api/sources')]);a.canConfigure=!!S.sources.can_configure;if(!valid())return;
    const wanted=a.requestedId;a.requestedId=null;
    if(S.journeyRouteStep!==null&&S.journeyRouteStep!==undefined){a.step=Math.min(S.journeyRouteStep,a.unlocked);S.journeyRouteStep=null;}
    if(wanted||!a.item){const id=wanted||a.data.rows.find(r=>r.origin===a.mode&&r.product_id==='DE-WEAR-001')?.product_id||a.data.rows.find(r=>r.origin===a.mode)?.product_id;if(id)await loadProduct(id);else{a.step=0;a.pending=false;draw();}}
    else{
      const current=a.data.rows.find(r=>r.product_id===a.id);
      if(!current){a.item=null;a.id=null;a.step=0;a.unlocked=0;draw();}
      else if(current.version!==a.item.version){await loadProduct(a.id);toast('Product inputs changed. Start again with the current version.');}
      else{
        if(a.dirty){a.step=Math.min(a.step,1);a.unlocked=1;a.plan=null;}
        else{
          const latest=await api('/api/v1/retail/analyze',{method:'POST',body:request()});if(!valid())return;
          if(latest.report.fingerprint!==a.item.report.fingerprint){a.plan=null;a.step=Math.min(a.step,3);a.unlocked=Math.min(a.unlocked,3);}
          a.item=latest;
        }
        a.pending=false;draw();if(a.dirty)await recalc();
      }
    }
    if(S.journeyFollowup?.linked_product_id===a.id){
      const c=S.journeyFollowup;
      a.request={...a.request,knowledge_notes:structuredClone(c.knowledge_notes||[]),customer_value:c.customer_value||null,comparables:structuredClone(c.comparables||[]),signal:c.signal,positioning:c.positioning,max_loss:c.max_volume_loss_pct,test_days:c.test_days,candidate_price:null};
      a.item=await api('/api/v1/retail/analyze',{method:'POST',body:request()});if(!valid())return;
      S.journeyFollowup=null;a.baseItem=structuredClone(a.item);a.step=1;a.unlocked=1;draw();
      toast('Your previous context is here. Check current costs, then update what you learned in Market & customers.');
    }
  }catch(e){if(valid())root.innerHTML=`<div class="journey-panel"><h1>We could not open this setup.</h1><p>${esc(e.message)}</p><a href="#overview">Return to the welcome page</a></div>`;return;}

  root.addEventListener('input',e=>{
    if(saving)return;
    const form=e.target.closest('form');if(!form||!['journey-cost-form','journey-market-form','journey-price-form'].includes(form.id))return;
    if(form.id==='journey-cost-form'){
      if(['item_price_gross','customer_shipping_gross','sales_30d','sales_period_end'].includes(e.target.name))form.elements.baseline_representative.checked=false;
      a.dirty=true;captureCosts(form);
    }
    if(form.id==='journey-market-form'){a.request.signal=form.elements.signal.value;a.request.positioning=form.elements.positioning.value;a.request.candidate_price=null;}
    if(form.id==='journey-price-form'){
      if(e.target.name==='price_range'){form.elements.candidate_price.value=e.target.value;a.request.candidate_price=e.target.value;}
      if(e.target.name==='candidate_price'){form.elements.price_range.value=e.target.value;a.request.candidate_price=e.target.value;}
    }
    invalidate();timer=setTimeout(recalc,300);
  });
  root.addEventListener('change',async e=>{if(saving)return;if(e.target.name==='auto_refresh'){a.autoRefresh=e.target.checked;return;}if(e.target.name==='product'){try{await loadProduct(e.target.value);}catch(err){if(valid()){a.item=null;busy(true,'Could not load this product. Choose it again to retry.');fail(err);}}}});
  root.addEventListener('click',async e=>{
    if(saving)return;
    const b=e.target.closest('[data-journey]');if(!b||!root.contains(b)||b.disabled)return;e.preventDefault();const action=b.dataset.journey;
    try{
      if(action==='knowledge-cancel'){a.editingKnowledge=null;draw();return;}
      if(action==='knowledge-edit'){a.editingKnowledge=Number(b.dataset.index);draw();root.querySelector('#journey-knowledge-form')?.scrollIntoView?.({block:'center',behavior:'smooth'});return;}
      if(action==='collect'){await refreshPrices();return;}
      if(action==='knowledge-remove'||action==='knowledge-toggle'){
        const index=Number(b.dataset.index),notes=structuredClone(a.request.knowledge_notes||[]);
        if(!Number.isInteger(index)||!notes[index])return;
        if(action==='knowledge-remove')notes.splice(index,1);else notes[index].resolve_first=!notes[index].resolve_first;
        await updateKnowledge(notes);return;
      }
      if(action==='goal'){a.goal=b.dataset.goal;a.request.max_loss=goals.find(g=>g[0]===a.goal)[3];a.unlocked=0;a.plan=null;draw();return;}
      if(action.startsWith('mode-')){++generation;clearTimeout(timer);a.mode=action==='mode-demo'?'demo':'merchant';const row=a.data.rows.find(r=>r.origin===a.mode&&(a.mode!=='demo'||r.product_id==='DE-WEAR-001'))||a.data.rows.find(r=>r.origin===a.mode);if(row)await loadProduct(row.product_id);else{a.item=null;a.id=null;a.plan=null;a.dirty=false;a.unlocked=0;a.step=0;draw();}return;}
      if(action==='step'||action==='back'){clearTimeout(timer);++generation;const next=action==='back'?a.step-1:Number(b.dataset.step);if(next<0||next>a.unlocked)return;if(action==='back'&&window.history?.state?.previousStep===next){window.history.back();return;}a.step=next;a.pending=false;draw();focus();if(next===2)await maybeRefresh();return;}
      if(action==='restart'){a.step=0;a.unlocked=0;a.plan=null;draw();focus();return;}
      if(action==='next'){
        if(a.step===0){if(!a.item)throw Error('Choose a product first.');a.step=1;a.unlocked=Math.max(a.unlocked,1);draw();focus();return;}
        if(a.step===2||a.step===3){if(!await recalc())return;a.step++;a.unlocked=Math.max(a.unlocked,a.step);draw();focus();return;}
      }
      if(action==='confirm-costs'){
        const form=root.querySelector('#journey-cost-form');if(!form.reportValidity())return;const draft=captureCosts(form);if(!draft.retail.cost_scope_confirmed)throw Error('Confirm the full order costs before continuing.');
        lock(true);b.disabled=true;const changed=JSON.stringify(draft)!==JSON.stringify(a.baseItem.product);
        if(changed){if(!a.canWrite)throw Error('This workspace is read-only.');const saved=await api('/api/v1/retail/product',{method:'PUT',body:{product:draft,expected_version:a.item.version}});if(!valid())return;a.item.version=saved.version;const local=S.entries.find(e=>e.product.product_id===a.id);if(local){local.product=saved.product;local.version=saved.version;}}
        const item=await api('/api/v1/retail/analyze',{method:'POST',body:request()});if(!valid())return;a.item=item;a.baseItem=structuredClone(item);a.fields=productFields(item);a.dirty=false;a.draft=null;a.step=2;a.unlocked=2;a.pending=false;a.requestId=crypto.randomUUID();draw();focus();await maybeRefresh();return;
      }
      if(['lower','current','higher','advice'].includes(action)){const price=Number(a.item.product.current_price_gross),factor=action==='lower'?.97:action==='higher'?1.03:1;a.request.candidate_price=action==='advice'?null:(price*factor).toFixed(2);const form=root.querySelector('#journey-price-form');if(a.request.candidate_price!==null){form.elements.candidate_price.value=a.request.candidate_price;form.elements.price_range.value=a.request.candidate_price;}invalidate();await recalc();return;}
      if(action==='save'){
        lock(true);
        b.disabled=true;if(a.item.draft||a.dirty)throw Error('Confirm product inputs before saving a plan.');const r=a.item.report;
        a.requestId??=crypto.randomUUID();const plan=await api('/api/v1/advisor/plans',{method:'POST',body:{request_id:a.requestId,input:r.input,fingerprint:r.fingerprint}});if(!valid())return;a.plan=plan;draw();toast('Plan recorded with its evidence. No shop price has changed.');return;
      }
      if(action==='open-plan'){S.advisor={phase:'plan',plan:a.plan,examples:[],plans:[],step:1};location.hash='plans';}
    }catch(err){if(valid()){fail(err);b.disabled=false;if(action.startsWith('knowledge-'))busy(false,'The context was not changed. Try again.');}}finally{if(saving)lock(false);}
  });
  root.addEventListener('submit',async e=>{
    e.preventDefault();if(saving)return;clearTimeout(timer);const form=e.target;
    if(form.id==='journey-knowledge-form'){
      const b=form.querySelector('[type="submit"]');b.disabled=true;
      try{
        if(!form.reportValidity())return;
        const f=Object.fromEntries(new FormData(form)),notes=structuredClone(a.request.knowledge_notes||[]);
        const note={topic:f.topic,statement:f.statement,basis:f.basis,evidence_note:f.evidence_note,checked_on:f.checked_on,resolve_first:form.elements.resolve_first.checked};
        if(Number.isInteger(a.editingKnowledge)&&notes[a.editingKnowledge])notes[a.editingKnowledge]=note;else notes.push(note);
        await updateKnowledge(notes);
      }
      catch(err){if(valid()){fail(err,form);busy(false,'The note was not added. Correct it or continue with the existing context.');}}
      finally{if(b.isConnected)b.disabled=false;}return;
    }
    if(form.id==='journey-source-form'){
      const b=form.querySelector('[type="submit"]');b.disabled=true;lock(true);
      try{
        const f=Object.fromEntries(new FormData(form));if(!form.elements.exact_variant_confirmed.checked)throw Error('Confirm the exact variant before connecting.');
        await api('/api/sources/connect-offer',{method:'POST',body:{input:a.item.report.input,exact_variant_confirmed:true,source:{source_id:'URL-'+crypto.randomUUID(),product_id:a.id,seller:f.seller,url:f.url,expected_gtin:f.expected_gtin,shipping_gross:f.shipping_gross,shipping_note:f.shipping_note}}});if(!valid())return;
        S.sources=await api('/api/sources');if(!valid())return;a.canConfigure=!!S.sources.can_configure;draw();lock(false);await refreshPrices();
      }catch(err){if(valid())fail(err,form);}finally{lock(false);if(b.isConnected)b.disabled=false;}return;
    }
    if(form.id!=='journey-offer-form'){await recalc();return;}
    const b=form.querySelector('[type="submit"]');b.disabled=true;
    try{if(!form.elements.same_offer.checked)throw Error('Confirm the same offer, availability and delivery first.');const f=Object.fromEntries(new FormData(form));const comparables=[...a.request.comparables,{seller:f.seller,total_price_gross:f.total_price_gross,url:f.url,observed_on:f.observed_on,same_offer:true,available:true}];
      const token=++generation;busy(true,'Checking this offer…');const item=await api('/api/v1/retail/analyze',{method:'POST',body:request({comparables})});if(!valid()||token!==generation)return;a.request.comparables=comparables;a.item=item;a.plan=null;a.unlocked=2;a.pending=false;draw();toast('Owner-entered offer added to this decision.');
    }catch(err){if(valid()){fail(err,form);busy(false,'Offer not added. Correct it or continue with existing evidence.');}}finally{if(b.isConnected)b.disabled=false;}
  });
  await maybeRefresh();
}
