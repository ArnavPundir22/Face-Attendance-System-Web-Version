# 🗄️ Onyx Face Attendance System Database Setup

This project relies on **Supabase** (a PostgreSQL database) combined with the **`pgvector`** extension to handle all data persistence and facial similarity math.

## Required Setup

To run this application, you must create a Supabase project and execute the following SQL script in your Supabase **SQL Editor**. 

This script will set up the necessary tables, enable the vector extension, and create the highly-optimized `match_face` RPC function used by the Flask backend.

```sql
-- 1. Enable the pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- 2. Create the students table with the vector column
CREATE TABLE students (
  id text PRIMARY KEY,
  name text NOT NULL,
  program text,
  branch text,
  mobile text,
  gmail text,
  embedding vector(512) -- InsightFace buffalo_l uses 512 dimensions
);

-- 3. Create the attendance table
CREATE TABLE attendance (
  id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  student_id text REFERENCES students(id),
  name text,
  program text,
  branch text,
  mobile text,
  status text,
  timestamp text,
  lecture text,
  section text
);

-- 4. Create the pgvector matching function
CREATE OR REPLACE FUNCTION match_face (
  query_embedding vector(512),
  match_threshold float
)
RETURNS TABLE (
  id text,
  name text,
  similarity float
)
LANGUAGE sql STABLE
AS $$
  SELECT
    id,
    name,
    1 - (embedding <=> query_embedding) AS similarity
  FROM students
  WHERE embedding IS NOT NULL AND 1 - (embedding <=> query_embedding) >= match_threshold
  ORDER BY embedding <=> query_embedding
  LIMIT 1;
$$;
```

## User Accounts and Admin Roles
Because this application integrates directly with **Supabase Auth** (email/password), we do not need to create or query a custom `users` database table. All user credentials and authentication policies are managed securely inside Supabase's identity provider. 

Admin roles are defined using custom user metadata:
- If a user has `"is_admin": true` inside their Supabase Auth user metadata, the application will grant them access to the Admin Panel.
- Modifying roles or creating initial users can be done directly from the Supabase Authentication dashboard, or through the web application's user management page if you are already logged in as an admin.

## How the Database Replaces Local Storage
In older versions of this application, face embeddings were stored in local `.pkl` or `.npy` files. This created "stateful" dependencies that made hosting on platforms like Vercel impossible without losing data.

By utilizing `pgvector` and the `match_face` RPC function, the Flask server simply passes the 512-dimensional array of a webcam photo to the database. The database then rapidly computes the cosine similarity against all stored students and returns the exact match in milliseconds.

