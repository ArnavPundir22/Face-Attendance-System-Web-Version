# 🧠 Memory — BioSecure AI
# AI Context & Decision Log

> **Purpose**: This file is the persistent memory for AI-assisted development on this project.
> Any AI agent working on this codebase **must read this file first** before making architectural decisions.
> It records decisions made, lessons learned, known gotchas, and important context.

**Last Updated**: 2026-07-14  
**Format**: Decisions are ordered newest-first.

---

## System Identity

| Field | Value |
|---|---|
| **Project Name** | BioSecure AI |
| **Repo** | `ArnavPundir22/Face-Attendance-System-Web-Version` |
| **Stack** | Flask + InsightFace + Supabase (pgvector) + TailwindCSS |
| **Entry Point** | `app.py` → `create_app()` |
| **Gunicorn Entry** | `app:app` |
| **Current Phase** | Phase 2 — Production Hardening |

---

## Critical Rules (Always Apply)

1. **Never use `print()`** — use `logger = logging.getLogger(__name__)` instead
2. **Never use bare `except:`** — always catch specific exceptions
3. **Admin routes use `supabase_admin`** — `utils/db.py` exports both clients
4. **Non-admin routes use `supabase`** — not the admin client
5. **`config.py` is the single source of truth** for all configuration
6. **Email is OPTIONAL** — `config.py` warns but does NOT crash if missing
7. **`utils/auth_helpers.py`** contains only in-memory rate limiting — no SQLite
8. **All 11 docs live in `docs/`** — always update `FTL.md` for feature changes

---

## Architectural Decisions

### [2026-07-14] Application Factory Pattern
**Decision**: Convert `app.py` from a module-level `app = Flask(__name__)` to `create_app()` factory function.  
**Rationale**: Enables proper testing (multiple app instances), environment-specific configuration, and blueprint isolation.  
**Impact**: Gunicorn entry point remains `app:app` (works because module-level `app = create_app()` exists).

---

### [2026-07-14] Email Made Optional
**Decision**: Changed `config.py` from `raise RuntimeError(...)` to `warnings.warn(...)` when `EMAIL_USER`/`EMAIL_PASS` are missing.  
**Rationale**: The `/send_attendance_email` route referenced in old docs doesn't exist in the current codebase. Making email a hard requirement blocked all deployments that don't use email. Email is a future feature, not a current one.  
**Impact**: App starts without email credentials. Email features will fail gracefully when the route is eventually added.

---

### [2026-07-14] Dual Supabase Clients
**Decision**: `utils/db.py` exports two clients: `supabase` (anon key) and `supabase_admin` (service-role key).  
**Rationale**: Using the service-role key for all operations bypasses Row Level Security (RLS), which is a security risk. The anon key respects RLS policies. Admin-only operations legitimately need to bypass RLS.  
**Current Gotcha**: `SUPABASE_ANON_KEY` may not be set yet — `supabase` client falls back to service-role key with a warning. This is noted in `docs/Rules.md` as a known limitation.

---

### [2026-07-14] auth_helpers.py — Rate Limiter Only
**Decision**: Completely rewrote `utils/auth_helpers.py` to remove all SQLite/bcrypt code.  
**Problem Found**: The old file imported `from utils.db import get_db_connection` — a function that doesn't exist in the Supabase-era `utils/db.py`. This was a silent broken import that would crash if the module was ever imported.  
**Solution**: Kept only the in-memory rate-limiting functions. OTP/password-reset now handled natively by Supabase Auth.  
**Warning**: Rate limiting is per-process only. In a multi-worker Gunicorn setup, each worker has its own lockout state. Solution: Redis-backed rate limiting (Phase 3 roadmap).

---

### [2026-07-13] pgvector Over Local Files
**Decision**: Store face embeddings in Supabase `vector(512)` column instead of local `.npy`/`.pkl` files.  
**Rationale**: Local files create stateful dependencies that prevent horizontal scaling and PaaS deployment. pgvector enables the same cosine similarity math in SQL.  
**Impact**: The `match_face` RPC function must exist in Supabase. See `docs/DATABASE.md` for the SQL.  
**Known Limitation**: If the Supabase project is reset, all student embeddings are lost (photos in `known_faces/` remain, but must be re-submitted to regenerate embeddings).

---

### [2026-07-13] InsightFace buffalo_l Model
**Decision**: Use InsightFace `buffalo_l` instead of `face_recognition` (dlib).  
**Rationale**: buffalo_l is state-of-the-art (ArcFace), ONNX-based (CPU/GPU portable), and produces 512-D embeddings compatible with pgvector. `face_recognition` is slower and less accurate.  
**Gotcha**: buffalo_l downloads ~300MB of model files to `~/.insightface` on first run. This is slow on cold starts (Render/Railway). Consider pre-downloading in the build step.  
**Config**: `INSIGHTFACE_CTX_ID=-1` for CPU, `=0` for first GPU.

