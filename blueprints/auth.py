"""
Authentication Blueprint.

Routes: /login, /logout, /register, /forgot_password
"""

import bcrypt
from flask import Blueprint, redirect, render_template, request, session, url_for

import config
from utils.auth_helpers import (
    check_password,
    clear_failed_logins,
    generate_and_store_otp,
    is_account_locked,
    is_current_user_admin,
    record_failed_login,
    remaining_attempts,
    verify_and_consume_otp,
)
from utils.db import create_user, get_db_connection, is_valid_email
from utils.mail import send_password_reset_otp

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()

        if not username or not password:
            return render_template('login.html', error="Username and password required")

        locked, secs = is_account_locked(username)
        if locked:
            mins, secsrem = divmod(secs, 60)
            return render_template(
                'login.html',
                error=(
                    f"Account locked after {config.LOGIN_MAX_ATTEMPTS} failed attempts. "
                    f"Try again in {mins}m {secsrem}s."
                ),
            )

        conn = get_db_connection()
        user = conn.execute("SELECT * FROM users WHERE username=?", (username,)).fetchone()
        conn.close()

        if not user:
            record_failed_login(username)
            return render_template('login.html', error="Invalid username or password")

        try:
            if check_password(user['password'], password):
                clear_failed_logins(username)
                session['logged_in'] = True
                session['username'] = username
                return redirect(url_for('attendance.index'))
            else:
                record_failed_login(username)
                locked, secs = is_account_locked(username)
                if locked:
                    mins, secsrem = divmod(secs, 60)
                    return render_template(
                        'login.html',
                        error=(
                            f"Account locked after too many failed attempts. "
                            f"Try again in {mins}m {secsrem}s."
                        ),
                    )
                left = remaining_attempts(username)
                return render_template(
                    'login.html',
                    error=f"Invalid username or password. {left} attempt(s) remaining before lockout.",
                )
        except Exception:
            return render_template('login.html', error="Invalid username or password")

    return render_template('login.html')


@auth_bp.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('auth.login'))


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    """Admin-only user-creation route."""
    if not is_current_user_admin():
        return render_template('login.html', error="Admin access required to create new users")

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        email    = request.form.get('email', '').strip()

        if not username or not password or not email:
            return render_template('register.html', error="All fields are required")
        if len(password) < config.MIN_PASSWORD_LENGTH:
            return render_template(
                'register.html',
                error=f"Password must be at least {config.MIN_PASSWORD_LENGTH} characters",
            )
        if not is_valid_email(email):
            return render_template('register.html', error="Enter a valid email address")

        if not create_user(username, password, is_admin=0, gmail=email):
            return render_template('register.html', error="Username already exists")
        return render_template('register.html', success="User created successfully!")

    return render_template('register.html')


@auth_bp.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    """Two-step email-OTP password reset."""
    if request.method == 'GET':
        return render_template('forgot_password.html', step='request')

    step = request.form.get('step', 'request')

    # --- Step 1: receive username → send OTP ---
    if step == 'request':
        username = request.form.get('username', '').strip()
        if not username:
            return render_template('forgot_password.html', step='request',
                                   error="Please enter your username.")

        conn = get_db_connection()
        user = conn.execute(
            "SELECT username, gmail FROM users WHERE username=?", (username,)
        ).fetchone()
        conn.close()

        generic_msg = (
            "If that username exists and has a registered email, "
            "an OTP has been sent. Check your inbox."
        )

        if not user or not user['gmail']:
            return render_template('forgot_password.html', step='request', info=generic_msg)

        try:
            otp = generate_and_store_otp(username)
            send_password_reset_otp(user['gmail'], otp, username)
        except Exception:
            return render_template(
                'forgot_password.html', step='request',
                error="Could not send OTP email. Please contact the admin.",
            )

        return render_template('forgot_password.html', step='verify',
                               username=username, info=generic_msg)

    # --- Step 2: verify OTP → update password ---
    if step == 'verify':
        username     = request.form.get('username', '').strip()
        otp          = request.form.get('otp', '').strip()
        new_password = request.form.get('new_password', '').strip()

        if not username or not otp or not new_password:
            return render_template('forgot_password.html', step='verify',
                                   username=username, error="All fields are required.")
        if len(new_password) < config.MIN_PASSWORD_LENGTH:
            return render_template(
                'forgot_password.html', step='verify', username=username,
                error=f"Password must be at least {config.MIN_PASSWORD_LENGTH} characters.",
            )
        if not verify_and_consume_otp(username, otp):
            return render_template('forgot_password.html', step='verify',
                                   username=username,
                                   error="Invalid or expired OTP. Please request a new one.")

        hashed = bcrypt.hashpw(new_password.encode(), bcrypt.gensalt())
        conn = get_db_connection()
        conn.execute("UPDATE users SET password=? WHERE username=?", (hashed, username))
        conn.commit()
        conn.close()
        clear_failed_logins(username)
        return redirect(url_for('auth.login'))

    return render_template('forgot_password.html', step='request')
