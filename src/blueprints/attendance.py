"""
Attendance Blueprint.

Routes:
  GET  /                       — upload page
  GET  /viewer                 — attendance viewer
  GET  /get_attendance_data    — JSON: full attendance table
  POST /upload_photo           — process uploaded photos, mark attendance
  POST /send_attendance_email  — generate PDF and email it
"""

import base64
from datetime import datetime, timedelta

import cv2
import numpy as np
from flask import Blueprint, jsonify, render_template, request

import re

from src import config
from src.utils.db import supabase_admin, is_valid_email
from src.utils.face import model, normalize_embedding

attendance_bp = Blueprint('attendance', __name__)


def extract_student_year(student_dict: dict):
    """Extract or derive the 4-digit enrollment/batch year for a student."""
    if not student_dict:
        return None
    
    # 1. Derive from student ID prefix (e.g. Cu240251013 -> 2024, CU26250073 / Ci26250070 -> 2026)
    sid = str(student_dict.get('id', '')).strip()
    if sid:
        match = re.match(r'(?i)^(?:cu|ci)?(\d{2})', sid)
        if match:
            two_digit = match.group(1)
            val = int(two_digit)
            if 15 <= val <= 35:
                return int(f"20{two_digit}")

    # 2. Check enrollment_year column
    ey = student_dict.get('enrollment_year')
    if ey is not None and str(ey).strip().isdigit():
        val = int(str(ey).strip())
        if 1900 <= val <= 2100:
            return val

    # 3. Check academic_year column
    ay = student_dict.get('academic_year')
    if ay:
        match = re.search(r'\b(20\d{2})\b', str(ay))
        if match:
            return int(match.group(1))

    return None


# ---------------------------------------------------------------------------
# Drift Detection Helper
# ---------------------------------------------------------------------------

def _compute_drift_level(ewma: float) -> str:
    """Map an EWMA drift value to a human-readable alert level."""
    if ewma >= config.DRIFT_ALERT_THRESHOLD:
        return 'ALERT'
    if ewma >= config.DRIFT_CRITICAL_THRESHOLD:
        return 'CRITICAL'
    if ewma >= config.DRIFT_WARN_THRESHOLD:
        return 'WARNING'
    return 'HEALTHY'


def _send_drift_email_alert(student_id: str, alert_level: str, ewma_drift: float):
    """Send an automated SMTP email notification to admin when biometric drift triggers CRITICAL or ALERT."""
    if not config.EMAIL_USER or not config.EMAIL_PASS:
        return  # Email not configured

    import smtplib
    from email.mime.multipart import MIMEMultipart
    from email.mime.text import MIMEText

    try:
        # Fetch student & admin contact info
        stu_resp = supabase_admin.table('students').select('name, program, branch, gmail').eq('id', student_id).maybe_single().execute()
        student = stu_resp.data or {}
        student_name = student.get('name', student_id)
        student_email = student.get('gmail', '')

        subject = f"Biometric Drift Alert [{alert_level}]: {student_name} ({student_id})"
        
        body_html = f"""
        <div style="font-family: Arial, sans-serif; padding: 20px; color: #333; background-color: #f9f9f9; border-radius: 8px;">
            <h2 style="color: #c0392b;">Biometric Template Drift Alert</h2>
            <p>Biometric monitoring system has detected significant template aging / appearance shift for student:</p>
            <table style="width: 100%; border-collapse: collapse; margin-top: 15px;">
                <tr><td style="padding: 8px; font-weight: bold; width: 150px;">Student ID:</td><td>{student_id}</td></tr>
                <tr><td style="padding: 8px; font-weight: bold;">Student Name:</td><td>{student_name}</td></tr>
                <tr><td style="padding: 8px; font-weight: bold;">Program / Branch:</td><td>{student.get('program', 'N/A')} - {student.get('branch', 'N/A')}</td></tr>
                <tr><td style="padding: 8px; font-weight: bold;">Current EWMA Drift:</td><td><b>{ewma_drift:.4f}</b></td></tr>
                <tr><td style="padding: 8px; font-weight: bold;">Alert Level:</td><td><span style="background-color: #e74c3c; color: white; padding: 4px 8px; border-radius: 4px;">{alert_level}</span></td></tr>
            </table>
            <p style="margin-top: 20px;"><b>Action Recommended:</b> Please arrange for student re-enrollment (capturing a new high-quality reference photo) in the admin portal.</p>
            <hr style="border: none; border-top: 1px solid #ddd; margin-top: 20px;">
            <p style="font-size: 12px; color: #777;">BioSecure AI Autonomous System Monitoring</p>
        </div>
        """

        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = config.EMAIL_USER
        msg['To'] = config.EMAIL_USER  # Admin recipient
        if student_email and is_valid_email(student_email):
            msg['Cc'] = student_email

        msg.attach(MIMEText(body_html, 'html'))

        with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=10) as server:
            server.login(config.EMAIL_USER, config.EMAIL_PASS)
            server.send_message(msg)

    except Exception as err:
        import logging
        logging.getLogger(__name__).warning("Failed to send drift email alert: %s", err)


