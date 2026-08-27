# 🌍 Production Deployment Guide

This guide details instructions on how to configure and deploy the stateless **BioSecure AI** application in production environments (VPS, containerized environments, or PaaS services like Render/Railway).

---

## 🛠️ Environment Variables Configuration

Ensure the following variables are configured in your production hosting panel or `.env` file:

```ini
# Flask Secrets
FLASK_SECRET_KEY="your-super-secret-random-hex"

# Supabase Configurations
SUPABASE_URL="https://your-project.supabase.co"
SUPABASE_SERVICE_ROLE_KEY="eyJhbG..."
SUPABASE_ANON_KEY="eyJhbG..."

# InsightFace Context Settings
# 0 = GPU Execution, -1 = CPU Execution (Default: -1)
INSIGHTFACE_CTX_ID=-1

# Tuneable Parameters
FACE_MATCH_THRESHOLD=0.3
REATTENDANCE_INTERVAL_MINUTES=10
```

---

## 🔒 Database Security & RLS Configuration

To prevent unauthorized public access to student biometric embeddings and PII, ensure Row Level Security (RLS) is enabled on your Supabase project (`avznrudspncnjbqersyg`):

1. Log in to [Supabase Dashboard](https://supabase.com/dashboard).
2. Open your project -> navigate to **SQL Editor**.
3. Copy and execute the security script located at [`scripts/fix_supabase_security.sql`](file:///home/dell/Face-Attendance-System-Web-Version/scripts/fix_supabase_security.sql).
4. Verify that **Advisors** -> **Security** shows zero `rls_disabled_in_public` or `sensitive_columns_exposed` warnings.


---

## 🚀 Deployment on a Linux VPS (Gunicorn + Nginx + Systemd)

### 1. Install System Dependencies
Make sure Python 3.10+, virtual environment libraries, and system dependencies for OpenCV are present:
```bash
sudo apt update
sudo apt install -y python3-pip python3-venv libgl1-mesa-glx libglib2.0-0 nginx
```

### 2. Configure the Systemd Service
Create a systemd service file `/etc/systemd/system/biosecure.service`:

```ini
[Unit]
Description=BioSecure AI Flask Application Daemon
After=network.target

[Service]
User=www-data
WorkingDirectory=/var/www/Face-Attendance-System-Web-Version
ExecStart=/var/www/Face-Attendance-System-Web-Version/.venv/bin/gunicorn wsgi:app --config gunicorn.conf.py
Restart=always

[Install]
WantedBy=multi-user.target
```

Enable and start the daemon:
```bash
sudo systemctl daemon-reload
sudo systemctl enable biosecure
sudo systemctl start biosecure
```

### 3. Setup Nginx Reverse Proxy
Add a virtual server configuration in `/etc/nginx/sites-available/biosecure`:

```nginx
server {
    listen 80;
    server_name yourdomain.com;

    client_max_body_size 20M; # Allocate enough buffer for group photo uploads

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

Link the file and restart Nginx:
```bash
sudo ln -s /etc/nginx/sites-available/biosecure /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```
