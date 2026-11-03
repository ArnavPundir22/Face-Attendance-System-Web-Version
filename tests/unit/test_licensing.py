"""
Comprehensive Unit Tests for Licensing & Tamper Protection (tests/unit/test_licensing.py)

Covers:
- Offline Ed25519 asymmetric signature verification
- Expired license boot termination (sys.exit(1))
- Tampered payload & forged signature rejection (sys.exit(1))
- Corrupted signature rejection (sys.exit(1))
- Untrusted / attacker key rejection (sys.exit(1))
- Missing license & missing public key handling (sys.exit(1))
- Malformed format / envelope rejection (sys.exit(1))
- Monotonic anti-rollback clock tracking (.license_state)
- Clock jitter tolerance (<= 300s)
- Mid-flight runtime request enforcement (active vs expired)
- Complete test isolation via ephemeral in-memory Ed25519 keypairs
"""

from __future__ import annotations

import base64
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
from typing import Tuple

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ed25519
import pytest

from src.security.license_verifier import (
    verify_license,
    enforce_license_boot,
    check_license_runtime,
    LicenseValidationError,
    _verify_anti_rollback,
    _set_runtime_cached_expiry,
)


# ---------------------------------------------------------------------------
# Test Fixtures & Helpers
# ---------------------------------------------------------------------------

@pytest.fixture
def ephemeral_keypair(tmp_path: Path) -> Tuple[ed25519.Ed25519PrivateKey, Path]:
    """Generate ephemeral Ed25519 keypair and save public key to tmp_path."""
    private_key = ed25519.Ed25519PrivateKey.generate()
    public_key = private_key.public_key()
    pub_pem = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    pub_path = tmp_path / "license_public_key.pem"
    pub_path.write_bytes(pub_pem)
    return private_key, pub_path


def make_test_license_token(
    private_key: ed25519.Ed25519PrivateKey,
    customer: str = "Test University",
    issued_at: datetime | None = None,
    expires_at: datetime | None = None,
    days: int = 30,
    tamper_payload: dict | None = None,
    corrupt_signature: bool = False,
) -> str:
    """Generate a base64-encoded signed license token."""
    now_utc = issued_at or datetime.now(timezone.utc)
    if expires_at is None:
        exp_utc = now_utc + timedelta(days=days)
    else:
        exp_utc = expires_at

    payload = {
        "customer": customer,
        "license_id": "test-uuid-1234",
        "issued_at": now_utc.isoformat(),
        "expires_at": exp_utc.isoformat(),
        "version": 1,
    }

    payload_canonical = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    signature = private_key.sign(payload_canonical)

    if tamper_payload:
        payload.update(tamper_payload)

    if corrupt_signature:
        sig_bytes = bytearray(signature)
        sig_bytes[0] ^= 0xFF
        signature = bytes(sig_bytes)

    envelope = {
        "payload": payload,
        "signature": base64.b64encode(signature).decode("utf-8"),
    }
    raw_envelope = json.dumps(envelope, sort_keys=True, indent=2).encode("utf-8")
    return base64.b64encode(raw_envelope).decode("utf-8")


# ---------------------------------------------------------------------------
# Unit Test Cases (12 Required Scenarios)
# ---------------------------------------------------------------------------

def test_valid_license_offline_verification(tmp_path: Path, ephemeral_keypair):
    """Confirm a valid signed license token passes verification cleanly."""
    priv_key, pub_path = ephemeral_keypair
    token = make_test_license_token(priv_key, customer="Client A", days=10)
    lic_path = tmp_path / ".license"
    lic_path.write_text(token)

    payload = verify_license(str(lic_path), str(pub_path), state_path=str(tmp_path / ".license_state"))
    assert payload["customer"] == "Client A"
    assert payload["version"] == 1
    assert "expires_at" in payload


