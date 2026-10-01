import test from 'node:test';
import assert from 'node:assert/strict';
import {parseRoute,recordJourneyStep,experienceNavigation} from '../../src/web/static/navigation.js';
import {openQuestions,collectionPanel} from '../../src/web/static/evidence.js';

test('step routes are bounded; unknown pages cannot hide the way home',()=>{
  const pages=['overview','shop','plans'];
  assert.deepEqual(parseRoute('#shop/3',pages),{page:'shop',step:2});
  assert.deepEqual(parseRoute('#shop/99',pages),{page:'shop',step:null});
  assert.deepEqual(parseRoute('#bad',pages),{page:'overview',step:null});
  const html=experienceNavigation({page:'shop',journey:{id:'SKU'}},pages.map(p=>[p,p]));
  assert.match(html,/href="#overview">Welcome/);assert.match(html,/Continue my setup/);
});

test('internal steps create browser history once; repaint does not create duplicate entries',()=>{
  const calls=[],env={location:{hash:'#shop'},history:{replaceState(state,_,hash){calls.push(['replace',state]);env.location.hash=hash;},pushState(state,_,hash){calls.push(['push',state]);env.location.hash=hash;}}};
  const a={step:0};recordJourneyStep(a,env);a.step=1;recordJourneyStep(a,env);recordJourneyStep(a,env);
  assert.equal(env.location.hash,'#shop/2');assert.equal(calls.length,2);
  assert.deepEqual(calls[1],['push',{pricepilotStep:1,previousStep:0}]);
  env.location.hash='#overview';a.step=2;recordJourneyStep(a,env);assert.equal(calls.length,2);
});

test('unmeasured factors stay attributed, escaped and linked to an observation plan',()=>{
  const html=openQuestions({discovery:{open_questions:[{topic:'trust',basis:'hypothesis',statement:'<script>bad</script>',evidence_note:'',resolve_first:true,collect:'Ask about warranty',interpret:'Not a trust score',checked_on:'2026-09-26'}]}},true);
  assert.doesNotMatch(html,/<script>/);assert.match(html,/Untested idea/);assert.match(html,/Resolve before a price test/);assert.match(html,/Ask about warranty/);assert.match(html,/No numerical score inferred/);
});

test('collection controls disclose source setup and never present simulated offers as collected',()=>{
  const base={item:{details:null},mode:'demo',canWrite:true,canConfigure:true,sourceCount:0};
  assert.doesNotMatch(collectionPanel(base),/id="journey-source-form"/);
  assert.match(collectionPanel(base),/offers are simulated/);
  const own=collectionPanel({...base,mode:'merchant'});
  assert.match(own,/data-journey="collect" disabled/);assert.match(own,/Connect & check/);
  assert.match(own,/Costs, private sales and customer motives/);
});
