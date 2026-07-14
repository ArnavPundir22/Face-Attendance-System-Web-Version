# 👨‍💼 Onyx Face Attendance System Administrator Guide

This guide covers how to manage the system, register students, and accurately capture daily attendance using the **Onyx Face Attendance System**.

## 1. Accessing the Dashboard & First Admin Setup

For security reasons, the `/register` route in the web interface is restricted to logged-in administrators only. To bootstrap your very first administrator account:

1. **Create a User in Supabase**:
   - Go to your **Supabase Dashboard** -> **Authentication** -> **Users**.
   - Click **Add User** -> **Create User** and enter the email and password for your admin account.
2. **Elevate to Admin**:
   - Open the **SQL Editor** in your Supabase Dashboard.
   - Run the following SQL query to update the raw user metadata, substituting your admin's email and preferred username:
     ```sql
     UPDATE auth.users 
     SET raw_user_meta_data = jsonb_build_object('is_admin', true, 'username', 'admin') 
     WHERE email = 'your-admin-email@example.com';
     ```
3. **Log In**:
   - Go to the `/login` page on the web application.
   - Log in using your newly created admin credentials. You will now see the **Admin Panel** accessible from the top navigation bar.

Once logged in as an admin, you can create additional user accounts directly from the `/register` web interface.

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
> The system has built-in **Re-attendance Cooldown**. If a student walks past the camera multiple times during the same lecture within the cooldown interval (e.g., 10 minutes), the system will mark them as "Already Marked" and will not create duplicate entries in the database.

## 4. User Account Management
As an administrator, you have access to a full user management portal under **Admin > Manage Users**:
- **List Users**: View all registered users, their emails, and admin status.
- **Edit Users**: Modify usernames, change emails, reset passwords, or promote/demote users to/from the admin role.
- **Delete Users**: Remove user accounts from Supabase Auth entirely (the application prevents you from deleting yourself or revoking the last remaining admin account).

## 5. Exporting Reports
To view and download attendance logs:
1. Navigate to the **Attendance Viewer** from the top navigation bar.
2. You can filter the table using the global search bar, or use the individual column search bars (e.g., search for a specific "Section").
3. Click the **CSV** button at the top of the table. Your browser will instantly generate and download an Excel-compatible spreadsheet of the filtered data!

