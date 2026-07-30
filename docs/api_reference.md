# 🔌 API Reference Manual

This manual documents the REST endpoints, expected payloads, and responses for **BioSecure AI**.

---

## 🔑 Authentication Endpoints

### `POST /login`
Authenticates a user session against Supabase Auth.
- **Request Headers**: `Content-Type: application/x-www-form-558enc` (Form submit)
- **Request Body**:
  - `email` (string): User email address.
  - `password` (string): User password.
- **Success Response**: Redirects to index `/` and sets session cookie.
- **Error Response**: Renders `login.html` with error message.

### `GET /logout`
Terminates the active session and clears cookies.
- **Success Response**: Redirects to `/login`.

---

## 📷 Attendance Endpoints

### `POST /upload_photo`
Uploads a classroom image to process and mark attendance.
- **Request Headers**: `Content-Type: multipart/form-data`
- **Request Body**:
  - `file` (file binary): The classroom group image (JPEG/PNG).
- **Success Response (200 OK - JSON)**:
  ```json
  {
    "matches": [
      {
        "name": "Jane Doe",
        "roll_number": "CSE-2026-045",
        "similarity": 0.895
      }
    ],
    "unknown_count": 2,
    "image": "data:image/jpeg;base64,/9j/4AAQSkZJR..."
  }
  ```
- **Error Responses**:
  - `400 Bad Request`: `{"error": "No file uploaded"}`
  - `500 Internal Error`: `{"error": "Internal server error"}`

### `GET /get_attendance_data`
Retrieves full attendance log lists.
- **Query Parameters**: None.
- **Success Response (200 OK - JSON)**:
  ```json
  {
    "students": [
      {
        "id": "a1b2c3d4-...",
        "name": "Jane Doe",
        "roll_number": "CSE-2026-045"
      }
    ],
    "attendance": [
      {
        "id": 1024,
        "student_id": "a1b2c3d4-...",
        "timestamp": "2026-07-30T13:45:00Z",
        "status": "Present"
      }
    ]
  }
  ```

---

## 👥 Student Registry Endpoints

### `POST /submit_student`
Registers a new student profile and generates their face embedding.
- **Request Headers**: `Content-Type: multipart/form-data`
- **Request Body**:
  - `name` (string): The student's full name.
  - `roll_number` (string): A unique roll number or ID.
  - `file` (file binary): A clear portrait photo of the student.
- **Success Response**: Redirects to `/students`.
- **Error Response**: Renders `add_student.html` with error message.
