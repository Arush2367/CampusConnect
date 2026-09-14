"""Static PostgreSQL compatibility checks that do not require a live database."""
from pathlib import Path
from backend.db_compat import postgres_schema, _translate_sql

ROOT = Path(__file__).resolve().parents[1]
schema = (ROOT / 'database' / 'schema.sql').read_text(encoding='utf-8')
out = postgres_schema(schema)
assert 'PRAGMA' not in out.upper()
assert 'AUTOINCREMENT' not in out.upper()
assert 'BIGSERIAL PRIMARY KEY' in out
assert _translate_sql("SELECT * FROM events WHERE event_date >= date('now')").endswith('CURRENT_DATE')
assert _translate_sql("SELECT last_insert_rowid()").strip() == 'SELECT last_insert_rowid()'
assert 'VALUES(%s,%s)' in _translate_sql('INSERT OR IGNORE INTO x(a,b) VALUES(?,?)')
print('POSTGRES_COMPAT_STATIC_CHECK_PASSED')
