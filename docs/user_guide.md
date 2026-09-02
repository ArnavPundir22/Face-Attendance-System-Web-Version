# 👤 User & Administrator Guide

This guide explains how to operate **BioSecure AI**, manage students, verify logs, and download attendance reports.

---

## 🔑 User Roles

BioSecure AI supports role-based access controls (RBAC):
- **User (Teacher)**:
  - Can take group attendance via webcam or upload.
  - Can view general lists and statistics.
- **Admin**:
  - Full dashboard administration.
  - Register new student profiles.
  - Edit or delete student records.
  - Grant admin rights to new user accounts.

---

## 👥 Registering a New Student

To ensure the AI can identify a student, you must register them with a clear, single-face portrait:

1. Log in with an **Admin** account.
2. Click **Add Student** in the navigation header.
3. Enter the student's **Full Name** and **Unique Roll Number**.
4. Upload a clean, front-facing portrait. Avoid hats, masks, or extreme lighting conditions.
5. Click **Submit**. The system will:
   - Detect the face using RetinaFace.
   - Extract a 512-dimensional embedding vector.
   - Save the details and embedding to the database.

---

## 📷 Running Group Attendance

To record attendance for a classroom:

1. Click **Take Attendance** (the main dashboard page).
2. Choose your method:
   - **Upload File**: Select a high-resolution photo showing the students sitting in the classroom.
   - **Webcam Mode**: Utilize the connected webcam feed to take active snapshots of the room.
3. Click **Process**.
4. The system outputs:
   - An annotated image: Green boxes for matched students, Red boxes with "Unknown" labels for faces that do not match any registered student.
   - A results sidebar listing identified students.
5. Marked records are instantly written as `Present` status inside `attendance_logs` in Supabase.

---

## 📊 Reviewing and Exporting Logs

1. Navigate to the **Attendance Viewer** tab.
2. Filter attendance entries dynamically by Date, Student Name, or Roll Number.
3. Click the **Export to CSV** button to download the filtered logs directly into a spreadsheet-ready format.

---

## 🛠️ Troubleshooting & Storage Handling

* **Automatic Folder Initialization**:
  - Uploaded enrollment photos are stored in `known_faces/` (configurable via `KNOWN_FACES_DIR`). The system automatically provisions this folder on first upload to prevent file write errors.
* **500 Server Connection Errors**:
  - If a 500 internal server error page is encountered, check application logs for database or dependency connectivity. API requests with standard JSON request headers (`Accept: application/json`) will receive structured JSON error bodies instead of HTML pages.

