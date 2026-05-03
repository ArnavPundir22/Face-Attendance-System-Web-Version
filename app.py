# app.py (merged + admin dashboard + context for templates)
from flask import Flask, render_template, request, jsonify, redirect, url_for, session, flash
import cv2, numpy as np, os, pickle, sqlite3, base64, secrets, hashlib
from datetime import datetime, timedelta
from email.utils import parseaddr
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
REATTENDANCE_INTERVAL_MINUTES = 10
FACE_MATCH_THRESHOLD = 0.4
EMAIL_USER = 'arnavp128@gmail.com'
EMAIL_PASS = 'pshk aoim hjde ydol'

# Secret key for sessions — change in production or load from env
app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'CHANGE_ME_TO_SOMETHING_SECRET')

# -------------------------
# Security / Auth settings
# -------------------------
LOGIN_MAX_ATTEMPTS = 5          # failed attempts before lockout
LOGIN_LOCKOUT_MINUTES = 15      # how long to lock the account
OTP_EXPIRY_MINUTES = 10         # how long a password-reset OTP stays valid
MIN_PASSWORD_LENGTH = 8         # minimum password length
OTP_RANGE_START = 100_000       # minimum 6-digit OTP value (no leading zeros)
OTP_RANGE_SIZE  = 900_000       # range size → codes from 100000 to 999999

# In-memory login-attempt tracker  { username: {'count': int, 'locked_until': datetime|None} }
_login_attempts: dict = {}

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
            is_admin INTEGER DEFAULT 0,
            gmail TEXT
        )
    """)
    # Add gmail column to existing databases that were created before this column existed
    try:
        conn.execute("ALTER TABLE users ADD COLUMN gmail TEXT")
    except sqlite3.OperationalError:
        pass  # column already exists

    # Table for email-OTP-based password reset
    conn.execute("""
        CREATE TABLE IF NOT EXISTS password_reset_tokens (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            otp TEXT NOT NULL,
            expires_at TEXT NOT NULL,
            used INTEGER DEFAULT 0
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

def create_user(username: str, password: str, is_admin: int = 0, gmail: str = ''):
    """Create a user with hashed password. Returns True on success, False if username exists."""
    conn = get_db_connection()
    try:
        hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt())
        conn.execute("INSERT INTO users (username, password, is_admin, gmail) VALUES (?, ?, ?, ?)",
                     (username, hashed, is_admin, gmail.strip()))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()

def is_valid_email(email: str) -> bool:
    """Return True only if email parses to a non-empty local-part and domain."""
    _, addr = parseaddr(email)
    if not addr or '@' not in addr:
        return False
    local, domain = addr.rsplit('@', 1)
    return bool(local) and bool(domain)

# -------------------------
# Login rate-limit helpers
# NOTE: this tracker is in-memory; it resets on server restart and is not shared
# across multiple worker processes. For production use, persist to the database or Redis.
# -------------------------
def _get_attempts(username: str) -> dict:
    return _login_attempts.setdefault(username, {'count': 0, 'locked_until': None})

def is_account_locked(username: str):
    """Return (locked: bool, seconds_remaining: int)."""
    entry = _get_attempts(username)
    if entry['locked_until'] and datetime.now() < entry['locked_until']:
        remaining = int((entry['locked_until'] - datetime.now()).total_seconds())
        return True, remaining
    # reset lock if it has expired
    if entry['locked_until'] and datetime.now() >= entry['locked_until']:
        entry['count'] = 0
        entry['locked_until'] = None
    return False, 0

def record_failed_login(username: str):
    """Increment failure counter; lock the account once threshold is reached."""
    entry = _get_attempts(username)
    entry['count'] += 1
    if entry['count'] >= LOGIN_MAX_ATTEMPTS:
        entry['locked_until'] = datetime.now() + timedelta(minutes=LOGIN_LOCKOUT_MINUTES)

def clear_failed_logins(username: str):
    """Clear failure counter on successful login."""
    _login_attempts.pop(username, None)

# -------------------------
# Password-reset OTP helpers
# -------------------------
def _hash_otp(otp: str) -> str:
    """Return a SHA-256 hex digest of the OTP for safe storage."""
    return hashlib.sha256(otp.encode()).hexdigest()

