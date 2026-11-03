"""
BioSecure AI — Cryptographic License Verifier & Runtime Enforcement.

Implements Ed25519 asymmetric signature verification, anti-rollback protection,
boot-time enforcement, and mid-flight request middleware checks.
Strictly read-only refusal: NO file deletions, NO destructive payloads.
"""

from __future__ import annotations

import base64
from datetime import datetime, timedelta, timezone
import json
import logging
import os
from pathlib import Path
import sys
import threading
import time
from typing import Any, Dict, Optional, Tuple

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ed25519

logger = logging.getLogger(__name__)

# Default file locations
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_LICENSE_PATH = Path(os.environ.get("LICENSE_PATH", PROJECT_ROOT / ".license"))
DEFAULT_PUBLIC_KEY_PATH = Path(
    os.environ.get("LICENSE_PUBLIC_KEY_PATH", Path(__file__).resolve().parent / "license_public_key.pem")
)
DEFAULT_STATE_PATH = Path(os.environ.get("LICENSE_STATE_PATH", PROJECT_ROOT / ".license_state"))

ALLOWED_CLOCK_DRIFT_SECONDS = 300.0  # 5 minutes tolerance for NTP drift
_state_file_lock = threading.Lock()


class LicenseValidationError(Exception):
    """Raised when license token validation fails."""
    pass


def load_public_key(pub_key_path: Optional[Path | str] = None) -> ed25519.Ed25519PublicKey:
    """Load and parse Ed25519 public key from PEM file."""
    path = Path(pub_key_path) if pub_key_path else DEFAULT_PUBLIC_KEY_PATH
    if not path.is_file():
        raise LicenseValidationError(f"Public key not found at {path}")

    try:
        pub_bytes = path.read_bytes()
        key = serialization.load_pem_public_key(pub_bytes)
        if not isinstance(key, ed25519.Ed25519PublicKey):
            raise LicenseValidationError("Loaded key is not an Ed25519 public key")
        return key
    except LicenseValidationError:
        raise
    except Exception as exc:
        raise LicenseValidationError(f"Error loading public key: {exc}")


def _verify_anti_rollback(
    state_file: Path,
    now_utc: datetime,
    payload: Dict[str, Any],
) -> None:
    """
    Verify host system clock has not moved backwards beyond the allowed tolerance.
    Preserves strictly monotonic high-water mark and updates the state file atomically.
    Thread-safe across concurrent requests.
    """
    now_ts = now_utc.timestamp()
    last_seen_ts: Optional[float] = None

    with _state_file_lock:
        if state_file.is_file():
            try:
                state_data = json.loads(state_file.read_text(encoding="utf-8"))
                last_seen_ts = state_data.get("last_seen_timestamp")
                if last_seen_ts is None and "last_seen" in state_data:
                    last_seen_dt = datetime.fromisoformat(state_data["last_seen"].replace("Z", "+00:00"))
                    if last_seen_dt.tzinfo is None:
                        last_seen_dt = last_seen_dt.replace(tzinfo=timezone.utc)
                    last_seen_ts = last_seen_dt.timestamp()

                if last_seen_ts is not None:
                    drift = last_seen_ts - now_ts
                    if drift > ALLOWED_CLOCK_DRIFT_SECONDS:
                        raise LicenseValidationError(
                            f"Host clock rollback detected: current time ({now_utc.isoformat()}) "
                            f"is {drift:.1f}s behind recorded state ({last_seen_ts})"
                        )
            except LicenseValidationError:
                raise
            except Exception as exc:
                logger.warning("Could not read license state file: %s. Reinitializing state.", exc)

        # Monotonic high-water mark: never regress recorded peak timestamp
        high_water_ts = max(last_seen_ts, now_ts) if last_seen_ts is not None else now_ts

        # Atomically write state file via thread-unique temporary file and os.replace
        try:
            state_content = {
                "version": 1,
                "customer": payload.get("customer", "unknown"),
                "license_id": payload.get("license_id", "default"),
                "last_seen": datetime.fromtimestamp(high_water_ts, tz=timezone.utc).isoformat(),
                "last_seen_timestamp": high_water_ts,
                "updated_at": now_utc.isoformat(),
            }
            temp_file = state_file.with_name(
                f"{state_file.name}.tmp.{os.getpid()}.{threading.get_ident()}.{time.time_ns()}"
            )
            temp_file.write_text(json.dumps(state_content, indent=2), encoding="utf-8")
            os.replace(temp_file, state_file)
        except Exception as exc:
            logger.warning("Failed to update license state file: %s", exc)