def _update_drift(student_id: str, cosine_sim: float, pose_yaw: float, pose_pitch: float) -> dict:
    """
    Pose-Gated EWMA Drift Tracking (Patent Idea #3).

    If the detected face pose exceeds the configured yaw/pitch thresholds,
    the EWMA is NOT updated — the event is logged as POSE_REJECTED so that
    bad-angle photos never inflate the drift signal.

    Returns a dict with keys: pose_accepted, alert_level, ewma_drift.
    """
    pose_accepted = (
        abs(pose_yaw)   <= config.DRIFT_POSE_YAW_MAX and
        abs(pose_pitch) <= config.DRIFT_POSE_PITCH_MAX
    )

    try:
        if pose_accepted:
            drift_score = 1.0 - cosine_sim

            # Fetch current EWMA from students table (fast single-row lookup)
            stu_resp = supabase_admin.table('students') \
                .select('current_ewma_drift') \
                .eq('id', student_id) \
                .maybe_single() \
                .execute()
            prev_ewma = (stu_resp.data or {}).get('current_ewma_drift') or 0.0

            new_ewma    = config.DRIFT_ALPHA * drift_score + (1 - config.DRIFT_ALPHA) * prev_ewma
            alert_level = _compute_drift_level(new_ewma)

            # Append event to embedding_health history
            supabase_admin.table('embedding_health').insert({
                'student_id':       student_id,
                'drift_score':      round(drift_score, 6),
                'ewma_drift':       round(new_ewma,    6),
                'match_confidence': round(cosine_sim,  6),
                'alert_level':      alert_level,
                'pose_yaw':         round(pose_yaw,    2),
                'pose_pitch':       round(pose_pitch,  2),
                'pose_accepted':    True,
            }).execute()

            # Keep students table in sync for fast dashboard queries
            supabase_admin.table('students').update({
                'current_ewma_drift': round(new_ewma, 6),
                'drift_alert_level':  alert_level,
            }).eq('id', student_id).execute()

            # Trigger email alert if CRITICAL or ALERT
            if alert_level in ('CRITICAL', 'ALERT'):
                _send_drift_email_alert(student_id, alert_level, new_ewma)

            return {'pose_accepted': True, 'alert_level': alert_level, 'ewma_drift': round(new_ewma, 4)}

        else:
            # Pose rejected — log the event but do NOT touch the EWMA
            supabase_admin.table('embedding_health').insert({
                'student_id':       student_id,
                'drift_score':      None,
                'ewma_drift':       None,
                'match_confidence': round(cosine_sim, 6),
                'alert_level':      'POSE_REJECTED',
                'pose_yaw':         round(pose_yaw,   2),
                'pose_pitch':       round(pose_pitch,  2),
                'pose_accepted':    False,
            }).execute()
            return {'pose_accepted': False, 'alert_level': 'POSE_REJECTED', 'ewma_drift': None}


    except Exception as exc:
        # Drift tracking must never break attendance marking
        import logging
        logging.getLogger(__name__).warning('Drift tracking error for %s: %s', student_id, exc)
        return {'pose_accepted': pose_accepted, 'alert_level': 'UNKNOWN', 'ewma_drift': None}


@attendance_bp.route('/')
def index():
    return render_template('index.html')


@attendance_bp.route('/viewer')
def viewer():
    return render_template('viewer.html')