def generate_and_store_otp(username: str) -> str:
    """Generate a 6-digit OTP (100000–999999), hash and store it, return the plain OTP."""
    # Use 100_000–999_999 to guarantee no leading zeros
    otp = str(secrets.randbelow(OTP_RANGE_SIZE) + OTP_RANGE_START)
    otp_hash = _hash_otp(otp)
    expires_at = (datetime.now() + timedelta(minutes=OTP_EXPIRY_MINUTES)).strftime("%Y-%m-%d %H:%M:%S")
    conn = get_db_connection()
    # Invalidate any existing unused tokens for this user
    conn.execute("UPDATE password_reset_tokens SET used=1 WHERE username=? AND used=0", (username,))
    conn.execute("INSERT INTO password_reset_tokens (username, otp, expires_at) VALUES (?, ?, ?)",
                 (username, otp_hash, expires_at))
    conn.commit()
    conn.close()
    return otp

def send_password_reset_otp(recipient_email: str, otp: str, username: str):
    """Send the 6-digit OTP to the user's registered email."""
    msg = EmailMessage()
    msg['Subject'] = '🔐 Password Reset OTP – Face Attendance System'
    msg['From'] = EMAIL_USER
    msg['To'] = recipient_email
    msg.set_content(
        f"Hello {username},\n\n"
        f"Your password reset OTP is: {otp}\n\n"
        f"This code is valid for {OTP_EXPIRY_MINUTES} minutes.\n"
        f"If you did not request a password reset, please ignore this email.\n\n"
        f"— Face Attendance System"
    )
    with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
        smtp.login(EMAIL_USER, EMAIL_PASS)
        smtp.send_message(msg)

def verify_and_consume_otp(username: str, otp: str) -> bool:
    """Return True and mark OTP used if it matches (hash comparison) and has not expired."""
    conn = get_db_connection()
    row = conn.execute(
        "SELECT id, otp, expires_at FROM password_reset_tokens "
        "WHERE username=? AND used=0 ORDER BY id DESC LIMIT 1",
        (username,)
    ).fetchone()
    if not row:
        conn.close()
        return False
    if datetime.now() > datetime.strptime(row['expires_at'], "%Y-%m-%d %H:%M:%S"):
        conn.close()
        return False
    stored_hash = row['otp']
    supplied_hash = _hash_otp(otp)
    if not secrets.compare_digest(stored_hash, supplied_hash):
        conn.close()
        return False
    conn.execute("UPDATE password_reset_tokens SET used=1 WHERE id=?", (row['id'],))
    conn.commit()
    conn.close()
    return True

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

# ensure users table and admin exist at startup
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
# - in memory we keep:
#     known_embeddings        – list of (embedding, name) kept for backward compat
#     known_embedding_matrix  – (N, D) float32 array of all L2-normalised embeddings
#     known_embedding_names   – list[str] of names in the same row order as the matrix
#
# The matrix lets us replace the O(N) Python for-loop with a single BLAS matrix-vector
# multiply:  scores = known_embedding_matrix @ query   →  argmax gives the best match.
# Because every embedding is L2-normalised, dot-product == cosine similarity.
known_encoding_dict    = {}          # name -> np.ndarray
known_embeddings       = []          # list of (embedding, name) — kept for compatibility
known_embedding_matrix = None        # np.ndarray shape (N, D), or None when empty
known_embedding_names  = []          # list[str] parallel to matrix rows

def _rebuild_embedding_matrix():
    """Rebuild the fast-search matrix from known_encoding_dict.

    Called after any change to known_encoding_dict so the matrix stays in sync.
    """
    global known_embedding_matrix, known_embedding_names, known_embeddings
    if not known_encoding_dict:
        known_embedding_matrix = None
        known_embedding_names  = []
        known_embeddings       = []
        return

    names = list(known_encoding_dict.keys())
    matrix = np.array([known_encoding_dict[n] for n in names], dtype=np.float32)
    known_embedding_names  = names
    known_embedding_matrix = matrix
    known_embeddings       = [(known_encoding_dict[n], n) for n in names]

