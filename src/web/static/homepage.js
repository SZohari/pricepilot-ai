import {esc} from './utils.js';

const photo=(name,alt,hero=false,cls='')=>`<img class="${cls}" src="/static/assets/images/${name}-960.webp" srcset="/static/assets/images/${name}-640.webp 640w, /static/assets/images/${name}-960.webp 960w, /static/assets/images/${name}-1536.webp 1536w" sizes="${hero?'(max-width: 760px) 100vw, 52vw':'(max-width: 760px) 100vw, 45vw'}" width="1536" height="1024" alt="${esc(alt)}" ${hero?'fetchpriority="high" loading="eager"':'loading="lazy"'} decoding="async">`;
const arrow='<span aria-hidden="true">↗</span>';
const cta=(action,label,extra='',primary=true)=>`<button class="home-button ${primary?'home-button-primary':''}" data-advisor="${action}" ${extra}>${label}${arrow}</button>`;
const chapters=[
  {image:'journey-stock',alt:'Illustration of preparing a watch catalog and stock records',caption:'01 / Get the business inputs ready',label:'Bring the data',title:'Start with the shop you actually run.',body:'Import a catalog or add one product. Keep the exact variant, what you paid, what replacing it costs and what customers pay in view.',headline:'Your catalog, checked.',detail:'Map the columns, check each row and confirm before saving. Existing SKUs are never silently overwritten.',action:'shop',cta:'Start with the guided setup',tone:'compare'},
  {image:'journey-compare',alt:'Illustration of comparing watches and considering the full offer',caption:'02 / Compare the offer, not just the number',label:'See the decision',title:'Understand what matters before moving a price.',body:'See which costs a sale covers, which competitor offers really match and what you still need to learn from customers.',headline:'A reason for the next step.',detail:'Cost pressure, low visibility and slow stock do not all call for a discount. Open the watch shop and follow the evidence.',action:'shop',cta:'Work through the five steps',tone:'listen'},
  {image:'journey-review',alt:'Illustration of a retailer reviewing an order workflow',caption:'03 / Make the next move and follow it up',label:'Learn what works',title:'Make a small move. Keep the result.',body:'Choose the limits, apply the change in your own shop and record what happened. Sales, the money left and other changes all belong in the review.',headline:'A plan you can follow.',detail:'A price test has a sales target and a review date. That target is a condition to check, not a promise about demand.',action:'shop',cta:'Build a plan step by step',tone:'test'},
];
function welcomeAnswer(chapter,mobile=false){return `<div class="home-answer ${mobile?'home-answer-inline':''}" data-tone="${chapter.tone}"><span class="home-label">${chapter.label}</span><h3>${chapter.headline}</h3><p>${chapter.detail}</p>${cta(chapter.action,chapter.cta,'',false)}</div>`;}
function story(){return `<section class="home-story home-wrap" id="home-how" aria-labelledby="home-story-title"><div class="home-section-heading" data-home-reveal><span class="home-label">FROM A CATALOG TO A CLEARER DECISION</span><h2 id="home-story-title">Your shop.<br><em>A thoughtful next move.</em></h2><p>A working example of an online watch shop.<br>Bring the data, question the suggestion, follow the result.</p></div><div class="home-story-layout"><div class="home-story-visual"><div class="home-story-photo">${chapters.map((c,i)=>`<div class="home-story-frame" data-home-photo="${i}" ${i?'hidden':''}>${photo(c.image,c.alt)}<span class="home-photo-label">${c.caption}<br>Kiez & Co · Fictional watch shop</span></div>`).join('')}</div><div class="home-story-console"><div class="home-story-tabs" role="group" aria-label="Explore the retailer workflow">${chapters.map((c,i)=>`<button data-home-step="${i}" aria-pressed="${i===0}" aria-controls="home-chapter-${i}"><span>0${i+1}</span>${c.label}</button>`).join('')}</div><div class="home-story-panels">${chapters.map((c,i)=>`<div data-home-panel="${i}" ${i?'hidden':''}>${welcomeAnswer(c)}</div>`).join('')}</div></div></div><div class="home-story-chapters">${chapters.map((c,i)=>`<article class="home-chapter" id="home-chapter-${i}" data-home-chapter="${i}" tabindex="-1"><span class="home-chapter-number">0${i+1}<span aria-hidden="true"></span></span><span class="home-label">${c.label}</span><h3>${c.title}</h3><p>${c.body}</p>${i===0?'<div class="home-test-note"><span aria-hidden="true">↳</span><p>One row per exact product.<br>Costs with a clear meaning.<br>A preview before anything is saved.</p></div>':i===1?'<blockquote>“What do we know about our customers that a list of prices cannot tell us?”<cite>The owner’s knowledge belongs in the decision.</cite></blockquote>':'<div class="home-test-note"><span aria-hidden="true">↳</span><p>Choose a price to try.<br>Protect earnings and sales.<br>Review what actually changed.</p></div>'}<div class="home-chapter-image">${photo(c.image,c.alt)}</div>${welcomeAnswer(c,true)}</article>`).join('')}</div></div><p class="home-story-footnote">Useful calculations. Visible assumptions. The final decision stays with the business.</p></section>`;}
const cases=[
  {sku:'DE-WEAR-004',photo:'design-store',label:'THE SAME SHOP / COST PRESSURE',title:'The supplier raised<br>the price.',alt:'Illustration of a warm independent retail space'},
  {sku:'DE-WEAR-001',photo:'watch-details',label:'THE SAME SHOP / MARKET COMPARISON',title:'Other sellers<br>charge less.',alt:'Illustrative unbranded smartwatches, not photographs of the demo models'},
  {sku:'DE-WEAR-006',photo:'watch-packing',label:'THE SAME SHOP / SLOW STOCK',title:'Stock is sitting.<br>What needs to change?',alt:'Illustration of a watch retailer packing an online order'},
];