@attendance_bp.route('/get_attendance_data')
def get_attendance_data():
    try:
        # Fetch all registered students to map student ID to batch/enrollment year
        students_resp = supabase_admin.table('students').select('id, name, branch, program, enrollment_year, academic_year').execute()
        stus = students_resp.data or []
        student_year_map = {}
        students_list = []
        for s in stus:
            s_dict = dict(s)
            y = extract_student_year(s_dict)
            s_dict['batch_year'] = y
            students_list.append(s_dict)
            if s.get('id'):
                student_year_map[str(s.get('id')).strip().upper()] = str(y) if y else ''

        # Fetch up to 4000 most recent attendance records ordered by att_id and timestamp descending
        try:
            response = supabase_admin.table('attendance')\
                .select('att_id, student_id, name, program, branch, status, timestamp, lecture')\
                .order('att_id', desc=True)\
                .limit(4000)\
                .execute()
        except Exception:
            response = supabase_admin.table('attendance')\
                .select('student_id, name, program, branch, status, timestamp, lecture')\
                .order('timestamp', desc=True)\
                .limit(4000)\
                .execute()
        data = []
        for row in response.data:
            sid = str(row.get('student_id', '')).strip().upper()
            batch_yr = student_year_map.get(sid, '')
            data.append([
                row.get('student_id', ''),
                row.get('name', ''),
                row.get('program', ''),
                row.get('branch', ''),
                batch_yr,
                row.get('status', ''),
                row.get('timestamp', ''),
                row.get('lecture', '')
            ])
            
        return jsonify({
            "attendance": data,
            "students": students_list
        })
    except Exception as e:
        import logging
        logging.getLogger(__name__).error("Error fetching attendance data: %s", e, exc_info=True)
        return jsonify({"attendance": [], "students": []})





