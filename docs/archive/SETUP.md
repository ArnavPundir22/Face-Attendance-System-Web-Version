# ⚙️ BioSecure AI Local Setup Guide

This guide covers everything you need to get **BioSecure AI** running locally.

Because facial recognition relies on compiled C++ libraries (ONNX/OpenCV), Linux/macOS is recommended.

## 1. Prerequisites
- **Python 3.10+**
- A **Supabase** account (the free tier is sufficient)

## 2. Clone the Repository

```bash
git clone https://github.com/ArnavPundir22/Face-Attendance-System-Web-Version.git
cd Face-Attendance-System-Web-Version
```

## 3. Create a Virtual Environment

```bash
python3 -m venv .venv
source .venv/bin/activate          # Linux/macOS
# .venv\Scripts\Activate.ps1       # Windows PowerShell
```

## 4. Install Dependencies

```bash
pip install -r requirements.txt
```

## 5. Configure Environment Variables

```bash
cp .env.example .env
```

Open `.env` and fill in your values:

```ini
# Required — Flask
FLASK_SECRET_KEY="your-generated-secret-key"
# Generate with: python3 -c "import secrets; print(secrets.token_hex(32))"

# Required — Supabase (Project Settings → API)
SUPABASE_URL="https://your-project-id.supabase.co"
SUPABASE_SERVICE_ROLE_KEY="your-service-role-key"
SUPABASE_ANON_KEY="your-anon-public-key"

# Optional — Email (leave blank to disable email reports)
EMAIL_USER="your_email@gmail.com"
EMAIL_PASS="your_gmail_app_password"

# Optional — Face Recognition (defaults are production-ready)
INSIGHTFACE_CTX_ID=-1         # -1 = CPU, 0 = GPU
FACE_MATCH_THRESHOLD=0.3
REATTENDANCE_INTERVAL_MINUTES=10
```

> [!WARNING]
> Never commit `.env` to version control. The `SUPABASE_SERVICE_ROLE_KEY` bypasses all Row Level Security — keep it completely secret.

## 6. Database Setup

Execute the SQL in `docs/DATABASE.md` in your Supabase SQL Editor to create tables and the `match_face` function.

## 7. Start the Application

```bash
python3 app.py
```

> [!NOTE]
> **First Run**: InsightFace downloads the `buffalo_l` model (~300MB) to `~/.insightface`. This takes a few minutes.

Access the app at: `http://127.0.0.1:5000`

## 8. Bootstrap First Admin

See `docs/ADMIN_GUIDE.md` → Section 1 for instructions on creating your first admin account via the Supabase SQL Editor.
