from __future__ import annotations

import pytest

import users

KELVIN = chr(0x212A)  # lowercases to "k"


def test_sign_up_then_authenticate(conn):
    assert users.sign_up(conn, "ada", "correct horse") == "ada"

    assert users.authenticate(conn, "ada", "correct horse") == "ada"


def test_wrong_password(conn):
    users.sign_up(conn, "ada", "correct horse")

    assert users.authenticate(conn, "ada", "battery staple") is None


def test_unknown_user(conn):
    assert users.authenticate(conn, "nobody", "correct horse") is None


def test_unknown_user_with_the_dummy_password(conn):
    assert users.authenticate(conn, "nobody", "unknown user") is None


def test_usernames_are_case_insensitive(conn):
    assert users.sign_up(conn, " Ada ", "correct horse") == "ada"

    assert users.authenticate(conn, "ADA", "correct horse") == "ada"


def test_non_ascii_lookalikes_are_not_the_same_user(conn):
    users.sign_up(conn, "kel", "correct horse")

    assert users.authenticate(conn, KELVIN + "el", "correct horse") is None


def test_username_taken(conn):
    users.sign_up(conn, "ada", "correct horse")

    with pytest.raises(users.UsernameTaken, match="ada is already taken"):
        users.sign_up(conn, "Ada", "another password")


@pytest.mark.parametrize("username", ["ab", "a" * 33, "ada lovelace", "ada!", "", "adé", KELVIN + "el"])
def test_invalid_username(conn, username):
    with pytest.raises(users.InvalidSignUp, match="Usernames are 3 to 32 characters"):
        users.sign_up(conn, username, "correct horse")


@pytest.mark.parametrize("password", ["short", "x" * 129])
def test_invalid_password(conn, password):
    with pytest.raises(users.InvalidSignUp, match="Passwords are 8 to 128 characters"):
        users.sign_up(conn, "ada", password)


def test_rehashes_outdated_hashes_on_login(conn):
    old = users.PasswordHasher(time_cost=1).hash("correct horse")
    conn.execute("INSERT INTO users (username, password_hash) VALUES ('ada', %s)", (old,))

    assert users.authenticate(conn, "ada", "correct horse") == "ada"
    (password_hash,) = conn.execute("SELECT password_hash FROM users").fetchone()
    assert password_hash != old
    assert not users.hasher.check_needs_rehash(password_hash)


def test_passwords_are_stored_hashed(conn):
    users.sign_up(conn, "ada", "correct horse")

    (password_hash,) = conn.execute("SELECT password_hash FROM users").fetchone()
    assert password_hash.startswith("$argon2id$")
    assert "correct horse" not in password_hash
