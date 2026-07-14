"""
Authentication helper functions — BioSecure AI.

Covers:
  - In-memory login rate-limiting (account lockout per email)
  - Remaining-attempts counter

NOTE: This tracker is in-memory only and resets on server restart.
      For multi-worker / multi-process deployments, persist attempt counts
      in Redis or the database instead of this module-level dict.

OTP and password-reset flows are handled natively by Supabase Auth.
"""

from __future__ import annotations

from datetime import datetime, timedelta

import config


# ---------------------------------------------------------------------------
# Login rate-limiting
# ---------------------------------------------------------------------------

# { email: {'count': int, 'locked_until': datetime | None} }
_login_attempts: dict[str, dict] = {}


def _get_attempts(email: str) -> dict:
    return _login_attempts.setdefault(email, {"count": 0, "locked_until": None})


def is_account_locked(email: str) -> tuple[bool, int]:
    """Return ``(locked, seconds_remaining)``."""
    entry = _get_attempts(email)
    now = datetime.now()
    if entry["locked_until"] and now < entry["locked_until"]:
        remaining = int((entry["locked_until"] - now).total_seconds())
        return True, remaining
    # Reset an expired lock.
    if entry["locked_until"] and now >= entry["locked_until"]:
        entry["count"] = 0
        entry["locked_until"] = None
    return False, 0


def record_failed_login(email: str) -> None:
    """Increment the failure counter; lock the account when threshold is reached."""
    entry = _get_attempts(email)
    entry["count"] += 1
    if entry["count"] >= config.LOGIN_MAX_ATTEMPTS:
        entry["locked_until"] = datetime.now() + timedelta(
            minutes=config.LOGIN_LOCKOUT_MINUTES
        )


def clear_failed_logins(email: str) -> None:
    """Clear the failure counter on a successful login."""
    _login_attempts.pop(email, None)


def remaining_attempts(email: str) -> int:
    """Return how many more failures are allowed before lockout."""
    count = _get_attempts(email)["count"]
    return max(config.LOGIN_MAX_ATTEMPTS - count, 0)
