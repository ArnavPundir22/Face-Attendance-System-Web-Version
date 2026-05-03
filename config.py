"""
Centralised configuration for Face Attendance System.

All tuneable constants live here so they can be overridden via environment
variables or a .env file without touching application code.
"""

import os

# -------------------------
# Paths / Files
# -------------------------
DB_FILE = os.environ.get('DB_FILE', 'database.db')

# New, safe numpy-based encoding storage (no pickle)
ENCODE_FILE_BASE   = os.environ.get('ENCODE_FILE_BASE', 'EncodeFile_Insight')
ENCODE_MATRIX_FILE = ENCODE_FILE_BASE + '.npy'        # numpy matrix, shape (N, D)
ENCODE_NAMES_FILE  = ENCODE_FILE_BASE + '_names.json' # ordered list of student names
ENCODE_FILE_LEGACY = ENCODE_FILE_BASE + '.pkl'         # legacy pickle — migrated on first load

KNOWN_FACES_DIR = os.environ.get('KNOWN_FACES_DIR', 'known_faces')

# -------------------------
# Face recognition
# -------------------------
FACE_MATCH_THRESHOLD = float(os.environ.get('FACE_MATCH_THRESHOLD', '0.4'))
REATTENDANCE_INTERVAL_MINUTES = int(os.environ.get('REATTENDANCE_INTERVAL_MINUTES', '10'))

# InsightFace model: ctx_id=0 → GPU, ctx_id=-1 → CPU
INSIGHTFACE_CTX_ID = int(os.environ.get('INSIGHTFACE_CTX_ID', '-1'))

# -------------------------
# Email (SMTP)
# -------------------------
EMAIL_USER = os.environ.get('EMAIL_USER', '')
EMAIL_PASS = os.environ.get('EMAIL_PASS', '')

# -------------------------
# Authentication / Security
# -------------------------
LOGIN_MAX_ATTEMPTS    = int(os.environ.get('LOGIN_MAX_ATTEMPTS', '5'))
LOGIN_LOCKOUT_MINUTES = int(os.environ.get('LOGIN_LOCKOUT_MINUTES', '15'))
OTP_EXPIRY_MINUTES    = int(os.environ.get('OTP_EXPIRY_MINUTES', '10'))
MIN_PASSWORD_LENGTH   = int(os.environ.get('MIN_PASSWORD_LENGTH', '8'))
OTP_RANGE_START = 100_000
OTP_RANGE_SIZE  = 900_000
