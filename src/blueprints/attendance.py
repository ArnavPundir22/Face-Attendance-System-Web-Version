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
from datetime import datetime
import logging
import re
import threading
import time

import cv2
import numpy as np
from flask import Blueprint, jsonify, render_template, request

from src import config
from src.utils.db import supabase_admin, is_valid_email, fetch_all_records
from src.utils.face import extract_faces, normalize_embedding
from src.utils.logger import log_audit, log_biometric
from src.utils.face_cache import (
    match_faces_batch,
    get_student_ewma,
    update_cached_student_drift,
    get_cached_students,
    get_cached_student_metadata,
    is_cache_populated
)

logger = logging.getLogger(__name__)

attendance_bp = Blueprint('attendance', __name__)


def extract_student_year(student_dict: dict):
    """Extract or derive the 4-digit enrollment/batch year for a student."""
    if not student_dict:
        return None
    
    # 1. Check explicit enrollment_year column first
    ey = student_dict.get('enrollment_year')
    if ey is not None and str(ey).strip().isdigit():
        val = int(str(ey).strip())
        if 1900 <= val <= 2100:
            return val

    # 2. Check academic_year column
    ay = student_dict.get('academic_year')
    if ay:
        match = re.search(r'\b(20\d{2})\b', str(ay))
        if match:
            return int(match.group(1))

    # 3. Derive from student ID prefix (e.g. CU240251013 -> 2024, CU26250073 -> 2026)
    sid = str(student_dict.get('id', '')).strip()
    if sid:
        match = re.match(r'(?i)^(?:cu|ci)?(\d{2})', sid)
        if match:
            two_digit = match.group(1)
            val = int(two_digit)
            if 15 <= val <= 35:
                return int(f"20{two_digit}")

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


def _compute_drift_event(student_id: str, cosine_sim: float, pose_yaw: float, pose_pitch: float):
    """
    In-memory Pose-Gated EWMA calculation for template health tracking.
    Runs with ZERO network latency by utilizing cached EWMA values.
    Returns (drift_info, health_log_dict, student_update_dict, email_tuple).
    """
    pose_accepted = (
        abs(pose_yaw)   <= config.DRIFT_POSE_YAW_MAX and
        abs(pose_pitch) <= config.DRIFT_POSE_PITCH_MAX
    )

    try:
        if pose_accepted:
            drift_score = 1.0 - cosine_sim
            prev_ewma = get_student_ewma(student_id)
            new_ewma = config.DRIFT_ALPHA * drift_score + (1.0 - config.DRIFT_ALPHA) * prev_ewma
            alert_level = _compute_drift_level(new_ewma)
            update_cached_student_drift(student_id, new_ewma, alert_level)

            health_log = {
                'student_id':       student_id,
                'drift_score':      round(drift_score, 6),
                'ewma_drift':       round(new_ewma,    6),
                'match_confidence': round(cosine_sim,  6),
                'alert_level':      alert_level,
                'pose_yaw':         round(pose_yaw,    2),
                'pose_pitch':       round(pose_pitch,  2),
                'pose_accepted':    True,
            }
            student_update = {
                'current_ewma_drift': round(new_ewma, 6),
                'drift_alert_level':  alert_level,
            }
            email_tuple = (student_id, alert_level, new_ewma) if alert_level in ('CRITICAL', 'ALERT') else None
            drift_info = {'pose_accepted': True, 'alert_level': alert_level, 'ewma_drift': round(new_ewma, 4)}
            return drift_info, health_log, student_update, email_tuple
        else:
            health_log = {
                'student_id':       student_id,
                'drift_score':      None,
                'ewma_drift':       None,
                'match_confidence': round(cosine_sim, 6),
                'alert_level':      'POSE_REJECTED',
                'pose_yaw':         round(pose_yaw,   2),
                'pose_pitch':       round(pose_pitch,  2),
                'pose_accepted':    False,
            }
            drift_info = {'pose_accepted': False, 'alert_level': 'POSE_REJECTED', 'ewma_drift': None}
            return drift_info, health_log, None, None
    except Exception as exc:
        logger.warning('Drift calculation error for %s: %s', student_id, exc)
        return {'pose_accepted': pose_accepted, 'alert_level': 'UNKNOWN', 'ewma_drift': None}, None, None, None