---

### [2026-07-12] Supabase Auth Over Custom Auth
**Decision**: Replaced custom bcrypt/SQLite user table with Supabase Auth.  
**Rationale**: Supabase Auth provides secure email/password, JWT tokens, user metadata, and the admin API for CRUD — all without writing auth infrastructure.  
**Admin Role**: Stored in `user_metadata.is_admin` (bool). Not in a database table.  
**How to bootstrap first admin**: See `docs/ADMIN_GUIDE.md` — run SQL in Supabase SQL editor.

---

## Known Bugs / Gotchas

### Bug: `timestamp` stored as `text`
**Status**: Known, accepted  
**Details**: The `attendance.timestamp` column is `text` type (e.g., `"2026-07-14 15:30:00"`), not `timestamptz`. This means date-range queries use `ILIKE` matching (e.g., `.ilike('timestamp', '2026-07-14%')`), which is inefficient.  
**Fix**: Migrate to `timestamptz` in a future schema migration.

### Bug: No JWT Refresh
**Status**: Known, accepted  
**Details**: After login, the Supabase JWT stored in `session['access_token']` expires after ~1 hour. The app does not refresh it — users must re-login.  
**Fix**: Implement token refresh using `supabase.auth.refresh_session()` via a middleware hook.

### Bug: Rate Limiter Not Multi-Worker Safe
**Status**: Known, accepted  
**Details**: `utils/auth_helpers._login_attempts` is a module-level dict. In a 2-worker Gunicorn setup, each worker tracks attempts independently. A user can effectively get 2× the allowed attempts by hitting different workers.  
**Fix**: Use Redis for shared state (Phase 3).

### Gotcha: InsightFace Loads at Import Time
**Status**: By design  
**Details**: `utils/face.py` creates the `FaceAnalysis` model at module import time. This means the model loads when the first blueprint imports `utils/face`. Slow cold starts are expected (~5-15s on first run for model download).  
**Workaround**: Accept cold start delay; Gunicorn's `--preload` flag can pre-load the model in the master process before forking workers.

### Gotcha: `known_faces/` Is Not the Source of Truth
**Status**: By design  
**Details**: Photos saved to `known_faces/{name}.jpg` are reference copies only. The actual matching data is the embedding in the Supabase database. If a photo is deleted from `known_faces/`, recognition still works. If the database embedding is deleted, recognition fails even though the photo exists.

---

## Environment Variable Quick Reference

| Variable | Required | Default |
|---|---|---|
| `FLASK_SECRET_KEY` | ✅ Yes | — (crash if missing) |
| `SUPABASE_URL` | ✅ Yes | — (crash if missing) |
| `SUPABASE_SERVICE_ROLE_KEY` | ✅ Yes | — (crash if missing) |
| `SUPABASE_ANON_KEY` | ⚠️ Recommended | Falls back to service-role key |
| `EMAIL_USER` | ❌ Optional | `""` (warns if missing) |
| `EMAIL_PASS` | ❌ Optional | `""` (warns if missing) |
| `INSIGHTFACE_CTX_ID` | ❌ Optional | `-1` (CPU) |
| `FACE_MATCH_THRESHOLD` | ❌ Optional | `0.3` |
| `REATTENDANCE_INTERVAL_MINUTES` | ❌ Optional | `10` |
| `LOGIN_MAX_ATTEMPTS` | ❌ Optional | `5` |
| `LOGIN_LOCKOUT_MINUTES` | ❌ Optional | `15` |
| `MIN_PASSWORD_LENGTH` | ❌ Optional | `8` |
| `KNOWN_FACES_DIR` | ❌ Optional | `known_faces` |
| `LOG_LEVEL` | ❌ Optional | `INFO` |
| `PORT` | ❌ Optional (PaaS) | `8000` (in gunicorn.conf.py) |

---

## AI Session Notes

### Session: 2026-07-14 — Production Refactor
- Performed complete codebase analysis
- Found and fixed: broken `auth_helpers.py` import, `config.py` crash on missing email, duplicate Supabase clients, missing env vars in `.env.example`
- Created: `app.py` (factory pattern), `gunicorn.conf.py`, `Procfile`
- Created: All 11 documentation files
- Updated: `docs/ARCHITECTURE.md` → `docs/Architecture.md` with BioSecure AI branding
- All existing routes and templates left unchanged (backward compatible)
