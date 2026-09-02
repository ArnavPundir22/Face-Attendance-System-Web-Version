# 🔌 API Reference Manual

This manual documents the REST endpoints, expected payloads, and responses for **BioSecure AI**, including the **Biometric Embedding Drift Engine (2026 Patent Application)**.

---

## 🔑 Authentication Endpoints

### `POST /login`
Authenticates a user session against Supabase Auth.
- **Request Headers**: `Content-Type: application/x-www-form-urlencoded`
- **Request Body**:
  - `email` (string): User email address.
  - `password` (string): User password.
- **Success Response**: Redirects to `/` and sets session cookie.

### `GET /logout`
Terminates the active session.
- **Success Response**: Redirects to `/login`.

---

## 📷 Attendance Endpoints

### `POST /upload_photo`
Uploads a classroom image to process attendance and update individual EWMA drift scores.
- **Request Headers**: `Content-Type: multipart/form-data`
- **Request Body**:
  - `file` (file binary): Classroom group photo (JPEG/PNG).
- **Success Response (200 OK - JSON)**:
  ```json
  {
    "matches": [
      {
        "id": "a1b2c3d4-...",
        "name": "Jane Doe",
        "roll_number": "CSE-2026-045",
        "similarity": 0.895,
        "ewma_drift": 0.105,
        "drift_status": "HEALTHY"
      }
    ],
    "unknown_count": 1,
    "image": "data:image/jpeg;base64,/9j/4AAQSkZJR..."
  }
  ```

### `GET /get_attendance_data`
Retrieves attendance records for the live dashboard.
- **Success Response (200 OK - JSON)**: Returns JSON list of student profiles and attendance log timestamps.

---

## 🛡️ Embedding Drift & Patent Admin Endpoints (Patent #3)

### `GET /admin/drift`
Renders the Biometric Embedding Drift Management Dashboard.
- **Access Control**: Admin users only (`is_admin = true`).
- **Template Context**: Supplies list of students sorted by highest `current_ewma_drift`, flagging accounts in `WARNING`, `CRITICAL`, or `ALERT` states.

### `GET /api/drift_history/<student_id>`
Retrieves historical EWMA drift log events for a specific student.
- **Path Parameter**: `student_id` (UUID).
- **Success Response (200 OK - JSON)**:
  ```json
  {
    "student_id": "a1b2c3d4-...",
    "history": [
      {
        "timestamp": "2026-08-01T10:15:00Z",
        "instantaneous_drift": 0.22,
        "ewma_drift": 0.18,
        "yaw_angle": 12.4,
        "pitch_angle": -8.1,
        "status": "OK"
      }
    ]
  }
  ```

### `POST /student/reset_drift/<student_id>`
Resets a student's EWMA drift score to `0.0` (`HEALTHY`) upon single-click re-enrollment.
- **Path Parameter**: `student_id` (UUID).
- **Success Response (200 OK - JSON)**:
  ```json
  {
    "success": true,
    "message": "Student drift score successfully reset to HEALTHY."
  }
  ```

---

## 👥 Student Registry Endpoints

### `POST /submit_student`
Registers a new student profile and generates their base 512D ArcFace facial embedding.
- **Request Headers**: `Content-Type: multipart/form-data`
- **Request Body**:
  - `name` (string): Student's full name.
  - `roll_number` (string): Unique roll number.
  - `file` (file binary): Enrollment portrait photo.
- **Success Response**: Redirects to `/students`.

---

## ⚠️ Error Handling & Status Codes

BioSecure AI includes built-in error handlers for standard HTTP error statuses (`403`, `404`, `500`):

* **API Requests** (`Accept: application/json` or `X-Requested-With: XMLHttpRequest`):
  - Returns structured JSON payloads (e.g., `{"error": "Internal server error"}`) with the appropriate HTTP status code.
* **Browser Requests**:
  - Renders custom glassmorphic HTML error pages (`error_404.html`, `error_403.html`, `error_500.html`).

### File Upload & Storage Safeguards
- **Auto-Directory Provisioning**: The server automatically initializes and creates the designated face photo directory (`config.KNOWN_FACES_DIR` / `known_faces/`) using `os.makedirs(..., exist_ok=True)` prior to saving uploaded student enrollment portraits, preventing missing directory `FileNotFoundError` (HTTP 500) failures during student registration (`/submit_student`) and profile updates.

