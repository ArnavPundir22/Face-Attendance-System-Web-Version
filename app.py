from flask import Flask, render_template, request, jsonify, redirect, url_for
import cv2, numpy as np, os, pickle, sqlite3, base64
from datetime import datetime
import insightface, smtplib
from email.message import EmailMessage
from io import BytesIO
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors

app = Flask(__name__)

DB_FILE = 'database.db'
ENCODE_FILE = 'EncodeFile_Insight.pkl'
REATTENDANCE_INTERVAL_MINUTES = 2
FACE_MATCH_THRESHOLD = 0.5
EMAIL_USER = 'arnavp128@gmail.com'
EMAIL_PASS = 'cyhy ppki rdny rjwc'

# --- Database utility functions ---
def get_db_connection():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

# Load InsightFace model
model = insightface.app.FaceAnalysis(name='buffalo_l')
model.prepare(ctx_id=0)

# Load known encodings
with open(ENCODE_FILE, 'rb') as f:
    known_embeddings = pickle.load(f)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/viewer')
def viewer():
    return render_template('viewer.html')

import sqlite3

@app.route('/get_attendance_data')
def get_attendance_data():
    try:
        conn = sqlite3.connect("database.db")
        cursor = conn.cursor()
        cursor.execute("""
            SELECT Student_ID, Name, Program, Branch, Mobile, Status, Timestamp, Lecture, Section 
            FROM attendance
        """)
        data = cursor.fetchall()
        conn.close()
        return jsonify(data)
    except Exception as e:
        return jsonify([])


@app.route('/students')
def students():
    try:
        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()
        cursor.execute("SELECT ID, Name, Program, Branch, Mobile, Gmail FROM students")
        data = cursor.fetchall()
        conn.close()
        return render_template('students.html', students=data)
    except Exception as e:
        return str(e)

@app.route('/send_attendance_email', methods=['POST'])
def send_attendance_email():
    data = request.get_json()
    email = data.get('email', '').strip()
    table_data = data.get('data', [])

    if not email or '@' not in email:
        return jsonify({'success': False, 'message': 'Invalid email address'})
    if not table_data or not isinstance(table_data, list):
        return jsonify({'success': False, 'message': 'No data received for email'})

    try:
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30)

        elements = []
        styles = getSampleStyleSheet()
        title_style = styles['Title']
        subtitle_style = styles['Heading2']

        # Add Title & Subtitle
        elements.append(Paragraph("Attendance Report", title_style))
        elements.append(Paragraph(datetime.now().strftime("Generated on %d %B %Y, %I:%M %p"), subtitle_style))
        elements.append(Spacer(1, 12))

        # Table header & data
        headers = ['ID', 'Name', 'Program', 'Branch', 'Mobile', 'Status', 'Timestamp', 'Lecture', 'Section']
        table_data = [headers] + table_data

        table = Table(table_data, repeatRows=1)
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1E3A8A')),  # Dark Blue header
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('FONTSIZE', (0, 1), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.whitesmoke, colors.lightgrey])
        ]))
        elements.append(table)

        doc.build(elements)
        pdf_data = buffer.getvalue()


        msg = EmailMessage()
        msg['Subject'] = 'Attendance Report'
        msg['From'] = EMAIL_USER
        msg['To'] = email
        msg.set_content('Attached is your attendance report.')
        msg.add_attachment(pdf_data, maintype='application', subtype='pdf', filename='attendance_report.pdf')

        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
            smtp.login(EMAIL_USER, EMAIL_PASS)
            smtp.send_message(msg)

        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/add_student')
def add_student():
    return render_template('add_student.html')

