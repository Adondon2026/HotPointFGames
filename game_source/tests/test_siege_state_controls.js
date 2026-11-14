/* Browser-independent regression for the 24-buff selector and the upstream Web Audio controller. */
'use strict';
const fs=require('fs'),assert=require('assert'),vm=require('vm');
const src=p=>fs.readFileSync(__dirname+'/../'+p,'utf8');
const lite=src('web/lite.js'),audio=src('web/games/siege_audio.js');
const sub=lite.substring(lite.indexOf('const siegeBuffList='),lite.indexOf('const siegeHard='));
const g=vm.createContext({});
vm.runInContext(sub+'\nthis.buffs=siegeBuffList;',g);
assert.equal(g.buffs.length,24);
assert(lite.includes("const choices=siegeChoices(),n=choices.filter(x=>x.checked).length;"));
assert(lite.includes("$('siegeBuffCount').textContent='已选 '+n+' / '+siegeBuffList.length;"));
assert(lite.includes("x.onchange=saveSiegeSettings"),'Selection must call immediate refresh and save');
assert(lite.includes("$('siegeBuffBack').onclick=()"),'Explicit collapse handler must exist');

let starts=0,stops=0,resumes=0;
class FakeAudioContext {
  constructor(){this.state='suspended';this.destination={};this.currentTime=0}
  resume(){this.state='running';resumes++;return Promise.resolve()}
  createGain(){return {gain:{value:0},connect(){}}}
  createBuffer(c,n){return {getChannelData:()=>new Float32Array(n)}}
  createBufferSource(){return {connect(){},disconnect(){},start(){starts++},stop(){stops++}}}
}
const local={siege_bgm:'arcade',siege_sfx:'on'};
const selection={siegeMusic:{value:'',addEventListener(){}},siegeEffects:{checked:false,addEventListener(){}}};
const env=vm.createContext({
  window:{AudioContext:FakeAudioContext,addEventListener(){}},
  document:{hidden:false,body:{classList:{contains:()=>true}},getElementById:k=>selection[k],addEventListener(){}},
  localStorage:{getItem:k=>local[k],setItem:(k,v)=>local[k]=v}
});
vm.runInContext(audio+'\nthis.sound=siegeAudio',env,{filename:'siege_audio.js'});
assert.equal(selection.siegeMusic.value,'arcade');
env.sound.enterBattle();
assert.equal(starts,1,'Saved arcade music should start without cycling');
assert(resumes>0);
env.sound.stop();
assert.equal(stops,1);
env.sound.enterBattle();
assert.equal(starts,2,'Re-entered room should resume the same music');
assert.equal(local.siege_bgm,'arcade');
console.log('ZMZ v0.20.1: 24 selectable buffs, live UI updates and persisted audio re-entry PASS');
