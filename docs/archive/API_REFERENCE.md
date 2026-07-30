# 🔌 API Reference Manual

This document details the REST API endpoints and form interfaces exposed by the BioSecure AI application server.

---

## 1. Authentication Routes

### `POST /login`
Authenticates administration users to grant portal sessions.
* **Payload**: Form Data
  * `username` (string, required)
  * `password` (string, required)
* **Response**:
  * Redirects to `/` on success
  * Renders `/login` with an error message on failure

---

## 2. Attendance Operations

### `POST /upload_photo`
Submits image frames containing student groups or individuals, matches faces, and logs attendance.
* **Payload**: Multipart Form Data
  * `images` (file binary, required - can be multiple)
  * `lecture` (string, required)
* **Response (JSON)**:
  ```json
  {
    "images": [
      {
        "annotated": "data:image/jpeg;base64,...",
        "results": [
          {
            "confidence": 0.824,
            "name": "Arnav Pundir",
            "status": "Present",
            "timestamp": "2026-07-30 12:15:00"
          }
        ]
      }
    ],
    "session_attendance": [
      ["221199", "Arnav Pundir", "B.Tech", "CSE", "Present", "2026-07-30 12:15:00", "OS Lecture"]
    ],
    "detected_program": "B.Tech",
    "detected_branch": "CSE"
  }
  ```

---

### `POST /update_attendance_status`
Manually updates or inserts individual attendance log statuses.
* **Payload**: JSON
  ```json
  {
    "student_id": "221199",
    "lecture": "OS Lecture",
    "timestamp": "2026-07-30 12:15:00",
    "status": "Absent"
  }
  ```
* **Response (JSON)**:
  * **Success (200 OK)**:
    ```json
    { "success": true }
    ```
  * **Error (400 Bad Request)**:
    ```json
    { "success": false, "error": "Missing parameters" }
    ```

---

### `GET /get_attendance_data`
Fetches attendance logs from the last 7 days and the complete student list.
* **Response (JSON)**:
  ```json
  {
    "attendance": [
      ["221199", "Arnav Pundir", "B.Tech", "CSE", "Present", "2026-07-30 12:15:00", "OS Lecture"]
    ],
    "students": [
      { "id": "221199", "name": "Arnav Pundir", "branch": "CSE", "program": "B.Tech" }
    ]
  }
  ```

---

## 3. Student Records Management

### `POST /submit_student`
Registers a new student profile and maps their facial identity profile.
* **Payload**: Multipart Form Data
  * `id` (string, required - Enrollment/Student ID)
  * `name` (string, required)
  * `program` (string, required)
  * `branch` (string, required)
  * `email` (string, required)
  * `enrollment_year` (string, optional)
  * `academic_year` (string, optional)
  * `photo` (file binary, required - Portrait JPG/PNG)
* **Response**:
  * Redirects to `/add_student` with `status=success` on successful registration.
  * Redirects to `/add_student` with `status=error` and a descriptive message in case of failure.
