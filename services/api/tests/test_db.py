"""Database bootstrap tests."""

from services.api.app import db


class _FakeCursor:
    def __init__(self, table_exists: bool):
        self.table_exists = table_exists
        self.executed = []

    def execute(self, sql, params=None):
        self.executed.append((sql, params))

    def fetchone(self):
        sql, _ = self.executed[-1]
        if "information_schema.tables" in sql:
            return (self.table_exists,)
        raise AssertionError(f"Unexpected fetchone() for SQL: {sql!r}")


class _FakeConnection:
    def __init__(self, cursor: _FakeCursor):
        self._cursor = cursor
        self.commits = 0

    def cursor(self):
        return self._cursor

    def commit(self):
        self.commits += 1


def test_ensure_base_schema_executes_bootstrap_sql_when_projects_table_missing(tmp_path, monkeypatch):
    sql_path = tmp_path / "init.sql"
    sql_path.write_text("CREATE TABLE bootstrap_marker (id INT);", encoding="utf-8")
    cursor = _FakeCursor(table_exists=False)
    conn = _FakeConnection(cursor)
    monkeypatch.setattr(db, "_bootstrap_schema_sql_path", lambda: sql_path)

    db._ensure_base_schema(conn)

    assert any("information_schema.tables" in sql for sql, _ in cursor.executed)
    assert cursor.executed[-1][0] == "CREATE TABLE bootstrap_marker (id INT);"
    assert conn.commits == 1


def test_ensure_base_schema_skips_bootstrap_when_projects_table_exists(tmp_path, monkeypatch):
    sql_path = tmp_path / "init.sql"
    sql_path.write_text("CREATE TABLE bootstrap_marker (id INT);", encoding="utf-8")
    cursor = _FakeCursor(table_exists=True)
    conn = _FakeConnection(cursor)
    monkeypatch.setattr(db, "_bootstrap_schema_sql_path", lambda: sql_path)

    db._ensure_base_schema(conn)

    assert len(cursor.executed) == 1
    assert "information_schema.tables" in cursor.executed[0][0]
    assert conn.commits == 0