def verify_license(
    license_path: Optional[Path | str] = None,
    public_key_path: Optional[Path | str] = None,
    state_path: Optional[Path | str] = None,
    now: Optional[datetime] = None,
    current_time: Optional[datetime] = None,
    check_anti_rollback: bool = True,
) -> Dict[str, Any]:
    """
    Verify the cryptographic signature, payload schema, expiration,
    and anti-rollback state of a license token.
    Returns the verified payload dictionary.
    Raises LicenseValidationError on any verification failure.
    """
    lic_file = Path(license_path) if license_path else DEFAULT_LICENSE_PATH
    if not lic_file.is_file():
        raise LicenseValidationError(f"License file not found at {lic_file}")

    public_key = load_public_key(public_key_path)

    # 1. Decode envelope (supports Base64 encoded JSON or raw JSON)
    try:
        raw_bytes = lic_file.read_bytes().strip()
        try:
            raw_json = base64.b64decode(raw_bytes)
            envelope = json.loads(raw_json)
        except Exception:
            envelope = json.loads(raw_bytes)
    except Exception as exc:
        raise LicenseValidationError(f"Malformed license token: cannot parse envelope ({exc})")

    if not isinstance(envelope, dict) or "payload" not in envelope or "signature" not in envelope:
        raise LicenseValidationError("Malformed license token: missing 'payload' or 'signature' in envelope")

    payload = envelope["payload"]
    if not isinstance(payload, dict):
        raise LicenseValidationError("Malformed license token: payload must be a JSON object")

    # 2. Verify Ed25519 cryptographic signature
    try:
        sig_bytes = base64.b64decode(envelope["signature"])
    except Exception as exc:
        raise LicenseValidationError(f"Malformed signature encoding: {exc}")

    canonical_payload = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    try:
        public_key.verify(sig_bytes, canonical_payload)
    except InvalidSignature:
        raise LicenseValidationError("Cryptographic signature verification failed: invalid or forged license token")
    except Exception as exc:
        raise LicenseValidationError(f"Signature verification error: {exc}")

    # 3. Expiration verification
    if "expires_at" not in payload:
        raise LicenseValidationError("Malformed license payload: missing 'expires_at'")

    try:
        expires_at_str = payload["expires_at"].replace("Z", "+00:00")
        expires_at = datetime.fromisoformat(expires_at_str)
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
    except Exception as exc:
        raise LicenseValidationError(f"Invalid timestamp in 'expires_at': {exc}")

    effective_now = current_time if current_time is not None else now
    now_utc = effective_now if effective_now is not None else datetime.now(timezone.utc)
    if now_utc.tzinfo is None:
        now_utc = now_utc.replace(tzinfo=timezone.utc)

    if now_utc > expires_at:
        raise LicenseValidationError(
            f"License expired on {expires_at.isoformat()} (current UTC time: {now_utc.isoformat()})"
        )

    # 4. Anti-Rollback verification
    if check_anti_rollback:
        state_file = Path(state_path) if state_path else DEFAULT_STATE_PATH
        _verify_anti_rollback(state_file, now_utc, payload)

    return payload


def enforce_license_boot(
    license_path: Optional[Path | str] = None,
    public_key_path: Optional[Path | str] = None,
    state_path: Optional[Path | str] = None,
    current_time: Optional[datetime] = None,
    now: Optional[datetime] = None,
) -> Dict[str, Any]:
    """
    Enforce license verification at boot time.
    Terminates immediately with sys.exit(1) on failure.
    Returns verified payload on success.
    """
    effective_now = current_time if current_time is not None else now
    try:
        payload = verify_license(
            license_path=license_path,
            public_key_path=public_key_path,
            state_path=state_path,
            now=effective_now,
            check_anti_rollback=True,
        )
        logger.info(
            "BioSecure AI license valid. Customer: '%s', License ID: '%s', Expires: '%s'",
            payload.get("customer", "N/A"),
            payload.get("license_id", "N/A"),
            payload.get("expires_at", "N/A"),
        )
        # Seed in-memory runtime cache from boot payload
        try:
            expires_at_str = payload["expires_at"].replace("Z", "+00:00")
            expires_at = datetime.fromisoformat(expires_at_str)
            if expires_at.tzinfo is None:
                expires_at = expires_at.replace(tzinfo=timezone.utc)
            _set_runtime_cached_expiry(expires_at)
        except Exception:
            pass
        return payload
    except LicenseValidationError as exc:
        logger.critical("License verification failed: %s", exc)
        print("\n" + "=" * 70, file=sys.stderr)
        print("FATAL: BIOSECURE AI APPLICATION BOOT HALTED BY LICENSE ENFORCEMENT", file=sys.stderr)
        print(f"Reason: {exc}", file=sys.stderr)
        print("Please obtain a valid '.license' token from the software vendor.", file=sys.stderr)
        print("=" * 70 + "\n", file=sys.stderr)
        sys.exit(1)
    except Exception as exc:
        logger.critical("Unexpected error during license verification: %s", exc, exc_info=True)
        print(f"FATAL: Unexpected licensing error: {exc}", file=sys.stderr)
        sys.exit(1)


