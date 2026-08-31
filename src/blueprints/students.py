"""
Students Blueprint (Supabase).

Routes:
  GET  /students        — list all students
  GET  /add_student     — add-student form
  POST /submit_student  — process the form, save photo, encode face
"""

import os
import cv2
import numpy as np
from flask import Blueprint, redirect, render_template, request, url_for
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
        response = supabase_admin.table('students').select('id, name, program, branch, enrollment_year, gmail').execute()
        data = response.data
        return render_template('students.html', students=data)
    except Exception as e:
        return render_template('students.html', students=[], error="Could not load students.")


@students_bp.route('/add_student')
def add_student():
    return render_template('add_student.html')


@students_bp.route('/submit_student', methods=['POST'])
def submit_student():
    """Save a new student record and encode their face embedding."""
    name       = request.form.get('name', '').strip()
    student_id = request.form.get('id', '').strip()
    program    = request.form.get('program', '').strip()
    branch     = request.form.get('branch', '').strip()
    gmail      = request.form.get('email', '').strip()
    enrollment_year = request.form.get('enrollment_year', '').strip()
    academic_year   = request.form.get('academic_year', '').strip()
    photo           = request.files.get('photo')

    if not name or not student_id or not photo:
        return redirect(url_for(
            'students.add_student', status='error',
            message='Name, ID and Photo are required',
        ))

    # Check for existing student
    try:
        # Check by exact ID only to allow same-name students
        existing = supabase_admin.table('students').select('id').eq('id', student_id).execute()
        if existing.data:
            return redirect(url_for(
                'students.add_student', status='error',
                message='Duplicate Student ID found',
            ))
    except Exception as e:
        return redirect(url_for(
            'students.add_student', status='error',
            message='Error checking existing students',
        ))

    # Save photo to known_faces/ — use secure_filename of the student_id to prevent path traversal and name collisions.
    safe_id = secure_filename(student_id)
    if not safe_id:
        return redirect(url_for(
            'students.add_student', status='error',
            message='Student ID contains invalid characters',
        ))
    filename = f"{safe_id}.jpg"
    filepath = os.path.join(config.KNOWN_FACES_DIR, filename)
    photo.save(filepath)

    # Encode the new face first
    image = cv2.imread(filepath)
    if image is None:
        return redirect(url_for(
            'students.add_student', status='error',
            message='Saved image could not be read',
        ))

    faces = model.get(image)
    if not faces:
        return redirect(url_for(
            'students.add_student', status='error',
            message='No face detected in uploaded image',
        ))

    face = faces[0]
    new_emb = np.array(face.embedding, dtype=np.float32)
    normalized_emb = normalize_embedding(new_emb)
    
    if normalized_emb is None:
        return redirect(url_for(
            'students.add_student', status='error',
            message='Generated embedding is invalid',
        ))

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
        return redirect(url_for(
            'students.add_student', status='error',
            message='Database error while adding student',
        ))



    return redirect(url_for(
        'students.add_student', status='success',
        message=f'{name} added successfully with 1 encoding',
    ))
