# 🏗️ Architecture — BioSecure AI

> **Quick Reference**: Canonical high-level architecture for onboarding and overview.
> For deep technical detail see [TAD.md](./TAD.md) and [SAD.md](./SAD.md).

---

## System Overview

**BioSecure AI** is a stateless web application. Machine learning inference (face detection + embedding) runs locally via ONNX Runtime, while all data persistence and vector similarity search is delegated to Supabase (managed PostgreSQL + pgvector).

```mermaid
graph TD
    Browser(Web Browser) -->|HTTP/HTTPS| Nginx[Nginx\nReverse Proxy]
    Nginx -->|Proxy| Gunicorn[Gunicorn\nWSGI Server]
    Gunicorn -->|WSGI| Flask[Flask Application]

    subgraph Flask Application
        Flask --> auth[auth_bp\n/login /logout /register]
        Flask --> attendance[attendance_bp\n/ /viewer /upload_photo]
        Flask --> students[students_bp\n/students /add_student]
        Flask --> admin[admin_bp\n/admin/*]
    end

    subgraph AI Inference Layer
        attendance -->|image bytes| IFace[InsightFace buffalo_l\nONNX Runtime]
        students -->|photo upload| IFace
        IFace -->|512D float vector| Normalise[L2 Normalise\nnumpy]
    end

    subgraph Supabase Cloud
        Normalise -->|RPC match_face| pgvector{pgvector\nCosine Similarity}
        pgvector --> DB[(PostgreSQL\nstudents\nattendance)]
        auth --> SupabaseAuth[Supabase Auth\nemail/password]
        admin -->|Admin API| SupabaseAuth
    end
```

---

## Student Registration Flow

```mermaid
sequenceDiagram
    participant Admin
    participant Flask
    participant InsightFace
    participant Supabase

    Admin->>Flask: POST /submit_student (form + photo)
    Flask->>Flask: Validate + duplicate check
    Flask->>InsightFace: Extract face embedding
    InsightFace-->>Flask: 512D float32 vector
    Flask->>Flask: L2 normalise
    Flask->>Supabase: INSERT INTO students (name, embedding, ...)
    Supabase-->>Flask: ✓ Success
    Flask-->>Admin: Redirect → success
```

---

## Attendance Marking Flow

```mermaid
sequenceDiagram
    participant Faculty
    participant Flask
    participant InsightFace
    participant Supabase

    Faculty->>Flask: POST /upload_photo (images[], lecture, section)
    
    loop Per uploaded image
        Flask->>InsightFace: Detect faces → embeddings
        
        loop Per detected face
            Flask->>Supabase: RPC match_face(embedding, threshold)
            Supabase-->>Flask: {id, name, similarity} or empty
            
            alt Match found + outside cooldown
                Flask->>Supabase: INSERT attendance record
            end
        end
        
        Flask->>Flask: Annotate image (bounding boxes)
    end
    
    Flask-->>Faculty: JSON {annotated images, results}
```

---

## Modular Blueprint Architecture

| Blueprint | Prefix | Responsibility |
|---|---|---|
| `auth_bp` | (root) | Login, logout, admin-created user registration |
| `attendance_bp` | (root) | Attendance marking, viewer, photo upload API |
| `students_bp` | (root) | Student list, add student form + submission |
| `admin_bp` | `/admin` | Dashboard, user CRUD, student CRUD, manual marking |

---

## The Tech Stack

| Layer | Technology | Why |
|---|---|---|
| **Web Framework** | Flask 3.1 | Python-native; simple integration with ML libraries |
| **AI Inference** | InsightFace `buffalo_l` (ONNX) | State-of-the-art face recognition; CPU/GPU flexible |
| **Vector Search** | Supabase pgvector | Cosine similarity in PostgreSQL; eliminates local state |
| **Database** | Supabase PostgreSQL | Managed; handles Auth, RLS, and REST API |
| **Auth** | Supabase Auth | Email/password with metadata for admin roles |
| **WSGI Server** | Gunicorn | Stable, production-grade Python server |
| **Reverse Proxy** | Nginx | TLS, static files, security headers |
| **Frontend** | TailwindCSS + Vanilla JS | Zero build step; direct CDN integration |
| **Icons** | Lucide | Consistent, lightweight SVG icon set |
| **Fonts** | Geist + Inter (Google Fonts) | Premium, legible typography |

---

## Security Architecture

```
┌─ Public (no auth) ──────────────────────────┐
│  GET  /login                                 │
│  GET  /static/*                              │
│  GET  /healthz                               │
└──────────────────────────────────────────────┘
         │ session['logged_in'] required
         ▼
┌─ Authenticated Zone ────────────────────────┐
│  GET  /  (attendance marking)                │
│  GET  /viewer                                │
│  GET  /students                              │
│  POST /upload_photo                          │
│  POST /submit_student                        │
└──────────────────────────────────────────────┘
         │ session['is_admin'] = True required
         ▼
┌─ Admin Zone ────────────────────────────────┐
│  ALL  /admin/*                               │
│  GET/POST /register                          │
│  (Uses service-role Supabase client)         │
└──────────────────────────────────────────────┘
```
