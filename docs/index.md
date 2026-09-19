# 🛡️ BioSecure AI — Technical Documentation Hub

Welcome to the official technical documentation portal for **BioSecure AI**, developed at **COER University, Roorkee**. 

BioSecure AI is a production-ready, high-performance automated facial recognition classroom attendance system designed to replace manual roll calls and physical attendance registers. It incorporates a novel **Pose-Gated EWMA Embedding Drift Engine (2026 Patent Application)** to solve biometric template aging.

---

## 🗺️ Documentation Directory

Explore the system through our dedicated sub-documentation modules:

| Document | Description | Core Contents |
| :--- | :--- | :--- |
| 🏗️ **[System Architecture](architecture.md)** | Dual-pipeline architecture | In-memory BLAS matrix matching, `pgvector` RPC fallback, 3D Pose Gate, EWMA Drift Engine, Sequence Flowcharts |
| 🗄️ **[Database & pgvector](database.md)** | Storage layer & vector similarity | Supabase PostgreSQL schemas (`students`, `attendance`, `embedding_health`, `academic_structure`), HNSW index, RLS policies |
| 🧠 **[ML & Inference Pipeline](ml_pipeline.md)** | Facial recognition & neural OCR | InsightFace ArcFace 512D embeddings, RetinaFace alignment, 3D Euler angles, EWMA math ($\alpha=0.30$), RapidOCR ONNX pipeline |
| 🔌 **[API Reference](api_reference.md)** | REST endpoints manual | Attendance logging, Neural ID Card OCR, student registration, `/admin/drift` APIs, status codes, `/healthz` |
| 🌍 **[Ops & Deployment](deployment.md)** | Production setup & guidelines | Gunicorn WSGI worker tuning, Nginx reverse proxy, systemd daemons, RLS security scripts, `.env` config |
| 👤 **[User & Admin Guide](user_guide.md)** | How to use the app | Registering students, Neural OCR ID scanning, classroom photo uploads, SMTP alerts, single-click drift resets |

---

## 📜 Intellectual Property & Patent Documentation

* 📄 **[Invention Disclosure Form (IDF)](file:///home/dell/Face-Attendance-System-Web-Version/IDF/New%20Patent%20IDF.docx)**: Official patent disclosure document detailing system architecture, traditional attendance replacement context, pose-gated EWMA drift scoring math, and 300 DPI system flowchart.
* 📄 **[Patent Prior Art & Novelty Search Report](file:///home/dell/Face-Attendance-System-Web-Version/IDF/Patent_Prior_Art_Search_Report.docx)**: Exhaustive search report covering InPASS, Google Patents, Espacenet, WIPO, USPTO, and IEEE Xplore databases up to August 2026.

---

## 🚀 High-Level Dual-Pipeline Architecture Overview

BioSecure AI relies on a clean dual-pipeline architecture where attendance marking, neural ID card OCR processing, and biometric template health monitoring execute seamlessly:

```mermaid
graph TD
    Browser[Client Browser / Instructor App] -->|1. Classroom Photo / OCR ID Upload| Nginx[Nginx Reverse Proxy]
    Nginx -->|WSGI Proxy| Gunicorn[Gunicorn Process Manager]
    Gunicorn -->|Flask Routing| App[BioSecure AI App Core]

    subgraph "Part A: Primary Attendance Pipeline"
        App --> |2. Decode Image| Dec[cv2.imdecode]
        Dec --> |3. Detect & Align| Retina[RetinaFace 5-Landmark Detector]
        Retina --> |4. 512D Embedding| Arc[ArcFace 512D Encoder]
        Arc --> |5. Fast BLAS Match <1ms| Cache[In-Memory NumPy Matrix Cache]
        Cache -->|Hit| Match[Match Found S >= 0.40]
        Cache -->|Miss| RPC[match_face RPC pgvector]
        RPC --> Match
        Match --> |6. Mark Attendance| RecLog[Mark Student PRESENT]
    end

    subgraph "Part B: Novel Embedding Drift Engine (Patent #3)"
        Arc --> |7. 3D Euler Angles| PoseGate{3D Pose Gate<br/>|Yaw|<=25° AND |Pitch|<=20°}
        PoseGate -->|No: Rejected| PoseReject[Log POSE_REJECTED<br/>EWMA Unchanged]
        PoseGate -->|Yes: Accepted| DriftCalc[Calculate Drift D = 1.0 - S]
        DriftCalc --> |8. EWMA Accumulator| EWMA[EWMA_t = 0.30*D + 0.70*EWMA_old]
        EWMA --> |9. State Evaluator| AlertEval{Alert Level Evaluator}
        AlertEval -->|EWMA >= 0.25| SMTP[Dispatch Gmail SMTP Alert]
        AlertEval -->|EWMA >= 0.35| AdminDash[Flag on /admin/drift Dashboard]
    end

    style Browser fill:#6366f1,stroke:#fafafa,stroke-width:2px,color:#fff
    style App fill:#18181b,stroke:#6366f1,stroke-width:2px,color:#fff
    style Cache fill:#064e3b,stroke:#10b981,stroke-width:2px,color:#fff
    style PoseGate fill:#d97706,stroke:#f59e0b,stroke-width:2px,color:#fff
    style SMTP fill:#991b1b,stroke:#ef4444,stroke-width:2px,color:#fff
```

---

## ⚡ Core Technical Highlights

- **Stateless App Architecture**: The Flask application holds no state across HTTP requests. Student reference embeddings are cached in a thread-safe NumPy contiguous matrix for sub-millisecond BLAS vector calculations.
- **Dual Matching Strategy**: Combines in-memory NumPy matrix dot-product operations ($Q \cdot M^T$) with fallback Supabase PostgreSQL `pgvector` Cosine distance RPC functions (`match_face`).
- **3D Pose-Gated Noise Suppression**: Filters out uncooperative head angles ($|\text{Yaw}| \le 25^\circ, |\text{Pitch}| \le 20^\circ$) to eliminate group-photo head-tilt noise from polluting drift scores.
- **Exponentially Weighted Moving Average (EWMA)**: Smooths single-session lighting noise ($\alpha = 0.30$) to isolate genuine facial appearance aging (beards, weight changes, haircuts).
- **Pretrained Neural RapidOCR ID Reader**: Integrates RapidOCR (DBNet + SVTR ONNX) and PyTesseract for instant student enrollment auto-filling from physical ID cards.
- **Single-Click Template Reset**: Allows administrators to refresh outdated student embeddings with a single click upon re-enrollment.
