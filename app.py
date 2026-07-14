"""
BioSecure AI — Application Factory.

Entry points:
  create_app()   — application factory, used by Gunicorn and tests.
  app            — convenience instance for `flask run` / direct execution.

Blueprint layout:
  blueprints/auth.py        /login  /logout  /register
  blueprints/attendance.py  /       /viewer  /upload_photo  /get_attendance_data
  blueprints/students.py    /students  /add_student  /submit_student
  blueprints/admin.py       /admin/…
"""

from __future__ import annotations

import logging
import os

from flask import Flask, jsonify, redirect, session, url_for

import config


# ---------------------------------------------------------------------------
# Logging setup  (called once, before create_app)
# ---------------------------------------------------------------------------

def _configure_logging() -> None:
    """Configure root logger with level and format from config."""
    log_level = getattr(logging, config.LOG_LEVEL, logging.INFO)
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
    )


_configure_logging()
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Application factory
# ---------------------------------------------------------------------------

def create_app() -> Flask:
    """Create and configure the Flask application."""
    app = Flask(__name__)

    secret_key = os.environ.get("FLASK_SECRET_KEY")
    if not secret_key:
        raise RuntimeError(
            "FLASK_SECRET_KEY is not set. "
            "Generate one with: python -c \"import secrets; print(secrets.token_hex(32))\" "
            "and add it to your .env file."
        )
    app.secret_key = secret_key

    # ------------------------------------------------------------------
    # Register blueprints
    # ------------------------------------------------------------------
    from blueprints.admin import admin_bp
    from blueprints.attendance import attendance_bp
    from blueprints.auth import auth_bp
    from blueprints.students import students_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(attendance_bp)
    app.register_blueprint(students_bp)
    app.register_blueprint(admin_bp)

    logger.info("All blueprints registered.")

    # ------------------------------------------------------------------
    # Global error handlers
    # ------------------------------------------------------------------

    @app.errorhandler(404)
    def not_found(error):
        if _is_api_request():
            return jsonify({"error": "Resource not found"}), 404
        return redirect(url_for("attendance.index"))

    @app.errorhandler(403)
    def forbidden(error):
        if _is_api_request():
            return jsonify({"error": "Forbidden"}), 403
        return redirect(url_for("auth.login"))

    @app.errorhandler(500)
    def internal_error(error):
        logger.exception("Internal server error: %s", error)
        if _is_api_request():
            return jsonify({"error": "Internal server error"}), 500
        return redirect(url_for("attendance.index"))

    # ------------------------------------------------------------------
    # Context processors
    # ------------------------------------------------------------------

    @app.context_processor
    def inject_user_info():
        return {
            "session_username": session.get("username"),
            "session_is_admin": (
                session.get("is_admin", False) if "username" in session else False
            ),
        }

    # ------------------------------------------------------------------
    # Request hooks
    # ------------------------------------------------------------------

    @app.before_request
    def require_login():
        """Redirect unauthenticated requests to /login, except public paths."""
        from flask import request

        public_paths = {"/login", "/favicon.ico", "/healthz"}
        if request.path.startswith("/static/") or request.path in public_paths:
            return None
        if "logged_in" not in session:
            return redirect(url_for("auth.login"))
        return None

    # ------------------------------------------------------------------
    # Health check — used by load balancers / container orchestrators
    # ------------------------------------------------------------------

    @app.route("/healthz")
    def healthz():
        return jsonify({"status": "ok", "service": "biosecure-ai-face-attendance"}), 200

    logger.info("BioSecure AI initialised successfully.")
    return app


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _is_api_request() -> bool:
    """Return True if the current request is an XHR / API call."""
    from flask import request

    return (
        request.path.startswith("/api/")
        or request.headers.get("X-Requested-With") == "XMLHttpRequest"
        or "application/json" in request.headers.get("Accept", "")
    )


# ---------------------------------------------------------------------------
# Convenience app instance (Gunicorn: `gunicorn app:app`)
# ---------------------------------------------------------------------------

app = create_app()


if __name__ == "__main__":
    app.run(debug=True)
