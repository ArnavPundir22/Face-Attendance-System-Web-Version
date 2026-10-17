#!/bin/bash
# start_face_attendance.sh
#
# Starts the BioSecure AI Face Attendance System with Nginx Load Balancer
# and Gunicorn production WSGI server.
#
# Usage:
#   ./start_face_attendance.sh
#
# Environment variables (set in a .env file or export before running):
#   FLASK_SECRET_KEY          — random secret key for session signing (required)
#   SUPABASE_URL              — Supabase database URL
#   SUPABASE_SERVICE_ROLE_KEY — Supabase service role API key
#   NGINX_PORT                — Frontend port for Nginx (default: 80 or 8080)
#   GUNICORN_PORT             — Internal port for Gunicorn (default: 8000)
#   NGINX_UPSTREAM_SERVERS    — Comma-separated backends for load balancing

set -euo pipefail

# Change to the directory where this script lives.
PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$PROJECT_DIR"

# 1. Activate virtual environment if present.
if [ -f ".venv/bin/activate" ]; then
    source .venv/bin/activate
fi

# 2. Load .env if present (simple KEY=VALUE format).
if [ -f ".env" ]; then
    set -o allexport
    source .env
    set +o allexport
fi

PYTHON_CMD="python3"
if [ -f ".venv/bin/python" ]; then
    PYTHON_CMD=".venv/bin/python"
fi

# 3. Generate dynamic Nginx configuration
NGINX_PID_FILE="$PROJECT_DIR/nginx/logs/nginx.pid"
CONFIG_FILE="$PROJECT_DIR/nginx/nginx-runtime.conf"

eval "$($PYTHON_CMD "$PROJECT_DIR/nginx/setup_nginx.py" --os Linux)"

# Fallback values if not set
NGINX_PORT="${NGINX_PORT:-8080}"
BACKEND_PORT="${BACKEND_PORT:-8000}"

# 4. Check if Nginx is installed. If not, offer automatic installation.
NGINX_AVAILABLE=0
if command -v nginx >/dev/null 2>&1; then
    NGINX_AVAILABLE=1
else
    echo "=========================================================="
    echo "⚠️  Nginx is not installed on this system."
    echo "Attempting automatic installation via apt (may ask for sudo password)..."
    echo "=========================================================="
    if command -v sudo >/dev/null 2>&1 && sudo -v 2>/dev/null; then
        if sudo apt-get update && sudo apt-get install -y nginx; then
            echo "✅ Nginx installed successfully."
            NGINX_AVAILABLE=1
        else
            echo "⚠️  Automatic Nginx installation failed. Proceeding without Nginx..."
        fi
    elif command -v sudo >/dev/null 2>&1; then
        echo "Please authenticate with sudo to install Nginx:"
        if sudo apt-get update && sudo apt-get install -y nginx; then
            echo "✅ Nginx installed successfully."
            NGINX_AVAILABLE=1
        else
            echo "⚠️  Could not install Nginx. Proceeding without Nginx..."
        fi
    else
        echo "⚠️  Sudo not available. Proceeding without Nginx..."
    fi
fi

# 5. Launch Nginx if available
if [ "$NGINX_AVAILABLE" -eq 1 ]; then
    echo "Testing Nginx configuration ($CONFIG_FILE)..."
    if nginx -t -c "$CONFIG_FILE" >/dev/null 2>&1; then
        # Stop any lingering previous instances
        if [ -f "$NGINX_PID_FILE" ]; then
            OLD_PID=$(cat "$NGINX_PID_FILE" 2>/dev/null || true)
            if [ -n "$OLD_PID" ] && kill -0 "$OLD_PID" 2>/dev/null; then
                kill -9 "$OLD_PID" 2>/dev/null || true
            fi
            rm -f "$NGINX_PID_FILE"
        fi

        # Start Nginx in background
        nginx -c "$CONFIG_FILE"
        echo "✅ Nginx Load Balancer started successfully on port ${NGINX_PORT}."

        # Setup cleanup trap to kill Nginx on exit
        cleanup() {
            echo ""
            echo "Shutting down Nginx Load Balancer..."
            if [ -f "$NGINX_PID_FILE" ]; then
                NGINX_PID=$(cat "$NGINX_PID_FILE" 2>/dev/null || true)
                if [ -n "$NGINX_PID" ] && kill -0 "$NGINX_PID" 2>/dev/null; then
                    kill "$NGINX_PID" 2>/dev/null || true
                fi
            fi
            nginx -c "$CONFIG_FILE" -s quit 2>/dev/null || true
            echo "BioSecure AI stopped."
        }
        trap cleanup EXIT INT TERM

        echo "=========================================================="
        echo "🚀 BioSecure AI is LIVE!"
        echo "🌐 Public / Frontend URL: http://localhost:${NGINX_PORT}"
        echo "⚙️ Backend WSGI Server:   http://127.0.0.1:${BACKEND_PORT}"
        echo "⚖️ Load Balancing Policy: Least Connections (least_conn)"
        echo "=========================================================="

        # Run Gunicorn bound to localhost (without exec so the cleanup trap executes on exit)
        gunicorn wsgi:app \
            --workers 2 \
            --bind "127.0.0.1:${BACKEND_PORT}" \
            --timeout "${GUNICORN_TIMEOUT:-300}" \
            --access-logfile - \
            --error-logfile -
        exit 0
    else
        echo "⚠️  Nginx configuration test failed. Falling back to Gunicorn directly..."
    fi
fi

# Fallback: Run Gunicorn directly on 0.0.0.0:8000 so the app never breaks
echo "=========================================================="
echo "🚀 BioSecure AI starting with direct Gunicorn server..."
echo "🌐 Access Application at: http://0.0.0.0:${BACKEND_PORT}"
echo "=========================================================="
exec gunicorn wsgi:app \
    --workers 2 \
    --bind "0.0.0.0:${BACKEND_PORT}" \
    --timeout "${GUNICORN_TIMEOUT:-300}" \
    --access-logfile - \
    --error-logfile -
