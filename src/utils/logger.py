"""
Production Logging & Auditing Engine — BioSecure AI.

Features:
- Dedicated rotating log sinks:
    * logs/app.log         — General application events (INFO, 5 backups)
    * logs/error.log       — System errors & 500s (ERROR, 10 backups)
    * logs/audit.log       — Compliance & security audit trail (INFO, 10 backups)
    * logs/biometrics.log  — Biometric inference & drift telemetry (INFO, 5 backups)
- Zero external dependencies (uses standard library logging.handlers.RotatingFileHandler)
- Privacy & anti-leak sanitization filter (redacts passwords, base64 images, 512D vectors)
- Standardized audit and biometric metric helpers
"""

from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
import os
from pathlib import Path
import re
from typing import Any, Optional

from flask import has_request_context, request, session

# ---------------------------------------------------------------------------
# Sizing and Retention Constants (Strict Disk Space Protection)
# ---------------------------------------------------------------------------
MAX_BYTES: int = 10 * 1024 * 1024  # 10 MB per log file
BACKUP_COUNT_STANDARD: int = 5      # 5 rotated archives (50 MB cap)
BACKUP_COUNT_AUDIT: int = 10        # 10 rotated archives (100 MB cap)


# ---------------------------------------------------------------------------
# Privacy & Anti-Leak Sanitizer Filter
# ---------------------------------------------------------------------------
class PrivacySanitizerFilter(logging.Filter):
    """
    Sanitizes log messages to ensure sensitive data (passwords, tokens,
    raw base64 image strings, and 512-dimensional face vectors) is never
    persisted to disk.
    """

    PASSWORD_PATTERN = re.compile(
        r"""(['"]?(?:password|passwd|secret|token|access_token|refresh_token|api_key|apikey)['"]?\s*[:=]\s*)(?:(['"])(.*?)\2|([^\s'",;&]+))""",
        re.IGNORECASE,
    )
    BASE64_DATA_URI_PATTERN = re.compile(
        r'data:image/[a-zA-Z0-9.+-]+;base64,[A-Za-z0-9+/=]+',
        re.IGNORECASE,
    )
    LONG_BASE64_PATTERN = re.compile(
        r'(?<![A-Za-z0-9+/=])(?P<b64>[A-Za-z0-9+/]{60,}={0,2})(?![A-Za-z0-9+/=])'
    )
    # Match arrays/lists containing 5 or more floats/numbers (e.g. 512D embeddings in lists or numpy arrays)
    # Supports floats with trailing dot (0.), leading dot (.1), scientific notation (1e-4), and numpy ellipsis (...)
    _NUM_OR_ELLIPSIS = r'(?:-?(?:\d+\.?\d*|\.\d+)(?:e[+-]?\d+)?|\.\.\.)'
    VECTOR_PATTERN = re.compile(
        r'\[\s*(?:' + _NUM_OR_ELLIPSIS + r'(?:\s*,\s*|\s+)){5,}' + _NUM_OR_ELLIPSIS + r'\s*\]',
        re.IGNORECASE,
    )

    def filter(self, record: logging.LogRecord) -> bool:
        try:
            msg = record.getMessage()
        except Exception:
            msg = str(record.msg)
        record.msg = self.sanitize(msg)
        record.args = None

        if record.exc_info and not record.exc_text:
            try:
                import traceback
                formatted_tb = "".join(traceback.format_exception(*record.exc_info))
                record.exc_text = self.sanitize(formatted_tb)
            except Exception:
                pass
        elif record.exc_text:
            record.exc_text = self.sanitize(record.exc_text)

        return True

    @classmethod
    def _is_path_or_url(cls, candidate: str, full_text: str, start_pos: int) -> bool:
        """Heuristic check to prevent redacting valid URLs or filesystem tracebacks as base64."""
        prefix = full_text[max(0, start_pos - 10):start_pos]
        if "://" in prefix or prefix.endswith("/"):
            return True
        if candidate.count("/") >= 2 and "+" not in candidate and "=" not in candidate:
            parts = candidate.split("/")
            if all(len(p) <= 45 for p in parts if p):
                return True
        return False

    @classmethod
    def sanitize(cls, text: str) -> str:
        if not isinstance(text, str):
            return text

        # 1. Mask password / secret credentials (supporting both quoted with spaces and unquoted)
        def _redact_pwd(m: re.Match) -> str:
            prefix = m.group(1)
            quote = m.group(2)
            if quote:
                return f"{prefix}{quote}[REDACTED]{quote}"
            return f"{prefix}[REDACTED]"

        text = cls.PASSWORD_PATTERN.sub(_redact_pwd, text)

        # 2. Mask data URIs containing base64 images
        text = cls.BASE64_DATA_URI_PATTERN.sub('[REDACTED_BASE64_IMAGE]', text)

        # 3. Mask standalone long base64 strings (>= 60 characters) while preserving URLs and file paths
        def _redact_b64(m: re.Match) -> str:
            val = m.group("b64")
            if cls._is_path_or_url(val, text, m.start("b64")):
                return val
            return "[REDACTED_BASE64]"

        text = cls.LONG_BASE64_PATTERN.sub(_redact_b64, text)

        # 4. Mask high-dimensional numeric arrays (embeddings in list or numpy format)
        text = cls.VECTOR_PATTERN.sub('[REDACTED_VECTOR]', text)
        return text


