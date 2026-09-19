# 🔌 REST API Reference Manual

This manual documents all REST endpoints, request parameters, JSON payloads, responses, and error codes for **BioSecure AI**, including attendance processing, neural ID card OCR scanning, and the **Biometric Embedding Drift Engine (2026 Patent Application)**.

---

## 🔑 Authentication Endpoints

### `POST /login`
Authenticates a user session against Supabase Auth.
- **Request Headers**: `Content-Type: application/x-www-form-urlencoded`
- **Request Body**:
  - `email` (string): User email address.
  - `password` (string): User password.
- **Success Response (302 Found)**: Redirects to `/` index page and sets session cookies (`SESSION_COOKIE_SAMESITE`, `SESSION_COOKIE_HTTPONLY`).

### `GET /logout`
Terminates active user session.
- **Success Response (302 Found)**: Clears Flask session and redirects to `/login`.

### `GET /login/oauth/<provider>`
Initiates OAuth PKCE authentication flow for Google, GitHub, or LinkedIn.
- **Path Parameter**: `provider` (`google`, `github`, `linkedin`).
- **Success Response (302 Found)**: Redirects user to OAuth provider sign-in portal.

### `GET /auth/callback`
OAuth callback endpoint handling authorization code exchange.
- **Query Parameters**: `code` (string), `error_description` (optional).
- **Success Response (302 Found)**: Exchanges code for session token and redirects to `/`.

---

## 📷 Attendance Endpoints

### `POST /upload_photo`
Uploads classroom images to process attendance, identify faces, and calculate pose-gated EWMA drift scores.
- **Request Headers**: `Content-Type: multipart/form-data`
- **Request Body**:
  - `images` (file binary list): One or more classroom group photos (JPEG/PNG).
  - `lecture` (string, optional): Lecture title or session label.
  - `program` (string, optional): Program name or `Auto-Detect`.
  - `branch` (string, optional): Branch name or `Auto-Detect`.
  - `year` / `enrollment_year` (string, optional): Batch year or `Auto-Detect`.
  - `is_combined_class` (string, optional): `'true'` for multi-branch joint lectures, `'false'` for separate single class.
- **Success Response (200 OK - JSON)**:
  ```json
  {
    "images": [
      {
        "results": [
          {
            "name": "Jane Doe",
            "status": "Present",
            "confidence": "0.89",
            "drift_alert": "HEALTHY",
            "pose_accepted": true
          }
        ],
        "annotated": "data:image/jpeg;base64,/9j/4AAQSkZJR..."
      }
    ],
    "session_attendance": [
      ["CU240251013", "Jane Doe", "B.Tech", "CSE", "Present", "2026-09-19 20:30:00", "Session 1"]
    ],
    "detected_program": "B.Tech",
    "detected_branch": "CSE",
    "detected_year": 2024,
    "is_combined_class": false
  }
  ```

### `GET /get_attendance_data`
Retrieves full attendance log records and student directory for the live viewer dashboard.
- **Success Response (200 OK - JSON)**:
  ```json
  {
    "attendance": [
      ["CU240251013", "Jane Doe", "B.Tech", "CSE", "2024", "Present", "2026-09-19 20:30:00", "Session 1"]
    ],
    "students": [
      {
        "id": "CU240251013",
        "name": "Jane Doe",
        "program": "B.Tech",
        "branch": "CSE",
        "enrollment_year": 2024,
        "batch_year": 2024
      }
    ]
  }
  ```

### `POST /update_attendance_status`
Manually toggles or updates a specific student's attendance status for a session.
- **Request Headers**: `Content-Type: application/json`
- **Request Body**:
  ```json
  {
    "student_id": "CU240251013",
    "lecture": "Session 1",
    "timestamp": "2026-09-19 20:30:00",
    "status": "Absent"
  }
  ```
- **Success Response (200 OK - JSON)**: `{"success": true}`

### `GET /api/academic_options`
Fetches distinct programs, branches, and batch years registered in the system.
- **Success Response (200 OK - JSON)**:
  ```json
  {
    "programs": ["B.Tech", "BCA", "M.Tech"],
    "branches": ["CSE", "ECE", "IT", "ME"],
    "years": [2026, 2025, 2024, 2023]
  }
  ```

