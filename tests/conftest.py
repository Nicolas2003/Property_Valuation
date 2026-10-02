from __future__ import annotations

import pytest

import db

# A real PostgreSQL database; PGHOST, PGUSER etc. come from the environment. Locally: createdb property_valuation_test
TEST_DATABASE = "property_valuation_test"


@pytest.fixture
def conn(monkeypatch):
    """A connection to the emptied test database. The app under test connects to it too."""
    monkeypatch.setenv("PGDATABASE", TEST_DATABASE)
    with db.connect() as conn:
        db.migrate(conn)
        conn.execute("TRUNCATE users")
        yield conn
