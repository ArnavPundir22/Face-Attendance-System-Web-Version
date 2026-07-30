# ⚙️ Technical Architecture Document (TAD)
# BioSecure AI

**Version**: 2.0  
**Last Updated**: 2026-07-14  

---

## 1. Repository Layout

```
Face-Attendance-System-Web-Version/
│
├── app.py                      # Application factory (create_app)
├── config.py                   # Centralised configuration from env vars
├── gunicorn.conf.py             # Gunicorn production config
├── Procfile                     # PaaS entry point (Render, Railway)
├── requirements.txt             # Python dependencies (pinned)
├── start_face_attendance.sh     # VPS startup helper script
├── .env                         # Local secrets (NOT committed)
├── .env.example                 # Env var template
├── .gitignore
│
├── blueprints/                  # Flask Blueprints (feature modules)
│   ├── __init__.py
│   ├── auth.py                  # /login /logout /register
│   ├── attendance.py            # / /viewer /upload_photo /get_attendance_data
│   ├── students.py              # /students /add_student /submit_student
│   └── admin.py                 # /admin/*
│
├── utils/                       # Shared utilities
│   ├── __init__.py
│   ├── db.py                    # Supabase client instances + helpers
│   ├── face.py                  # InsightFace model + normalize_embedding
│   └── auth_helpers.py          # In-memory rate limiter
│
├── templates/                   # Jinja2 HTML templates
│   ├── login.html
│   ├── register.html
│   ├── index.html               # Attendance marking (main page)
│   ├── viewer.html              # Attendance records table
│   ├── students.html            # Student list
│   ├── add_student.html         # Student registration form
│   ├── edit_student.html        # Student edit form
│   ├── admin_dashboard.html     # Admin home
│   ├── admin_students.html      # Admin student list
│   ├── admin_users.html         # User management
│   ├── admin_edit_user.html     # User edit form
│   ├── admin_mark.html          # Manual attendance form
│   └── view_images.html         # Image viewer
│
├── static/
│   ├── css/
│   │   └── style.css            # BioSecure AI design system tokens + utilities
│   └── js/
│       └── script.js            # Shared JS utilities
│
├── known_faces/                 # Student reference photos (local backup)
├── nginx/
│   └── nginx.conf               # Nginx reverse-proxy config
└── docs/                        # All documentation
    ├── Agents.md
    ├── PRD.md
    ├── FAD.md
    ├── FTL.md
    ├── SAD.md
    ├── TAD.md                   # This file
    ├── Architecture.md
    ├── Rules.md
    ├── phases.md
    ├── design.md
    ├── memory.md
    ├── ARCHITECTURE.md
    ├── SETUP.md
    ├── DEPLOYMENT.md
    ├── DATABASE.md
    └── ADMIN_GUIDE.md
```

---

## 2. Module Reference

### `app.py`

| Symbol | Type | Description |
|---|---|---|
| `create_app()` | `function` | Application factory — creates and configures Flask instance |
| `app` | `Flask` | Convenience instance for Gunicorn (`app:app`) |
| `_configure_logging()` | `function` | Sets up root logger from `config.LOG_LEVEL` |
| `_is_api_request()` | `function` | Returns True for XHR/JSON requests (used by error handlers) |

**Registered Blueprints** (in order):
1. `auth_bp` — prefix: (none)
2. `attendance_bp` — prefix: (none)  
3. `students_bp` — prefix: (none)
4. `admin_bp` — prefix: `/admin`

---

### `config.py`

