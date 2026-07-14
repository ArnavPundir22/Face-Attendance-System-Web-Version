# ⚙️ Local Setup Guide

This guide covers everything you need to know to get the Face Attendance System running locally on your machine for development or testing.

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
The application relies heavily on environment variables to connect to Supabase.

1. Copy the example configuration file:
   ```bash
   cp .env.example .env
   ```
2. Open the `.env` file in your code editor.
3. Replace the placeholder values with your actual Supabase credentials. You can find these in your Supabase Project Dashboard under **Project Settings > API**.

```ini
# Found under "Project URL"
SUPABASE_URL="https://your-project.supabase.co"

# Found under "Project API Keys" -> "anon public"
SUPABASE_KEY="your-anon-public-key"

# Found under "Project API Keys" -> "service_role"
SUPABASE_SERVICE_ROLE_KEY="your-service-role-key"
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
