# 🏗️ System Architecture Guide

This document describes the design patterns, application structure, and execution lifecycles of **BioSecure AI**.

---

## 📁 Production-Grade Directory Structure

BioSecure AI is organized using the standard **Python Application Factory** layout. Code is decoupled from entry scripts, assets, and tests:

```
/
├── app.py                      # Flask development entrypoint (flask run)
├── wsgi.py                     # Production WSGI entrypoint (gunicorn wsgi:app)
├── config.py                   # Global configuration loading (maps environment vars)
├── requirements.txt            # Project python dependencies
├── gunicorn.conf.py            # Gunicorn WSGI daemon configurations
├── Procfile                    # Deployment service configuration for PaaS platforms
│
├── src/                        # Main Application Code
│   ├── __init__.py            # Application factory initialization (create_app)
│   ├── config.py              # Loads .env configuration relative to source directory
│   ├── blueprints/            # Blueprint route modules (Controllers)
│   │   ├── admin.py           # Admin routes: user management, statistics
│   │   ├── attendance.py      # Attendance marking, uploads, dynamic exports
│   │   ├── auth.py            # User registration & session auth helper
│   │   └── students.py        # Student records & registration
│   │
│   ├── utils/                 # Sub-system Utilities (Services)
│   │   ├── auth_helpers.py    # Login rate limits & brute-force protection
│   │   ├── db.py              # Supabase Client connections (Anon & Service Role)
│   │   └── face.py            # Face analysis inference (InsightFace model)
│   │
│   ├── templates/             # HTML Templates (Jinja2)
│   └── static/                # CSS, client JS, assets
│
├── scripts/                    # Maintenance & Setup Scripts
│   ├── process_photos.py      # Batch student photo importer (bg removal & parsing)
│   └── check_endpoint.py      # Endpoint health check test script
│
├── tests/                      # Automated Test Suite (Unit & Functional)
└── docs/                       # System Documentation Hub
```

---

## 🔄 Request Execution Lifecycle

When an attendance photo is uploaded, the request transitions through Nginx, Gunicorn, the Flask Blueprint, the ML face model, and finally performs a vector matching query on Supabase:

```mermaid
sequenceDiagram
    autonumber
    actor Client as Browser Client
    participant Proxy as Nginx / Gunicorn
    participant App as Flask Controller (attendance.py)
    participant ML as ML Engine (utils/face.py)
    participant DB as Supabase pgvector (Database)

    Client->>Proxy: POST /upload_photo (multipart image payload)
    Proxy->>App: Forward Request to Endpoint
    App->>App: Read image bytes & convert to numpy array (cv2)
    App->>ML: Send image array to InsightFace
    ML->>ML: Detect bounding boxes (RetinaFace)
    ML->>ML: Generate 512D embeddings (ArcFace)
    ML->>ML: Perform L2 vector normalisation
    ML->>App: Return normalise embeddings list
    
    loop For Each Detected Face
        App->>DB: Invoke match_face RPC (embedding, threshold)
        DB->>DB: Perform Cosine distance query in pgvector
        DB-->>App: Return matching student_id & confidence
        
        alt Match Found (Confidence >= Threshold)
            App->>DB: Check re-attendance cooldown
            alt Cooldown OK (> 10m)
                App->>DB: Insert attendance log row
                App-->>Client: Mark "Present" status
            else Cooldown Active
                App-->>Client: Skip Log (Already marked)
            end
        else No Match Found
            App-->>Client: Mark "Unknown" status
        end
    end
    App-->>Client: Send JSON results + Base64 annotated image
```

---

## ⚡ Concurrency & Scaling Model

1. **Stateless WSGI**:
   The application holds zero state in-memory or on local disk. Since student embeddings are fetched/stored in Supabase, any worker process can handle any request independently.
2. **Process-Level Scaling**:
   We use **Gunicorn** to spawn multiple synchronous worker processes. Since facial recognition is CPU-intensive (ONNX running on CPU), having multiple Gunicorn workers allows the app to process multiple uploads in parallel.
3. **Database Connection Pooling**:
   Connections to Supabase are stateless HTTP calls via the PostgREST API, meaning there is no risk of running out of traditional PostgreSQL socket connection pools under heavy load.
