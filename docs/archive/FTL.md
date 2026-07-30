# 📅 Feature Tracking Log (FTL)
# BioSecure AI

**Format**: `[DATE] | [VERSION] | [STATUS] | Description`  
**Status Legend**: ✅ Done · 🔄 In Progress · 📋 Planned · ❌ Cancelled · 🐛 Bug Fix · 🔒 Security

---

## v2.0 — Production Refactor (2026-07-14)

| Date | Status | Feature / Change |
|---|---|---|
| 2026-07-14 | ✅ Done | **App Factory Pattern** — `app.py` refactored to `create_app()` for testability |
| 2026-07-14 | ✅ Done | **Structured Logging** — replaced all `print()` calls with `logging` module |
| 2026-07-14 | ✅ Done | **Global Error Handlers** — 404, 403, 500 with JSON/redirect responses |
| 2026-07-14 | ✅ Done | **Health Check Endpoint** — `GET /healthz` for load balancers and monitoring |
| 2026-07-14 | ✅ Done | **Config Hardening** — email made optional (warn instead of crash) |
| 2026-07-14 | ✅ Done | **SUPABASE_ANON_KEY** — added separate anon/admin client separation |
| 2026-07-14 | ✅ Done | 🔒 **Auth Helpers Rewrite** — removed broken SQLite-era `get_db_connection` import |
| 2026-07-14 | ✅ Done | **Procfile** — PaaS deployment support (Render, Railway, Heroku) |
| 2026-07-14 | ✅ Done | **gunicorn.conf.py** — centralised Gunicorn configuration |
| 2026-07-14 | ✅ Done | **.env.example** — all 15 environment variables documented with descriptions |
| 2026-07-14 | ✅ Done | **11 Documentation Files** — Agents, PRD, FAD, FTL, SAD, TAD, Architecture, Rules, Phases, Design, Memory |
| 2026-07-14 | ✅ Done | **BioSecure AI Branding** — all docs updated to "BioSecure AI" |

---

## v1.5 — Supabase Migration (2026-07-14)

| Date | Status | Feature / Change |
|---|---|---|
| 2026-07-14 | ✅ Done | **Admin Metrics Fix** — switched to `supabase_admin` (service-role) client for RLS bypass |
| 2026-07-14 | ✅ Done | **Mobile Responsive Forms** — grid layout improvements across admin templates |
| 2026-07-14 | ✅ Done | **BioSecure AI UI Update** — documentation reflects new glassmorphic dark design |

---

## v1.4 — Admin Panel Expansion (2026-07-14)

| Date | Status | Feature / Change |
|---|---|---|
| 2026-07-14 | ✅ Done | **User Management Portal** — list, edit, delete users via Supabase Admin API |
| 2026-07-14 | ✅ Done | **Last Admin Guard** — prevent deleting or demoting the last admin account |
| 2026-07-14 | ✅ Done | **Manual Attendance Marking** — admin can mark attendance without face recognition |
| 2026-07-14 | ✅ Done | **7-Day Attendance Trend** — chart on admin dashboard |
| 2026-07-14 | ✅ Done | **Image Viewer** — admin route to view attendance-related images |

---

## v1.3 — pgvector Integration (2026-07-13)

| Date | Status | Feature / Change |
|---|---|---|
| 2026-07-13 | ✅ Done | **pgvector Storage** — migrated face embeddings from `.npy`/`.pkl` to Supabase `vector(512)` |
| 2026-07-13 | ✅ Done | **`match_face` RPC** — PostgreSQL function for cosine similarity matching |
| 2026-07-13 | ✅ Done | **InsightFace buffalo_l** — replaced legacy `face_recognition` library |
| 2026-07-13 | ✅ Done | **L2 Normalisation** — `normalize_embedding()` in `utils/face.py` |
| 2026-07-13 | ✅ Done | **Stateless Architecture** — no more local `.pkl` / `.npy` file dependencies |

---

## v1.2 — Blueprint Architecture (2026-07-12)

| Date | Status | Feature / Change |
|---|---|---|
| 2026-07-12 | ✅ Done | **Flask Blueprints** — monolith split into `auth`, `attendance`, `students`, `admin` |
| 2026-07-12 | ✅ Done | **Supabase Auth** — replaced bcrypt/SQLite user table with Supabase email/password |
| 2026-07-12 | ✅ Done | **Session Management** — JWT stored in Flask session |
| 2026-07-12 | ✅ Done | **`is_admin` via Metadata** — admin flag stored in Supabase user_metadata |

---

## v1.1 — Webcam & Upload UX

| Date | Status | Feature / Change |
|---|---|---|
| — | ✅ Done | **Multi-file Upload** — process multiple group photos in one request |
| — | ✅ Done | **Desktop Webcam** — `getUserMedia` + canvas capture |
| — | ✅ Done | **Mobile Camera Input** — native `<input capture="environment">` |
| — | ✅ Done | **Auto-Capture Mode** — timed interval captures |
| — | ✅ Done | **Re-attendance Cooldown** — configurable duplicate prevention |
| — | ✅ Done | **Annotated Preview** — bounding boxes drawn on returned images |
| — | ✅ Done | **CSV Download** — client-side CSV generation from session data |

---

## v1.0 — Initial Release

| Date | Status | Feature / Change |
|---|---|---|
| — | ✅ Done | Flask web application (single file) |
| — | ✅ Done | `face_recognition` library (dlib backend) |
| — | ✅ Done | SQLite database for users, students, attendance |
| — | ✅ Done | Basic login/logout with bcrypt |
| — | ✅ Done | `.pkl` file storage for face encodings |

---

## Planned Features (Roadmap)

| Priority | Feature | Target Phase |
|---|---|---|
| P1 | 🔄 Email attendance report route (route is missing, config exists) | v2.1 |
| P1 | JWT token refresh (currently requires re-login after 1hr) | v2.1 |
| P1 | Redis-backed rate limiting (multi-worker safe) | v2.1 |
| P2 | Multi-face enrollment per student | v2.2 |
| P2 | Attendance export to Excel (`.xlsx`) | v2.2 |
| P2 | Real-time attendance feed (WebSocket/SSE) | v3.0 |
| P3 | Multi-institution / tenant support | v3.0 |
| P3 | Native mobile apps (React Native / Flutter) | v4.0 |
| P3 | Facial liveness detection (anti-spoofing) | v4.0 |
