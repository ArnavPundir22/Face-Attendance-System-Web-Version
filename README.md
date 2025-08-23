# 📸 Face Attendance Web System

[![Python](https://img.shields.io/badge/Python-3.9%2B-blue?logo=python)](https://www.python.org/)  
[![Flask](https://img.shields.io/badge/Flask-2.0%2B-black?logo=flask)](https://flask.palletsprojects.com/)  
[![InsightFace](https://img.shields.io/badge/InsightFace-Buffalo__L-orange?logo=ai)](https://github.com/deepinsight/insightface)  
[![TailwindCSS](https://img.shields.io/badge/TailwindCSS-3.0%2B-38B2AC?logo=tailwind-css)](https://tailwindcss.com/)  
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)  

A modern, **web-based attendance system** powered by **InsightFace** for accurate face recognition and automatic attendance logging.  
Built with **Flask**, **SQLite**, and **TailwindCSS**, it allows **photo-based student recognition**, smart attendance tracking, and intuitive record management.  

---

## 📑 Table of Contents

- [🚀 Features](#-features)  
- [🖥️ Tech Stack](#️-tech-stack)  
- [📁 Project Structure](#-project-structure)  
- [⚙️ Setup Instructions](#️-setup-instructions)  
- [🔑 Configuration](#-configuration)  
- [📝 Database Schema](#-database-schema)  
- [📷 Face Encoding Workflow](#-face-encoding-workflow)  
- [📬 Email Export](#-email-export)  
- [🔐 Security Notes](#-security-notes)  
- [🤝 Contributions](#-contributions)  
- [💡 Future Enhancements](#-future-enhancements)  
- [👨‍💻 Developed By](#-developed-by)  

---

## 🚀 Features

- **🔍 Face Recognition with InsightFace**  
  High-accuracy embeddings using the **Buffalo_L** model.  

- **📷 Photo Upload for Attendance**  
  Detects multiple faces from **group or individual photos** and marks students present.  

- **📚 Lecture & Section Tagging**  
  Attendance linked to specific **lectures & sections**.  

- **✅ Smart Re-Attendance Prevention**  
  Prevents duplicate entries within a configurable time window (**default: 10 minutes**).  

- **📊 Live Attendance Viewer**  
  Full attendance history with **filters, search, row styling, and export options**.  

- **👨‍🎓 Student Management**  
  Add new students with full details + face photo → system **auto-encodes** embeddings.  

- **📧 Email Attendance Reports**  
  Send **filtered PDF attendance reports** to any Gmail ID.  

- **💾 Persistent Storage**  
  Face encodings stored in `EncodeFile_Insight.pkl`, records in `database.db`.  

---

## 🖥️ Tech Stack

| Layer         | Tools / Libraries                          |
|---------------|---------------------------------------------|
| Backend       | Flask, SQLite3, InsightFace, OpenCV         |
| Frontend      | HTML, TailwindCSS, DataTables, JavaScript   |
| Face Encoding | InsightFace (Buffalo_L), NumPy, OpenCV      |
| PDF Export    | ReportLab                                   |
| Email         | smtplib, EmailMessage                       |

---

## 📁 Project Structure

```bash
├── app.py                     # Main Flask server
├── encode_faces.py            # Script to encode all known faces
├── templates/
│   ├── index.html             # Upload photos for attendance
│   ├── viewer.html            # Attendance viewer + filters
│   ├── add_student.html       # Add student form + photo upload
├── static/                    # Static assets (CSS/JS if any)
├── known_faces/               # Stores student photos
├── EncodeFile_Insight.pkl     # Saved embeddings
├── database.db                # SQLite DB (students + attendance)
├── requirements.txt           # Python dependencies
```

---

## ⚙️ Setup Instructions

1. **Clone this repo**:
   ```bash
   git clone https://github.com/your-username/face-attendance-web.git
   cd face-attendance-web
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Encode faces**:
   ```bash
   python encode_faces.py
   ```

4. **Run the server**:
   ```bash
   python app.py
   ```

5. **Access in browser**:  
   👉 [http://127.0.0.1:5000](http://127.0.0.1:5000)

---

## 🔑 Configuration

Inside **`app.py`**:

```python
ENCODE_FILE = 'EncodeFile_Insight.pkl'
DB_FILE = 'database.db'
REATTENDANCE_INTERVAL_MINUTES = 10
FACE_MATCH_THRESHOLD = 0.5
EMAIL_USER = 'your_email@gmail.com'
EMAIL_PASS = 'your_app_password'  # Use Gmail App Password
```

---

## 📝 Database Schema

- **students**  
  ```
  ID | Name | Program | Branch | Mobile | Gmail
  ```

- **attendance**  
  ```
  Student_ID | Name | Program | Branch | Mobile | Status | Timestamp | Lecture | Section
  ```

---

## 📷 Face Encoding Workflow

- `encode_faces.py`:
  - Loads images from `known_faces/`
  - Detects faces → generates embeddings
  - Averages multiple embeddings per student
  - Saves to `EncodeFile_Insight.pkl`

- During attendance:
  - Uploaded photo → embeddings generated
  - Compared with stored encodings using **cosine similarity**
  - Match if similarity > `FACE_MATCH_THRESHOLD`

---

## 📬 Email Export

- Filter logs in **Attendance Viewer**  
- Export them as a **styled PDF**  
- Email directly via Gmail SMTP  

---

## 🔐 Security Notes

- Use **App Passwords** for Gmail → [Setup Here](https://myaccount.google.com/apppasswords)  
- Never commit `database.db` or `EncodeFile_Insight.pkl` in public repos  

---

## 🤝 Contributions

Pull requests, suggestions, and feature ideas are **always welcome** 🚀  

---

## 💡 Future Enhancements

- ✅ Face quality checks (blur / tilt detection)  
- ✅ Optional live webcam attendance  
- ✅ Multi-face detection with bounding box previews  
- ✅ Admin dashboard for attendance editing  
- ✅ OTP verification before student enrollment  

---

## 👨‍💻 Developed By

**Arnav Pundir**  
🎓 B.Tech CSE | COER University Roorkee  
📧 Email: *arnavp128@gmail.com*  
🌐 Portfolio: [arnavpundir22.github.io](https://arnavpundir22.github.io)  

---
