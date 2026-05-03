"""
Students Blueprint.

Routes:
  GET  /students        — list all students
  GET  /add_student     — add-student form
  POST /submit_student  — process the form, save photo, encode face
"""

import os
import sqlite3

import cv2
import numpy as np
from flask import Blueprint, abort, redirect, render_template, request, url_for
from werkzeug.utils import secure_filename

import config
from utils.db import get_db_connection
from utils.face import add_or_update_encoding, model

students_bp = Blueprint('students', __name__)


@students_bp.route('/students')
def students():
    try:
        conn = sqlite3.connect(config.DB_FILE)
        cursor = conn.cursor()
        cursor.execute("SELECT ID, Name, Program, Branch, Mobile, Gmail FROM students")
        data = cursor.fetchall()
        conn.close()
        return render_template('students.html', students=data)
    except Exception:
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

    conn = get_db_connection()
    existing = conn.execute(
        "SELECT 1 FROM students WHERE ID=? OR lower(Name)=?",
        (student_id, name.lower()),
    ).fetchone()
    if existing:
        conn.close()
        return redirect(url_for(
            'students.add_student', status='error',
            message='Duplicate Name or ID found',
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

    # Persist student record
    conn.execute(
        'INSERT INTO students (ID, Name, Program, Branch, Mobile, Gmail) VALUES (?, ?, ?, ?, ?, ?)',
        (student_id, name, program, branch, mobile, gmail),
    )
    conn.commit()
    conn.close()

    # Encode the new face
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

    face    = faces[0]
    new_emb = np.array(face.embedding, dtype=np.float32)

    try:
        add_or_update_encoding(name, new_emb)
    except Exception:
        return redirect(url_for(
            'students.add_student', status='error',
            message='Student added but face encoding failed',
        ))

    return redirect(url_for(
        'students.add_student', status='success',
        message=f'{name} added successfully with 1 encoding',
    ))
