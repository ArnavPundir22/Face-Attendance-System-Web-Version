# 🌍 BioSecure AI Production Deployment

**BioSecure AI** is entirely **stateless** — face embeddings live in Supabase, not on disk. This means you can deploy anywhere that supports Python without worrying about persistent volumes.

## 1. Hardware Requirements

- **Minimum RAM**: 2 GB (InsightFace requires ~1 GB to load)
- **Recommended RAM**: 4 GB (for 2 workers + headroom)
- **CPU**: 1 vCPU minimum; 2+ recommended for photo processing throughput
- **GPU**: Optional — set `INSIGHTFACE_CTX_ID=0` and use `onnxruntime-gpu`

---

## 2. Option A — Virtual Private Server (VPS)

Best for: DigitalOcean, AWS EC2, Hetzner, Linode, Google Cloud VM.

### Steps

```bash
# 1. Provision Ubuntu 22.04+ server
# 2. Clone repository
git clone https://github.com/ArnavPundir22/Face-Attendance-System-Web-Version.git
cd Face-Attendance-System-Web-Version

# 3. Create virtual environment
python3 -m venv .venv && source .venv/bin/activate

# 4. Install dependencies
pip install -r requirements.txt

# 5. Set up environment variables
cp .env.example .env
# Edit .env with your Supabase and Flask credentials

# 6. Start with Gunicorn
gunicorn app:app --config gunicorn.conf.py
```

### Nginx Reverse Proxy

An example Nginx configuration is at `nginx/nginx.conf`. Copy it to `/etc/nginx/sites-available/`:

```bash
sudo cp nginx/nginx.conf /etc/nginx/sites-available/biosecure-ai-attendance
sudo ln -s /etc/nginx/sites-available/biosecure-ai-attendance /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx
```

### HTTPS with Let's Encrypt

```bash
sudo certbot --nginx -d your.domain.com
```

### Systemd Service (Auto-restart)

Create `/etc/systemd/system/biosecure-ai-attendance.service`:

```ini
[Unit]
Description=BioSecure AI Face Attendance System
After=network.target

[Service]
User=www-data
WorkingDirectory=/var/www/biosecure-ai-attendance
EnvironmentFile=/var/www/biosecure-ai-attendance/.env
ExecStart=/var/www/biosecure-ai-attendance/.venv/bin/gunicorn app:app --config gunicorn.conf.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable biosecure-ai-attendance
sudo systemctl start biosecure-ai-attendance
```

---

## 3. Option B — Platform as a Service (PaaS)

Best for: zero-ops deployments. The `Procfile` handles the startup command.

### Render.com

1. Connect your GitHub repository to Render
2. Create a new **Web Service**
3. Set **Environment**: Python 3
4. **Build Command**: `pip install -r requirements.txt`
5. **Start Command** is read automatically from `Procfile`:
   ```
   gunicorn app:app --config gunicorn.conf.py
   ```
6. Add all variables from `.env.example` to Render's **Environment Variables** panel
7. Set **Instance Type** to at least **Standard** (1 GB RAM minimum)

> [!CAUTION]
> Render **Free tier** has only 512 MB RAM. InsightFace requires ~1 GB minimum. Use at least the **Starter** paid plan.

### Railway

1. Connect your GitHub repository
2. Railway auto-detects Python and runs the `Procfile`
3. Add environment variables in the Railway dashboard
4. Railway auto-assigns `$PORT` — `gunicorn.conf.py` reads it automatically

### Fly.io

```bash
fly launch
fly secrets import < .env
fly deploy
```

---

## 4. Environment Variables Checklist

Before deploying, ensure these are set in your platform's environment:

| Variable | Where to Find |
|---|---|
| `FLASK_SECRET_KEY` | Generate: `python -c "import secrets; print(secrets.token_hex(32))"` |
| `SUPABASE_URL` | Supabase Dashboard → Project Settings → API |
| `SUPABASE_SERVICE_ROLE_KEY` | Supabase Dashboard → Project Settings → API |
| `SUPABASE_ANON_KEY` | Supabase Dashboard → Project Settings → API |
| `EMAIL_USER` | Your Gmail address (optional) |
| `EMAIL_PASS` | Gmail App Password (optional) |

---

## 5. Health Check

After deployment, verify the application is running:

```bash
curl https://your.domain.com/healthz
# Expected: {"status": "ok", "service": "biosecure-ai-face-attendance"}
```

Configure your platform to use `/healthz` as the health check endpoint.

> [!WARNING]
> If you deploy to a **Serverless** platform (Vercel, AWS Lambda), the InsightFace model cannot be loaded — it requires a persistent container process. Use a dedicated container platform (Render, Railway, Fly.io, VPS).