def load_encodings_from_file():
    """Load encodings from ENCODE_FILE, normalize, and populate in-memory structures."""
    global known_encoding_dict
    if not os.path.exists(ENCODE_FILE):
        known_encoding_dict = {}
        _rebuild_embedding_matrix()
        return

    try:
        with open(ENCODE_FILE, 'rb') as f:
            data = pickle.load(f)
    except Exception:
        # if file exists but corrupted, reset
        known_encoding_dict = {}
        _rebuild_embedding_matrix()
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
    _rebuild_embedding_matrix()

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
# Inject admin flag into templates
# -------------------------
@app.context_processor
def inject_user_info():
    return {
        'session_username': session.get('username'),
        'session_is_admin': is_current_user_admin() if 'username' in session else False
    }

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

        # Check rate limit before hitting the database
        locked, secs = is_account_locked(username)
        if locked:
            mins = secs // 60
            secsrem = secs % 60
            return render_template('login.html',
                                   error=f"Account locked after {LOGIN_MAX_ATTEMPTS} failed attempts. "
                                         f"Try again in {mins}m {secsrem}s.")

        conn = get_db_connection()
        user = conn.execute("SELECT * FROM users WHERE username=?", (username,)).fetchone()
        conn.close()

        if not user:
            # Don't reveal whether the username exists
            record_failed_login(username)
            return render_template('login.html', error="Invalid username or password")

        stored_hash = user['password']  # this is bytes (BLOB)

        # stored_hash might be a memoryview (depending on sqlite). Ensure bytes.
        if isinstance(stored_hash, memoryview):
            stored_hash = stored_hash.tobytes()

        try:
            if bcrypt.checkpw(password.encode(), stored_hash):
                clear_failed_logins(username)
                session['logged_in'] = True
                session['username'] = username
                return redirect(url_for('index'))
            else:
                record_failed_login(username)
                locked, secs = is_account_locked(username)
                remaining_attempts = max(LOGIN_MAX_ATTEMPTS - _get_attempts(username)['count'], 0)
                if locked:
                    mins = secs // 60
                    secsrem = secs % 60
                    return render_template('login.html',
                                           error=f"Account locked after too many failed attempts. "
                                                 f"Try again in {mins}m {secsrem}s.")
                return render_template('login.html',
                                       error=f"Invalid username or password. "
                                             f"{remaining_attempts} attempt(s) remaining before lockout.")
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
        email = request.form.get('email', '').strip()

        if not username or not password or not email:
            return render_template('register.html', error="All fields are required")

        if len(password) < MIN_PASSWORD_LENGTH:
            return render_template('register.html',
                                   error=f"Password must be at least {MIN_PASSWORD_LENGTH} characters")

        if not is_valid_email(email):
            return render_template('register.html', error="Enter a valid email address")

        success = create_user(username, password, is_admin=0, gmail=email)
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
    """
    Two-step email-OTP password reset:
      Step 1 (GET or step=request): User enters their username.
              System looks up their registered gmail, sends a 6-digit OTP,
              and renders the verify form.
      Step 2 (step=verify): User enters the OTP + new password.
              System verifies the OTP, updates the password.
    """
    if request.method == 'GET':
        return render_template('forgot_password.html', step='request')

    step = request.form.get('step', 'request')

    # ------------------------------------------------------------------
    # STEP 1 – receive username, send OTP email
    # ------------------------------------------------------------------
    if step == 'request':
        username = request.form.get('username', '').strip()
        if not username:
            return render_template('forgot_password.html', step='request',
                                   error="Please enter your username.")

        conn = get_db_connection()
        user = conn.execute("SELECT username, gmail FROM users WHERE username=?", (username,)).fetchone()
        conn.close()

        # Always show the same message to prevent username enumeration.
        # Also send the OTP (or silently skip) so the response time is consistent.
        generic_sent_msg = ("If that username exists and has a registered email, "
                            "an OTP has been sent. Check your inbox.")

        if not user or not user['gmail']:
            # No user / no email — return the same message but don't proceed further
            return render_template('forgot_password.html', step='request',
                                   info=generic_sent_msg)

        try:
            otp = generate_and_store_otp(username)
            send_password_reset_otp(user['gmail'], otp, username)
        except Exception as e:
            app.logger.exception("Failed to send OTP email: %s", e)
            return render_template('forgot_password.html', step='request',
                                   error="Could not send OTP email. Please contact the admin.")

        # Use the same generic message to avoid revealing that the user exists and has an email
        return render_template('forgot_password.html', step='verify',
                               username=username,
                               info=generic_sent_msg)

    # ------------------------------------------------------------------
    # STEP 2 – verify OTP and set new password
    # ------------------------------------------------------------------
    if step == 'verify':
        username = request.form.get('username', '').strip()
        otp = request.form.get('otp', '').strip()
        new_password = request.form.get('new_password', '').strip()

        if not username or not otp or not new_password:
            return render_template('forgot_password.html', step='verify',
                                   username=username, error="All fields are required.")

        if len(new_password) < MIN_PASSWORD_LENGTH:
            return render_template('forgot_password.html', step='verify',
                                   username=username,
                                   error=f"Password must be at least {MIN_PASSWORD_LENGTH} characters.")

        if not verify_and_consume_otp(username, otp):
            return render_template('forgot_password.html', step='verify',
                                   username=username,
                                   error="Invalid or expired OTP. Please request a new one.")

        hashed = bcrypt.hashpw(new_password.encode(), bcrypt.gensalt())
        conn = get_db_connection()
        conn.execute("UPDATE users SET password=? WHERE username=?", (hashed, username))
        conn.commit()
        conn.close()

        # Clear any login lockout for this user after successful reset
        clear_failed_logins(username)

        return redirect(url_for('login'))

    # Fallback
    return render_template('forgot_password.html', step='request')
    


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
                # ... (kept same as before)
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
        _rebuild_embedding_matrix()

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

    now = datetime.now()
    timestamp = now.strftime("%Y-%m-%d %H:%M:%S")

    all_outputs = []
    session_attendance = []     # <---- COLLECT ONLY THIS SCAN'S ATTENDANCE

    conn = get_db_connection()

    # Snapshot matrix + names once per request so mid-request updates don't race.
    # All embeddings are L2-normalised, so dot-product == cosine similarity.
    # A single BLAS matrix-vector multiply (matrix @ query) replaces the Python
    # for-loop and is typically 10-100x faster due to SIMD / multi-core BLAS.
    search_matrix = known_embedding_matrix   # shape (N, D) float32, or None
    search_names  = known_embedding_names    # list[str], len N

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

                if search_matrix is not None and search_matrix.shape[0] > 0:
                    # Vectorised nearest-neighbour: one BLAS matrix-vector multiply
                    # replaces the O(N) Python loop. Both the stored embeddings (in the
                    # matrix) and the query embedding (normalised at line 822 above) are
                    # L2-normalised, so dot-product equals cosine similarity.
                    scores    = search_matrix @ embedding   # shape (N,)
                    best_idx  = int(np.argmax(scores))
                    best_score = float(scores[best_idx])
                    best_name  = search_names[best_idx]

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

