#!/bin/bash
cd /home/dell/face_attendance_web/backend/


# Activate virtual environment
source .venv/bin/activate

# Start Flask server
export FLASK_APP=app.py
export FLASK_ENV=development

# Open browser after slight delay
(sleep 6 && xdg-open http://127.0.0.1:5000) &

# Run Flask server in foreground (to see logs)
flask run
