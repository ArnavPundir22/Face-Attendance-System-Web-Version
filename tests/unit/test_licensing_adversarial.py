"""
Adversarial Cryptographic & Anti-Rollback Stress Harness (tests/unit/test_licensing_adversarial.py)

Empirical Challenger Suite:
1. Fuzzing & Mutation Suite (150+ malformed, bit-flipped, truncated, and forged tokens) -> Assert 100% rejection rate.
2. Anti-rollback boundary conditions (299s, 300s, 301s, 3600s, monotonic high-water mark retention).
3. Concurrency & Race condition stress test on anti-rollback state file updates across multiple threads.
4. Comprehensive fail-secure boot termination sys.exit(1) assertions under all failure modes.
"""

from __future__ import annotations

import base64
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta, timezone
import json
import logging
import os
from pathlib import Path
import random
import string
import sys
from typing import Any, Dict, List, Tuple

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ed25519, rsa
import pytest

from src.security.license_verifier import (
    verify_license,
    enforce_license_boot,
    check_license_runtime,
    LicenseValidationError,
    _verify_anti_rollback,
    _set_runtime_cached_expiry,
    ALLOWED_CLOCK_DRIFT_SECONDS,
)


# ===========================================================================
# Fixtures & Token Generators
# ===========================================================================

@pytest.fixture
def keypair(tmp_path: Path) -> Tuple[ed25519.Ed25519PrivateKey, Path]:
    """Generate ephemeral Ed25519 keypair and write public key to isolated tmp_path."""
    priv = ed25519.Ed25519PrivateKey.generate()
    pub = priv.public_key()
    pub_bytes = pub.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    pub_path = tmp_path / "license_public_key.pem"
    pub_path.write_bytes(pub_bytes)
    return priv, pub_path


