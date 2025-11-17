# app.py (full updated file)
from flask import Flask, render_template, request, jsonify, redirect, url_for, session
import cv2, numpy as np, os, pickle, sqlite3, base64
from datetime import datetime
import insightface, smtplib
from email.message import EmailMessage
from io import BytesIO
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
import bcrypt

app = Flask(__name__)

# -------------------------
# Configuration
# -------------------------
DB_FILE = 'database.db'
ENCODE_FILE = 'EncodeFile_Insight.pkl'
REATTENDANCE_INTERVAL_MINUTES = 2
FACE_MATCH_THRESHOLD = 0.5
EMAIL_USER = 'arnavp128@gmail.com'
EMAIL_PASS = 'pshk aoim hjde ydol'

# Secret key for sessions — change in production or load from env
app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'CHANGE_ME_TO_SOMETHING_SECRET')

# --- Database utility functions ---
def get_db_connection():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def init_users_table_and_admin():
    """
    Create users table if not exists and auto-create an admin user if there are no users.
    Admin credentials (first-run):
        username: admin
        password: admin123
    """
    conn = get_db_connection()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            password BLOB,
            is_admin INTEGER DEFAULT 0
        )
    """)
    conn.commit()

    # Check if any user exists
    cur = conn.execute("SELECT COUNT(*) AS cnt FROM users")
    row = cur.fetchone()
    count = row['cnt'] if row else 0

    if count == 0:
        # create default admin
        admin_user = "admin"
        admin_pass = "admin123"
        hashed = bcrypt.hashpw(admin_pass.encode(), bcrypt.gensalt())
        conn.execute("INSERT INTO users (username, password, is_admin) VALUES (?, ?, ?)",
                     (admin_user, hashed, 1))
        conn.commit()
        app.logger.info("Auto-created default admin -> username: 'admin', password: 'admin123' (please change immediately)")
    conn.close()

def create_user(username: str, password: str, is_admin: int = 0):
    """Create a user with hashed password. Returns True on success, False if username exists."""
    conn = get_db_connection()
    try:
        hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt())
        conn.execute("INSERT INTO users (username, password, is_admin) VALUES (?, ?, ?)",
                     (username, hashed, is_admin))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()

def is_current_user_admin():
    """Return True if current logged in user is admin."""
    if 'username' not in session:
        return False
    username = session['username']
    conn = get_db_connection()
    user = conn.execute("SELECT is_admin FROM users WHERE username=?", (username,)).fetchone()
    conn.close()
    if not user:
        return False
    return bool(user['is_admin'])


# -------------------------
# Ensure users table and admin exist at startup
# -------------------------
init_users_table_and_admin()


# -------------------------
# Face recognition setup (unchanged logic)
# -------------------------
# ensure directories exist
os.makedirs('known_faces', exist_ok=True)

# Load InsightFace model once
model = insightface.app.FaceAnalysis(name='buffalo_l')
model.prepare(ctx_id=0)

# Internal encoding store:
# - on disk we keep a dict: { name: np.ndarray_embedding }
# - in memory we keep known_embeddings_list: list of (embedding, name) for fast iteration
known_encoding_dict = {}         # name -> np.ndarray
known_embeddings = []            # list of (embedding, name) used by recognition loops

def load_encodings_from_file():
    """Load encodings from ENCODE_FILE, normalize, and populate both dict and list."""
    global known_encoding_dict, known_embeddings
    if not os.path.exists(ENCODE_FILE):
        known_encoding_dict = {}
        known_embeddings = []
        return

    try:
        with open(ENCODE_FILE, 'rb') as f:
            data = pickle.load(f)
    except Exception:
        # if file exists but corrupted, reset
        known_encoding_dict = {}
        known_embeddings = []
        return

    # support both legacy formats: list of (embedding, name) or dict{name: embedding}
    enc_dict = {}
    if isinstance(data, dict):
        enc_dict = data
    elif isinstance(data, list):
        # list of (embedding, name) -> convert to dict by keeping latest/last embedding per name
        for item in data:
            if isinstance(item, (list, tuple)) and len(item) == 2:
                emb, name = item
                try:
                    emb_arr = np.array(emb, dtype=np.float32)
                    enc_dict[name] = emb_arr
                except Exception:
                    continue
    else:
        enc_dict = {}

    # normalize embeddings and ensure numpy arrays
    cleaned = {}
    for name, emb in enc_dict.items():
        try:
            arr = np.array(emb, dtype=np.float32)
            norm = np.linalg.norm(arr)
            if norm == 0:
                continue
            arr = arr / norm
            cleaned[name] = arr
        except Exception:
            continue

    known_encoding_dict = cleaned
    known_embeddings = [(emb, name) for name, emb in known_encoding_dict.items()]

def save_encodings_to_file():
    """Save the current known_encoding_dict to disk (pickle)."""
    try:
        with open(ENCODE_FILE, 'wb') as f:
            pickle.dump(known_encoding_dict, f)
    except Exception as e:
        app.logger.exception("Failed to save encodings: %s", e)

# Load encodings at startup
load_encodings_from_file()


# -------------------------
# Authentication enforcement
# -------------------------
@app.before_request
def require_login():
    """
    Option A: protect all routes except /login and static files.
    /register is admin-only — so it is NOT publicly accessible.
    """
    allowed_paths = [
    '/login',
    '/forgot_password',
    '/favicon.ico'
]

    # allow static files (css/js/img served from /static/…)
    if request.path.startswith('/static/') or request.path in allowed_paths:
        return None

    # If user not logged in, redirect to login
    if 'logged_in' not in session:
        return redirect(url_for('login'))

    # if user is logged in, allow (further admin checks are done inside /register)
    return None


# -------------------------
# Routes: Authentication
# -------------------------
@app.route('/login', methods=['GET', 'POST'])
def login():
    # Public route
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()

        if not username or not password:
            return render_template('login.html', error="Username and password required")

        conn = get_db_connection()
        user = conn.execute("SELECT * FROM users WHERE username=?", (username,)).fetchone()
        conn.close()

        if not user:
            return render_template('login.html', error="Invalid username or password")

        stored_hash = user['password']  # this is bytes (BLOB)

        # stored_hash might be a memoryview (depending on sqlite). Ensure bytes.
        if isinstance(stored_hash, memoryview):
            stored_hash = stored_hash.tobytes()

        try:
            if bcrypt.checkpw(password.encode(), stored_hash):
                session['logged_in'] = True
                session['username'] = username
                return redirect(url_for('index'))
            else:
                return render_template('login.html', error="Invalid username or password")
        except Exception:
            return render_template('login.html', error="Invalid username or password")

    return render_template('login.html')


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))


@app.route('/register', methods=['GET', 'POST'])
def register():
    """
    Admin-only registration route.
    The before_request ensures user is logged in; here we check if that user is admin.
    """
    if not is_current_user_admin():
        return render_template('login.html', error="Admin access required to create new users")

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()

        if not username or not password:
            return render_template('register.html', error="All fields required")

        success = create_user(username, password, is_admin=0)
        if not success:
            return render_template('register.html', error="Username already exists")
        return render_template('register.html', success="User created successfully!")

    return render_template('register.html')


# -------------------------
# Face Attendance / App routes (protected by before_request)
# -------------------------
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/viewer')
def viewer():
    return render_template('viewer.html')

@app.route('/get_attendance_data')
def get_attendance_data():
    try:
        conn = sqlite3.connect(DB_FILE)
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
        conn = sqlite3.connect(DB_FILE)
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


@app.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        username = request.form['username'].strip()
        new_password = request.form['new_password'].strip()

        conn = get_db_connection()
        user = conn.execute("SELECT * FROM users WHERE username=?", (username,)).fetchone()

        if not user:
            conn.close()
            return render_template('forgot_password.html', error="User does not exist.")

        # 🔐 Hash new password before saving
        hashed = bcrypt.hashpw(new_password.encode(), bcrypt.gensalt())

        conn.execute("UPDATE users SET password=? WHERE username=?", (hashed, username))
        conn.commit()
        conn.close()

        return redirect(url_for('login'))

    return render_template('forgot_password.html')
    


@app.route('/submit_student', methods=['POST'])
def submit_student():
    """
    Adds a student:
     - saves photo as NameWithoutSpaces.jpg (no underscores)
     - computes embedding for the newly uploaded image
     - updates (or creates) a single normalized embedding per student in ENCODE_FILE
     - updates in-memory known_embeddings for instant recognition
    """
    global known_encoding_dict, known_embeddings

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

    # Save photo to known_faces folder WITHOUT underscore
    clean_name = name.replace(" ", " ")   # Avanya Pundir.jpg (no underscore)
    filename = f"{clean_name}.jpg"
    filepath = os.path.join('known_faces', filename)
    photo.save(filepath)

    # Save student record in DB
    conn.execute('INSERT INTO students (ID, Name, Program, Branch, Mobile, Gmail) VALUES (?, ?, ?, ?, ?, ?)',
                 (student_id, name, program, branch, mobile, gmail))
    conn.commit()
    conn.close()

    # --- Encode ONLY this new image (fast) ---
    image = cv2.imread(filepath)
    if image is None:
        return redirect(url_for('add_student', status='error', message='Saved image could not be read'))

    faces = model.get(image)
    if not faces:
        return redirect(url_for('add_student', status='error', message='No face detected in uploaded image'))

    # We will use the first face detected for the student's ID (if multiple faces exist in the photo)
    face = faces[0]
    emb = np.array(face.embedding, dtype=np.float32)
    norm = np.linalg.norm(emb)
    if norm == 0:
        return redirect(url_for('add_student', status='error', message='Embedding extraction failed'))
    emb = emb / norm

    # Update stored encoding: average with existing if present (then renormalize)
    try:
        # load current dict (already loaded at startup, but re-read current file to be safe)
        if os.path.exists(ENCODE_FILE):
            with open(ENCODE_FILE, 'rb') as f:
                disk_data = pickle.load(f)
            # convert legacy formats if needed
            if isinstance(disk_data, list):
                tmp = {}
                for item in disk_data:
                    if isinstance(item, (list, tuple)) and len(item) == 2:
                        e, n = item
                        try:
                            arr = np.array(e, dtype=np.float32)
                            arr_norm = np.linalg.norm(arr)
                            if arr_norm > 0:
                                tmp[n] = arr / arr_norm
                        except Exception:
                            pass
                disk_data = tmp
            elif not isinstance(disk_data, dict):
                disk_data = {}
        else:
            disk_data = {}

        # If existing embedding exists for this name, average them
        if name in disk_data:
            existing_emb = np.array(disk_data[name], dtype=np.float32)
            # normalize just in case
            if np.linalg.norm(existing_emb) > 0:
                existing_emb = existing_emb / np.linalg.norm(existing_emb)
            combined = existing_emb + emb
            if np.linalg.norm(combined) > 0:
                combined = combined / np.linalg.norm(combined)
            final_emb = combined
        else:
            final_emb = emb

        # write back to disk dictionary (single embedding per name)
        disk_data[name] = final_emb
        with open(ENCODE_FILE, 'wb') as f:
            pickle.dump(disk_data, f)

        # update in-memory structures for recognition (fast)
        known_encoding_dict = {k: np.array(v, dtype=np.float32) for k, v in disk_data.items()}
        # ensure normalization
        for k in list(known_encoding_dict.keys()):
            v = known_encoding_dict[k]
            normv = np.linalg.norm(v)
            if normv > 0:
                known_encoding_dict[k] = v / normv
        known_embeddings = [(emb, n) for n, emb in known_encoding_dict.items()]

    except Exception as e:
        app.logger.exception("Failed to update encoding for new student: %s", e)
        # still continue - we don't want to block student addition entirely
        return redirect(url_for('add_student', status='error', message='Student added but encoding failed'))

    return redirect(url_for('add_student', status='success', message=f'{name} added successfully with 1 encoding'))


@app.route('/upload_photo', methods=['POST'])
def upload_photo():
    if 'images' not in request.files:
        return jsonify({"images": [], "session_attendance": []})

    lecture = request.form.get('lecture', '').strip()
    section = request.form.get('section', '').strip()
    files = request.files.getlist('images')

    def cosine_sim(a, b):
        return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))

    now = datetime.now()
    timestamp = now.strftime("%Y-%m-%d %H:%M:%S")

    all_outputs = []
    session_attendance = []     # <---- COLLECT ONLY THIS SCAN’S ATTENDANCE

    conn = get_db_connection()

    # small optimization: copy known_embeddings to local var
    embeddings_for_search = known_embeddings.copy()

    for file in files:
        npimg = np.frombuffer(file.read(), np.uint8)
        frame = cv2.imdecode(npimg, cv2.IMREAD_COLOR)
        original = frame.copy()
        faces = model.get(frame)

        results = []
        if faces:
            for face in faces:
                bbox = [int(v) for v in face.bbox]
                embedding = np.array(face.embedding, dtype=np.float32)
                # normalize embedding
                if np.linalg.norm(embedding) == 0:
                    continue
                embedding = embedding / np.linalg.norm(embedding)

                best_score = -1.0
                best_name = None

                for known_emb, name in embeddings_for_search:
                    # known_emb should be numpy array already
                    try:
                        score = cosine_sim(embedding, known_emb)
                    except Exception:
                        continue
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

                # Insert attendance
                conn.execute('''
                    INSERT INTO attendance (Student_ID, Name, Program, Branch, Mobile, Status, Timestamp, Lecture, Section)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (student['ID'], student['Name'], student['Program'], student['Branch'],
                      student['Mobile'], status, timestamp, lecture, section))
                conn.commit()

                result_entry = {
                    "name": best_name,
                    "status": status,
                    "confidence": f"{best_score:.2f}",
                    "timestamp": timestamp
                }

                results.append(result_entry)

                # ---- SAVE ONLY THIS SESSION ATTENDANCE ----
                session_attendance.append([
                    student['ID'],
                    student['Name'],
                    student['Program'],
                    student['Branch'],
                    student['Mobile'],
                    status,
                    timestamp,
                    lecture,
                    section
                ])

        # Encode image
        _, buffer = cv2.imencode('.jpg', original)
        encoded_img = base64.b64encode(buffer).decode('utf-8')
        image_url = f"data:image/jpeg;base64,{encoded_img}"

        all_outputs.append({"results": results, "annotated": image_url})

    conn.close()

    # RETURN SESSION ATTENDANCE!
    return jsonify({
        "images": all_outputs,
        "session_attendance": session_attendance
    })

if __name__ == '__main__':
    app.run(debug=True)