| Symbol | Type | Source | Default |
|---|---|---|---|
| `SUPABASE_URL` | `str` | `SUPABASE_URL` env | — |
| `SUPABASE_SERVICE_ROLE_KEY` | `str` | `SUPABASE_SERVICE_ROLE_KEY` env | — |
| `SUPABASE_ANON_KEY` | `str` | `SUPABASE_ANON_KEY` env | `""` |
| `KNOWN_FACES_DIR` | `str` | `KNOWN_FACES_DIR` env | `"known_faces"` |
| `FACE_MATCH_THRESHOLD` | `float` | `FACE_MATCH_THRESHOLD` env | `0.3` |
| `REATTENDANCE_INTERVAL_MINUTES` | `int` | `REATTENDANCE_INTERVAL_MINUTES` env | `10` |
| `INSIGHTFACE_CTX_ID` | `int` | `INSIGHTFACE_CTX_ID` env | `-1` |
| `EMAIL_USER` | `str` | `EMAIL_USER` env | `""` |
| `EMAIL_PASS` | `str` | `EMAIL_PASS` env | `""` |
| `LOGIN_MAX_ATTEMPTS` | `int` | `LOGIN_MAX_ATTEMPTS` env | `5` |
| `LOGIN_LOCKOUT_MINUTES` | `int` | `LOGIN_LOCKOUT_MINUTES` env | `15` |
| `MIN_PASSWORD_LENGTH` | `int` | `MIN_PASSWORD_LENGTH` env | `8` |
| `LOG_LEVEL` | `str` | `LOG_LEVEL` env | `"INFO"` |

---

### `utils/db.py`

| Symbol | Type | Description |
|---|---|---|
| `supabase` | `Client` | Anon key client (or service-role fallback) |
| `supabase_admin` | `Client` | Service-role client (bypasses RLS) |
| `is_valid_email(email)` | `bool` | Structural email validation |

**Import pattern:**
```python
from utils.db import supabase              # regular operations
from utils.db import supabase_admin        # admin operations only
from utils.db import supabase_admin as supabase  # admin blueprint pattern
```

---

### `utils/face.py`

| Symbol | Type | Description |
|---|---|---|
| `model` | `FaceAnalysis` | InsightFace `buffalo_l` instance (singleton) |
| `normalize_embedding(arr)` | `ndarray \| None` | L2-normalises a float32 array; returns None if norm is 0 |

**Lifecycle**: `model` is instantiated at **module import time**. This means the InsightFace model is loaded when the first worker imports `utils/face`, which happens at blueprint import time. Subsequent requests reuse the same model object.

---

### `utils/auth_helpers.py`

| Symbol | Type | Description |
|---|---|---|
| `is_account_locked(email)` | `(bool, int)` | Returns (locked, seconds_remaining) |
| `record_failed_login(email)` | `None` | Increments failure counter; locks on threshold |
| `clear_failed_logins(email)` | `None` | Resets counter on successful login |
| `remaining_attempts(email)` | `int` | How many failures before lockout |

**State**: Module-level dict `_login_attempts`. **Not** shared across Gunicorn workers.

---

### `blueprints/auth.py`

| Route | Method | Handler | Auth |
|---|---|---|---|
| `/login` | GET, POST | `login()` | Public |
| `/logout` | GET | `logout()` | Authenticated |
| `/register` | GET, POST | `register()` | Admin only |

---

### `blueprints/attendance.py`

| Route | Method | Handler | Auth |
|---|---|---|---|
| `/` | GET | `index()` | Authenticated |
| `/viewer` | GET | `viewer()` | Authenticated |
| `/get_attendance_data` | GET | `get_attendance_data()` | Authenticated |
| `/upload_photo` | POST | `upload_photo()` | Authenticated |

---

### `blueprints/students.py`

| Route | Method | Handler | Auth |
|---|---|---|---|
| `/students` | GET | `students()` | Authenticated |
| `/add_student` | GET | `add_student()` | Authenticated |
| `/submit_student` | POST | `submit_student()` | Authenticated |

---

### `blueprints/admin.py`

| Route | Method | Handler | Auth |
|---|---|---|---|
| `/admin` | GET | `admin_dashboard()` | Admin |
| `/admin/stats` | GET | `admin_stats()` | Admin |
| `/admin/students` | GET | `admin_students()` | Admin |
| `/admin/student/edit/<id>` | GET, POST | `admin_edit_student()` | Admin |
| `/admin/student/delete/<id>` | POST | `admin_delete_student()` | Admin |
| `/admin/mark` | GET, POST | `admin_mark_attendance()` | Admin |
| `/admin/view_images` | GET | `view_images()` | Admin |
| `/admin/users` | GET | `admin_users()` | Admin |
| `/admin/user/edit/<id>` | GET, POST | `admin_edit_user()` | Admin |
| `/admin/user/delete/<id>` | POST | `admin_delete_user()` | Admin |