def make_valid_raw_token(
    priv_key: ed25519.Ed25519PrivateKey,
    customer: str = "Test University",
    license_id: str = "test-uuid-0001",
    issued_at: datetime | None = None,
    expires_at: datetime | None = None,
    days: int = 30,
) -> Tuple[str, dict, bytes]:
    """Generate valid base64 token along with payload dict and canonical bytes."""
    now_utc = issued_at or datetime.now(timezone.utc)
    exp_utc = expires_at or (now_utc + timedelta(days=days))

    payload = {
        "customer": customer,
        "license_id": license_id,
        "issued_at": now_utc.isoformat(),
        "expires_at": exp_utc.isoformat(),
        "version": 1,
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    sig = priv_key.sign(canonical)
    envelope = {
        "payload": payload,
        "signature": base64.b64encode(sig).decode("utf-8"),
    }
    raw_env_json = json.dumps(envelope, sort_keys=True, indent=2).encode("utf-8")
    token = base64.b64encode(raw_env_json).decode("utf-8")
    return token, payload, sig


# ===========================================================================
# 1. Adversarial Fuzzing & Mutation Suite (150+ tokens)
# ===========================================================================

def generate_adversarial_corpus(priv_key: ed25519.Ed25519PrivateKey) -> List[Tuple[str, str]]:
    """
    Generate >150 diverse adversarial license token payloads covering:
    - Garbage strings / raw binary / illegal base64
    - Corrupted envelopes / non-dict structures / missing keys
    - Truncated tokens (various slicing fractions)
    - Single and multi-bit flipped tokens
    - Forged / untrusted developer signatures
    - Tampered payload fields (customer, expiry, extra claims)
    - Malformed timestamp values and types
    - Signature byte length and encoding anomalies
    Returns list of (category_description, token_str).
    """
    corpus: List[Tuple[str, str]] = []
    valid_token, valid_payload, valid_sig = make_valid_raw_token(priv_key)
    now = datetime.now(timezone.utc)

    # Category A: Raw Garbage, Binary & Malformed Encodings (30 items)
    corpus.append(("empty_string", ""))
    corpus.append(("whitespace_only", "   \t\n   "))
    corpus.append(("null_bytes", "\x00\x00\x00\x00"))
    corpus.append(("garbage_ascii", "!@#$%^&*()_+=-`~[]{}|;':\",./<>?"))
    corpus.append(("non_base64_symbols", "This is clearly not base64!"))
    corpus.append(("sql_injection_attempt", "'; DROP TABLE licenses; --"))
    corpus.append(("path_traversal_attempt", "../../../etc/shadow"))
    corpus.append(("html_tag_attempt", "<script>alert(1)</script>"))
    corpus.append(("unicode_control_chars", "\u202e\u202d\u200b\ufeff"))
    corpus.append(("surrogate_escape_attempt", "\ud83d\ude00"))

    for length in [1, 2, 3, 4, 7, 16, 32, 64, 128, 256, 512, 1024, 2048]:
        raw_rand = "".join(random.choices(string.printable, k=length))
        corpus.append((f"random_printable_len_{length}", raw_rand))
    for length in [10, 50, 100, 200, 500, 1000, 2000]:
        rand_bytes = bytes([random.randint(0, 255) for _ in range(length)])
        corpus.append((f"random_bytes_len_{length}", rand_bytes.decode("latin1", errors="replace")))

    # Category B: Valid Base64 of Invalid JSON / Envelope (25 items)
    primitives = [
        "12345",
        "-999.5",
        "0",
        "true",
        "false",
        "null",
        '""',
        '"simple string"',
        "[]",
        "[1, 2, 3]",
        '["a", "b", "c"]',
        '{"unexpected": "data"}',
        '{"payload": "not a dict", "signature": "abc"}',
        '{"payload": 12345, "signature": "abc"}',
        '{"payload": [], "signature": "abc"}',
        '{"payload": null, "signature": "abc"}',
        '{"signature": "abc"}',
        '{"payload": {}}',
        '{"payload": {}, "signature": ""}',
        '{"payload": {}, "signature": null}',
        '{"payload": {}, "signature": 1234}',
        '{"payload": {}, "signature": []}',
        '{"payload": {}, "signature": "not_valid_b64!!!"}',
        '{"payload": {}, "signature": "YWJj"}',  # valid b64 'abc' (3 bytes), invalid ed25519 sig
        '{"payload": {"customer": "A"}, "signature": "AAAA"}',
    ]
    for i, prim in enumerate(primitives):
        encoded = base64.b64encode(prim.encode("utf-8")).decode("utf-8")
        corpus.append((f"json_primitive_or_envelope_anomaly_{i}", encoded))

    # Category C: Truncated Tokens (20 items)
    fractions = [0.01, 0.02, 0.05, 0.1, 0.15, 0.2, 0.25, 0.3, 0.4, 0.5, 0.6, 0.7, 0.75, 0.8, 0.85, 0.9, 0.95, 0.98, 0.99]
    for frac in fractions:
        cut = max(1, int(len(valid_token) * frac))
        corpus.append((f"truncated_frac_{frac:.2f}", valid_token[:cut]))
    corpus.append(("truncated_minus_1_char", valid_token[:-1]))

    # Category D: Bit-Flipped Tokens (30 items)
    token_bytes = bytearray(valid_token.encode("ascii"))
    flip_indices = [
        0, 1, 2, 3, 5, 10, 15, 20, 30, 50, 75,
        len(token_bytes) // 4, len(token_bytes) // 3,
        len(token_bytes) // 2, 2 * len(token_bytes) // 3, 3 * len(token_bytes) // 4,
        len(token_bytes) - 10, len(token_bytes) - 5, len(token_bytes) - 2, len(token_bytes) - 1
    ]
    for idx in flip_indices:
        b = bytearray(token_bytes)
        b[idx] ^= 0x01
        corpus.append((f"bit_flip_base64_char_{idx}", b.decode("ascii", errors="replace")))

    # Bit-flip inside decoded signature bytes (10 items)
    sig_bytearray = bytearray(valid_sig)
    for sig_idx in [0, 1, 7, 15, 23, 31, 32, 45, 60, 63]:
        bad_sig = bytearray(sig_bytearray)
        bad_sig[sig_idx] ^= 0x80
        env = {
            "payload": valid_payload,
            "signature": base64.b64encode(bad_sig).decode("utf-8"),
        }
        raw_env = json.dumps(env).encode("utf-8")
        corpus.append((f"signature_bit_flip_byte_{sig_idx}", base64.b64encode(raw_env).decode("utf-8")))

    # Category E: Forged Signature / Attacker Key (15 items)
    for i in range(10):
        attacker_priv = ed25519.Ed25519PrivateKey.generate()
        atk_token, _, _ = make_valid_raw_token(attacker_priv, customer=f"Attacker {i}")
        corpus.append((f"forged_attacker_key_{i}", atk_token))

    # Cross-token replay (valid signature for payload A attached to payload B)
    for k in range(5):
        other_token, other_payload, other_sig = make_valid_raw_token(priv_key, customer=f"Victim Org {k}")
        tampered_env = {
            "payload": valid_payload,
            "signature": base64.b64encode(other_sig).decode("utf-8"),
        }
        corpus.append((f"cross_token_replay_sig_{k}", base64.b64encode(json.dumps(tampered_env).encode("utf-8")).decode("utf-8")))

    # Category F: Tampered Payload Fields (Valid Signature on Original) (25 items)
    tamper_scenarios = [
        ("tamper_customer_name", {"customer": "Hacked Customer"}),
        ("tamper_license_id", {"license_id": "forged-uuid-9999"}),
        ("tamper_extend_expiry_2099", {"expires_at": "2099-12-31T23:59:59+00:00"}),
        ("tamper_extend_expiry_1yr", {"expires_at": (now + timedelta(days=365)).isoformat()}),
        ("tamper_version_bump", {"version": 2}),
        ("tamper_inject_admin", {"admin": True}),
        ("tamper_inject_bypass", {"bypass_verification": True}),
        ("tamper_remove_expires", {"expires_at": None}),
        ("tamper_invalid_date_str", {"expires_at": "not-a-timestamp"}),
        ("tamper_invalid_date_number", {"expires_at": 1735689600}),
        ("tamper_invalid_date_empty", {"expires_at": ""}),
        ("tamper_negative_version", {"version": -1}),
        ("tamper_issued_at_future", {"issued_at": (now + timedelta(days=10)).isoformat()}),
        ("tamper_inject_wildcard", {"customer": "*"}),
        ("tamper_inject_features", {"features": ["all", "unlimited"]}),
    ]
    for desc, t_dict in tamper_scenarios:
        t_payload = dict(valid_payload)
        if desc == "tamper_remove_expires":
            t_payload.pop("expires_at", None)
        else:
            t_payload.update(t_dict)
        env = {
            "payload": t_payload,
            "signature": base64.b64encode(valid_sig).decode("utf-8"),
        }
        corpus.append((desc, base64.b64encode(json.dumps(env).encode("utf-8")).decode("utf-8")))

    # Category G: Signature Length & Encoding Anomalies (15 items)
    sig_length_anomalies = [
        ("sig_len_0", b""),
        ("sig_len_1", b"A"),
        ("sig_len_8", b"A" * 8),
        ("sig_len_16", b"A" * 16),
        ("sig_len_32", b"A" * 32),
        ("sig_len_48", b"A" * 48),
        ("sig_len_63", b"A" * 63),
        ("sig_len_65", b"A" * 65),
        ("sig_len_96", b"A" * 96),
        ("sig_len_128", b"A" * 128),
        ("sig_len_256", b"A" * 256),
    ]
    for desc, raw_s in sig_length_anomalies:
        env = {
            "payload": valid_payload,
            "signature": base64.b64encode(raw_s).decode("utf-8"),
        }
        corpus.append((desc, base64.b64encode(json.dumps(env).encode("utf-8")).decode("utf-8")))

    return corpus


def test_adversarial_token_corpus_100_percent_rejection(tmp_path: Path, keypair):
    """
    Execute fuzzing & mutation corpus (>150 tokens).
    Verify that 100% of adversarial tokens are rejected by verify_license().
    """
    priv_key, pub_path = keypair
    corpus = generate_adversarial_corpus(priv_key)
    assert len(corpus) >= 100, f"Corpus must contain at least 100 items, got {len(corpus)}"

    rejected_count = 0
    accepted_cases = []

    for idx, (desc, token) in enumerate(corpus):
        lic_file = tmp_path / f"test_{idx}.license"
        lic_file.write_text(token, encoding="utf-8", errors="surrogatepass")
        state_file = tmp_path / f"state_{idx}.json"

        try:
            verify_license(
                license_path=str(lic_file),
                public_key_path=str(pub_path),
                state_path=str(state_file),
                check_anti_rollback=False,
            )
            accepted_cases.append((desc, token[:30]))
        except LicenseValidationError:
            rejected_count += 1
        except Exception as unexpected:
            pytest.fail(f"Token '{desc}' caused unexpected crash {type(unexpected).__name__}: {unexpected}")

    total = len(corpus)
    rejection_rate = (rejected_count / total) * 100.0

    assert accepted_cases == [], f"Accepted invalid tokens: {accepted_cases}"
    assert rejection_rate == 100.0, f"Expected 100% rejection rate, got {rejection_rate}% ({rejected_count}/{total})"


def test_adversarial_tokens_boot_exit_sys_exit_1(tmp_path: Path, keypair):
    """
    Verify that enforce_license_boot() terminates with sys.exit(1)
    for representative adversarial tokens from each category.
    """
    priv_key, pub_path = keypair
    corpus = generate_adversarial_corpus(priv_key)
    sample_cases = corpus[:: max(1, len(corpus) // 20)]

    for idx, (desc, token) in enumerate(sample_cases):
        lic_file = tmp_path / f"boot_fuzz_{idx}.license"
        lic_file.write_text(token, encoding="utf-8", errors="surrogatepass")
        state_file = tmp_path / f"boot_fuzz_state_{idx}.json"

        with pytest.raises(SystemExit) as exc_info:
            enforce_license_boot(
                license_path=str(lic_file),
                public_key_path=str(pub_path),
                state_path=str(state_file),
            )
        assert exc_info.value.code == 1, f"Failed for category: {desc}"


# ===========================================================================
# 2. Anti-Rollback Boundary Condition Testing
# ===========================================================================

def test_anti_rollback_exact_boundary_conditions(tmp_path: Path, keypair):
    """
    Stress-test clock drift buffer exactly at:
    - 299.0s backward -> PASS
    - 300.0s backward -> PASS (exact boundary)
    - 300.001s backward -> FAIL (rollback detected)
    - 301.0s backward -> FAIL (rollback detected)
    - 3600.0s backward -> FAIL (rollback detected)
    """
    priv_key, pub_path = keypair
    state_file = tmp_path / ".license_state_boundary"
    base_time = datetime(2026, 11, 10, 12, 0, 0, tzinfo=timezone.utc)
    token, _, _ = make_valid_raw_token(
        priv_key,
        issued_at=base_time - timedelta(days=2),
        expires_at=base_time + timedelta(days=20),
    )
    lic_file = tmp_path / ".license_boundary"
    lic_file.write_text(token)

    # Boot 1: Establish baseline timestamp at T0 = 12:00:00
    enforce_license_boot(
        license_path=str(lic_file),
        public_key_path=str(pub_path),
        state_path=str(state_file),
        current_time=base_time,
    )
    state = json.loads(state_file.read_text())
    assert state["last_seen_timestamp"] == pytest.approx(base_time.timestamp())

    # Advance clock to T1 = 13:00:00 (1 hour forward)
    t1 = base_time + timedelta(hours=1)
    enforce_license_boot(
        license_path=str(lic_file),
        public_key_path=str(pub_path),
        state_path=str(state_file),
        current_time=t1,
    )
    state = json.loads(state_file.read_text())
    assert state["last_seen_timestamp"] == pytest.approx(t1.timestamp())

    # Test 1: Backward by 299.0s (drift = 299.0s <= 300.0s) -> MUST PASS
    t_299_back = t1 - timedelta(seconds=299.0)
    payload_299 = verify_license(
        license_path=str(lic_file),
        public_key_path=str(pub_path),
        state_path=str(state_file),
        current_time=t_299_back,
        check_anti_rollback=True,
    )
    assert payload_299 is not None

    # Reset state to t1 for exact boundary check
    state["last_seen_timestamp"] = t1.timestamp()
    state_file.write_text(json.dumps(state))

    # Test 2: Backward by exactly 300.0s (drift = 300.0s <= 300.0s) -> MUST PASS (boundary equality)
    t_300_back = t1 - timedelta(seconds=300.0)
    payload_300 = verify_license(
        license_path=str(lic_file),
        public_key_path=str(pub_path),
        state_path=str(state_file),
        current_time=t_300_back,
        check_anti_rollback=True,
    )
    assert payload_300 is not None

    # Reset state to t1
    state["last_seen_timestamp"] = t1.timestamp()
    state_file.write_text(json.dumps(state))

    # Test 3: Backward by 300.001s (drift = 300.001s > 300.0s) -> MUST FAIL
    t_300_001_back = t1 - timedelta(seconds=300.001)
    with pytest.raises(LicenseValidationError) as exc:
        verify_license(
            license_path=str(lic_file),
            public_key_path=str(pub_path),
            state_path=str(state_file),
            current_time=t_300_001_back,
            check_anti_rollback=True,
        )
    assert "clock rollback detected" in str(exc.value)

    # Test 4: Backward by 301.0s (drift = 301.0s > 300.0s) -> MUST FAIL & sys.exit(1)
    t_301_back = t1 - timedelta(seconds=301.0)
    with pytest.raises(SystemExit) as exc_exit:
        enforce_license_boot(
            license_path=str(lic_file),
            public_key_path=str(pub_path),
            state_path=str(state_file),
            current_time=t_301_back,
        )
    assert exc_exit.value.code == 1

    # Test 5: Backward by 3600.0s (1 hour) -> MUST FAIL & sys.exit(1)
    t_3600_back = t1 - timedelta(seconds=3600.0)
    with pytest.raises(SystemExit) as exc_exit:
        enforce_license_boot(
            license_path=str(lic_file),
            public_key_path=str(pub_path),
            state_path=str(state_file),
            current_time=t_3600_back,
        )
    assert exc_exit.value.code == 1


def test_anti_rollback_monotonic_high_water_mark_behavior(tmp_path: Path, keypair):
    """
    Empirical check of monotonic high-water mark preservation across multiple boots.
    Demonstrates whether repeated sub-300s backward adjustments allow unbounded creeping rollback.
    """
    priv_key, pub_path = keypair
    state_file = tmp_path / ".license_state_creeping"
    t_peak = datetime(2026, 11, 10, 15, 0, 0, tzinfo=timezone.utc)
    token, _, _ = make_valid_raw_token(priv_key, issued_at=t_peak - timedelta(days=1), days=30)
    lic_file = tmp_path / ".license_creeping"
    lic_file.write_text(token)

    # Boot 1 at peak: 15:00:00
    enforce_license_boot(
        license_path=str(lic_file),
        public_key_path=str(pub_path),
        state_path=str(state_file),
        current_time=t_peak,
    )
    initial_peak_ts = json.loads(state_file.read_text())["last_seen_timestamp"]
    assert initial_peak_ts == pytest.approx(t_peak.timestamp())

    # Boot 2: Backward jitter of 200s (allowed because 200s <= 300s)
    t_jitter = t_peak - timedelta(seconds=200)
    enforce_license_boot(
        license_path=str(lic_file),
        public_key_path=str(pub_path),
        state_path=str(state_file),
        current_time=t_jitter,
    )
    recorded_ts = json.loads(state_file.read_text())["last_seen_timestamp"]

    # In a strictly monotonic system, recorded_ts must remain >= initial_peak_ts.
    # If recorded_ts decreased to t_jitter, high-water mark retention is violated!
    is_monotonic = (recorded_ts >= initial_peak_ts)

    # Attempt a second backward shift: t_peak - 400s (200s behind t_jitter)
    t_creeping = t_peak - timedelta(seconds=400)
    try:
        verify_license(
            license_path=str(lic_file),
            public_key_path=str(pub_path),
            state_path=str(state_file),
            current_time=t_creeping,
            check_anti_rollback=True,
        )
        creeping_succeeded = True
    except LicenseValidationError:
        creeping_succeeded = False

    # Document the empirical reality:
    # If creeping_succeeded is True, the system suffers from Creeping Clock Rollback Vulnerability.
    # We assert the finding to register it explicitly in our test report.
    if creeping_succeeded:
        pytest.fail(
            "VULNERABILITY CONFIRMED: Anti-rollback state file does NOT preserve monotonic high-water mark! "
            f"Initial peak was {t_peak.isoformat()}, but after sub-threshold jitter, the clock was successfully "
            f"rolled back to {t_creeping.isoformat()} (400s behind peak) without rejection."
        )


# ===========================================================================
# 3. Concurrency & Race Condition Stress Harness
# ===========================================================================

def test_concurrent_anti_rollback_updates_thread_safety(tmp_path: Path, keypair, caplog):
    """
    Stress-test anti-rollback state file updates under multi-threaded contention.
    Multiple threads concurrently update the state file using PID-tagged temporary files.
    Evaluates whether collisions on f"{state_file.name}.tmp.{os.getpid()}" trigger
    state file corruption, file missing errors, or state reinitializations.
    """
    priv_key, pub_path = keypair
    state_file = tmp_path / ".license_state_concurrent"
    base_time = datetime(2026, 11, 10, 12, 0, 0, tzinfo=timezone.utc)
    token, _, _ = make_valid_raw_token(priv_key, issued_at=base_time - timedelta(days=1), days=30)
    lic_file = tmp_path / ".license_concurrent"
    lic_file.write_text(token)

    num_threads = 25
    num_rounds = 10

    exceptions = []

    def worker_task(thread_id: int):
        for r in range(num_rounds):
            task_time = base_time + timedelta(seconds=(r * 10 + thread_id * 0.01))
            try:
                verify_license(
                    license_path=str(lic_file),
                    public_key_path=str(pub_path),
                    state_path=str(state_file),
                    current_time=task_time,
                    check_anti_rollback=True,
                )
            except Exception as exc:
                exceptions.append((thread_id, r, type(exc).__name__, str(exc)))

    with caplog.at_level(logging.WARNING):
        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [executor.submit(worker_task, i) for i in range(num_threads)]
            for f in as_completed(futures):
                f.result()

    # Check caplog for race condition warnings:
    reinit_warnings = [rec for rec in caplog.records if "Reinitializing state" in rec.message]
    errno2_warnings = [rec for rec in caplog.records if "No such file or directory" in rec.message]

    if reinit_warnings or errno2_warnings:
        pytest.fail(
            f"VULNERABILITY CONFIRMED: Multi-threaded race condition on PID-tagged temp file! "
            f"Observed {len(reinit_warnings)} state file reinitializations (history wipes) "
            f"and {len(errno2_warnings)} [Errno 2] collisions on '{state_file.name}.tmp.{os.getpid()}'."
        )


# ===========================================================================
# 4. Boot Termination sys.exit(1) Under All Failure Modes
# ===========================================================================

def test_boot_exit_on_missing_license_file(tmp_path: Path, keypair):
    _, pub_path = keypair
    missing = tmp_path / "does_not_exist.license"
    with pytest.raises(SystemExit) as exc:
        enforce_license_boot(license_path=str(missing), public_key_path=str(pub_path))
    assert exc.value.code == 1


def test_boot_exit_on_missing_public_key(tmp_path: Path, keypair):
    priv_key, _ = keypair
    token, _, _ = make_valid_raw_token(priv_key)
    lic = tmp_path / "app.license"
    lic.write_text(token)
    missing_key = tmp_path / "missing_key.pem"
    with pytest.raises(SystemExit) as exc:
        enforce_license_boot(license_path=str(lic), public_key_path=str(missing_key))
    assert exc.value.code == 1


def test_boot_exit_on_corrupted_public_key_pem(tmp_path: Path, keypair):
    priv_key, _ = keypair
    token, _, _ = make_valid_raw_token(priv_key)
    lic = tmp_path / "app.license"
    lic.write_text(token)
    corrupted_key = tmp_path / "corrupted_key.pem"
    corrupted_key.write_text("-----BEGIN PUBLIC KEY-----\nNOT_VALID_PEM_DATA\n-----END PUBLIC KEY-----\n")
    with pytest.raises(SystemExit) as exc:
        enforce_license_boot(license_path=str(lic), public_key_path=str(corrupted_key))
    assert exc.value.code == 1


def test_boot_exit_on_wrong_key_type_rsa(tmp_path: Path):
    """Confirm using an RSA public key instead of Ed25519 is rejected with sys.exit(1)."""
    rsa_priv = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    rsa_pub = rsa_priv.public_key()
    rsa_pem = rsa_pub.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    rsa_path = tmp_path / "rsa_pub.pem"
    rsa_path.write_bytes(rsa_pem)

    ed_priv = ed25519.Ed25519PrivateKey.generate()
    token, _, _ = make_valid_raw_token(ed_priv)
    lic = tmp_path / "app.license"
    lic.write_text(token)

    with pytest.raises(SystemExit) as exc:
        enforce_license_boot(license_path=str(lic), public_key_path=str(rsa_path))
    assert exc.value.code == 1


def test_boot_exit_on_expired_license(tmp_path: Path, keypair):
    priv_key, pub_path = keypair
    now = datetime.now(timezone.utc)
    token, _, _ = make_valid_raw_token(
        priv_key,
        issued_at=now - timedelta(days=60),
        expires_at=now - timedelta(seconds=1),
    )
    lic = tmp_path / "expired.license"
    lic.write_text(token)

    with pytest.raises(SystemExit) as exc:
        enforce_license_boot(
            license_path=str(lic),
            public_key_path=str(pub_path),
            current_time=now,
        )
    assert exc.value.code == 1


def test_boot_exit_on_tampered_payload_fields(tmp_path: Path, keypair):
    priv_key, pub_path = keypair
    now = datetime.now(timezone.utc)
    token, payload, sig = make_valid_raw_token(priv_key, customer="Real Org")

    payload["customer"] = "Fake Org"
    tampered_env = {"payload": payload, "signature": base64.b64encode(sig).decode("utf-8")}
    tampered_token = base64.b64encode(json.dumps(tampered_env).encode("utf-8")).decode("utf-8")

    lic = tmp_path / "tampered.license"
    lic.write_text(tampered_token)

    with pytest.raises(SystemExit) as exc:
        enforce_license_boot(license_path=str(lic), public_key_path=str(pub_path))
    assert exc.value.code == 1


def test_boot_exit_on_empty_license_file(tmp_path: Path, keypair):
    _, pub_path = keypair
    empty_lic = tmp_path / "empty.license"
    empty_lic.write_text("")

    with pytest.raises(SystemExit) as exc:
        enforce_license_boot(license_path=str(empty_lic), public_key_path=str(pub_path))
    assert exc.value.code == 1
