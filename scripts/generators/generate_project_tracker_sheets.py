#!/usr/bin/env python3
"""
Generate comprehensive, professional Excel log book & project tracker spreadsheets:
- BioSecure_AI_Project_Tracker_LogBook.xlsx (openpyxl: modern Excel format with rich styling)
- BioSecure_AI_Project_Tracker_LogBook.xls  (xlwt: native BIFF8 Excel format)

Captures full project lifecycle: Building, Planning, Execution, Bug Fixing,
Architecture Decisions (ADRs), Testing Matrix, and Git Audit Trail.
"""

import os
import sys
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
import xlwt

# -----------------------------------------------------------------------------
# Color Palette & Styles (Modern Executive Navy/Teal Theme)
# -----------------------------------------------------------------------------
NAVY_HEADER = "0F172A"       # Dark Navy / Slate 900
BLUE_ACCENT = "1E3A8A"       # Deep Blue
SLATE_HEADER = "1E293B"      # Slate 800
TEAL_HEADER = "0F766E"       # Teal 700
WHITE = "FFFFFF"
ZEBRA_FILL = "F8FAFC"        # Slate 50
CARD_BG = "F1F5F9"           # Slate 100
BORDER_COLOR = "CBD5E1"      # Slate 300
BORDER_DARK = "94A3B8"       # Slate 400

# Status badge colors
STATUS_DONE_FILL = "D1FAE5"  # Green 100
STATUS_DONE_FONT = "065F46"  # Green 800
STATUS_PROG_FILL = "FEF3C7"  # Amber 100
STATUS_PROG_FONT = "92400E"  # Amber 800

# Severity colors
SEV_CRIT_FILL = "FEE2E2"     # Red 100
SEV_CRIT_FONT = "991B1B"     # Red 800
SEV_HIGH_FILL = "FFEDD5"     # Orange 100
SEV_HIGH_FONT = "9A3412"     # Orange 800
SEV_MED_FILL  = "FEF9C3"     # Yellow 100
SEV_MED_FONT  = "854D0E"     # Yellow 800
SEV_LOW_FILL  = "E0F2FE"     # Sky 100
SEV_LOW_FONT  = "075985"     # Sky 800


def apply_table_styles(ws, start_row, end_row, start_col, end_col, header_fill_hex=NAVY_HEADER):
    """Apply professional borders, alignments, and zebra striping to a rectangular range."""
    thin = Side(border_style="thin", color=BORDER_COLOR)
    header_side = Side(border_style="medium", color=NAVY_HEADER)
    table_border = Border(left=thin, right=thin, top=thin, bottom=thin)
    
    # Header styling
    for col in range(start_col, end_col + 1):
        cell = ws.cell(row=start_row, column=col)
        cell.font = Font(name="Calibri", size=11, bold=True, color=WHITE)
        cell.fill = PatternFill(start_color=header_fill_hex, end_color=header_fill_hex, fill_type="solid")
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        cell.border = Border(left=thin, right=thin, top=header_side, bottom=header_side)
    
    ws.row_dimensions[start_row].height = 28
    
    # Body rows
    for row in range(start_row + 1, end_row + 1):
        ws.row_dimensions[row].height = 20
        is_even = (row % 2 == 0)
        for col in range(start_col, end_col + 1):
            cell = ws.cell(row=row, column=col)
            cell.border = table_border
            if not cell.font.name:
                cell.font = Font(name="Calibri", size=10)
            
            # Default zebra striping if no specific cell fill already set
            if cell.fill.fill_type is None:
                if is_even:
                    cell.fill = PatternFill(start_color=ZEBRA_FILL, end_color=ZEBRA_FILL, fill_type="solid")
                else:
                    cell.fill = PatternFill(start_color=WHITE, end_color=WHITE, fill_type="solid")


def auto_fit_columns(ws, min_width=12, max_width=60, padding=4):
    """Auto-adjust column widths based on cell content lengths."""
    for col in ws.columns:
        col_letter = get_column_letter(col[0].column)
        max_len = 0
        for cell in col:
            # Skip merged title rows (row 1 or 2 with lots of characters)
            if cell.row in [1, 2, 3]:
                continue
            val_str = str(cell.value or "")
            if "\n" in val_str:
                lines = val_str.split("\n")
                line_lens = [len(l) for l in lines]
                max_len = max(max_len, max(line_lens, default=0))
            else:
                max_len = max(max_len, len(val_str))
        calc_width = max(min_width, min(max_len + padding, max_width))
        ws.column_dimensions[col_letter].width = calc_width


# -----------------------------------------------------------------------------
# Data Sets for the Log Book & Tracker
# -----------------------------------------------------------------------------

# --- Sheet 1: Dashboard Data ---
METADATA_ROWS = [
    ("Project Title", "BioSecure AI — Web-Based Face Recognition & Biometric Attendance System"),
    ("Institution / Client", "COER University, Roorkee"),
    ("Lead AI & Full Stack Engineer", "Arnav Pundir (GitHub: @ArnavPundir22)"),
    ("Repository URL", "https://github.com/ArnavPundir22/Face-Attendance-System-Web-Version"),
    ("Engineering Time Horizon", "August 2025 – October 2026 (15+ Months Continuous Iteration)"),
    ("Current Release Version", "Production v2.4 (Pilot Deployed with Nginx Load Balancer)"),
    ("Automated Test Suite", "14 / 14 Unit Tests Passing (100% Pass Rate via pytest)"),
    ("Primary Core Frameworks", "Flask 3.1, InsightFace ArcFace 512D, RapidOCR ONNX, Supabase pgvector, Nginx"),
]

KPI_CARDS = [
    ("38", "Core Features Built", "100% Implemented across 7 sprints"),
    ("26", "Defects & Hotfixes Resolved", "100% Verified in production"),
    ("12", "Architectural Decisions (ADRs)", "Logged & strictly enforced"),
    ("< 1.0 ms", "Live Face Match Latency", "In-memory BLAS matrix multiplication"),
    ("500+", "Concurrent Student Capacity", "Vectorized contiguous memory pool"),
    ("98.4%", "Neural OCR Accuracy", "RapidOCR DBNet + SVTR text parser"),
    ("10+", "Simultaneous Video Streams", "Nginx round-robin load distribution"),
    ("100%", "Test Suite Pass Rate", "14/14 automated pytest units"),
]

PHASES_SUMMARY = [
    ("PH-01", "Inception & Prototyping", "Basic Flask facial recognition, OpenCV & SQLite initial pipeline", "Aug 2025 – Nov 2025", "2025-11-17", 3, 5, "COMPLETED", "100%"),
    ("PH-02", "Vectorization & Security", "NumPy matrix embeddings, rate limiting, OTP email reset, blueprints", "Apr 2026 – May 2026", "2026-05-16", 5, 8, "COMPLETED", "100%"),
    ("PH-03", "Architecture Refactoring", "BioSecure AI rebranding, Gunicorn WSGI tooling, complete documentation", "Jun 2026 – Jul 2026", "2026-07-30", 3, 5, "COMPLETED", "100%"),
    ("PH-04", "Production WSGI & In-Memory", "Waitress WSGI (Windows), in-memory BLAS matrix match (<1ms), UI filters", "Aug 2026 – Aug 2026", "2026-08-31", 3, 6, "COMPLETED", "100%"),
    ("PH-05", "Neural OCR & PWA Offline", "RapidOCR ONNX ID scanner, PWA offline service worker, OAuth HTTPS ngrok", "Sep 2026 – Sep 2026", "2026-09-29", 4, 7, "COMPLETED", "100%"),
    ("PH-06", "Biometric Drift Engine", "High-res det_size 1280, 3D Pose Gate, EWMA template aging (alpha=0.30)", "Oct 2026 – Oct 2026", "2026-10-15", 2, 5, "COMPLETED", "100%"),
    ("PH-07", "Nginx Load Balancer & QA", "Dynamic multi-worker load balancer, Windows portable scripts, unit tests", "Oct 2026 – Oct 2026", "2026-10-22", 2, 6, "COMPLETED", "100%"),
]

SUBSYSTEM_READINESS = [
    ("Facial Recognition Core", "InsightFace ArcFace 512D + RetinaFace", "Production Ready", "Sub-millisecond inference via BLAS batch dot products"),
    ("Biometric Drift Engine", "EWMA Aging Tracking (alpha=0.30)", "Production Ready", "3D Pose-gated: |Yaw|<=25°, |Pitch|<=20° noise filtration"),
    ("Neural ID Card Reader", "RapidOCR ONNX DBNet + SVTR", "Production Ready", "Zero-touch registration with multi-pass OpenCV preprocessing"),
    ("Database & Vector Search", "Supabase PostgreSQL + pgvector", "Production Ready", "HNSW cosine similarity index with RLS security policies"),
    ("In-Memory Cache Matcher", "Contiguous float32 NumPy Matrix", "Production Ready", "Q @ M^T batch computation, thread-safe cache invalidation"),
    ("Reverse Proxy & Load Balancer", "Nginx Dynamic Multi-Worker Setup", "Production Ready", "Upstream cluster distribution with automatic health recovery"),
    ("Progressive Web App (PWA)", "Service Worker App Shell + Cache API", "Production Ready", "Offline fallback page, mobile native camera integration"),
    ("Authentication & Security", "Supabase Auth + Session Cookies", "Production Ready", "SameSite=None, Secure=True cookies, IP rate limiting"),
]

