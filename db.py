"""PostgreSQL connection and migrations. `python -m db` applies the pending migrations.

Connection settings come from the standard libpq env vars (PGHOST, PGPORT, PGUSER, PGPASSWORD,
PGSSLMODE, ...); only the database name has a default here.
"""

from __future__ import annotations

import os
from pathlib import Path

import psycopg

DEFAULT_DATABASE = "property_valuation"
MIGRATIONS = Path(__file__).parent / "migrations"

# pg_advisory_lock key, so two containers starting at once don't both migrate.
MIGRATION_LOCK = 4_815_162_342


def connect() -> psycopg.Connection:
    return psycopg.connect(dbname=os.environ.get("PGDATABASE", DEFAULT_DATABASE), autocommit=True)


def migrate(conn: psycopg.Connection, directory: Path = MIGRATIONS) -> list[str]:
    """Apply the migrations not applied yet, each in its own transaction, and return their names."""
    conn.execute("SELECT pg_advisory_lock(%s)", (MIGRATION_LOCK,))
    try:
        conn.execute("CREATE TABLE IF NOT EXISTS schema_migrations (version text PRIMARY KEY, applied_at timestamptz NOT NULL DEFAULT now())")
        applied = {version for (version,) in conn.execute("SELECT version FROM schema_migrations")}
        pending = [path for path in sorted(directory.glob("*.sql")) if path.stem not in applied]
        for path in pending:
            with conn.transaction():
                conn.execute(path.read_text())
                conn.execute("INSERT INTO schema_migrations (version) VALUES (%s)", (path.stem,))
        return [path.stem for path in pending]
    finally:
        conn.execute("SELECT pg_advisory_unlock(%s)", (MIGRATION_LOCK,))


if __name__ == "__main__":
    with connect() as conn:
        applied = migrate(conn)
    print(f"Applied migrations: {', '.join(applied)}" if applied else "No migrations to apply.")