# -------------------------
# ADMIN: Dashboard, students, manual mark
# -------------------------
@app.route('/admin')
def admin_dashboard():
    if not is_current_user_admin():
        return render_template('login.html', error="Admin access required")
    conn = get_db_connection()
    total_students = conn.execute("SELECT COUNT(*) AS cnt FROM students").fetchone()['cnt'] or 0
    total_attendance = conn.execute("SELECT COUNT(*) AS cnt FROM attendance").fetchone()['cnt'] or 0
    total_users = conn.execute("SELECT COUNT(*) AS cnt FROM users").fetchone()['cnt'] or 0

    # Today's attendance count
    today_date = datetime.now().strftime("%Y-%m-%d")
    cur = conn.execute("SELECT COUNT(*) AS cnt FROM attendance WHERE date(Timestamp)=?", (today_date,))
    today_att = cur.fetchone()['cnt'] or 0

    conn.close()
    return render_template('admin_dashboard.html',
                           total_students=total_students,
                           total_attendance=total_attendance,
                           total_users=total_users,
                           today_attendance=today_att)

@app.route('/admin/stats')
def admin_stats():
    if not is_current_user_admin():
        return jsonify({'error': 'admin required'}), 403
    conn = get_db_connection()
    # 7-day trend
    trend = []
    for d in range(6, -1, -1):
        day = (datetime.now() - timedelta(days=d)).strftime("%Y-%m-%d")
        cnt = conn.execute("SELECT COUNT(*) AS cnt FROM attendance WHERE date(Timestamp)=?", (day,)).fetchone()['cnt'] or 0
        trend.append({'date': day, 'count': cnt})
    # today present vs absent
    today = datetime.now().strftime("%Y-%m-%d")
    present = conn.execute("SELECT COUNT(*) AS cnt FROM attendance WHERE date(Timestamp)=? AND Status LIKE '%Present%'", (today,)).fetchone()['cnt'] or 0
    total_today = conn.execute("SELECT COUNT(*) AS cnt FROM attendance WHERE date(Timestamp)=?", (today,)).fetchone()['cnt'] or 0
    absent = max(total_today - present, 0)
    conn.close()
    return jsonify({'trend': trend, 'present': present, 'absent': absent})

