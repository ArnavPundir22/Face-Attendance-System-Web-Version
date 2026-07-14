# 👨‍💼 BioSecure AI Administrator Guide

This guide covers system management, student registration, and daily attendance capture using **BioSecure AI**.

---

## 1. First Admin Setup

For security, the `/register` route is restricted to logged-in administrators. To bootstrap your first admin account:

**Step 1 — Create a User in Supabase:**
- Go to **Supabase Dashboard → Authentication → Users**
- Click **Add User → Create User**
- Enter the admin's email and a strong password

**Step 2 — Grant Admin Role via SQL:**
- Open **Supabase Dashboard → SQL Editor**
- Run the following (replace with your admin's email and chosen username):

```sql
UPDATE auth.users
SET raw_user_meta_data = jsonb_build_object(
    'is_admin', true,
    'username', 'admin'
)
WHERE email = 'your-admin-email@example.com';
```

**Step 3 — Log In:**
- Go to `/login` on the web application
- Log in with your admin credentials
- The **Admin Portal** will appear in the navigation bar

Once logged in, create additional accounts via the `/register` interface.

---

## 2. Registering Students

To add a new student to the facial recognition database:

1. Navigate to **Admin → Students** or click **Add Student** in the nav
2. Fill in the student's details:
   - **Name** (required) — used as the display name
   - **Student ID** (required) — must be unique
   - **Program, Branch, Mobile, Email** (optional)
3. **Upload a clear portrait photo** — guidelines:
   - One face only in the frame
   - Well-lit, facing the camera directly
   - JPEG/PNG format
4. Click **Submit**

The system encodes the face and stores the 512-dimensional embedding in Supabase. Recognition is active immediately.

> [!TIP]
> For best recognition accuracy, use a high-resolution, front-facing portrait. Avoid sunglasses, heavy shadows, or obscured faces in the registration photo.

---

## 3. Taking Attendance

Navigate to the home page (`/`) to mark attendance.

**Step 1 — Set Session Metadata:**
- Enter the **Lecture Name** (e.g., `CS101`) and **Section** (e.g., `A`)
- These are stored with each attendance record for filtering

**Step 2 — Choose Input Method:**

| Method | Best For |
|---|---|
| **Upload Files** | Group classroom photos taken with a phone/DSLR |
| **PC Webcam** | Desk/lab setup; single student at a time |
| **Mobile Camera** | Holding the phone and photographing the class |

**Step 3 — Submit and Review:**
- Click **Scan & Mark Present**
- View annotated results (bounding boxes + names + confidence %)
- Download a CSV of the session's attendance

> [!TIP]
> **Re-attendance Cooldown**: The system ignores duplicate scans within the configured interval (default: 10 minutes per lecture). Students who pass the camera multiple times will show as **"Already Marked"** — no duplicate entries are created.

---

## 4. Manual Attendance Marking

For exceptions (sick students, late arrivals, corrections):

1. Go to **Admin Panel → Mark Attendance**
2. Select the student from the dropdown
3. Choose **Present** or **Absent**
4. Enter the lecture name and section
5. Click **Mark Attendance**

Records created this way bypass face recognition and are inserted directly.

---

## 5. User Account Management

Under **Admin Portal → Manage Users**:

| Action | Notes |
|---|---|
| **View Users** | Lists all Supabase Auth users with email, username, and admin status |
| **Edit User** | Change username, email, password, or admin role |
| **Promote to Admin** | Toggle `is_admin` flag in user metadata |
| **Delete User** | Removes from Supabase Auth entirely |

**Safety guards:**
- You cannot delete your own account
- You cannot remove the last remaining admin account
- Password changes require minimum length (`MIN_PASSWORD_LENGTH`, default: 8 characters)

---

## 6. Attendance Records & Export

Navigate to **View Records** (`/viewer`):

- Full searchable table of all attendance records
- **Global search**: Filter by any field
- **Column search**: Filter by lecture, section, date, etc.
- **CSV Export**: Click the **CSV** button to download the currently filtered data as a spreadsheet

---

## 7. Health & Monitoring

The system exposes a health check endpoint:
```
GET /healthz → {"status": "ok", "service": "biosecure-ai-face-attendance"}
```

Use this with UptimeRobot, Betterstack, or any uptime monitoring service to receive alerts if the application goes down.

---

## 8. Troubleshooting

| Problem | Likely Cause | Solution |
|---|---|---|
| All dashboard metrics show 0 | Supabase RLS blocking admin queries | Ensure `supabase_admin` uses service-role key |
| Face not recognised | Low-quality photo or threshold too strict | Lower `FACE_MATCH_THRESHOLD` or re-register student |
| "No face detected" error | No face in image or model not loaded | Wait for model load; ensure image has a clear face |
| Login locked out | Too many failed attempts | Wait `LOGIN_LOCKOUT_MINUTES` (default: 15 min) |
| Slow first request | InsightFace model loading | Expected — model loads once at startup (~5-15s) |
