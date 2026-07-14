# 📋 Product Requirements Document (PRD)
# BioSecure AI

**Version**: 2.0  
**Status**: Active  
**Owner**: ArnavPundir22  
**Last Updated**: 2026-07-14  

---

## 1. Executive Summary

**BioSecure AI** is a web-based biometric attendance management platform. It uses AI-powered facial recognition (InsightFace `buffalo_l`) to automatically identify and log student attendance from photos or live webcam feeds. The system eliminates manual roll calls, prevents proxy attendance, and provides real-time analytics for administrators.

---

## 2. Problem Statement

Traditional attendance methods are:
- **Slow** — manual roll call wastes 5–10 minutes of lecture time per session.
- **Fraud-prone** — proxy attendance is trivially easy.
- **Data-poor** — paper records can't be easily queried, exported, or analysed.
- **Non-scalable** — grows linearly with class size.

---

## 3. Goals & Success Metrics

| Goal | Metric | Target |
|---|---|---|
| Accurate face recognition | Identification rate | ≥ 95% on clear photos |
| Fast attendance marking | Time per class session | < 30 seconds for ≤ 50 students |
| Zero proxy attendance | Duplicate detection rate | 100% within cooldown window |
| Admin efficiency | Admin operations completable | < 3 clicks |
| Reliable availability | Uptime | ≥ 99.5% |

---

## 4. User Personas

### Persona A — Faculty / Operator
- Takes attendance at the start of each lecture.
- Uploads a group photo or uses webcam capture.
- Needs: fast, simple UI; CSV export; no technical knowledge required.

### Persona B — Administrator
- Manages students, user accounts, system configuration.
- Monitors attendance trends via the dashboard.
- Needs: full CRUD access; analytics; user role management.

### Persona C — System Deployer
- Sets up and maintains the server environment.
- Needs: clear deployment guide; environment variable documentation; health check endpoint.

---

## 5. User Stories

### Authentication
| ID | Story | Priority |
|---|---|---|
| US-01 | As a user, I can log in with my email and password. | P0 |
| US-02 | As a user, I am locked out after 5 failed attempts. | P0 |
| US-03 | As an admin, I can create new user accounts without logging them in. | P0 |
| US-04 | As a user, I can log out and have my session cleared. | P0 |

### Attendance
| ID | Story | Priority |
|---|---|---|
| US-10 | As a faculty member, I can upload one or more photos to mark attendance. | P0 |
| US-11 | As a faculty member, I can use a webcam to capture and submit a photo. | P0 |
| US-12 | As a faculty member, I can specify the lecture name and section before submitting. | P0 |
| US-13 | As a faculty member, I see annotated results showing who was recognised and their confidence score. | P0 |
| US-14 | As a faculty member, I can download a CSV report of the session's attendance. | P0 |
| US-15 | As a system, I prevent duplicate attendance marks within the cooldown interval. | P0 |
| US-16 | As a faculty member on mobile, I can use the native device camera to take and submit a photo. | P1 |

### Students
| ID | Story | Priority |
|---|---|---|
| US-20 | As an admin, I can register a new student with their photo, name, ID, program, and branch. | P0 |
| US-21 | As a user, I can view the list of all registered students. | P0 |
| US-22 | As an admin, I can edit a student's details. | P1 |
| US-23 | As an admin, I can delete a student record. | P1 |
| US-24 | As a system, I prevent duplicate student IDs or names. | P0 |

### Admin Dashboard
| ID | Story | Priority |
|---|---|---|
| US-30 | As an admin, I can view total students, total attendance records, total users, and today's attendance count. | P0 |
| US-31 | As an admin, I can see a 7-day attendance trend chart. | P1 |
| US-32 | As an admin, I can manually mark a student's attendance. | P1 |
| US-33 | As an admin, I can manage all user accounts (view, edit, delete, change roles). | P0 |

### Records & Reporting
| ID | Story | Priority |
|---|---|---|
| US-40 | As a user, I can view the full attendance table with search/filter. | P0 |
| US-41 | As a user, I can export the attendance table as a CSV. | P0 |

---

## 6. Feature Matrix

| Feature | Status | Notes |
|---|---|---|
| Face detection (InsightFace buffalo_l) | ✅ Production | ONNX Runtime, CPU/GPU |
| Face matching (pgvector cosine similarity) | ✅ Production | Supabase RPC |
| Multi-photo upload | ✅ Production | Multiple files per request |
| Webcam capture (desktop) | ✅ Production | `getUserMedia` API |
| Mobile camera input | ✅ Production | Native file input |
| Re-attendance cooldown | ✅ Production | Configurable interval |
| Student registration | ✅ Production | Photo + embedding stored |
| Admin dashboard | ✅ Production | Stats + charts |
| User management | ✅ Production | Supabase Auth Admin API |
| CSV export | ✅ Production | Client-side generation |
| Email reports | ⚠️ Partial | Config exists, route absent |
| Multi-tenant support | ❌ Planned | Phase 3 |
| Mobile app | ❌ Planned | Phase 4 |
| Real-time websocket attendance | ❌ Planned | Phase 3 |

---

## 7. Non-Functional Requirements

| Category | Requirement |
|---|---|
| **Performance** | Single photo processed in < 5s on CPU, < 1s on GPU |
| **Security** | No student photos stored in accessible web paths; RLS enforced on all tables |
| **Scalability** | Stateless design allows horizontal scaling (PostgreSQL handles shared state) |
| **Reliability** | Graceful error handling; no uncaught exceptions exposed to users |
| **Accessibility** | WCAG AA colour contrast ratios; keyboard-navigable forms |
| **Compatibility** | Works in Chrome, Firefox, Safari (latest two versions); iOS/Android mobile browsers |
| **Privacy** | Face embeddings stored as float vectors, not raw photos; GDPR-aligned |

---

## 8. Out of Scope (v2.0)

- Real-time video streaming attendance
- Offline / PWA mode
- Native mobile apps (iOS / Android)
- Multi-institution / SaaS multi-tenancy
- LDAP / SSO authentication
- Attendance notification emails to students
