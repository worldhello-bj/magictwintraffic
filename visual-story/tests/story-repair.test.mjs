import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {createHash, webcrypto} from 'node:crypto';
import {fileURLToPath} from 'node:url';
import vm from 'node:vm';
const root=fileURLToPath(new URL('../', import.meta.url));
const source=readFileSync(root+'src/story.js','utf8');
const read=(f)=>JSON.parse(readFileSync(root+'dist/story-data/'+f));
const catalog=read('catalog.json'),network=read('network.json');
const entry=readFileSync(root+'dist/story.html','utf8');
const asset=(ext)=>root+'dist'+entry.match(new RegExp('/assets/story-[A-Za-z0-9_-]+\\.'+ext))[0];
const nodes=new Map();
function element(id){if(!nodes.has(id))nodes.set(id,{id,innerHTML:'',textContent:'',value:'1',hidden:false,disabled:false,dataset:{},attrs:{},classList:{add(){},remove(){},toggle(){}},setAttribute(k,v){this.attrs[k]=v},addEventListener(){},removeEventListener(){},scrollIntoView(){}});return nodes.get(id)}
const context=vm.createContext({console,Map,Set,Number,Math,String,Object,Array,Error,DOMException,AbortController,TextDecoder,crypto:webcrypto,performance:{now:()=>0},cancelAnimationFrame(){},requestAnimationFrame(){return 1},document:{querySelector:()=>element('story-app'),getElementById:element,querySelectorAll:()=>[],addEventListener(){},documentElement:{classList:{add(){}}}},window:{addEventListener(){},removeEventListener(){}},fetch:async(path)=>{const bytes=readFileSync(root+'dist/'+path.replace(/^\.\//,''));return {ok:true,arrayBuffer:async()=>bytes.buffer.slice(bytes.byteOffset,bytes.byteOffset+bytes.byteLength)}}});
vm.runInContext(source.replace(/^import[^;]+;/,'').replace(/ce\(\);\s*$/,'')+`;globalThis.api={me,ue,fe,T,be,O,q,ee,te,H,ne,C,we,I,ie,re,Se,xe,$e,E,le,oe,setup(c,net){g=c;z=net},setPair(a,b,ra,rb,frame,compare=true){f=a;u=b;w=ra;$=rb;d=frame;x=compare;j=true},state(){return {j,d,N,f,u,x,comparisonPreference}},resetPreference(){comparisonPreference=undefined},viewSpy(first,second){v=[{update:first},{update:second}]},selectRoad(index){k=index;_e()},setClock(frame){d=frame;U=frame;J=0;N=true},template:ge.innerHTML};`,context);
const api=context.api;api.setup(catalog,network);
test('source and deployed assets agree; all frozen data hashes still match',()=>{
 assert.equal(source,readFileSync(asset('js'),'utf8'));
 for(const ext of ['js','css'])assert.ok(asset(ext).endsWith(createHash('sha256').update(readFileSync(root+'src/story.'+ext)).digest('hex').slice(0,12)+'.'+ext));
 assert.equal(readFileSync(root+'src/story.css','utf8'),readFileSync(asset('css'),'utf8'));
 for(const item of [catalog.network,...catalog.runs])assert.equal(createHash('sha256').update(readFileSync(root+'dist/story-data/'+item.file)).digest('hex'),item.sha256,item.file);
});
test('all 40 records validate with 24 windows and 240 vehicle samples',()=>{
 api.me(catalog);api.ue(network,catalog.network.network_hash);
 for(const meta of catalog.runs){const run=read(meta.file);api.fe(run,meta,network.edges.length);assert.equal(run.windows.length,24);assert.equal(run.series.length,240);assert.equal(run.series.at(-1)[3],meta.completed);}
});
test('person columns never enter window displays; final totals include every unfinished status',()=>{
 assert.ok(!source.includes('person-ledger'));assert.ok(!source.includes('计划已到期'));assert.ok(!source.includes('function Ae('));
 for(const meta of catalog.runs){const base=catalog.runs.find(x=>x.id===meta.reference_id),a=read(base.file),b=read(meta.file);const totals=api.te(base,meta);assert.equal(totals.residualB,meta.cohort-meta.completed);
  // Poison person-event columns: the interface must not consume them at any playback position.
  for(const run of [a,b])for(const row of run.series)for(const col of [3,5,6,7])row[col]=987654321;
  api.fe(a,base,network.edges.length);api.fe(b,meta,network.edges.length);
  api.setPair(base,meta,a,b,0);api.$e();const fixed=element('result-strip').innerHTML;
  for(let frame=0;frame<24;frame++){api.setPair(base,meta,a,b,frame);api.E();assert.equal(element('result-strip').innerHTML,fixed);assert.ok(!element('queue-chart').innerHTML.includes('987654321'));assert.ok(!element('map-count-a').textContent.includes('987654321'));}
 }
});
test('timeline boundaries, speed, pause, restart, and scrubbing remain deterministic',()=>{
 assert.equal(api.T(-5),0);assert.equal(api.T(999),23);assert.equal(api.T(NaN),0);assert.equal(api.be(0,1600,1),1);assert.equal(api.be(0,1600,.5),0);assert.equal(api.be(0,1600,4),4);
 const meta=catalog.runs[0],run=read(meta.file);api.setPair(meta,meta,run,run,23);api.we();assert.equal(api.state().d,0);assert.equal(api.state().N,true);api.we();assert.equal(api.state().N,false);api.I(14);assert.equal(api.state().d,14);assert.equal(api.state().N,false);api.setClock(22);api.ie(1600);assert.equal(api.state().d,23);assert.equal(api.state().N,false);
 element('story-reset').onclick();assert.equal(api.state().d,0);element('story-next').onclick();assert.equal(api.state().d,1);element('story-prev').onclick();assert.equal(api.state().d,0);
});
test('missing road observations differ from measured zero, comparison and speed controls remain wired',()=>{
 assert.notEqual(api.ee(undefined,'stopped'),api.ee(0,'stopped'));assert.notEqual(api.ee(undefined,'speed'),api.ee(0,'speed'));
 for(const id of ['zoom-in','zoom-out','reset-map','choose-metric','show-comparison','story-speed','apply-case'])assert.equal(typeof(element(id).onclick??element(id).onchange),'function');
 const meta=catalog.runs[0],run=read(meta.file);api.setPair(meta,meta,run,run,0,false);api.E();assert.equal(element('pane-b').hidden,true);element('show-comparison').checked=true;element('show-comparison').onchange();assert.equal(element('pane-b').hidden,false);
});
test('actual fetch, SHA verification, unavailable selection, retry and rapid newer selection',async()=>{
 await api.re('am',42,'baseline');assert.equal(api.state().u.id,'am_42_baseline');assert.equal(api.state().j,true);
 await api.re('am',43,'combined_0.5');assert.equal(api.state().j,false);assert.match(element('load-error').innerHTML,/第1组/);
 await api.re('pm',43,'bus');assert.equal(api.state().u.id,'pm_43_bus');assert.equal(api.state().j,true);
 await Promise.all([api.re('am',44,'priority'),api.re('pm',44,'walk')]);assert.equal(api.state().u.id,'pm_44_walk');assert.equal(api.state().j,true);
});
test('main guide, group names and folded methodology are present',()=>{
 assert.match(api.template,/先播放看变化/);assert.match(api.template,/<details id="method"/);assert.match(api.template,/<option value="42">第1组/);assert.ok(!api.template.includes('随机种子'));
 api.Se();assert.match(element('result-matrix').innerHTML,/第3组/);api.xe();assert.match(element('source-info').innerHTML,/不展示任何逐窗人数/);
});

test('main HTML has balanced structural elements after folding methodology',()=>{
 const stack=[],voids=new Set(['input','br','meta','link','img','hr']);
 for(const token of api.template.matchAll(/<(\/?)([a-z][a-z0-9-]*)\b[^>]*>/gi)){
  const tag=token[2].toLowerCase();if(voids.has(tag))continue;
  if(token[1])assert.equal(stack.pop(),tag,'balanced closing '+tag);else stack.push(tag);
 }assert.equal(stack.length,0);
});

test('unchecked and checked Apply preserve preference and keep maps, chart, readout and totals on the selected run',async()=>{
 let visibleRows;
 api.viewSpy(rows=>{visibleRows=rows},()=>{});
 function choose(policy='bus',period='pm',seed=43){element('choose-period').value=period;element('choose-seed').value=String(seed);element('choose-policy').value=policy;}
 function checkSingle(){
  const {u,f,d,x}=api.state(),target=read(u.file),reference=read(f.file);
  assert.equal(x,false);assert.equal(element('show-comparison').checked,false);assert.equal(element('pane-b').hidden,true);
  assert.equal(element('label-a').textContent,u.label);assert.equal(element('chart-label-a').textContent,u.label);assert.equal(element('panel-key-a').textContent,'B');
  assert.equal(JSON.stringify([...visibleRows.values()]),JSON.stringify(target.windows[d]));
  assert.equal(element('map-count-a').textContent,`窗末停等 ${target.series[(d+1)*10-1][2].toLocaleString('zh-CN')} 辆`);
  const ceiling=Math.ceil(Math.max(100,...target.series.map(r=>r[2]),...reference.series.map(r=>r[2]))/500)*500;
  const path=target.series.map((r,i)=>`${i?'L':'M'}${(44+r[0]/7200*694).toFixed(2)},${(106-r[2]/ceiling*84).toFixed(2)}`).join(' ');
  assert.ok(element('queue-chart').innerHTML.includes(`d="${path}"`));assert.ok(!element('queue-chart').innerHTML.includes('series-line series-b'));
  assert.ok(element('result-strip').innerHTML.includes(`<strong>${u.completed.toLocaleString('zh-CN')}<em>人</em>`));
  assert.ok(element('result-strip').innerHTML.includes(`<strong>${(u.cohort-u.completed).toLocaleString('zh-CN')}<em>人</em>`));assert.ok(!element('result-strip').innerHTML.includes('<b>→</b>'));
  const road=target.windows[d][0]?.[0];if(road!==undefined){api.selectRoad(road);assert.ok(element('road-readout').innerHTML.includes(`B ${u.label}：`));}
 }
 api.resetPreference();await api.oe(0);assert.equal(api.state().x,false);await api.oe(1);assert.equal(api.state().x,true);
 element('show-comparison').checked=false;element('show-comparison').onchange();choose();await element('apply-case').onclick();checkSingle();
 const fixed=element('result-strip').innerHTML;api.I(23);checkSingle();assert.equal(element('result-strip').innerHTML,fixed);
 await api.oe(3);checkSingle();assert.equal(api.state().u.id,'am_44_priority');choose('walk','am',42);await element('apply-case').onclick();checkSingle();
 element('show-comparison').checked=true;element('show-comparison').onchange();choose();await element('apply-case').onclick();
 assert.equal(api.state().x,true);assert.equal(element('show-comparison').checked,true);assert.equal(element('pane-b').hidden,false);assert.equal(element('label-a').textContent,api.state().f.label);assert.equal(element('label-b').textContent,api.state().u.label);assert.ok(element('result-strip').innerHTML.includes('<b>→</b>'));
 await api.oe(0);assert.equal(api.state().x,true);await api.oe(2);assert.equal(api.state().x,true);
 // Applying an unchecked value works even if an event was not dispatched first.
 element('show-comparison').checked=false;choose('priority','am',44);await element('apply-case').onclick();checkSingle();
});
