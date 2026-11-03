#!/bin/bash
# BioSecure AI — Interactive Licensing Console Launcher
# Delegates to self-contained license_kit/run_console.sh
set -e
PROJECT_ROOT="$(cd "$(dirname "$0")" && pwd)"
exec "$PROJECT_ROOT/license_kit/run_console.sh" "$@"