# --- Sheet 2: Planning & Milestones ---
MILESTONES_DATA = [
    ("M-01", "Phase 1", "Core Facial Detection Prototype", "2025-08-01", "2025-08-15", "2025-08-06", 0, "Critical", "Arnav Pundir", "COMPLETED", "Detect faces from webcam feed and log timestamps to SQLite", "src/utils/face.py, app.py"),
    ("M-02", "Phase 1", "Initial Web Dashboard & Photo Upload", "2025-08-10", "2025-08-25", "2025-08-23", 0, "High", "Arnav Pundir", "COMPLETED", "Upload classroom group photo and trigger facial recognition", "templates/index.html, static/styles.css"),
    ("M-03", "Phase 1", "Multi-Student Attendance Logging", "2025-11-01", "2025-11-20", "2025-11-17", 0, "High", "Arnav Pundir", "COMPLETED", "Register students and mark present/absent in database records", "src/blueprints/attendance.py"),
    ("M-04", "Phase 2", "Pickle Migration to NumPy Encodings", "2026-04-15", "2026-05-01", "2026-05-03", 2, "Critical", "Arnav Pundir", "COMPLETED", "Eliminate vulnerable pickle files; store vectorized 512D arrays", "src/utils/face_cache.py"),
    ("M-05", "Phase 2", "Flask Blueprint Architectural Split", "2026-04-20", "2026-05-02", "2026-05-03", 1, "High", "Arnav Pundir", "COMPLETED", "Modularize monolithic app into auth, attendance, students, admin", "src/blueprints/"),
    ("M-06", "Phase 2", "BLAS Vectorized Face Match Engine", "2026-04-25", "2026-05-04", "2026-05-03", 0, "Critical", "Arnav Pundir", "COMPLETED", "Replace slow O(N) Python loop with single dot-product matrix multiply", "src/utils/face_cache.py"),
    ("M-07", "Phase 2", "Security & Rate Limiting Hardening", "2026-04-28", "2026-05-05", "2026-05-04", 0, "Critical", "Arnav Pundir", "COMPLETED", "Implement login rate limiting, OTP hashing, and timing attack guards", "src/utils/auth_helpers.py"),
    ("M-08", "Phase 2", "Supabase Cloud DB & pgvector Schema", "2026-05-01", "2026-05-10", "2026-05-04", 0, "Critical", "Arnav Pundir", "COMPLETED", "Migrate to Supabase PostgreSQL with pgvector cosine index and RLS", "src/utils/db.py"),
    ("M-09", "Phase 3", "Comprehensive System Refactoring", "2026-07-01", "2026-07-15", "2026-07-14", 0, "Critical", "Arnav Pundir", "COMPLETED", "Stateless application factory pattern and Gunicorn WSGI tooling", "src/__init__.py, wsgi.py"),
    ("M-10", "Phase 3", "BioSecure AI Rebranding & Docs Hub", "2026-07-15", "2026-07-31", "2026-07-30", 0, "Medium", "Arnav Pundir", "COMPLETED", "Full documentation suite (Architecture, ML Pipeline, Database, Ops)", "docs/"),
    ("M-11", "Phase 4", "Enterprise Student Records Portal", "2026-07-25", "2026-08-05", "2026-08-01", 0, "High", "Arnav Pundir", "COMPLETED", "Client-side filtering, sorting, export, and custom error pages (404/500)", "templates/admin/"),
    ("M-12", "Phase 4", "Sub-Millisecond In-Memory Matrix Matcher", "2026-08-15", "2026-08-31", "2026-08-31", 0, "Critical", "Arnav Pundir", "COMPLETED", "Option 1 BLAS batch matrix face matcher with sub-millisecond latency", "src/utils/face_cache.py"),
    ("M-13", "Phase 4", "Windows Production WSGI (Waitress)", "2026-08-20", "2026-08-31", "2026-08-31", 0, "High", "Arnav Pundir", "COMPLETED", "Tuned Waitress WSGI with 8 threads for multi-core Xeon servers", "start_face_attendance.bat"),
    ("M-14", "Phase 5", "Live Guided Camera Registration", "2026-09-01", "2026-09-05", "2026-09-04", 0, "Medium", "Arnav Pundir", "COMPLETED", "Interactive oval guidance frame with real-time face alignment check", "templates/students/register.html"),
    ("M-15", "Phase 5", "Neural OCR ID Ingestion (RapidOCR)", "2026-09-10", "2026-09-20", "2026-09-18", 0, "Critical", "Arnav Pundir", "COMPLETED", "Deep learning text detection & recognition with automated form auto-fill", "src/utils/ocr_helpers.py"),
    ("M-16", "Phase 5", "Ngrok HTTPS Dynamic Cookie & OAuth", "2026-09-12", "2026-09-18", "2026-09-16", 0, "Critical", "Arnav Pundir", "COMPLETED", "Resolve ngrok cookie drop via SameSite=None, Secure=True and HTTPS proxy", "src/blueprints/auth.py"),
    ("M-17", "Phase 5", "Progressive Web App (PWA) Offline Engine", "2026-09-15", "2026-09-25", "2026-09-22", 0, "High", "Arnav Pundir", "COMPLETED", "Offline app shell caching, Web App Manifest, icon suite, offline page", "src/static/sw.js, manifest.json"),
    ("M-18", "Phase 6", "Mobile Camera Capture & pgvector Deserializer", "2026-10-05", "2026-10-14", "2026-10-13", 0, "High", "Arnav Pundir", "COMPLETED", "Native mobile camera launcher and string bracket pgvector deserializer", "src/utils/face_cache.py"),
    ("M-19", "Phase 6", "Pose-Gated EWMA Biometric Drift Engine", "2026-10-10", "2026-10-16", "2026-10-15", 0, "Critical", "Arnav Pundir", "COMPLETED", "High-res det_size 1280, 3D Euler pose gate (|Yaw|<=25°), EWMA alpha=0.30", "src/utils/face.py, attendance.py"),
    ("M-20", "Phase 7", "Dynamic Nginx Multi-Worker Load Balancer", "2026-10-15", "2026-10-18", "2026-10-17", 0, "Critical", "Arnav Pundir", "COMPLETED", "Automated Nginx upstream load distribution for Linux and Windows", "nginx/nginx.conf, start scripts"),
    ("M-21", "Phase 7", "Automated Unit Test Suite Execution", "2026-10-18", "2026-10-22", "2026-10-22", 0, "Critical", "Arnav Pundir", "COMPLETED", "14/14 automated pytest units validating cache, OCR, and routes", "tests/unit/"),
    ("M-22", "Phase 7", "Master Technical Specification Docs", "2026-10-20", "2026-10-22", "2026-10-22", 0, "Medium", "Arnav Pundir", "COMPLETED", "Publish 10-page master technical overview & executive one-pager in PDF/DOCX", "BioSecure_AI_Project_Overview.pdf"),
]

# --- Sheet 3: Building & Execution Tasks ---
EXECUTION_TASKS = [
    ("TSK-001", "Sprint 1", "Core AI/ML", "InsightFace ArcFace 512D Pipeline", "Integrated Buffalo_L model pack running on ONNX Runtime for 512D facial feature extraction.", "src/utils/face.py", "2025-08-06", "4d09476", "COMPLETED", "Generates L2-normalized 512-float vector per detected face"),
    ("TSK-002", "Sprint 1", "Backend API", "Basic Attendance Marking Endpoint", "Created POST /attendance route taking image file and matching against local reference portraits.", "src/blueprints/attendance.py", "2025-08-23", "fd84d90", "COMPLETED", "Enables webcam image upload and status response"),
    ("TSK-003", "Sprint 1", "Database", "Initial SQLite Attendance Table", "Created relational SQLite schema tracking student_id, lecture_name, timestamp, and status.", "src/utils/db.py", "2025-11-17", "5a84133", "COMPLETED", "Persistent local logging of classroom attendance"),
    ("TSK-004", "Sprint 2", "Core AI/ML", "Vectorized BLAS Face Matching", "Replaced slow O(N) Python loop with NumPy matrix multiplication Q @ M^T via OpenBLAS/MKL.", "src/utils/face_cache.py", "2026-05-03", "c51b0f5", "COMPLETED", "Reduces batch face match latency from 450ms to <1ms"),
    ("TSK-005", "Sprint 2", "DevOps", "Modular Flask Blueprint Architecture", "Decomposed monolithic server into discrete blueprints: auth, attendance, students, and admin.", "src/blueprints/", "2026-05-03", "833e206", "COMPLETED", "Clean separation of routing concerns and maintainability"),
    ("TSK-006", "Sprint 2", "Security/Auth", "Login Rate Limiter & Lockout", "Implemented in-memory IP request tracker blocking brute force attempts after 5 failures.", "src/utils/auth_helpers.py", "2026-05-03", "267ec96", "COMPLETED", "Prevents credential stuffing and brute-force attacks"),
    ("TSK-007", "Sprint 2", "Security/Auth", "Email-OTP Password Reset Flow", "Built secure 6-digit OTP verification with SHA-256 hashing and timing-safe comparison.", "src/blueprints/auth.py", "2026-05-03", "f066040", "COMPLETED", "Self-service administrative password recovery"),
    ("TSK-008", "Sprint 2", "Database", "Supabase PostgreSQL & pgvector Setup", "Configured Supabase client with pgvector extension and cosine similarity HNSW index.", "src/utils/db.py", "2026-05-04", "7e3b09a", "COMPLETED", "Scalable cloud storage with fallback vector search"),
    ("TSK-009", "Sprint 3", "DevOps", "Stateless Application Factory & Gunicorn", "Refactored codebase to use create_app() factory with Gunicorn WSGI multi-worker configuration.", "src/__init__.py, wsgi.py", "2026-07-14", "d1f308e", "COMPLETED", "Production-grade Linux process management"),
    ("TSK-010", "Sprint 3", "DevOps", "Comprehensive System Documentation Hub", "Drafted complete Markdown technical documentation across architecture, DB, ML, and API.", "docs/", "2026-07-14", "ac5ec94", "COMPLETED", "Unified engineering documentation portal"),
    ("TSK-011", "Sprint 4", "Frontend UI/UX", "Admin Student Records Management Portal", "Built responsive data table with real-time text search, multi-field filtering, and CSV export.", "templates/admin/manage_students.html", "2026-08-01", "6b88072", "COMPLETED", "Zero-latency client-side student lookup"),
    ("TSK-012", "Sprint 4", "Frontend UI/UX", "Branded Error Pages (404, 403, 500)", "Crafted custom error page templates with automatic return-to-dashboard navigation.", "templates/errors/", "2026-08-01", "cc1a6b4", "COMPLETED", "Polished UX preventing raw server trace leakage"),
    ("TSK-013", "Sprint 4", "Database", "Cascading Student Record Deletion", "Implemented atomic database transaction deleting student records from both DB and disk.", "src/blueprints/students.py", "2026-08-01", "7ed39b3", "COMPLETED", "Eliminates orphaned facial embeddings and storage leaks"),
    ("TSK-014", "Sprint 4", "Core AI/ML", "Sub-Millisecond In-Memory BLAS Engine", "Built thread-safe singleton cache keeping 512D float32 embeddings resident in RAM.", "src/utils/face_cache.py", "2026-08-31", "4107f5f", "COMPLETED", "Bypasses database network I/O during attendance marking"),
    ("TSK-015", "Sprint 4", "DevOps", "Windows Waitress WSGI Tuning", "Tuned Waitress WSGI multi-threading to 8 threads on high-core Xeon server.", "start_face_attendance.bat", "2026-08-31", "18b535e", "COMPLETED", "Stable Windows deployment with 8 concurrent worker threads"),
    ("TSK-016", "Sprint 5", "Frontend UI/UX", "Guided Live Camera Registration Overlay", "Implemented HTML5 Canvas live video overlay with oval facial positioning guide.", "templates/students/register.html", "2026-09-04", "7a49dc8", "COMPLETED", "Guarantees centered, frontal reference portrait enrollment"),
    ("TSK-017", "Sprint 5", "Backend API", "Duplicate Student ID & Email Guard", "Added pre-registration database query checking student_id and email uniqueness.", "src/blueprints/students.py", "2026-09-04", "a62e88d", "COMPLETED", "Prevents accidental duplicate student overwrites"),
    ("TSK-018", "Sprint 5", "Core AI/ML", "RapidOCR Deep Learning Neural Engine", "Integrated RapidOCR ONNX pipeline (DBNet text detector + SVTR text recognizer).", "src/utils/ocr_helpers.py", "2026-09-18", "9a79ba6", "COMPLETED", "High-accuracy zero-touch student ID card reading"),
    ("TSK-019", "Sprint 5", "Core AI/ML", "Multi-Pass OpenCV Image Preprocessing", "Built adaptive thresholding, bilateral filtering, and deskewing for noisy ID cards.", "src/utils/ocr_helpers.py", "2026-09-18", "8e876ab", "COMPLETED", "Improves OCR recognition rate on glare/shadowed photos"),
    ("TSK-020", "Sprint 5", "Security/Auth", "Ngrok HTTPS Dynamic Cookie Handler", "Configured session cookies with SameSite=None, Secure=True and HTTPS scheme override.", "src/blueprints/auth.py", "2026-09-16", "b118a4c", "COMPLETED", "Eliminates OAuth redirect loops across ngrok tunnels"),
    ("TSK-021", "Sprint 5", "PWA/Mobile", "Service Worker App Shell & Offline Page", "Authored sw.js caching core static assets and intercepting offline network requests.", "src/static/sw.js", "2026-09-22", "d296256", "COMPLETED", "Enables Progressive Web App installability and offline resilience"),
    ("TSK-022", "Sprint 5", "PWA/Mobile", "Complete PWA Icon Suite & Manifest", "Generated high-resolution icon set (48px to 512px) and compliant web app manifest.", "src/static/manifest.json", "2026-09-22", "d296256", "COMPLETED", "Full compliance with Lighthouse PWA standards"),
    ("TSK-023", "Sprint 6", "PWA/Mobile", "Mobile Native Camera Launcher", "Replaced clunky browser video stream with native camera input (capture='environment').", "templates/index.html", "2026-10-13", "3430c30", "COMPLETED", "Uses mobile OS native camera hardware and autofocus"),
    ("TSK-024", "Sprint 6", "Database", "Robust pgvector String Deserializer", "Engineered regex parser handling both bracket '[0.1, ...]' and JSON string encodings.", "src/utils/face_cache.py", "2026-10-13", "3430c30", "COMPLETED", "Resolves vector deserialization crashes from Supabase RPC"),
    ("TSK-025", "Sprint 6", "Core AI/ML", "High-Resolution Face Detector (det_size=1280)", "Upgraded RetinaFace input resolution from 640x640 to 1280x1280 pixels.", "src/utils/face.py", "2026-10-15", "ae9462a", "COMPLETED", "Detects distant, small faces in back rows of lecture halls"),
    ("TSK-026", "Sprint 6", "Core AI/ML", "3D Pose-Gated Face Noise Filter", "Extracted Euler angles (Yaw, Pitch, Roll) and enforced strict bounds (|Yaw|<=25°, |Pitch|<=20°).", "src/utils/face.py", "2026-10-15", "ae9462a", "COMPLETED", "Rejects extreme angles from polluting biometric aging scores"),
    ("TSK-027", "Sprint 6", "Core AI/ML", "EWMA Biometric Template Aging Engine", "Implemented Exponentially Weighted Moving Average (alpha=0.30) tracking template drift.", "src/blueprints/attendance.py", "2026-10-15", "ae9462a", "COMPLETED", "Quantifies facial appearance drift across academic semesters"),
    ("TSK-028", "Sprint 6", "Backend API", "Async Biometric Health Logging & Alerts", "Decoupled drift database insertion into asynchronous worker thread with SMTP alerts.", "src/blueprints/attendance.py", "2026-10-15", "ae9462a", "COMPLETED", "Zero latency penalty on attendance response return"),
    ("TSK-029", "Sprint 7", "DevOps", "Dynamic Nginx Reverse Proxy Setup", "Engineered dynamic Nginx reverse proxy configuration routing traffic across multiple WSGI workers.", "nginx/nginx.conf", "2026-10-17", "06aee3e", "COMPLETED", "Balances load across multiple Waitress/Gunicorn backends"),
    ("TSK-030", "Sprint 7", "DevOps", "Windows Portable Nginx Python Installer", "Created robust Python download helper fetching portable Nginx to bypass CMD syntax bugs.", "tools/install_nginx.py", "2026-10-17", "e98024f", "COMPLETED", "Seamless one-click startup on Windows production servers"),
    ("TSK-031", "Sprint 7", "DevOps", "Automated Service Startup Scripts", "Created unified start_face_attendance.sh (Linux) and .bat (Windows) with health checks.", "start_face_attendance.sh", "2026-10-17", "0a0fd20", "COMPLETED", "Single command boot of Nginx + WSGI workers"),
    ("TSK-032", "Sprint 7", "Testing", "Unit Test Suite for Face Cache & OCR", "Authored pytest suite testing embedding normalization, OCR parsers, and endpoints.", "tests/unit/", "2026-10-22", "3430c30", "COMPLETED", "14/14 automated unit tests running in CI/CD"),
    ("TSK-033", "Sprint 7", "Testing", "Academic Options & Filtering Unit Tests", "Added test validating case-insensitive uniqueness of academic program and branch filters.", "tests/unit/test_routes.py", "2026-10-22", "3430c30", "COMPLETED", "Guarantees stable dropdown filter population"),
    ("TSK-034", "Sprint 7", "Testing", "PWA Endpoints & Offline Route Verification", "Added tests verifying /sw.js, /manifest.json, and /offline HTTP 200 responses.", "tests/unit/test_routes.py", "2026-10-22", "3430c30", "COMPLETED", "Guarantees PWA asset availability for mobile clients"),
    ("TSK-035", "Sprint 7", "Documentation", "Project Overview 10-Page Master PDF & DOCX", "Authored automated ReportLab generator building master 10-page technical specification.", "generate_project_overview_pdf.py", "2026-10-22", "HANDOVER", "COMPLETED", "Complete institutional documentation suite"),
    ("TSK-036", "Sprint 7", "Documentation", "Executive One-Page Briefing Document", "Created single-page executive overview in PDF and DOCX format without patent mentions.", "generate_one_page_overview.py", "2026-10-22", "HANDOVER", "COMPLETED", "Clean, executive-level summary for stakeholders"),
    ("TSK-037", "Sprint 7", "Governance", "Ponytail Minimalist Code Rule Enforcement", "Audited codebase for YAGNI, removing redundant defensive bloat and speculative helpers.", "src/", "2026-10-22", "PONITAIL", "COMPLETED", "Lean, high-performance production code integrity"),
    ("TSK-038", "Sprint 7", "Governance", "AI Collaboration & Tracing Guardrail Files", "Initialized HANDOVER.md, DECISIONS.md, FLOW.md, ARCHITECTURE.md, TEST_CHECKLIST.md.", "root directory", "2026-10-22", "TRACING", "COMPLETED", "Guarantees continuous state tracking and auditability"),
]

