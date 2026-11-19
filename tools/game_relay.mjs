// Single-host private relay. The public HTTPS proxy is configured separately.
import http from 'node:http';
import { createHash, timingSafeEqual } from 'node:crypto';
import { cloudAccounts } from './cloud_accounts.mjs';
const accessHash = process.env.GAME_ACCESS_HASH;
if (!/^[a-f0-9]{64}$/.test(accessHash || '')) throw Error('Missing relay key');
const limit = 4 * 1024 * 1024;
const backupDir = process.env.STATE_DIRECTORY;
const accounts = backupDir && process.env.GAME_ADMIN_CODE_HASH
  ? cloudAccounts(backupDir, process.env.GAME_ADMIN_CODE_HASH).handle : null;
const attempts = new Map();
let authInFlight = 0;
const pending = new Map();
let waiter, invitation, lastPoll = 0, nextId = 0;

function same(a, b) {
  return typeof a === 'string' && typeof b === 'string'
    && Buffer.byteLength(a) === Buffer.byteLength(b)
    && timingSafeEqual(Buffer.from(a), Buffer.from(b));
}
function access(req) {
  const prefix = 'Bearer ';
  const header = req.headers.authorization || '';
  if (!header.startsWith(prefix)) return false;
  const token = header.slice(prefix.length);
  return /^[a-f0-9]{64}$/.test(token)
    && same(createHash('sha256').update(token).digest('hex'), accessHash);
}
function allowAttempt(req, key, maximum, count = true) {
  const now = Date.now();
  for (const [id, entry] of attempts) if (now >= entry.until) attempts.delete(id);
  const ip = req.headers['x-game-client-ip'] || req.socket.remoteAddress;
  const id = key + ':' + ip;
  if (!attempts.has(id) && attempts.size >= 2048) return false;
  const entry = attempts.get(id) || {until: now + 60_000, count: 0};
  if (entry.count >= maximum) return false;
  if (count) {
    entry.count++;
    attempts.set(id, entry);
  }
  return true;
}
function authorize(req) {
  if (!allowAttempt(req, 'access', 30, false)) return 429;
  if (access(req)) return 200;
  allowAttempt(req, 'access', 30);
  return 403;
}
function send(res, status, body = '', type = 'text/plain; charset=utf-8') {
  res.writeHead(status, {'Content-Type': type, 'Cache-Control': 'no-store',
    'Referrer-Policy': 'no-referrer', 'X-Content-Type-Options': 'nosniff'});
  res.end(body);
}
async function read(req, maximum = limit * 2) {
  const chunks = [];
  let size = 0;
  for await (const chunk of req) {
    size += chunk.length;
    if (size > maximum) throw Object.assign(new Error('request too large'), {status: 413});
    chunks.push(chunk);
  }
  return Buffer.concat(chunks);
}
function dispatch() {
  if (!waiter) return;
  const entry = [...pending.values()].find(item => !item.dispatched);
  if (!entry) return;
  const res = waiter;
  waiter = null;
  entry.dispatched = true;
  send(res, 200, JSON.stringify(entry.job), 'application/json');
}

const server = http.createServer(async (req, res) => {
  try {
    const path = req.url;
    if (path === '/cloud/account') {
      if (!accounts || req.method !== 'POST') return send(res, 404);
      const code = authorize(req);
      if (code !== 200) return send(res, code);
      const body = await read(req, 128 * 1024);
      const data = JSON.parse(body);
      const auth = data.action === 'login' || data.action === 'register';
      if (auth && (authInFlight >= 4 || !allowAttempt(req, 'account', 12))) return send(res, 429);
      if (auth) authInFlight++;
      try {
        const result = await accounts(data);
        return send(res, 200, JSON.stringify(result), 'application/json');
      } catch (err) {
        return send(res, err.status || 500,
          JSON.stringify({error: err.status ? err.message : '云端操作暂时失败'}), 'application/json');
      } finally {
        if (auth) authInFlight--;
      }
    }
    if (path === '/relay/poll' || path === '/relay/reply' || path === '/relay/close') {
      if (req.method !== 'POST') return send(res, 405);
      const code = authorize(req);
      if (code !== 200) return send(res, code);
      const invite = req.headers['x-game-invite'];
      if (!/^[a-f0-9]{48}$/.test(invite || '')) return send(res, 400);
      if (path === '/relay/poll') {
        if (invitation && !same(invitation, invite) && Date.now() - lastPoll < 30_000) return send(res, 409);
        if (waiter) send(waiter, 204);
        invitation = invite;
        lastPoll = Date.now();
        waiter = res;
        const timer = setTimeout(() => send(res, 204), 12_000);
        res.on('close', () => {
          clearTimeout(timer);
          if (waiter === res) waiter = null;
        });
        dispatch();
        return;
      }
      if (!same(invitation, invite)) return send(res, 409);
      if (path === '/relay/close') {
        invitation = undefined;
        if (waiter) send(waiter, 204);
        for (const entry of pending.values()) send(entry.res, 503);
        pending.clear();
        return send(res, 204);
      }
      const result = JSON.parse(await read(req));
      const entry = pending.get(result.id);
      if (entry && same(entry.invite, invite)) {
        const type = typeof result.type === 'string' && /^[\x20-\x7e]{1,120}$/.test(result.type)
          ? result.type : 'application/octet-stream';
        const body = Buffer.from(result.body, 'base64');
        const status = Number.isInteger(result.status) && result.status >= 200 && result.status <= 599
          ? result.status : 502;
        if (body.length <= limit) send(entry.res, status, body, type);
        else send(entry.res, 502);
      }
      return send(res, 204);
    }

    if (!invitation || Date.now() - lastPoll > 30_000) return send(res, 503, '房主暂未连接');
    if (req.method === 'GET' && path.startsWith('/invite/')) {
      if (!same(path.slice(8), invitation)) return send(res, 404);
      const secure = process.env.GAME_RELAY_SECURE !== '0' ? '; Secure' : '';
      res.writeHead(303, {Location: '/', 'Cache-Control': 'no-store', 'Referrer-Policy': 'no-referrer',
        'Set-Cookie': 'game_invite=' + invitation + '; Path=/; HttpOnly; SameSite=Lax' + secure});
      return res.end();
    }
    const cookie = (req.headers.cookie || '').match(/(?:^|; *)game_invite=([a-f0-9]{48})(?:;|$)/);
    if (!same(cookie?.[1], invitation)) return send(res, 403, '请打开房主分享的邀请链接');
    if ((req.method === 'POST' && req.headers['sec-fetch-site'] === 'cross-site') || !['GET', 'POST'].includes(req.method)
      || !path.startsWith('/') || path.startsWith('//') || path.includes('\\')) return send(res, 403);
    if (pending.size >= 12) return send(res, 503, '房间繁忙，请重试');
    const invite = invitation;
    const body = req.method === 'POST' ? await read(req, limit) : Buffer.alloc(0);
    if (body.length > limit || pending.size >= 12 || !same(invite, invitation)) return send(res, 503);
    const id = ++nextId;
    const timer = setTimeout(() => send(res, 504, '房主响应超时'), 12_000);
    res.on('close', () => { clearTimeout(timer); pending.delete(id); });
    pending.set(id, {res, invite, dispatched: false,
      job: {id, path, method: req.method, body: body.toString('base64')}});
    dispatch();
  } catch (err) {
    if (!res.headersSent && !res.destroyed) send(res, err.status || 400);
  }
});
server.requestTimeout = 15_000;
server.headersTimeout = 10_000;
server.listen(Number(process.env.GAME_RELAY_PORT || 18765), '127.0.0.1');
