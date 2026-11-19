// This page is served by the relay only while a valid private room invitation
// cookie exists. Passwords go to the cloud endpoint over HTTPS; no local guest
// credentials or cloud session tokens are exposed to browser JavaScript.
export const remoteAccountPage = `<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<meta name="theme-color" content="#152923"><title>加入好友游戏厅 · 云账号</title>
<style>
*{box-sizing:border-box}body{margin:0;min-height:100dvh;display:grid;place-items:center;padding:22px;background:#142923;color:#edf2e7;font:15px/1.6 system-ui,"Microsoft YaHei",sans-serif}
main{width:min(100%,420px);padding:28px 25px;border:1px solid #4b6c5b;border-radius:18px;background:#20382f;box-shadow:0 16px 48px #091b1455}
.kicker{font-size:11px;letter-spacing:.16em;color:#abc5b1}h1{font-size:25px;font-weight:650;margin:7px 0 3px}p{color:#adc5b6;margin:0 0 20px;font-size:13px}
nav{display:grid;grid-template-columns:1fr 1fr;gap:5px;margin:0 0 20px;padding:4px;background:#142923;border-radius:9px}
nav button{background:transparent;border:0;color:#aac1b2;padding:10px;min-height:42px;cursor:pointer;font-weight:600}
nav button[aria-selected=true]{color:#20382f;background:#b8d3b7;border-radius:7px}
label{display:block;font-size:13px;color:#d5e1d5;margin-top:13px;margin-bottom:5px}
input{display:block;width:100%;height:45px;padding:0 12px;border:1px solid #698579;background:#152b26;border-radius:9px;color:white;font-size:15px;outline-offset:2px}input:focus{outline:2px solid #c7dbb1}
small{display:block;color:#a8beaf;font-size:12px;margin-top:5px}button.submit{display:block;width:100%;margin-top:24px;min-height:46px;background:#b8d3b7;border:0;border-radius:9px;color:#1b3328;font-size:15px;font-weight:700;cursor:pointer}
button:disabled{opacity:.55;cursor:wait}#message{min-height:22px;margin:9px 0 0;color:#f4b6a4;font-size:13px}
.hidden{display:none!important}
</style></head><body><main><div class="kicker">HOTPOINT / PRIVATE INVITE</div><h1>加入好友游戏厅</h1><p>使用云账号进入房间；首次受邀可以直接注册，账号会保存在云端。</p>
<nav role="tablist"><button id="signinTab" role="tab" aria-selected="true" type="button">登录</button><button id="signupTab" role="tab" aria-selected="false" type="button">注册</button></nav>
<form id="form"><label for="username">账号名</label><input id="username" name="username" autocomplete="username" minlength="1" maxlength="10" required placeholder="用于下次登录">
<div id="nicknameField" class="hidden"><label for="nickname">游戏昵称</label><input id="nickname" name="nickname" maxlength="12" autocomplete="nickname" placeholder="朋友看到的名字"><small>登录账号名固定，游戏昵称之后可以修改。</small></div>
<label for="password">密码</label><input id="password" name="password" type="password" minlength="8" maxlength="128" autocomplete="current-password" required placeholder="至少 8 位">
<button class="submit" id="submit" type="submit">登录并进入</button><div id="message" role="status" aria-live="polite"></div>
</form></main><script>
const byId=id=>document.getElementById(id);let signup=false;
function mode(value){signup=value;byId('signinTab').setAttribute('aria-selected',String(!value));
byId('signupTab').setAttribute('aria-selected',String(value));byId('nicknameField').classList.toggle('hidden',!value);
byId('password').autocomplete=value?'new-password':'current-password';byId('submit').textContent=value?'注册并进入':'登录并进入';byId('message').textContent=''}
byId('signinTab').onclick=()=>mode(false);byId('signupTab').onclick=()=>mode(true);
byId('form').onsubmit=async e=>{e.preventDefault();const button=byId('submit');button.disabled=true;byId('message').textContent='';
try{const payload={action:signup?'register':'login',name:byId('username').value.trim(),password:byId('password').value};
if(signup)payload.displayName=byId('nickname').value.trim()||payload.name;
const response=await fetch('/cloud/account',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload),credentials:'same-origin'});
const data=await response.json();if(!response.ok)throw Error(data.error||'验证失败');
location.reload()}catch(error){byId('message').textContent=error.message||'登录失败';button.disabled=false}};
</script></body></html>`;
