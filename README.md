<div align="center">

# 🤖 BioSecure AI

**Automated Facial Recognition Attendance System with Proactive Pose-Gated EWMA Embedding Drift Detection**

[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Flask-3.1-000000?logo=flask&logoColor=white)](https://flask.palletsprojects.com/)
[![InsightFace](https://img.shields.io/badge/InsightFace-Buffalo__L-FF6B35)](https://github.com/deepinsight/insightface)
[![Supabase](https://img.shields.io/badge/Supabase-pgvector-3ECF8E?logo=supabase&logoColor=white)](https://supabase.com/)
[![TailwindCSS](https://img.shields.io/badge/TailwindCSS-CDN-38B2AC?logo=tailwind-css&logoColor=white)](https://tailwindcss.com/)
[![Patent Status](https://img.shields.io/badge/Patent_Status-IDF_Filed_2026-1F4E78)](file:///home/dell/Face-Attendance-System-Web-Version/IDF/New%20Patent%20IDF.docx)

</div>

---

## 📖 Project Overview

**BioSecure AI** is a state-of-the-art, production-ready web application designed to replace traditional manual paper registers and verbal roll calls in educational institutions with an automated, contactless AI facial recognition pipeline. 

By taking or uploading a single classroom group photo, the system instantly identifies all registered students, marks them **PRESENT** in a PostgreSQL database powered by Supabase `pgvector`, and provides real-time digital attendance records.

Beyond standard attendance marking, BioSecure AI includes a novel, patent-pending **Biometric Embedding Drift Engine (2026 Patent Application)**. This parallel engine monitors facial template aging over time (beards, hairstyles, weight changes) using **3D Pose-Gated EWMA Accumulation**, proactively notifying administrators before biometric recognition failure occurs.

---

## 📜 Intellectual Property & Patent Documentation

This repository contains the official 2026 Patent Filing Package for COER University, Roorkee:

* 📄 **[Invention Disclosure Form (IDF)](file:///home/dell/Face-Attendance-System-Web-Version/IDF/New%20Patent%20IDF.docx)**: Official patent disclosure document detailing system architecture, traditional attendance replacement context, pose-gated EWMA drift scoring math, and 300 DPI system flowchart.
* 📄 **[Patent Prior Art & Novelty Search Report](file:///home/dell/Face-Attendance-System-Web-Version/IDF/Patent_Prior_Art_Search_Report.docx)**: Exhaustive search report covering InPASS, Google Patents, Espacenet, WIPO, USPTO, and IEEE Xplore databases up to August 2026, establishing clear novelty and non-obviousness.

---

## 📚 Documentation Hub Index

Explore our comprehensive, detailed sub-documentation guides in the [`docs/`](file:///home/dell/Face-Attendance-System-Web-Version/docs) directory:

* 📖 **[Documentation Hub Index](file:///home/dell/Face-Attendance-System-Web-Version/docs/index.md)**: Central portal and component sequence flowcharts.
* 🏗️ **[System Architecture Guide](file:///home/dell/Face-Attendance-System-Web-Version/docs/architecture.md)**: Dual-pipeline architecture (Attendance Pipeline + Pose-Gated EWMA Drift Engine).
* 🗄️ **[Database & pgvector Setup](file:///home/dell/Face-Attendance-System-Web-Version/docs/database.md)**: PostgreSQL schemas, Supabase `pgvector` indexing, and drift tracking tables.
* 🧠 **[ML & Inference Pipeline](file:///home/dell/Face-Attendance-System-Web-Version/docs/ml_pipeline.md)**: InsightFace `buffalo_l` ArcFace embeddings, RetinaFace landmark alignment, 3D Pose Gate, and EWMA mathematics.
* 🔌 **[API Reference Guide](file:///home/dell/Face-Attendance-System-Web-Version/docs/api_reference.md)**: REST endpoints for attendance logging, student management, and drift dashboard APIs.
* 🌍 **[Production Ops & Deployment](file:///home/dell/Face-Attendance-System-Web-Version/docs/deployment.md)**: Gunicorn WSGI tuning, Nginx reverse proxy, systemd services, and `.env` setup.
* 👨‍💼 **[User & Administrator Guide](file:///home/dell/Face-Attendance-System-Web-Version/docs/user_guide.md)**: Manual for student registrations, attendance uploads, SMTP alerts, and single-click drift resets.

---

## ✨ Features at a Glance

| Category | Feature | Technical Description |
|---|---|---|
| **Attendance Automation** | 📷 **Classroom Photo Ingestion** | Detects and identifies multiple student faces from classroom group photos or camera frames. |
| **Biometric AI** | 🧠 **InsightFace ArcFace 512D** | Extracts high-precision 512-dimensional normalized hyperspherical face embeddings. |
| **Stateless Database** | 🚀 **Supabase pgvector** | Vector indexing and cosine distance queries executed natively in PostgreSQL (`match_face` RPC). |
| **Patent Novelty** | 🛡️ **3D Pose Gate Validator** | Filters out uncooperative head angles ($|\text{Yaw}| \le 25^\circ, |\text{Pitch}| \le 20^\circ$) to eliminate group-photo noise. |
| **Patent Novelty** | 📈 **EWMA Drift Accumulator** | Exponentially Weighted Moving Average ($\alpha = 0.30$) tracking facial template aging ($D_t = 1 - S$). |
| **Patent Novelty** | 🚨 **Multi-Tier Alert Machine** | Classifies template health (`HEALTHY` $<0.15$, `WARNING` $\ge 0.15$, `CRITICAL` $\ge 0.25$, `ALERT` $\ge 0.35$). |
| **Automation** | 📧 **SMTP Email Dispatcher** | Dispatches real-time Gmail warning emails to administrators upon `CRITICAL` state escalation. |
| **Management** | 👨‍💼 **Admin Drift Dashboard** | `/admin/drift` management portal featuring single-click re-enrollment template reset functionality. |
| **Security** | 🛡️ **Re-attendance Cooldown** | Blocks accidental duplicate marks within a configurable window (default: 10 mins per lecture). |
| **UI/UX** | 🎨 **Dark Glassmorphic UI** | Premium dark-mode interface built with TailwindCSS, Lucide icons, and interactive canvas particles. |

---

## ⚙️ Key System Configuration Constants (`src/config.py` / `.env`)

```ini
# Face Matching Threshold (Cosine Similarity: 0.0 - 1.0)
FACE_MATCH_THRESHOLD=0.40

# Embedding Drift Detection (Patent Idea #3)
DRIFT_ALPHA=0.30                # EWMA smoothing factor α
DRIFT_POSE_YAW_MAX=25.0         # Max yaw angle limit (°)
DRIFT_POSE_PITCH_MAX=20.0       # Max pitch angle limit (°)

# EWMA Alert Thresholds
DRIFT_WARN_THRESHOLD=0.15       # WARNING state cutoff
DRIFT_CRITICAL_THRESHOLD=0.25   # CRITICAL state cutoff (Triggers SMTP Email)
DRIFT_ALERT_THRESHOLD=0.35      # ALERT state cutoff (Triggers Re-Enroll Prompt)
```

---

## 💻 Quick Start & Running Locally

1. **Clone & Install Dependencies:**
   ```bash
   git clone https://github.com/ArnavPundir22/Face-Attendance-System-Web-Version.git
   cd Face-Attendance-System-Web-Version
   python3 -m venv .venv && source .venv/bin/activate
   pip install -r requirements.txt
   ```

2. **Set Up Environment Variables:**
   ```bash
   cp .env.example .env
   # Edit .env with your Supabase credentials
   ```

3. **Run Dev Server:**
   ```bash
   python app.py
   ```
   Access the web app at `http://localhost:5000`.