---

## 💳 Student Enrollment & Neural OCR Endpoints

### `POST /submit_student`
Registers a new student profile, saves reference photo to `known_faces/`, extracts 512D ArcFace embedding, and updates in-memory BLAS matrix cache.
- **Request Headers**: `Content-Type: multipart/form-data`
- **Request Body**:
  - `name` (string, required): Full student name.
  - `id` (string, required): Student ID / Roll Number.
  - `program` (string): Academic program (e.g. B.Tech).
  - `branch` (string): Academic branch (e.g. CSE).
  - `email` (string): Student email.
  - `enrollment_year` (int): 4-digit batch year (e.g. 2024).
  - `academic_year` (string): Academic session string.
  - `photo` (file binary, required): Portrait image.
- **Success Response (200 OK - JSON / Redirect)**:
  ```json
  {
    "success": true,
    "message": "Student profile for \"Jane Doe\" (ID: CU240251013) successfully registered!"
  }
  ```

### `POST /api/ocr_id_card`
Scans physical ID cards using pretrained RapidOCR (DBNet + SVTR ONNX) and PyTesseract to extract enrollment fields.
- **Request Headers**: `Content-Type: multipart/form-data` or `application/json`
- **Request Body** (Multipart): `id_card_image` (file binary) or `raw_text` (string).
- **Request Body** (JSON): `{"image_data": "data:image/jpeg;base64,...", "raw_text": ""}`
- **Success Response (200 OK - JSON)**:
  ```json
  {
    "success": true,
    "parsed_data": {
      "name": "Arnav Pundir",
      "id": "CU240251013",
      "program": "B.Tech",
      "branch": "CSE",
      "enrollment_year": "2024",
      "email": "cu240251013@coeruniversity.ac.in"
    },
    "raw_text": "COER UNIVERSITY\nName: Arnav Pundir\nCU-ID: CU240251013\nProgram: B.Tech (CSE)..."
  }
  ```

---

## 🛡️ Embedding Drift & Patent Admin Endpoints (Patent #3)

### `GET /admin/drift`
Renders the Biometric Embedding Drift Management Dashboard.
- **Access Control**: Admin role required (`is_admin = true`).
- **Context**: Supplies student list sorted by highest `current_ewma_drift`, flagging accounts in `WARNING`, `CRITICAL`, or `ALERT` states.

### `GET /api/drift_history/<student_id>`
Retrieves historical EWMA drift log events for a specific student.
- **Path Parameter**: `student_id` (string).
- **Success Response (200 OK - JSON)**:
  ```json
  {
    "success": true,
    "data": [
      {
        "created_at": "2026-09-19T20:30:00Z",
        "drift_score": 0.22,
        "ewma_drift": 0.18,
        "match_confidence": 0.78,
        "pose_yaw": 12.4,
        "pose_pitch": -8.1,
        "pose_accepted": true,
        "alert_level": "WARNING"
      }
    ]
  }
  ```

### `POST /student/reset_drift/<student_id>`
Resets student EWMA drift score to `0.0` (`HEALTHY`) upon single-click re-enrollment.
- **Path Parameter**: `student_id` (string).
- **Success Response (302 Found)**: Resets database drift score and redirects to `/admin/drift`.

---

## 🏥 Health Monitoring Endpoint

### `GET /healthz`
Health check endpoint for container orchestrators, Nginx proxies, and load balancers.
- **Success Response (200 OK - JSON)**:
  ```json
  {
    "status": "ok",
    "service": "biosecure-ai-face-attendance"
  }
  ```

---

## ⚠️ Error Handling & Status Codes

BioSecure AI includes built-in error handlers for standard HTTP error statuses (`403`, `404`, `500`):

- **API Requests** (`Accept: application/json` or `X-Requested-With: XMLHttpRequest`):
  - Returns structured JSON payloads (e.g., `{"error": "Resource not found"}`) with appropriate HTTP status codes.
- **Browser Requests**:
  - Renders custom glassmorphic HTML error pages (`error_404.html`, `error_403.html`, `error_500.html`).
