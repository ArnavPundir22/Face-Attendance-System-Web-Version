# gunicorn.conf.py — BioSecure AI
#
# Gunicorn production configuration.
# Override any value via environment variable: GUNICORN_<UPPERCASED_SETTING>
#
# Usage:
#   gunicorn app:app --config gunicorn.conf.py
#
import multiprocessing
import os

# ---------------------------------------------------------------
# Server socket
# ---------------------------------------------------------------
# Render / Railway inject $PORT; fall back to 8000 for VPS/local.
bind = f"0.0.0.0:{os.environ.get('PORT', '8000')}"

# ---------------------------------------------------------------
# Workers
# ---------------------------------------------------------------
# 2 workers is safe for 2 GB RAM + CPU-only InsightFace.
# Increase to (2 * cpu_count + 1) if you have enough RAM (≥ 4 GB).
workers = int(os.environ.get("WEB_CONCURRENCY", 2))
worker_class = "sync"  # sync is fine; use gthread if you need threading

# ---------------------------------------------------------------
# Timeouts
# ---------------------------------------------------------------
# InsightFace model loading + group-photo inference can be slow.
timeout = int(os.environ.get("GUNICORN_TIMEOUT", 120))
graceful_timeout = 30
keepalive = 5

# ---------------------------------------------------------------
# Logging
# ---------------------------------------------------------------
accesslog = "-"   # stdout
errorlog = "-"    # stderr
loglevel = os.environ.get("LOG_LEVEL", "info").lower()
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)sµs'

# ---------------------------------------------------------------
# Process naming
# ---------------------------------------------------------------
proc_name = "biosecure-ai-face-attendance"

# ---------------------------------------------------------------
# Security
# ---------------------------------------------------------------
# Strip sensitive headers forwarded by Nginx.
forwarded_allow_ips = os.environ.get("FORWARDED_ALLOW_IPS", "127.0.0.1")
