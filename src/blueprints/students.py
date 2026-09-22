"""
Students Blueprint (Supabase).

Routes:
  GET  /students        — list all students
  GET  /add_student     — add-student form
  POST /submit_student  — process the form, save photo, encode face
"""

import base64
import os
import cv2
import numpy as np
from flask import Blueprint, jsonify, redirect, render_template, request, send_from_directory, url_for
from werkzeug.utils import secure_filename

from src import config
from src.utils.db import supabase_admin
from src.utils.face import normalize_embedding, model
from src.utils.face_cache import add_student_to_cache

students_bp = Blueprint('students', __name__)


@students_bp.route('/students')
def students():
    try:
        # Fetch students from Supabase
        response = supabase_admin.table('students').select('id, name, program, branch, enrollment_year, gmail, current_ewma_drift, drift_alert_level').execute()
        data = response.data or []
        return render_template('students.html', students=data)
    except Exception as e:
        return render_template('students.html', students=[], error="Could not load students.")


@students_bp.route('/student/photo/<student_id>')
def student_photo(student_id):
    """Serve student photo from known_faces directory."""
    safe_id = secure_filename(student_id)
    if not safe_id:
        return jsonify({"error": "Invalid student ID"}), 400
    
    filename = f"{safe_id}.jpg"
    filepath = os.path.join(config.KNOWN_FACES_DIR, filename)
    if os.path.exists(filepath):
        return send_from_directory(config.KNOWN_FACES_DIR, filename)
    
    # Return 404 if no image exists
    return jsonify({"error": "Photo not found"}), 404


@students_bp.route('/api/student/<student_id>')
def api_get_student(student_id):
    """Fetch single student details for viewing/editing modal."""
    try:
        resp = supabase_admin.table('students').select('id, name, program, branch, enrollment_year, gmail, current_ewma_drift, drift_alert_level').eq('id', student_id).execute()
        if not resp.data:
            return jsonify({"success": False, "error": "Student not found"}), 404
        
        student = resp.data[0]
        safe_id = secure_filename(student_id)
        photo_exists = os.path.exists(os.path.join(config.KNOWN_FACES_DIR, f"{safe_id}.jpg"))
        student['has_photo'] = photo_exists
        student['photo_url'] = f"/student/photo/{student_id}" if photo_exists else None
        return jsonify({"success": True, "student": student})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@students_bp.route('/add_student')
def add_student():
    return render_template('add_student.html')


