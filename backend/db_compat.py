"""Small database compatibility layer for SQLite and PostgreSQL.

The application keeps the existing SQLite SQL surface for local development,
while production can use PostgreSQL by setting DATABASE_URL.
"""
import re


def _raise_db_error(exc):
    try:
        from psycopg import errors as pg_errors
        from backend.utils import DatabaseIntegrityError, DatabaseOperationalError, DatabaseError
        if isinstance(exc, pg_errors.IntegrityError):
            raise DatabaseIntegrityError(str(exc)) from exc
        if isinstance(exc, pg_errors.OperationalError):
            raise DatabaseOperationalError(str(exc)) from exc
        raise DatabaseError(str(exc)) from exc
    except ImportError:
        raise exc


def _translate_sql(sql: str) -> str:
    s = sql
    # SQLite placeholder syntax -> PostgreSQL/psycopg parameter style.
    s = s.replace('?', '%s')
    # SQLite upsert syntax used by the existing seed/migration code.
    s = re.sub(r'\bINSERT\s+OR\s+IGNORE\s+INTO\b', 'INSERT INTO', s, flags=re.I)
    if re.search(r'\bINSERT INTO\b', s, flags=re.I) and 'ON CONFLICT' not in s.upper() and 'INSERT INTO' in s.upper():
        # Only add DO NOTHING for the legacy INSERT OR IGNORE conversion marker.
        # The marker is added by a second pass below to avoid changing normal INSERTs.
        pass
    # Specific marker produced by the previous substitution: retain a lightweight
    # convention by converting the prefix to a tagged comment first is more work
    # than the few call-sites need. They are handled by the regex below.
    # Convert SQLite date helpers used by this project.
    s = s.replace("date('now')", 'CURRENT_DATE')
    s = s.replace("datetime(otp_expires_at)", "otp_expires_at::timestamp")
    s = s.replace("datetime('now','-1 day')", "CURRENT_TIMESTAMP - INTERVAL '1 day'")
    return s


def postgres_schema(sql_text: str) -> str:
    """Translate the project's SQLite schema into PostgreSQL-compatible DDL."""
    s = sql_text
    s = re.sub(r'^\s*PRAGMA\s+[^;]+;\s*$', '', s, flags=re.I | re.M)
    s = re.sub(r'INTEGER\s+PRIMARY\s+KEY\s+AUTOINCREMENT', 'BIGSERIAL PRIMARY KEY', s, flags=re.I)
    # INTEGER primary keys without AUTOINCREMENT are rare here; keep them as BIGINT.
    s = re.sub(r'\bINTEGER\s+PRIMARY\s+KEY\b', 'BIGINT PRIMARY KEY', s, flags=re.I)
    # Convert SQLite's INSERT OR IGNORE only if it somehow appears in DDL seed snippets.
    s = re.sub(r'\bINSERT\s+OR\s+IGNORE\s+INTO\b', 'INSERT INTO', s, flags=re.I)
    return s


class PGCursor:
    def __init__(self, cursor, connection):
        self._cursor = cursor
        self._connection = connection

    def execute(self, sql, params=None):
        try:
            self._cursor.execute(_translate_sql(sql), params)
        except Exception as exc:
            _raise_db_error(exc)
        return self

    def fetchone(self):
        return self._cursor.fetchone()

    def fetchall(self):
        return self._cursor.fetchall()

    @property
    def rowcount(self):
        return self._cursor.rowcount

    def close(self):
        return self._cursor.close()


class PGConnection:
    def __init__(self, raw_connection):
        self._raw = raw_connection

    def execute(self, sql, params=None):
        cur = self._raw.cursor()
        # Compatibility for SQLite's last_insert_rowid().
        if re.fullmatch(r'\s*SELECT\s+last_insert_rowid\(\)\s*', sql, flags=re.I):
            cur.execute('SELECT LASTVAL() AS id')
            return PGCursor(cur, self)
        translated = _translate_sql(sql)
        # Convert only legacy INSERT OR IGNORE calls that still reach this layer.
        if re.search(r'\bINSERT\s+OR\s+IGNORE\s+INTO\b', sql, flags=re.I):
            translated = re.sub(r'\bINSERT\s+OR\s+IGNORE\s+INTO\b', 'INSERT INTO', translated, flags=re.I)
            translated += ' ON CONFLICT DO NOTHING'
        try:
            cur.execute(translated, params)
        except Exception as exc:
            _raise_db_error(exc)
        return PGCursor(cur, self)

    def executescript(self, sql_text):
        """Run SQLite schema DDL in an order PostgreSQL accepts."""
        sql = postgres_schema(sql_text)
        statements = [
            statement.strip()
            for statement in sql.split(';')
            if statement.strip()
        ]

        table_statements = []
        other_statements = []

        for statement in statements:
            match = re.search(
                r'CREATE\s+TABLE\s+IF\s+NOT\s+EXISTS\s+([a-zA-Z_][a-zA-Z0-9_]*)',
                statement,
                flags=re.I,
            )
            if match:
                table_statements.append((match.group(1).lower(), statement))
            else:
                other_statements.append(statement)

        created_tables = set()

        while table_statements:
            progressed = False

            for table_name, statement in table_statements[:]:
                dependencies = {
                    name.lower()
                    for name in re.findall(
                        r'REFERENCES\s+([a-zA-Z_][a-zA-Z0-9_]*)',
                        statement,
                        flags=re.I,
                    )
                }

                if dependencies.issubset(created_tables):
                    self.execute(statement)
                    created_tables.add(table_name)
                    table_statements.remove((table_name, statement))
                    progressed = True

            if not progressed:
                for table_name, statement in table_statements:
                    self.execute(statement)
                    created_tables.add(table_name)
                break

        for statement in other_statements:
            self.execute(statement)

    def commit(self):
        self._raw.commit()

    def rollback(self):
        self._raw.rollback()

    def close(self):
        self._raw.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        if exc_type:
            self.rollback()
        else:
            self.commit()
        self.close()
        return False
