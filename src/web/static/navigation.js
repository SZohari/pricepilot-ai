import {esc} from './utils.js';

export function parseRoute(hash, pages){
  const [page,part]=hash.replace(/^#/,'').split('/');
  return {page:pages.includes(page)?page:'overview',step:page==='shop'&&/^[1-5]$/.test(part||'')?Number(part)-1:null};
}

// pushState records a completed transition without rebuilding an active form.
// Back/Forward between different fragments is handled by the app hashchange listener.
export function recordJourneyStep(a, env=window){
  if(!env.history||!env.location?.hash.startsWith('#shop'))return;
  const hash=`#shop/${a.step+1}`;
  if(env.location.hash!==hash){
    const method=a.renderedStep===undefined?'replaceState':'pushState';
    env.history[method]({pricepilotStep:a.step,previousStep:a.renderedStep??null},'',hash);
  }
  a.renderedStep=a.step;
}

export function experienceNavigation(S,nav){
  const resume=S.journey?.id;
  return `<a class="experience-brand" href="#overview">PricePilot<span>.</span></a><nav aria-label="Main pages"><a href="#overview">Welcome</a><a href="#shop" ${S.page==='shop'?'aria-current="page"':''}>${resume?'Continue my setup':'Start pricing setup'}</a><a href="#plans" ${S.page==='plans'?'aria-current="page"':''}>Saved plans</a><details class="experience-more"><summary>Tools</summary><div>${nav.filter(([id])=>!['overview','shop','plans'].includes(id)).map(([id,label])=>`<a href="#${esc(id)}">${esc(label)}</a>`).join('')}</div></details></nav>`;
}
