"""
Centralised configuration — BioSecure AI.

All tuneable constants live here so they can be overridden via environment
variables or a .env file without touching application code.

Required environment variables (must be set):
  FLASK_SECRET_KEY          — random secret for session signing
  SUPABASE_URL              — Supabase project URL
  SUPABASE_SERVICE_ROLE_KEY — Supabase service-role key (bypasses RLS)

Optional environment variables (sensible defaults provided):
  SUPABASE_ANON_KEY         — Supabase anon/public key (for least-privilege reads)
  EMAIL_USER                — Gmail address for SMTP (leave blank to disable email)
  EMAIL_PASS                — Gmail App Password
  INSIGHTFACE_CTX_ID        — 0 = GPU, -1 = CPU (default: -1)
  FACE_MATCH_THRESHOLD      — cosine similarity threshold (default: 0.3)
  REATTENDANCE_INTERVAL_MINUTES — cooldown between re-marks (default: 10)
  LOGIN_MAX_ATTEMPTS        — failed logins before lockout (default: 5)
  LOGIN_LOCKOUT_MINUTES     — lockout duration (default: 15)
  OTP_EXPIRY_MINUTES        — OTP validity window (default: 10)
  MIN_PASSWORD_LENGTH       — minimum password length (default: 8)
  KNOWN_FACES_DIR           — path to face photo storage (default: known_faces)
  LOG_LEVEL                 — Python logging level (default: INFO)

  --- Embedding Drift Detection (Patent Idea #3) ---
  DRIFT_ALPHA               — EWMA smoothing factor 0<α<1 (default: 0.3)
  DRIFT_POSE_YAW_MAX        — max yaw angle (°) to accept for drift update (default: 25)
  DRIFT_POSE_PITCH_MAX      — max pitch angle (°) to accept for drift update (default: 20)
  DRIFT_WARN_THRESHOLD      — EWMA level that triggers WARNING alert (default: 0.15)
  DRIFT_CRITICAL_THRESHOLD  — EWMA level that triggers CRITICAL alert (default: 0.25)
  DRIFT_ALERT_THRESHOLD     — EWMA level that triggers RE-ENROLLMENT REQUIRED (default: 0.35)
"""

import logging
import os
import warnings
from pathlib import Path

from dotenv import load_dotenv

# Load .env from the project root directory (one level up from src/).
_env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(_env_path)


# -------------------------
# Paths / Directories
# -------------------------
KNOWN_FACES_DIR: str = os.environ.get("KNOWN_FACES_DIR", "known_faces")

# -------------------------
# Supabase
# -------------------------
SUPABASE_URL: str = os.environ.get("SUPABASE_URL", "")
SUPABASE_SERVICE_ROLE_KEY: str = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")
SUPABASE_ANON_KEY: str = os.environ.get("SUPABASE_ANON_KEY", "")

# -------------------------
# Face recognition
# -------------------------
FACE_MATCH_THRESHOLD: float = float(os.environ.get("FACE_MATCH_THRESHOLD", "0.3"))
REATTENDANCE_INTERVAL_MINUTES: int = int(
    os.environ.get("REATTENDANCE_INTERVAL_MINUTES", "10")
)
# InsightFace model: ctx_id=0 → GPU, ctx_id=-1 → CPU
INSIGHTFACE_CTX_ID: int = int(os.environ.get("INSIGHTFACE_CTX_ID", "-1"))

# -------------------------
# Embedding Drift Detection  (Patent Idea #3 — Pose-Gated EWMA)
# -------------------------
# EWMA smoothing factor — lower = smoother / slower to react; higher = faster
DRIFT_ALPHA: float               = float(os.environ.get("DRIFT_ALPHA", "0.3"))
# Pose gate: skip drift update when face angle exceeds these limits
DRIFT_POSE_YAW_MAX: float        = float(os.environ.get("DRIFT_POSE_YAW_MAX", "25.0"))
DRIFT_POSE_PITCH_MAX: float      = float(os.environ.get("DRIFT_POSE_PITCH_MAX", "20.0"))
# EWMA alert thresholds
DRIFT_WARN_THRESHOLD: float      = float(os.environ.get("DRIFT_WARN_THRESHOLD",     "0.15"))
DRIFT_CRITICAL_THRESHOLD: float  = float(os.environ.get("DRIFT_CRITICAL_THRESHOLD", "0.25"))
DRIFT_ALERT_THRESHOLD: float     = float(os.environ.get("DRIFT_ALERT_THRESHOLD",    "0.35"))

# -------------------------
# Email (SMTP) — optional
# -------------------------
EMAIL_USER: str = os.environ.get("EMAIL_USER", "")
EMAIL_PASS: str = os.environ.get("EMAIL_PASS", "")

if not EMAIL_USER or not EMAIL_PASS:
    warnings.warn(
        "EMAIL_USER and/or EMAIL_PASS are not set. "
        "Email-based attendance reports will be unavailable. "
        "See .env.example for setup instructions.",
        RuntimeWarning,
        stacklevel=1,
    )

# -------------------------
# Authentication / Security
# -------------------------
LOGIN_MAX_ATTEMPTS: int = int(os.environ.get("LOGIN_MAX_ATTEMPTS", "5"))
LOGIN_LOCKOUT_MINUTES: int = int(os.environ.get("LOGIN_LOCKOUT_MINUTES", "15"))
OTP_EXPIRY_MINUTES: int = int(os.environ.get("OTP_EXPIRY_MINUTES", "10"))
MIN_PASSWORD_LENGTH: int = int(os.environ.get("MIN_PASSWORD_LENGTH", "8"))
OTP_RANGE_START: int = 100_000
OTP_RANGE_SIZE: int = 900_000

# -------------------------
# Logging
# -------------------------
LOG_LEVEL: str = os.environ.get("LOG_LEVEL", "INFO").upper()
