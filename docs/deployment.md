# 🌍 Production Deployment Guide

This guide details step-by-step instructions on how to configure, tune, and deploy the stateless **BioSecure AI** application in production environments (Linux VPS, containerized Docker environments, or PaaS services).

---

## 🛠️ Environment Variables Configuration Reference

Ensure the following environment variables are specified in your production hosting environment or `.env` file:

```ini
# Flask Configuration
FLASK_SECRET_KEY="your-super-secret-random-32-byte-hex-string"
LOG_LEVEL="INFO"

# Supabase PostgreSQL Configuration
SUPABASE_URL="https://your-project.supabase.co"
SUPABASE_SERVICE_ROLE_KEY="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..." # Bypasses RLS for server operations
SUPABASE_ANON_KEY="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."         # Public client Key

# InsightFace Machine Learning Context
# 0 = GPU Execution (CUDA), -1 = CPU Execution (ONNX Runtime)
INSIGHTFACE_CTX_ID=-1

# Face Vector Matching Thresholds
FACE_MATCH_THRESHOLD=0.40

# Biometric Embedding Drift Engine Constants (2026 Patent Application)
DRIFT_ALPHA=0.30                # EWMA smoothing weight α
DRIFT_POSE_YAW_MAX=25.0         # Max yaw angle threshold (°)
DRIFT_POSE_PITCH_MAX=20.0       # Max pitch angle threshold (°)

# EWMA Alert Level Cutoffs
DRIFT_WARN_THRESHOLD=0.15       # WARNING state cutoff
DRIFT_CRITICAL_THRESHOLD=0.25   # CRITICAL state cutoff (Dispatches SMTP Email)
DRIFT_ALERT_THRESHOLD=0.35      # ALERT state cutoff (Flags student on /admin/drift)

# SMTP Gmail Warning Notification Credentials
EMAIL_USER="admin-alerts@yourdomain.com"
EMAIL_PASS="your-gmail-app-password"

# Local Storage Directory
KNOWN_FACES_DIR="known_faces"
```

---

## 🔑 Supabase Auth Redirect URL Configuration

To ensure OAuth / Magic link / Session callback redirects function seamlessly across production domain names and local ports:

1. Log in to [Supabase Dashboard](https://supabase.com/dashboard) and select your project.
2. Navigate to **Authentication** -> **URL Configuration**.
3. Set **Site URL** to your canonical production URL (e.g. `https://biosecure.yourdomain.com`).
4. Under **Redirect URLs**, click **Add URL** and add:
   - `https://biosecure.yourdomain.com/*`
   - `https://biosecure.yourdomain.com/auth/callback`
   - `http://localhost:5000/*`
   - `http://localhost:5000/auth/callback`
   - `https://*.trycloudflare.com/*` *(if tunneling webcam feeds via Cloudflare)*

---

## 🔒 Database Security & RLS Policy Enforcement

To prevent unauthorized public API access to student 512D ArcFace embeddings and student PII, ensure Row-Level Security (RLS) is executed:

1. Log in to [Supabase Dashboard](https://supabase.com/dashboard) -> open **SQL Editor**.
2. Run the security script located at [`scripts/fix_supabase_security.sql`](file:///home/dell/Face-Attendance-System-Web-Version/scripts/fix_supabase_security.sql).
3. Verify that **Database** -> **Advisors** shows zero `rls_disabled_in_public` security warnings.

---

## 🚀 Production Deployment on Linux VPS (Gunicorn + Nginx + Systemd)

### 1. Install System Dependencies & OpenCV Libraries
Install Python 3.10+, virtual environment tools, and OpenGL system dependencies required by OpenCV and ONNX Runtime:
```bash
sudo apt update
sudo apt install -y python3-pip python3-venv python3-dev libgl1-mesa-glx libglib2.0-0 nginx tesseract-ocr
```

### 2. Set Up Application Directory & Virtual Environment
```bash
sudo mkdir -p /var/www/biosecure
sudo chown -R $USER:$USER /var/www/biosecure
cd /var/www/biosecure

# Clone project and initialize virtualenv
git clone https://github.com/ArnavPundir22/Face-Attendance-System-Web-Version.git .
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

### 3. Configure Systemd Application Daemon
Create a systemd unit file `/etc/systemd/system/biosecure.service`:

```ini
[Unit]
Description=BioSecure AI Flask Application Daemon
After=network.target

[Service]
User=www-data
Group=www-data
WorkingDirectory=/var/www/biosecure
Environment="PATH=/var/www/biosecure/.venv/bin"
ExecStart=/var/www/biosecure/.venv/bin/gunicorn wsgi:app --config gunicorn.conf.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

Enable and launch the daemon:
```bash
sudo systemctl daemon-reload
sudo systemctl enable biosecure
sudo systemctl start biosecure
sudo systemctl status biosecure
```

### 4. Setup Nginx Reverse Proxy
Create Nginx configuration in `/etc/nginx/sites-available/biosecure`:

```nginx
server {
    listen 80;
    server_name biosecure.yourdomain.com;

    # Allocate client body buffer size for high-resolution group photos
    client_max_body_size 25M;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 120s;
        proxy_connect_timeout 120s;
    }

    # Static assets caching
    location /static/ {
        alias /var/www/biosecure/src/static/;
        expires 30d;
        add_header Cache-Control "public, no-transform";
    }

    # Health check endpoint for load balancers
    location /healthz {
        proxy_pass http://127.0.0.1:8000/healthz;
        access_log off;
    }
}
```

Enable the site configuration and restart Nginx:
```bash
sudo ln -s /etc/nginx/sites-available/biosecure /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

---

## 🏥 Health Check Verification

Test application readiness and database connectivity:
```bash
curl -i http://localhost/healthz
```
Expected HTTP output:
```http
HTTP/1.1 200 OK
Content-Type: application/json

{"service":"biosecure-ai-face-attendance","status":"ok"}
```
