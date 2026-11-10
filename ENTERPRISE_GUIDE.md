# BioSecure AI — Enterprise Architecture, Engineering & Operations Guide

> **Official Enterprise Manual for the Face Attendance System**  
> Covers System Architecture, Biometric Pipelines, Cryptographic Deployment Integrity, Concurrency Hardening, and Production Host Operations.

---

## Table of Contents
1. [Executive Overview & Core Stack](#1-executive-overview--core-stack)
2. [Complete Enterprise Directory Blueprint](#2-complete-enterprise-directory-blueprint)
3. [Engineering "What & Where" Operational Map](#3-engineering-what--where-operational-map)
   - [3.1 Environment & API Keys](#31-environment--api-keys)
   - [3.2 Web Blueprints & Business Logic](#32-web-blueprints--business-logic)
   - [3.3 Biometric Engine, Thread-Safe Inference & Vector Cache](#33-biometric-engine-thread-safe-inference--vector-cache)
   - [3.4 Database Layer, Range Pagination & PostgREST Efficiency](#34-database-layer-range-pagination--postgrest-efficiency)
   - [3.5 Host Stability, Terminal QuickEdit Suppression & Reverse Proxy](#35-host-stability-terminal-quickedit-suppression--reverse-proxy)
   - [3.6 Frontend UI, Templates & Progressive Web App](#36-frontend-ui-templates--progressive-web-app)
4. [Cryptographic Host Verification & System Integrity (`src/security/`)](#4-cryptographic-host-verification--system-integrity-srcsecurity)
   - [4.1 Cryptographic Architecture & Signature Verification](#41-cryptographic-architecture--signature-verification)
   - [4.2 Automated Verification Engine & Boot Guard](#42-automated-verification-engine--boot-guard)
   - [4.3 Deployment Certificate Provisioning](#43-deployment-certificate-provisioning)
   - [4.4 Certificate Renewal & Update Lifecycle](#44-certificate-renewal--update-lifecycle)
   - [4.5 Monotonic Clock Drift & Tamper Protection](#45-monotonic-clock-drift--tamper-protection)
5. [Automated Testing & Verification Suite](#5-automated-testing--verification-suite)
6. [Building a Sourceless Production Distribution](#6-building-a-sourceless-production-distribution)
7. [Host Machine Deployment Runbook (Linux / Systemd & Windows)](#7-host-machine-deployment-runbook-linux--systemd--windows)
8. [Security Guardrails & Compliance Standards](#8-security-guardrails--compliance-standards)

---

## 1. Executive Overview & Core Stack

**BioSecure AI** is a production-grade facial biometric attendance and student identity management system engineered for educational and enterprise environments.

### Core Technology Stack
- **Web Framework**: Python 3.10+ Flask with modular Blueprint controllers (`admin`, `attendance`, `students`, `auth`).
- **Database & Vector Store**: Supabase (PostgreSQL with `pgvector` for 512-dimensional ArcFace vector storage and HNSW indexing).
- **Biometric Inference**: InsightFace (`buffalo_l` pipeline: RetinaFace `det_10g` detection and ArcFace `w600k_r50` recognition) with thread-safe `_inference_lock` ONNX Runtime serialization.
- **In-Memory Biometric Cache**: High-throughput NumPy matrix dot-product matcher (`src/utils/face_cache.py`) enabling $< 1\text{ms}$ biometric lookups without database round-trips, hardened with double-checked locking (`_init_lock`) and copy-on-write array updates.
- **Host Stability & Gateway**: Windows console QuickEdit mode suppression via Win32 API (`src/utils/console_helpers.py`), single-backend Nginx gateway resilience (`max_fails=0`), and Gunicorn/Waitress multi-worker execution.
- **Frontend Layer**: Server-rendered Jinja2 templates, Tailwind CSS, Lucide icons, DataTables, and Service Worker PWA support (Fast Stale-While-Revalidate caching).
- **Enterprise Integrity**: Asymmetric Ed25519 digital signature verification, monotonic audit clock drift protection, and sourceless `.pyc` distribution packaging.

---

## 2. Complete Enterprise Directory Blueprint

```
Face-Attendance-System-Web-Version/
├── 📁 src/                             # [CORE APP] Flask application, business logic & UI
│   ├── 📁 blueprints/                 # Modular MVC controllers & API endpoints
│   │   ├── admin.py                   # Administrative dashboard, drift monitoring, bulk academic operations
│   │   ├── attendance.py              # Biometric processing, photo check-in, attendance roster
│   │   ├── students.py                # Student directory, registration, photo uploads & base64 decoding
│   │   └── auth.py                    # Session authentication, login/logout, CSRF SameSite guards
│   ├── 📁 security/                   # Cryptographic verification & public keys
│   │   ├── license_verifier.py        # Offline Ed25519 verifier, boot guard & monotonic clock check
│   │   └── license_public_key.pem     # Application public verification key
│   ├── 📁 utils/                      # Computational engines, caching & data pipelines
│   │   ├── face.py                    # InsightFace 512D ArcFace inference & thread-safe _inference_lock
│   │   ├── face_cache.py              # In-memory NumPy vector matrix, copy-on-write updates & EWMA drift
│   │   ├── db.py                      # Supabase client & chunked fetch_all_records range pagination
│   │   ├── console_helpers.py         # Win32 QuickEdit console mode suppression & host stability
│   │   ├── ocr_helpers.py             # RapidOCR ONNX neural text recognition engine
│   │   └── auth_helpers.py            # Password hashing, rate limiting & session protection
│   ├── 📁 templates/                  # Jinja2 HTML views (viewer, scanner, admin, drift, etc.)
│   ├── 📁 static/                     # Tailwind CSS, Vanilla JS, pwa-nav.js, manifest.json, sw.js
│   ├── __init__.py                    # Flask application factory (create_app)
│   └── config.py                      # Validated environment configurations
│
├── 📁 nginx/                           # [REVERSE PROXY & GATEWAY]
│   ├── nginx.conf                     # Production Nginx reverse proxy configuration template
│   ├── setup_nginx.py                 # Automated cross-platform Nginx generator (max_fails=0)
│   └── mime.types                     # HTTP MIME type definitions
│
├── 📁 deploy/                          # [DEVOPS & SYSTEM INFRASTRUCTURE]
│   └── 📁 systemd/                    # Production system daemon units
│       └── biosecure-attendance.service # Gunicorn auto-restart service unit
│
├── 📁 scripts/                         # [OPERATIONAL TOOLING & AUTOMATION]
│   ├── build_dist.py                  # Sourceless (.pyc) release packaging pipeline
│   ├── 📁 generators/                 # Institutional tracker and document generation engines
│   ├── 📁 tracker_data/               # Modular milestone dataset packages (Phase 1-7)
│   └── 📁 launchers/                  # Platform startup scripts for Linux, Windows, & Tunnels
│
├── 📁 deliverables/                    # [DELIVERABLES & REPORTS]
│   ├── 📁 trackers/                   # Institutional Work Trackers (.xlsx, .xls)
│   ├── 📁 specifications/             # Architecture specifications (.pdf, .docx)
│   ├── 📁 briefs/                     # One-page executive overviews and setup manuals
│   └── 📁 reports/                    # Status reports and representations
│
├── 📁 tests/                           # [QUALITY ASSURANCE & ADVERSARIAL HARNESSES]
│   ├── 📁 unit/                       # Modular unit tests (routes, face cache, verification)
│   ├── test_adversarial_challenger2.py# PostgREST 1000-row & SameSite stress tests
│   └── conftest.py                    # Test session fixtures & isolation shields
│
├── 📁 docs/                            # [DOCUMENTATION & RUNBOOKS]
│   ├── index.md                       # Portal index & sequence diagrams
│   ├── architecture.md                # Multi-tier dual pipeline architecture
│   ├── api_reference.md               # Comprehensive REST API specifications
│   ├── database.md                    # PostgreSQL schema, pgvector & RLS policies
│   ├── deployment.md                  # Production ops, Gunicorn, systemd & Nginx
│   ├── ml_pipeline.md                 # InsightFace, 3D Pose Gate, EWMA math & OCR
│   └── user_guide.md                  # Administrative manual & user workflows
│
├── 📁 known_faces/                     # Student reference biometric photos (gitignored)
├── app.py / wsgi.py                   # Production WSGI application entrypoints
├── gunicorn.conf.py                   # Enterprise Gunicorn configuration
├── .env.example                       # Verified environment template
├── start_face_attendance.bat          # Windows launcher with QuickEdit suppression
├── start_face_attendance.sh           # Linux launcher script
└── .license                           # Active deployment authorization certificate (signed token)
```

---

## 3. Engineering "What & Where" Operational Map

### 3.1 Environment & API Keys
- **File**: `.env` (copy from `.env.example`)
- **Config Loader**: `src/config.py`
- **Key Variables**:
  - `SUPABASE_URL`: Supabase project endpoint.
  - `SUPABASE_SERVICE_ROLE_KEY`: Supabase service role key (required for backend operations).
  - `SUPABASE_ANON_KEY`: Supabase anon key for public client calls.
  - `FLASK_SECRET_KEY`: High-entropy string for session cookie encryption.
  - `PORT`: HTTP port (defaults to `8000`).
  - `WEB_CONCURRENCY`: Gunicorn worker count (defaults to `2`).
  - `EMAIL_USER` / `EMAIL_PASS`: SMTP credentials for automated attendance summaries.

### 3.2 Web Blueprints & Business Logic
All HTTP request handlers and business logic are divided into modular Blueprints under `src/blueprints/`:
- **`attendance.py`**:
  - `upload_photo()`: Photo check-in and automated face matching against the in-memory biometric cache.
  - `get_attendance_data()`: Real-time attendance grid and attendance percentage metrics.
  - `/api/academic_options`: Cascading dropdown filter API (enrollment year, program, branch).
- **`admin.py`**:
  - `admin_view()`: Central management console with scalar `head=True` count queries for zero payload egress.
  - `admin_delete_student()`: Removes student record, deletes reference photo, and purges the embedding from in-memory cache via thread-safe hooks.
  - `admin_drift()`: EWMA biometric drift monitoring across student cohorts.
  - `admin_reset()`: Cohort or full database wipe with synchronized cache clearing.
- **`students.py`**:
  - `students()`: Searchable student table with scalar column projection.
  - `add_student()` / `submit_student()`: Student registration, webcam/upload processing, base64 decoding, and 512D ArcFace embedding generation.
  - `update_student()`: Modal edit handler supporting both integer and string `enrollment_year` payloads with cache updates.
- **`auth.py`**:
  - `login()` / `logout()`: Admin session authentication with CSRF SameSite protection.

### 3.3 Biometric Engine, Thread-Safe Inference & Vector Cache
- **Model Loader & Inference (`src/utils/face.py`)**:
  - Loads InsightFace ONNX models into RAM once at boot.
  - Detects faces with bounding boxes, keypoints, and extracts 512-dimensional normalized ArcFace embeddings.
  - **Inference Concurrency**: Serializes all ONNX Runtime `model.get()` calls under `_inference_lock = threading.Lock()`, preventing CPU core thrashing and thread starvation during concurrent multi-photo attendance requests.
- **In-Memory Biometric Cache (`src/utils/face_cache.py`)**:
  - Maintains `_embeddings_matrix` as a contiguous NumPy array of shape `(N, 512)` and `_student_metadata` holding full roster data in RAM.
  - Performs matrix dot-product multiplication ($Q \cdot M^T$) against all registered faces in $< 1\text{ms}$.
  - **Thread-Safe Architecture**:
    - Decoupled network calls: Supabase fetches occur outside `_cache_lock`.
    - Double-checked locking: Cache initialization utilizes `_init_lock` to eliminate thundering herd contention.
    - Copy-on-Write (CoW): Array updates replace pointers atomically rather than mutating in place, allowing active readers to query snapshots without blocking.
    - Synchronized lifecycle methods: `add_student_to_cache()`, `remove_student_from_cache()`, and `clear_face_cache()`.

### 3.4 Database Layer, Range Pagination & PostgREST Efficiency
- **Database Client & Helpers (`src/utils/db.py`)**:
  - Provides `get_db()` and `get_supabase_client()`.
  - **Range Pagination Helper**: `fetch_all_records(client, table, select_fields, order_field, batch_size=1000)`
    - Automatically paginates queries beyond PostgREST's default 1,000-row limit in 1,000-item ranges.
    - Used by attendance reporting, academic options, and drift dashboards so datasets $> 1,000$ students are never silently truncated.
  - **Egress & Mutation Optimization**:
    - Attendance inserts enforce `returning='minimal'`, eliminating redundant echo payloads over the network.
    - Admin count queries use `count='exact', head=True` to retrieve counts from headers without downloading row bodies.

### 3.5 Host Stability, Terminal QuickEdit Suppression & Reverse Proxy
- **Windows Console Mode Helper (`src/utils/console_helpers.py`)**:
  - Programmatically clears `ENABLE_QUICK_EDIT_MODE` (`0x0040`) using Windows `kernel32` Win32 API functions (`GetStdHandle`, `GetConsoleMode`, `SetConsoleMode`).
  - Executed at boot in `create_app()` and `app.py`, completely preventing Windows Command Prompt stdout freezes when an operator clicks inside the terminal.
- **Nginx Reverse Proxy & Upstream Resilience (`nginx/setup_nginx.py`)**:
  - In single-backend setups, dynamically sets `max_fails=0` for the upstream server.
  - Prevents Nginx from taking the backend server offline during sudden traffic bursts, eliminating false 502 Bad Gateway outages.

### 3.6 Frontend UI, Templates & Progressive Web App
- **Jinja2 Templates (`src/templates/`)**:
  - `viewer.html`: Attendance dashboard and real-time live grid.
  - `scanner.html`: Interactive camera scanner for kiosk attendance check-in.
  - `admin.html`: Master admin portal.
  - `students.html`: Student enrollment and directory view.
  - `base.html`: Common layout, responsive navbar, and PWA integration.
- **PWA Persistent Shell Navigation (`src/static/js/pwa-nav.js` & `sw.js`)**:
  - Service Worker v2 with Fast Stale-While-Revalidate caching, serving cached HTML in $<15\text{ms}$.
  - Persistent App Shell with HTML5 History API view swapping and native View Transitions API animations.
  - Deterministic camera stream teardown (`MediaStreamTrack.stop()`) to eliminate hardware lockups when navigating between tabs.

---

## 4. Cryptographic Host Verification & System Integrity (`src/security/`)

BioSecure AI incorporates an enterprise cryptographic integrity and deployment verification subsystem located in `src/security/`. This subsystem ensures that application instances run within authorized, cryptographically certified host environments with intact configuration parameters.

### 4.1 Cryptographic Architecture & Signature Verification
```
+-------------------------------------------------------------+
|                 Release Staging Environment                 |
|                                                             |
|   Deployment Signing Key (Ed25519)                          |
|              │                                              |
|              ▼                                              |
|   Cryptographic Certificate Generator                       |
|              │                                              |
|              ▼                                              |
|   output/<environment>.license  ──(Deployment)───────┐      |
+------------------------------------------------------│------+
                                                       │
                                                       ▼
+-------------------------------------------------------------+
|                    Target Host Environment                  |
|                                                             |
|   - .license (Signed Deployment Certificate)                |
|   - src/security/license_public_key.pem (Public Verifier)   |
|   - .license_state (Monotonic Audit Clock State)            |
|                                                             |
|                    Application Startup                      |
|                            │                                |
|                            ▼                                |
|            src/security/license_verifier.py                 |
|                            │                                |
|             ┌──────────────┴──────────────┐                 |
|             ▼                             ▼                 |
|       Verified & Current          Unverified or Mismatch    |
|       Application Starts             Clean Exit (1)         |
|   (Mid-flight Auth Guard)         (Integrity Refusal)       |
+-------------------------------------------------------------+
```

### 4.2 Automated Verification Engine & Boot Guard
- **Engine**: `src/security/license_verifier.py`
- **Boot Hook**: During application bootstrapping in `src/__init__.py:create_app()`, `enforce_license_boot()` validates the host's `.license` deployment certificate against `src/security/license_public_key.pem`.
- **Signature Algorithm**: Asymmetric Ed25519 (Edwards-curve Digital Signature Algorithm), providing high-assurance cryptographic verification with minimal CPU overhead.
- **Runtime Metadata**: On successful verification, deployment metadata (authorized institutional environment, valid timeframe, configuration version) is cached in runtime memory for periodic non-blocking checks.

### 4.3 Deployment Certificate Provisioning
A deployment certificate (`.license`) contains signed JSON parameters authorizing the specific environment:
```json
{
  "customer": "COER University",
  "issued_at": 1730650000,
  "expires_at": 1762186000,
  "version": 1
}
```
The signature is appended to the payload using base64 encoding.

### 4.4 Certificate Renewal & Update Lifecycle
When a deployment authorization is updated or extended:
1. An updated signed `.license` certificate is generated for the target environment.
2. The administrator replaces `.license` in the application root directory (`/var/www/biosecure/.license` or deployment root).
3. The running server picks up the new certificate immediately on next validation check—**zero recompilation or code modifications required**.

### 4.5 Monotonic Clock Drift & Tamper Protection
- **Audit Chronology Protection**: Attendance logging and biometric drift monitoring require strict chronological fidelity. Manipulating the host system time could disrupt attendance records and falsify audit events.
- **Monotonic State File**: The application maintains `.license_state` recording monotonic timestamps and high-water marks.
- **Retrograde Detection**: If the host clock is set backwards by more than $300\text{ seconds}$ (5-minute NTP tolerance window), the verifier immediately flags a clock integrity violation to prevent replay anomalies or audit falsification.

---

## 5. Automated Testing & Verification Suite

The repository contains an enterprise testing harness with **86 automated tests**:

```bash
# Run all tests across the entire codebase
.venv/bin/pytest tests/ -v
```

### Test Suite Structure
| Test File | Test Count | Focus Area |
|---|---|---|
| `tests/unit/test_licensing.py` | 12 | Valid deployment tokens, expired tokens, forged signatures, missing public keys, clock rollback, and mid-flight 403 checks. |
| `tests/unit/test_licensing_adversarial.py` | 12 | 150+ fuzzing corpus, boundary clock drift (299s vs 301s), thread-safe concurrency, and monotonic high-water mark retention. |
| `tests/test_adversarial_challenger2.py` | 24 | PostgREST 1,000/2,000 boundary pagination, vector column exclusion, and SameSite cookie invariance. |
| `tests/unit/test_face_cache.py` | 9 | Array normalization, vector dot-product matching, cache updates, single/multi-index removals, and full resets. |
| `tests/unit/test_routes.py` | 12 | Web routes, healthz, offline PWA, 404 handler, SameSite cookies, and admin deletion synchronization. |
| `tests/unit/test_ocr_helpers.py` | 7 | ID card image preprocessing and text parsing. |
| `tests/unit/test_admin_academics.py` | 4 | Academic views, dropdown options, and bulk delete actions. |

---

## 6. Building a Sourceless Production Distribution

To package the application for production hosting environments without exposing plain-text Python source files:

```bash
# Run the sourceless bytecode builder and verification test:
.venv/bin/python scripts/build_dist.py --verify
```

### What this pipeline does:
1. Copies runtime assets (`src/`, `nginx/`, `deploy/`, launchers, templates, static files).
2. Compiles all `.py` files into optimized `.pyc` bytecode using `compileall` with optimization level 1 (`-O1`).
3. **Strips all `.py` source files** from the distribution tree.
4. **Purges all non-runtime files**:
   - Internal keys and signing tools
   - Local `.env` files
   - Test suites and fuzzing harnesses
   - Ephemeral cache state
5. Executes an automated smoke test verifying that `wsgi.py` imports and boots from sourceless `.pyc` files.
6. Packages the output cleanly into the `dist/` directory ready for deployment.

---

## 7. Host Machine Deployment Runbook (Linux / Systemd & Windows)

### Linux VPS / Server Deployment (Gunicorn + Nginx + Systemd)

#### Step 1: Copy Distribution to Host
Copy the compiled `dist/` directory or repository files to the target server directory (e.g. `/opt/biosecure`):
```bash
sudo mkdir -p /opt/biosecure
sudo chown -R $USER:$USER /opt/biosecure
cp -r dist/* /opt/biosecure/
```

#### Step 2: Set Up Python Virtual Environment on Host
```bash
cd /opt/biosecure
python3 -m venv .venv
.venv/bin/pip install --upgrade pip
.venv/bin/pip install -r requirements.txt
```

#### Step 3: Configure Environment Variables
```bash
cp .env.example .env
nano .env
# Set SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY, FLASK_SECRET_KEY, and PORT=8000
```

#### Step 4: Install Deployment Certificate
Place the signed deployment certificate in `/opt/biosecure/.license`:
```bash
cp /path/to/deployment.license /opt/biosecure/.license
```

#### Step 5: Install & Start Systemd Service
```bash
# Copy systemd service unit
sudo cp deploy/systemd/biosecure-attendance.service /etc/systemd/system/

# Reload systemd and start service
sudo systemctl daemon-reload
sudo systemctl enable --now biosecure-attendance

# Check service status
sudo systemctl status biosecure-attendance
```

#### Step 6: View Live Application Logs
```bash
journalctl -u biosecure-attendance -f
```

---

### Windows Host Deployment (Waitress / Batch)

#### Step 1: Configure Python & Dependencies
Ensure Python 3.10+ is installed on the Windows server:
```cmd
python -m venv .venv
.venv\Scripts\activate
pip install --upgrade pip
pip install -r requirements-windows.txt
```

#### Step 2: Configure Environment & Certificate
```cmd
copy .env.example .env
notepad .env
copy \path\to\deployment.license .license
```

#### Step 3: Launch with Console Freeze Protection
Execute the hardened Windows launcher:
```cmd
start_face_attendance.bat
```
> [!NOTE]
> The launcher and application automatically invoke `src/utils/console_helpers.py` to suppress Windows QuickEdit mode, ensuring mouse selections in the terminal window do not pause application execution.

---

## 8. Security Guardrails & Compliance Standards

- **Non-Destructive Integrity Enforcement**:
  - The system enforces platform security and deployment authorization exclusively through non-destructive refusal: clean process termination (`sys.exit(1)`) or HTTP 403 Forbidden.
  - The software contains **zero** self-deleting logic, zero file-wiping scripts, and zero covert backdoors, strictly adhering to computer safety and compliance standards.
- **Public Key Cryptography**:
  - The host application contains only the public verification key (`src/security/license_public_key.pem`). Private signing material is never deployed to host servers.
- **SameSite Session Security & CSRF Defense**:
  - Session cookies enforce `SameSite='Lax'` and `HttpOnly` unconditionally across both HTTP and HTTPS, protecting admin and attendance endpoints against cross-site request forgery (CSRF).
- **Database Row-Level Security (RLS)**:
  - Supabase PostgreSQL tables enforce Row-Level Security policies. Server-side operations authenticate securely using the dedicated service role key, bypassing public exposure.
