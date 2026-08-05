# 🏗️ System Architecture Guide

This document describes the design patterns, application structure, and execution lifecycles of **BioSecure AI**, including both the **Primary Facial Recognition Attendance Pipeline** and the novel **Pose-Gated EWMA Embedding Drift Engine (2026 Patent Application)**.

---

## 📁 Production-Grade Directory Structure

BioSecure AI is organized using the standard **Python Application Factory** layout:

```
/
├── app.py                      # Flask development entrypoint
├── wsgi.py                     # Production WSGI entrypoint (gunicorn wsgi:app)
├── config.py                   # Global configuration loading (.env mapping)
├── requirements.txt            # Project python dependencies
├── gunicorn.conf.py            # Gunicorn WSGI daemon configurations
├── Procfile                    # Deployment configuration for PaaS
│
├── IDF/                        # Official 2026 Patent Filing Package
│   ├── New Patent IDF.docx     # Invention Disclosure Form (Full System & Math)
│   └── Patent_Prior_Art_Search_Report.docx # Global Prior Art Search Report (2018-2026)
│
├── src/                        # Main Application Code
│   ├── __init__.py            # Application factory initialization (create_app)
│   ├── config.py              # Centralised configuration (overrides via .env)
│   ├── blueprints/            # Blueprint route modules (Controllers)
│   │   ├── admin.py           # Admin routes: user management, /admin/drift dashboard, resets
│   │   ├── attendance.py      # Attendance marking, group photo processing, EWMA drift engine
│   │   ├── auth.py            # User registration & session auth helpers
│   │   └── students.py        # Student records & enrollment management
│   │
│   ├── utils/                 # Sub-system Utilities (Services)
│   │   ├── auth_helpers.py    # Login rate limits & brute-force protection
│   │   ├── db.py              # Supabase Client connections (Anon & Service Role)
│   │   └── face.py            # InsightFace ArcFace 512D & pose angle inference
│   │
│   ├── templates/             # HTML Templates (Jinja2, admin_drift.html)
│   └── static/                # CSS, client JS, particle canvas assets
│
├── scripts/                    # Maintenance & Setup Scripts
└── docs/                       # System Documentation Hub
```

---

## 🔄 Request Execution Lifecycle & Dual Pipeline

When an attendance photo is uploaded, the request transitions through Nginx, Gunicorn, the Flask Blueprint, the ML face model, performs a vector matching query on Supabase, and concurrently executes the Pose-Gated EWMA Drift Engine:

```mermaid
sequenceDiagram
    autonumber
    actor Client as Instructor Web App
    participant Proxy as Nginx / Gunicorn
    participant App as Attendance Controller (attendance.py)
    participant ML as ML Engine (utils/face.py)
    participant DB as Supabase pgvector (PostgreSQL)
    participant Mail as SMTP Dispatcher (Gmail)

    Client->>Proxy: POST /upload_photo (Classroom Group Photo)
    Proxy->>App: Forward Request to Endpoint
    App->>App: Read image bytes & convert to numpy array (cv2)
    App->>ML: Send image array to InsightFace
    ML->>ML: Detect bounding boxes & 5 landmarks (RetinaFace)
    ML->>ML: Generate 512D ArcFace embeddings & 3D Euler angles (Yaw, Pitch, Roll)
    ML->>App: Return normalized embeddings list + Pose Angles

    loop For Each Detected Face
        App->>DB: Invoke match_face RPC (embedding, FACE_MATCH_THRESHOLD=0.40)
        DB->>DB: Perform Cosine similarity query in pgvector
        DB-->>App: Return matching student_id & confidence S

        alt Match Found (Confidence S >= 0.40)
            App->>DB: Check re-attendance cooldown (>10 mins)
            App->>DB: Log attendance record as PRESENT
            
            note over App, DB: --- PART B: EMBEDDING DRIFT ENGINE (PATENT #3) ---
            App->>App: Check 3D Pose Gate (|Yaw| <= 25° AND |Pitch| <= 20°)
            alt Pose Gate Passed (Frontal Face)
                App->>App: Compute instantaneous drift D = 1.0 - S
                App->>App: Update EWMA accumulator: EWMA_t = 0.30*D + 0.70*EWMA_old
                App->>DB: Update student current_ewma_drift & log event in drift_logs
                
                alt EWMA >= DRIFT_CRITICAL_THRESHOLD (0.25)
                    App->>Mail: Dispatch Gmail SMTP Alert Email to Admin
                end
                alt EWMA >= DRIFT_ALERT_THRESHOLD (0.35)
                    App->>DB: Update student status to ALERT (Prompt Re-Enrollment)
                end
            else Pose Gate Failed (|Yaw| > 25° or |Pitch| > 20°)
                App->>DB: Log event status as POSE_REJECTED (EWMA Unchanged)
            end

        else No Match Found (S < 0.40)
            App-->>Client: Mark "Unknown" status
        end
    end
    App-->>Client: Return JSON results + Annotated Image
```

---

## ⚡ Concurrency & Scaling Model

1. **Stateless WSGI**:
   The application holds zero state in-memory or on local disk. Since student embeddings are fetched/stored in Supabase, any worker process can handle any request independently.
2. **Process-Level Scaling**:
   We use **Gunicorn** to spawn multiple synchronous worker processes. Since facial recognition is CPU-intensive (ONNX running on CPU), having multiple Gunicorn workers allows the app to process multiple uploads in parallel.
3. **Database Connection Pooling**:
   Connections to Supabase are stateless HTTP calls via the PostgREST API, meaning there is no risk of running out of traditional PostgreSQL socket connection pools under heavy load.
