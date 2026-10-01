import test from 'node:test';
import assert from 'node:assert/strict';
import {homepage,activeChapter,heroTravel,bindHomepage} from '../../src/web/static/homepage.js';

const data=()=>({plans:[]});

test('welcome landing opens the same shop and its three actual SKU decisions',()=>{
  const html=homepage(data(),{entries:[]});
  for(const sku of ['DE-WEAR-001','DE-WEAR-004','DE-WEAR-006'])assert.match(html,new RegExp('data-sku="'+sku+'"'));
  assert.match(html,/data-advisor="shop"/);assert.match(html,/data-advisor="import-products"/);
  assert.match(html,/One fictional online shop/);assert.match(html,/Illustrative images made with AI/);
  assert.doesNotMatch(html,/portrait-studio|cycle-workshop|discovery-open|Photography|hamburg/i);
});
test('landing describes the workflow without pretending to calculate a price',()=>{
  const html=homepage(data(),{});
  assert.match(html,/Bring the data/);assert.match(html,/See the decision/);assert.match(html,/Learn what works/);
  assert.match(html,/condition to check, not a promise/);assert.doesNotMatch(html,/€|predicted profit|optimal price/i);
});
test('new illustrative photos include responsive sizes and the explanatory jump has the correct destination',()=>{
  const html=homepage(data(),{});
  assert.match(html,/watch-packing-640.webp/);assert.match(html,/watch-details-1536.webp/);
  assert.match(html,/data-home-jump="home-how">See how it works/);
  assert.match(html,/width="1536" height="1024"/);
  for(const name of ['stock','compare','review'])assert.match(html,new RegExp(`journey-${name}-960.webp`));
  assert.equal((html.match(/data-home-photo="/g)||[]).length,3);
  assert.equal((html.match(/class="home-chapter-image"/g)||[]).length,3);
});
test('fast scrolls and reverse scrolls select the visible chapter, with bounded photo travel',()=>{
  assert.equal(activeChapter([1000,1700,2400],800),0);
  assert.equal(activeChapter([-800,-100,600],800),1);
  assert.equal(activeChapter([-2400,-1700,-900],800),2);
  assert.equal(activeChapter([100,800,1500],800),0);
  assert.equal(heroTravel(400,600),0);assert.equal(heroTravel(-300,600),15);
  assert.equal(heroTravel(-5000,0),30);
});

function fixture({reduced=false,stored=null,homeScroll=0}={}){
  const events=new Map(),rootEvents=new Map(),mediaEvents=new Map(),frames=new Map();let frameId=0;
  const classes=()=>{const values=new Set();return {toggle:(k,on)=>on?values.add(k):values.delete(k),has:k=>values.has(k)};};
  const el=(dataset={})=>({dataset,attributes:{},classList:classes(),hidden:false,setAttribute(k,v){this.attributes[k]=v;},focus(){this.focused=true;},scrollIntoView(options){this.scrolled=options;}});
  const page=el(),hero=el(),button=el();hero.style={setProperty(k,v){this[k]=v;}};hero.getBoundingClientRect=()=>({top:-100,height:600});
  const chapters=[0,1,2].map(i=>({...el(),top:i*700+100,getBoundingClientRect(){return {top:this.top};}}));
  const tabs=[0,1,2].map(i=>el({homeStep:String(i)}));const panels=[0,1,2].map(()=>el());
  const photos=[0,1,2].map(()=>el());
  const root={isConnected:true,querySelector:s=>({'.home-page':page,'.home-hero':hero,'[data-home-motion]':button,'#home-how':chapters[0]}[s]),querySelectorAll:s=>({'[data-home-chapter]':chapters,'[data-home-panel]':panels,'[data-home-photo]':photos,'[data-home-step]':tabs,'[data-home-reveal]':[]}[s]||[]),addEventListener:(k,f)=>rootEvents.set(k,f),removeEventListener:k=>rootEvents.delete(k)};
  const media={matches:reduced,addEventListener:(k,f)=>mediaEvents.set(k,f),removeEventListener:k=>mediaEvents.delete(k)};
  const env={innerHeight:800,scrollY:0,scrollTo({top}){this.scrollY=top;},matchMedia:()=>media,localStorage:{getItem:()=>stored,setItem:(k,v)=>{stored=v;}},addEventListener:(k,f)=>events.set(k,f),removeEventListener:k=>events.delete(k),requestAnimationFrame:f=>{frames.set(++frameId,f);return frameId;},cancelAnimationFrame:id=>frames.delete(id)};
  const a={homeScroll};const dispose=bindHomepage(root,a,env);
  const flush=()=>{const pending=[...frames.values()];frames.clear();pending.forEach(f=>f());};
  const click=(selector,target)=>{const event={preventDefault(){this.prevented=true;},target:{closest:s=>s===selector?target:null}};rootEvents.get('click')(event);return event;};
  return {a,env,page,hero,button,chapters,tabs,panels,photos,root,events,rootEvents,media,mediaEvents,frames,dispose,flush,click};
}
test('scroll updates the visible answer and selected button without rebuilding the page',()=>{
  const f=fixture();f.flush();assert.equal(f.a.discoveryStep,0);
  f.chapters.forEach(c=>c.top-=800);f.events.get('scroll')();f.events.get('scroll')();
  assert.equal(f.frames.size,1);f.flush();
  assert.equal(f.a.discoveryStep,1);assert.equal(f.panels[0].hidden,true);assert.equal(f.panels[1].hidden,false);
  assert.deepEqual(f.photos.map(p=>p.hidden),[true,false,true]);
  assert.equal(f.tabs[1].attributes['aria-pressed'],'true');f.dispose();
});
test('keyboard step buttons expose the same answer and move focus to its chapter',()=>{
  const f=fixture();f.flush();f.click('[data-home-step]',f.tabs[2]);
  assert.equal(f.a.discoveryStep,2);assert.equal(f.chapters[2].focused,true);
  assert.deepEqual(f.photos.map(p=>p.hidden),[true,true,false]);
  assert.deepEqual(f.chapters[2].scrolled,{behavior:'smooth',block:'start'});f.dispose();
});
test('homepage jump links retain the route and place focus at their destination',()=>{
  const f=fixture();f.flush();const event=f.click('[data-home-jump]',{dataset:{homeJump:'home-how'}});
  assert.equal(event.prevented,true);assert.equal(f.chapters[0].focused,true);
  assert.equal(f.chapters[0].attributes.tabindex,'-1');f.dispose();
});
test('reduced motion disables transforms and smooth jumps but preserves all answers',()=>{
  const f=fixture({reduced:true});f.flush();
  assert.equal(f.page.classList.has('home-has-motion'),false);assert.equal(f.button.disabled,true);
  assert.equal(f.hero.style['--hero-travel'],'0px');
  f.click('[data-home-step]',f.tabs[2]);assert.equal(f.panels[2].hidden,false);
  assert.equal(f.chapters[2].scrolled.behavior,'instant');f.dispose();
});
test('motion preference survives storage and responds to an OS preference change',()=>{
  const f=fixture({stored:'off'});f.flush();assert.equal(f.button.attributes['aria-pressed'],'false');
  f.click('[data-home-motion]',f.button);assert.equal(f.button.attributes['aria-pressed'],'true');
  f.media.matches=true;f.mediaEvents.get('change')();assert.equal(f.button.attributes['aria-pressed'],'false');f.dispose();
});
test('leaving the homepage cancels pending work and releases global listeners',()=>{
  const f=fixture();assert.equal(f.frames.size,1);f.dispose();
  assert.equal(f.frames.size,0);assert.equal(f.events.size,0);assert.equal(f.mediaEvents.size,0);assert.equal(f.rootEvents.size,0);
});
test('scroll events for a detached homepage cannot change the consultation state',()=>{
  const f=fixture();f.flush();f.root.isConnected=false;f.chapters.forEach(c=>c.top-=3000);
  f.events.get('scroll')();f.flush();assert.equal(f.a.discoveryStep,0);f.dispose();
});


test('returning to welcome restores the prior scroll position and offers the current setup',()=>{
  const f=fixture({homeScroll:900});try{f.flush();assert.equal(f.env.scrollY,900);assert.equal(f.a.homeScroll,900);
    const html=homepage(data(),{journey:{id:'W1',step:2}});assert.match(html,/Continue my pricing setup/);
  }finally{f.dispose();}
});
