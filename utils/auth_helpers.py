"""
Authentication helper functions.

Covers:
  - In-memory login rate-limiting (account lockout)
  - Password-reset OTP generation, storage, and verification
  - Admin-status check for the current session user
"""

import hashlib
import secrets
from datetime import datetime, timedelta

import bcrypt
from flask import session

import config
from utils.db import get_db_connection


# ---------------------------------------------------------------------------
# Login rate-limiting
#
# NOTE: This tracker is in-memory and resets on server restart.  It is also
# not shared across multiple worker processes.  For multi-worker production
# deployments persist attempt counts in the database or Redis instead.
# ---------------------------------------------------------------------------

_login_attempts: dict = {}  # { username: {'count': int, 'locked_until': datetime|None} }


def _get_attempts(username: str) -> dict:
    return _login_attempts.setdefault(username, {'count': 0, 'locked_until': None})


def is_account_locked(username: str) -> tuple[bool, int]:
    """Return ``(locked, seconds_remaining)``."""
    entry = _get_attempts(username)
    now = datetime.now()
    if entry['locked_until'] and now < entry['locked_until']:
        remaining = int((entry['locked_until'] - now).total_seconds())
        return True, remaining
    # Reset an expired lock.
    if entry['locked_until'] and now >= entry['locked_until']:
        entry['count'] = 0
        entry['locked_until'] = None
    return False, 0


def record_failed_login(username: str) -> None:
    """Increment the failure counter; lock the account when the threshold is reached."""
    entry = _get_attempts(username)
    entry['count'] += 1
    if entry['count'] >= config.LOGIN_MAX_ATTEMPTS:
        entry['locked_until'] = datetime.now() + timedelta(minutes=config.LOGIN_LOCKOUT_MINUTES)


def clear_failed_logins(username: str) -> None:
    """Clear the failure counter on a successful login or password reset."""
    _login_attempts.pop(username, None)


def remaining_attempts(username: str) -> int:
    """Return how many more failures are allowed before lockout."""
    count = _get_attempts(username)['count']
    return max(config.LOGIN_MAX_ATTEMPTS - count, 0)


# ---------------------------------------------------------------------------
# Password-reset OTP
# ---------------------------------------------------------------------------

def _hash_otp(otp: str) -> str:
    """Return a SHA-256 hex digest of *otp* for safe storage."""
    return hashlib.sha256(otp.encode()).hexdigest()


def generate_and_store_otp(username: str) -> str:
    """Generate a 6-digit OTP (100 000 – 999 999), store its hash, and return the plain value."""
    otp = str(secrets.randbelow(config.OTP_RANGE_SIZE) + config.OTP_RANGE_START)
    otp_hash = _hash_otp(otp)
    expires_at = (
        datetime.now() + timedelta(minutes=config.OTP_EXPIRY_MINUTES)
    ).strftime("%Y-%m-%d %H:%M:%S")

    conn = get_db_connection()
    # Invalidate any existing unused tokens for this user.
    conn.execute(
        "UPDATE password_reset_tokens SET used=1 WHERE username=? AND used=0",
        (username,),
    )
    conn.execute(
        "INSERT INTO password_reset_tokens (username, otp, expires_at) VALUES (?, ?, ?)",
        (username, otp_hash, expires_at),
    )
    conn.commit()
    conn.close()
    return otp


def verify_and_consume_otp(username: str, otp: str) -> bool:
    """Return ``True`` and mark the OTP as used if it matches and has not expired."""
    conn = get_db_connection()
    row = conn.execute(
        "SELECT id, otp, expires_at FROM password_reset_tokens "
        "WHERE username=? AND used=0 ORDER BY id DESC LIMIT 1",
        (username,),
    ).fetchone()

    if not row:
        conn.close()
        return False
    if datetime.now() > datetime.strptime(row['expires_at'], "%Y-%m-%d %H:%M:%S"):
        conn.close()
        return False
    if not secrets.compare_digest(_hash_otp(otp), row['otp']):
        conn.close()
        return False

    conn.execute("UPDATE password_reset_tokens SET used=1 WHERE id=?", (row['id'],))
    conn.commit()
    conn.close()
    return True


# ---------------------------------------------------------------------------
# Session / admin helpers
# ---------------------------------------------------------------------------

def is_current_user_admin() -> bool:
    """Return ``True`` if the currently logged-in session user has admin rights."""
    username = session.get('username')
    if not username:
        return False
    conn = get_db_connection()
    user = conn.execute("SELECT is_admin FROM users WHERE username=?", (username,)).fetchone()
    conn.close()
    return bool(user and user['is_admin'])


def check_password(stored_hash, plain_password: str) -> bool:
    """Safely verify *plain_password* against *stored_hash* (bytes or memoryview)."""
    if isinstance(stored_hash, memoryview):
        stored_hash = stored_hash.tobytes()
    return bcrypt.checkpw(plain_password.encode(), stored_hash)
