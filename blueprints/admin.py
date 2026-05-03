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
"""

from datetime import datetime, timedelta

from flask import Blueprint, jsonify, redirect, render_template, request, url_for

from utils.auth_helpers import is_current_user_admin
from utils.db import get_db_connection

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

_ADMIN_REQUIRED_RESPONSE = lambda: render_template('login.html', error="Admin access required")


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