---

## 3. Dependency Graph

```
app.py
  ├── config.py
  ├── blueprints/auth.py
  │     ├── utils/db.py  (supabase, supabase_admin)
  │     └── config.py
  ├── blueprints/attendance.py
  │     ├── utils/db.py  (supabase)
  │     ├── utils/face.py
  │     └── config.py
  ├── blueprints/students.py
  │     ├── utils/db.py  (supabase)
  │     ├── utils/face.py
  │     └── config.py
  └── blueprints/admin.py
        ├── utils/db.py  (supabase_admin)
        └── config.py

utils/db.py
  └── supabase-py (create_client)

utils/face.py
  ├── insightface (FaceAnalysis)
  └── config.py (INSIGHTFACE_CTX_ID)

utils/auth_helpers.py
  └── config.py (LOGIN_MAX_ATTEMPTS, LOGIN_LOCKOUT_MINUTES)
```

---

## 4. Template Inheritance

Currently, templates do **not** use Jinja2 `extends`/`block` inheritance — each template is standalone and includes its own `<head>`, navigation, and scripts. This is intentional for simplicity, but creates code duplication in the nav bar and head section.

**Future improvement**: Create `templates/base.html` with a Jinja content block for DRY navigation.

---

## 5. Frontend Architecture

### CSS Framework
- **TailwindCSS** (CDN `v3`) — utility classes used inline in templates
- **BioSecure AI custom classes** (`static/css/style.css`) — glassmorphic utilities: `.glass-panel`, `.glass-card`, `.btn-primary-glass`, etc.
- **Google Fonts**: Geist (headings) + Inter (body)

### Icons
- **Lucide** (`unpkg.com/lucide@latest`) — `data-lucide` attribute icons, initialised with `lucide.createIcons()`

### JavaScript
All JavaScript is inline in templates (no module bundler). Key patterns:
- `DataTransfer` API for programmatic file management
- `navigator.mediaDevices.getUserMedia` for webcam
- `fetch()` for async form submissions
- `base64` image display from server response
- Client-side CSV generation via `data:text/csv` URI

---

## 6. Database Schema

```sql
-- Extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Students
CREATE TABLE students (
    id        text PRIMARY KEY,
    name      text NOT NULL,
    program   text,
    branch    text,
    gmail     text,
    embedding vector(512)
);

-- Attendance
CREATE TABLE attendance (
    id         bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    student_id text REFERENCES students(id),
    name       text,
    program    text,
    branch     text,
    status     text,
    timestamp  text,   -- 'YYYY-MM-DD HH:MM:SS'
    lecture    text,
    section    text
);

-- Face matching RPC
CREATE OR REPLACE FUNCTION match_face(
    query_embedding vector(512),
    match_threshold float
) RETURNS TABLE (id text, name text, similarity float)
LANGUAGE sql STABLE AS $$
    SELECT id, name, 1 - (embedding <=> query_embedding) AS similarity
    FROM   students
    WHERE  embedding IS NOT NULL
    AND    1 - (embedding <=> query_embedding) >= match_threshold
    ORDER  BY embedding <=> query_embedding
    LIMIT  1;
$$;
```

---

## 7. Key Design Decisions

| Decision | Rationale |
|---|---|
| **Application factory pattern** | Enables testing, multiple environments, and blueprint isolation |
| **Supabase over raw PostgreSQL** | Managed Auth, RLS, pgvector, and REST API out-of-the-box |
| **Service-role key for admin routes** | Bypass RLS to accurately count all users/records |
| **InsightFace buffalo_l** | State-of-the-art open-source model; ONNX allows CPU/GPU flexibility |
| **pgvector for embedding storage** | Eliminates local file state; enables horizontal scaling |
| **Sync Gunicorn workers** | InsightFace is CPU-bound; async workers provide no benefit |
| **No template inheritance** | Simplicity; each page is self-contained and easy to modify |
