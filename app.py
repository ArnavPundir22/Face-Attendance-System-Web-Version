"""
Face Attendance System — Flask application factory.

The application is split into focused modules:
  config.py                   — tunable constants (env-var driven)
  utils/db.py                 — database helpers
  utils/face.py               — InsightFace model + encoding I/O (numpy, no pickle)
  utils/mail.py               — email delivery helpers
  blueprints/auth.py          — /login, /logout, /register
  blueprints/attendance.py    — /, /viewer, /upload_photo, /get_attendance_data, …
  blueprints/students.py      — /students, /add_student, /submit_student
  blueprints/admin.py         — /admin/…
"""

import os

from flask import Flask, redirect, session, url_for

from blueprints.admin import admin_bp
from blueprints.attendance import attendance_bp
from blueprints.auth import auth_bp
from blueprints.students import students_bp

# ---------------------------------------------------------------------------
# Application factory
# ---------------------------------------------------------------------------

app = Flask(__name__)
app.secret_key = os.environ.get('FLASK_SECRET_KEY')
if not app.secret_key:
    raise RuntimeError(
        "FLASK_SECRET_KEY is not set. "
        "Generate one with: python -c \"import secrets; print(secrets.token_hex(32))\" "
        "and add it to your .env file."
    )

# ---------------------------------------------------------------------------
# Register blueprints
# ---------------------------------------------------------------------------

app.register_blueprint(auth_bp)
app.register_blueprint(attendance_bp)
app.register_blueprint(students_bp)
app.register_blueprint(admin_bp)

# ---------------------------------------------------------------------------
# Application-wide hooks
# ---------------------------------------------------------------------------

@app.context_processor
def inject_user_info():
    return {
        'session_username': session.get('username'),
        'session_is_admin': session.get('is_admin', False) if 'username' in session else False,
    }


@app.before_request
def require_login():
    """Redirect unauthenticated requests to /login, except for public paths."""
    from flask import request

    public_paths = {'/login', '/favicon.ico'}
    if request.path.startswith('/static/') or request.path in public_paths:
        return None
    if 'logged_in' not in session:
        return redirect(url_for('auth.login'))
    return None

# ---------------------------------------------------------------------------
# Startup initialisation
# ---------------------------------------------------------------------------

if __name__ == '__main__':
    app.run(debug=True)

