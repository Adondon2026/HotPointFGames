/* Main + ZMZ pagination: pagination, no touch-scroll handoff, cross-page selections. */
'use strict';
const fs=require('fs'),assert=require('assert'),vm=require('vm');
const read=p=>fs.readFileSync(__dirname+'/../'+p,'utf8');
const html=read('web/90_shell_after_games.html'),css=read('web/lite.css'),build=read('build.py');
const script=read('web/siege_buff_pages.js');
const catalog=read('web/games/siege_catalog.js');
const keys=(catalog.match(/const siegeV24Keys=\[([^\]]+)\]/)||[])[1]?.match(/'[^']+'/g)||[];
assert.equal(keys.length,28,'v24 catalog must contain 28 gains');
assert(build.includes('read("web/siege_buff_pages.js")'),'must bundle selector');
for(const id of ['siegeBuffBack','zmzBuffPager','zmzBuffPrev','zmzBuffNext','zmzBuffPageNumbers','zmzBuffPresets'])
  assert(html.includes('id="'+id+'"'),id);
assert(css.includes('#settingsModal.zmz-buff-mode')&&css.includes('.zmz-page-off{display:none!important}'));
assert(css.includes('overflow:hidden!important'),'pager must not rely on scrolling');
assert(!script.includes('list.scrollTop+='),'old touch-driven scroll must be gone');
assert(script.includes('list.scrollHeight>list.clientHeight+2'),'every page must be measured to fit screen');
assert(script.includes('details.scrollHeight>details.clientHeight+2'),'the whole dialog must fit, not just its list');
assert(script.includes('footerBottom>sheetBottom-5'),'the return button must remain on screen');
assert(script.includes('pageSize=Math.min(9'),'portrait phone should use 9 items/page (4 pages)');
assert(script.includes('while(pageSize>1)'),'short screens may need one-item pages');
assert(script.includes("classList.toggle('zmz-page-off'"),'visibility only; preserve hidden checkboxes');
assert(script.includes('list.addEventListener(\'touchmove\''),'suppress swiping');
assert(script.includes("presets.textContent=showing?'返回增益':'预设'"),'preset entry preserved');
assert(read('web/games/siege.html').includes('siegeCatalog'),'retain main v24 game');
new vm.Script(script,{filename:'siege_buff_pages.js'});

function classes(...names){
 const set=new Set(names);
 return {contains:k=>set.has(k),add:k=>set.add(k),remove:k=>set.delete(k),
  toggle:(k,force)=>{const value=force===undefined?!set.has(k):!!force;if(value)set.add(k);else set.delete(k);return value}};
}
function element(name,cls){
 const handlers={};
 return {name,classList:classes(...cls),children:[],attributes:{},disabled:false,textContent:'',
  addEventListener:(ev,fn,options)=>{handlers[ev]={fn,options}},
  dispatch:(ev,arg={})=>handlers[ev]?.fn(arg),
  setAttribute(k,v){this.attributes[k]=v},
  getAttribute(k){return this.attributes[k]},
  replaceChildren(...xs){this.children=xs},querySelectorAll:()=>[]};
}
const modal=element('modal',['hidden']),details=element('details',[]),
  list=element('list',[]),back=element('back',[]),pager=element('pager',[]),
  numbers=element('numbers',[]),prev=element('prev',[]),
  next=element('next',[]),presets=element('presets',[]),
  summary=element('summary',[]);