# In-memory cached state for request-level middleware
_RUNTIME_CACHE: Dict[str, Any] = {
    "cached_expires_timestamp": None,
    "last_check_ts": 0.0,
    "cached_payload": None,
}
_RUNTIME_CACHE_LOCK = threading.Lock()
RUNTIME_CACHE_TTL_SECONDS = 60.0


def _set_runtime_cached_expiry(expiry: Optional[datetime | float]) -> None:
    """Helper to set or override runtime cached expiry timestamp (used by tests and boot)."""
    with _RUNTIME_CACHE_LOCK:
        if expiry is None:
            _RUNTIME_CACHE["cached_expires_timestamp"] = None
        elif isinstance(expiry, (int, float)):
            _RUNTIME_CACHE["cached_expires_timestamp"] = float(expiry)
        elif isinstance(expiry, datetime):
            exp = expiry if expiry.tzinfo is not None else expiry.replace(tzinfo=timezone.utc)
            _RUNTIME_CACHE["cached_expires_timestamp"] = exp.timestamp()
        _RUNTIME_CACHE["last_check_ts"] = time.time()


def check_license_runtime(
    license_path: Optional[Path | str] = None,
    public_key_path: Optional[Path | str] = None,
    state_path: Optional[Path | str] = None,
    current_time: Optional[datetime] = None,
    now: Optional[datetime] = None,
    ttl_seconds: float = RUNTIME_CACHE_TTL_SECONDS,
) -> Tuple[bool, Optional[str]]:
    """
    Fast in-memory cached license check for HTTP request middleware.
    Returns:
        (is_expired: bool, error_message: Optional[str])
        When expired: (True, "License Expired: ...")
        When active / valid: (False, None)
    """
    effective_now = current_time if current_time is not None else now
    now_utc = effective_now if effective_now is not None else datetime.now(timezone.utc)
    if now_utc.tzinfo is None:
        now_utc = now_utc.replace(tzinfo=timezone.utc)
    now_ts = now_utc.timestamp()

    with _RUNTIME_CACHE_LOCK:
        cached_expires_ts = _RUNTIME_CACHE["cached_expires_timestamp"]
        last_check_ts = _RUNTIME_CACHE["last_check_ts"]

        # Fast path: check cached timestamp
        if cached_expires_ts is not None:
            if now_ts > cached_expires_ts:
                return True, f"License Expired: validity ended at timestamp {cached_expires_ts}"
            # Within TTL window and not expired
            if (now_ts - last_check_ts) < ttl_seconds:
                return False, None

    # If cache is not seeded or TTL expired, re-verify with full validation
    try:
        payload = verify_license(
            license_path=license_path,
            public_key_path=public_key_path,
            state_path=state_path,
            now=now_utc,
            check_anti_rollback=True,
        )
        expires_at_str = payload["expires_at"].replace("Z", "+00:00")
        expires_at = datetime.fromisoformat(expires_at_str)
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)

        with _RUNTIME_CACHE_LOCK:
            _RUNTIME_CACHE["cached_expires_timestamp"] = expires_at.timestamp()
            _RUNTIME_CACHE["last_check_ts"] = now_ts
            _RUNTIME_CACHE["cached_payload"] = payload

        if now_ts > expires_at.timestamp():
            return True, f"License Expired on {expires_at.isoformat()}"
        return False, None
    except LicenseValidationError as exc:
        logger.error("Runtime license check failed: %s", exc)
        return True, f"License Expired or Invalid: {exc}"
    except Exception as exc:
        logger.error("Unexpected runtime license error: %s", exc)
        return True, f"License validation error: {exc}"
