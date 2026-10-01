export const esc = v => String(v ?? '').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
export const money = v => v == null ? '—' : new Intl.NumberFormat('de-DE',{style:'currency',currency:'EUR',maximumFractionDigits:2}).format(Number(v));
export const pct = v => v == null ? '—' : (Number(v)*100).toFixed(1)+'%';
export const label = v => String(v).replaceAll('_',' ').replace(/^./,c=>c.toUpperCase());
export const paths = {
market:'M12 2a10 10 0 1 0 0 20 10 10 0 0 0 0-20 M2 12h20 M12 2c-6 6-6 14 0 20 M12 2c6 6 6 14 0 20',
overview:'M3 3h7v7H3z M14 3h7v7h-7z M3 14h7v7H3z M14 14h7v7h-7z',
decisions:'M4 17l5-5 4 3 7-10 M15 5h5v5 M4 4v16h16',
catalog:'M12 3l9 5-9 5-9-5z M3 8v9l9 5 9-5V8 M12 13v9 M7.5 5.5l9 5',
scenarios:'M5 3v18 M12 3v18 M19 3v18 M2 8h6 M9 16h6 M16 7h6',
data:'M3 6c0-4 18-4 18 0s-18 4-18 0 M3 6v12c0 4 18 4 18 0V6 M3 12c0 4 18 4 18 0',
search:'M10 3a7 7 0 1 0 0 14 7 7 0 0 0 0-14 M15 15l6 6',
refresh:'M20 7a9 9 0 1 0 1 7 M20 2v5h-5',
watch:'M8 7V2h8v5 M8 17v5h8v-5 M8 7h8a3 3 0 0 1 3 3v4a3 3 0 0 1-3 3H8a3 3 0 0 1-3-3v-4a3 3 0 0 1 3-3z M12 9v3l2 1 M19 10h2',
close:'M6 6l12 12 M6 18L18 6',arrow:'M5 12h14 M14 7l5 5-5 5',
download:'M12 3v12 M7 10l5 5 5-5 M4 16v5h16v-5',
plus:'M12 4v16 M4 12h16',shield:'M12 2l8 4v6c0 5-8 10-8 10S4 17 4 12V6z M8 12l3 3 5-6',
menu:'M4 6h16 M4 12h16 M4 18h16',globe:'M12 2a10 10 0 1 0 0 20 10 10 0 0 0 0-20 M2 12h20 M12 2c-6 6-6 14 0 20 M12 2c6 6 6 14 0 20'
};
export const icon = name => '<svg class="icon" viewBox="0 0 24 24" aria-hidden="true"><path d="'+(paths[name]||paths.watch)+'"/></svg>';
export const strategies=['trust_builder','balanced','profit_protection','market_penetration','premium_positioning','clearance_cashflow'];
export function safeLink(url){try{const u=new URL(url);return u.protocol==='https:'?esc(u.href):'';}catch{return '';}}
export function summarize(products,recs){return {count:products.length,margin:recs.length?recs.reduce((s,r)=>s+Number(r.current_margin),0)/recs.length:0,stock:products.reduce((s,p)=>s+p.inventory*Number(p.replacement_cost_net),0),review:recs.filter(r=>r.requires_review).length,ready:recs.filter(r=>r.quality.status==='ready').length};}
