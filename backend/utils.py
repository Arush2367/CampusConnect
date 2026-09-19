"""Campus Buddy — Shared utility functions."""
import hashlib, hmac, json, secrets, re
from datetime import datetime, timezone, timedelta
import sqlite3
import os

from backend.config import DB, SESSION_DAYS, PERMISSIONS


class DatabaseError(Exception):
    """Backend database error abstraction used by both SQLite and PostgreSQL."""


class DatabaseIntegrityError(DatabaseError):
    """Constraint/integrity violation abstraction."""


class DatabaseOperationalError(DatabaseError):
    """Operational database error abstraction."""


# ── Time helpers ──────────────────────────────────────────────
def now():
    """Current UTC time as ISO-8601 string."""
    return datetime.now(timezone.utc).isoformat(timespec='seconds')


def later(days):
    """UTC time `days` in the future as ISO-8601 string."""
    return (datetime.now(timezone.utc) + timedelta(days=days)).isoformat(timespec='seconds')


# ── Database connection ───────────────────────────────────────
def conn():
    """Open a database connection. PostgreSQL is used when DATABASE_URL is set; otherwise SQLite."""
    database_url = os.environ.get('DATABASE_URL', '').strip()
    if database_url:
        try:
            import psycopg
            from psycopg.rows import dict_row
            from psycopg import errors as pg_errors
            from backend.db_compat import PGConnection
            raw = psycopg.connect(database_url, row_factory=dict_row, connect_timeout=10)
            # Expose a sqlite-compatible error surface to existing code through
            # module-level abstractions; the actual handler catches the abstraction.
            return PGConnection(raw)
        except ImportError as exc:
            raise RuntimeError('DATABASE_URL is set but psycopg is not installed. Run pip install -r requirements.txt.') from exc
        except Exception as exc:
            # Keep PostgreSQL connection failures inside the API's controlled
            # error path instead of letting a serverless invocation crash.
            raise DatabaseOperationalError('Unable to connect to PostgreSQL.') from exc
    c = sqlite3.connect(DB, timeout=8, check_same_thread=False)
    c.row_factory = sqlite3.Row
    c.execute('PRAGMA foreign_keys=ON')
    c.execute('PRAGMA journal_mode=WAL')
    c.execute('PRAGMA busy_timeout=8000')
    return c


# ── Password hashing (scrypt) ─────────────────────────────────
def hpw(password, salt=None):
    """Hash a password with scrypt. Returns 'salt_hex:hash_hex'."""
    salt = salt or secrets.token_bytes(16)
    digest = hashlib.scrypt(password.encode(), salt=salt, n=16384, r=8, p=1, dklen=64)
    return f'{salt.hex()}:{digest.hex()}'


def vpw(password, stored):
    """Verify password against a stored scrypt hash. Returns bool."""
    try:
        salt_hex, hash_hex = stored.split(':', 1)
        digest = hashlib.scrypt(password.encode(), salt=bytes.fromhex(salt_hex),
                                n=16384, r=8, p=1, dklen=64)
        return hmac.compare_digest(digest.hex(), hash_hex)
    except Exception:
        return False


# ── Schema migration helper ───────────────────────────────────
def ensure_column(c, table, name, ddl):
    """Add a column to `table` if it doesn't already exist."""
    if os.environ.get('DATABASE_URL', '').strip():
        exists = c.execute(
            "SELECT 1 FROM information_schema.columns WHERE table_schema='public' AND table_name=%s AND column_name=%s",
            (table, name),
        ).fetchone()
        if not exists:
            c.execute(f'ALTER TABLE {table} ADD COLUMN IF NOT EXISTS {name} {ddl}')
        return
    cols = {r[1] for r in c.execute(f'PRAGMA table_info({table})').fetchall()}
    if name not in cols:
        c.execute(f'ALTER TABLE {table} ADD COLUMN {name} {ddl}')


# ── Audit logging ─────────────────────────────────────────────
def audit(c, actor_id, actor_role, action, entity_type=None, entity_id=None,
          previous_state=None, new_state=None, correlation_id=None,
          request_id=None, meta=None):
    """Insert an append-only audit event."""
    c.execute(
        'INSERT INTO audit_events(actor_id,actor_role,action,entity_type,'
        'entity_id,previous_state,new_state,correlation_id,request_id,'
        'metadata_json) VALUES(?,?,?,?,?,?,?,?,?,?)',
        (actor_id, actor_role, action, entity_type, entity_id,
         previous_state, new_state, correlation_id, request_id,
         json.dumps(meta or {}, separators=(',', ':')))
    )


# ── Notification helper ───────────────────────────────────────
def notify(c, user_id, typ, title, body, entity_type=None, entity_id=None):
    """Create a persistent notification for a user."""
    if user_id:
        c.execute(
            'INSERT INTO notifications(user_id,type,title,body,entity_type,'
            'entity_id) VALUES(?,?,?,?,?,?)',
            (user_id, typ, title, body, entity_type, entity_id)
        )


# ── Locker event helper ───────────────────────────────────────
def locker_event(c, locker_id, actor_id, typ, previous_state, new_state,
                 request_code=None, notes=None, correlation_id=None):
    """Record a locker lifecycle event."""
    c.execute(
        'INSERT INTO locker_events(locker_id,actor_user_id,event_type,'
        'previous_state,new_state,request_code,notes,correlation_id) '
        'VALUES(?,?,?,?,?,?,?,?)',
        (locker_id, actor_id, typ, previous_state, new_state,
         request_code, notes, correlation_id)
    )


# ── Permission helpers ────────────────────────────────────────
def get_permissions(user):
    """Return the set of permissions for a user row."""
    return PERMISSIONS.get(user['access_role'], set())


# ── Cookie helper ─────────────────────────────────────────────
import os

def make_cookie(sid, delete=False):
    """Build a Set-Cookie header value for the session."""
    if delete:
        return 'sid=; Max-Age=0; Path=/; HttpOnly; SameSite=Lax'
    from backend.config import HTTPS, COOKIE_SAMESITE
    secure = '; Secure' if HTTPS else ''
    return (f'sid={sid}; Max-Age={SESSION_DAYS * 86400}; '
            f'Path=/; HttpOnly; SameSite={COOKIE_SAMESITE}{secure}')


# ── Public user serialization ─────────────────────────────────
def public_user(r, private=False):
    """Serialize a user row for API response, omitting sensitive fields."""
    d = {
        'id': r['student_id'] or r['username'],
        'loginId': r['username'],
        'name': r['full_name'],
        'role': r['role'],
        'accountType': r['account_type'],
        'accessRole': r['access_role'],
        'course': r['course'],
        'branch': r['branch'],
        'year': r['year'],
        'semester': r['semester'],
        'campus': r['campus'],
        'email': r['email'],
        'joinedAt': r['joined_at'] or r['created_at'],
    }
    if private:
        d.update({
            'mobile': r['mobile'],
            'profilePhoto': r['profile_photo'],
            'studentId': r['student_id'],
        })
    return d
