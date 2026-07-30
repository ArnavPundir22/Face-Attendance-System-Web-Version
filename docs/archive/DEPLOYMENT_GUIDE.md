# 🚀 Operations & Deployment Guide

This document describes the environment variable configurations, Gunicorn server metrics, Nginx setup, and scaling guidelines.

---

## 1. Environment Configurations (`.env`)

Configure the environment variables by duplicating `.env.example` into a `.env` file in the root workspace:

```ini
FLASK_SECRET_KEY=yoursecretkeyhere
SUPABASE_URL=https://your-project-id.supabase.co
SUPABASE_KEY=your-anon-or-service-role-key-here
LOG_LEVEL=INFO
FACE_MATCH_THRESHOLD=0.3
```

---

## 2. Gunicorn Worker Tuning

InsightFace runtimes run local CPU tensor mathematical calculations (ONNX Runtime). Because of this overhead, synchronous worker configurations must be calibrated to ensure system stability.

Recommended `gunicorn.conf.py` settings for a host with **2 GB RAM**:
```python
bind = "127.0.0.1:8000"
workers = 2          # Prevents memory exhaustion from concurrent models
timeout = 120        # Allows time for processing large class photos
```

---

## 3. Reverse Proxy Configuration (Nginx)

Nginx is placed in front of Gunicorn to manage SSL/TLS certificates, serve static frontend assets directly, and filter payload size thresholds.

Example Server Block (`/etc/nginx/sites-available/biosecure-ai`):
```nginx
server {
    listen 80;
    server_name attendance.example.local;

    # Limit uploads to 20MB for high-resolution class photos
    client_max_body_size 20M;

    # Serve static assets directly (bypasses Gunicorn)
    location /static/ {
        alias /home/dell/Face-Attendance-System-Web-Version/static/;
        expires 7d;
        add_header Cache-Control "public, no-transform";
    }

    # Forward other requests to Gunicorn
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Increase proxy timeouts to match Gunicorn execution duration
        proxy_connect_timeout 120s;
        proxy_read_timeout 120s;
    }
}
```

---

## 4. Production Security Hardening

To ensure the security of data records and ML endpoints:
1. **Enable SSL**: Always terminate connections with Let's Encrypt certificates at the Nginx reverse proxy.
2. **Restrict DB Access**: Use Supabase Row Level Security (RLS) policies to isolate user and administrator tables.
3. **Isolate Python Environments**: Ensure Gunicorn runs under a dedicated, unprivileged system user (`wsgi` or `www-data`), never as root.
