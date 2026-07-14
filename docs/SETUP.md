# ⚙️ BioSecure AI Local Setup Guide

This guide covers everything you need to know to get **BioSecure AI** running locally on your machine for development or testing.

Because the facial recognition relies on compiled C++ libraries (ONNX/OpenCV), a standard Linux/macOS environment is highly recommended.

## 1. Prerequisites
- **Python 3.10+**
- A **Supabase** account (The free tier is perfectly fine).

## 2. Clone the Repository
Open your terminal and clone the repository:

```bash
git clone https://github.com/ArnavPundir22/Face-Attendance-System-Web-Version.git
cd Face-Attendance-System-Web-Version
```

## 3. Create a Virtual Environment
It is highly recommended to isolate your dependencies using a Python virtual environment.

```bash
# Create the virtual environment
python3 -m venv .venv

# Activate it (Linux/macOS)
source .venv/bin/activate

# Activate it (Windows PowerShell)
# .venv\Scripts\Activate.ps1
```

## 4. Install Dependencies
Install all the required Python packages (Flask, InsightFace, OpenCV, etc.).

```bash
pip install -r requirements.txt
```

## 5. Configure Environment Variables
The application relies heavily on environment variables to connect to Supabase and configure application properties.

1. Copy the example configuration file:
   ```bash
   cp .env.example .env
   ```
2. Open the `.env` file in your code editor.
3. Generate a secure random string for your `FLASK_SECRET_KEY`:
   ```bash
   python3 -c "import secrets; print(secrets.token_hex(32))"
   ```
4. Replace the placeholder values with your actual credentials:

```ini
# Flask Secret Key
FLASK_SECRET_KEY="your-generated-secret-key"

# Supabase Credentials (found in Project Settings > API)
SUPABASE_URL="https://your-project.supabase.co"
SUPABASE_SERVICE_ROLE_KEY="your-service-role-key"

# Email Configuration (SMTP)
EMAIL_USER="your_email_address@gmail.com"
EMAIL_PASS="your_app_password"

# Face Recognition Settings (optional, default values provided)
INSIGHTFACE_CTX_ID=-1                  # -1 for CPU, 0 for first GPU
FACE_MATCH_THRESHOLD=0.3               # Cosine similarity threshold (0.3 is optimal)
REATTENDANCE_INTERVAL_MINUTES=10       # Cooldown period between consecutive logs for a student
```

> [!WARNING]  
> Never commit your `.env` file to version control. Keep your `SUPABASE_SERVICE_ROLE_KEY` completely secret, as it bypasses Row Level Security!

## 6. Run the Database Setup
Before starting the application, ensure you have set up your Supabase tables. Follow the instructions in [DATABASE.md](./DATABASE.md) to execute the necessary SQL script.

## 7. Start the Application
Start the Flask development server:

```bash
python3 app.py
```

> [!NOTE]  
> **First Run Only**: The application will automatically download the `InsightFace buffalo_l` AI models (~300MB) to your local `~/.insightface` directory. This may take a few minutes depending on your internet connection.

Once the models are loaded, the application will be accessible in your web browser at:
`http://127.0.0.1:5000`

