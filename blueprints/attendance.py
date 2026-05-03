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
import sqlite3
from datetime import datetime

import cv2
import numpy as np
from flask import Blueprint, jsonify, render_template, request

import config
from utils.db import get_db_connection
from utils.face import (
    known_embedding_matrix,
    known_embedding_names,
    model,
)
from utils.mail import send_attendance_email as _send_email

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
        conn = sqlite3.connect(config.DB_FILE)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT Student_ID, Name, Program, Branch, Mobile, Status, Timestamp, Lecture, Section "
            "FROM attendance"
        )
        data = cursor.fetchall()
        conn.close()
        return jsonify(data)
    except Exception:
        return jsonify([])


@attendance_bp.route('/send_attendance_email', methods=['POST'])
def send_attendance_email():
    payload    = request.get_json()
    email      = payload.get('email', '').strip()
    table_data = payload.get('data', [])

    if not email or '@' not in email:
        return jsonify({'success': False, 'message': 'Invalid email address'})
    if not table_data or not isinstance(table_data, list):
        return jsonify({'success': False, 'message': 'No data received for email'})

    try:
        _send_email(email, table_data)
        return jsonify({'success': True})
    except Exception:
        return jsonify({'success': False, 'message': 'Failed to send email. Please try again later.'})


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

    # Import module-level globals lazily so we always get the current state.
    import utils.face as face_module

    conn = get_db_connection()

    # Snapshot the matrix and names once per request to avoid mid-request races.
    search_matrix = face_module.known_embedding_matrix
    search_names  = face_module.known_embedding_names

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
                embedding = np.array(face.embedding, dtype=np.float32)
                emb_norm  = np.linalg.norm(embedding)
                if emb_norm == 0:
                    continue
                embedding = embedding / emb_norm

                best_score = -1.0
                best_name  = None

                if search_matrix is not None and search_matrix.shape[0] > 0:
                    scores     = search_matrix @ embedding
                    best_idx   = int(np.argmax(scores))
                    best_score = float(scores[best_idx])
                    best_name  = search_names[best_idx]

                color = (0, 255, 0) if best_score >= config.FACE_MATCH_THRESHOLD else (0, 0, 255)
                label = best_name   if best_score >= config.FACE_MATCH_THRESHOLD else "Unknown"

                cv2.rectangle(original, (bbox[0], bbox[1]), (bbox[2], bbox[3]), color, 2)
                cv2.putText(
                    original,
                    f"{label} ({best_score:.2f})",
                    (bbox[0], bbox[1] - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2,
                )

                if best_score < config.FACE_MATCH_THRESHOLD:
                    results.append({
                        "name": "Unknown",
                        "status": "Unknown",
                        "confidence": f"{best_score:.2f}",
                    })
                    continue

                student = conn.execute(
                    'SELECT * FROM students WHERE Name=?', (best_name,)
                ).fetchone()
                if not student:
                    results.append({
                        "name": best_name,
                        "status": "Not Found",
                        "confidence": f"{best_score:.2f}",
                    })
                    continue

                last_mark = conn.execute(
                    "SELECT Timestamp FROM attendance WHERE Student_ID=? "
                    "ORDER BY Timestamp DESC LIMIT 1",
                    (student['ID'],),
                ).fetchone()

                remark = False
                if last_mark:
                    last_time = datetime.strptime(last_mark['Timestamp'], "%Y-%m-%d %H:%M:%S")
                    elapsed   = (now - last_time).total_seconds() / 60
                    if elapsed < config.REATTENDANCE_INTERVAL_MINUTES:
                        results.append({
                            "name":       best_name,
                            "status":     "Already Marked",
                            "confidence": f"{best_score:.2f}",
                            "timestamp":  last_time.strftime("%Y-%m-%d %H:%M:%S"),
                        })
                        continue
                    else:
                        remark = True

                status = 'Re-Marked' if remark else 'Present'

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

                results.append({
                    "name":       best_name,
                    "status":     status,
                    "confidence": f"{best_score:.2f}",
                    "timestamp":  timestamp,
                })
                session_attend.append([
                    student['ID'], student['Name'], student['Program'],
                    student['Branch'], student['Mobile'],
                    status, timestamp, lecture, section,
                ])

        _, buf = cv2.imencode('.jpg', original)
        encoded_img = base64.b64encode(buf).decode('utf-8')
        all_outputs.append({
            "results":   results,
            "annotated": f"data:image/jpeg;base64,{encoded_img}",
        })

    conn.close()
    return jsonify({"images": all_outputs, "session_attendance": session_attend})