def test_expired_license_boot_sys_exit_1(tmp_path: Path, ephemeral_keypair):
    """Confirm expired license causes enforce_license_boot() to terminate with sys.exit(1)."""
    priv_key, pub_path = ephemeral_keypair
    now = datetime.now(timezone.utc)
    token = make_test_license_token(
        priv_key,
        issued_at=now - timedelta(days=10),
        expires_at=now - timedelta(days=2),
    )
    lic_path = tmp_path / ".license"
    lic_path.write_text(token)

    with pytest.raises(SystemExit) as exc_info:
        enforce_license_boot(
            license_path=str(lic_path),
            public_key_path=str(pub_path),
            state_path=str(tmp_path / ".license_state"),
            current_time=now,
        )
    assert exc_info.value.code == 1


def test_tampered_payload_signature_mismatch(tmp_path: Path, ephemeral_keypair):
    """Confirm tampering with payload fields causes immediate signature rejection."""
    priv_key, pub_path = ephemeral_keypair
    token = make_test_license_token(
        priv_key,
        customer="Client A",
        days=5,
        tamper_payload={"expires_at": (datetime.now(timezone.utc) + timedelta(days=365)).isoformat()},
    )
    lic_path = tmp_path / ".license"
    lic_path.write_text(token)

    with pytest.raises(SystemExit) as exc_info:
        enforce_license_boot(
            license_path=str(lic_path),
            public_key_path=str(pub_path),
            state_path=str(tmp_path / ".license_state"),
        )
    assert exc_info.value.code == 1


def test_corrupted_signature_rejection(tmp_path: Path, ephemeral_keypair):
    """Confirm corrupted signature bytes cause boot termination with sys.exit(1)."""
    priv_key, pub_path = ephemeral_keypair
    token = make_test_license_token(priv_key, corrupt_signature=True)
    lic_path = tmp_path / ".license"
    lic_path.write_text(token)

    with pytest.raises(SystemExit) as exc_info:
        enforce_license_boot(
            license_path=str(lic_path),
            public_key_path=str(pub_path),
            state_path=str(tmp_path / ".license_state"),
        )
    assert exc_info.value.code == 1


def test_untrusted_developer_key_rejection(tmp_path: Path, ephemeral_keypair):
    """Confirm signature produced by an unauthorized/attacker key is rejected."""
    _, pub_path = ephemeral_keypair
    attacker_key = ed25519.Ed25519PrivateKey.generate()
    token = make_test_license_token(attacker_key, customer="Unauthorized User")
    lic_path = tmp_path / ".license"
    lic_path.write_text(token)

    with pytest.raises(SystemExit) as exc_info:
        enforce_license_boot(
            license_path=str(lic_path),
            public_key_path=str(pub_path),
            state_path=str(tmp_path / ".license_state"),
        )
    assert exc_info.value.code == 1


def test_missing_license_file_boot_exit(tmp_path: Path, ephemeral_keypair):
    """Confirm missing .license file results in sys.exit(1)."""
    _, pub_path = ephemeral_keypair
    non_existent_license = tmp_path / "non_existent.license"

    with pytest.raises(SystemExit) as exc_info:
        enforce_license_boot(
            license_path=str(non_existent_license),
            public_key_path=str(pub_path),
            state_path=str(tmp_path / ".license_state"),
        )
    assert exc_info.value.code == 1


def test_missing_public_key_boot_exit(tmp_path: Path, ephemeral_keypair):
    """Confirm missing public key file results in sys.exit(1)."""
    priv_key, _ = ephemeral_keypair
    token = make_test_license_token(priv_key)
    lic_path = tmp_path / ".license"
    lic_path.write_text(token)
    non_existent_key = tmp_path / "missing_key.pem"

    with pytest.raises(SystemExit) as exc_info:
        enforce_license_boot(
            license_path=str(lic_path),
            public_key_path=str(non_existent_key),
            state_path=str(tmp_path / ".license_state"),
        )
    assert exc_info.value.code == 1


