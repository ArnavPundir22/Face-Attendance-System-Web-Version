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

from src import config
from src.utils.db import supabase
from src.utils.face import model, normalize_embedding

attendance_bp = Blueprint('attendance', __name__)


@attendance_bp.route('/')
def index():
    return render_template('index.html')


@attendance_bp.route('/viewer')
def viewer():
    return render_template('viewer.html')


@attendance_bp.route('/get_attendance_data')
def get_attendance_data():
    try:
        # Fetch logs from the last 7 days to ensure query size is under payload caps
        seven_days_ago = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d %H:%M:%S")
        response = supabase.table('attendance')\
            .select('student_id, name, program, branch, status, timestamp, lecture')\
            .gte('timestamp', seven_days_ago)\
            .order('timestamp', desc=True)\
            .limit(4000)\
            .execute()
        data = []
        for row in response.data:
            data.append([
                row.get('student_id', ''),
                row.get('name', ''),
                row.get('program', ''),
                row.get('branch', ''),
                row.get('status', ''),
                row.get('timestamp', ''),
                row.get('lecture', '')
            ])
            
        # Fetch all registered students
        students_resp = supabase.table('students').select('id, name, branch, program').execute()
        students_list = students_resp.data or []
        
        return jsonify({
            "attendance": data,
            "students": students_list
        })
    except Exception as e:
        print("Error fetching attendance data:", e)
        return jsonify({"attendance": [], "students": []})




@attendance_bp.route('/upload_photo', methods=['POST'])
def upload_photo():
    if 'images' not in request.files:
        return jsonify({"images": [], "session_attendance": [], "detected_program": None, "detected_branch": None})

    lecture = request.form.get('lecture', '').strip()
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
                    match_resp = supabase.rpc('match_face', rpc_params).execute()
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
                        match_resp = supabase.rpc('match_face', raw_rpc_params).execute()
                        match_data = match_resp.data
                except Exception as e:
                    print(f"Error matching face via pgvector: {e}")
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
                    results.append({
                        "name": best_name,
                        "status": "Present",
                        "confidence": f"{best_score:.2f}",
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

    # Auto-detect program and branch based on recognized student IDs
    detected_program = None
    detected_branch = None
    all_students = []

    if recognized_ids:
        try:
            rec_students_resp = supabase.table('students').select('id, program, branch').in_('id', list(recognized_ids)).execute()
            rec_students = rec_students_resp.data or []
            
            from collections import Counter
            combinations = []
            for s in rec_students:
                p = s.get('program')
                b = s.get('branch')
                if p and b:
                    combinations.append((p, b))
            
            if combinations:
                most_common = Counter(combinations).most_common(1)[0][0]
                detected_program = most_common[0]
                detected_branch = most_common[1]
        except Exception as e:
            print(f"Error in class auto-detection: {e}")

    # Fallback to general default values or keep them empty if absolutely no match
    if not detected_program or not detected_branch:
        detected_program = request.form.get('program', '').strip()
        detected_branch  = request.form.get('branch', '').strip()

    if detected_program and detected_branch:
        try:
            students_resp = supabase.table('students').select('*').ilike('program', detected_program).ilike('branch', detected_branch).execute()
            all_students = students_resp.data or []
        except Exception as e:
            print(f"Error fetching students for detected class: {e}")

    # Prepare bulk attendance records for ALL registered students in the auto-detected program & branch
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
            insert_resp = supabase.table('attendance').insert(attendance_records).execute()
            print("Successfully inserted logs:", len(insert_resp.data or []))
        except Exception as e:
            print(f"Failed to insert bulk attendance: {e}")
            raise e

    return jsonify({
        "images": all_outputs,
        "session_attendance": session_attend,
        "detected_program": detected_program,
        "detected_branch": detected_branch
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
        existing = supabase.table('attendance').select('att_id').eq('student_id', student_id).eq('lecture', lecture).eq('timestamp', timestamp).execute()
        
        if existing.data:
            supabase.table('attendance').update({"status": status}).eq('student_id', student_id).eq('lecture', lecture).eq('timestamp', timestamp).execute()
        else:
            # Fetch student details for a complete attendance insert
            student_resp = supabase.table('students').select('*').eq('id', student_id).execute()
            if student_resp.data:
                student = student_resp.data[0]
                supabase.table('attendance').insert({
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
        print(f"Error updating/inserting attendance status: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@attendance_bp.route('/api/academic_options')
def get_academic_options():
    """Return distinct programs and branches registered in DB."""
    try:
        struct_resp = supabase.table('academic_structure').select('type, value').execute()
        rows = struct_resp.data or []
        
        programs = sorted(list({r.get('value') for r in rows if r.get('type') == 'program'}))
        branches = sorted(list({r.get('value') for r in rows if r.get('type') == 'branch'}))

        return jsonify({
            "programs": programs,
            "branches": branches
        })
    except Exception as e:
        print("Error fetching academic options:", e)
        return jsonify({
            "programs": [],
            "branches": []
        })



