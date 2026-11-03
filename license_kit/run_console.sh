#!/bin/bash
# BioSecure AI — Standalone License Kit Launcher
set -e
KIT_DIR="$(cd "$(dirname "$0")" && pwd)"
PYTHON_EXEC="$KIT_DIR/../.venv/bin/python"
if [ ! -f "$PYTHON_EXEC" ]; then
    PYTHON_EXEC="python3"
fi
exec "$PYTHON_EXEC" "$KIT_DIR/license_console.py" "$@"