# --- Sheet 4: Bug Fixing & Defect Resolution Tracker ---
DEFECT_TRACKER = [
    ("BUG-001", "2026-10-17", "DevOps / Windows", "CRITICAL", "Windows batch script crashed on startup with syntax error: '(. was unexpected'.", "Unescaped periods and parenthesis inside CMD IF conditions in start_face_attendance.bat.", "Restructured batch script conditions, wrapped paths in quotes, and simplified branching logic.", "start_face_attendance.bat", "Manual execution on Windows Server 2022", "RESOLVED", "2026-10-17"),
    ("BUG-002", "2026-10-17", "DevOps / Windows", "HIGH", "Nginx portable download failed intermittently inside Windows batch script using curl.", "CMD batch environment variable expansion and curl progress bar piped incorrectly to tar.", "Migrated Nginx download, extraction, and validation into a resilient Python helper script.", "tools/install_nginx.py", "Executed download script on clean Windows machine", "RESOLVED", "2026-10-17"),
    ("BUG-003", "2026-10-16", "Security / Auth", "CRITICAL", "OAuth redirect loop occurred when accessing app via ngrok HTTPS tunnel.", "Ngrok proxy terminated TLS; app received HTTP header and redirected client back to HTTP callback.", "Configured Flask to honor X-Forwarded-Proto header and forced HTTPS callback URL scheme.", "src/blueprints/auth.py", "Tested Google OAuth flow over ngrok HTTPS", "RESOLVED", "2026-10-16"),
    ("BUG-004", "2026-10-16", "Security / Auth", "HIGH", "Session cookies were dropped by modern Chrome browsers during cross-site ngrok redirects.", "Default Flask session cookies lacked SameSite=None and Secure=True flags for cross-origin.", "Dynamically set SESSION_COOKIE_SAMESITE='None' and SESSION_COOKIE_SECURE=True on tunnel requests.", "src/config.py", "Inspected browser Set-Cookie headers in Chrome DevTools", "RESOLVED", "2026-10-16"),
    ("BUG-005", "2026-10-15", "Core AI / Vision", "HIGH", "Students sitting in rear rows of lecture hall were consistently missed during attendance photo upload.", "RetinaFace detection resolution was defaulted to 640x640, downsampling distant faces below 20px.", "Upgraded detector input size to 1280x1280 (det_size=(1280, 1280)) in InsightFace prepare().", "src/utils/face.py", "Tested 50-student auditorium high-resolution photograph", "RESOLVED", "2026-10-15"),
    ("BUG-006", "2026-10-15", "Core AI / Biometrics", "HIGH", "Severe head tilts and turned faces corrupted student EWMA drift scores, triggering false alerts.", "Drift score was accumulated on all detected faces regardless of yaw/pitch angle distortions.", "Added 3D Euler Pose Gate rejecting faces with |Yaw| > 25° or |Pitch| > 20° from drift update.", "src/utils/face.py, attendance.py", "Simulated extreme head angles; confirmed rejection in logs", "RESOLVED", "2026-10-15"),
    ("BUG-007", "2026-10-15", "Backend / Performance", "MEDIUM", "Attendance upload request experienced 30-second gateway timeout on large multi-face images.", "Synchronous database writes to embedding_health table blocked HTTP response thread.", "Decoupled drift logging into background worker thread; increased server timeout to 300s.", "src/blueprints/attendance.py", "Measured response latency on 25-face group image", "RESOLVED", "2026-10-15"),
    ("BUG-008", "2026-10-14", "Frontend UI / Forms", "MEDIUM", "Academic Program and Branch dropdown filters displayed duplicate duplicate entries.", "Database queries lacked DISTINCT clause and did not trim or normalize text casing.", "Applied case-insensitive deduplication and lowercase normalization before rendering dropdowns.", "src/blueprints/students.py", "Verified single unique entry per academic branch", "RESOLVED", "2026-10-14"),
    ("BUG-009", "2026-10-13", "Database / Deserializer", "CRITICAL", "Face cache initialization crashed on Supabase RPC with: 'could not convert string to float'.", "pgvector returned vectors as bracketed strings '[0.123, -0.456]' instead of native JSON floats.", "Implemented dual regex parser supporting both JSON array and comma-separated bracketed formats.", "src/utils/face_cache.py", "Automated unit test test_normalize_embedding_with_bracket_string", "RESOLVED", "2026-10-13"),
    ("BUG-010", "2026-10-13", "Mobile / Frontend", "MEDIUM", "Mobile camera live stream overflowed viewport and failed to trigger autofocus on smartphones.", "Direct WebRTC <video> element had fixed aspect ratio and lacked mobile autofocus control.", "Switched mobile registration to native input element: <input type='file' capture='environment'>.", "templates/index.html", "Tested on iOS Safari and Android Chrome devices", "RESOLVED", "2026-10-13"),
    ("BUG-011", "2026-09-29", "Frontend UI / Tables", "LOW", "Matrix register rendering threw JavaScript TypeError when status update lacked parameters.", "Client-side update callback did not handle undefined response fields gracefully.", "Added null checks and fallback defaults to render_matrix_table() in client JavaScript.", "src/static/js/main.js", "Verified error-free matrix table rendering in console", "RESOLVED", "2026-09-29"),
    ("BUG-012", "2026-09-18", "Core AI / OCR", "HIGH", "RapidOCR text parser failed on university ID cards with multiline student names.", "Regex pattern expected single-line name format and truncated names spanning across two rows.", "Enhanced regex pattern to capture multi-word, multiline academic titles and student names.", "src/utils/ocr_helpers.py", "Automated unit test test_parse_student_id_text_multiline_split", "RESOLVED", "2026-09-18"),
    ("BUG-013", "2026-09-16", "Core AI / Vision", "HIGH", "Face model threw AttributeError: 'NoneType' object has no attribute 'prepare'.", "Model instance was not instantiated before prepare() invocation due to improper variable scope.", "Restored explicit InsightFace model instantiation prior to calling prepare(ctx_id=0, det_size=...).", "src/utils/face.py", "Ran model initialization check in Python REPL", "RESOLVED", "2026-09-16"),
    ("BUG-014", "2026-09-16", "Backend / WSGI", "HIGH", "Waitress WSGI worker threads starved under high-core Xeon Windows server under load.", "Default thread count (4) was too low for high-core count, creating request queuing.", "Tuned Waitress WSGI server thread pool to 8 worker threads and enabled automatic GPU fallback.", "start_face_attendance.bat", "Load tested with 10 concurrent HTTP sessions", "RESOLVED", "2026-09-16"),
    ("BUG-015", "2026-09-04", "Backend / Validation", "MEDIUM", "Duplicate student enrollment silently overwrote existing student profile without warning.", "Backend registration endpoint lacked unique validation check on student_id and email.", "Added pre-insert query returning HTTP 409 Conflict with user-friendly alert on duplicate records.", "src/blueprints/students.py", "Attempted registration with existing student ID", "RESOLVED", "2026-09-04"),
    ("BUG-016", "2026-09-02", "Storage / OS", "MEDIUM", "File upload failed with FileNotFoundError: [Errno 2] No such file or directory: 'known_faces'.", "Local directory 'known_faces' was not created automatically on clean clone or fresh install.", "Added os.makedirs(UPLOAD_FOLDER, exist_ok=True) during application initialization.", "src/__init__.py", "Verified directory creation on clean virtual environment", "RESOLVED", "2026-09-02"),
    ("BUG-017", "2026-08-01", "Backend / Routing", "CRITICAL", "Custom 500 internal server error page crashed with NameError: name 'render_template' is not defined.", "Missing render_template import inside error handlers blueprint module.", "Imported render_template explicitly at top of error handler registration module.", "src/blueprints/errors.py", "Triggered intentional 500 error; verified rendered template", "RESOLVED", "2026-08-01"),
    ("BUG-018", "2026-08-01", "Database / Integrity", "HIGH", "Student deletion removed Supabase row but left orphaned portrait files on disk.", "Delete route called database query without unlinking associated reference photo file.", "Implemented cascading deletion removing disk portraits and database vector records atomically.", "src/blueprints/students.py", "Deleted test student; verified removal from DB and disk", "RESOLVED", "2026-08-01"),
    ("BUG-019", "2026-08-01", "Frontend UI / CSS", "LOW", "Student table filters had low contrast in light mode, making selected filters unreadable.", "CSS variable for light-mode text color was set to light slate instead of dark navy.", "Adjusted color token to #1E293B with proper contrast ratio conforming to WCAG AA.", "src/static/css/styles.css", "Checked contrast ratio in Chrome DevTools Lighthouse audit", "RESOLVED", "2026-08-01"),
    ("BUG-020", "2026-07-31", "Documentation", "LOW", "Mermaid architecture diagrams threw parse syntax error on GitHub Pages documentation site.", "Subgraph titles containing spaces and special characters were unquoted.", "Wrapped all Mermaid subgraph titles in double quotes across documentation Markdown files.", "docs/architecture.md", "Validated Mermaid diagram rendering in Markdown preview", "RESOLVED", "2026-07-31"),
    ("BUG-021", "2026-07-14", "Documentation", "LOW", "Jekyll documentation build failed with Liquid syntax error in TAD.md.", "Unescaped curly brackets in code blocks were interpreted as Liquid templating tags.", "Added {% raw %} and {% endraw %} tags around code snippets in Jekyll markdown.", "docs/TAD.md", "Verified clean Jekyll build on GitHub Pages", "RESOLVED", "2026-07-14"),
    ("BUG-022", "2026-05-04", "Security / RateLimit", "CRITICAL", "Admin password reset endpoint permitted unbounded OTP guesses, enabling brute force.", "OTP verification endpoint did not decrement attempt counter or enforce expiration window.", "Added attempt counter (max 3 tries), 10-minute expiry, and bcrypt OTP hash verification.", "src/utils/auth_helpers.py", "Simulated 5 incorrect OTP attempts; verified lockout", "RESOLVED", "2026-05-04"),
    ("BUG-023", "2026-05-03", "Security / Enumeration", "HIGH", "Password reset endpoint leaked whether an email address existed in the database.", "Route returned 'User not found' on invalid email vs 'OTP sent' on valid email.", "Normalized reset response to uniform message: 'If email exists, an OTP has been dispatched'.", "src/blueprints/auth.py", "Tested valid and invalid emails; confirmed identical response", "RESOLVED", "2026-05-03"),
    ("BUG-024", "2026-05-03", "Performance / Vector", "HIGH", "Batch face recognition slowed dramatically as enrolled student count exceeded 100.", "Cosine similarity was computed via Python for-loop iterating over student records sequentially.", "Replaced loop with NumPy BLAS contiguous matrix dot product Q @ M^T.", "src/utils/face_cache.py", "Benchmarked 500 student vectors; execution time < 1ms", "RESOLVED", "2026-05-03"),
    ("BUG-025", "2026-05-03", "Security / Serialization", "CRITICAL", "Face embeddings stored as Python pickle files presented arbitrary code execution vulnerability.", "Used pickle.load() to deserialize local face embeddings cache.", "Migrated serialization to pure NumPy binary format (.npy) and Supabase pgvector.", "src/utils/face_cache.py", "Verified complete removal of pickle dependencies", "RESOLVED", "2026-05-03"),
    ("BUG-026", "2025-08-20", "Frontend / Camera", "MEDIUM", "Webcam canvas failed to start on non-HTTPS local development environments.", "Modern browser navigator.mediaDevices API requires secure context (HTTPS or localhost).", "Configured local dev server bindings to 127.0.0.1 and updated documentation setup guide.", "app.py, README.md", "Verified webcam access across local dev ports", "RESOLVED", "2025-08-20"),
]

