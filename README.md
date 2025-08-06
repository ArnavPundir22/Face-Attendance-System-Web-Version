
# 📸 Face Attendance Web System

A modern, web-based attendance system that uses **InsightFace** for accurate face recognition and automatic attendance logging. Built with **Flask**, **SQLite**, and a sleek **TailwindCSS** frontend, this system allows for photo-based student recognition and intuitive record management.

---

## 🚀 Features

- **Face Recognition using InsightFace**  
  High-accuracy face embeddings using the Buffalo_L model.

- **Photo Upload for Attendance**  
  Upload group or individual photos and automatically detect & mark students present.

- **Lecture & Section Tagging**  
  Easily associate attendance with specific lectures and sections.

- **Smart Re-Attendance Prevention**  
  Prevents duplicate entries within a configurable time window (default: 10 minutes).

- **Live Attendance Viewer**  
  View all attendance logs with filters (date, status, section, lecture), export options, and styled rows.

- **Student Management**  
  Add new students with details and face photos. Automatically encodes and saves embeddings.

- **Email Attendance Report**  
  Email filtered attendance records as a PDF report to any Gmail ID.

- **Persistent Storage**  
  Uses SQLite (`database.db`) and Pickle (`EncodeFile_Insight.pkl`) for storing metadata and face encodings.

---

## 🖥️ Tech Stack

| Layer         | Tools / Libraries                          |
|---------------|---------------------------------------------|
| Backend       | Flask, SQLite3, InsightFace, OpenCV         |
| Frontend      | HTML, TailwindCSS, DataTables, JS           |
| Face Encoding | InsightFace (Buffalo_L), NumPy, cv2         |
| PDF Report    | ReportLab                                   |
| Email         | smtplib, EmailMessage                       |

---

## 📁 Project Structure

```bash
├── app.py                     # Main Flask server
├── encode_faces.py           # Script to encode all known faces
├── templates/
│   ├── index.html            # Main UI for uploading photos
│   ├── viewer.html           # Attendance viewer & filters
│   ├── add_student.html      # Add new student with photo
├── static/                   # (Optional) Static assets if any
├── known_faces/              # Folder to store face images
├── EncodeFile_Insight.pkl    # Pickled list of (embedding, name)
├── database.db               # SQLite DB storing students & logs
├── requirements.txt          # All Python dependencies
```

---

## ⚙️ Setup Instructions

1. **Clone this repo**:
   ```bash
   git clone https://github.com/your-username/face-attendance-web.git
   cd face-attendance-web
   ```

2. **Install dependencies**:
   *(preferably in a virtualenv)*
   ```bash
   pip install -r requirements.txt
   ```

3. **Run the encoding script (if not already encoded)**:
   ```bash
   python encode_faces.py
   ```

4. **Start the server**:
   ```bash
   python app.py
   ```

5. **Open in browser**:  
   Navigate to `http://127.0.0.1:5000`

---

## 🔑 Configuration

You can modify some values inside `app.py`:

```python
ENCODE_FILE = 'EncodeFile_Insight.pkl'
DB_FILE = 'database.db'
REATTENDANCE_INTERVAL_MINUTES = 10
FACE_MATCH_THRESHOLD = 0.5
EMAIL_USER = 'your_email@gmail.com'
EMAIL_PASS = 'your_app_password'  # Use App Password for Gmail
```

---

## 📝 Database Schema

- `students` table:
  ```
  ID | Name | Program | Branch | Mobile | Gmail
  ```

- `attendance` table:
  ```
  Student_ID | Name | Program | Branch | Mobile | Status | Timestamp | Lecture | Section
  ```

---

## 📷 Face Encoding Logic

- Run `encode_faces.py` to:
  - Load all images from `known_faces/`
  - Detect faces and generate embeddings
  - Average multiple images per person
  - Save to `EncodeFile_Insight.pkl`

- During attendance:
  - Embedding is compared using cosine similarity
  - If score > `FACE_MATCH_THRESHOLD`, it's considered a match

---

## 📬 Email Export

- Users can filter attendance records and email the results as a **PDF report** directly from the UI.
- Emails are sent using **Gmail SMTP**, configured in `app.py`.

---

## 🔐 Security Notes

- For email to work, generate an [App Password](https://myaccount.google.com/apppasswords) for Gmail.
- Do **not** commit `database.db` or `EncodeFile_Insight.pkl` to public repositories.

---


## 🤝 Contributions

Feel free to fork this project and submit pull requests. Suggestions, bug reports, and ideas are welcome!

---



## 💡 Future Improvements

- Add face quality checks (blur/tilt)
- Use live webcam again (optional)
- Support multi-face detection with bounding boxes
- Admin dashboard for report generation and editing attendance
- OTP verification before adding student?

---


## 👨‍💻 Developed By

**Arnav Pundir**  
B.Tech CSE | COER University Roorkee  
Email: *arnavp128@gmail.com*  
Portfolio: *arnavpundir22.github.io*  

---
