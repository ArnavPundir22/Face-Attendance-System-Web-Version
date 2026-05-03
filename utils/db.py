"""
Database utility functions.

Provides connection helpers, schema initialisation, and user management.
All functions use parameterised queries to prevent SQL injection.
"""

import sqlite3
import bcrypt
from email.utils import parseaddr

import config


def get_db_connection() -> sqlite3.Connection:
    """Return a new SQLite connection with Row factory enabled."""
    conn = sqlite3.connect(config.DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn


def init_users_table_and_admin():
    """
    Create required tables if they do not exist and seed a default admin
    account on first run.

    Default admin credentials (first run only):
        username : admin
        password : admin123   ← change immediately after first login
    """
    conn = get_db_connection()

    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id       INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            password BLOB,
            is_admin INTEGER DEFAULT 0,
            gmail    TEXT
        )
    """)

    # Migrate older databases that were created before the gmail column existed.
    try:
        conn.execute("ALTER TABLE users ADD COLUMN gmail TEXT")
    except sqlite3.OperationalError:
        pass  # column already exists

    conn.execute("""
        CREATE TABLE IF NOT EXISTS password_reset_tokens (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            username   TEXT NOT NULL,
            otp        TEXT NOT NULL,
            expires_at TEXT NOT NULL,
            used       INTEGER DEFAULT 0
        )
    """)
    conn.commit()

    row = conn.execute("SELECT COUNT(*) AS cnt FROM users").fetchone()
    if (row['cnt'] if row else 0) == 0:
        hashed = bcrypt.hashpw(b'admin123', bcrypt.gensalt())
        conn.execute(
            "INSERT INTO users (username, password, is_admin) VALUES (?, ?, ?)",
            ('admin', hashed, 1),
        )
        conn.commit()

    conn.close()


def create_user(username: str, password: str, is_admin: int = 0, gmail: str = '') -> bool:
    """Hash *password* and insert a new user row.

    Returns ``True`` on success, ``False`` if the username already exists.
    """
    conn = get_db_connection()
    try:
        hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt())
        conn.execute(
            "INSERT INTO users (username, password, is_admin, gmail) VALUES (?, ?, ?, ?)",
            (username, hashed, is_admin, gmail.strip()),
        )
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()


def is_valid_email(email: str) -> bool:
    """Return ``True`` only when *email* has a non-empty local-part and domain."""
    _, addr = parseaddr(email)
    if not addr or '@' not in addr:
        return False
    local, domain = addr.rsplit('@', 1)
    return bool(local) and bool(domain)