# ---------------------------------------------------------------------------
# Setup Function
# ---------------------------------------------------------------------------
def setup_production_logging(
    app: Optional[Any] = None,
    log_dir: Optional[str | Path] = None,
    max_bytes: int = MAX_BYTES,
    backup_standard: int = BACKUP_COUNT_STANDARD,
    backup_audit: int = BACKUP_COUNT_AUDIT,
) -> Path:
    """
    Initialize production logging with rotating file handlers and anti-leak filters.

    Args:
        app: Optional Flask application instance.
        log_dir: Optional path override for logs directory.
        max_bytes: Maximum size in bytes before rotating.
        backup_standard: Number of backup archives to keep for standard sinks.
        backup_audit: Number of backup archives to keep for audit/error sinks.

    Returns:
        Path to the resolved logs directory.
    """
    # 1. Resolve logs directory
    if log_dir is not None:
        target_dir = Path(log_dir)
    elif app and app.config.get("LOGS_DIR"):
        target_dir = Path(app.config["LOGS_DIR"])
    elif os.environ.get("LOGS_DIR"):
        target_dir = Path(os.environ["LOGS_DIR"])
    else:
        # Default: <project_root>/logs
        target_dir = Path(__file__).resolve().parent.parent.parent / "logs"

    target_dir.mkdir(parents=True, exist_ok=True)
    if app is not None:
        app.config["LOGS_DIR"] = str(target_dir)

    sanitizer = PrivacySanitizerFilter()

    # Formatter definitions
    app_formatter = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
    )
    audit_formatter = logging.Formatter(
        "%(asctime)s | AUDIT | %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
    )
    bio_formatter = logging.Formatter(
        "%(asctime)s | BIOMETRIC | %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
    )

    root_logger = logging.getLogger()
    # Ensure root logger processes INFO events so app.log receives general events
    if root_logger.level == logging.NOTSET or root_logger.level > logging.INFO:
        root_logger.setLevel(logging.INFO)

    audit_logger = logging.getLogger("biosecure.audit")
    bio_logger = logging.getLogger("biosecure.biometrics")

    # Helper to purge existing rotating file handlers for idempotency
    def _clean_handlers(logger: logging.Logger, filename: str) -> None:
        remaining = []
        for h in logger.handlers:
            if isinstance(h, RotatingFileHandler) and Path(h.baseFilename).name == filename:
                try:
                    h.close()
                except Exception:
                    pass
            else:
                remaining.append(h)
        logger.handlers = remaining

    # 1. Root Application Logger (logs/app.log — INFO)
    _clean_handlers(root_logger, "app.log")
    app_handler = RotatingFileHandler(
        target_dir / "app.log",
        maxBytes=max_bytes,
        backupCount=backup_standard,
        encoding="utf-8",
    )
    app_handler.setLevel(logging.INFO)
    app_handler.setFormatter(app_formatter)
    app_handler.addFilter(sanitizer)
    root_logger.addHandler(app_handler)

    # 2. System Error Logger (logs/error.log — ERROR)
    _clean_handlers(root_logger, "error.log")
    err_handler = RotatingFileHandler(
        target_dir / "error.log",
        maxBytes=max_bytes,
        backupCount=backup_audit,
        encoding="utf-8",
    )
    err_handler.setLevel(logging.ERROR)
    err_handler.setFormatter(app_formatter)
    err_handler.addFilter(sanitizer)
    root_logger.addHandler(err_handler)

    # 3. Dedicated Security & Audit Logger (logs/audit.log — INFO)
    audit_logger.setLevel(logging.INFO)
    audit_logger.propagate = False
    _clean_handlers(audit_logger, "audit.log")
    audit_handler = RotatingFileHandler(
        target_dir / "audit.log",
        maxBytes=max_bytes,
        backupCount=backup_audit,
        encoding="utf-8",
    )
    audit_handler.setLevel(logging.INFO)
    audit_handler.setFormatter(audit_formatter)
    audit_handler.addFilter(sanitizer)
    audit_logger.addHandler(audit_handler)

    # 4. Dedicated Biometrics Telemetry Logger (logs/biometrics.log — INFO)
    bio_logger.setLevel(logging.INFO)
    bio_logger.propagate = False
    _clean_handlers(bio_logger, "biometrics.log")
    bio_handler = RotatingFileHandler(
        target_dir / "biometrics.log",
        maxBytes=max_bytes,
        backupCount=backup_standard,
        encoding="utf-8",
    )
    bio_handler.setLevel(logging.INFO)
    bio_handler.setFormatter(bio_formatter)
    bio_handler.addFilter(sanitizer)
    bio_logger.addHandler(bio_handler)

    return target_dir


