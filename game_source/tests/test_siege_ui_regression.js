/* Regression coverage for the browser-only siege page and lobby settings.
   Source-level parse plus bootstrap-order and responsive structure checks. */
const fs=require('fs'),assert=require('assert'),vm=require('vm');
const src=p=>fs.readFileSync(__dirname+'/../'+p,'utf8');
const builder=src('build.py'),page=src('web/games/siege.html'),audio=src('web/games/siege_audio.js');
const lobby=src('web/90_shell_after_games.html'),css=src('web/lite.css'),lite=src('web/lite.js');
assert(builder.includes('replace("<script>", "<script>\\n" + read("web/games/siege_audio.js")'));
const embedded=page.replace('<script>','<script>\n'+audio+'\n');
const script=embedded.match(/<script>([\s\S]*?)<\/script>/);
assert(script,'Siege page must have one embedded script');
new vm.Script(script[1],{filename:'siege.html'});
assert(script[1].indexOf('const siegeAudio=')>=0);
assert(script[1].indexOf('const siegeAudio=')<script[1].indexOf("enter('state')"),'Audio initialized after automatic room entry');
assert(page.includes("if(type!=='state')siegeAudio.unlock()"),'Autoload must not invoke WebAudio before user gesture');
assert(page.includes("进入对局失败，请返回房间重试"),'Load errors must be recoverable');
assert(lobby.includes('<details id="siegeAllowedConfig"'),'Buff selector must be collapsible');
assert(lobby.includes('<summary>允许出现的增益'),'Buff selector must have visible summary');
assert(lite.includes("querySelectorAll('.setting-grid > label')"),'Only direct setting labels should be toggled');
assert(lite.includes("box.querySelector('.sheet').scrollTop=0"),'New settings modal must scroll to start');
assert(css.includes('#settingsModal .sheet{')&&css.includes('overflow-x:hidden;overflow-y:auto;'), 'Settings sheet must allow vertical scrolling');
assert(css.includes('#siegeAllowedConfig{grid-column:1/-1'), 'Buff choices must not break the two-column layout');
assert(css.includes('#siegeBuffChoices{display:grid'), 'Buff choices must use compact multi-column grid');
console.log('Siege UI regression tests passed: bootstrap, controls, scrolling and script syntax');
