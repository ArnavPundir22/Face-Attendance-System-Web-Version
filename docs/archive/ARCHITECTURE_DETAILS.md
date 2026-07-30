# 🏗️ System Architecture & Logic Flowcharts

This document describes the design patterns, runtime architecture, reverse proxy pipelines, and sequence flows of **BioSecure AI**.

---

## 1. Modular Execution Pipeline

The server stack utilizes **Nginx** as a reverse proxy, forwarding connection requests to **Gunicorn** which manages sync workers running the **Flask Application Factory**.

```
  [ Web Client ] 
        │ (HTTPS)
        ▼
  [ Nginx Reverse Proxy (Port 80/443) ]
        │ (HTTP proxy to loopback)
        ▼
  [ Gunicorn Process Manager (Port 8000) ]
        │ (WSGI Interface)
        ▼
  [ Flask Blueprint Router (create_app) ]
```

---

## 2. Interactive Logic Flowcharts

### 2.1 Student Registration Flow

When an administrator submits a new student profile, the server validates inputs, generates a face embedding from the photo, and stores the metadata alongside the vector in Supabase.

```mermaid
sequenceDiagram
    autonumber
    actor Admin as System Administrator
    participant Flask as Flask Server (blueprints/students)
    participant Model as InsightFace Engine (buffalo_l)
    participant DB as Supabase Database (PostgreSQL)

    Admin->>Flask: POST /submit_student (ID, Name, Branch, Email + Photo)
    Note over Flask: 1. Validate inputs<br/>2. Guard: duplicate ID or Name
    Flask->>DB: Query matches (select where id = ID or name = Name)
    DB-->>Flask: Returns count (0 = Proceed)
    Note over Flask: 3. Save photo reference to known_faces/
    Flask->>Model: Run model.get(frame) on uploaded image
    Model-->>Flask: Return Bounding Box & Raw Embedding (512D)
    Note over Flask: 4. Normalise embedding (L2 Norm)
    Flask->>DB: INSERT INTO students (id, name, program, branch, gmail, embedding)
    DB-->>Flask: HTTP 201 Created (Success)
    Flask-->>Admin: Redirect with Success Message
```

---

### 2.2 Facial Recognition & Attendance Marking Flow

The attendance marking process receives webcam frames or uploaded photos, aligns faces, processes matching vectors, checks cooldown constraints, and logs transactions.

```mermaid
sequenceDiagram
    autonumber
    actor Browser as Faculty UI / Client Webcam
    participant Flask as Flask Server (blueprints/attendance)
    participant Model as InsightFace Engine (buffalo_l)
    participant DB as Supabase Database (PostgreSQL)

    Browser->>Flask: POST /upload_photo (Images, Lecture, Program, Branch)
    loop Per Uploaded Image
        Flask->>Flask: Decode bytes using OpenCV
        Flask->>Model: Run model.get(frame)
        Model-->>Flask: Return Bounding Boxes & raw Embeddings
        loop Per Detected Face
            Note over Flask: L2 Normalise raw embedding vector
            Flask->>DB: RPC match_face(query_embedding, threshold=0.3)
            DB-->>Flask: Return Top Match (Student ID, Name, Similarity)
            
            alt Match found && Similarity >= Threshold
                Flask->>DB: SELECT timestamp FROM attendance WHERE student_id = ID AND lecture = LECTURE ORDER BY timestamp DESC LIMIT 1
                DB-->>Flask: Return last timestamp (if any)
                
                alt Time elapsed < Cooldown (10 minutes)
                    Note over Flask: Set status to "Already Marked"
                else Time elapsed >= Cooldown or No previous record
                    Flask->>DB: INSERT INTO attendance (student_id, name, program, branch, status="Present", timestamp, lecture)
                    DB-->>Flask: Insertion Confirmed
                    Note over Flask: Set status to "Present"
                end
            else Match not found or Similarity < Threshold
                Note over Flask: Set status to "Absent" (Unknown Face)
            end
            Note over Flask: Crop face & Draw annotated bbox / name on frame
        end
    end
    Note over Flask: Encode annotated frame to Base64 JPEG
    Flask-->>Browser: JSON response (session logs, annotated images)
```

---

## 3. Modular Blueprint Configuration

The backend is cleanly structured into Flask Blueprints to isolate responsibilities:

| Blueprint Module | Route Prefix | Responsibility |
| :--- | :--- | :--- |
| **`auth_bp`** | `/` | User login, registration, session validation, and logout. |
| **`students_bp`**| `/` | Directory listing of registered students and registration forms. |
| **`attendance_bp`**| `/` | Webcam index interface, live attendance processor, viewer history, and statuses. |
| **`admin_bp`** | `/admin` | Admin dashboards, student and user deletion, and manual marking forms. |
