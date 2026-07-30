# 🛡️ BioSecure AI — Documentation Hub

Welcome to the **BioSecure AI** technical documentation portal. BioSecure AI is a next-generation, high-performance, stateless facial recognition attendance platform. The system leverages state-of-the-art AI inference locally via ONNX Runtime and offloads high-dimensional vector search to a secure PostgreSQL database powered by Supabase and `pgvector`.

---

## 🗺️ Documentation Directory

Explore the system in-depth through our dedicated sub-documentation modules:

| Document | Purpose | Core Contents |
| :--- | :--- | :--- |
| **[System Architecture](file:///home/dell/Face-Attendance-System-Web-Version/docs/ARCHITECTURE_DETAILS.md)** | Core architecture & logic flowcharts | stateless WSGI model, Gunicorn process scaling, Nginx proxies, sequence flows |
| **[ML & Inference Pipeline](file:///home/dell/Face-Attendance-System-Web-Version/docs/ML_PIPELINE.md)** | Facial recognition logic | InsightFace `buffalo_l`, RetinaFace bounding boxes, ArcFace embeddings, L2 normalisation |
| **[Database & pgvector Engine](file:///home/dell/Face-Attendance-System-Web-Version/docs/DATABASE_SCHEMA.md)** | Persistent layer & Vector search | Table definitions, RLS policies, custom Cosine similarity match_face RPC |
| **[API Reference Manual](file:///home/dell/Face-Attendance-System-Web-Version/docs/API_REFERENCE.md)** | REST API and forms specification | Endpoint schemas, request/response models, and error statuses |
| **[Ops & Deployment Guide](file:///home/dell/Face-Attendance-System-Web-Version/docs/DEPLOYMENT_GUIDE.md)** | Setup & Server configuration | Local setup, environment config, Nginx configuration, Gunicorn tuning |

---

## 🚀 High-Level Architecture Overview

BioSecure AI relies on a modular, stateless design where resource-intensive tasks (image parsing and face encoding) happen on-the-fly, and matching operations are offloaded to Postgres vectors:

```mermaid
graph TD
    Browser[Client Browser] -->|HTTP/HTTPS Request| Nginx[Nginx Reverse Proxy]
    Nginx -->|FastCGI/WSGI Proxy| Gunicorn[Gunicorn Process Manager]
    Gunicorn -->|WSGI Handlers| Flask[Flask Application Factory]

    subgraph Computational Pipeline (Flask Backend)
        Flask --> |1. Image Bytes| Dec[cv2.imdecode]
        Dec --> |2. Detect & Align| Retina[RetinaFace Detector]
        Retina --> |3. Bounding Boxes| Arc[ArcFace Encoder]
        Arc --> |4. 512D Vector| L2[L2 Normalisation]
    end

    subgraph Database Search Engine (Supabase)
        L2 --> |5. Cosine Distance Matching| RPC[match_face RPC]
        RPC --> |6. Similarity Lookup| Db[(PostgreSQL DB)]
    end

    Db --> |7. Match / Similarity score| Flask
    Flask --> |8. Cooldown checks & Insert log| Db
    Flask --> |9. Base64 Annotated Image + JSON| Browser

    style Browser fill:#6366f1,stroke:#fafafa,stroke-width:2px,color:#fff
    style Flask fill:#18181b,stroke:#6366f1,stroke-width:2px,color:#fff
    style Retina fill:#312e81,stroke:#6366f1,stroke-width:1px,color:#fff
    style RPC fill:#064e3b,stroke:#10b981,stroke-width:2px,color:#fff
    style Db fill:#0f172a,stroke:#38bdf8,stroke-width:1px,color:#fff
```

---

## ⚡ Core Technical Highlights

* **Stateless Operations**: The Flask application server is completely stateless. No face templates or user parameters are cached on the server disk. This enables simple horizontal scaling behind a load balancer.
* **Vector Match Performance**: Employs PostgreSQL `pgvector` for indexing and matching embeddings. Cosine similarity queries are executed directly inside database engine memory, delivering match calculations in milliseconds.
* **Double-Match Cooldown Guard**: Prevents recording duplicate attendance records within a configurable interval (default: 10 minutes) for the same lecture/session.
* **Responsive Glassmorphism Styling**: Implements a sleek dark UI utilizing custom CSS and Tailwind classes to optimize visual engagement and clear feedback loops on mobile and desktop devices.
