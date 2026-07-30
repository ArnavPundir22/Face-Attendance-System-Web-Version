<div align="center">

<h1>🤖 BioSecure AI</h1>
<p><strong>Automated, stateless classroom attendance powered by InsightFace AI and Supabase <code>pgvector</code></strong></p>

[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Flask-3.1-000000?logo=flask&logoColor=white)](https://flask.palletsprojects.com/)
[![InsightFace](https://img.shields.io/badge/InsightFace-Buffalo__L-FF6B35)](https://github.com/deepinsight/insightface)
[![Supabase](https://img.shields.io/badge/Supabase-pgvector-3ECF8E?logo=supabase&logoColor=white)](https://supabase.com/)
[![TailwindCSS](https://img.shields.io/badge/TailwindCSS-CDN-38B2AC?logo=tailwind-css&logoColor=white)](https://tailwindcss.com/)
[![License](https://img.shields.io/badge/License-MIT-green)](LICENSE)

</div>

---

## 📖 What Is This?

**BioSecure AI** is a modern, state-of-the-art web application that completely eliminates manual roll-calls using advanced facial recognition. A teacher uploads a classroom photo (or captures one with a webcam), and the system instantly identifies every student in the image, marking them present in a secure PostgreSQL database.

Built for the modern web, this application is **100% stateless**. By leveraging **Supabase `pgvector`**, facial embeddings are stored and queried directly inside the database, meaning the application can be hosted anywhere (Vercel, Render, VPS) without worrying about ephemeral file systems wiping out your AI data.

---

## 📚 Documentation Index

To keep this repository clean and easy to navigate, we have split our documentation into focused, in-depth guides. Please select the guide you need from the list below:

*   **[📖 Documentation Hub](docs/index.md)**: The central portal/table of contents with component flowcharts.
*   **[🏗️ Architecture Guide](docs/architecture.md)**: Deep dive into the stateless system flow, modular layouts, and execution sequence diagrams.
*   **[🗄️ Database Setup](docs/database.md)**: SQL schemas, RLS security configurations, and custom cosine matching RPC functions.
*   **[🧠 ML & Inference Pipeline](docs/ml_pipeline.md)**: InsightFace model specs, RetinaFace alignment, and ArcFace vector mathematics.
*   **[🔌 API Reference](docs/api_reference.md)**: Comprehensive manual for authentication, students, and attendance REST endpoints.
*   **[🌍 Production Deployment & Setup](docs/deployment.md)**: Local configurations, environment vars, Gunicorn tuning, and systemd/Nginx configurations.
*   **[👨‍💼 User & Admin Guide](docs/user_guide.md)**: Operational manual for student registrations, attendance logging, and exporting reports.

---

## ✨ Features at a Glance

| Feature | Description |
|---|---|
| 🔍 **AI Face Recognition** | High-accuracy embeddings generated via the `InsightFace buffalo_l` model. |
| 🚀 **Stateless Architecture** | Embeddings are stored natively in Supabase using `pgvector`. No local `.npy` or `.pkl` files! |
| 📷 **Auto-Capture Webcam** | Captures and analyzes 5 webcam photos automatically to ensure everyone is caught. |
| 👥 **Group Photo Support** | Detects and identifies multiple faces in a single photograph simultaneously. |
| 🛡️ **Re-attendance Cooldown** | Blocks duplicate marks within a configurable time window (e.g., 10 minutes) per student. |
| 📊 **Real-time Dashboard** | Filterable attendance table with an instant **CSV Download** feature for reporting. |
| 👨‍💼 **Admin & User Control** | Full user management interface to list, edit roles (`is_admin`), delete accounts, or reset passwords. |
| 📈 **Live Trend Metrics** | Visual 7-day attendance trend widgets and status counts queried dynamically from the database. |
| 🖼️ **Image Capture Inspector** | Dedicated view page to inspect processed and bounding-box annotated attendance photos. |
| 🎨 **Premium BioSecure AI UI/UX** | Stunning dark glassmorphism aesthetic built with TailwindCSS, custom canvas particles, and Lucide Icons. |
| 🔐 **Secure Supabase Auth** | Fully integrated user authentication backed by Supabase Auth and role-based route protection. |
| 🧩 **Modular Blueprint Layout** | Refactored into clean Python Flask blueprints (`auth`, `attendance`, `students`, `admin`) for maximum maintainability. |

---