const sheet={scrollTop:75,getBoundingClientRect:()=>({bottom:height+180})};
modal.querySelector=()=>sheet;details.open=false;
back.getBoundingClientRect=()=>({bottom:list.scrollHeight+160});
const groups=['弹药','机制','效果','技能','负面'].map(name=>element(name,['siege-buff-group']));
const counts=[4,5,3,12,4];
let j=0;const rows=[];
groups.forEach((g,i)=>{
 list.children.push(g);
 for(let n=0;n<counts[i];n++){const row=element('buff'+j++,['siege-buff-row']);row.checked=j%2===0;row.group=g;rows.push(row);list.children.push(row)}
});
list.querySelectorAll=sel=>sel==='.siege-buff-group'?groups:sel==='.siege-buff-row'?rows:[];
let height=300;
Object.defineProperties(details,{clientHeight:{get:()=>height+30},scrollHeight:{get:()=>list.scrollHeight+80}});
Object.defineProperty(list,'clientHeight',{get:()=>height});
Object.defineProperty(list,'scrollHeight',{get(){
 const visible=rows.filter(x=>!x.classList.contains('zmz-page-off')&&!x.classList.contains('hidden')).length;
 const visibleGroups=groups.filter(x=>!x.classList.contains('zmz-page-off')).length;
 return Math.ceil(visible/2)*36+visibleGroups*28+5;
}});
const map={settingsModal:modal,siegeAllowedConfig:details,siegeBuffChoices:list,
 siegeBuffBack:back,zmzBuffPager:pager,zmzBuffPageNumbers:numbers,
 zmzBuffPrev:prev,zmzBuffNext:next,zmzBuffPresets:presets,
 zmzBuffPageSummary:summary};
const window={events:{},addEventListener(k,fn){this.events[k]=fn}};
const document={getElementById:id=>map[id],createElement:k=>element(k,[])};
vm.runInNewContext(script,{document,window},{filename:'siege_buff_pages_mock.js'});
modal.classList.remove('hidden');details.open=true;details.dispatch('toggle');
assert(modal.classList.contains('zmz-buff-mode'),'open selector must focus a screen-bounded page');
assert.equal(numbers.children.length,3);
assert.deepEqual(numbers.children.map(x=>x.textContent),['1','2','3']);
assert.equal(rows.filter(x=>!x.classList.contains('zmz-page-off')).length,9);
assert.equal(summary.textContent,'第 1 / 4 页 · 本页 9 项，共 28 项');
assert(list.scrollHeight<=list.clientHeight,'page 1 fits');
const save=rows.map(r=>r.checked);
next.dispatch('click');
assert.equal(rows.filter(x=>!x.classList.contains('zmz-page-off')).length,9);
assert(list.scrollHeight<=list.clientHeight,'page 2 fits');
next.dispatch('click');
assert.equal(rows.filter(x=>x.classList.contains('zmz-page-off')).length,19);
assert.equal(rows.filter(x=>!x.classList.contains('zmz-page-off')).length,9);
assert(list.scrollHeight<=list.clientHeight,'page 3 fits');
next.dispatch('click');
assert.equal(rows.filter(x=>!x.classList.contains('zmz-page-off')).length,1);
assert.equal(summary.textContent,'第 4 / 4 页 · 本页 1 项，共 28 项');
assert.deepEqual(numbers.children.map(x=>x.textContent),['2','3','4']);
assert(list.scrollHeight<=list.clientHeight,'page 4 fits');
assert.deepEqual(rows.map(x=>x.checked),save,'switching pages must preserve all other-page states');
const gesture={cancelable:true,blocked:false,stopped:false,preventDefault(){this.blocked=true},stopPropagation(){this.stopped=true}};
list.dispatch('touchmove',gesture);
assert(gesture.blocked&&gesture.stopped,'no scrolling the list OR its parent');
assert.equal(sheet.scrollTop,0);
presets.dispatch('click');assert(modal.classList.contains('zmz-buff-presets'));
assert.equal(presets.textContent,'返回增益');
presets.dispatch('click');assert(!modal.classList.contains('zmz-buff-presets'));
height=125;window.events.resize();
const visible=rows.filter(x=>!x.classList.contains('zmz-page-off')).length;
assert(visible<9,'short screens must reduce page size');
assert(list.scrollHeight<=list.clientHeight,'even a short viewport page fits');
assert(numbers.children.length<=3);
back.dispatch('click');assert.equal(details.open,false);
assert(!modal.classList.contains('zmz-buff-mode'),'closing restores other settings');
assert.equal(sheet.scrollTop,75,'other settings restore previous scroll position');
assert.deepEqual(rows.map(x=>x.checked),save,'closing keeps all selections');
console.log('Main + ZMZ pagination pager: 28 gains, 4 pages, short-screen fit, no scrolling, cross-page state, presets and return PASS');

// Zombie room: negative benefits are hidden but remain in the DOM for classic mode.