@students_bp.route('/submit_student', methods=['POST'])
def submit_student():
    """Save a new student record and encode their face embedding."""

    def _respond(status: str, message: str, http_code: int = 400):
        is_ajax = (
            request.headers.get('X-Requested-With') == 'XMLHttpRequest'
            or 'application/json' in request.headers.get('Accept', '')
            or request.is_json
        )
        if is_ajax:
            if status == 'success':
                return jsonify({"success": True, "message": message}), 200
            else:
                return jsonify({"success": False, "error": message}), http_code
        return redirect(url_for('students.add_student', status=status, message=message))

    name       = request.form.get('name', '').strip()
    student_id = request.form.get('id', '').strip()
    program    = request.form.get('program', '').strip()
    branch     = request.form.get('branch', '').strip()
    gmail      = request.form.get('email', '').strip()
    enrollment_year = request.form.get('enrollment_year', '').strip()
    academic_year   = request.form.get('academic_year', '').strip()
    photo           = request.files.get('photo')

    if not name or not student_id or not photo:
        return _respond('error', 'Name, Student ID, and Photo are required fields.', 400)

    # Check for existing student by ID
    try:
        existing = supabase_admin.table('students').select('id, name').eq('id', student_id).execute()
        if existing.data:
            existing_name = existing.data[0].get('name', 'another student')
            return _respond(
                'error',
                f'Student ID "{student_id}" is already registered in the system (assigned to {existing_name}).',
                409
            )
    except Exception as e:
        return _respond('error', f'Error checking database for existing student: {e}', 500)

    # Check for existing student by email if provided
    if gmail:
        try:
            existing_email = supabase_admin.table('students').select('id, name, gmail').eq('gmail', gmail).execute()
            if existing_email.data:
                existing_id = existing_email.data[0].get('id')
                return _respond(
                    'error',
                    f'Email address "{gmail}" is already registered to Student ID "{existing_id}".',
                    409
                )
        except Exception:
            pass

    # Save photo to known_faces/ — use secure_filename of the student_id
    safe_id = secure_filename(student_id)
    if not safe_id:
        return _respond('error', 'Student ID contains invalid characters.', 400)
    
    filename = f"{safe_id}.jpg"
    os.makedirs(config.KNOWN_FACES_DIR, exist_ok=True)
    filepath = os.path.join(config.KNOWN_FACES_DIR, filename)
    photo.save(filepath)

    # Encode the new face first
    image = cv2.imread(filepath)
    if image is None:
        return _respond('error', 'Saved photo image could not be read.', 400)

    faces = model.get(image)
    if not faces:
        return _respond('error', 'No face detected in uploaded photo. Please ensure clear lighting and position face towards camera.', 400)

    face = faces[0]
    new_emb = np.array(face.embedding, dtype=np.float32)
    normalized_emb = normalize_embedding(new_emb)
    
    if normalized_emb is None:
        return _respond('error', 'Generated face embedding is invalid or corrupted.', 400)

    # Persist student record and embedding in Supabase
    try:
        insert_data = {
            "id": student_id,
            "name": name,
            "program": program,
            "branch": branch,
            "gmail": gmail,
            "embedding": normalized_emb.tolist()
        }
        if enrollment_year:
            insert_data["enrollment_year"] = int(enrollment_year)
        if academic_year:
            insert_data["academic_year"] = academic_year

        supabase_admin.table('students').insert(insert_data).execute()

        # Auto-register new Program & Branch into academic_structure if not present
        if program:
            try:
                ex_p = supabase_admin.table('academic_structure').select('id').eq('type', 'program').eq('value', program).execute()
                if not ex_p.data:
                    supabase_admin.table('academic_structure').insert({"type": "program", "value": program}).execute()
            except Exception:
                pass

        if branch:
            try:
                ex_b = supabase_admin.table('academic_structure').select('id').eq('type', 'branch').eq('value', branch).execute()
                if not ex_b.data:
                    supabase_admin.table('academic_structure').insert({"type": "branch", "value": branch}).execute()
            except Exception:
                pass

        # Update in-memory matrix face cache
        add_student_to_cache(
            student_id=student_id,
            name=name,
            program=program,
            branch=branch,
            embedding=normalized_emb,
            enrollment_year=int(enrollment_year) if enrollment_year else None,
            academic_year=academic_year
        )
    except Exception as e:
        return _respond('error', f'Database insertion error: {e}', 500)

    return _respond('success', f'Student profile for "{name}" (ID: {student_id}) successfully registered!', 200)