def _update_drift(student_id: str, cosine_sim: float, pose_yaw: float, pose_pitch: float) -> dict:
    """Async wrapper for single drift update events (backward compatibility)."""
    drift_info, health_log, student_update, email_tuple = _compute_drift_event(student_id, cosine_sim, pose_yaw, pose_pitch)
    def _save():
        if health_log:
            try:
                supabase_admin.table('embedding_health').insert(health_log, returning='minimal').execute()
            except Exception:
                pass
        if student_update:
            try:
                supabase_admin.table('students').update(student_update, returning='minimal').eq('id', student_id).execute()
            except Exception:
                pass
        if email_tuple:
            _send_drift_email_alert(*email_tuple)
    threading.Thread(target=_save, daemon=True).start()
    return drift_info


@attendance_bp.route('/')
def index():
    return render_template('index.html')


@attendance_bp.route('/viewer')
def viewer():
    return render_template('viewer.html')


@attendance_bp.route('/get_attendance_data')
def get_attendance_data():
    try:
        # Fetch registered students: prefer in-memory cache if populated and not monkeypatched
        if is_cache_populated() and getattr(fetch_all_records, '__module__', None) == 'src.utils.db':
            stus = get_cached_students()
        else:
            stus = fetch_all_records(
                client=supabase_admin,
                table_name='students',
                select_fields='id, name, branch, program, enrollment_year, academic_year'
            )
        student_year_map = {}
        students_list = []
        for s in stus:
            s_dict = dict(s)
            y = extract_student_year(s_dict)
            s_dict['batch_year'] = y
            students_list.append(s_dict)
            if s.get('id'):
                student_year_map[str(s.get('id')).strip().upper()] = str(y) if y else ''

        # Date and limit filtering to reduce egress
        filter_date = request.args.get('date', '').strip()
        limit_param = request.args.get('limit', type=int)
        query_limit = min(limit_param, 4000) if (limit_param and limit_param > 0) else 4000

        # Fetch attendance records ordered descending
        try:
            query = supabase_admin.table('attendance')\
                .select('att_id, student_id, name, program, branch, status, timestamp, lecture')\
                .order('att_id', desc=True)
            if filter_date:
                query = query.ilike('timestamp', f'{filter_date}%')
            response = query.limit(query_limit).execute()
        except Exception:
            query = supabase_admin.table('attendance')\
                .select('student_id, name, program, branch, status, timestamp, lecture')\
                .order('timestamp', desc=True)
            if filter_date:
                query = query.ilike('timestamp', f'{filter_date}%')
            response = query.limit(query_limit).execute()
        data = []
        for row in (response.data or []):
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
        logger.error("Error fetching attendance data: %s", e, exc_info=True)
        return jsonify({"attendance": [], "students": []})





