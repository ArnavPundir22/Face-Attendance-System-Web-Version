# 🏗️ Feature Architecture Document (FAD)
# BioSecure AI

**Version**: 2.0  
**Last Updated**: 2026-07-14  

---

## 1. Authentication Feature

### Architecture
The authentication system is a thin wrapper around **Supabase Auth** (email/password provider).

```
Browser → POST /login (email, password)
              ↓
         auth_bp.login()
              ↓
         supabase.auth.sign_in_with_password({email, password})
              ↓ (success)
         Extract user_metadata: {username, is_admin}
              ↓
         Flask session: {logged_in, username, is_admin, user_id, access_token}
              ↓
         redirect → /
```

### Components
| Component | File | Responsibility |
|---|---|---|
| Login route | `blueprints/auth.py` | POST handler, session management |
| Logout route | `blueprints/auth.py` | Session clear, Supabase sign-out |
| Register route | `blueprints/auth.py` | Admin-only user creation |
| Rate limiter | `utils/auth_helpers.py` | In-memory lockout after N failures |
| Auth guard | `app.py → before_request` | Redirects unauthenticated requests |
| DB client | `utils/db.py → supabase` | Supabase Auth calls |

### Session Lifecycle
1. **Login** → session populated with user identity.
2. **Every request** → `before_request` checks `session['logged_in']`.
3. **Logout** → `supabase.auth.sign_out()` + `session.clear()`.
4. **Token refresh** → not implemented (Supabase JWT expires after 1hr; user must re-login).

### Security Controls
- Passwords never stored by Flask — handled by Supabase Auth.
- Failed login counter tracked per email address.
- Admin creation requires existing admin session.
- Last admin account cannot be deleted or demoted.

---

## 2. Face Recognition Pipeline

### End-to-End Flow

```
File Upload / Webcam Capture
         ↓
POST /upload_photo (multipart/form-data: images[], lecture, section)
         ↓
attendance_bp.upload_photo()
         ↓ (per file)
np.frombuffer → cv2.imdecode → BGR frame
         ↓
utils/face.model.get(frame)         → List[Face]
         ↓ (per face)
face.embedding → normalize_embedding() → float32[512]
         ↓
supabase.rpc('match_face', {
    query_embedding: float[],
    match_threshold: 0.3
})                                  → {id, name, similarity}
         ↓
Attendance cooldown check
         ↓
supabase.table('attendance').insert({...})
         ↓
cv2.rectangle + cv2.putText → annotated frame
         ↓
cv2.imencode → base64 JPEG
         ↓
JSON response: {images: [{annotated, results}], session_attendance}
```

### Key Parameters

| Parameter | Config Key | Default | Effect |
|---|---|---|---|
| Cosine threshold | `FACE_MATCH_THRESHOLD` | 0.3 | Min similarity to count as a match |
| GPU/CPU | `INSIGHTFACE_CTX_ID` | -1 (CPU) | -1=CPU, 0=GPU |
| Cooldown | `REATTENDANCE_INTERVAL_MINUTES` | 10 | Minutes between re-marks |

### Model Details
- **Model**: `buffalo_l` (ArcFace R100 backbone + RetinaFace detector)
- **Embedding size**: 512 dimensions
- **Normalisation**: L2-normalised (`arr / np.linalg.norm(arr)`)
- **Storage**: PostgreSQL `vector(512)` column via pgvector
- **Similarity metric**: Cosine similarity (`1 - cosine_distance`)

### Error States

| Condition | Returned Status | Action |
|---|---|---|
| No face in image | `[]` results | "No faces detected" shown |
| Similarity < threshold | `Unknown` | Not logged |
| Student not in DB | `Not Found` | Not logged |
| Within cooldown | `Already Marked` | Not logged (duplicate prevention) |
| DB RPC error | `[]` match_data | Caught, logged, treated as Unknown |

---

## 3. Student Management Feature

