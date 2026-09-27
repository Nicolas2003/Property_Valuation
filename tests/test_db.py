from __future__ import annotations

import psycopg
import pytest

import db


@pytest.fixture
def scratch(conn):
    """The test connection, creating tables in an empty schema that's dropped afterwards."""
    conn.execute("DROP SCHEMA IF EXISTS migrations_test CASCADE")
    conn.execute("CREATE SCHEMA migrations_test")
    conn.execute("SET search_path TO migrations_test")
    yield conn
    conn.execute("SET search_path TO DEFAULT")
    conn.execute("DROP SCHEMA migrations_test CASCADE")


@pytest.fixture
def migrations(tmp_path):
    def write(name: str, sql: str) -> None:
        (tmp_path / f"{name}.sql").write_text(sql)

    write.directory = tmp_path
    return write


def recorded(conn) -> list[str]:
    return [v for (v,) in conn.execute("SELECT version FROM schema_migrations ORDER BY version")]


def test_applies_migrations_in_name_order(scratch, migrations):
    migrations("002_add_row", "INSERT INTO things VALUES (1)")
    migrations("001_create_things", "CREATE TABLE things (id int)")

    assert db.migrate(scratch, migrations.directory) == ["001_create_things", "002_add_row"]
    assert scratch.execute("SELECT id FROM things").fetchall() == [(1,)]
    assert recorded(scratch) == ["001_create_things", "002_add_row"]


def test_applies_each_migration_once(scratch, migrations):
    migrations("001_create_things", "CREATE TABLE things (id int)")
    db.migrate(scratch, migrations.directory)

    assert db.migrate(scratch, migrations.directory) == []

    migrations("002_add_row", "INSERT INTO things VALUES (1)")
    assert db.migrate(scratch, migrations.directory) == ["002_add_row"]


def test_a_failed_migration_is_rolled_back_and_not_recorded(scratch, migrations):
    migrations("001_create_things", "CREATE TABLE things (id int)")
    migrations("002_broken", "CREATE TABLE others (id int); SELECT 1 / 0")

    with pytest.raises(psycopg.errors.DivisionByZero):
        db.migrate(scratch, migrations.directory)

    assert recorded(scratch) == ["001_create_things"]
    assert scratch.execute("SELECT to_regclass('others')").fetchone() == (None,)
    with db.connect() as other:  # the lock was released
        assert other.execute("SELECT pg_try_advisory_lock(%s)", (db.MIGRATION_LOCK,)).fetchone()[0]


def test_the_app_migrations_apply_cleanly(scratch):
    assert db.migrate(scratch) == sorted(path.stem for path in db.MIGRATIONS.glob("*.sql"))
    assert db.migrate(scratch) == []