def test_malformed_token_format_rejection(tmp_path: Path, ephemeral_keypair):
    """Confirm invalid base64 or garbage JSON content causes sys.exit(1)."""
    _, pub_path = ephemeral_keypair
    lic_path = tmp_path / ".license"
    lic_path.write_text("NOT_VALID_BASE64_GARBAGE!@#$%^")

    with pytest.raises(SystemExit) as exc_info:
        enforce_license_boot(
            license_path=str(lic_path),
            public_key_path=str(pub_path),
            state_path=str(tmp_path / ".license_state"),
        )
    assert exc_info.value.code == 1


def test_anti_rollback_clock_backward_detected(tmp_path: Path, ephemeral_keypair):
    """Confirm moving clock backwards past allowable threshold halts boot with sys.exit(1)."""
    priv_key, pub_path = ephemeral_keypair
    state_file = tmp_path / ".license_state"
    now = datetime(2026, 11, 10, 12, 0, 0, tzinfo=timezone.utc)
    token = make_test_license_token(priv_key, issued_at=now - timedelta(days=5), expires_at=now + timedelta(days=20))
    lic_path = tmp_path / ".license"
    lic_path.write_text(token)

    # First run at T=12:00
    enforce_license_boot(
        license_path=str(lic_path),
        public_key_path=str(pub_path),
        state_path=str(state_file),
        current_time=now,
    )
    assert state_file.exists()

    # Second run at T=12:30 (forward)
    t_forward = now + timedelta(minutes=30)
    enforce_license_boot(
        license_path=str(lic_path),
        public_key_path=str(pub_path),
        state_path=str(state_file),
        current_time=t_forward,
    )

    # Third run: Clock set backwards to 11:00 (1.5 hours backwards, exceeds 300s buffer)
    t_backward = now - timedelta(hours=1)
    with pytest.raises(SystemExit) as exc_info:
        enforce_license_boot(
            license_path=str(lic_path),
            public_key_path=str(pub_path),
            state_path=str(state_file),
            current_time=t_backward,
        )
    assert exc_info.value.code == 1


def test_anti_rollback_clock_jitter_tolerance(tmp_path: Path, ephemeral_keypair):
    """Confirm minor backward clock jitter (<= 300s) is tolerated without false abort."""
    priv_key, pub_path = ephemeral_keypair
    state_file = tmp_path / ".license_state"
    now = datetime(2026, 11, 10, 12, 0, 0, tzinfo=timezone.utc)
    token = make_test_license_token(priv_key, issued_at=now - timedelta(days=1), expires_at=now + timedelta(days=10))
    lic_path = tmp_path / ".license"
    lic_path.write_text(token)

    # First run
    enforce_license_boot(
        license_path=str(lic_path),
        public_key_path=str(pub_path),
        state_path=str(state_file),
        current_time=now,
    )

    # Minor jitter backwards by 60 seconds (within 300s tolerance)
    jitter_time = now - timedelta(seconds=60)
    # Must succeed without SystemExit
    payload = enforce_license_boot(
        license_path=str(lic_path),
        public_key_path=str(pub_path),
        state_path=str(state_file),
        current_time=jitter_time,
    )
    assert payload is not None


def test_midflight_runtime_enforcement_blocks_expired():
    """Confirm check_license_runtime() blocks incoming requests with expired state."""
    now = datetime.now(timezone.utc)
    # Set cached expiry in the past
    _set_runtime_cached_expiry(now - timedelta(minutes=5))

    is_expired, error_msg = check_license_runtime(current_time=now)
    assert is_expired is True
    assert error_msg is not None
    assert "License Expired" in error_msg


def test_midflight_runtime_enforcement_allows_active():
    """Confirm check_license_runtime() allows active licenses to proceed cleanly."""
    now = datetime.now(timezone.utc)
    _set_runtime_cached_expiry(now + timedelta(days=5))

    is_expired, error_msg = check_license_runtime(current_time=now)
    assert is_expired is False
    assert error_msg is None