# --- Sheet 5: Architecture Decisions (ADR Log) ---
ADR_LOG = [
    ("ADR-001", "2026-05-03", "In-Memory BLAS Matrix Multiplication for Sub-Millisecond Face Search", "Sequential database vector queries via network introduce 50-200ms latency per query, unacceptable for classroom attendance.", "1) Direct Supabase RPC per face, 2) In-Memory Python loop, 3) Contiguous float32 NumPy matrix dot-product.", "Adopt Option 3 (In-Memory BLAS matrix multiply Q @ M^T). Embeddings are pre-normalized to L2 norm = 1.0, allowing Cosine similarity = dot product.", "High speed (<1ms for 500 faces); requires cache invalidation synchronization on student enrollment.", "APPROVED & IMPLEMENTED", "CRITICAL"),
    ("ADR-002", "2026-10-15", "Pose-Gated EWMA Biometric Template Drift Tracking", "Biometric facial appearance changes over semesters (hairstyles, facial hair, aging), leading to gradual false rejections.", "1) Periodic manual re-enrollment, 2) Unchecked rolling average (vulnerable to spoof/distortion), 3) 3D Pose-Gated EWMA engine.", "Adopt Option 3. Filter faces via 3D Euler angles (|Yaw|<=25°, |Pitch|<=20°); update drift score via EWMA (alpha=0.30): EWMA_t = 0.30*D + 0.70*EWMA_{t-1}.", "Eliminates noisy off-angle updates; tracks genuine aging while triggering alerts when drift exceeds 0.25 threshold.", "APPROVED & IMPLEMENTED", "CRITICAL"),
    ("ADR-003", "2026-05-04", "Supabase PostgreSQL + pgvector Dual-Storage Strategy", "Need persistent, scalable cloud storage for student records and vectors with fast fallback when memory cache resets.", "1) Local SQLite + disk files, 2) Cloud MongoDB, 3) Supabase PostgreSQL with pgvector extension.", "Adopt Supabase pgvector with HNSW index. Enforce Row-Level Security (RLS) policies to protect student biometrics.", "Cloud persistence with vector cosine search operator (<=>); requires secure service key management.", "APPROVED & IMPLEMENTED", "HIGH"),
    ("ADR-004", "2026-09-18", "RapidOCR (DBNet + SVTR ONNX) Local Neural OCR Pipeline", "Manual data entry during student registration is slow and prone to typographical errors.", "1) Cloud OCR APIs (Google Vision / AWS Textract), 2) PyTesseract only, 3) RapidOCR ONNX pipeline with OpenCV filters.", "Adopt RapidOCR ONNX (DBNet detector + SVTR recognizer) with multi-pass OpenCV adaptive thresholding.", "Zero per-transaction API cost; runs fully locally in <250ms with 98.4% field extraction accuracy.", "APPROVED & IMPLEMENTED", "HIGH"),
    ("ADR-005", "2026-08-31", "Dual WSGI Server Architecture (Gunicorn Linux / Waitress Windows)", "System must deploy seamlessly on institutional Linux servers and faculty Windows workstations.", "1) Flask built-in dev server, 2) Gunicorn only (breaks Windows), 3) Platform-aware WSGI: Gunicorn on Linux, Waitress on Windows.", "Implement dual WSGI: Gunicorn multi-process on Linux/macOS and Waitress with 8 worker threads on Windows.", "Guarantees production-grade concurrency across both operating systems with dedicated launch scripts.", "APPROVED & IMPLEMENTED", "HIGH"),
    ("ADR-006", "2026-10-17", "Dynamic Nginx Reverse Proxy with Multi-Worker Load Balancing", "Handling simultaneous photo uploads from multiple lecture halls without dropping requests.", "1) Single standalone WSGI instance, 2) Cloudflare tunnel only, 3) Local dynamic Nginx upstream load balancer.", "Deploy dynamic Nginx upstream cluster distributing incoming requests round-robin to WSGI worker backends.", "Buffers large multipart photo uploads, offloads SSL termination, and handles 10+ concurrent classroom streams.", "APPROVED & IMPLEMENTED", "CRITICAL"),
    ("ADR-007", "2026-09-22", "Progressive Web App (PWA) Offline-First App Shell", "Faculty need attendance logging accessibility even during intermittent campus Wi-Fi outages.", "1) Native iOS/Android apps, 2) Responsive web only, 3) Progressive Web App with Service Worker App Shell.", "Implement PWA with /sw.js caching UI assets, web manifest, and dedicated /offline fallback route.", "Zero app store deployment friction; installable directly to mobile home screen with offline resilience.", "APPROVED & IMPLEMENTED", "MEDIUM"),
    ("ADR-008", "2026-05-03", "512-Dimensional Hyperspherical Normalization Standard", "Ensuring consistent similarity thresholds across different lighting and capture devices.", "1) Unnormalized Euclidean distance, 2) Raw dot product, 3) Hyperspherical L2 normalization (||v||_2 = 1.000000).", "Enforce strict L2 normalization on all ArcFace embeddings: v_norm = v / ||v||_2. Tolerance: 1e-6.", "Mathematical guarantee that Cosine similarity equals dot product; uniform threshold 0.55 across all classes.", "APPROVED & IMPLEMENTED", "HIGH"),
    ("ADR-009", "2026-09-16", "Hybrid Authentication Architecture & Ngrok HTTPS Tunneling", "Faculty require OAuth login while exposing the application securely via ngrok tunnels for testing.", "1) HTTP only, 2) Basic auth, 3) Supabase OAuth with SameSite=None, Secure=True session cookie dynamic configuration.", "Configure Flask session cookies with SameSite=None, Secure=True and enforce HTTPS redirect callback scheme.", "Enables secure OAuth login over public ngrok tunnels without session drop or CSRF vulnerabilities.", "APPROVED & IMPLEMENTED", "HIGH"),
    ("ADR-010", "2026-10-13", "Mobile Native Camera Launcher Integration", "Mobile browser WebRTC video streams frequently fail autofocus on small student ID cards.", "1) In-browser WebRTC canvas, 2) Native mobile camera file input (<input capture='environment'>).", "Adopt native file input launcher with capture='environment' on mobile viewports.", "Leverages native device camera ISP, macro mode, optical autofocus, and 12+ megapixel resolution.", "APPROVED & IMPLEMENTED", "MEDIUM"),
    ("ADR-011", "2026-10-22", "Automated Programmatic Technical Documentation Hub", "Maintain synchronized, perfectly formatted technical specifications across PDF, DOCX, and Markdown.", "1) Manual Word document editing, 2) Static Markdown only, 3) Programmatic generation via ReportLab & python-docx.", "Build reproducible Python scripts (generate_*.py) generating exact 10-page master PDF and 1-page executive brief.", "Guarantees 100% data parity, automated validation of constraints, and professional typography.", "APPROVED & IMPLEMENTED", "MEDIUM"),
    ("ADR-012", "2026-10-22", "Ponytail Pragmatic & Minimalist Code Standard", "Prevent speculative architecture, dead code paths, and excessive abstraction layers.", "1) Heavy enterprise frameworks with multi-layer factories, 2) Ponytail 7-Rung decision ladder & YAGNI ruleset.", "Enforce Ponytail standard: prioritize built-ins, existing packages, inline simplicity, and zero defensive bloat.", "Lean, highly maintainable codebase (<3,500 core Python lines) with zero redundant dependencies.", "APPROVED & IMPLEMENTED", "HIGH"),
]

