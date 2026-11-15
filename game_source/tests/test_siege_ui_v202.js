/* v0.20.2 UI regression: the old .buff element is hidden by upstream HUD. */
'use strict';
const fs=require('fs'),assert=require('assert'),vm=require('vm');
const src=p=>fs.readFileSync(__dirname+'/../'+p,'utf8');
const html=src('web/games/siege.html');
const build=src('build.py');
assert(build.includes('GAME_DISPLAY_VERSION = "ZMZ v0.20.2"'));
for(let i=0;i<2;i++){
  assert(html.includes('id="neg'+i+'"'),'Separate visible negative state for player '+i);
  assert(html.includes("$('neg'+i)"),'Render pending negative for player '+i);
}
assert(html.includes('id="negativeAlert"')&&html.includes('role="status"'));
assert(html.includes("#game #hud .seat .negative-state{display:block!important"));
assert(html.includes("#game #hud .seat .negative-state.hidden{display:none!important"));
assert(html.includes('room.negativePending?.[room.seat]'));
assert(html.includes('playing.event.negativeActive||[]'));
assert(html.includes('下一发强制生效')&&html.includes('本发负面效果'));
assert(html.includes("wobble:'↗'"),'Unstable is now a one-time angular deviation');
const audio=src('web/games/siege_audio.js');
const js=html.replace('<script>','<script>\n'+audio+'\n').match(/<script>([\s\S]*?)<\/script>/);
assert(js);new vm.Script(js[1],{filename:'siege_v202_ui.js'});
console.log('v0.20.2 negative-pending HUD, clear own-shot warning, game version and JS syntax PASS');