export function homepage(a,S){
  return `<div class="home-page" id="home-top">
    <header class="home-header home-wrap"><a href="#overview" data-home-jump="home-top" class="home-brand" aria-label="PricePilot home"><span class="home-brand-icon" aria-hidden="true">p<span>↗</span></span>PricePilot<span class="home-brand-period">.</span></a><nav aria-label="Homepage"><button data-home-jump="home-how">How it helps</button><button data-home-jump="home-cases">Try an example</button><button data-advisor="plans">My plans${a.plans.length?` <span>${a.plans.length}</span>`:''}</button></nav><button class="home-motion" data-home-motion aria-pressed="true" title="Turn decorative movement on or off">Motion on <span aria-hidden="true">◉</span></button></header>
    <section class="home-hero home-wrap" aria-labelledby="home-title">
      <div class="home-hero-copy"><div class="home-label home-availability"><span></span>PRICING ADVICE FOR YOUR NEXT MOVE</div><h1 id="home-title">A better price.<br><em>A clearer<br>next step.</em></h1><p>You know your business. Build a pricing routine, one clear step at a time. We check the numbers. You choose the next move.</p><div class="home-hero-actions">${cta('shop',S.journey?.id?'Continue my pricing setup':'Build my pricing routine')}<button class="home-text-link" data-home-jump="home-how">See how it works <span aria-hidden="true">↓</span></button></div><small>Interactive prototype · Germany / EUR<br>Five guided steps · No account needed.${S.journey?.id?`<br><span class="home-resume-note">Your setup is waiting at step ${S.journey.step+1} of 5.</span>`:''}</small></div>
      <figure class="home-hero-picture"><div class="home-hero-image">${photo('design-store','Illustration of a warmly lit independent shop, with ceramics and an oak counter',true)}</div><figcaption><span>For the decisions<br>behind every price.</span><span class="home-picture-index">01 — 03<br>INDEPENDENT BUSINESS</span></figcaption><div class="home-photo-note"><span class="home-note-symbol" aria-hidden="true">↗</span><div><strong>“Should I change my price?”</strong><span>Start with what your business needs.</span></div></div></figure>
    </section>
    <div class="home-promise home-wrap"><span>SELL WELL.</span><span>EARN ENOUGH.</span><span>LEARN WHAT WORKS.</span><button data-home-jump="home-how" aria-label="See how PricePilot helps"><span aria-hidden="true">↓</span></button></div>
    ${story()}
    <section class="home-cases" id="home-cases" aria-labelledby="home-cases-title"><div class="home-wrap"><div class="home-section-heading home-cases-heading" data-home-reveal><div><span class="home-label">MAKE IT YOUR DECISION</span><h2 id="home-cases-title">Sounds <em>familiar?</em></h2></div><p>Choose a starting point.<br>Change the numbers. See the advice change.</p></div>
      <div class="home-case-grid">${cases.map((c,i)=>`<button class="home-case" data-advisor="shop" data-sku="${c.sku}" data-home-reveal><div class="home-case-photo">${photo(c.photo,c.alt)}<span class="home-case-number">0${i+1}</span><span class="home-case-arrow" aria-hidden="true">↗</span></div><span class="home-label">${c.label}</span><h3>${c.title}</h3><span class="home-case-link">Explore this shop decision <span aria-hidden="true">→</span></span></button>`).join('')}</div><p class="home-case-disclosure">One fictional online shop. Simulated prices, costs and sales. Illustrative images made with AI; they do not depict specific retail models.</p>
    </div></section>
    <section class="home-closing home-wrap" data-home-reveal><span class="home-label">YOUR BUSINESS. YOUR CALL.</span><h2>Less second-guessing.<br><em>One useful next step.</em></h2><p>Start with the watch shop example.<br>Or bring the products and costs you already work with.</p>${cta('import-products','Bring my product data')}<p><button class="home-text-link" data-advisor="shop">Keep exploring the demo <span aria-hidden="true">→</span></button></p></section>
    <footer class="home-footer home-wrap"><div><a class="home-brand" href="#overview" data-home-jump="home-top">PricePilot<span class="home-brand-period">.</span></a><p>Better questions. Better pricing decisions.</p></div><nav aria-label="More about PricePilot"><a href="#market">Check competitor prices ↗</a><a href="#method">The thinking behind it ↗</a><a href="#learning">Explore the ML lab ↗</a></nav><div class="home-footer-note">A working MVP.<br>Every price change stays your decision.</div></footer>
  </div>`;
}

