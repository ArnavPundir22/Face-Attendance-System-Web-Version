#!/bin/bash
# BioSecure AI Enterprise Launcher Entrypoint
# Delegates execution to scripts/launchers/start_face_attendance.sh

set -e
PROJECT_ROOT="$(cd "$(dirname "$0")" && pwd)"
exec "$PROJECT_ROOT/scripts/launchers/start_face_attendance.sh" "$@"