@attendance_bp.route('/upload_photo', methods=['POST'])
def upload_photo():
    if 'images' not in request.files:
        return jsonify({"images": [], "session_attendance": [], "detected_program": None, "detected_branch": None, "detected_year": None})

    lecture = request.form.get('lecture', '').strip()
    if not lecture:
        lecture = f"Session {datetime.now().strftime('%Y-%m-%d %H:%M')}"

    files   = request.files.getlist('images')

    now       = datetime.now()
    timestamp = now.strftime("%Y-%m-%d %H:%M:%S")

    recognized_ids = set()
    all_outputs      = []
    confidence_map   = {}

    for file in files:
        npimg  = np.frombuffer(file.read(), np.uint8)
        frame  = cv2.imdecode(npimg, cv2.IMREAD_COLOR)
        if frame is None:
            all_outputs.append({"results": [], "annotated": ""})
            continue

        original = frame.copy()
        faces    = model.get(frame)
        results  = []

        if faces:
            for face in faces:
                bbox      = [int(v) for v in face.bbox]
                new_emb = np.array(face.embedding, dtype=np.float32)
                embedding = normalize_embedding(new_emb)
                
                if embedding is None:
                    continue

                best_score = -1.0
                best_name  = None
                matched_id = None

                try:
                    # Try matching with L2-normalized embedding (Global scope)
                    rpc_params = {
                        'query_embedding': embedding.tolist(),
                        'match_threshold': config.FACE_MATCH_THRESHOLD,
                        'filter_program': None,
                        'filter_branch': None,
                        'filter_section': None
                    }
                    match_resp = supabase_admin.rpc('match_face', rpc_params).execute()
                    match_data = match_resp.data

                    # Fallback: try matching with raw InsightFace embedding (Global scope)
                    if not match_data or len(match_data) == 0:
                        raw_rpc_params = {
                            'query_embedding': new_emb.tolist(),
                            'match_threshold': config.FACE_MATCH_THRESHOLD,
                            'filter_program': None,
                            'filter_branch': None,
                            'filter_section': None
                        }
                        match_resp = supabase_admin.rpc('match_face', raw_rpc_params).execute()
                        match_data = match_resp.data
                except Exception as e:
                    import logging
                    logging.getLogger(__name__).error("Error matching face via pgvector: %s", e)
                    match_data = []

                if match_data and len(match_data) > 0:
                    best_match = match_data[0]
                    best_score = float(best_match['similarity'])
                    best_name = best_match['name']
                    matched_id = best_match['id']
                
                color = (0, 255, 0) if best_score >= config.FACE_MATCH_THRESHOLD else (0, 0, 255)
                label = best_name if best_name else "Unknown"

                cv2.rectangle(original, (bbox[0], bbox[1]), (bbox[2], bbox[3]), color, 2)
                cv2.putText(
                    original,
                    f"{label} ({best_score:.2f})",
                    (bbox[0], bbox[1] - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2,
                )

                if matched_id and best_score >= config.FACE_MATCH_THRESHOLD:
                    recognized_ids.add(matched_id)
                    confidence_map[matched_id] = best_score

                    # ── Pose-Gated Drift Detection (Patent Idea #3) ──────────────────
                    pose_yaw   = float(face.pose[1]) if (hasattr(face, 'pose') and face.pose is not None) else 0.0
                    pose_pitch = float(face.pose[0]) if (hasattr(face, 'pose') and face.pose is not None) else 0.0
                    drift_info = _update_drift(matched_id, best_score, pose_yaw, pose_pitch)
                    # ─────────────────────────────────────────────────────────────────

                    results.append({
                        'name':       best_name,
                        'status':     'Present',
                        'confidence': f'{best_score:.2f}',
                        'drift_alert': drift_info['alert_level'],
                        'pose_accepted': drift_info['pose_accepted'],
                    })
                else:
                    results.append({
                        "name": "Unknown",
                        "status": "Unknown",
                        "confidence": f"{best_score:.2f}" if best_score > 0 else "0.00",
                    })

        _, buf = cv2.imencode('.jpg', original)
        encoded_img = base64.b64encode(buf).decode('utf-8')
        all_outputs.append({
            "results":   results,
            "annotated": f"data:image/jpeg;base64,{encoded_img}",
        })

    # Auto-detect program, branch, and batch year (enrollment_year) based on recognized student IDs
    detected_program = None
    detected_branch  = None
    detected_year    = None
    all_students     = []
    rec_students     = []

    if recognized_ids:
        try:
            rec_students_resp = supabase_admin.table('students').select('*').in_('id', list(recognized_ids)).execute()
            rec_students = rec_students_resp.data or []
            
            from collections import Counter
            pb_list = []
            year_list = []
            for s in rec_students:
                p = s.get('program')
                b = s.get('branch')
                y = extract_student_year(s)
                if p and b:
                    pb_list.append((p, b))
                if y is not None:
                    year_list.append(y)
            
            if pb_list:
                most_common_pb = Counter(pb_list).most_common(1)[0][0]
                detected_program = most_common_pb[0]
                detected_branch  = most_common_pb[1]

            if year_list:
                detected_year = Counter(year_list).most_common(1)[0][0]
        except Exception as e:
            import logging
            logging.getLogger(__name__).error("Error in class auto-detection: %s", e)

    # Fallback to form field inputs if not auto-detected or if explicit form selection provided
    form_prog = request.form.get('program', '').strip()
    form_bran = request.form.get('branch', '').strip()
    form_year = request.form.get('enrollment_year') or request.form.get('year')

    if form_prog and form_prog != 'Auto-Detect':
        detected_program = form_prog
    if form_bran and form_bran != 'Auto-Detect':
        detected_branch = form_bran
    if form_year and str(form_year).strip().isdigit() and str(form_year).strip() != 'Auto-Detect':
        detected_year = int(str(form_year).strip())

    if detected_program and detected_branch:
        try:
            students_resp = supabase_admin.table('students').select('*').ilike('program', detected_program).ilike('branch', detected_branch).execute()
            raw_students = students_resp.data or []
            
            # If detected_year is still None, derive the most common batch year among raw_students for that program & branch
            if detected_year is None and raw_students:
                years_in_raw = [extract_student_year(s) for s in raw_students if extract_student_year(s) is not None]
                if years_in_raw:
                    from collections import Counter
                    detected_year = Counter(years_in_raw).most_common(1)[0][0]

            # ALWAYS strictly filter by detected_year so students of different batch years are NEVER mixed together
            if detected_year is not None:
                all_students = [s for s in raw_students if extract_student_year(s) == detected_year]
            else:
                all_students = raw_students
        except Exception as e:
            import logging
            logging.getLogger(__name__).error("Error fetching students for detected class: %s", e)

    # Fallback: If class query yielded no results but we recognized student(s), use recognized list
    if not all_students and rec_students:
        all_students = rec_students

    # CRITICAL FIX: Ensure ALL recognized students are ALWAYS included in all_students so their Present mark is never lost
    existing_student_ids = {str(s.get('id')).strip().upper() for s in all_students if s.get('id')}
    for rs in rec_students:
        rs_id = str(rs.get('id')).strip().upper() if rs.get('id') else None
        if rs_id and rs_id not in existing_student_ids:
            all_students.append(rs)
            existing_student_ids.add(rs_id)

    # Prepare bulk attendance records for ALL registered students in the auto-detected program & branch & batch year
    attendance_records = []
    session_attend = []

    clean_recognized_ids = {str(rid).strip().upper() for rid in recognized_ids if rid}

    for student in all_students:
        s_id = student.get('id')
        is_present = str(s_id).strip().upper() in clean_recognized_ids if s_id else False
        status = 'Present' if is_present else 'Absent'

        record = {
            "student_id": s_id,
            "name": student.get('name'),
            "program": student.get('program'),
            "branch": student.get('branch'),
            "status": status,
            "timestamp": timestamp,
            "lecture": lecture
        }
        attendance_records.append(record)
        session_attend.append([
            s_id, student.get('name'), student.get('program'),
            student.get('branch'),
            status, timestamp, lecture
        ])

    # Bulk insert attendance records
    if attendance_records:
        try:
            insert_resp = supabase_admin.table('attendance').insert(attendance_records).execute()
            import logging
            logging.getLogger(__name__).info("Successfully inserted logs: %d", len(insert_resp.data or []))
        except Exception as e:
            import logging
            logging.getLogger(__name__).error("Failed to insert bulk attendance: %s", e, exc_info=True)

    return jsonify({
        "images": all_outputs,
        "session_attendance": session_attend,
        "detected_program": detected_program,
        "detected_branch": detected_branch,
        "detected_year": detected_year
    })


@attendance_bp.route('/update_attendance_status', methods=['POST'])
def update_attendance_status():
    data = request.get_json() or {}
    student_id = data.get('student_id')
    lecture = data.get('lecture')
    timestamp = data.get('timestamp')
    status = data.get('status')
    
    if not student_id or not lecture or not timestamp or not status:
        return jsonify({"success": False, "error": "Missing parameters"}), 400
        
    try:
        # Check if record already exists
        existing = supabase_admin.table('attendance').select('att_id').eq('student_id', student_id).eq('lecture', lecture).eq('timestamp', timestamp).execute()
        
        if existing.data:
            supabase_admin.table('attendance').update({"status": status}).eq('student_id', student_id).eq('lecture', lecture).eq('timestamp', timestamp).execute()
        else:
            # Fetch student details for a complete attendance insert
            student_resp = supabase_admin.table('students').select('*').eq('id', student_id).execute()
            if student_resp.data:
                student = student_resp.data[0]
                supabase_admin.table('attendance').insert({
                    "student_id": student_id,
                    "name": student.get('name'),
                    "program": student.get('program'),
                    "branch": student.get('branch'),
                    "status": status,
                    "timestamp": timestamp,
                    "lecture": lecture
                }).execute()
            else:
                return jsonify({"success": False, "error": "Student not found in directory"}), 404
        return jsonify({"success": True})
    except Exception as e:
        import logging
        logging.getLogger(__name__).error("Error updating/inserting attendance status: %s", e, exc_info=True)
        return jsonify({"success": False, "error": str(e)}), 500


@attendance_bp.route('/api/academic_options')
def get_academic_options():
    """Return distinct programs, branches, and batch years registered in DB."""
    try:
        struct_resp = supabase_admin.table('academic_structure').select('type, value').execute()
        rows = struct_resp.data or []
        
        programs = sorted(list({r.get('value') for r in rows if r.get('type') == 'program'}))
        branches = sorted(list({r.get('value') for r in rows if r.get('type') == 'branch'}))

        # Also fetch distinct batch years from students
        students_resp = supabase_admin.table('students').select('*').execute()
        stus = students_resp.data or []
        years = sorted(list({extract_student_year(s) for s in stus if extract_student_year(s) is not None}), reverse=True)

        return jsonify({
            "programs": programs,
            "branches": branches,
            "years": years
        })
    except Exception as e:
        import logging
        logging.getLogger(__name__).error("Error fetching academic options: %s", e, exc_info=True)
        return jsonify({
            "programs": [],
            "branches": [],
            "years": []
        })