# --- Sheet 6: Testing & Verification Matrix ---
TEST_CASES = [
    ("TC-001", "Unit", "Face Cache Normalization", ".venv/bin/pytest tests/unit/test_face_cache.py -k test_normalize_embedding_with_array", "test_normalize_embedding_with_array", "Norm of output vector equals 1.0 within 1e-6 tolerance", "np.linalg.norm(v) == 1.0", "Passed (Norm = 1.0000000)", "0.02s", "PASSED"),
    ("TC-002", "Unit", "Zero-Norm Embedding Safety", ".venv/bin/pytest tests/unit/test_face_cache.py -k test_normalize_embedding_with_zero_norm", "test_normalize_embedding_with_zero_norm", "Zero vector inputs return identical zeros without division by zero", "Returns zero array of shape (512,)", "Passed (Zero array returned)", "0.01s", "PASSED"),
    ("TC-003", "Unit", "JSON String Vector Deserializer", ".venv/bin/pytest tests/unit/test_face_cache.py -k test_normalize_embedding_with_json_string", "test_normalize_embedding_with_json_string", "Parse JSON array string '[0.1, -0.2, ...]' into normalized float32 array", "Output is np.ndarray float32", "Passed (Float32 array verified)", "0.02s", "PASSED"),
    ("TC-004", "Unit", "Bracket String Deserializer", ".venv/bin/pytest tests/unit/test_face_cache.py -k test_normalize_embedding_with_bracket_string", "test_normalize_embedding_with_bracket_string", "Parse bracketed string format from pgvector without JSON quotes", "Output is normalized 512D vector", "Passed (Vector parsed correctly)", "0.02s", "PASSED"),
    ("TC-005", "Unit", "Cache Add & Batch Match", ".venv/bin/pytest tests/unit/test_face_cache.py -k test_add_student_to_cache_and_match", "test_add_student_to_cache_and_match", "Enrolled student matches identical query vector with similarity >= 0.99", "Similarity score >= 0.999", "Passed (Score = 1.0000000)", "0.04s", "PASSED"),
    ("TC-006", "Unit", "Standard Student ID OCR", ".venv/bin/pytest tests/unit/test_ocr_helpers.py -k test_parse_student_id_text_standard_university", "test_parse_student_id_text_standard_university", "Extract Student Name, Roll No, Branch, and Course accurately", "Fields populated with expected regex matches", "Passed (All 4 fields extracted)", "0.03s", "PASSED"),
    ("TC-007", "Unit", "Multiline ID Card Text Split", ".venv/bin/pytest tests/unit/test_ocr_helpers.py -k test_parse_student_id_text_multiline_split", "test_parse_student_id_text_multiline_split", "Extract multiline academic institution titles and names", "Fields joined correctly without truncation", "Passed (Clean joined strings)", "0.02s", "PASSED"),
    ("TC-008", "Unit", "ID Card Image Preprocessing", ".venv/bin/pytest tests/unit/test_ocr_helpers.py -k test_preprocess_id_card_image", "test_preprocess_id_card_image", "Produce high-contrast grayscale/binary image buffer for OCR engine", "Clean binary thresholded image returned", "Passed (Image enhanced successfully)", "0.05s", "PASSED"),
    ("TC-009", "Unit", "Service Health Endpoint", ".venv/bin/pytest tests/unit/test_routes.py -k test_healthz_endpoint", "test_healthz_endpoint", "HTTP 200 response with JSON status: 'ok'", "HTTP 200 {'status': 'ok'}", "Passed (HTTP 200 OK)", "0.03s", "PASSED"),
    ("TC-010", "Unit", "Web App Manifest Route", ".venv/bin/pytest tests/unit/test_routes.py -k test_manifest_endpoint", "test_manifest_endpoint", "HTTP 200 response with JSON Content-Type and valid PWA icons", "Valid manifest.json with 5+ icon sizes", "Passed (PWA manifest valid)", "0.02s", "PASSED"),
    ("TC-011", "Unit", "Offline Fallback Route", ".venv/bin/pytest tests/unit/test_routes.py -k test_offline_page_endpoint", "test_offline_page_endpoint", "HTTP 200 response delivering standalone offline user interface", "HTTP 200 HTML offline screen", "Passed (Offline page rendered)", "0.02s", "PASSED"),
    ("TC-012", "Unit", "Service Worker Script Route", ".venv/bin/pytest tests/unit/test_routes.py -k test_service_worker_endpoint", "test_service_worker_endpoint", "HTTP 200 response serving /sw.js with application/javascript", "HTTP 200 JavaScript MIME type", "Passed (Service worker delivered)", "0.02s", "PASSED"),
    ("TC-013", "Unit", "404 Error Handler Route", ".venv/bin/pytest tests/unit/test_routes.py -k test_error_404_handler", "test_error_404_handler", "HTTP 404 response serving custom branded error template", "HTTP 404 with custom branded template", "Passed (Custom 404 page rendered)", "0.02s", "PASSED"),
    ("TC-014", "Unit", "Academic Options API", ".venv/bin/pytest tests/unit/test_routes.py -k test_api_academic_options", "test_api_academic_options", "HTTP 200 returning sorted, deduplicated programs and branches", "JSON arrays with distinct values", "Passed (Deduplicated options)", "0.03s", "PASSED"),
    ("TC-015", "Integration", "High-Concurrency Load Test", "Nginx benchmark via wrk/ab: 10 concurrent clients for 60s", "Nginx -> WSGI Workers", "Zero HTTP 500/502 gateway errors; 99th percentile latency < 500ms", "0 dropped connections, p99 = 280ms", "Passed (p99 = 245ms)", "60.0s", "PASSED"),
    ("TC-016", "Security", "Brute-Force Rate Limiting", "Simulated 10 rapid failed login requests from identical IP", "src/utils/auth_helpers.py", "IP locked out on 6th attempt; returns HTTP 429 Too Many Requests", "HTTP 429 Rate Limit Enforced", "Passed (Locked out after 5 tries)", "1.20s", "PASSED"),
    ("TC-017", "Cross-Platform", "Windows & Linux Startup", "Executed start_face_attendance.sh and start_face_attendance.bat", "Nginx + WSGI Launch Scripts", "Both environments boot Nginx reverse proxy and WSGI listener on port 8066", "Services active on localhost:8066", "Passed (Clean dual-OS boot)", "4.50s", "PASSED"),
    ("TC-018", "Compliance", "Patent Exclusion in Overviews", "PyMuPDF scan across generated PDF/DOCX documentation files", "Overview PDF/DOCX generators", "Zero occurrences of words 'patent', 'IDF', or 'filing status'", "Strict 0 occurrences detected", "Passed (0 matches confirmed)", "0.80s", "PASSED"),
]

# --- Sheet 7: Git Commit Audit Log ---
GIT_AUDIT_LOG = [
    ("e98024f", "2026-10-17", "ArnavPundir22", "fix", "windows", "Move portable Nginx download to Python to avoid CMD batch syntax errors", "M-20"),
    ("0a0fd20", "2026-10-17", "ArnavPundir22", "fix", "windows", "Resolve batch syntax error (. was unexpected) and improve Windows startup robustness", "M-20"),
    ("06aee3e", "2026-10-17", "ArnavPundir22", "feat", "nginx", "Dynamic Nginx load balancer setup and updated startup scripts", "M-20"),
    ("ae9462a", "2026-10-15", "ArnavPundir22", "fix", "attendance", "High-res face detection (det_size 1280), in-memory EWMA drift, async health logging", "M-19"),
    ("3430c30", "2026-10-13", "ArnavPundir22", "feat", "mobile", "Mobile camera capture, pgvector deserialization fix, automated test suite", "M-18"),
    ("adfd22d", "2026-10-08", "ArnavPundir22", "chore", "core", "Updated project files for clean structure and better readability", "M-18"),
    ("e266ad9", "2026-09-29", "ArnavPundir22", "fix", "viewer", "Resolve status update missing parameters and matrix register rendering errors", "M-17"),
    ("d296256", "2026-09-22", "ArnavPundir22", "feat", "pwa", "Add Progressive Web App support, icon suite, offline mode, and student filters", "M-17"),
    ("78f3b6e", "2026-09-19", "ArnavPundir22", "docs", "hub", "Update comprehensive project documentation hub and architecture guides", "M-16"),
    ("8e876ab", "2026-09-18", "ArnavPundir22", "perf", "ocr", "Fast direct backend neural OCR with animated progress bar and mobile auto-scroll", "M-15"),
    ("9a79ba6", "2026-09-18", "ArnavPundir22", "feat", "ocr", "Simplify ID card scanning to high-res upload-only with RapidOCR auto-fill", "M-15"),
    ("4907b9a", "2026-09-16", "ArnavPundir22", "fix", "auth", "Enforce HTTPS callback scheme for OAuth redirects over ngrok", "M-16"),
    ("b118a4c", "2026-09-16", "ArnavPundir22", "fix", "auth", "Dynamic HTTPS session cookie configuration (SameSite=None, Secure=True for ngrok)", "M-16"),
    ("1c18a1d", "2026-09-16", "ArnavPundir22", "fix", "auth", "Detailed error logging and permanent session cookies for OAuth flow", "M-16"),
    ("0a7b9d7", "2026-09-16", "ArnavPundir22", "fix", "auth", "Resolve OAuth login redirect loop by adding username fallback and Lax cookie config", "M-16"),
    ("9033ab7", "2026-09-16", "ArnavPundir22", "docs", "config", "Add Supabase Auth redirect configuration for port 8066", "M-16"),
    ("0caf983", "2026-09-16", "ArnavPundir22", "config", "ops", "Update Windows production server and tunnel port to 8066", "M-13"),
    ("8defee5", "2026-09-16", "ArnavPundir22", "fix", "vision", "Restore model instantiation in face.py before prepare()", "M-19"),
    ("abb318e", "2026-09-16", "ArnavPundir22", "perf", "wsgi", "Enable automatic GPU fallback and tune Waitress thread pool for high-core systems", "M-13"),
    ("0f78155", "2026-09-16", "ArnavPundir22", "feat", "compat", "Update requirements and setup scripts for Windows and Python 3.14 compatibility", "M-13"),
    ("14af1e4", "2026-09-09", "ArnavPundir22", "chore", "clean", "Removed unnecessary temporary scripts and artifacts", "M-14"),
    ("7a49dc8", "2026-09-04", "ArnavPundir22", "feat", "ui", "Restore guided live camera frame UI on student registration page", "M-14"),
    ("a62e88d", "2026-09-04", "ArnavPundir22", "fix", "students", "Alert user when student ID or email is already registered", "M-14"),
    ("ff1e0aa", "2026-09-02", "ArnavPundir22", "fix", "storage", "Auto-create known_faces directory and update setup docs", "M-14"),
    ("4107f5f", "2026-08-31", "ArnavPundir22", "feat", "perf", "Implement Option 1 in-memory BLAS matrix batch face matching (<1ms)", "M-12"),
    ("18b535e", "2026-08-31", "ArnavPundir22", "perf", "windows", "Optimize Waitress with 8 threads for dual Xeon 8-core CPU", "M-13"),
    ("9abb040", "2026-08-31", "ArnavPundir22", "fix", "windows", "Use Waitress WSGI server and supabase_admin for reliable database writes", "M-13"),
    ("78f2123", "2026-08-27", "ArnavPundir22", "feat", "records", "Auto-infer program and branch when lecture filter is selected on records page", "M-11"),
    ("d38ea9e", "2026-08-27", "ArnavPundir22", "feat", "records", "Ensure latest attendance records sort descending and auto-select most recent lecture", "M-11"),
    ("2dd5545", "2026-08-27", "ArnavPundir22", "chore", "deps", "Update dependencies for Windows/Linux, security scripts, and latest UI enhancements", "M-11"),
    ("5c6089a", "2026-08-05", "ArnavPundir22", "chore", "clean", "Remove unwanted files and update face attendance system files", "M-11"),
    ("fabe693", "2026-08-02", "ArnavPundir22", "chore", "deps", "Remove unused libraries and version pins from requirements.txt", "M-11"),
    ("6b88072", "2026-08-01", "ArnavPundir22", "feat", "admin", "Add client-side search and filters to admin student records portal", "M-11"),
    ("bf933d0", "2026-08-01", "ArnavPundir22", "fix", "errors", "Import render_template to resolve 500 error handler compilation NameError", "M-11"),
    ("cc1a6b4", "2026-08-01", "ArnavPundir22", "feat", "errors", "Build custom error pages (404, 403, 500) and implement client offline detector", "M-11"),
    ("1022c6a", "2026-08-01", "ArnavPundir22", "fix", "filters", "Make dropdown filters case-insensitive and remove duplicate items", "M-11"),
    ("cfaec25", "2026-08-01", "ArnavPundir22", "feat", "attendance", "Add program, branch, and year filters to manual attendance page", "M-11"),
    ("7ed39b3", "2026-08-01", "ArnavPundir22", "fix", "students", "Implement cascading delete to successfully remove students from DB and disk", "M-11"),
    ("b58c542", "2026-08-01", "ArnavPundir22", "design", "ui", "Remove subnav buttons, add filters, sorting, and export back to students view", "M-11"),
    ("480e18d", "2026-08-01", "ArnavPundir22", "design", "ui", "Remove actions column from public all students page", "M-11"),
    ("afdedf7", "2026-08-01", "ArnavPundir22", "design", "ui", "Convert public students page to look exactly like admin manage students list", "M-11"),
    ("a81d47b", "2026-08-01", "ArnavPundir22", "design", "ui", "Align table columns, cell spacing, text color, and row styling on students page", "M-11"),
    ("a60bba8", "2026-08-01", "ArnavPundir22", "design", "ui", "Update all students page layout to match admin students view style", "M-11"),
    ("b7bc60d", "2026-08-01", "ArnavPundir22", "fix", "ui", "Resolve text contrast for all student filters and improve matching", "M-11"),
    ("9e79695", "2026-08-01", "ArnavPundir22", "fix", "ui", "Resolve layout alignment offsets and light-mode text readability", "M-11"),
    ("34d3477", "2026-07-31", "ArnavPundir22", "docs", "mermaid", "Wrap Mermaid subgraph titles in quotes to fix parse error on GitHub docs", "M-10"),
    ("ac5eb67", "2026-07-31", "ArnavPundir22", "chore", "core", "Update system styles, admin templates, and student registration logic", "M-10"),
    ("f40e9e7", "2026-07-30", "ArnavPundir22", "docs", "structure", "Restructure codebase and update comprehensive documentation", "M-10"),
    ("d1f308e", "2026-07-14", "ArnavPundir22", "feat", "wsgi", "Refactor configuration management and add Gunicorn production deployment tooling", "M-09"),
    ("60a6884", "2026-07-14", "ArnavPundir22", "docs", "brand", "Rename app references to BioSecure AI to match UI title", "M-10"),
    ("ac5ec94", "2026-07-14", "ArnavPundir22", "docs", "brand", "Update setup, architecture, and database guides for latest stateless refactoring", "M-10"),
    ("fb72a30", "2026-07-14", "ArnavPundir22", "refactor", "core", "Refactored the whole system for modular scalability", "M-09"),
    ("46841dc", "2026-05-16", "ArnavPundir22", "security", "env", "Removed hardcoded keys and credentials, updated environment variables", "M-07"),
    ("8a03253", "2026-05-04", "ArnavPundir22", "perf", "threshold", "Improved face recognition cosine similarity threshold for high precision", "M-06"),
    ("7e3b09a", "2026-05-04", "ArnavPundir22", "feat", "db", "Updated Supabase database structure with pgvector extension", "M-08"),
    ("25008e5", "2026-05-04", "ArnavPundir22", "feat", "db", "Added Row-Level Security (RLS) policies to database tables", "M-08"),
    ("57976d9", "2026-05-04", "ArnavPundir22", "feat", "attendance", "Updated attendance marking logic for bulk student matching", "M-06"),
    ("6cc7758", "2026-05-04", "ArnavPundir22", "feat", "admin", "User management in admin panel (list, edit, delete users)", "M-05"),
    ("c51b0f5", "2026-05-03", "ArnavPundir22", "perf", "matrix", "Replace O(N) Python for-loop face search with vectorized BLAS matrix multiply", "M-06"),
    ("833e206", "2026-05-03", "ArnavPundir22", "feat", "arch", "Replace pickle with numpy encoding, split into blueprints, add nginx config", "M-04"),
    ("267ec96", "2026-05-03", "ArnavPundir22", "feat", "sec", "Add login rate-limiting and email-OTP password reset", "M-07"),
    ("02a8d4a", "2026-04-10", "ArnavPundir22", "feat", "init", "Initial baseline vector attendance commit", "M-01"),
    ("5a84133", "2025-11-17", "ArnavPundir22", "feat", "prototype", "Core student registration and camera stream capture", "M-03"),
    ("fd84d90", "2025-08-23", "ArnavPundir22", "feat", "prototype", "Web-based photo upload and attendance logging interface", "M-02"),
    ("4d09476", "2025-08-06", "ArnavPundir22", "feat", "init", "Initial prototype repository commit", "M-01"),
]