@app.route('/admin/students')
def admin_students():
    if not is_current_user_admin():
        return render_template('login.html', error="Admin access required")
    conn = get_db_connection()
    students = conn.execute("SELECT * FROM students ORDER BY Name COLLATE NOCASE").fetchall()
    conn.close()
    return render_template('admin_students.html', students=students)

@app.route('/admin/student/edit/<student_id>', methods=['GET', 'POST'])
def admin_edit_student(student_id):
    if not is_current_user_admin():
        return render_template('login.html', error="Admin access required")
    conn = get_db_connection()
    student = conn.execute("SELECT * FROM students WHERE ID=?", (student_id,)).fetchone()
    if not student:
        conn.close()
        return redirect(url_for('admin_students'))
    if request.method == 'POST':
        name = request.form['name'].strip()
        program = request.form['program'].strip()
        branch = request.form['branch'].strip()
        mobile = request.form['mobile'].strip()
        gmail = request.form['gmail'].strip()
        conn.execute('UPDATE students SET Name=?, Program=?, Branch=?, Mobile=?, Gmail=? WHERE ID=?',
                     (name, program, branch, mobile, gmail, student_id))
        conn.commit()
        conn.close()
        return redirect(url_for('admin_students'))
    conn.close()
    return render_template('edit_student.html', student=student)

@app.route('/admin/student/delete/<student_id>', methods=['POST'])
def admin_delete_student(student_id):
    if not is_current_user_admin():
        return render_template('login.html', error="Admin access required")
    conn = get_db_connection()
    conn.execute("DELETE FROM students WHERE ID=?", (student_id,))
    conn.commit()
    conn.close()
    return redirect(url_for('admin_students'))

@app.route('/admin/mark', methods=['GET', 'POST'])
def admin_mark_attendance():
    if not is_current_user_admin():
        return render_template('login.html', error="Admin access required")
    conn = get_db_connection()
    students = conn.execute("SELECT ID, Name FROM students ORDER BY Name COLLATE NOCASE").fetchall()
    if request.method == 'POST':
        student_id = request.form.get('student_id')
        status = request.form.get('status', 'Present')
        lecture = request.form.get('lecture','').strip()
        section = request.form.get('section','').strip()
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        student = conn.execute("SELECT * FROM students WHERE ID=?", (student_id,)).fetchone()
        if not student:
            conn.close()
            return render_template('admin_mark.html', students=students, error="Student not found")
        conn.execute('''
            INSERT INTO attendance (Student_ID, Name, Program, Branch, Mobile, Status, Timestamp, Lecture, Section)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (student['ID'], student['Name'], student['Program'], student['Branch'],
              student['Mobile'], status, timestamp, lecture, section))
        conn.commit()
        conn.close()
        return redirect(url_for('admin_dashboard'))
    conn.close()
    return render_template('admin_mark.html', students=students)

if __name__ == '__main__':
    app.run(debug=True)

