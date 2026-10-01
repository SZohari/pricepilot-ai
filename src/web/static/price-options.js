import {simulate,defaults} from './cockpit.js';

export const priorities={
  balanced:{label:'Balance sales & earnings',tolerance:5},
  earnings:{label:'Protect earnings',tolerance:10},
  volume:{label:'Move more stock',tolerance:20}
};
const cents=n=>Math.round(n*100)/100;
// Sensitivity analysis only: no learned/causal demand claim. Same assumptions
// and inventory cap apply to both the current price and every alternative.
export function priceOptions(p,rec,{goal='balanced',cost=0,sensitivity='medium',tolerance=priorities[goal].tolerance}={}){
  const bands={low:[.5,1.5],medium:[.8,2.5],high:[2,4]};
  const band=bands[sensitivity]||bands.medium;
  const current=Number(p.current_price_gross);
  const evaluate=price=>{
    const a={...defaults(),cost,price:(price/current-1)*100};
    const outcomes=[band[0],(band[0]+band[1])/2,band[1]].map(elasticity=>simulate(p,{...a,elasticity}));
    const mid=outcomes[1];
    return {price:cents(price),change:(price/current-1)*100,...Object.fromEntries(['units','contribution'].map(k=>[k,{low:Math.min(...outcomes.map(o=>o[k])),mid:mid[k],high:Math.max(...outcomes.map(o=>o[k]))}])),unit:mid.unit,margin:mid.margin,floor:Math.ceil((mid.floor-1e-8)*100)/100,stockLimited:outcomes.some(o=>o.limited)};
  };
  const baseline=evaluate(current);
  const unavailable=!rec||rec.recommended_price_gross==null||rec.market_median_gross==null||rec.quality.status==='blocked';
  const state=!Number(p.inventory)?'no_stock':!Number(p.sales_30d)?'no_sales':unavailable?'no_market':'ready';
  if(state!=='ready')return {state,baseline,options:[{...baseline,key:'current',title:'Keep current price'}],selected:baseline,goal,band,cost,tolerance};
  // A small reviewable test range; no large extrapolation or automatic repricing.
  const ceiling=Math.min(current*1.1,Math.max(current,Number(rec.market_median_gross)*1.05));
  const candidates=Array.from({length:41},(_,i)=>cents(current*(.9+i*.005)))
    .filter((v,i,a)=>a.indexOf(v)===i&&v>=baseline.floor&&v<=ceiling+.001)
    .map(evaluate);
  const choose=(g)=>{
    const minimum=1-(g===goal?tolerance:priorities[g].tolerance)/100;
    const eligible=candidates.filter(c=>{
      if(g==='volume')return c.units.low>=baseline.units.mid&&c.contribution.low>=Math.max(0,baseline.contribution.mid*minimum);
      return c.units.low>=baseline.units.mid*minimum&&c.contribution.low>=0;
    });
    eligible.sort((a,b)=>{
      const score=x=>g==='volume'?x.units.low:x.contribution.low;
      return score(b)-score(a)||Math.abs(a.change)-Math.abs(b.change);
    });
    return eligible[0]||null;
  };
  const winner=choose(goal);
  const lower=[...candidates].filter(c=>c.price<current).sort((a,b)=>a.price-b.price);
  const higher=[...candidates].filter(c=>c.price>current).sort((a,b)=>a.price-b.price);
  const options=[{...baseline,key:'current',title:'Keep current price'}];
  const add=(c,key,title)=>{if(c&&!options.some(o=>o.price===c.price))options.push({...c,key,title:key==='suggested'?title:c.price<current?'Lower-price option':'Higher-price option'});};
  add(winner,'suggested','Option for your priority');
  add(choose('volume')||lower.at(-1),'volume','Try a lower price');
  add(choose('earnings')||higher[0],'earnings','Try a higher price');
  // Keep comparisons concise without losing the selected result.
  return {state:winner?'ready':'no_safe_option',baseline,options:options.slice(0,3),selected:winner||baseline,goal,band,cost,tolerance,
    evidenceLimited:rec.quality.status!=='ready'||rec.requires_review,ceiling};
}

export function decisionMessage(p,result){
  const {state,selected:s,baseline:b}=result;
  if(state==='no_stock')return {title:'Confirm stock before changing the price',body:'There are no units available to sell. A new price cannot fix availability.',action:'Check inventory'};
  if(state==='no_sales')return {title:'Collect sales history before estimating demand',body:'There are no recorded sales in the last 30 days. We cannot estimate a sales response from this baseline.',action:'Add sales history'};
  if(state==='no_market')return {title:'Refresh competitor prices first',body:'There is no fresh, available market benchmark. Keep the price decision on hold while you check sources.',action:'Check market evidence'};
  if(state==='no_safe_option')return {title:'Review costs before testing a new price',body:'No price in the small test range meets both the margin floor and your sales/earnings constraint. Do not treat the current price as approved.',action:'Review product costs'};
  if(s.price===b.price)return {title:'Keep the current price for now',body:'Within this test range, no alternative improves the selected objective while meeting its constraints across the assumed customer responses.',action:'Save comparison'};
  if(s.price<b.price)return {title:'Consider a small price reduction',body:'This option favors unit sales. Compare the possible reduction in total contribution before choosing it.',action:'Save test plan'};
  return {title:'Consider a small price increase',body:'This option protects contribution. Some unit sales may be lost; the comparison below makes that trade-off visible.',action:'Save test plan'};
}
