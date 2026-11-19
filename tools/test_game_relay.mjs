// End-to-end regression for invitation-gated cloud login and verified relay identity.
import assert from 'node:assert/strict';
import { spawn } from 'node:child_process';
import { createHash } from 'node:crypto';
import { mkdtempSync, rmSync } from 'node:fs';
import { createServer } from 'node:net';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { once } from 'node:events';

const hash = value => createHash('sha256').update(value).digest('hex');
const secret = '1'.repeat(64), invitation = 'a'.repeat(48), bootstrap = 'owner-code';
const dir = mkdtempSync(join(tmpdir(),'hotpoint-relay-test-'));
const freePort = createServer();
freePort.listen(0,'127.0.0.1');
await once(freePort,'listening');
const port = freePort.address().port;
freePort.close();
await once(freePort,'close');
const base = 'http://127.0.0.1:'+port;
const ownerHeaders = {Authorization:'Bearer '+secret, 'Content-Type':'application/json'};
const relayHeaders = {...ownerHeaders, 'X-Game-Invite':invitation};
const child = spawn(process.execPath,['tools/game_relay.mjs'],{
  env:{...process.env,GAME_RELAY_PORT:String(port),GAME_ACCESS_HASH:hash(secret),
    STATE_DIRECTORY:dir,GAME_ADMIN_CODE_HASH:hash(bootstrap),GAME_RELAY_SECURE:'0'},
  stdio:['ignore','pipe','pipe']
});
let stderr='';
child.stderr.on('data',buf=>{stderr+=buf.toString()});
const request = async (path, options={}) => {
  const r=await fetch(base+path,{redirect:'manual',signal:AbortSignal.timeout(8000),...options});
  const raw=await r.text();
  return {status:r.status,headers:r.headers,text:raw,json:()=>JSON.parse(raw)};
};
try {
  let ready=false;
  for(let attempt=0;attempt<40;attempt++){
    if(child.exitCode!==null)break;
    try{await request('/cloud/me');ready=true;break}catch{await new Promise(resolve=>setTimeout(resolve,75))}
  }
  assert.ok(ready,'relay not ready: '+stderr);
  const owner=await request('/cloud/account',{method:'POST',headers:ownerHeaders,
    body:JSON.stringify({action:'register',name:'owner',password:'test-pass-123',code:bootstrap})});
  assert.equal(owner.status,200,owner.text);
  const waiting=fetch(base+'/relay/poll',{method:'POST',headers:relayHeaders,body:'{}',signal:AbortSignal.timeout(15000)});
  // Wait until the relay has accepted the long-poll before visiting.
  let inviteResponse;
  for(let i=0;i<60;i++){
    inviteResponse=await request('/invite/'+invitation);
    if(inviteResponse.status===303)break;
    await new Promise(resolve=>setTimeout(resolve,50));
  }
  assert.equal(inviteResponse.status,303,inviteResponse.text);
  const inviteCookie=inviteResponse.headers.get('set-cookie').split(';')[0];
  const headers={'Content-Type':'application/json',Cookie:inviteCookie};
  const unauth=await request('/',{headers});
  assert.equal(unauth.status,200);
  assert.match(unauth.text,/云账号/);
  assert.equal((await request('/api/rooms',{headers})).status,401);
  const registered=await request('/cloud/account',{method:'POST',headers,
    body:JSON.stringify({action:'register',name:'user2',displayName:'旅途队友',password:'strong-pass-123'})});
  assert.equal(registered.status,200,registered.text);
  assert.equal(registered.json().name,'旅途队友');
  assert.equal(registered.json().username,'user2');
  assert.ok(!registered.json().token,'Browser response must not contain bearer token');
  const session=registered.headers.get('set-cookie').split(';')[0];
  const signed={Cookie:inviteCookie+'; '+session,'Content-Type':'application/json'};
  const profile=await request('/cloud/me',{headers:signed});
  assert.equal(profile.status,200);
  assert.equal(profile.json().id,registered.json().id);
  assert.equal((await request('/cloud/account',{method:'POST',headers:signed,
    body:JSON.stringify({action:'sync',token:'fake'})})).status,403);
  const relayed=request('/api/rooms',{headers:signed});
  const poll=await waiting;
  assert.equal(poll.status,200);
  const job=await poll.json();
  assert.equal(job.identity.id,profile.json().id);
  assert.equal(job.identity.name,'旅途队友');
  assert.equal(job.identity.username,'user2');
  assert.ok(!job.identity.token);
  const reply=await request('/relay/reply',{method:'POST',headers:relayHeaders,
    body:JSON.stringify({id:job.id,type:'application/json',status:200,
      body:Buffer.from(JSON.stringify({rooms:[]})).toString('base64')})});
  assert.equal(reply.status,204);
  const forwarded=await relayed;
  assert.equal(forwarded.status,200);
  assert.deepEqual(forwarded.json(),{rooms:[]});
  const rename=await request('/cloud/account',{method:'POST',headers:signed,
    body:JSON.stringify({action:'rename',displayName:'三号炮手'})});
  assert.equal(rename.status,200);
  assert.equal((await request('/cloud/me',{headers:signed})).json().name,'三号炮手');
  const logout=await request('/cloud/account',{method:'POST',headers:signed,body:JSON.stringify({action:'logout'})});
  assert.equal(logout.status,200);
  assert.equal((await request('/cloud/me',{headers:signed})).status,401);
  console.log('Remote invite: no guest access, cloud signup, authenticated relay UID, rename and logout PASS');
} finally {
  child.kill('SIGTERM');
  await Promise.race([once(child,'exit'),new Promise(resolve=>setTimeout(resolve,1500))]);
  rmSync(dir,{recursive:true,force:true});
}
