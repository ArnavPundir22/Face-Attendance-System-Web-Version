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
"""

from datetime import datetime, timedelta

from flask import Blueprint, jsonify, redirect, render_template, request, session, url_for

from src.utils.db import supabase_admin as supabase, is_valid_email
from src import config

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')


def _require_admin():
    """Return a redirect/render when the current user is not admin, else None."""
    if not session.get('is_admin'):
        return render_template('login.html', error="Admin access required")
    return None


@admin_bp.route('')
@admin_bp.route('/')
def admin_dashboard():
    denied = _require_admin()
    if denied:
        return denied

    try:
        total_students = supabase.table('students').select('*', count='exact').execute().count or 0
        total_attendance = supabase.table('attendance').select('*', count='exact').execute().count or 0
        
        # We can't efficiently count auth.users from client without admin API, so we fetch all
        users_resp = supabase.auth.admin.list_users()
        total_users = len(users_resp) if isinstance(users_resp, list) else len(getattr(users_resp, 'users', []))
        
        today_date = datetime.now().strftime("%Y-%m-%d")
        
        # Count attendance where timestamp starts with today's date
        today_att_resp = supabase.table('attendance').select('*', count='exact').ilike('timestamp', f'{today_date}%').execute()
        today_att = today_att_resp.count or 0
    except Exception as e:
        print("Dashboard error:", e)
        total_students, total_attendance, total_users, today_att = 0, 0, 0, 0

    return render_template(
        'admin_dashboard.html',
        total_students=total_students,
        total_attendance=total_attendance,
        total_users=total_users,
        today_attendance=today_att,
    )


@admin_bp.route('/stats')
def admin_stats():
    if not session.get('is_admin'):
        return jsonify({'error': 'admin required'}), 403

    trend = []
    try:
        for d in range(6, -1, -1):
            day = (datetime.now() - timedelta(days=d)).strftime("%Y-%m-%d")
            
            cnt_resp = supabase.table('attendance').select('*', count='exact').ilike('timestamp', f'{day}%').execute()
            cnt = cnt_resp.count or 0
            trend.append({'date': day, 'count': cnt})

        today = datetime.now().strftime("%Y-%m-%d")
        present_resp = supabase.table('attendance').select('*', count='exact').ilike('timestamp', f'{today}%').ilike('status', '%Present%').execute()
        present = present_resp.count or 0
        
        total_today_resp = supabase.table('attendance').select('*', count='exact').ilike('timestamp', f'{today}%').execute()
        total_today = total_today_resp.count or 0
        
    except Exception as e:
        print("Stats error:", e)
        present = 0
        total_today = 0

    return jsonify({'trend': trend, 'present': present, 'absent': max(total_today - present, 0)})


@admin_bp.route('/students')
def admin_students():
    denied = _require_admin()
    if denied:
        return denied

    try:
        students_resp = supabase.table('students').select('*').order('name').execute()
        students = students_resp.data
    except Exception:
        students = []
        
    return render_template('admin_students.html', students=students)


@admin_bp.route('/student/edit/<student_id>', methods=['GET', 'POST'])
def admin_edit_student(student_id):
    denied = _require_admin()
    if denied:
        return denied

    try:
        student_resp = supabase.table('students').select('*').eq('id', student_id).execute()
        if not student_resp.data:
            return redirect(url_for('admin.admin_students'))
        student = student_resp.data[0]
    except Exception:
        return redirect(url_for('admin.admin_students'))

    if request.method == 'POST':
        name    = request.form['name'].strip()
        program = request.form['program'].strip()
        branch  = request.form['branch'].strip()
        gmail   = request.form['gmail'].strip()
        
        try:
            supabase.table('students').update({
                'name': name,
                'program': program,
                'branch': branch,
                'gmail': gmail
            }).eq('id', student_id).execute()
        except Exception as e:
            print("Update student error:", e)
            
        return redirect(url_for('admin.admin_students'))

    return render_template('edit_student.html', student=student)


@admin_bp.route('/student/delete/<student_id>', methods=['POST'])
def admin_delete_student(student_id):
    denied = _require_admin()
    if denied:
        return denied

    try:
        # 1. Delete student attendance logs first to satisfy foreign key constraints
        supabase.table('attendance').delete().eq('student_id', student_id).execute()
        
        # 2. Delete the student profile from the database
        supabase.table('students').delete().eq('id', student_id).execute()
        
        # 3. Clean up the registered photo from disk
        from werkzeug.utils import secure_filename
        safe_id = secure_filename(student_id)
        if safe_id:
            filename = f"{safe_id}.jpg"
            filepath = os.path.join(config.KNOWN_FACES_DIR, filename)
            if os.path.exists(filepath):
                os.remove(filepath)
    except Exception as e:
        print(f"Cascading delete failed for student {student_id}: {e}")
        
    return redirect(url_for('admin.admin_students'))


@admin_bp.route('/mark', methods=['GET', 'POST'])
def admin_mark_attendance():
    denied = _require_admin()
    if denied:
        return denied

    try:
        students_resp = supabase.table('students').select('*').order('name').execute()
        students = students_resp.data or []
    except Exception:
        students = []

    if request.method == 'POST':
        present_ids = set(request.form.getlist('student_ids'))
        lecture     = request.form.get('lecture', '').strip()
        timestamp   = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        if not lecture:
            return render_template('admin_mark.html', students=students, error="Lecture name is required")

        attendance_records = []
        for s in students:
            s_id = s.get('id')
            status = 'Present' if s_id in present_ids else 'Absent'
            attendance_records.append({
                "student_id": s_id,
                "name": s.get('name'),
                "program": s.get('program'),
                "branch": s.get('branch'),
                "status": status,
                "timestamp": timestamp,
                "lecture": lecture
            })

        try:
            if attendance_records:
                supabase.table('attendance').insert(attendance_records).execute()
        except Exception as e:
            print("Bulk manual mark attendance error:", e)
            return render_template('admin_mark.html', students=students, error="Database error")
            
        return redirect(url_for('admin.admin_dashboard'))

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

    try:
        users_resp = supabase.auth.admin.list_users()
        users_list = users_resp if isinstance(users_resp, list) else getattr(users_resp, 'users', [])
        users = []
        for u in users_list:
            metadata = u.user_metadata or {}
            users.append({
                'id': u.id,
                'email': u.email,
                'username': metadata.get('username', u.email),
                'is_admin': metadata.get('is_admin', False)
            })
        
        # Sort users by username case-insensitive
        users.sort(key=lambda x: x['username'].lower())
    except Exception as e:
        print("List users error:", e)
        users = []
        
    return render_template('admin_users.html', users=users, current_user=session.get('username'))


@admin_bp.route('/user/edit/<user_id>', methods=['GET', 'POST'])
def admin_edit_user(user_id):
    denied = _require_admin()
    if denied:
        return denied

    try:
        user_resp = supabase.auth.admin.get_user_by_id(user_id)
        u = user_resp.user
        metadata = u.user_metadata or {}
        user = {
            'id': u.id,
            'email': u.email,
            'username': metadata.get('username', u.email),
            'is_admin': metadata.get('is_admin', False)
        }
    except Exception:
        return redirect(url_for('admin.admin_users'))

    if request.method == 'POST':
        new_username = request.form.get('username', '').strip()
        new_email    = request.form.get('email', '').strip()
        new_is_admin = 1 if request.form.get('is_admin') else 0
        new_password = request.form.get('password', '').strip()

        if not new_username:
            return render_template('admin_edit_user.html', user=user,
                                   error="Username is required.",
                                   current_user=session.get('username'))

        if new_email and not is_valid_email(new_email):
            return render_template('admin_edit_user.html', user=user,
                                   error="Enter a valid email address.",
                                   current_user=session.get('username'))

        # Prevent removing admin rights from the last admin
        if user['is_admin'] and not new_is_admin:
            try:
                # Count admins
                all_users_resp = supabase.auth.admin.list_users()
                users_list = all_users_resp if isinstance(all_users_resp, list) else getattr(all_users_resp, 'users', [])
                admin_count = sum(1 for u in users_list if (u.user_metadata or {}).get('is_admin', False))
                
                if admin_count <= 1:
                    return render_template('admin_edit_user.html', user=user,
                                        error="Cannot revoke the last admin account.",
                                        current_user=session.get('username'))
            except Exception:
                pass

        try:
            update_data = {
                "email": new_email if new_email else user['email'],
                "user_metadata": {
                    "username": new_username,
                    "is_admin": bool(new_is_admin)
                }
            }
            if new_password:
                if len(new_password) < config.MIN_PASSWORD_LENGTH:
                    return render_template('admin_edit_user.html', user=user,
                                           error=f"Password must be >= {config.MIN_PASSWORD_LENGTH} chars.",
                                           current_user=session.get('username'))
                update_data["password"] = new_password
                
            supabase.auth.admin.update_user_by_id(user_id, update_data)
        except Exception as e:
            return render_template('admin_edit_user.html', user=user,
                                   error="Error updating user: " + str(e),
                                   current_user=session.get('username'))

        return redirect(url_for('admin.admin_users'))

    return render_template('admin_edit_user.html', user=user, current_user=session.get('username'))


@admin_bp.route('/user/delete/<user_id>', methods=['POST'])
def admin_delete_user(user_id):
    denied = _require_admin()
    if denied:
        return denied

    # Don't allow user to delete themselves
    if session.get('user_id') == user_id:
        return redirect(url_for('admin.admin_users'))

    try:
        user_resp = supabase.auth.admin.get_user_by_id(user_id)
        u = user_resp.user
        
        # Prevent deleting the last admin
        if (u.user_metadata or {}).get('is_admin', False):
            all_users_resp = supabase.auth.admin.list_users()
            users_list = all_users_resp if isinstance(all_users_resp, list) else getattr(all_users_resp, 'users', [])
            admin_count = sum(1 for u in users_list if (u.user_metadata or {}).get('is_admin', False))
            if admin_count <= 1:
                return redirect(url_for('admin.admin_users'))

        supabase.auth.admin.delete_user(user_id)
    except Exception:
        pass

    return redirect(url_for('admin.admin_users'))


@admin_bp.route('/reset', methods=['POST'])
def admin_reset():
    denied = _require_admin()
    if denied:
        return denied

    reset_type = request.form.get('reset_type')
    import os

    try:
        if reset_type == 'attendance':
            # Delete all rows in attendance table where att_id is greater than 0
            supabase.table('attendance').delete().gt('att_id', 0).execute()
        elif reset_type == 'all':
            # Delete attendance first because of foreign key dependency
            supabase.table('attendance').delete().gt('att_id', 0).execute()
            # Delete all students (where ID is not empty)
            supabase.table('students').delete().neq('id', '').execute()

            # Empty the known_faces directory
            if os.path.exists(config.KNOWN_FACES_DIR):
                for filename in os.listdir(config.KNOWN_FACES_DIR):
                    file_path = os.path.join(config.KNOWN_FACES_DIR, filename)
                    try:
                        if os.path.isfile(file_path) or os.path.islink(file_path):
                            os.unlink(file_path)
                    except Exception as e:
                        print(f"Failed to delete {file_path} on disk: {e}")
        else:
            return redirect(url_for('admin.admin_dashboard', error="Invalid reset type"))

        return redirect(url_for('admin.admin_dashboard', status="success", message="Database reset successfully"))
    except Exception as e:
        print("Reset error:", e)
        return redirect(url_for('admin.admin_dashboard', error=str(e)))


@admin_bp.route('/academics', methods=['GET', 'POST'])
def admin_academics():
    denied = _require_admin()
    if denied:
        return denied

    if request.method == 'POST':
        action = request.form.get('action')
        item_type = request.form.get('type')  # program, branch
        item_value = request.form.get('value', '').strip()

        if action == 'add' and item_type and item_value:
            try:
                supabase.table('academic_structure').upsert({
                    'type': item_type,
                    'value': item_value
                }, on_conflict='type,value').execute()
            except Exception as e:
                print("Error adding academic item:", e)

        elif action == 'delete' and item_type and item_value:
            try:
                # First delete matching rows from academic_structure table
                supabase.table('academic_structure').delete().eq('type', item_type).eq('value', item_value).execute()
            except Exception as e:
                print("Error deleting academic item from academic_structure:", e)

        return redirect(url_for('admin.admin_academics'))

    # Fetch academic structure from table
    try:
        resp = supabase.table('academic_structure').select('*').order('value').execute()
        rows = resp.data or []
    except Exception:
        rows = []

    programs = sorted(list({r['value'] for r in rows if r.get('type') == 'program'}))
    branches = sorted(list({r['value'] for r in rows if r.get('type') == 'branch'}))

    return render_template(
        'admin_academics.html',
        programs=programs,
        branches=branches
    )

