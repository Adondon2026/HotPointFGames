// Exercise the real presentation helpers and DOM overlay without a browser.
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const source=fs.readFileSync(path.join(__dirname,'../web/games/army.js'),'utf8');
new Function(source); // syntax
const helpers=source.slice(source.indexOf('const armyFxDurations'),source.indexOf('function armyFxSync'))+source.slice(source.indexOf('function armyFxContact'),source.indexOf('function armyIsSetup'));
const run=new Function('assert',helpers+`
 let armyFx=null,armyFxQueue=[],armyFxStage='',armyFxLast=null,armyBoardKey='',armyFxTimer=null;
 let pending=[],time=0;function setTimeout(fn,ms){pending.push([fn,ms]);return pending.length}function renderSafe(){}
 const armyKey=JSON.stringify,armyPosition=n=>[10+n[1]*20,4.2+n[0]*7.9+(n[0]>=6?4.7:0)],armyHorizontal=()=>false;
 const matchMedia=()=>({matches:false});
 const element=()=>({className:'',textContent:'',children:[],style:{setProperty(){}},append(x){this.children.push(x)},animate(){}});
 const document={createElement:element};
 for(const h of [false,true])for(const dst of [[10,4.2],[90,95.8],[50,50]])for(const prev of [[0,0],[100,100],[0,100],[100,0]]){
  const {a,d,axis}=armyFxContact(dst,prev,h),size=axis===0?(h?6.7:16):(h?13:5.1);
  assert.ok(Math.abs(a[axis]-d[axis])>=size);assert.ok([...a,...d].every(n=>n>=0&&n<=100));
 }
 const src=[5,0],dst=[6,0],p={id:1,node:src,owner:0,rank:'司令'},d={id:2,node:dst,owner:1,rank:'UNKNOWN'};
 for(const [result,winner] of [['attacker',0],['defender',1],['both',null],['capture_flag',0]]){
  const survivor=winner===0?{...p,node:dst}:winner===1?d:null;
  const e={player:0,src,dst,path:[src,dst],battle:true,result,before:{pieces:[p,d]},after:{pieces:survivor?[survivor]:[]}};
  assert.equal(armyFxOutcome(e,0).winner,winner);
  for(const stage of ['approach','clash','result','settle']){
   armyFxStage=stage;const board=element();armyFxOverlay(board,e,0);
   const ghosts=board.children.filter(x=>x.className.includes('army-fx-ghost'));
   if(stage==='settle')assert.equal(ghosts.length,survivor?1:0);
   else assert.equal(ghosts.length,2);
   if(stage==='result'){
    assert.equal(ghosts.filter(x=>x.className.includes('loser')).length,winner===null?2:1);
    assert.equal(ghosts.filter(x=>x.className.includes('survivor')).length,winner===null?0:1);
   }
   for(const g of ghosts.filter(x=>x.className.includes('enemy')))assert.equal(g.textContent,'');
  }
 }
 armyFxQueue=[{id:1,battle:true},{id:2,battle:false}];armyFxStep();const seen=[armyFxStage];
 while(pending.length){const [fn,ms]=pending.shift();time+=ms;fn();seen.push(armyFxStage)}
 assert.equal(seen.join(','),'approach,clash,result,settle,approach,result,');
 assert.equal(time,2670);assert.equal(armyFxLast.id,2);
`);
run(assert);
console.log('Army presentation: contact geometry, three outcomes, private ranks, DOM overlays, queue timing PASS');
