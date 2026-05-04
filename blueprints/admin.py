"""
Admin Blueprint.

Routes:
  GET        /admin                          — dashboard
  GET        /admin/stats                    — JSON: 7-day trend + today stats
  GET        /admin/students                 — student list
  GET/POST   /admin/student/edit/<id>        — edit student
  POST       /admin/student/delete/<id>      — delete student
  GET/POST   /admin/mark                     — manual attendance marking
  GET        /admin/view_images              — attendance image viewer
  GET        /admin/users                    — user list
  GET/POST   /admin/user/edit/<id>           — edit user
  POST       /admin/user/delete/<id>         — delete user
  POST       /admin/reset                        — reset users, attendance, tokens (students preserved)
"""

import bcrypt
from datetime import datetime, timedelta

from flask import Blueprint, jsonify, redirect, render_template, request, session, url_for

from utils.auth_helpers import is_current_user_admin
from utils.db import get_db_connection, is_valid_email
import config

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')


def _require_admin():
    """Return a redirect/render when the current user is not admin, else None."""
    if not is_current_user_admin():
        return render_template('login.html', error="Admin access required")
    return None


@admin_bp.route('')
@admin_bp.route('/')
def admin_dashboard():
    denied = _require_admin()
    if denied:
        return denied

    conn = get_db_connection()
    total_students  = conn.execute("SELECT COUNT(*) AS cnt FROM students").fetchone()['cnt'] or 0
    total_attendance = conn.execute("SELECT COUNT(*) AS cnt FROM attendance").fetchone()['cnt'] or 0
    total_users     = conn.execute("SELECT COUNT(*) AS cnt FROM users").fetchone()['cnt'] or 0
    today_date      = datetime.now().strftime("%Y-%m-%d")
    today_att       = (
        conn.execute(
            "SELECT COUNT(*) AS cnt FROM attendance WHERE date(Timestamp)=?", (today_date,)
        ).fetchone()['cnt'] or 0
    )
    conn.close()

    return render_template(
        'admin_dashboard.html',
        total_students=total_students,
        total_attendance=total_attendance,
        total_users=total_users,
        today_attendance=today_att,
    )


@admin_bp.route('/stats')
def admin_stats():
    if not is_current_user_admin():
        return jsonify({'error': 'admin required'}), 403

    conn  = get_db_connection()
    trend = []
    for d in range(6, -1, -1):
        day = (datetime.now() - timedelta(days=d)).strftime("%Y-%m-%d")
        cnt = (
            conn.execute(
                "SELECT COUNT(*) AS cnt FROM attendance WHERE date(Timestamp)=?", (day,)
            ).fetchone()['cnt'] or 0
        )
        trend.append({'date': day, 'count': cnt})

    today   = datetime.now().strftime("%Y-%m-%d")
    present = (
        conn.execute(
            "SELECT COUNT(*) AS cnt FROM attendance "
            "WHERE date(Timestamp)=? AND Status LIKE '%Present%'",
            (today,),
        ).fetchone()['cnt'] or 0
    )
    total_today = (
        conn.execute(
            "SELECT COUNT(*) AS cnt FROM attendance WHERE date(Timestamp)=?", (today,)
        ).fetchone()['cnt'] or 0
    )
    conn.close()

    return jsonify({'trend': trend, 'present': present, 'absent': max(total_today - present, 0)})


@admin_bp.route('/students')
def admin_students():
    denied = _require_admin()
    if denied:
        return denied

    conn     = get_db_connection()
    students = conn.execute(
        "SELECT * FROM students ORDER BY Name COLLATE NOCASE"
    ).fetchall()
    conn.close()
    return render_template('admin_students.html', students=students)


@admin_bp.route('/student/edit/<student_id>', methods=['GET', 'POST'])
def admin_edit_student(student_id):
    denied = _require_admin()
    if denied:
        return denied

    conn    = get_db_connection()
    student = conn.execute("SELECT * FROM students WHERE ID=?", (student_id,)).fetchone()
    if not student:
        conn.close()
        return redirect(url_for('admin.admin_students'))

    if request.method == 'POST':
        name    = request.form['name'].strip()
        program = request.form['program'].strip()
        branch  = request.form['branch'].strip()
        mobile  = request.form['mobile'].strip()
        gmail   = request.form['gmail'].strip()
        conn.execute(
            'UPDATE students SET Name=?, Program=?, Branch=?, Mobile=?, Gmail=? WHERE ID=?',
            (name, program, branch, mobile, gmail, student_id),
        )
        conn.commit()
        conn.close()
        return redirect(url_for('admin.admin_students'))

    conn.close()
    return render_template('edit_student.html', student=student)


@admin_bp.route('/student/delete/<student_id>', methods=['POST'])
def admin_delete_student(student_id):
    denied = _require_admin()
    if denied:
        return denied

    conn = get_db_connection()
    conn.execute("DELETE FROM students WHERE ID=?", (student_id,))
    conn.commit()
    conn.close()
    return redirect(url_for('admin.admin_students'))


@admin_bp.route('/mark', methods=['GET', 'POST'])
def admin_mark_attendance():
    denied = _require_admin()
    if denied:
        return denied

    conn     = get_db_connection()
    students = conn.execute(
        "SELECT ID, Name FROM students ORDER BY Name COLLATE NOCASE"
    ).fetchall()

    if request.method == 'POST':
        student_id = request.form.get('student_id')
        status     = request.form.get('status', 'Present')
        lecture    = request.form.get('lecture', '').strip()
        section    = request.form.get('section', '').strip()
        timestamp  = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        student = conn.execute("SELECT * FROM students WHERE ID=?", (student_id,)).fetchone()
        if not student:
            conn.close()
            return render_template('admin_mark.html', students=students, error="Student not found")

        conn.execute(
            "INSERT INTO attendance "
            "(Student_ID, Name, Program, Branch, Mobile, Status, Timestamp, Lecture, Section) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                student['ID'], student['Name'], student['Program'],
                student['Branch'], student['Mobile'],
                status, timestamp, lecture, section,
            ),
        )
        conn.commit()
        conn.close()
        return redirect(url_for('admin.admin_dashboard'))

    conn.close()
    return render_template('admin_mark.html', students=students)