@attendance_bp.route('/upload_photo', methods=['POST'])
def upload_photo():
    if 'images' not in request.files:
        return jsonify({"images": [], "session_attendance": [], "detected_program": None, "detected_branch": None, "detected_year": None})

    start_time = time.perf_counter()
    lecture = request.form.get('lecture', '').strip()
    if not lecture:
        lecture = f"Session {datetime.now().strftime('%Y-%m-%d %H:%M')}"

    files   = request.files.getlist('images')

    now       = datetime.now()
    timestamp = now.strftime("%Y-%m-%d %H:%M:%S")

    total_detected_faces = 0
    total_matched_faces = 0
    total_unknown_faces = 0

    recognized_ids = set()
    all_outputs      = []
    confidence_map   = {}
    pending_health_logs = []
    pending_student_updates = {}
    pending_email_alerts = []

    for file in files:
        npimg  = np.frombuffer(file.read(), np.uint8)
        frame  = cv2.imdecode(npimg, cv2.IMREAD_COLOR)
        if frame is None:
            all_outputs.append({"results": [], "annotated": ""})
            continue

        original = frame.copy()
        faces    = extract_faces(frame)
        results  = []

        if faces:
            total_detected_faces += len(faces)
            # 1. Batch extract and normalize all face embeddings for this image
            face_embeddings = [np.array(face.embedding, dtype=np.float32) for face in faces]
            
            # 2. Ultra-fast BLAS in-memory batch matrix matching (< 1ms on CPU)
            batch_matches = match_faces_batch(face_embeddings)

            for idx, face in enumerate(faces):
                bbox = [int(v) for v in face.bbox]
                match = batch_matches[idx]

                # Fallback to Supabase RPC if in-memory match returned None
                if not match:
                    new_emb = face_embeddings[idx]
                    embedding = normalize_embedding(new_emb)
                    if embedding is not None:
                        try:
                            rpc_params = {
                                'query_embedding': embedding.tolist(),
                                'match_threshold': config.FACE_MATCH_THRESHOLD,
                                'filter_program': None,
                                'filter_branch': None,
                                'filter_section': None
                            }
                            match_resp = supabase_admin.rpc('match_face', rpc_params).execute()
                            if match_resp.data:
                                best_m = match_resp.data[0]
                                match = {
                                    'id': best_m['id'],
                                    'name': best_m['name'],
                                    'similarity': float(best_m['similarity'])
                                }
                        except Exception as e:
                            logger.error("Fallback match_face error: %s", e)

                best_score = match['similarity'] if match else -1.0
                best_name = match['name'] if match else None
                matched_id = match['id'] if match else None

                color = (0, 255, 0) if (matched_id and best_score >= config.FACE_MATCH_THRESHOLD) else (0, 0, 255)
                label = best_name if best_name else "Unknown"

                cv2.rectangle(original, (bbox[0], bbox[1]), (bbox[2], bbox[3]), color, 2)
                cv2.putText(
                    original,
                    f"{label} ({best_score:.2f})",
                    (bbox[0], bbox[1] - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2,
                )

                if matched_id and best_score >= config.FACE_MATCH_THRESHOLD:
                    total_matched_faces += 1
                    recognized_ids.add(matched_id)
                    confidence_map[matched_id] = best_score

                    # ── Fast In-Memory Pose-Gated Drift Engine ───────────────────────
                    pose_yaw   = float(face.pose[1]) if (hasattr(face, 'pose') and face.pose is not None) else 0.0
                    pose_pitch = float(face.pose[0]) if (hasattr(face, 'pose') and face.pose is not None) else 0.0
                    drift_info, h_log, s_update, e_alert = _compute_drift_event(matched_id, best_score, pose_yaw, pose_pitch)
                    if h_log:
                        pending_health_logs.append(h_log)
                    if s_update:
                        pending_student_updates[matched_id] = s_update
                    if e_alert:
                        pending_email_alerts.append(e_alert)
                    # ─────────────────────────────────────────────────────────────────

                    results.append({
                        'name':       best_name,
                        'status':     'Present',
                        'confidence': f'{best_score:.2f}',
                        'drift_alert': drift_info['alert_level'],
                        'pose_accepted': drift_info['pose_accepted'],
                    })
                else:
                    total_unknown_faces += 1
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
            cached_found = []
            missing_ids = []
            for rid in recognized_ids:
                meta = get_cached_student_metadata(rid)
                if meta and meta.get('id'):
                    cached_found.append(meta)
                else:
                    missing_ids.append(rid)

            if missing_ids:
                rec_students_resp = supabase_admin.table('students').select('id, name, program, branch, enrollment_year, academic_year, gmail').in_('id', missing_ids).execute()
                rec_students = cached_found + (rec_students_resp.data or [])
            else:
                rec_students = cached_found
            
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
            logger.error("Error in class auto-detection: %s", e)

    # Read attendance mode (Combined Class vs Separate Class)
    is_combined_class = request.form.get('is_combined_class', 'false').lower() == 'true'

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

    if is_combined_class:
        # ── COMBINED CLASS MODE ────────────────────────────────────────────────
        # Fetch rosters for ALL program & branch combinations represented among recognized students
        combined_students = []
        represented_pbs = set()
        represented_years = set()

        for s in rec_students:
            p = s.get('program')
            b = s.get('branch')
            y = extract_student_year(s)
            if p and b:
                represented_pbs.add((p.strip(), b.strip()))
            if y is not None:
                represented_years.add(y)

        if represented_pbs:
            for p, b in represented_pbs:
                try:
                    p_clean = p.strip().lower()
                    b_clean = b.strip().lower()
                    if is_cache_populated():
                        raw = [
                            s for s in get_cached_students()
                            if (s.get('program') or '').strip().lower() == p_clean
                            and (s.get('branch') or '').strip().lower() == b_clean
                        ]
                    else:
                        resp = supabase_admin.table('students').select('id, name, program, branch, enrollment_year, academic_year, gmail').ilike('program', p).ilike('branch', b).execute()
                        raw = resp.data or []
                    if represented_years:
                        filtered_raw = [s for s in raw if extract_student_year(s) in represented_years]
                    else:
                        filtered_raw = raw
                    combined_students.extend(filtered_raw if filtered_raw else raw)
                except Exception as e:
                    logger.error("Error fetching roster for combined class (%s, %s): %s", p, b, e)

        # Remove duplicate students by ID
        unique_combined = []
        seen_ids = set()
        for s in combined_students:
            sid = str(s.get('id')).strip().upper() if s.get('id') else None
            if sid and sid not in seen_ids:
                seen_ids.add(sid)
                unique_combined.append(s)

        all_students = unique_combined
        if not all_students and rec_students:
            all_students = rec_students

        distinct_branches = sorted(list({s.get('branch') for s in all_students if s.get('branch')}))
        detected_program = "Combined Class"
        detected_branch  = ", ".join(distinct_branches) if distinct_branches else "Multi-Branch"
        detected_year    = "Combined"
    else:
        # ── SEPARATE CLASS MODE (Single Group Focus) ─────────────────────────
        if detected_program and detected_branch:
            try:
                p_clean = detected_program.strip().lower()
                b_clean = detected_branch.strip().lower()
                if is_cache_populated():
                    raw_students = [
                        s for s in get_cached_students()
                        if (s.get('program') or '').strip().lower() == p_clean
                        and (s.get('branch') or '').strip().lower() == b_clean
                    ]
                else:
                    students_resp = supabase_admin.table('students').select('id, name, program, branch, enrollment_year, academic_year, gmail').ilike('program', detected_program).ilike('branch', detected_branch).execute()
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
                logger.error("Error fetching students for detected class: %s", e)

        # Fallback: If class query yielded no results but we recognized student(s), use recognized list
        if not all_students and rec_students:
            all_students = rec_students

    if is_combined_class:
        # In Combined Class Mode, ensure all recognized students are present in all_students
        existing_student_ids = {str(s.get('id')).strip().upper() for s in all_students if s.get('id')}
        for rs in rec_students:
            rs_id = str(rs.get('id')).strip().upper() if rs.get('id') else None
            if rs_id and rs_id not in existing_student_ids:
                all_students.append(rs)
                existing_student_ids.add(rs_id)
    else:
        # In Separate Class Mode, strictly enforce class boundary filtering
        # Ensure only students matching the target program, branch, and batch year are included
        if detected_program and detected_branch and detected_year is not None:
            filtered_target = []
            for s in all_students:
                prog_match = str(s.get('program', '')).strip().upper() == str(detected_program).strip().upper()
                bran_match = str(s.get('branch', '')).strip().upper() == str(detected_branch).strip().upper()
                year_match = extract_student_year(s) == detected_year
                if prog_match and bran_match and year_match:
                    filtered_target.append(s)
            all_students = filtered_target

    # Prepare bulk attendance records for ALL registered students in the detected class / combined rosters
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
            insert_resp = supabase_admin.table('attendance').insert(attendance_records, returning='minimal').execute()
            import logging
            logging.getLogger(__name__).info("Successfully inserted logs: %d", len(attendance_records))
        except Exception as e:
            import logging
            logging.getLogger(__name__).error("Failed to insert bulk attendance: %s", e, exc_info=True)

    # ── Non-blocking background persistence of drift logs and alert emails ────
    if pending_health_logs or pending_student_updates or pending_email_alerts:
        import threading
        def _async_persist_drift(h_logs, s_updates, emails):
            # 1. Bulk insert all health logs in 1 single HTTP request
            if h_logs:
                try:
                    supabase_admin.table('embedding_health').insert(h_logs, returning='minimal').execute()
                except Exception as err:
                    import logging
                    logging.getLogger(__name__).warning("Async bulk health logs insert failed: %s", err)

            # 2. Update students table drift scores
            for sid, u_data in s_updates.items():
                try:
                    supabase_admin.table('students').update(u_data, returning='minimal').eq('id', sid).execute()
                except Exception as err:
                    import logging
                    logging.getLogger(__name__).warning("Async student drift update failed for %s: %s", sid, err)

            # 3. Dispatch alert emails
            for sid, a_lvl, ewma in emails:
                try:
                    _send_drift_email_alert(sid, a_lvl, ewma)
                except Exception as err:
                    import logging
                    logging.getLogger(__name__).warning("Async email alert failed for %s: %s", sid, err)

        threading.Thread(
            target=_async_persist_drift,
            args=(pending_health_logs, pending_student_updates, pending_email_alerts),
            daemon=True
        ).start()
    # ─────────────────────────────────────────────────────────────────────────

    latency_ms = (time.perf_counter() - start_time) * 1000.0
    log_biometric(
        images=len(files),
        detected=total_detected_faces,
        matched=total_matched_faces,
        unknown=total_unknown_faces,
        latency_ms=latency_ms,
        lecture=lecture,
    )

    return jsonify({
        "images": all_outputs,
        "session_attendance": session_attend,
        "detected_program": detected_program,
        "detected_branch": detected_branch,
        "detected_year": detected_year,
        "is_combined_class": is_combined_class
    })


@attendance_bp.route('/update_attendance_status', methods=['POST'])
def update_attendance_status():
    data = request.get_json() or {}
    student_id = str(data.get('student_id') or '').strip()
    lecture = str(data.get('lecture') or '').strip()
    timestamp = str(data.get('timestamp') or '').strip()
    status = str(data.get('status') or '').strip()
    
    if not student_id or not timestamp or not status:
        return jsonify({"success": False, "error": "Missing parameters"}), 400
        
    try:
        # Check if record already exists for this student and timestamp
        query = supabase_admin.table('attendance').select('att_id, lecture').eq('student_id', student_id).eq('timestamp', timestamp)
        if lecture:
            query = query.eq('lecture', lecture)
        existing = query.execute()
        
        # If not found with specific lecture, try matching by student_id and timestamp only
        if not existing.data and lecture:
            existing = supabase_admin.table('attendance').select('att_id, lecture').eq('student_id', student_id).eq('timestamp', timestamp).execute()

        if existing.data:
            existing_rec = existing.data[0]
            eff_lecture = lecture or existing_rec.get('lecture') or 'General'
            update_payload = {"status": status}
            if eff_lecture:
                update_payload["lecture"] = eff_lecture
            supabase_admin.table('attendance').update(update_payload, returning='minimal').eq('att_id', existing_rec['att_id']).execute()
        else:
            # If lecture wasn't provided, infer lecture from existing logs for the same timestamp session
            if not lecture:
                session_logs = supabase_admin.table('attendance').select('lecture').eq('timestamp', timestamp).limit(1).execute()
                if session_logs.data and session_logs.data[0].get('lecture'):
                    lecture = session_logs.data[0].get('lecture')
                else:
                    lecture = 'General'

            # Fetch student details for a complete attendance insert
            student_resp = supabase_admin.table('students').select('id, name, program, branch, enrollment_year, academic_year, gmail').eq('id', student_id).execute()
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
                }, returning='minimal').execute()
            else:
                return jsonify({"success": False, "error": "Student not found in directory"}), 404

        eff_lec = lecture or (existing.data[0].get('lecture') if existing.data else 'General')
        log_audit(
            action="ATTENDANCE_OVERRIDE",
            target=student_id,
            status="SUCCESS",
            details=f"Status changed to {status} for lecture '{eff_lec}' at {timestamp}",
        )
        return jsonify({"success": True})
    except Exception as e:
        logger.error("Error updating/inserting attendance status: %s", e, exc_info=True)
        log_audit(
            action="ATTENDANCE_OVERRIDE",
            target=student_id,
            status="FAILED",
            details=str(e),
        )
        return jsonify({"success": False, "error": str(e)}), 500


@attendance_bp.route('/api/academic_options')
def get_academic_options():
    """Return distinct programs, branches, and batch years registered in DB."""
    try:
        struct_resp = supabase_admin.table('academic_structure').select('type, value').execute()
        rows = struct_resp.data or []
        
        programs = sorted(list({r.get('value') for r in rows if r.get('type') == 'program'}))
        branches = sorted(list({r.get('value') for r in rows if r.get('type') == 'branch'}))

        # Also fetch distinct batch years: prefer in-memory cache if populated and not monkeypatched
        if is_cache_populated() and getattr(fetch_all_records, '__module__', None) == 'src.utils.db':
            stus = get_cached_students()
        else:
            stus = fetch_all_records(
                client=supabase_admin,
                table_name='students',
                select_fields='id, enrollment_year, academic_year'
            )
        years = sorted(list({extract_student_year(s) for s in stus if extract_student_year(s) is not None}), reverse=True)

        return jsonify({
            "programs": programs,
            "branches": branches,
            "years": years
        })
    except Exception as e:
        logger.error("Error fetching academic options: %s", e, exc_info=True)
        return jsonify({
            "programs": [],
            "branches": [],
            "years": []
        })




