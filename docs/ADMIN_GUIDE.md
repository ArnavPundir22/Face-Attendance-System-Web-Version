# 👨‍💼 Administrator Guide

This guide covers how to manage the system, register students, and accurately capture daily attendance.

## 1. Accessing the Dashboard

For security reasons, you cannot automatically register as an admin from the web interface. 
1. Go to the `/register` page and create a new user account.
2. Log in to your Supabase Dashboard.
3. Open the `users` table and manually set the `is_admin` boolean flag to `TRUE` for your newly created account.
4. Log back into the web application. You will now see the **Admin Panel** accessible from the top navigation bar.

## 2. Registering Students
To add a new student to the facial recognition database:
1. Navigate to the **Admin > Students** page.
2. Click **Add New Student**.
3. Fill in the student's details (Name, ID, Program, etc.).
4. **Upload a clear, well-lit portrait photo.** Ensure the student is looking directly at the camera and there are no other faces in the background.
5. Submit. The system will encode their face instantly into the database.

## 3. Taking Attendance
Taking attendance is entirely automated. You can do this via the home page (`/`).

1. **Select Metadata**: Choose the current **Lecture** and **Section** from the dropdowns so the database knows what class you are tracking.
2. **Choose a Method**:
   - **File Upload**: Take a high-resolution photo of the entire classroom with a smartphone or DSLR and upload it. The system will scan the image and find all known faces simultaneously.
   - **Webcam (Manual)**: Click the "Capture Photo" button to take a single snapshot of whoever is standing in front of the camera.
   - **Webcam (Auto-Capture)**: Click "Start Auto-Capture". The system will automatically take 5 photos over a set interval. This is perfect for setting up a laptop at the door as students walk into the room!

> [!TIP]  
> The system has built-in **Re-attendance Prevention**. If a student walks past the camera multiple times during the same lecture within 60 minutes, the system will mark them as "Already Marked" and will not create duplicate entries in the database.

## 4. Exporting Reports
To view and download attendance logs:
1. Navigate to the **Attendance Viewer** from the top navigation bar.
2. You can filter the table using the global search bar, or use the individual column search bars (e.g., search for a specific "Section").
3. Click the **CSV** button at the top of the table. Your browser will instantly generate and download an Excel-compatible spreadsheet of the filtered data!