@admin_bp.route('/view_images')
def view_images():
    denied = _require_admin()
    if denied:
        return denied
    return render_template('view_images.html')


@admin_bp.route('/users')
def admin_users():
    denied = _require_admin()
    if denied:
        return denied

    conn  = get_db_connection()
    users = conn.execute("SELECT id, username, gmail, is_admin FROM users ORDER BY username COLLATE NOCASE").fetchall()
    conn.close()
    return render_template('admin_users.html', users=users, current_user=session.get('username'))


@admin_bp.route('/user/edit/<int:user_id>', methods=['GET', 'POST'])
def admin_edit_user(user_id):
    denied = _require_admin()
    if denied:
        return denied

    conn = get_db_connection()
    user = conn.execute("SELECT id, username, gmail, is_admin FROM users WHERE id=?", (user_id,)).fetchone()
    if not user:
        conn.close()
        return redirect(url_for('admin.admin_users'))

    if request.method == 'POST':
        new_username = request.form.get('username', '').strip()
        new_email    = request.form.get('email', '').strip()
        new_is_admin = 1 if request.form.get('is_admin') else 0
        new_password = request.form.get('password', '').strip()

        if not new_username:
            conn.close()
            return render_template('admin_edit_user.html', user=user,
                                   error="Username is required.",
                                   current_user=session.get('username'))

        if new_email and not is_valid_email(new_email):
            conn.close()
            return render_template('admin_edit_user.html', user=user,
                                   error="Enter a valid email address.",
                                   current_user=session.get('username'))

        # Prevent removing admin rights from the last admin
        if user['is_admin'] and not new_is_admin:
            admin_count = conn.execute(
                "SELECT COUNT(*) AS cnt FROM users WHERE is_admin=1"
            ).fetchone()['cnt']
            if admin_count <= 1:
                conn.close()
                return render_template('admin_edit_user.html', user=user,
                                       error="Cannot remove admin rights: at least one admin must remain.",
                                       current_user=session.get('username'))

        # Check username uniqueness (exclude current user)
        existing = conn.execute(
            "SELECT id FROM users WHERE username=? AND id!=?", (new_username, user_id)
        ).fetchone()
        if existing:
            conn.close()
            return render_template('admin_edit_user.html', user=user,
                                   error="That username is already taken.",
                                   current_user=session.get('username'))

        if new_password:
            if len(new_password) < config.MIN_PASSWORD_LENGTH:
                conn.close()
                return render_template('admin_edit_user.html', user=user,
                                       error=f"Password must be at least {config.MIN_PASSWORD_LENGTH} characters.",
                                       current_user=session.get('username'))
            hashed = bcrypt.hashpw(new_password.encode(), bcrypt.gensalt())
            conn.execute(
                "UPDATE users SET username=?, gmail=?, is_admin=?, password=? WHERE id=?",
                (new_username, new_email, new_is_admin, hashed, user_id),
            )
        else:
            conn.execute(
                "UPDATE users SET username=?, gmail=?, is_admin=? WHERE id=?",
                (new_username, new_email, new_is_admin, user_id),
            )

        conn.commit()
        conn.close()

        # Keep session consistent if admin edited their own username
        if session.get('username') == user['username'] and new_username != user['username']:
            session['username'] = new_username

        return redirect(url_for('admin.admin_users'))

    conn.close()
    return render_template('admin_edit_user.html', user=user, current_user=session.get('username'))


@admin_bp.route('/user/delete/<int:user_id>', methods=['POST'])
def admin_delete_user(user_id):
    denied = _require_admin()
    if denied:
        return denied

    conn = get_db_connection()
    user = conn.execute("SELECT id, username, is_admin FROM users WHERE id=?", (user_id,)).fetchone()

    if not user:
        conn.close()
        return redirect(url_for('admin.admin_users'))

    # Prevent deleting the last admin
    if user['is_admin']:
        admin_count = conn.execute(
            "SELECT COUNT(*) AS cnt FROM users WHERE is_admin=1"
        ).fetchone()['cnt']
        if admin_count <= 1:
            conn.close()
            return redirect(url_for('admin.admin_users', error='last_admin'))

    # Prevent admin from deleting their own account
    if user['username'] == session.get('username'):
        conn.close()
        return redirect(url_for('admin.admin_users', error='self_delete'))

    conn.execute("DELETE FROM users WHERE id=?", (user_id,))
    conn.commit()
    conn.close()
    return redirect(url_for('admin.admin_users'))


@admin_bp.route('/reset', methods=['POST'])
def admin_reset():
    denied = _require_admin()
    if denied:
        return denied

    conn = get_db_connection()
    try:
        # Delete all attendance records
        conn.execute("DELETE FROM attendance")

        # Delete all users (including the current admin)
        conn.execute("DELETE FROM users")

        # Clear password reset tokens
        conn.execute("DELETE FROM password_reset_tokens")

        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

    # Re-seed the default admin account so the system remains accessible
    from utils.db import init_users_table_and_admin
    init_users_table_and_admin()

    # Log out the current admin
    session.clear()
    return redirect(url_for('auth.login'))
