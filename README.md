# Property_Valuation

Visitors sign up and log in with a username and password, stored in PostgreSQL.

## Setup

```sh
uv sync
createdb property_valuation        # the app's database
createdb property_valuation_test   # the tests' database
uv run python -m db                # apply the migrations
uv run streamlit run app.py
```

The app connects with the standard libpq environment variables (`PGHOST`, `PGUSER`, `PGPASSWORD`,
...), so with a local Homebrew PostgreSQL there is nothing to configure. The tests use
`property_valuation_test`, which each test empties first.

## Schema changes

The schema is built by the SQL files in [`migrations/`](migrations), applied in name order by
`python -m db` ([`db.py`](db.py)). Each runs once, in its own transaction; the `schema_migrations`
table records which have run. Every deploy applies new ones before the app starts, and a failing
migration stops the deploy with the previous version still running.

To change the schema, add the next file, e.g. `migrations/002_add_email_to_users.sql`. Two rules:

- **Never edit a migration that has been merged.** It has already run in production and won't run
  again. Add a new one instead.
- **Keep each migration compatible with the code before it.** The old container keeps serving
  until the new one is healthy, against the migrated schema. So add a column in one deploy and
  start requiring it in the next; stop using a column in one deploy and drop it in the next.

## Accounts

Anyone can sign up. Usernames are case-insensitive, 3 to 32 characters of ASCII letters, digits,
`.`, `-` and `_`; passwords are 8 to 128 characters and stored as argon2id hashes
([`users.py`](users.py)). A login lasts as long as the browser tab's session. There is no password
reset and no limit on login attempts.

See [doc/deployment.md](doc/deployment.md) for deployment.
