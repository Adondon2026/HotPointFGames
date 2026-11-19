import { createHash, randomBytes, scrypt, timingSafeEqual } from 'node:crypto';
import { promisify } from 'node:util';
import { DatabaseSync } from 'node:sqlite';
import { join } from 'node:path';

const derive = promisify(scrypt);
const digest = value => createHash('sha256').update(value).digest('hex');
const random = bytes => randomBytes(bytes).toString('hex');
const second = () => Math.floor(Date.now() / 1000);
const error = (status, message) => Object.assign(new Error(message), {status});

export function cloudAccounts(directory, bootstrapDigest) {
  const db = new DatabaseSync(join(directory, 'cloud-accounts.sqlite'));
  db.exec(`
    PRAGMA journal_mode=WAL;
    CREATE TABLE IF NOT EXISTS accounts(id TEXT PRIMARY KEY, name TEXT UNIQUE COLLATE NOCASE,
      salt TEXT NOT NULL, password TEXT NOT NULL, admin INT NOT NULL, settings TEXT, revision INT NOT NULL DEFAULT 0);
    CREATE TABLE IF NOT EXISTS codes(hash TEXT PRIMARY KEY, expires INT NOT NULL);
    CREATE TABLE IF NOT EXISTS sessions(hash TEXT PRIMARY KEY, uid TEXT NOT NULL, expires INT NOT NULL);
    CREATE TABLE IF NOT EXISTS results(seq INTEGER PRIMARY KEY, uid TEXT NOT NULL, match TEXT NOT NULL,
      payload TEXT NOT NULL, UNIQUE(uid, match));
    CREATE INDEX IF NOT EXISTS results_uid_seq ON results(uid,seq);
  `);
  // Existing installations have no display_name. Keep login IDs permanent
  // while allowing an independent, editable public nickname.
  if (!db.prepare('PRAGMA table_info(accounts)').all().some(row => row.name === 'display_name')) {
    db.exec('ALTER TABLE accounts ADD COLUMN display_name TEXT');
  }
  function transaction(run) {
    db.exec('BEGIN IMMEDIATE');
    try {
      const value = run();
      db.exec('COMMIT');
      return value;
    } catch (err) {
      db.exec('ROLLBACK');
      throw err;
    }
  }
  const publicAccount = account => ({id: account.id, username: account.name,
    name: account.display_name || account.name, admin: !!account.admin});
  async function handle(data, options = {}) {
    const { action, name, password, code, token } = data;
    if (action === 'login' || action === 'register') {
      if (typeof name !== 'string' || !name.trim() || Array.from(name.trim()).length > 10
        || typeof password !== 'string' || password.length < 8 || password.length > 128) {
        throw error(400, '昵称限 1～10 字，账号密码至少 8 位');
      }
      const displayName = data.displayName == null ? name.trim() : String(data.displayName).trim();
      if (action === 'register' && (!displayName || Array.from(displayName).length > 12)) {
        throw error(400, '昵称限 1～12 字');
      }
      const existing = db.prepare('SELECT * FROM accounts WHERE name=?').get(name.trim());
      const salt = existing?.salt || random(16);
      const encoded = await derive(password, salt, 32);
      let account;
      if (action === 'login') {
        if (!existing || !timingSafeEqual(encoded, Buffer.from(existing.password, 'hex'))) {
          throw error(401, '昵称或账号密码不正确');
        }
        account = existing;
      } else {
        if (existing) throw error(409, '昵称已注册');
        const hash = digest(typeof code === 'string' ? code.trim() : '');
        account = transaction(() => {
          const first = !db.prepare('SELECT 1 FROM accounts LIMIT 1').get();
          const valid = first ? hash === bootstrapDigest
            : options.invited === true || db.prepare('DELETE FROM codes WHERE hash=? AND expires>?').run(hash, second()).changes === 1;
          if (!valid) throw error(403, '注册邀请码无效或已用过');
          const account = { id: random(16), name: name.trim(), admin: first ? 1 : 0 };
          db.prepare('INSERT INTO accounts(id,name,salt,password,admin,display_name) VALUES(?,?,?,?,?,?)')
            .run(account.id, account.name, salt, encoded.toString('hex'), account.admin, displayName);
          return account;
        });
      }
      const session = random(32);
      db.prepare('DELETE FROM sessions WHERE expires<=?').run(second());
      db.prepare('INSERT INTO sessions VALUES(?,?,?)').run(digest(session), account.id, second() + 90 * 86400);
      const fresh = db.prepare('SELECT * FROM accounts WHERE id=?').get(account.id);
      return { ...publicAccount(fresh), token: session };
    }
    const user = typeof token === 'string' && token.length === 64 && db.prepare(
      'SELECT a.* FROM accounts a JOIN sessions s ON a.id=s.uid WHERE s.hash=? AND s.expires>?'
    ).get(digest(token), second());
    if (!user) throw error(401, '云账号登录已失效，请重新登录');
    if (action === 'profile') return publicAccount(user);
    if (action === 'rename') {
      const displayName = typeof data.displayName === 'string' ? data.displayName.trim() : '';
      if (!displayName || Array.from(displayName).length > 12 || /[\\u0000-\\u001f]/u.test(displayName)) {
        throw error(400, '昵称限 1～12 字，不能包含控制字符');
      }
      db.prepare('UPDATE accounts SET display_name=? WHERE id=?').run(displayName,user.id);
      return publicAccount(db.prepare('SELECT * FROM accounts WHERE id=?').get(user.id));
    }
    if (action === 'logout') {
      db.prepare('DELETE FROM sessions WHERE hash=?').run(digest(token));
      return {};
    }
    if (action === 'invite') {
      if (!user.admin) throw error(403, '只有主账号能生成注册邀请码');
      const invite = random(12);
      db.prepare('DELETE FROM codes WHERE expires<=?').run(second());
      db.prepare('INSERT INTO codes VALUES(?,?)').run(digest(invite), second() + 86400);
      return { code: invite };
    }
    if (action === 'sync') {
      const { results, revision, settings, cursor } = data;
      if (!Array.isArray(results) || results.length > 100
        || !Number.isSafeInteger(cursor) || cursor < 0 || !Number.isSafeInteger(revision) || revision < 0
        || (settings != null && (typeof settings !== 'string' || settings.length > 16384))) throw error(400, '同步数据格式不正确');
      const insert = db.prepare('INSERT OR IGNORE INTO results(uid,match,payload) VALUES(?,?,?)');
      transaction(() => {
        for (const row of results) {
          if (!row || typeof row.match_id !== 'string' || row.match_id.length > 96 || !row.match_id
            || typeof row.game !== 'string' || row.game.length > 32 || ![0, 1].includes(row.won)
            || ![row.points, row.raw, row.ended].every(Number.isSafeInteger)
            || row.points < 0 || row.points > 100000 || !['friends','practice','legacy'].includes(row.queue)) {
            throw error(400, '战绩数据无效');
          }
          const { match_id, game, won, points, raw, ended, queue } = row;
          insert.run(user.id, match_id, JSON.stringify({match_id, game, won, points, raw, ended, queue}));
        }
        if (settings != null && settings !== user.settings && revision === user.revision) {
          const parsed = JSON.parse(settings);
          if (!parsed || Array.isArray(parsed) || typeof parsed !== 'object') throw error(400, '开房偏好无效');
          db.prepare('UPDATE accounts SET settings=?, revision=revision+1 WHERE id=?').run(settings, user.id);
        }
      });
      const saved = db.prepare('SELECT settings,revision FROM accounts WHERE id=?').get(user.id);
      const rows = db.prepare('SELECT seq,payload FROM results WHERE uid=? AND seq>? ORDER BY seq LIMIT 100').all(user.id,cursor);
      return {...saved, results:rows.map(row => JSON.parse(row.payload)), cursor:rows.at(-1)?.seq ?? cursor,
        accepted:results.map(row => row.match_id), more:rows.length === 100};
    }
    throw error(400, '未知账户操作');
  }
  return {handle, close: () => db.close()};
}
