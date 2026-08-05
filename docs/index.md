# 🛡️ BioSecure AI — Technical Documentation Hub

Welcome to the official technical documentation portal for **BioSecure AI**, developed at **COER University, Roorkee**. 

BioSecure AI is a production-ready, stateless, high-performance automated facial recognition classroom attendance system designed to replace traditional paper registers. It incorporates a novel **Pose-Gated EWMA Embedding Drift Engine (2026 Patent Application)** to solve biometric template aging.

---

## 🗺️ Documentation Directory

Explore the system through our dedicated sub-documentation modules:

| Document | Description | Core Contents |
| :--- | :--- | :--- |
| 🏗️ **[System Architecture](architecture.md)** | Dual-pipeline architecture | Attendance Pipeline, 3D Pose Gate, EWMA Drift Engine, Sequence Flowcharts |
| 🗄️ **[Database & pgvector](database.md)** | Storage layer & vector similarity | Supabase PostgreSQL schemas, `match_face` RPC, `students` & `drift_logs` tables |
| 🧠 **[ML & Inference Pipeline](ml_pipeline.md)** | Facial recognition & drift logic | InsightFace ArcFace 512D embeddings, RetinaFace alignment, 3D Euler angles, EWMA math ($\alpha=0.30$) |
| 🔌 **[API Reference](api_reference.md)** | REST endpoints manual | Attendance logging, student registration, `/admin/drift` APIs, status codes |
| 🌍 **[Ops & Deployment](deployment.md)** | Production setup & guidelines | Gunicorn tuning, Nginx reverse proxy, systemd services, `.env` config |
| 👤 **[User & Admin Guide](user_guide.md)** | How to use the app | Registering students, classroom photo uploads, SMTP alerts, single-click drift resets |

---

## 📜 Intellectual Property & Patent Documentation

* 📄 **[Invention Disclosure Form (IDF)](file:///home/dell/Face-Attendance-System-Web-Version/IDF/New%20Patent%20IDF.docx)**: Official patent disclosure document detailing system architecture, traditional attendance replacement context, pose-gated EWMA drift scoring math, and 300 DPI system flowchart.
* 📄 **[Patent Prior Art & Novelty Search Report](file:///home/dell/Face-Attendance-System-Web-Version/IDF/Patent_Prior_Art_Search_Report.docx)**: Exhaustive search report covering InPASS, Google Patents, Espacenet, WIPO, USPTO, and IEEE Xplore databases up to August 2026.

---

## 🚀 High-Level Dual-Pipeline Architecture Overview

BioSecure AI relies on a clean dual-pipeline architecture where attendance marking and biometric template health monitoring execute in parallel:

```mermaid
graph TD
    Browser[Client Browser / Instructor App] -->|1. Classroom Photo Upload| Nginx[Nginx Reverse Proxy]
    Nginx -->|WSGI Proxy| Gunicorn[Gunicorn Process Manager]
    Gunicorn -->|Flask Routing| AttendanceBP[Attendance Blueprint]

    subgraph "Part A: Primary Attendance Pipeline"
        AttendanceBP --> |2. Decode Image| Dec[cv2.imdecode]
        Dec --> |3. Detect & Align| Retina[RetinaFace Detector]
        Retina --> |4. 512D Embedding| Arc[ArcFace Encoder]
        Arc --> |5. Vector Search S >= 0.40| RPC[match_face RPC]
        RPC --> |6. Similarity Match| Db[(Supabase Postgres + pgvector)]
        Db --> |7. Mark Attendance| RecLog[Mark Student PRESENT]
    end

    subgraph "Part B: Novel Embedding Drift Engine (Patent #3)"
        Arc --> |8. 3D Euler Angles| PoseGate{3D Pose Gate<br/>|Yaw|<=25° AND |Pitch|<=20°}
        PoseGate -->|No: Rejected| PoseReject[Log POSE_REJECTED<br/>EWMA Unchanged]
        PoseGate -->|Yes: Accepted| DriftCalc[Calculate Drift D = 1.0 - S]
        DriftCalc --> |9. EWMA Accumulator| EWMA[EWMA_t = 0.30*D + 0.70*EWMA_old]
        EWMA --> |10. State Evaluator| AlertEval{Alert Evaluator}
        AlertEval -->|EWMA >= 0.25| SMTP[Dispatch Gmail SMTP Alert]
        AlertEval -->|EWMA >= 0.35| AdminDash[Flag on /admin/drift Dashboard]
    end

    style Browser fill:#6366f1,stroke:#fafafa,stroke-width:2px,color:#fff
    style AttendanceBP fill:#18181b,stroke:#6366f1,stroke-width:2px,color:#fff
    style RPC fill:#064e3b,stroke:#10b981,stroke-width:2px,color:#fff
    style PoseGate fill:#d97706,stroke:#f59e0b,stroke-width:2px,color:#fff
    style SMTP fill:#991b1b,stroke:#ef4444,stroke-width:2px,color:#fff
```

---

## ⚡ Core Technical Highlights

- **Stateless App Architecture**: The Flask application holds no state. No face templates are cached on server disks, allowing effortless horizontal scaling.
- **pgvector Integration**: Employs PostgreSQL's `pgvector` extension. Cosine similarity queries are calculated directly in-database in milliseconds (`FACE_MATCH_THRESHOLD = 0.40`).
- **3D Pose-Gated Noise Suppression**: Filters out uncooperative head angles ($|\text{Yaw}| \le 25^\circ, |\text{Pitch}| \le 20^\circ$) to eliminate group-photo artifacts.
- **Exponentially Weighted Moving Average (EWMA)**: Smooths single-session lighting noise ($\alpha = 0.30$) to isolate genuine facial appearance aging.
- **Single-Click Template Reset**: Allows administrators to refresh outdated student embeddings with a single click upon re-enrollment.
