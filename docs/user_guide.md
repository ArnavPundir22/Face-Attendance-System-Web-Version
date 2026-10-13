# 👤 User & Administrator Manual

This guide explains how to operate **BioSecure AI**, enroll new student profiles using manual input or Neural OCR ID card scanning, process classroom group attendance, monitor biometric drift, and manage system records.

---

## 🔑 User Roles & Access Control (RBAC)

BioSecure AI supports Role-Based Access Control (RBAC):

- **Instructor / User**:
  - Process group classroom photos or active webcam video streams.
  - View live attendance records and filter by date, program, branch, or batch year.
  - Export attendance logs to CSV spreadsheets.
- **Administrator**:
  - Full access to all instructor capabilities.
  - Enroll new student profiles with 512D ArcFace facial embedding generation.
  - Access Neural OCR ID card scanner (`/api/ocr_id_card`).
  - Access the **Biometric Embedding Drift Dashboard** (`/admin/drift`) to monitor template aging.
  - Perform single-click student re-enrollment template resets.
  - Manage user accounts, assign admin roles, and modify academic structures.

---

## 💳 Student Enrollment & RapidOCR Scanning

To add a new student profile into the system:

1. Log in with an **Admin** account.
2. Click **Add Student** in the navigation header (`/add_student`).
3. Choose your preferred input method for auto-filling student details:
   - **Click ID Photo (Mobile Camera Window)**:
     - On mobile phones, tap **Click ID Photo**. The device's native camera window launches immediately (`capture="environment"`, ChatGPT-style), allowing you to capture a high-resolution snapshot of the physical student ID card directly.
     - The neural scanner automatically analyzes the captured photo and populates form fields.
   - **Upload ID Card (Gallery / File)**:
     - Tap **Upload ID Card** to select an existing digital ID card photo from your phone's photo library or computer files.
     - The system runs pretrained **RapidOCR (DBNet + SVTR ONNX)** to automatically extract and populate **Full Name**, **Student ID**, **Program**, **Branch**, **Batch Year**, and **Email**.
   - **Manual Input**:
     - Type the student's **Full Name**, **Student ID / Roll Number**, **Program** (e.g., B.Tech), **Branch** (e.g., CSE), and **Enrollment Year** (e.g., 2024).
4. Upload or snap a clear, front-facing portrait photo using the **Guided Live Camera** with face oval stencil. Ensure good lighting and avoid sunglasses, heavy tilt, or face coverings.
5. Click **Submit Student Profile**.
   - The system detects the face using RetinaFace.
   - Extracts a 512-dimensional ArcFace embedding vector.
   - Saves the profile to Supabase and updates the in-memory BLAS matrix cache for instant matching.

---

## 📱 Progressive Web App (PWA) & Offline Usage

BioSecure AI is engineered as a Progressive Web App (PWA) for native mobile and desktop experiences:

1. **Installation**:
   - **Android Chrome**: Tap the "Add BioSecure AI to Home Screen" prompt or select **Install App** from the browser menu.
   - **iOS Safari**: Tap the **Share** button $\rightarrow$ **Add to Home Screen**.
   - **Desktop Chrome / Edge**: Click the install icon in the URL bar.
2. **Offline Resilience**:
   - The Service Worker (`/sw.js`) caches the core App Shell (CSS, JS, icons, UI layouts).
   - If network connectivity drops, the system seamlessly redirects to `/offline`, preserving offline navigation without broken browser screens.

---

## 📷 Running Classroom Attendance

To record attendance for a class session:

1. Click **Take Attendance** on the main dashboard (`/`).
2. Select your attendance mode:
   - **Separate Class Mode** (Default): Restricts attendance marking strictly to students registered under the detected/selected Program, Branch, and Batch Year.
   - **Combined Class Mode**: Enables joint multi-branch lecture attendance where students from different branches are evaluated together.
3. Select your photo source:
   - **Upload File**: Select one or more high-resolution group photos showing the seated students.
   - **Webcam Snapshot**: Capture live snapshots using your connected camera feed.
4. Click **Process Attendance**.
5. The system displays:
   - **Annotated Image**: Green bounding boxes with names and confidence scores ($S \ge 0.40$) for identified students; Red bounding boxes labeled "Unknown" for unrecognized faces.
   - **Roster Sidebar**: List of identified students marked `Present` or `Absent`.
   - Attendance logs are automatically persisted to the database.

---

## 🛡️ Monitoring Biometric Drift (`/admin/drift`)

To manage biometric template aging (Patent Application #3):

1. Navigate to **Drift Monitoring** in the admin header (`/admin/drift`).
2. The dashboard displays all enrolled students sorted by highest `EWMA Drift Score`:
   - 🟢 **HEALTHY** ($EWMA < 0.15$): Biometric template performing optimally.
   - 🟡 **WARNING** ($0.15 \le EWMA < 0.25$): Minor appearance shift detected.
   - 🟠 **CRITICAL** ($0.25 \le EWMA < 0.35$): Significant drift detected; automated Gmail SMTP alert dispatched to admin.
   - 🔴 **ALERT** ($EWMA \ge 0.35$): Severe template aging; flagged for immediate re-enrollment.
3. **Single-Click Re-enrollment Reset**:
   - To update an outdated student template, upload a new reference portrait and click **Reset Drift Score**. The EWMA drift score resets to `0.00` (`HEALTHY`) and updates the embedding matrix.

---

## 📊 Viewing and Exporting Attendance Logs

1. Click **Attendance Viewer** (`/viewer`).
2. Filter entries dynamically by Date Range, Program, Branch, Batch Year, or Student Name.
3. Click **Export to CSV** to download a spreadsheet-ready report.

---

## 🛠️ Operational Safeguards & Directory Handling

- **Automatic Folder Creation**: Uploaded student portraits are saved in `known_faces/`. The server automatically provisions this directory on startup to prevent `FileNotFoundError` exceptions.
- **Stateless Error Handlers**: API requests (`Accept: application/json`) encountering errors receive structured JSON error payloads instead of HTML error pages.