export function activeChapter(tops,viewportHeight){
  let active=0;
  tops.forEach((top,i)=>{if(top<=viewportHeight*.54)active=i;});
  return active;
}

export function heroTravel(top,height){return Math.min(1,Math.max(0,-top/Math.max(1,height)))*30;}

/** Native scrolling; no wheel handlers, synthetic scroll area or animation library. */
export function bindHomepage(root,a,env=window){
  const page=root.querySelector('.home-page');if(!page)return ()=>{};
  if(a.homeScroll>0)env.scrollTo?.({top:a.homeScroll,behavior:'instant'});
  const media=env.matchMedia('(prefers-reduced-motion: reduce)');
  const hero=root.querySelector('.home-hero');
  const chapterEls=[...root.querySelectorAll('[data-home-chapter]')];
  const panels=[...root.querySelectorAll('[data-home-panel]')];
  const photos=[...root.querySelectorAll('[data-home-photo]')];
  const tabs=[...root.querySelectorAll('[data-home-step]')];
  const motionButton=root.querySelector('[data-home-motion]');
  let storedMotion=true;
  try{storedMotion=env.localStorage.getItem('pricepilot-home-motion')!=='off';}catch{/* Private browsing can disable storage. */}
  let disposed=false,frame=0,current=-1,animate=false;
  const select=index=>{
    if(index===current)return;current=index;a.discoveryStep=index;page.dataset.chapter=String(index);
    panels.forEach((p,i)=>{p.hidden=i!==index;});
    photos.forEach((p,i)=>{p.hidden=i!==index;});
    tabs.forEach((t,i)=>t.setAttribute('aria-pressed',String(i===index)));
    chapterEls.forEach((c,i)=>c.classList.toggle('is-current',i===index));
  };
  const update=()=>{
    frame=0;if(disposed||!root.isConnected)return;a.homeScroll=env.scrollY||0;
    select(activeChapter(chapterEls.map(c=>c.getBoundingClientRect().top),env.innerHeight));
    if(animate&&hero){const rect=hero.getBoundingClientRect();hero.style.setProperty('--hero-travel',`${heroTravel(rect.top,rect.height)}px`);}
  };
  const schedule=()=>{if(!disposed&&!frame)frame=env.requestAnimationFrame(update);};
  const motion=()=>{
    animate=storedMotion&&!media.matches;page.classList.toggle('home-has-motion',animate);
    motionButton.setAttribute('aria-pressed',String(animate));
    motionButton.disabled=media.matches;
    motionButton.textContent=animate?'Motion on ◉':'Motion off ○';
    motionButton.title=media.matches?'Your device is set to reduce motion':'Turn decorative movement on or off';
    if(!animate&&hero)hero.style.setProperty('--hero-travel','0px');schedule();
  };
  const jump=(target,focus=false)=>{target?.scrollIntoView({behavior:animate?'smooth':'instant',block:'start'});if(focus)target?.focus({preventScroll:true});};
  const click=e=>{
    const toggle=e.target.closest('[data-home-motion]');
    if(toggle){storedMotion=!storedMotion;try{env.localStorage.setItem('pricepilot-home-motion',storedMotion?'on':'off');}catch{}motion();return;}
    const step=e.target.closest('[data-home-step]');
    if(step){const index=Number(step.dataset.homeStep);select(index);jump(chapterEls[index],true);return;}
    const link=e.target.closest('[data-home-jump]');
    if(link){e.preventDefault();const target=root.querySelector('#'+link.dataset.homeJump);if(target){target.setAttribute('tabindex','-1');jump(target,true);}}
  };
  root.addEventListener('click',click);
  env.addEventListener('scroll',schedule,{passive:true});env.addEventListener('resize',schedule);
  media.addEventListener('change',motion);
  let observer;
  if(env.IntersectionObserver){observer=new env.IntersectionObserver(entries=>{for(const entry of entries)if(entry.isIntersecting){entry.target.classList.add('is-visible');observer.unobserve(entry.target);}},{threshold:.08});root.querySelectorAll('[data-home-reveal]').forEach(el=>observer.observe(el));}
  motion();
  return ()=>{disposed=true;if(frame)env.cancelAnimationFrame(frame);observer?.disconnect();root.removeEventListener('click',click);env.removeEventListener('scroll',schedule);env.removeEventListener('resize',schedule);media.removeEventListener('change',motion);};
}