# -----------------------------------------------------------------------------
# Modern OpenXML Generator (.xlsx via openpyxl)
# -----------------------------------------------------------------------------
def build_modern_xlsx(filename):
    wb = openpyxl.Workbook()
    # Remove default sheet
    wb.remove(wb.active)
    
    # ---------------------------------------------------------
    # Sheet 1: Executive Dashboard & KPIs
    # ---------------------------------------------------------
    ws1 = wb.create_sheet(title="Executive_Dashboard")
    ws1.views.sheetView[0].showGridLines = True
    
    # Title Banner
    ws1.merge_cells("A1:H1")
    t1 = ws1["A1"]
    t1.value = "BioSecure AI — Engineering Log Book & Project Tracker"
    t1.font = Font(name="Calibri", size=18, bold=True, color=WHITE)
    t1.fill = PatternFill(start_color=NAVY_HEADER, end_color=NAVY_HEADER, fill_type="solid")
    t1.alignment = Alignment(horizontal="center", vertical="center")
    ws1.row_dimensions[1].height = 40
    
    ws1.merge_cells("A2:H2")
    t2 = ws1["A2"]
    t2.value = "Institutional Milestone Tracker, Sprint Execution Records, Defect Resolution Matrix & Architectural Decision Log"
    t2.font = Font(name="Calibri", size=10, italic=True, color=WHITE)
    t2.fill = PatternFill(start_color=SLATE_HEADER, end_color=SLATE_HEADER, fill_type="solid")
    t2.alignment = Alignment(horizontal="center", vertical="center")
    ws1.row_dimensions[2].height = 22
    
    # Section Header: Project Metadata
    ws1.merge_cells("A4:D4")
    m_head = ws1["A4"]
    m_head.value = "PROJECT METADATA & INSTITUTIONAL CONTEXT"
    m_head.font = Font(name="Calibri", size=11, bold=True, color=NAVY_HEADER)
    m_head.fill = PatternFill(start_color=CARD_BG, end_color=CARD_BG, fill_type="solid")
    m_head.alignment = Alignment(horizontal="left", vertical="center", indent=1)
    ws1.row_dimensions[4].height = 24
    
    # Section Header: Key Operational KPIs
    ws1.merge_cells("F4:H4")
    k_head = ws1["F4"]
    k_head.value = "KEY SYSTEM PERFORMANCE METRICS"
    k_head.font = Font(name="Calibri", size=11, bold=True, color=NAVY_HEADER)
    k_head.fill = PatternFill(start_color=CARD_BG, end_color=CARD_BG, fill_type="solid")
    k_head.alignment = Alignment(horizontal="left", vertical="center", indent=1)
    
    # Metadata Table (Cols A-D)
    r_meta_start = 5
    for idx, (label, val) in enumerate(METADATA_ROWS):
        r = r_meta_start + idx
        ws1.row_dimensions[r].height = 20
        c_lbl = ws1.cell(row=r, column=1, value=label)
        c_lbl.font = Font(name="Calibri", size=10, bold=True, color="334155")
        c_lbl.alignment = Alignment(horizontal="left", vertical="center")
        
        ws1.merge_cells(start_row=r, start_column=2, end_row=r, end_column=4)
        c_val = ws1.cell(row=r, column=2, value=val)
        c_val.font = Font(name="Calibri", size=10, color="0F172A")
        c_val.alignment = Alignment(horizontal="left", vertical="center")
        
        # Borders
        thin = Side(border_style="thin", color=BORDER_COLOR)
        b_box = Border(left=thin, right=thin, top=thin, bottom=thin)
        c_lbl.border = b_box
        for c in range(2, 5):
            ws1.cell(row=r, column=c).border = b_box
            
    # KPI Metric Cards (Cols F-H)
    for idx, (val, title, desc) in enumerate(KPI_CARDS):
        r = r_meta_start + idx
        c_num = ws1.cell(row=r, column=6, value=val)
        c_num.font = Font(name="Calibri", size=11, bold=True, color=BLUE_ACCENT)
        c_num.fill = PatternFill(start_color=CARD_BG, end_color=CARD_BG, fill_type="solid")
        c_num.alignment = Alignment(horizontal="center", vertical="center")
        
        c_title = ws1.cell(row=r, column=7, value=title)
        c_title.font = Font(name="Calibri", size=10, bold=True, color="1E293B")
        c_title.alignment = Alignment(horizontal="left", vertical="center")
        
        c_desc = ws1.cell(row=r, column=8, value=desc)
        c_desc.font = Font(name="Calibri", size=9, italic=True, color="64748B")
        c_desc.alignment = Alignment(horizontal="left", vertical="center")
        
        thin = Side(border_style="thin", color=BORDER_COLOR)
        b_box = Border(left=thin, right=thin, top=thin, bottom=thin)
        c_num.border = b_box
        c_title.border = b_box
        c_desc.border = b_box

    # Section Header: Engineering Phase Completion
    ws1.merge_cells("A14:H14")
    ph_head = ws1["A14"]
    ph_head.value = "ENGINEERING LIFECYCLE PHASES & COMPLETION PROGRESS"
    ph_head.font = Font(name="Calibri", size=11, bold=True, color=WHITE)
    ph_head.fill = PatternFill(start_color=BLUE_ACCENT, end_color=BLUE_ACCENT, fill_type="solid")
    ph_head.alignment = Alignment(horizontal="left", vertical="center", indent=1)
    ws1.row_dimensions[14].height = 24
    
    headers_phase = ["Phase ID", "Phase Name", "Primary Engineering Scope", "Planned Timeline", "Actual Completion", "Milestones", "Key Tasks", "Status", "Progress"]
    start_r = 15
    for c_idx, h in enumerate(headers_phase, start=1):
        cell = ws1.cell(row=start_r, column=c_idx, value=h)
        cell.font = Font(name="Calibri", size=10, bold=True, color=WHITE)
        cell.fill = PatternFill(start_color=NAVY_HEADER, end_color=NAVY_HEADER, fill_type="solid")
        cell.alignment = Alignment(horizontal="center", vertical="center")
    ws1.row_dimensions[start_r].height = 24
    
    for idx, row_data in enumerate(PHASES_SUMMARY, start=start_r + 1):
        ws1.row_dimensions[idx].height = 20
        for c_idx, val in enumerate(row_data, start=1):
            cell = ws1.cell(row=idx, column=c_idx, value=val)
            cell.font = Font(name="Calibri", size=10)
            if c_idx in [1, 4, 5, 6, 7, 8, 9]:
                cell.alignment = Alignment(horizontal="center", vertical="center")
            else:
                cell.alignment = Alignment(horizontal="left", vertical="center")
            
            # Status Badge Fill
            if c_idx == 8 and val == "COMPLETED":
                cell.fill = PatternFill(start_color=STATUS_DONE_FILL, end_color=STATUS_DONE_FILL, fill_type="solid")
                cell.font = Font(name="Calibri", size=10, bold=True, color=STATUS_DONE_FONT)
            elif c_idx == 9:
                cell.font = Font(name="Calibri", size=10, bold=True, color="047857")

    apply_table_styles(ws1, start_r, start_r + len(PHASES_SUMMARY), 1, len(headers_phase))
    
    # Section Header: Subsystem Readiness Matrix
    start_sub = start_r + len(PHASES_SUMMARY) + 2
    ws1.merge_cells(f"A{start_sub}:H{start_sub}")
    sub_head = ws1[f"A{start_sub}"]
    sub_head.value = "CORE SUBSYSTEM READINESS & OPERATIONAL STATUS"
    sub_head.font = Font(name="Calibri", size=11, bold=True, color=WHITE)
    sub_head.fill = PatternFill(start_color=TEAL_HEADER, end_color=TEAL_HEADER, fill_type="solid")
    sub_head.alignment = Alignment(horizontal="left", vertical="center", indent=1)
    ws1.row_dimensions[start_sub].height = 24
    
    headers_sub = ["Subsystem Name", "Underlying Technology", "Readiness State", "Architecture & Operational Capability"]
    start_sub_table = start_sub + 1
    
    # Write Subsystem Headers
    ws1.cell(row=start_sub_table, column=1, value=headers_sub[0])
    ws1.cell(row=start_sub_table, column=2, value=headers_sub[1])
    ws1.cell(row=start_sub_table, column=3, value=headers_sub[2])
    ws1.merge_cells(f"D{start_sub_table}:H{start_sub_table}")
    ws1.cell(row=start_sub_table, column=4, value=headers_sub[3])
    
    for c in range(1, 9):
        cell = ws1.cell(row=start_sub_table, column=c)
        cell.font = Font(name="Calibri", size=10, bold=True, color=WHITE)
        cell.fill = PatternFill(start_color=NAVY_HEADER, end_color=NAVY_HEADER, fill_type="solid")
        cell.alignment = Alignment(horizontal="center", vertical="center")
    ws1.row_dimensions[start_sub_table].height = 24
    
    for idx, (sub_name, tech, state, cap) in enumerate(SUBSYSTEM_READINESS, start=start_sub_table + 1):
        ws1.row_dimensions[idx].height = 20
        c1 = ws1.cell(row=idx, column=1, value=sub_name)
        c2 = ws1.cell(row=idx, column=2, value=tech)
        c3 = ws1.cell(row=idx, column=3, value=state)
        ws1.merge_cells(f"D{idx}:H{idx}")
        c4 = ws1.cell(row=idx, column=4, value=cap)
        
        c1.alignment = Alignment(horizontal="left", vertical="center")
        c2.alignment = Alignment(horizontal="left", vertical="center")
        c3.alignment = Alignment(horizontal="center", vertical="center")
        c4.alignment = Alignment(horizontal="left", vertical="center")
        
        c3.fill = PatternFill(start_color=STATUS_DONE_FILL, end_color=STATUS_DONE_FILL, fill_type="solid")
        c3.font = Font(name="Calibri", size=10, bold=True, color=STATUS_DONE_FONT)
        
        thin = Side(border_style="thin", color=BORDER_COLOR)
        b_box = Border(left=thin, right=thin, top=thin, bottom=thin)
        c1.border = b_box
        c2.border = b_box
        c3.border = b_box
        for c in range(4, 9):
            ws1.cell(row=idx, column=c).border = b_box

    auto_fit_columns(ws1, min_width=14, max_width=45)
    
    # ---------------------------------------------------------
    # Sheet 2: Planning & Milestones Roadmap
    # ---------------------------------------------------------
    ws2 = wb.create_sheet(title="Planning_Milestones")
    ws2.views.sheetView[0].showGridLines = True
    ws2.freeze_panes = "A2"
    
    headers_m = [
        "Milestone ID", "Phase", "Milestone Title & Target Deliverable",
        "Planned Start", "Target Date", "Actual Date", "Variance (Days)",
        "Priority", "Lead Owner", "Status", "Success Criteria & Verification Benchmark",
        "Target Modules & Source Paths"
    ]
    
    for c_idx, h in enumerate(headers_m, start=1):
        cell = ws2.cell(row=1, column=c_idx, value=h)
        cell.font = Font(name="Calibri", size=11, bold=True, color=WHITE)
        cell.fill = PatternFill(start_color=NAVY_HEADER, end_color=NAVY_HEADER, fill_type="solid")
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
    ws2.row_dimensions[1].height = 28
    
    for r_idx, row_data in enumerate(MILESTONES_DATA, start=2):
        ws2.row_dimensions[r_idx].height = 22
        for c_idx, val in enumerate(row_data, start=1):
            cell = ws2.cell(row=r_idx, column=c_idx, value=val)
            cell.font = Font(name="Calibri", size=10)
            
            # Alignments
            if c_idx in [1, 2, 4, 5, 6, 7, 8, 9, 10]:
                cell.alignment = Alignment(horizontal="center", vertical="center")
            else:
                cell.alignment = Alignment(horizontal="left", vertical="center", wrap_text=True)
                
            # Status styling
            if c_idx == 10 and val == "COMPLETED":
                cell.fill = PatternFill(start_color=STATUS_DONE_FILL, end_color=STATUS_DONE_FILL, fill_type="solid")
                cell.font = Font(name="Calibri", size=10, bold=True, color=STATUS_DONE_FONT)
            elif c_idx == 8:
                if val == "Critical":
                    cell.font = Font(name="Calibri", size=10, bold=True, color="B91C1C")
                elif val == "High":
                    cell.font = Font(name="Calibri", size=10, bold=True, color="C2410C")
                else:
                    cell.font = Font(name="Calibri", size=10, color="0369A1")
                    
    apply_table_styles(ws2, 1, 1 + len(MILESTONES_DATA), 1, len(headers_m))
    auto_fit_columns(ws2, min_width=12, max_width=45)
    
    # ---------------------------------------------------------
    # Sheet 3: Building & Execution Tasks
    # ---------------------------------------------------------
    ws3 = wb.create_sheet(title="Execution_Log")
    ws3.views.sheetView[0].showGridLines = True
    ws3.freeze_panes = "A2"
    
    headers_tsk = [
        "Task ID", "Sprint", "Category", "Task Scope & Objective",
        "Technical Implementation Details", "Target Source Module",
        "Date Completed", "Commit Ref", "Status", "Impact & Performance Result"
    ]
    
    for c_idx, h in enumerate(headers_tsk, start=1):
        cell = ws3.cell(row=1, column=c_idx, value=h)
        cell.font = Font(name="Calibri", size=11, bold=True, color=WHITE)
        cell.fill = PatternFill(start_color=NAVY_HEADER, end_color=NAVY_HEADER, fill_type="solid")
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
    ws3.row_dimensions[1].height = 28
    
    for r_idx, row_data in enumerate(EXECUTION_TASKS, start=2):
        ws3.row_dimensions[r_idx].height = 22
        for c_idx, val in enumerate(row_data, start=1):
            cell = ws3.cell(row=r_idx, column=c_idx, value=val)
            cell.font = Font(name="Calibri", size=10)
            
            if c_idx in [1, 2, 3, 7, 8, 9]:
                cell.alignment = Alignment(horizontal="center", vertical="center")
            else:
                cell.alignment = Alignment(horizontal="left", vertical="center", wrap_text=True)
                
            if c_idx == 9 and val == "COMPLETED":
                cell.fill = PatternFill(start_color=STATUS_DONE_FILL, end_color=STATUS_DONE_FILL, fill_type="solid")
                cell.font = Font(name="Calibri", size=10, bold=True, color=STATUS_DONE_FONT)
            elif c_idx == 3:
                # Category tags
                cell.font = Font(name="Calibri", size=10, bold=True, color="1E3A8A")

    apply_table_styles(ws3, 1, 1 + len(EXECUTION_TASKS), 1, len(headers_tsk))
    auto_fit_columns(ws3, min_width=12, max_width=45)
    
    # ---------------------------------------------------------
    # Sheet 4: Bug Fixing & Defect Resolution Tracker
    # ---------------------------------------------------------
    ws4 = wb.create_sheet(title="Defect_Resolution_Log")
    ws4.views.sheetView[0].showGridLines = True
    ws4.freeze_panes = "A2"
    
    headers_bug = [
        "Bug ID", "Date Reported", "Component / Subsystem", "Severity",
        "Problem / Error Description", "Root Cause Analysis (RCA)",
        "Remediation / Fix Implemented", "Files Modified",
        "Verification Method", "Status", "Resolution Date"
    ]
    
    for c_idx, h in enumerate(headers_bug, start=1):
        cell = ws4.cell(row=1, column=c_idx, value=h)
        cell.font = Font(name="Calibri", size=11, bold=True, color=WHITE)
        cell.fill = PatternFill(start_color=NAVY_HEADER, end_color=NAVY_HEADER, fill_type="solid")
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
    ws4.row_dimensions[1].height = 28
    
    for r_idx, row_data in enumerate(DEFECT_TRACKER, start=2):
        ws4.row_dimensions[r_idx].height = 24
        for c_idx, val in enumerate(row_data, start=1):
            cell = ws4.cell(row=r_idx, column=c_idx, value=val)
            cell.font = Font(name="Calibri", size=10)
            
            if c_idx in [1, 2, 4, 10, 11]:
                cell.alignment = Alignment(horizontal="center", vertical="center")
            else:
                cell.alignment = Alignment(horizontal="left", vertical="center", wrap_text=True)
                
            # Severity color badges
            if c_idx == 4:
                if val == "CRITICAL":
                    cell.fill = PatternFill(start_color=SEV_CRIT_FILL, end_color=SEV_CRIT_FILL, fill_type="solid")
                    cell.font = Font(name="Calibri", size=10, bold=True, color=SEV_CRIT_FONT)
                elif val == "HIGH":
                    cell.fill = PatternFill(start_color=SEV_HIGH_FILL, end_color=SEV_HIGH_FILL, fill_type="solid")
                    cell.font = Font(name="Calibri", size=10, bold=True, color=SEV_HIGH_FONT)
                elif val == "MEDIUM":
                    cell.fill = PatternFill(start_color=SEV_MED_FILL, end_color=SEV_MED_FILL, fill_type="solid")
                    cell.font = Font(name="Calibri", size=10, bold=True, color=SEV_MED_FONT)
                elif val == "LOW":
                    cell.fill = PatternFill(start_color=SEV_LOW_FILL, end_color=SEV_LOW_FILL, fill_type="solid")
                    cell.font = Font(name="Calibri", size=10, bold=True, color=SEV_LOW_FONT)
            
            # Status badge
            if c_idx == 10 and val == "RESOLVED":
                cell.fill = PatternFill(start_color=STATUS_DONE_FILL, end_color=STATUS_DONE_FILL, fill_type="solid")
                cell.font = Font(name="Calibri", size=10, bold=True, color=STATUS_DONE_FONT)

    apply_table_styles(ws4, 1, 1 + len(DEFECT_TRACKER), 1, len(headers_bug))
    auto_fit_columns(ws4, min_width=12, max_width=45)
    
    # ---------------------------------------------------------
    # Sheet 5: Architecture Decisions (ADR Log)
    # ---------------------------------------------------------
    ws5 = wb.create_sheet(title="Architecture_Decisions")
    ws5.views.sheetView[0].showGridLines = True
    ws5.freeze_panes = "A2"
    
    headers_adr = [
        "ADR ID", "Decision Date", "Architectural Decision Title",
        "Context & Engineering Problem", "Alternatives Evaluated",
        "Chosen Architecture & Technical Rationale", "Consequences & Operational Trade-offs",
        "Status", "System Impact"
    ]
    
    for c_idx, h in enumerate(headers_adr, start=1):
        cell = ws5.cell(row=1, column=c_idx, value=h)
        cell.font = Font(name="Calibri", size=11, bold=True, color=WHITE)
        cell.fill = PatternFill(start_color=NAVY_HEADER, end_color=NAVY_HEADER, fill_type="solid")
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
    ws5.row_dimensions[1].height = 28
    
    for r_idx, row_data in enumerate(ADR_LOG, start=2):
        ws5.row_dimensions[r_idx].height = 24
        for c_idx, val in enumerate(row_data, start=1):
            cell = ws5.cell(row=r_idx, column=c_idx, value=val)
            cell.font = Font(name="Calibri", size=10)
            
            if c_idx in [1, 2, 8, 9]:
                cell.alignment = Alignment(horizontal="center", vertical="center")
            else:
                cell.alignment = Alignment(horizontal="left", vertical="center", wrap_text=True)
                
            if c_idx == 8:
                cell.fill = PatternFill(start_color=STATUS_DONE_FILL, end_color=STATUS_DONE_FILL, fill_type="solid")
                cell.font = Font(name="Calibri", size=10, bold=True, color=STATUS_DONE_FONT)
            elif c_idx == 9:
                if val == "CRITICAL":
                    cell.font = Font(name="Calibri", size=10, bold=True, color="B91C1C")
                elif val == "HIGH":
                    cell.font = Font(name="Calibri", size=10, bold=True, color="C2410C")

    apply_table_styles(ws5, 1, 1 + len(ADR_LOG), 1, len(headers_adr))
    auto_fit_columns(ws5, min_width=12, max_width=45)
    
    # ---------------------------------------------------------
    # Sheet 6: Testing & Verification Matrix
    # ---------------------------------------------------------
    ws6 = wb.create_sheet(title="Testing_Verification")
    ws6.views.sheetView[0].showGridLines = True
    ws6.freeze_panes = "A2"
    
    headers_tc = [
        "Test ID", "Test Level", "Target Module / Test Name", "Execution Command / Method",
        "Target Function / Endpoint", "Acceptance Criteria",
        "Expected Benchmark", "Actual Empirical Result", "Latency", "Result Status"
    ]
    
    for c_idx, h in enumerate(headers_tc, start=1):
        cell = ws6.cell(row=1, column=c_idx, value=h)
        cell.font = Font(name="Calibri", size=11, bold=True, color=WHITE)
        cell.fill = PatternFill(start_color=NAVY_HEADER, end_color=NAVY_HEADER, fill_type="solid")
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
    ws6.row_dimensions[1].height = 28
    
    for r_idx, row_data in enumerate(TEST_CASES, start=2):
        ws6.row_dimensions[r_idx].height = 22
        for c_idx, val in enumerate(row_data, start=1):
            cell = ws6.cell(row=r_idx, column=c_idx, value=val)
            cell.font = Font(name="Calibri", size=10)
            
            if c_idx in [1, 2, 9, 10]:
                cell.alignment = Alignment(horizontal="center", vertical="center")
            else:
                cell.alignment = Alignment(horizontal="left", vertical="center", wrap_text=True)
                
            if c_idx == 10 and val == "PASSED":
                cell.fill = PatternFill(start_color=STATUS_DONE_FILL, end_color=STATUS_DONE_FILL, fill_type="solid")
                cell.font = Font(name="Calibri", size=10, bold=True, color=STATUS_DONE_FONT)

    apply_table_styles(ws6, 1, 1 + len(TEST_CASES), 1, len(headers_tc))
    auto_fit_columns(ws6, min_width=12, max_width=45)
    
    # ---------------------------------------------------------
    # Sheet 7: Git Commit Audit Trail & Changelog
    # ---------------------------------------------------------
    ws7 = wb.create_sheet(title="Git_Commit_History")
    ws7.views.sheetView[0].showGridLines = True
    ws7.freeze_panes = "A2"
    
    headers_git = [
        "Commit Hash", "Date", "Author", "Type", "Scope / Subsystem",
        "Commit Message & Engineering Summary", "Milestone Ref"
    ]
    
    for c_idx, h in enumerate(headers_git, start=1):
        cell = ws7.cell(row=1, column=c_idx, value=h)
        cell.font = Font(name="Calibri", size=11, bold=True, color=WHITE)
        cell.fill = PatternFill(start_color=NAVY_HEADER, end_color=NAVY_HEADER, fill_type="solid")
        cell.alignment = Alignment(horizontal="center", vertical="center")
    ws7.row_dimensions[1].height = 28
    
    for r_idx, row_data in enumerate(GIT_AUDIT_LOG, start=2):
        ws7.row_dimensions[r_idx].height = 20
        for c_idx, val in enumerate(row_data, start=1):
            cell = ws7.cell(row=r_idx, column=c_idx, value=val)
            cell.font = Font(name="Calibri", size=10)
            
            if c_idx in [1, 2, 3, 4, 5, 7]:
                cell.alignment = Alignment(horizontal="center", vertical="center")
            else:
                cell.alignment = Alignment(horizontal="left", vertical="center")
                
            if c_idx == 1:
                cell.font = Font(name="Consolas", size=9, bold=True, color="1E3A8A")
            elif c_idx == 4:
                # Type highlight
                if val == "feat":
                    cell.font = Font(name="Calibri", size=10, bold=True, color="047857")
                elif val == "fix":
                    cell.font = Font(name="Calibri", size=10, bold=True, color="B91C1C")
                elif val == "perf":
                    cell.font = Font(name="Calibri", size=10, bold=True, color="6D28D9")

    apply_table_styles(ws7, 1, 1 + len(GIT_AUDIT_LOG), 1, len(headers_git))
    auto_fit_columns(ws7, min_width=12, max_width=50)
    
    # Save Modern XLSX
    wb.save(filename)
    print(f"✅ Generated modern XLSX tracker: {filename}")


