import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { mkdtempSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { cloudAccounts } from './cloud_accounts.mjs';

const dir = mkdtempSync(join(tmpdir(), 'hotpoint-cloud-test-'));
let accounts;
try {
  const first = 'test-owner-invite';
  accounts = cloudAccounts(dir, createHash('sha256').update(first).digest('hex'));
  const run = accounts.handle;
  const password = 'test-password';
  await assert.rejects(run({action:'register',name:'房主',password,code:'wrong'}), {status:403});
  const owner = await run({action:'register',name:'房主',password,code:first});
  assert.equal(owner.admin, true);
  await assert.rejects(run({action:'register',name:'朋友',password,code:first}), {status:403});
  const {code} = await run({action:'invite',token:owner.token});
  const friend = await run({action:'register',name:'朋友',password,code});
  await assert.rejects(run({action:'register',name:'旁观',password,code}), {status:403});
  await assert.rejects(run({action:'invite',token:friend.token}), {status:403});
  await assert.rejects(run({action:'login',name:'房主',password:'wrong-password'}), {status:401});

  const row = {match_id:'a',game:'siege',won:1,points:3,raw:100,ended:10000,queue:'friends'};
  const sync = {action:'sync',token:owner.token,cursor:0,revision:0,settings:'{"ammo":4}',results:[row]};
  await run(sync);
  const retry = await run(sync);
  assert.deepEqual(retry.results, [row]);
  assert.equal(retry.revision, 1);
  const fresh = await run({action:'login',name:'房主',password});
  assert.equal(fresh.id, owner.id);
  const download = await run({...sync,token:fresh.token,settings:null,results:[]});
  assert.deepEqual(download.results, [row]);
  assert.equal(download.settings, '{"ammo":4}');
  const other = await run({...sync,token:friend.token,settings:null,results:[]});
  assert.deepEqual(other.results, []);
  assert.equal(other.settings, null);

  // Private room invitations grant *only* the right to register; a cloud
  // account still needs an immutable username and a password.
  await assert.rejects(run({action:'register',name:'无邀请',password,displayName:'昵称'}), {status:403});
  const invited = await run({action:'register',name:'person3',password,displayName:'路上同行者'}, {invited:true});
  assert.equal(invited.username,'person3');
  assert.equal(invited.name,'路上同行者');
  assert.equal(invited.admin,false);
  const profile = await run({action:'profile',token:invited.token});
  assert.equal(profile.name,'路上同行者');
  assert.equal(profile.username,'person3');
  const changed = await run({action:'rename',token:invited.token,displayName:'三号炮手'});
  assert.equal(changed.name,'三号炮手');
  assert.equal(changed.username,'person3');
  assert.equal((await run({action:'login',name:'person3',password})).name,'三号炮手');
  await assert.rejects(run({action:'rename',token:'invalid',displayName:'冒名修改'}), {status:401});
  await assert.rejects(run({action:'rename',token:invited.token,displayName:''}), {status:400});
  await assert.rejects(run({action:'register',name:'same-id',password,displayName:'其他'}, {invited:true})
    .then(()=>run({action:'register',name:'same-id',password,displayName:'其他'}, {invited:true})), {status:409});
  assert.equal((await run({action:'profile',token:owner.token})).username,'房主');
  console.log('Cloud accounts: invitations, account isolation, deduplication and device restore PASS');
} finally {
  accounts?.close();
  rmSync(dir, {recursive:true,force:true});
}
