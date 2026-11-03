import json
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from app.core.config import DATABASE


def now():
    return datetime.now(timezone.utc).isoformat()


def uid():
    return uuid.uuid4().hex


@contextmanager
def connection():
    db = sqlite3.connect(DATABASE, timeout=20)
    db.row_factory = sqlite3.Row
    db.execute('PRAGMA foreign_keys=ON')
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def init_db():
    DATABASE.parent.mkdir(parents=True, exist_ok=True)
    with connection() as db:
        db.execute('PRAGMA journal_mode=WAL')
        db.executescript('''
        CREATE TABLE IF NOT EXISTS users (
          id TEXT PRIMARY KEY, username TEXT UNIQUE NOT NULL, password TEXT NOT NULL,
          role TEXT NOT NULL, created_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS sessions (
          token TEXT PRIMARY KEY, user_id TEXT NOT NULL REFERENCES users(id), expires REAL NOT NULL);
        CREATE TABLE IF NOT EXISTS locations (
          id TEXT PRIMARY KEY, name TEXT NOT NULL, building TEXT NOT NULL,
          floor TEXT NOT NULL, created_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS people (
          id TEXT PRIMARY KEY, employee_id TEXT UNIQUE NOT NULL, name TEXT NOT NULL,
          contact TEXT NOT NULL, department TEXT NOT NULL, active INTEGER NOT NULL DEFAULT 1,
          consent INTEGER NOT NULL, consent_at TEXT, created_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS face_templates (
          id TEXT PRIMARY KEY, person_id TEXT REFERENCES people(id) ON DELETE CASCADE,
          embedding TEXT NOT NULL, model TEXT NOT NULL, created_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS cameras (
          id TEXT PRIMARY KEY, name TEXT NOT NULL, location_id TEXT NOT NULL REFERENCES locations(id),
          source TEXT NOT NULL, role TEXT NOT NULL, enabled INTEGER NOT NULL DEFAULT 0,
          recording INTEGER NOT NULL DEFAULT 0, line_x REAL NOT NULL DEFAULT 0.5,
          entry_direction TEXT NOT NULL DEFAULT 'right', retention_days INTEGER NOT NULL DEFAULT 7,
          created_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS attendance_events (
          id TEXT PRIMARY KEY, person_id TEXT NOT NULL REFERENCES people(id), camera_id TEXT REFERENCES cameras(id),
          kind TEXT NOT NULL, source TEXT NOT NULL, reason TEXT NOT NULL,
          occurred_at TEXT NOT NULL, event_key TEXT UNIQUE NOT NULL);
        CREATE TABLE IF NOT EXISTS attendance_sessions (
          id TEXT PRIMARY KEY, person_id TEXT NOT NULL REFERENCES people(id), in_at TEXT NOT NULL,
          out_at TEXT, in_event TEXT NOT NULL REFERENCES attendance_events(id),
          out_event TEXT REFERENCES attendance_events(id));
        CREATE UNIQUE INDEX IF NOT EXISTS one_open_session ON attendance_sessions(person_id) WHERE out_at IS NULL;
        CREATE TABLE IF NOT EXISTS sightings (
          id TEXT PRIMARY KEY, person_id TEXT NOT NULL REFERENCES people(id), camera_id TEXT NOT NULL REFERENCES cameras(id),
          confidence REAL NOT NULL, track_id TEXT NOT NULL, occurred_at TEXT NOT NULL);
        CREATE INDEX IF NOT EXISTS sighting_lookup ON sightings(person_id, occurred_at);
        CREATE TABLE IF NOT EXISTS recordings (
          id TEXT PRIMARY KEY, camera_id TEXT NOT NULL REFERENCES cameras(id), path TEXT NOT NULL,
          started_at TEXT NOT NULL, ended_at TEXT, status TEXT NOT NULL DEFAULT 'recording',
          bytes INTEGER NOT NULL DEFAULT 0);
        CREATE TABLE IF NOT EXISTS review_items (
          id TEXT PRIMARY KEY, person_id TEXT REFERENCES people(id), camera_id TEXT REFERENCES cameras(id),
          message TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'open', created_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS audit_logs (
          id TEXT PRIMARY KEY, actor TEXT NOT NULL, action TEXT NOT NULL, entity_id TEXT,
          details TEXT NOT NULL, created_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT NOT NULL);

        ''')
        # Upgrade existing horizontal camera settings without losing camera records.
        columns = {row['name'] for row in db.execute('PRAGMA table_info(cameras)')}
        if 'line_y' in columns and 'line_x' not in columns:
            db.execute('ALTER TABLE cameras RENAME COLUMN line_y TO line_x')
        db.execute("UPDATE cameras SET entry_direction=CASE entry_direction WHEN 'down' THEN 'right' WHEN 'up' THEN 'left' ELSE entry_direction END WHERE entry_direction IN ('down','up')")
        db.execute('PRAGMA user_version=2')
        defaults = {'timezone': 'Asia/Karachi', 'organization': 'Workspace', 'stale_seconds': 30}
        for key, value in defaults.items():
            db.execute('INSERT OR IGNORE INTO settings VALUES (?,?)', (key, json.dumps(value)))


def rows(sql, args=()):
    with connection() as db:
        return [dict(row) for row in db.execute(sql, args).fetchall()]


def audit(actor, action, entity_id=None, details=''):
    with connection() as db:
        db.execute('INSERT INTO audit_logs VALUES (?,?,?,?,?,?)',
                   (uid(), actor, action, entity_id, details, now()))