# ---------------------------------------------------------------------------
# Structured Telemetry Helpers
# ---------------------------------------------------------------------------
def extract_client_ip(req: Optional[Any] = None) -> str:
    """
    Safely extract client IP from request, supporting reverse proxies with comma-separated chains.
    """
    if not req:
        return "127.0.0.1"
    try:
        forwarded = req.headers.get("X-Forwarded-For")
        if forwarded:
            parts = [p.strip() for p in forwarded.split(",") if p.strip()]
            if parts:
                return parts[0]
        if req.remote_addr and req.remote_addr.strip():
            return req.remote_addr.strip()
    except Exception:
        pass
    return "127.0.0.1"


def _clean_field(value: Any, default: str = "-") -> str:
    """Sanitize individual field values against log injection (CWE-117), delimiter injection, and trailing whitespace."""
    if value is None:
        return default
    # Replace carriage returns, newlines, and pipe delimiters to prevent log/field injection
    s = str(value).replace("\r", " ").replace("\n", " ").replace("|", "-").strip()
    return s if s else default


def log_audit(
    action: str,
    target: str = "-",
    status: str = "SUCCESS",
    details: str = "-",
) -> None:
    """
    Emit a structured audit log entry with client IP and authenticated actor.

    Format:
        YYYY-MM-DDTHH:MM:SS | AUDIT | IP | ACTOR | ACTION | TARGET | STATUS | DETAILS
    """
    actor = "system"
    client_ip = "internal"

    if has_request_context():
        try:
            if session and session.get("username"):
                actor = str(session.get("username"))
            elif session and session.get("user_id"):
                actor = str(session.get("user_id"))
            else:
                actor = "anonymous"
        except Exception:
            actor = "anonymous"

        client_ip = extract_client_ip(request)

    actor_clean = _clean_field(actor, default="anonymous")
    client_ip_clean = _clean_field(client_ip, default="127.0.0.1")
    action_clean = _clean_field(action, default="-")
    target_clean = _clean_field(target, default="-")
    status_clean = _clean_field(status, default="SUCCESS")
    details_clean = PrivacySanitizerFilter.sanitize(_clean_field(details, default="-"))

    audit_logger = logging.getLogger("biosecure.audit")
    audit_logger.info(
        f"{client_ip_clean} | {actor_clean} | {action_clean} | {target_clean} | {status_clean} | {details_clean}"
    )


def _safe_int(val: Any, default: int = 0) -> int:
    try:
        return int(val)
    except (ValueError, TypeError):
        return default


def _safe_float(val: Any, default: float = 0.0) -> float:
    try:
        f = float(val)
        import math
        return default if math.isnan(f) or math.isinf(f) else max(0.0, f)
    except (ValueError, TypeError):
        return default


def log_biometric(
    images: int,
    detected: int,
    matched: int,
    unknown: int,
    latency_ms: float,
    lecture: str = "-",
) -> None:
    """
    Emit a structured biometric inference and matching metric entry.

    Format:
        YYYY-MM-DDTHH:MM:SS | BIOMETRIC | images=X detected=Y matched=Z unknown=W latency_ms=L lecture='LEC'
    """
    lecture_clean = _clean_field(lecture, default="-").replace("'", "")
    bio_logger = logging.getLogger("biosecure.biometrics")
    bio_logger.info(
        f"images={_safe_int(images)} detected={_safe_int(detected)} matched={_safe_int(matched)} "
        f"unknown={_safe_int(unknown)} latency_ms={_safe_float(latency_ms):.1f} lecture='{lecture_clean}'"
    )