@app.route('/submit_student', methods=['POST'])
def submit_student():
    name = request.form['name'].strip()
    student_id = request.form['id'].strip()
    program = request.form['program'].strip()
    branch = request.form['branch'].strip()
    mobile = request.form['mobile'].strip()
    gmail = request.form['email'].strip()
    photo = request.files.get('photo')

    if not name or not student_id or not photo:
        return redirect(url_for('add_student', status='error', message='Name, ID and Photo are required'))

    conn = get_db_connection()
    existing = conn.execute("SELECT 1 FROM students WHERE ID=? OR lower(Name)=?", (student_id, name.lower())).fetchone()
    if existing:
        conn.close()
        return redirect(url_for('add_student', status='error', message='Duplicate Name or ID found'))

    filename = f"{name.replace(' ', '_')}.jpg"
    filepath = os.path.join('known_faces', filename)
    photo.save(filepath)

    conn.execute('INSERT INTO students (ID, Name, Program, Branch, Mobile, Gmail) VALUES (?, ?, ?, ?, ?, ?)',
                 (student_id, name, program, branch, mobile, gmail))
    conn.commit()
    conn.close()

    image = cv2.imread(filepath)
    faces = model.get(image)
    if not faces:
        return redirect(url_for('add_student', status='error', message='No face detected in uploaded image'))

    embedding = faces[0].embedding
    if os.path.exists(ENCODE_FILE):
        with open(ENCODE_FILE, 'rb') as f:
            known_embeddings = pickle.load(f)
    else:
        known_embeddings = []

    known_embeddings.append((embedding, name))
    with open(ENCODE_FILE, 'wb') as f:
        pickle.dump(known_embeddings, f)

    return redirect(url_for('add_student', status='success', message=f'{name} added successfully'))

@app.route('/upload_photo', methods=['POST'])
def upload_photo():
    if 'images' not in request.files:
        return jsonify({"images": []})

    lecture = request.form.get('lecture', '').strip()
    section = request.form.get('section', '').strip()
    files = request.files.getlist('images')

    def cosine_sim(a, b):
        return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))

    now = datetime.now()
    timestamp = now.strftime("%Y-%m-%d %H:%M:%S")

    all_outputs = []
    conn = get_db_connection()

    for file in files:
        npimg = np.frombuffer(file.read(), np.uint8)
        frame = cv2.imdecode(npimg, cv2.IMREAD_COLOR)
        original = frame.copy()
        faces = model.get(frame)

        results = []
        if faces:
            for face in faces:
                bbox = [int(v) for v in face.bbox]
                embedding = face.embedding
                best_score = -1
                best_name = None

                for known_embedding, name in known_embeddings:
                    score = cosine_sim(embedding, known_embedding)
                    if score > best_score:
                        best_score = score
                        best_name = name

                color = (0, 255, 0) if best_score >= FACE_MATCH_THRESHOLD else (0, 0, 255)
                label = best_name if best_score >= FACE_MATCH_THRESHOLD else "Unknown"

                cv2.rectangle(original, (bbox[0], bbox[1]), (bbox[2], bbox[3]), color, 2)
                cv2.putText(original, f"{label} ({best_score:.2f})", (bbox[0], bbox[1] - 10),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)

                if best_score < FACE_MATCH_THRESHOLD:
                    results.append({"name": "Unknown", "status": "Unknown", "confidence": f"{best_score:.2f}"})
                    continue

                student = conn.execute('SELECT * FROM students WHERE Name=?', (best_name,)).fetchone()
                if not student:
                    results.append({"name": best_name, "status": "Not Found", "confidence": f"{best_score:.2f}"})
                    continue

                # Check last mark time
                last_mark = conn.execute(
                    "SELECT Timestamp FROM attendance WHERE Student_ID=? ORDER BY Timestamp DESC LIMIT 1",
                    (student['ID'],)
                ).fetchone()

                remark = False
                if last_mark:
                    last_time = datetime.strptime(last_mark['Timestamp'], "%Y-%m-%d %H:%M:%S")
                    elapsed = (now - last_time).total_seconds() / 60
                    if elapsed < REATTENDANCE_INTERVAL_MINUTES:
                        results.append({
                            "name": best_name,
                            "status": "Already Marked",
                            "confidence": f"{best_score:.2f}",
                            "timestamp": last_time.strftime("%Y-%m-%d %H:%M:%S")
                        })
                        continue
                    else:
                        remark = True

                status = 'Re-Marked' if remark else 'Present'
                conn.execute('''
                    INSERT INTO attendance (Student_ID, Name, Program, Branch, Mobile, Status, Timestamp, Lecture, Section)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (student['ID'], student['Name'], student['Program'], student['Branch'],
                      student['Mobile'], status, timestamp, lecture, section))
                conn.commit()

                results.append({
                    "name": best_name,
                    "status": status,
                    "confidence": f"{best_score:.2f}",
                    "timestamp": timestamp
                })

        # Encode annotated image
        _, buffer = cv2.imencode('.jpg', original)
        encoded_img = base64.b64encode(buffer).decode('utf-8')
        image_url = f"data:image/jpeg;base64,{encoded_img}"

        all_outputs.append({"results": results, "annotated": image_url})

    conn.close()
    return jsonify({"images": all_outputs})

if __name__ == '__main__':
    app.run(debug=True)

