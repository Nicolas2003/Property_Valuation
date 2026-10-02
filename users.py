"""User accounts: sign up and log in with a username and an argon2id-hashed password."""

from __future__ import annotations

import re
from contextlib import suppress

import psycopg
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerifyMismatchError

USERNAME = re.compile(r"[a-z0-9_.-]{3,32}")
MIN_PASSWORD = 8
MAX_PASSWORD = 128

hasher = PasswordHasher()
UNKNOWN_USER_HASH = hasher.hash("unknown user")


class InvalidSignUp(ValueError):
    pass


class UsernameTaken(InvalidSignUp):
    def __init__(self, username: str):
        super().__init__(f"The username {username} is already taken.")


def normalize(username: str) -> str:
    # Only ASCII is lowercased: Unicode lowercasing folds some characters into ASCII (the Kelvin sign becomes "k").
    username = username.strip()
    return username.lower() if username.isascii() else username


def sign_up(conn: psycopg.Connection, username: str, password: str) -> str:
    """Create an account and return its normalized username."""
    username = normalize(username)
    if not USERNAME.fullmatch(username):
        raise InvalidSignUp("Usernames are 3 to 32 characters: letters, digits, dots, dashes and underscores.")
    if not MIN_PASSWORD <= len(password) <= MAX_PASSWORD:
        raise InvalidSignUp(f"Passwords are {MIN_PASSWORD} to {MAX_PASSWORD} characters.")

    try:
        conn.execute("INSERT INTO users (username, password_hash) VALUES (%s, %s)", (username, hasher.hash(password)))
    except psycopg.errors.UniqueViolation:
        raise UsernameTaken(username) from None
    return username


def authenticate(conn: psycopg.Connection, username: str, password: str) -> str | None:
    """Return the normalized username if the password is right, None otherwise."""
    username = normalize(username)
    row = conn.execute("SELECT password_hash FROM users WHERE username = %s", (username,)).fetchone()
    if row is None:
        # Same work as a wrong password, so response times don't reveal which usernames exist.
        with suppress(VerifyMismatchError):
            hasher.verify(UNKNOWN_USER_HASH, password)
        return None

    (password_hash,) = row
    try:
        hasher.verify(password_hash, password)
    except (VerifyMismatchError, InvalidHashError):
        return None

    if hasher.check_needs_rehash(password_hash):
        conn.execute("UPDATE users SET password_hash = %s WHERE username = %s", (hasher.hash(password), username))
    return username
