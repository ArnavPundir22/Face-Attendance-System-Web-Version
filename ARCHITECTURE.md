# Project Architecture Map — BioSecure AI

## System Topology & Directory Structure
```
Face-Attendance-System-Web-Version/
├── app.py                      # Development Flask runner
├── wsgi.py                     # Production WSGI entrypoint (gunicorn wsgi:app)
├── gunicorn.conf.py            # Gunicorn WSGI production configuration
├── Procfile                    # PaaS deployment manifest
├── requirements.txt            # Linux/macOS production dependencies
├── requirements-windows.txt    # Windows development dependencies
├── start_face_attendance.sh    # Linux service startup shell script
├── start_face_attendance.bat   # Windows service startup batch file
├── docs/                       # In-depth architectural & API sub-guides
├── nginx/                      # Nginx reverse proxy configuration templates
├── known_faces/                # Local enrollment reference portraits storage
├── tests/                      # Automated unit and integration test suite
│   ├── conftest.py
│   └── unit/                   # Unit tests (cache, OCR, routes)
└── src/                        # Core application package
    ├── __init__.py             # Flask application factory (create_app)
    ├── config.py               # Centralized configuration & environment loader
    ├── blueprints/             # Route controllers
    │   ├── admin.py            # Admin operations & drift dashboard
    │   ├── attendance.py       # Attendance inference & EWMA drift processing
    │   ├── auth.py             # Authentication & OAuth session management
    │   └── students.py         # Student records & OCR ingestion endpoint
    ├── utils/                  # Core services & utilities
    │   ├── auth_helpers.py     # Authentication security & rate limiting
    │   ├── db.py               # Supabase PostgreSQL client connections
    │   ├── face.py             # InsightFace ArcFace 512D & 3D pose extraction
    │   ├── face_cache.py       # Thread-safe in-memory BLAS matrix matcher
    │   └── ocr_helpers.py      # RapidOCR neural engine & regex parsers
    ├── templates/              # Jinja2 HTML templates
    └── static/                 # Progressive Web App assets (sw.js, manifest, CSS, JS)
```

## Core Subsystems
1. **Inference Pipeline**: RetinaFace 5-point face detector + ArcFace 512-dimensional hyperspherical feature extractor via InsightFace ONNX Runtime.
2. **In-Memory Matching Engine**: Contiguous float32 NumPy embedding matrix performing batch matrix multiplication $Q \cdot M^T$ in $<1\text{ ms}$ on CPU with fallback to Supabase `pgvector` HNSW index.
3. **Biometric Drift Engine**: 3D Pose-Gated noise filter ($|\text{Yaw}| \le 25^\circ, |\text{Pitch}| \le 20^\circ$) coupled with Exponentially Weighted Moving Average (EWMA, $\alpha = 0.30$) tracking template aging across semesters.
4. **Neural OCR ID Reader**: RapidOCR ONNX (DBNet detector + SVTR recognizer) and PyTesseract with multi-pass OpenCV preprocessing for zero-touch enrollment.
5. **Progressive Web App (PWA)**: Service Worker App Shell caching (`/sw.js`), mobile camera capture (`capture="environment"`), and offline fallback (`/offline`).
