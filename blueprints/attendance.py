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

import cv2
import numpy as np
from flask import Blueprint, jsonify, render_template, request

import config
from utils.db import supabase
from utils.face import model, normalize_embedding

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
        # Fetch all attendance records from Supabase
        response = supabase.table('attendance').select('student_id, name, program, branch, mobile, status, timestamp, lecture, section').execute()
        # Convert list of dicts to list of tuples if frontend expects tuples
        # The existing frontend expects tuples since it used cursor.fetchall()
        # Looking at original code: it returned data = cursor.fetchall(), which was serialized to JSON
        # A list of dictionaries might break frontend JS if it expects arrays: row[0], row[1]
        # Let's format it as list of lists/tuples to be safe
        data = []
        for row in response.data:
            data.append([
                row.get('student_id', ''),
                row.get('name', ''),
                row.get('program', ''),
                row.get('branch', ''),
                row.get('mobile', ''),
                row.get('status', ''),
                row.get('timestamp', ''),
                row.get('lecture', ''),
                row.get('section', '')
            ])
        return jsonify(data)
    except Exception as e:
        print("Error fetching attendance:", e)
        return jsonify([])




@attendance_bp.route('/upload_photo', methods=['POST'])
def upload_photo():
    if 'images' not in request.files:
        return jsonify({"images": [], "session_attendance": []})

    lecture = request.form.get('lecture', '').strip()
    section = request.form.get('section', '').strip()
    files   = request.files.getlist('images')

    now       = datetime.now()
    timestamp = now.strftime("%Y-%m-%d %H:%M:%S")

    all_outputs      = []
    session_attend   = []


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
                student_data = []

                try:
                    match_resp = supabase.rpc('match_face', {
                        'query_embedding': embedding.tolist(),
                        'match_threshold': config.FACE_MATCH_THRESHOLD
                    }).execute()
                    match_data = match_resp.data
                except Exception as e:
                    print(f"Error matching face via pgvector: {e}")
                    match_data = []

                if match_data and len(match_data) > 0:
                    best_match = match_data[0]
                    best_score = float(best_match['similarity'])
                    best_name = best_match['name']
                    # We also need the full student data for the attendance log
                    try:
                        student_resp = supabase.table('students').select('*').eq('id', best_match['id']).execute()
                        student_data = student_resp.data
                    except Exception:
                        student_data = []
                
                color = (0, 255, 0) if best_score >= config.FACE_MATCH_THRESHOLD else (0, 0, 255)
                label = best_name if best_name else "Unknown"

                cv2.rectangle(original, (bbox[0], bbox[1]), (bbox[2], bbox[3]), color, 2)
                cv2.putText(
                    original,
                    f"{label} ({best_score:.2f})",
                    (bbox[0], bbox[1] - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2,
                )

                if not best_name or best_score < config.FACE_MATCH_THRESHOLD:
                    results.append({
                        "name": "Unknown",
                        "status": "Unknown",
                        "confidence": f"{best_score:.2f}" if best_score > 0 else "0.00",
                    })
                    continue

                if not student_data:
                    results.append({
                        "name": best_name,
                        "status": "Not Found",
                        "confidence": f"{best_score:.2f}",
                    })
                    continue
                
                student = student_data[0]

                # Check last attendance record for this student and lecture
                try:
                    last_record_resp = supabase.table('attendance').select('timestamp').eq('student_id', student['id']).eq('lecture', lecture).order('timestamp', desc=True).limit(1).execute()
                    last_record_data = last_record_resp.data
                except Exception:
                    last_record_data = []

                if last_record_data:
                    last_time_str = last_record_data[0]['timestamp']
                    try:
                        last_time = datetime.strptime(last_time_str, "%Y-%m-%d %H:%M:%S")
                        elapsed   = (now - last_time).total_seconds() / 60
                        if elapsed < config.REATTENDANCE_INTERVAL_MINUTES:
                            results.append({
                                "name":       best_name,
                                "status":     "Already Marked",
                                "confidence": f"{best_score:.2f}",
                                "timestamp":  last_time_str,
                            })
                            continue
                    except ValueError:
                        pass # Ignore parsing errors for timestamp format mismatches

                status = 'Present'

                # Insert attendance record into Supabase
                try:
                    supabase.table('attendance').insert({
                        "student_id": student.get('id'),
                        "name": student.get('name'),
                        "program": student.get('program'),
                        "branch": student.get('branch'),
                        "mobile": student.get('mobile'),
                        "status": status,
                        "timestamp": timestamp,
                        "lecture": lecture,
                        "section": section
                    }).execute()
                except Exception as e:
                    print(f"Failed to insert attendance for {best_name}: {e}")

                results.append({
                    "name":       best_name,
                    "status":     status,
                    "confidence": f"{best_score:.2f}",
                    "timestamp":  timestamp,
                })
                session_attend.append([
                    student.get('id'), student.get('name'), student.get('program'),
                    student.get('branch'), student.get('mobile'),
                    status, timestamp, lecture, section,
                ])

        _, buf = cv2.imencode('.jpg', original)
        encoded_img = base64.b64encode(buf).decode('utf-8')
        all_outputs.append({
            "results":   results,
            "annotated": f"data:image/jpeg;base64,{encoded_img}",
        })

    return jsonify({"images": all_outputs, "session_attendance": session_attend})
