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

import config
from utils.db import supabase
from utils.face import normalize_embedding, model

students_bp = Blueprint('students', __name__)

@students_bp.route('/students')
def students():
    try:
        # Fetch students from Supabase
        response = supabase.table('students').select('id, name, program, branch, mobile, gmail').execute()
        # The frontend templates might expect tuple-like access if they used Row factory,
        # but supabase returns a list of dicts. We should format it correctly for the template.
        # e.g. student['id'], student['name'] - which dict already supports!
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
    mobile     = request.form.get('mobile', '').strip()
    gmail      = request.form.get('email', '').strip()
    photo      = request.files.get('photo')

    if not name or not student_id or not photo:
        return redirect(url_for(
            'students.add_student', status='error',
            message='Name, ID and Photo are required',
        ))

    # Check for existing student
    try:
        # Check by exact ID or case-insensitive Name
        existing = supabase.table('students').select('id').or_(f"id.eq.{student_id},name.ilike.{name}").execute()
        if existing.data:
            return redirect(url_for(
                'students.add_student', status='error',
                message='Duplicate Name or ID found',
            ))
    except Exception as e:
        return redirect(url_for(
            'students.add_student', status='error',
            message='Error checking existing students',
        ))

    # Save photo to known_faces/ — use secure_filename to prevent path traversal.
    safe_name = secure_filename(name)
    if not safe_name:
        return redirect(url_for(
            'students.add_student', status='error',
            message='Student name contains invalid characters',
        ))
    filename = f"{safe_name}.jpg"
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
        supabase.table('students').insert({
            "id": student_id,
            "name": name,
            "program": program,
            "branch": branch,
            "mobile": mobile,
            "gmail": gmail,
            "embedding": normalized_emb.tolist()
        }).execute()
    except Exception as e:
        return redirect(url_for(
            'students.add_student', status='error',
            message='Database error while adding student',
        ))

    return redirect(url_for(
        'students.add_student', status='success',
        message=f'{name} added successfully with 1 encoding',
    ))