@students_bp.route('/api/student/update', methods=['POST'])
@students_bp.route('/student/edit/<student_id>', methods=['POST'])
def update_student(student_id=None):
    """
    Update student details (Name, Program, Branch, Year, Gmail) and optional Photo.
    Processes multipart form or JSON payload. Re-encodes face embedding if a new photo is uploaded/captured.
    """
    is_json = request.is_json
    req_data = request.get_json() if is_json else request.form

    sid = student_id or req_data.get('id') or req_data.get('student_id')
    if not sid:
        return jsonify({"success": False, "error": "Student ID is required."}), 400

    name = req_data.get('name', '').strip()
    program = req_data.get('program', '').strip()
    branch = req_data.get('branch', '').strip()
    gmail = req_data.get('gmail') or req_data.get('email', '').strip()
    enrollment_year = req_data.get('enrollment_year', '').strip()

    if not name:
        return jsonify({"success": False, "error": "Student Name is required."}), 400

    # Prepare update payload for Supabase
    update_payload = {
        'name': name,
        'program': program,
        'branch': branch,
        'gmail': gmail
    }
    if enrollment_year:
        try:
            update_payload['enrollment_year'] = int(enrollment_year)
        except ValueError:
            pass

    safe_id = secure_filename(sid)
    if not safe_id:
        return jsonify({"success": False, "error": "Invalid Student ID."}), 400

    new_embedding = None
    photo_file = request.files.get('photo')
    photo_base64 = req_data.get('photo_base64') if is_json else request.form.get('photo_base64')

    filepath = os.path.join(config.KNOWN_FACES_DIR, f"{safe_id}.jpg")
    os.makedirs(config.KNOWN_FACES_DIR, exist_ok=True)

    # Process file upload or base64 image data if provided
    if photo_file and photo_file.filename:
        photo_file.save(filepath)
    elif photo_base64:
        try:
            if ',' in photo_base64:
                photo_base64 = photo_base64.split(',', 1)[1]
            img_bytes = base64.b64decode(photo_base64)
            with open(filepath, 'wb') as f:
                f.write(img_bytes)
        except Exception as e:
            return jsonify({"success": False, "error": f"Failed to decode photo: {e}"}), 400

    # If photo was provided (or saved), read and re-encode face
    if (photo_file and photo_file.filename) or photo_base64:
        image = cv2.imread(filepath)
        if image is None:
            return jsonify({"success": False, "error": "Uploaded photo could not be read."}), 400

        faces = model.get(image)
        if not faces:
            return jsonify({"success": False, "error": "No face detected in new photo. Please upload a clear face photo."}), 400

        face = faces[0]
        new_emb = np.array(face.embedding, dtype=np.float32)
        normalized_emb = normalize_embedding(new_emb)
        if normalized_emb is None:
            return jsonify({"success": False, "error": "Generated face embedding is invalid."}), 400

        new_embedding = normalized_emb
        update_payload['embedding'] = normalized_emb.tolist()
        update_payload['current_ewma_drift'] = 0.0
        update_payload['drift_alert_level'] = 'HEALTHY'

        # Optional drift health log event
        try:
            supabase_admin.table('embedding_health').insert({
                'student_id': sid,
                'drift_score': 0.0,
                'ewma_drift': 0.0,
                'match_confidence': 1.0,
                'alert_level': 'RE_ENROLLED',
                'pose_yaw': 0.0,
                'pose_pitch': 0.0,
                'pose_accepted': True
            }).execute()
        except Exception:
            pass

    # Update database
    try:
        supabase_admin.table('students').update(update_payload).eq('id', sid).execute()
    except Exception as e:
        return jsonify({"success": False, "error": f"Database update failed: {e}"}), 500

    # Update in-memory face cache
    if new_embedding is not None:
        add_student_to_cache(
            student_id=sid,
            name=name,
            program=program,
            branch=branch,
            embedding=new_embedding,
            enrollment_year=int(enrollment_year) if enrollment_year and enrollment_year.isdigit() else None
        )
    else:
        # If no new photo, update metadata in cache
        try:
            from src.utils.face_cache import _student_metadata, _cache_lock
            with _cache_lock:
                if sid in _student_metadata:
                    _student_metadata[sid]['name'] = name
                    _student_metadata[sid]['program'] = program
                    _student_metadata[sid]['branch'] = branch
                    if enrollment_year and enrollment_year.isdigit():
                        _student_metadata[sid]['enrollment_year'] = int(enrollment_year)
        except Exception:
            pass

    return jsonify({
        "success": True,
        "message": f"Student profile for {name} ({sid}) successfully updated!",
        "student": {
            "id": sid,
            "name": name,
            "program": program,
            "branch": branch,
            "enrollment_year": enrollment_year,
            "gmail": gmail,
            "photo_url": f"/student/photo/{sid}"
        }
    })


@students_bp.route('/api/ocr_id_card', methods=['POST'])
def api_ocr_id_card():
    """
    Process student ID card photo or OCR text payload.
    Accepts base64 image_data, uploaded id_card_image, or raw_text string.
    Returns parsed student details (name, id, program, branch, enrollment_year, email).
    """
    from src.utils.ocr_helpers import perform_python_ocr, parse_student_id_text

    raw_text = ""
    image_bytes = None

    # 1. Parse JSON payload
    if request.is_json:
        req_json = request.get_json() or {}
        raw_text = req_json.get('raw_text', '').strip()
        image_data = req_json.get('image_data', '').strip()

        if image_data:
            try:
                if ',' in image_data:
                    image_data = image_data.split(',', 1)[1]
                image_bytes = base64.b64decode(image_data)
            except Exception as e:
                print(f"Base64 image decode error: {e}")

    # 2. Parse Multipart File Upload
    if not image_bytes and 'id_card_image' in request.files:
        image_file = request.files['id_card_image']
        if image_file and image_file.filename:
            image_bytes = image_file.read()

    # 3. Form data raw_text
    if not raw_text and request.form.get('raw_text'):
        raw_text = request.form.get('raw_text', '').strip()

    # 4. Perform Python OCR on image if bytes available
    python_text = ""
    if image_bytes:
        python_text = perform_python_ocr(image_bytes)

    # Combine text from both client Tesseract.js and Python OCR
    combined_raw_text = "\n".join([t for t in [raw_text, python_text] if t])

    parsed_data = {}
    if combined_raw_text:
        parsed_data = parse_student_id_text(combined_raw_text)

    return jsonify({
        "success": True,
        "parsed_data": parsed_data,
        "raw_text": combined_raw_text or "No text recognized. Ensure image has good lighting and legible text."
    })
