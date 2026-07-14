#!/bin/bash
# start_face_attendance.sh
#
# Starts the Face Attendance System using Gunicorn (production WSGI server).
# For development you can still do: flask run --debug
#
# Usage:
#   ./start_face_attendance.sh
#
# Environment variables (set in a .env file or export before running):
#   FLASK_SECRET_KEY      — random secret key for session signing (required in prod)
#   SUPABASE_URL          — Supabase database URL
#   SUPABASE_SERVICE_ROLE_KEY — Supabase service role API key
#   EMAIL_USER            — Gmail address for SMTP configurations
#   EMAIL_PASS            — Gmail App Password
#   INSIGHTFACE_CTX_ID    — 0 for GPU, -1 for CPU (default: -1)
#   ENCODE_FILE_BASE      — base name for encoding files (default: EncodeFile_Insight)

set -euo pipefail

# Change to the directory where this script lives.
cd "$(dirname "$0")"

# Activate virtual environment if present.
if [ -f ".venv/bin/activate" ]; then
    source .venv/bin/activate
fi

# Load .env if present (simple KEY=VALUE format, no export needed).
if [ -f ".env" ]; then
    set -o allexport
    source .env
    set +o allexport
fi

# Run with multiple workers since the system has migrated to PostgreSQL.
exec gunicorn app:app \
    --workers 2 \
    --bind 0.0.0.0:8000 \
    --timeout 120 \
    --access-logfile - \
    --error-logfile -

