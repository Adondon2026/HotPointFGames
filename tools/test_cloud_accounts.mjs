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
  console.log('Cloud accounts: invitations, account isolation, deduplication and device restore PASS');
} finally {
  accounts?.close();
  rmSync(dir, {recursive:true,force:true});
}
