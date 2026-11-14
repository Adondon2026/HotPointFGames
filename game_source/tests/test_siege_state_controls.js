/* ZMZ v0.19.2: exercise checkbox feedback and saved-track re-entry, not just source strings. */
'use strict';
const fs=require('fs'),assert=require('assert'),vm=require('vm');
const root=__dirname+'/../';
const lite=fs.readFileSync(root+'web/lite.js','utf8');
const siege=fs.readFileSync(root+'web/games/siege.html','utf8');
const audio=fs.readFileSync(root+'web/games/siege_audio.js','utf8');
const gameActivity=fs.readFileSync(root+'../app/src/main/java/com/chuanmahjong/nearby/GameActivity.kt','utf8');

const start=lite.indexOf('const siegeBuffList='),end=lite.indexOf('function liteSettings(){',start);
assert(start>=0&&end>start,'Cannot extract buff controller');
let boxes=[];
const elements={
  siegeBuffCount:{textContent:''},
  siegeBuffAll:{disabled:false},
  siegeBuffNone:{disabled:false}
};
const parent={
  set innerHTML(html){
    boxes=[...html.matchAll(/data-siege-buff="([^"]+)"\s*(checked)?/g)].map(m=>({
      dataset:{siegeBuff:m[1]},checked:m[2]==='checked',disabled:false,onchange:null
    }));
  },
  querySelectorAll(){return boxes;}
};
elements.siegeBuffChoices=parent;
const state={isHost:true,settings:{siegeAllowedBuffs:['big','power']}};
const submitted=[];
const ctx=vm.createContext({
 state,
 $:id=>elements[id]||{value:0},
 document:{querySelectorAll:selector=>{
    assert(selector.startsWith('#siegeBuffChoices input'));
    return boxes;
 }},
 action:(kind,payload)=>{submitted.push({kind,payload});return Promise.resolve({ok:true});}
});
vm.runInContext(lite.slice(start,end),ctx,{filename:'lite-buff-controller.js'});
const init=vm.runInContext('siegeBuffChoiceUI',ctx);
init();
assert.equal(boxes.length,16);
assert.equal(elements.siegeBuffCount.textContent,'已选 2 / 16');
boxes[0].checked=false;
boxes[0].onchange();
assert.equal(elements.siegeBuffCount.textContent,'已选 1 / 16','Count must change before a new game is started');
assert.equal(submitted.at(-1).kind,'siege_settings');
assert.deepEqual(Array.from(submitted.at(-1).payload.allowedBuffs),['power']);
const actionStart=lite.indexOf("$('siegeBuffAll').onclick=");
const actionEnd=lite.indexOf(";$('liteGameRules')",actionStart);
assert(actionStart>0&&actionEnd>actionStart);
vm.runInContext(lite.slice(actionStart,actionEnd),ctx);
elements.siegeBuffAll.onclick();
assert.equal(elements.siegeBuffCount.textContent,'已选 16 / 16','Select-all must update immediately');
elements.siegeBuffNone.onclick();
assert.equal(elements.siegeBuffCount.textContent,'已选 0 / 16','Deselect-all must update immediately');
assert.equal(submitted.at(-1).payload.allowedBuffs.length,0);

assert.equal((siege.match(/classList\.add\('in-battle'\);if\(!old\|\|old\.code!==d\.code\)siegeAudio\.enterBattle\(\)/g)||[]).length,3,'All three combat modes must restore BGM on entry');
assert(gameActivity.includes('settings.mediaPlaybackRequiresUserGesture = false'),'Android WebView must allow BGM when re-entering');

const counters={starts:0,stops:0,resumes:0};
class FakeAudioContext {
  constructor(){this.state='suspended';this.destination={};}
  resume(){this.state='running';counters.resumes++;return Promise.resolve();}
  createGain(){return {gain:{value:0},connect(){}};}
  createBuffer(_channels,count){const samples=new Float32Array(count);return {getChannelData:()=>samples};}
  createBufferSource(){return {buffer:null,loop:false,connect(){},disconnect(){},start(){counters.starts++},stop(){counters.stops++}};}
}
const stored={siege_bgm:'arcade',siege_sfx:'on'};
const button=()=>({textContent:'',addEventListener(){},setAttribute(){}});
const buttons={siegeMusicToggle:button(),siegeEffectToggle:button()};
const audioDoc={
  body:{classList:{contains:()=>true}},
  getElementById:id=>buttons[id],
  addEventListener(){},
  hidden:false
};
const aCtx=vm.createContext({
 window:{AudioContext:FakeAudioContext},
 document:audioDoc,
 localStorage:{getItem:k=>stored[k]||null,setItem:(k,v)=>{stored[k]=v;}}
});
vm.runInContext(audio+'\nthis.soundTest=siegeAudio;',aCtx,{filename:'siege_audio.js'});
const sound=aCtx.soundTest;
assert.equal(counters.starts,0);
assert(buttons.siegeMusicToggle.textContent.includes('轻快像素'));
sound.enterBattle();
assert.equal(counters.starts,1,'Saved pixel BGM must start automatically on room entry');
assert(counters.resumes>0,'Suspended AudioContext should attempt to resume');
sound.stop();
assert.equal(counters.stops,1);
sound.enterBattle();
assert.equal(counters.starts,2,'Saved BGM must restart after leaving and re-entering a room');
assert.equal(stored.siege_bgm,'arcade','Autostart must not cycle or overwrite last-selected track');
console.log('Siege controls regressions passed: live 0/16..16/16 counter and persisted autoplay/re-entry');