### Registration Flow
```
POST /submit_student (name, id, program, branch, mobile, email, photo)
         ↓
Validate: name, id, photo present
         ↓
Duplicate check: supabase.table('students').select().or_(id.eq | name.ilike)
         ↓
secure_filename(name) → save photo to known_faces/{name}.jpg
         ↓
cv2.imread → model.get() → embedding[0]
         ↓
normalize_embedding() → float32[512]
         ↓
supabase.table('students').insert({id, name, ..., embedding})
         ↓
redirect /add_student?status=success
```

### Data Schema (`students` table)
```sql
CREATE TABLE students (
    id        text PRIMARY KEY,
    name      text NOT NULL,
    program   text,
    branch    text,
    mobile    text,
    gmail     text,
    embedding vector(512)
);
```

### Constraints
- One face per student (first detected face used for enrollment).
- Photos saved to `known_faces/` for reference only — not used for matching.
- Actual matching uses pgvector embeddings in the database.
- Duplicate guard: exact ID match OR case-insensitive name match.

---

## 4. Attendance Records Feature

### Data Schema (`attendance` table)
```sql
CREATE TABLE attendance (
    id         bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    student_id text REFERENCES students(id),
    name       text,
    program    text,
    branch     text,
    mobile     text,
    status     text,   -- 'Present' | 'Absent'
    timestamp  text,   -- 'YYYY-MM-DD HH:MM:SS'
    lecture    text,
    section    text
);
```

### Viewer (`GET /viewer`)
- Full attendance table rendered via `templates/viewer.html`.
- Client-side DataTable with search, filter, and CSV export.
- Data fetched from `GET /get_attendance_data` → JSON array of arrays.

### CSV Export
- Generated entirely client-side from the `session_attendance` array returned by `/upload_photo`.
- Viewer page uses DataTables built-in CSV button for full-table export.

---

## 5. Admin Dashboard Feature

### Stats Endpoint (`GET /admin/stats`)
Returns JSON used by the dashboard's chart:
```json
{
  "trend": [{"date": "2026-07-08", "count": 42}, ...],  // 7-day
  "present": 38,
  "absent": 4
}
```

### Dashboard Metrics (server-side, at page load)
```python
total_students   = supabase_admin.table('students').select(count='exact')
total_attendance = supabase_admin.table('attendance').select(count='exact')
total_users      = len(supabase_admin.auth.admin.list_users())
today_attendance = supabase_admin.table('attendance').ilike('timestamp', 'YYYY-MM-DD%')
```

> [!NOTE]
> `supabase_admin` (service-role key) is used to bypass RLS for accurate counting.

### Manual Attendance (`POST /admin/mark`)
- Admin selects student from dropdown, chooses status, lecture, section.
- Record inserted directly without face verification.
- Used for exceptions: sick students, late arrivals, etc.

---

## 6. User Management Feature

### Operations Available

| Operation | API Call | Guard |
|---|---|---|
| List users | `auth.admin.list_users()` | `is_admin` session |
| Get user | `auth.admin.get_user_by_id(id)` | `is_admin` session |
| Update user | `auth.admin.update_user_by_id(id, {...})` | `is_admin` session |
| Delete user | `auth.admin.delete_user(id)` | `is_admin` + not self + not last admin |
| Create user | `auth.admin.create_user({...})` | `is_admin` session (via `/register`) |

### Admin Promotion / Demotion
Admin status stored in `user_metadata.is_admin` (bool) on the Supabase Auth user object.

SQL to bootstrap first admin:
```sql
UPDATE auth.users
SET raw_user_meta_data = jsonb_build_object('is_admin', true, 'username', 'admin')
WHERE email = 'your-admin@example.com';
```

---

## 7. Health Check Feature

### Endpoint: `GET /healthz`

```json
{"status": "ok", "service": "biosecure-ai-face-attendance"}
```

Used by:
- Container orchestrators (Kubernetes, Docker Compose health checks)
- Load balancers (Nginx upstream checks)
- PaaS platforms (Render, Railway)
- Uptime monitoring services (UptimeRobot, Betterstack)
