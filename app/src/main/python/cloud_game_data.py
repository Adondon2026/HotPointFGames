"""Sync the active cloud player's rows through the game's local account database."""
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import secrets
import sqlite3
import time


@contextmanager
def _database():
    data = Path(os.environ.get("GAMEHALL_DATA_DIR", str(Path.home())))
    data.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(data / "gamehall_accounts.sqlite3", timeout=5)
    db.row_factory = sqlite3.Row
    try:
        db.executescript("""
            CREATE TABLE IF NOT EXISTS users(id TEXT PRIMARY KEY,name TEXT UNIQUE COLLATE NOCASE,salt TEXT NOT NULL,pin_hash TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS room_preferences(owner TEXT PRIMARY KEY,settings TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS sessions(token_hash TEXT PRIMARY KEY,user_id TEXT NOT NULL,expires INTEGER NOT NULL);
            CREATE TABLE IF NOT EXISTS results(match_id TEXT NOT NULL,user_id TEXT NOT NULL,game TEXT NOT NULL,won INTEGER NOT NULL,
                points INTEGER NOT NULL,raw INTEGER NOT NULL,ended INTEGER NOT NULL,queue TEXT NOT NULL DEFAULT 'legacy',PRIMARY KEY(match_id,user_id));
            CREATE TABLE IF NOT EXISTS cloud_sync(uid TEXT PRIMARY KEY,cursor INTEGER NOT NULL,revision INTEGER NOT NULL,settings TEXT);
            CREATE TABLE IF NOT EXISTS cloud_synced(uid TEXT NOT NULL,match_id TEXT NOT NULL,PRIMARY KEY(uid,match_id));
        """)
        with db:
            db.execute("BEGIN IMMEDIATE")
            if "queue" not in {column[1] for column in db.execute("PRAGMA table_info(results)")}:
                db.execute("ALTER TABLE results ADD COLUMN queue TEXT NOT NULL DEFAULT 'legacy'")
            yield db
    finally:
        db.close()


def prepare(uid, name, local_token):
    with _database() as db:
        collision = db.execute("SELECT id FROM users WHERE name=? AND id<>?", (name, uid)).fetchone()
        if collision:
            raise ValueError("本机已有同名旧账号，请为云端账号换一个昵称")
        db.execute("INSERT OR IGNORE INTO users VALUES(?,?,?,?)",
                   (uid, name, secrets.token_hex(16), secrets.token_hex(32)))
        token_hash = hashlib.sha256(local_token.encode()).hexdigest()
        db.execute("INSERT OR REPLACE INTO sessions VALUES(?,?,?)", (token_hash, uid, int(time.time()) + 3650 * 86400))


def _settings(db, uid):
    row = db.execute("SELECT settings FROM room_preferences WHERE owner=?", ("account:" + uid,)).fetchone()
    return row["settings"] if row else None


def forget_session(local_token):
    with _database() as db:
        db.execute("DELETE FROM sessions WHERE token_hash=?", (hashlib.sha256(local_token.encode()).hexdigest(),))


def pending(uid):
    with _database() as db:
        previous = db.execute("SELECT cursor,revision,settings FROM cloud_sync WHERE uid=?", (uid,)).fetchone()
        results = db.execute("""SELECT r.match_id,r.game,r.won,r.points,r.raw,r.ended,r.queue FROM results r
            WHERE r.user_id=? AND NOT EXISTS(SELECT 1 FROM cloud_synced s WHERE s.uid=r.user_id AND s.match_id=r.match_id)
            ORDER BY r.ended,r.match_id LIMIT 100""", (uid,)).fetchall()
        local = _settings(db, uid)
        return json.dumps({
            "cursor": previous["cursor"] if previous else 0, "revision": previous["revision"] if previous else 0,
            "settings": local if not previous or local != previous["settings"] else None,
            "localSettings": local, "results": [dict(row) for row in results],
        }, ensure_ascii=False)


def apply(uid, sent_settings, raw):
    response = json.loads(raw)
    with _database() as db:
        for row in response["results"]:
            db.execute("INSERT OR IGNORE INTO results(match_id,user_id,game,won,points,raw,ended,queue) VALUES(?,?,?,?,?,?,?,?)",
                       (row["match_id"], uid, row["game"], row["won"], row["points"], row["raw"], row["ended"], row["queue"]))
        db.executemany("INSERT OR IGNORE INTO cloud_synced VALUES(?,?)",
                       [(uid, match) for match in response["accepted"]] + [(uid, row["match_id"]) for row in response["results"]])
        settings = response["settings"]
        if settings is not None and _settings(db, uid) == sent_settings:
            db.execute("INSERT OR REPLACE INTO room_preferences VALUES(?,?)", ("account:" + uid, settings))
        db.execute("INSERT OR REPLACE INTO cloud_sync VALUES(?,?,?,?)",
                   (uid, response["cursor"], response["revision"], settings))
