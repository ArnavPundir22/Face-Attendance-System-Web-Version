<div align="center">

# 🤖 BioSecure AI

**Automated Facial Recognition Attendance System with Proactive Pose-Gated EWMA Embedding Drift Detection**

[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Flask-3.1-000000?logo=flask&logoColor=white)](https://flask.palletsprojects.com/)
[![InsightFace](https://img.shields.io/badge/InsightFace-Buffalo__L-FF6B35)](https://github.com/deepinsight/insightface)
[![Supabase](https://img.shields.io/badge/Supabase-pgvector-3ECF8E?logo=supabase&logoColor=white)](https://supabase.com/)
[![RapidOCR](https://img.shields.io/badge/RapidOCR-ONNX_DBNet_SVTR-4B8BBE)](https://github.com/RapidAI/RapidOCR)
[![TailwindCSS](https://img.shields.io/badge/TailwindCSS-CDN-38B2AC?logo=tailwind-css&logoColor=white)](https://tailwindcss.com/)
[![Patent Status](https://img.shields.io/badge/Patent_Status-IDF_Filed_2026-1F4E78)](file:///home/dell/Face-Attendance-System-Web-Version/IDF/New%20Patent%20IDF.docx)

</div>

---

## 📖 Project Overview

**BioSecure AI** is a state-of-the-art, production-ready web application designed for educational institutions and organizations. It replaces traditional manual roll calls and paper attendance registers with an automated, contactless AI facial recognition pipeline.

By taking or uploading a single classroom group photo, the system instantly identifies all registered students, marks them **PRESENT** in a PostgreSQL database powered by Supabase `pgvector`, and provides real-time digital attendance records with detailed analytics.

Beyond standard attendance marking, BioSecure AI features a novel, patent-pending **Biometric Embedding Drift Engine (2026 Patent Application)**. This parallel monitoring engine tracks facial template aging over time (beards, hairstyles, weight changes, semester progression) using **3D Pose-Gated EWMA Accumulation**, proactively notifying administrators before biometric recognition degradation or identity verification failure occurs.

---

## 📜 Intellectual Property & Patent Documentation

This repository contains the official 2026 Patent Filing Package for COER University, Roorkee:

* 📄 **[Invention Disclosure Form (IDF)](file:///home/dell/Face-Attendance-System-Web-Version/IDF/New%20Patent%20IDF.docx)**: Official patent disclosure document detailing system architecture, traditional attendance replacement context, pose-gated EWMA drift scoring math, and 300 DPI system flowcharts.
* 📄 **[Patent Prior Art & Novelty Search Report](file:///home/dell/Face-Attendance-System-Web-Version/IDF/Patent_Prior_Art_Search_Report.docx)**: Exhaustive search report covering InPASS, Google Patents, Espacenet, WIPO, USPTO, and IEEE Xplore databases up to August 2026, establishing clear novelty and non-obviousness.

---

## 📚 Documentation Hub Index

Explore our comprehensive, detailed technical sub-documentation guides in the [`docs/`](file:///home/dell/Face-Attendance-System-Web-Version/docs) directory:

| Document | Link | Focus Area |
| :--- | :--- | :--- |
| 📖 **Documentation Portal Index** | [docs/index.md](file:///home/dell/Face-Attendance-System-Web-Version/docs/index.md) | Central documentation index & high-level system sequence flowcharts. |
| 🏗️ **System Architecture Guide** | [docs/architecture.md](file:///home/dell/Face-Attendance-System-Web-Version/docs/architecture.md) | Dual-pipeline architecture, thread-safe memory caching, sequence diagrams. |
| 🗄️ **Database & pgvector Setup** | [docs/database.md](file:///home/dell/Face-Attendance-System-Web-Version/docs/database.md) | PostgreSQL schemas, HNSW vector indexing, RLS security policies, `match_face` RPC. |
| 🧠 **ML & Inference Pipeline** | [docs/ml_pipeline.md](file:///home/dell/Face-Attendance-System-Web-Version/docs/ml_pipeline.md) | InsightFace ArcFace 512D, RetinaFace 5-landmark alignment, 3D Pose Gate, EWMA math ($\alpha=0.30$), RapidOCR ONNX. |
| 🔌 **API Reference Guide** | [docs/api_reference.md](file:///home/dell/Face-Attendance-System-Web-Version/docs/api_reference.md) | REST API endpoints for attendance, student enrollment, OCR scanning, drift dashboard, and `/healthz`. |
| 🌍 **Production Ops & Deployment** | [docs/deployment.md](file:///home/dell/Face-Attendance-System-Web-Version/docs/deployment.md) | Gunicorn WSGI worker tuning, Nginx reverse proxy configuration, systemd daemons, `.env` guide. |
| 👤 **User & Administrator Manual** | [docs/user_guide.md](file:///home/dell/Face-Attendance-System-Web-Version/docs/user_guide.md) | Step-by-step user guide for student registration, OCR ID card scanning, group attendance, and drift resets. |

---

## ✨ Key Features & Innovation Matrix

| Feature Category | Capability | Technical Implementation |
|---|---|---|
| **Attendance Automation** | 📷 **Multi-Source Photo Ingestion** | Processes classroom group photos and live webcam streams, identifying multiple student faces in parallel. |
| **Biometric AI** | 🧠 **InsightFace ArcFace 512D** | Extracts high-precision 512-dimensional normalized hyperspherical face embeddings using ONNX Runtime. |
| **Ultra-Fast Matching** | ⚡ **In-Memory BLAS Matrix Vector Matcher** | Performs batch matrix dot-product operations ($Q \cdot M^T$) in $<1\text{ ms}$ on CPU, bypassing network roundtrips. |
| **Persistent Search** | 🚀 **Supabase pgvector Integration** | Native PostgreSQL vector Cosine similarity RPC queries (`match_face` at `FACE_MATCH_THRESHOLD = 0.40`). |
| **Patent Novelty #1** | 🛡️ **3D Pose Gate Noise Validator** | Rejects uncooperative head angles ($|\text{Yaw}| \le 25^\circ, |\text{Pitch}| \le 20^\circ$) to eliminate group-photo noise (`POSE_REJECTED`). |
| **Patent Novelty #2** | 📈 **EWMA Drift Accumulator** | Exponentially Weighted Moving Average ($\alpha = 0.30$) tracking template aging ($D_t = 1.0 - S$). |
| **Patent Novelty #3** | 🚨 **Multi-Tier Alert Machine** | Classifies biometric health (`HEALTHY` $<0.15$, `WARNING` $\ge 0.15$, `CRITICAL` $\ge 0.25$, `ALERT` $\ge 0.35$). |
| **Smart Automation** | 📧 **SMTP Email Dispatcher** | Dispatches real-time Gmail warning emails to administrators upon `CRITICAL` or `ALERT` drift escalation. |
| **ID Card Scanner** | 💳 **RapidOCR Neural ID Card Reader** | Pretrained RapidOCR (DBNet + SVTR ONNX) and PyTesseract scanner (`/api/ocr_id_card`) for student enrollment. |
| **Class Modes** | 🏫 **Separate vs Combined Roster Modes** | Supports single-class roster boundary enforcement and joint multi-branch combined lectures. |
| **Admin Controls** | 👨‍💼 **Biometric Drift Management Portal** | Dedicated `/admin/drift` dashboard featuring single-click re-enrollment template reset functionality. |
| **Security** | 🛡️ **Row-Level Security & RBAC** | Supabase Row-Level Security (RLS) policies protecting biometric vectors and student PII with proxy fix middleware. |

---

## 🏗️ System Architecture Overview

```mermaid
graph TD
    Browser[Client Browser / Mobile App] -->|1. Classroom Photo Upload / OCR Request| Nginx[Nginx Reverse Proxy]
    Nginx -->|Proxy Headers / WSGI| Gunicorn[Gunicorn WSGI Process Manager]
    Gunicorn -->|Flask Application Factory| App[BioSecure AI App Instance]

    subgraph "Part A: Facial Recognition & Fast In-Memory Matching"
        App --> |2. Decode Image| Dec[cv2.imdecode]
        Dec --> |3. Detect & Align| Retina[RetinaFace 5-Landmark Detector]
        Retina --> |4. ArcFace Embeddings| Arc[ArcFace 512D Normalizer]
        Arc --> |5. In-Memory Matrix Match <1ms| Matrix[NumPy BLAS Matrix Engine]
        Matrix -->|Cache Hit| MatchRes[Match Found S >= 0.40]
        Matrix -->|Cache Miss| RPC[Supabase pgvector match_face RPC]
        RPC --> MatchRes
        MatchRes --> |6. Write Attendance| AttLog[(Supabase attendance Table)]
    end

    subgraph "Part B: Novel Pose-Gated EWMA Drift Engine (2026 Patent)"
        Arc --> |7. 3D Euler Angles| PoseGate{3D Pose Gate<br/>|Yaw|<=25° & |Pitch|<=20°}
        PoseGate -->|No: Rejected| PoseReject[Log POSE_REJECTED<br/>EWMA Unchanged]
        PoseGate -->|Yes: Accepted| DriftCalc[Calculate Drift D = 1.0 - S]
        DriftCalc --> |8. EWMA Update| EWMA[EWMA_t = 0.30*D + 0.70*EWMA_old]
        EWMA --> |9. Health Evaluator| AlertEval{Alert Level Evaluator}
        AlertEval -->|EWMA >= 0.25| SMTP[Dispatch Admin SMTP Email]
        AlertEval -->|EWMA >= 0.35| AdminDash[Flag on /admin/drift Dashboard]
    end

    style Browser fill:#6366f1,stroke:#fafafa,stroke-width:2px,color:#fff
    style App fill:#18181b,stroke:#6366f1,stroke-width:2px,color:#fff
    style Matrix fill:#064e3b,stroke:#10b981,stroke-width:2px,color:#fff
    style PoseGate fill:#d97706,stroke:#f59e0b,stroke-width:2px,color:#fff
    style SMTP fill:#991b1b,stroke:#ef4444,stroke-width:2px,color:#fff
```

---

## ⚙️ Configuration Constants (`src/config.py` / `.env`)

```ini
# Flask Secret Key
FLASK_SECRET_KEY="your-super-secret-hex-key"

# Supabase Credentials
SUPABASE_URL="https://your-project.supabase.co"
SUPABASE_SERVICE_ROLE_KEY="your-supabase-service-role-key"
SUPABASE_ANON_KEY="your-supabase-anon-key"

# Face Matching Threshold (Cosine Similarity: 0.0 - 1.0)
FACE_MATCH_THRESHOLD=0.40

# Embedding Drift Engine Constants (2026 Patent Application)
DRIFT_ALPHA=0.30                # EWMA smoothing factor α
DRIFT_POSE_YAW_MAX=25.0         # Max yaw angle cutoff (°)
DRIFT_POSE_PITCH_MAX=20.0       # Max pitch angle cutoff (°)

# EWMA Alert Level Thresholds
DRIFT_WARN_THRESHOLD=0.15       # WARNING state cutoff
DRIFT_CRITICAL_THRESHOLD=0.25   # CRITICAL state cutoff (Triggers SMTP Email)
DRIFT_ALERT_THRESHOLD=0.35      # ALERT state cutoff (Triggers Re-Enrollment Flag)

# SMTP Gmail Alert Configuration
EMAIL_USER="your-admin-email@gmail.com"
EMAIL_PASS="your-gmail-app-password"
```

---

## 💻 Quick Start & Running Locally

1. **Clone Repository & Setup Environment:**
   ```bash
   git clone https://github.com/ArnavPundir22/Face-Attendance-System-Web-Version.git
   cd Face-Attendance-System-Web-Version

   # On Linux / macOS:
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt

   # On Windows (Command Prompt / PowerShell):
   python -m venv .venv
   .venv\Scripts\activate
   pip install -r requirements-windows.txt
   ```

2. **Configure Environment Variables:**
   ```bash
   cp .env.example .env
   # Edit .env and supply your Supabase and SMTP credentials
   ```

3. **Launch Development Server:**
   ```bash
   python app.py
   ```
   Open your browser at `http://localhost:5000` (or configured port).

4. **Verify System Health:**
   ```bash
   curl http://localhost:5000/healthz
   # Expected output: {"service":"biosecure-ai-face-attendance","status":"ok"}
   ```

---

## 🤝 Citation & Attribution

If you utilize BioSecure AI or the Pose-Gated EWMA Embedding Drift Engine in your research or institutional deployments, please reference:

```bibtex
@patent{biosecure_ai_2026,
  title={Automated Facial Recognition Attendance System with Pose-Gated EWMA Biometric Embedding Drift Engine},
  author={Pundir, Arnav and COER University Patent Team},
  year={2026},
  holder={COER University, Roorkee},
  note={Invention Disclosure Form (IDF) Filed}
}
```
