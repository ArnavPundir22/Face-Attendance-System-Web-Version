# 🏗️ Onyx Face Attendance System Architecture

The **Onyx Face Attendance System** has been entirely rebuilt to be a **stateless** web application. Heavy machine learning inference is handled locally by the Flask application via ONNX Runtime, but the complex mathematical task of matching faces is offloaded entirely to a PostgreSQL database powered by Supabase.

## System Flow
The diagram below illustrates the exact path an image takes from the user's browser, through the AI inference layer, and finally to the database for matching.

```mermaid
graph TD
    Browser(Web Browser / UI) -->|HTTP POST Image| Flask[Flask Backend]
    
    subgraph AI Inference Layer
        Flask -->|Extract Image| IFace[InsightFace buffalo_l]
        IFace -->|Generate 512d array| Embedding([512D Float Embedding])
    end
    
    subgraph Supabase Database
        Embedding -->|RPC call: match_face| pgvector{pgvector <br/>Cosine Similarity}
        pgvector -->|Return match| DB[(PostgreSQL)]
    end
    
    DB -->|Log Attendance| Flask
    Flask -->|JSON Response| Browser
```

## Student Registration Flow
When an administrator registers a new student, the system bypasses local storage and writes the facial signature directly to the database.

```mermaid
sequenceDiagram
    participant Admin
    participant Flask
    participant InsightFace
    participant Supabase

    Admin->>Flask: Submits Student Form + Photo
    Flask->>InsightFace: Pass photo for analysis
    InsightFace-->>Flask: Returns 512D Vector
    Flask->>Supabase: INSERT INTO students (name, embedding)
    Supabase-->>Flask: Success
    Flask-->>Admin: Registration Complete
```

## Modular Code Architecture (Flask Blueprints)

To maintain code readability and clean separation of concerns, the Onyx Face Attendance System's backend is modularized into four distinct Flask Blueprints:

1. **`auth` Blueprint (`blueprints/auth.py`)**: Integrates with Supabase Auth to handle user logins, logouts, registration of new user accounts, and credentials validation.
2. **`attendance` Blueprint (`blueprints/attendance.py`)**: Manages webcam/file uploads, processes uploaded images, calculates embeddings, matches faces via Supabase RPC, and serves the main dashboard.
3. **`students` Blueprint (`blueprints/students.py`)**: Handles showing registered students list and submitting new student data (saving local files to `known_faces/` and writing vectors to Supabase).
4. **`admin` Blueprint (`blueprints/admin.py`)**: Powers the admin area, including real-time user management (list, edit roles, delete accounts), dashboard stats generation, and the capture image viewer.

## The Tech Stack

### 1. Flask (Backend)
Flask handles all routing, session management, and HTML template rendering. We use Flask because it seamlessly integrates with Python's rich data science and machine learning ecosystem.

### 2. InsightFace (AI Inference)
We use the `buffalo_l` model from the InsightFace library. It is widely considered one of the most accurate open-source facial recognition models available. It generates a 512-dimensional array (vector) for every face it detects.

### 3. Supabase `pgvector` (Database)
Supabase provides a powerful managed PostgreSQL database. By enabling the `pgvector` extension, we can store the 512-dimensional arrays directly in our database rows. When we need to recognize a face, we send the new array to Supabase, which uses **Cosine Similarity** (`<=>`) to instantly find the closest matching student.

### 4. TailwindCSS & Vanilla JS (Frontend)
The frontend utilizes a modern "dark glassmorphism" aesthetic built with TailwindCSS. It relies heavily on vanilla JavaScript to interact with the webcam (`navigator.mediaDevices.getUserMedia`) and to submit images to the Flask API.

