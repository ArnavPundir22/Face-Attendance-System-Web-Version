# BioSecure AI — Enterprise Architecture, Developer & Operations Guide

> **Official Enterprise Manual for the Face Attendance System**  
> Covers System Architecture, Developer Operations, Biometric Pipelines, Cryptographic Licensing, and Host Deployment.

---

## Table of Contents
1. [Executive Overview & Core Stack](#1-executive-overview--core-stack)
2. [Complete Enterprise Directory Blueprint](#2-complete-enterprise-directory-blueprint)
3. [Developer "What & Where" Operational Map](#3-developer-what--where-operational-map)
   - [3.1 Environment & API Keys](#31-environment--api-keys)
   - [3.2 Web Blueprints & Business Logic](#32-web-blueprints--business-logic)
   - [3.3 Biometric Engine & In-Memory Vector Cache](#33-biometric-engine--in-memory-vector-cache)
   - [3.4 Database Layer & PostgREST Pagination](#34-database-layer--postgrest-pagination)
   - [3.5 Frontend UI, Templates & Styling](#35-frontend-ui-templates--styling)
4. [Standalone Developer Licensing Kit (`license_kit/`)](#4-standalone-developer-licensing-kit-license_kit)
   - [4.1 Security Architecture & Key Isolation](#41-security-architecture--key-isolation)
   - [4.2 Interactive Terminal Console UI](#42-interactive-terminal-console-ui)
   - [4.3 Issuing a Client License](#43-issuing-a-client-license)
   - [4.4 Client Renewal Workflow](#44-client-renewal-workflow)
   - [4.5 Anti-Rollback Clock Protection](#45-anti-rollback-clock-protection)
5. [Automated Testing & Verification Suite](#5-automated-testing--verification-suite)
6. [Building a Sourceless Production Distribution](#6-building-a-sourceless-production-distribution)
7. [Host Machine Deployment Runbook (Linux / Systemd)](#7-host-machine-deployment-runbook-linux--systemd)
8. [Security Guardrails & Legal Standards](#8-security-guardrails--legal-standards)

---

## 1. Executive Overview & Core Stack

**BioSecure AI** is a production-grade facial biometric attendance and student identity management system engineered for educational and enterprise environments.

### Core Technology Stack
- **Web Framework**: Python 3.10+ Flask with modular Blueprint controllers (`admin`, `attendance`, `students`, `auth`).
- **Database & Vector Store**: Supabase (PostgreSQL with `pgvector` for 512-dimensional ArcFace vector storage).
- **Biometric Inference**: InsightFace (`buffalo_l` pipeline: `det_10g` detection and `w600k_r50` recognition).
- **In-Memory Biometric Cache**: High-throughput NumPy matrix dot-product matcher (`src/utils/face_cache.py`) enabling $< 1\text{ms}$ biometric lookups without database round-trips.
- **Frontend Layer**: Server-rendered Jinja2 templates, Tailwind CSS, Lucide icons, DataTables, and Service Worker PWA support.
- **Licensing & Protection**: Asymmetric Ed25519 digital signatures, monotonic anti-rollback clock tracking, and sourceless `.pyc` bytecode packaging.

---

## 2. Complete Enterprise Directory Blueprint

```
Face-Attendance-System-Web-Version/
├── 📁 src/                             # [CORE APP] Flask application, business logic & UI
│   ├── 📁 blueprints/                 # Modular MVC controllers & API endpoints
│   │   ├── admin.py                   # Administrative dashboard, drift monitoring, bulk academic operations
│   │   ├── attendance.py              # Biometric processing, photo check-in, attendance roster
│   │   ├── students.py                # Student directory, registration, photo uploads
│   │   └── auth.py                    # Session authentication, login/logout
│   ├── 📁 security/                   # Hardened verification & public keys
│   │   ├── license_verifier.py        # Offline Ed25519 verifier, boot guard & anti-rollback
│   │   └── license_public_key.pem     # Application public key (Bundled with app)
│   ├── 📁 utils/                      # Computational engines and data pipelines
│   │   ├── face.py                    # InsightFace 512D ArcFace inference pipeline
│   │   ├── face_cache.py              # In-memory NumPy vector matrix & EWMA drift tracker
│   │   ├── db.py                      # Supabase client & chunked PostgREST queries
│   │   ├── ocr.py                     # OCR ID card text extraction engine
│   │   └── email_service.py           # Automated email reporting
│   ├── 📁 templates/                  # Jinja2 HTML views (viewer, scanner, admin, etc.)
│   ├── 📁 static/                     # Tailwind CSS, Vanilla JS, PWA assets
│   ├── __init__.py                    # Flask application factory (create_app)
│   └── config.py                      # Validated environment configurations
│
├── 📁 license_kit/                     # [DEVELOPER ONLY - KEEP OFF HOST MACHINE]
│   ├── developer_private_key.pem      # PRIVATE KEY (chmod 600, NEVER deploy/share)
│   ├── license_public_key.pem         # Local public key copy
│   ├── license_console.py             # Standalone interactive TUI application
│   ├── run_console.sh                 # Linux/macOS kit launcher
│   ├── run_console.bat                # Windows kit launcher
│   ├── requirements.txt               # Minimal dependencies (cryptography>=3.4.0)
│   ├── README.md                      # Kit operator guide & workflow
│   └── 📁 output/                     # Generated customer .license files
│
├── 📁 deploy/                          # [DEVOPS & SYSTEM INFRASTRUCTURE]
│   └── 📁 systemd/                    # Production system daemon units
│       └── biosecure-attendance.service # Gunicorn auto-restart service unit
│
├── 📁 nginx/                           # [REVERSE PROXY & GATEWAY]
│   ├── nginx.conf                     # Production Nginx reverse proxy configuration
│   └── mime.types                     # HTTP MIME type definitions
│
├── 📁 scripts/                         # [OPERATIONAL TOOLING & AUTOMATION]
│   ├── build_dist.py                  # Sourceless (.pyc) distribution packager
│   ├── 📁 devtools/                   # Developer CLI tools (license_tool.py)
│   └── 📁 launchers/                  # Platform startup scripts
│
├── 📁 tests/                           # [QUALITY ASSURANCE & ADVERSARIAL HARNESSES]
│   ├── 📁 unit/                       # Modular unit tests (routes, face cache, licensing)
│   ├── test_adversarial_challenger2.py# PostgREST 1000-row & SameSite stress tests
│   └── conftest.py                    # Test session fixtures & isolation shields
│
├── 📁 docs/                            # [DOCUMENTATION & RUNBOOKS]
├── 📁 known_faces/                     # Student reference biometric photos (gitignored)
├── app.py / wsgi.py                   # Production WSGI application entrypoints
├── gunicorn.conf.py                   # Enterprise Gunicorn configuration
├── .env.example                       # Verified environment template
├── license_console.sh / .bat          # Root developer console launcher shortcuts
└── .license                           # Active host license token (when deployed)
```

---

## 3. Developer "What & Where" Operational Map

### 3.1 Environment & API Keys
- **File**: `.env` (copy from `.env.example`)
- **Config Loader**: `src/config.py`
- **Key Variables**:
  - `SUPABASE_URL`: Supabase project endpoint.
  - `SUPABASE_KEY`: Supabase service role key (required for backend operations).
  - `FLASK_SECRET_KEY`: High-entropy string for session cookie encryption.
  - `PORT`: HTTP port (defaults to `8000`).
  - `WEB_CONCURRENCY`: Gunicorn worker count (defaults to `2`).
  - `EMAIL_USER` / `EMAIL_PASS`: SMTP credentials for automated attendance summaries.

### 3.2 Web Blueprints & Business Logic
All HTTP request handlers and business logic are divided into modular Blueprints under `src/blueprints/`:
- **`attendance.py`**:
  - `upload_photo()`: Photo check-in and automated face matching against the biometric cache.
  - `get_attendance_data()`: Real-time attendance grid and attendance percentage metrics.
  - `/api/academic_options`: Cascading dropdown filter API (enrollment year, program, branch).
- **`admin.py`**:
  - `admin_view()`: Central management console.
  - `admin_delete_student()`: Removes student record, deletes reference photo, and purges the embedding from in-memory cache.
  - `admin_drift()`: EWMA biometric drift monitoring across student cohorts.
  - `admin_reset()`: Cohort or full database wipe with synchronized cache clearing.
- **`students.py`**:
  - `students()`: Searchable student table.
  - `add_student()`: Student registration, webcam/upload processing, and 512D ArcFace embedding generation.
  - `update_student()`: Modal edit handler updating metadata in both Supabase and memory cache.
- **`auth.py`**:
  - `login()` / `logout()`: Admin session authentication with CSRF SameSite protection.

### 3.3 Biometric Engine & In-Memory Vector Cache
- **Model Loader & Inference (`src/utils/face.py`)**:
  - Loads InsightFace ONNX models into RAM once at boot.
  - Detects faces with bounding boxes, keypoints, and extracts 512-dimensional normalized ArcFace embeddings.
  - Provides `compute_similarity(emb1, emb2)` using cosine distance.
- **In-Memory Biometric Cache (`src/utils/face_cache.py`)**:
  - Maintains `_embeddings_matrix` as a NumPy array of shape `(N, 512)`.
  - Performs matrix dot-product multiplication against all registered faces in $< 1\text{ms}$.
  - Synchronized via `_cache_lock` with public thread-safe primitives:
    - `add_student_to_cache(student_id, embedding, metadata)`
    - `update_student_metadata_cache(student_id, metadata)`
    - `remove_student_from_cache(student_id)`
    - `clear_face_cache()`

### 3.4 Database Layer & PostgREST Pagination
- **Database Client & Helpers (`src/utils/db.py`)**:
  - Provides `get_db()` and `get_supabase_client()`.
  - **Crucial Helper**: `fetch_all_records(client, table, select_fields, order_field, batch_size=1000)`
    - Automatically paginates queries beyond PostgREST's default 1,000-row limit in 1,000-item ranges.
    - Used by attendance reporting, academic options, and drift dashboards so datasets $> 1,000$ students are never silently truncated.

### 3.5 Frontend UI, Templates & Styling
- **Jinja2 Templates (`src/templates/`)**:
  - `viewer.html`: Attendance dashboard and real-time live grid.
  - `scanner.html`: Interactive camera scanner for kiosk attendance check-in.
  - `admin.html`: Master admin portal.
  - `students.html`: Student enrollment and directory view.
  - `base.html`: Common layout, responsive navbar, and PWA integration.
- **Static Assets (`src/static/`)**:
  - Tailwind CSS stylesheets, client-side camera/webcam drivers, PWA service worker (`sw.js`), and web manifest (`manifest.json`).

---

## 4. Standalone Developer Licensing Kit (`license_kit/`)

The licensing system allows developers to protect their intellectual property and enforce contractual evaluation/milestone periods when deploying to client or host machines.

### 4.1 Security Architecture & Key Isolation
```
+-------------------------------------------------------------+
|                 Developer Workstation / USB                 |
|                                                             |
|   license_kit/developer_private_key.pem  [SECRET - CHMOD 600|
|              │                            NEVER COMMIT]     |
|              ▼                                              |
|   ./license_kit/run_console.sh                              |
|     └─ Option [1]: Issue License Token                      |
|              │                                              |
|              ▼                                              |
|   license_kit/output/<client>.license  ──(Transfer)───┐     |
+-------------------------------------------------------│-----+
                                                        │
                                                        ▼
+-------------------------------------------------------------+
|                    Client Host Machine                      |
|                                                             |
|   - .license (Signed Token)                                 |
|   - src/security/license_public_key.pem (Public Verifier)   |
|   - .license_state (Monotonic Anti-Rollback Tracker)        |
|                                                             |
|                    Application Startup                      |
|                            │                                |
|                            ▼                                |
|            src/security/license_verifier.py                 |
|                            │                                |
|             ┌──────────────┴──────────────┐                 |
|             ▼                             ▼                 |
|       Valid & Current             Expired or Forged         |
|       Application Starts             sys.exit(1)            |
|   (Mid-flight HTTP 403 on)        (Hard Boot Failure)       |
+-------------------------------------------------------------+
```

### 4.2 Interactive Terminal Console UI
Launch the console from the project root or inside `license_kit/`:
```bash
# Linux / macOS:
./license_kit/run_console.sh

# Windows:
license_kit\run_console.bat
```

```
╔══════════════════════════════════════════════════════════════════════╗
║          BIOSECURE AI — DEVELOPER LICENSING CONSOLE (STANDALONE)   ║
║          Developer Licensing & Cryptographic Access Control          ║
╚══════════════════════════════════════════════════════════════════════╝

 KIT ENVIRONMENT STATUS
 ├─ Private Key (Secret) : READY (Confidential 0o600) (developer_private_key.pem)
 ├─ Public Key (Verifier): READY (license_public_key.pem)
 ├─ Issued Licenses Saved: 1 files in license_kit/output/
 └─ Application Linkage  : DETECTED (Synced with Face-Attendance App)
────────────────────────────────────────────────────────────────────────

AVAILABLE ACTIONS:
  [1] Issue Client License Token        (Interactive Wizard)
  [2] Inspect / Verify License File     (Signature & Expiry Check)
  [3] Generate / Rotate Keypair         (Ed25519 Private & Public Keys)
  [4] Security & Deployment Guide       (Architecture & Best Practices)
  [5] System Diagnostics               (Inspect Keys & Tokens)
  [0] Exit
```

### 4.3 Issuing a Client License
1. Launch `./license_kit/run_console.sh` and choose **Option [1]**.
2. Enter the **Client/Organization Name** (e.g. `National University`).
3. Select a duration preset:
   - `[1]` 7 Days (Demo / Evaluation)
   - `[2]` 14 Days (Standard Pilot)
   - `[3]` 30 Days (Monthly Lease / Milestone Delivery)
   - `[4]` 90 Days (Quarterly)
   - `[5]` 365 Days (Annual)
   - `[6]` Custom Days
   - `[7]` Specific Date (`YYYY-MM-DD`)
4. Output is generated at `license_kit/output/<client>.license`.
5. Send **ONLY** that `.license` file to the client.

### 4.4 Client Renewal Workflow
When a client renews or pays a project milestone:
1. Open the console on your workstation: `./license_kit/run_console.sh`.
2. Select **[1]**, enter the client's name, and choose the extended duration.
3. Send the new `.license` file to the client.
4. The client replaces `.license` in their project root—**no server recompilation or code change required**.

### 4.5 Anti-Rollback Clock Protection
- The host application maintains `.license_state` recording monotonic timestamps.
- If a host administrator sets the system clock backwards by $> 300\text{ seconds}$ (5-minute NTP tolerance), anti-rollback immediately invalidates the license and terminates execution (`sys.exit(1)`).
- High-water mark retention guarantees that repeated small backward clock adjustments cannot be used to cheat license expiration.

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
| `tests/unit/test_licensing.py` | 12 | Valid tokens, expired tokens, forged signatures, missing keys, clock rollback, and mid-flight 403 checks. |
| `tests/unit/test_licensing_adversarial.py` | 12 | 150+ fuzzing corpus, boundary clock drift (299s vs 301s), thread-safe concurrency, and monotonic high-water mark retention. |
| `tests/test_adversarial_challenger2.py` | 24 | PostgREST 1,000/2,000 boundary pagination, vector column exclusion, and SameSite cookie invariance. |
| `tests/unit/test_face_cache.py` | 9 | Array normalization, vector dot-product matching, cache updates, single/multi-index removals, and full resets. |
| `tests/unit/test_routes.py` | 12 | Web routes, healthz, offline PWA, 404 handler, SameSite cookies, and admin deletion synchronization. |
| `tests/unit/test_ocr_helpers.py` | 7 | ID card image preprocessing and text parsing. |
| `tests/unit/test_admin_academics.py` | 4 | Unauthorized redirects, academic views, and bulk delete actions. |

---

## 6. Building a Sourceless Production Distribution

To deliver the software to a host machine without plain-text Python files that can be easily modified:

```bash
# Run the sourceless bytecode builder and verification test:
.venv/bin/python scripts/build_dist.py --verify
```

### What this pipeline does:
1. Copies runtime assets (`src/`, `nginx/`, `deploy/`, launchers, templates, static files).
2. Compiles all `.py` files into optimized `.pyc` bytecode using `compileall` with optimization level 1.
3. **Strips all `.py` source files** from the distribution.
4. **Purges all sensitive developer files**:
   - `developer_private_key.pem`
   - `license_kit/`
   - `.env`
   - `tests/`
   - `.license_state`
5. Executes an automated smoke test verifying that `wsgi.py` imports and boots from sourceless `.pyc` files.
6. Packages the output cleanly into the `dist/` directory.

---

## 7. Host Machine Deployment Runbook (Linux / Systemd)

Follow these steps to deploy on a client's Linux server:

### Step 1: Copy Distribution to Host
Copy the compiled `dist/` folder to the target server directory (e.g. `/opt/biosecure`).

### Step 2: Set Up Python Virtual Environment on Host
```bash
cd /opt/biosecure
python3 -m venv .venv
.venv/bin/pip install --upgrade pip
.venv/bin/pip install -r requirements.txt
```

### Step 3: Configure Environment Variables
```bash
cp .env.example .env
nano .env
# Set SUPABASE_URL, SUPABASE_KEY, FLASK_SECRET_KEY, and PORT=8000
```

### Step 4: Install the Client License
Place the customer's signed license file in `/opt/biosecure/.license`:
```bash
cp /path/to/customer.license /opt/biosecure/.license
```

### Step 5: Install & Start Systemd Service
```bash
# Copy systemd service unit
sudo cp deploy/systemd/biosecure-attendance.service /etc/systemd/system/

# Reload systemd and start service
sudo systemctl daemon-reload
sudo systemctl enable --now biosecure-attendance

# Check service status
sudo systemctl status biosecure-attendance
```

### Step 6: View Live Application Logs
```bash
journalctl -u biosecure-attendance -f
```

---

## 8. Security Guardrails & Legal Standards

- **Zero Destructive Code**:
  - The software enforces licensing strictly through non-destructive refusal: **Hard Boot Failure (`sys.exit(1)`)** and **HTTP 403 Forbidden**.
  - It contains **zero** self-deleting logic bombs, zero file-wiping scripts, and zero covert backdoors, strictly adhering to computer crime and software safety statutes.
- **Private Key Confidentiality**:
  - `developer_private_key.pem` is strictly ignored by version control (`.gitignore`) and excluded from all distribution builds.
  - File permissions are enforced at `0o600` (read/write by owner only).
- **SameSite Session Security**:
  - Session cookies enforce `SameSite='Lax'` unconditionally across both HTTP and HTTPS, protecting admin and attendance endpoints against cross-site request forgery (CSRF).