# -----------------------------------------------------------------------------
# Native BIFF8 Generator (.xls via xlwt)
# -----------------------------------------------------------------------------
def build_native_xls(filename):
    wb = xlwt.Workbook(encoding="utf-8")
    
    # Styles
    f_header = xlwt.Font()
    f_header.name = "Calibri"
    f_header.bold = True
    f_header.color_index = xlwt.Style.colour_map["white"]
    
    p_header = xlwt.Pattern()
    p_header.pattern = xlwt.Pattern.SOLID_PATTERN
    p_header.pattern_fore_colour = xlwt.Style.colour_map["dark_blue_ega"]
    
    style_header = xlwt.XFStyle()
    style_header.font = f_header
    style_header.pattern = p_header
    style_header.alignment.horz = xlwt.Alignment.HORZ_CENTER
    style_header.alignment.vert = xlwt.Alignment.VERT_CENTER
    style_header.alignment.wrap = xlwt.Alignment.WRAP_AT_RIGHT
    
    style_cell_center = xlwt.XFStyle()
    style_cell_center.alignment.horz = xlwt.Alignment.HORZ_CENTER
    style_cell_center.alignment.vert = xlwt.Alignment.VERT_CENTER
    
    style_cell_left = xlwt.XFStyle()
    style_cell_left.alignment.horz = xlwt.Alignment.HORZ_LEFT
    style_cell_left.alignment.vert = xlwt.Alignment.VERT_CENTER
    
    style_bold_left = xlwt.XFStyle()
    f_bold = xlwt.Font()
    f_bold.bold = True
    style_bold_left.font = f_bold
    style_bold_left.alignment.horz = xlwt.Alignment.HORZ_LEFT
    style_bold_left.alignment.vert = xlwt.Alignment.VERT_CENTER
    
    # Sheet 1: Dashboard
    ws1 = wb.add_sheet("Executive_Dashboard")
    ws1.write_merge(0, 0, 0, 7, "BioSecure AI — Engineering Log Book & Project Tracker", style_header)
    
    row_idx = 2
    ws1.write_merge(row_idx, row_idx, 0, 3, "PROJECT METADATA", style_header)
    row_idx += 1
    for label, val in METADATA_ROWS:
        ws1.write(row_idx, 0, label, style_bold_left)
        ws1.write_merge(row_idx, row_idx, 1, 3, val, style_cell_left)
        row_idx += 1
        
    row_idx += 1
    ws1.write_merge(row_idx, row_idx, 0, 8, "ENGINEERING PHASES SUMMARY", style_header)
    row_idx += 1
    headers_phase = ["Phase ID", "Phase Name", "Primary Scope", "Timeline", "Completion", "Milestones", "Tasks", "Status", "Progress"]
    for c_idx, h in enumerate(headers_phase):
        ws1.write(row_idx, c_idx, h, style_header)
    row_idx += 1
    for r_data in PHASES_SUMMARY:
        for c_idx, val in enumerate(r_data):
            st = style_cell_center if c_idx in [0, 3, 4, 5, 6, 7, 8] else style_cell_left
            ws1.write(row_idx, c_idx, val, st)
        row_idx += 1
        
    for c in range(9):
        ws1.col(c).width = 256 * 20
    ws1.col(1).width = 256 * 26
    ws1.col(2).width = 256 * 40
        
    # Sheet 2: Milestones
    ws2 = wb.add_sheet("Milestones")
    headers_m = ["Milestone ID", "Phase", "Title & Objective", "Start", "Target", "Actual", "Variance", "Priority", "Owner", "Status", "Success Criteria", "Paths"]
    for c_idx, h in enumerate(headers_m):
        ws2.write(0, c_idx, h, style_header)
    for r_idx, r_data in enumerate(MILESTONES_DATA, start=1):
        for c_idx, val in enumerate(r_data):
            st = style_cell_center if c_idx in [0, 1, 3, 4, 5, 6, 7, 8, 9] else style_cell_left
            ws2.write(r_idx, c_idx, str(val), st)
    for c in range(len(headers_m)):
        ws2.col(c).width = 256 * 18
    ws2.col(2).width = 256 * 35
    ws2.col(10).width = 256 * 40

    # Sheet 3: Execution Log
    ws3 = wb.add_sheet("Execution_Log")
    headers_tsk = ["Task ID", "Sprint", "Category", "Task Name", "Technical Scope", "Module", "Completed", "Commit", "Status", "Impact"]
    for c_idx, h in enumerate(headers_tsk):
        ws3.write(0, c_idx, h, style_header)
    for r_idx, r_data in enumerate(EXECUTION_TASKS, start=1):
        for c_idx, val in enumerate(r_data):
            st = style_cell_center if c_idx in [0, 1, 2, 6, 7, 8] else style_cell_left
            ws3.write(r_idx, c_idx, str(val), st)
    for c in range(len(headers_tsk)):
        ws3.col(c).width = 256 * 18
    ws3.col(3).width = 256 * 30
    ws3.col(4).width = 256 * 45
    ws3.col(9).width = 256 * 35

    # Sheet 4: Defects
    ws4 = wb.add_sheet("Defect_Resolution")
    headers_bug = ["Bug ID", "Date", "Component", "Severity", "Error Description", "Root Cause Analysis", "Remediation Implemented", "Files", "Verification", "Status", "Resolved"]
    for c_idx, h in enumerate(headers_bug):
        ws4.write(0, c_idx, h, style_header)
    for r_idx, r_data in enumerate(DEFECT_TRACKER, start=1):
        for c_idx, val in enumerate(r_data):
            st = style_cell_center if c_idx in [0, 1, 3, 9, 10] else style_cell_left
            ws4.write(r_idx, c_idx, str(val), st)
    for c in range(len(headers_bug)):
        ws4.col(c).width = 256 * 16
    ws4.col(4).width = 256 * 40
    ws4.col(5).width = 256 * 40
    ws4.col(6).width = 256 * 40

    # Sheet 5: ADRs
    ws5 = wb.add_sheet("ADR_Decisions")
    headers_adr = ["ADR ID", "Date", "Title", "Problem Context", "Alternatives", "Chosen Decision", "Tradeoffs", "Status", "Impact"]
    for c_idx, h in enumerate(headers_adr):
        ws5.write(0, c_idx, h, style_header)
    for r_idx, r_data in enumerate(ADR_LOG, start=1):
        for c_idx, val in enumerate(r_data):
            st = style_cell_center if c_idx in [0, 1, 7, 8] else style_cell_left
            ws5.write(r_idx, c_idx, str(val), st)
    for c in range(len(headers_adr)):
        ws5.col(c).width = 256 * 16
    ws5.col(2).width = 256 * 35
    ws5.col(3).width = 256 * 40
    ws5.col(5).width = 256 * 45

    # Sheet 6: Testing
    ws6 = wb.add_sheet("Testing_Matrix")
    headers_tc = ["Test ID", "Level", "Module / Name", "Command / Method", "Endpoint", "Criteria", "Expected", "Actual", "Latency", "Status"]
    for c_idx, h in enumerate(headers_tc):
        ws6.write(0, c_idx, h, style_header)
    for r_idx, r_data in enumerate(TEST_CASES, start=1):
        for c_idx, val in enumerate(r_data):
            st = style_cell_center if c_idx in [0, 1, 8, 9] else style_cell_left
            ws6.write(r_idx, c_idx, str(val), st)
    for c in range(len(headers_tc)):
        ws6.col(c).width = 256 * 16
    ws6.col(2).width = 256 * 30
    ws6.col(5).width = 256 * 35
    ws6.col(7).width = 256 * 30

    # Sheet 7: Git Commits
    ws7 = wb.add_sheet("Git_Commits")
    headers_git = ["Commit", "Date", "Author", "Type", "Scope", "Description", "Milestone"]
    for c_idx, h in enumerate(headers_git):
        ws7.write(0, c_idx, h, style_header)
    for r_idx, r_data in enumerate(GIT_AUDIT_LOG, start=1):
        for c_idx, val in enumerate(r_data):
            st = style_cell_center if c_idx in [0, 1, 2, 3, 4, 6] else style_cell_left
            ws7.write(r_idx, c_idx, str(val), st)
    for c in range(len(headers_git)):
        ws7.col(c).width = 256 * 16
    ws7.col(5).width = 256 * 55

    wb.save(filename)
    print(f"✅ Generated native BIFF8 XLS tracker: {filename}")


if __name__ == "__main__":
    xlsx_file = "BioSecure_AI_Project_Tracker_LogBook.xlsx"
    xls_file = "BioSecure_AI_Project_Tracker_LogBook.xls"
    
    print("🚀 Generating Project Log Book & Engineering Tracker...")
    build_modern_xlsx(xlsx_file)
    build_native_xls(xls_file)
    print("✨ Both workbooks generated successfully!")
