# 🗄️ BioSecure AI Database Setup

This project uses **Supabase** (managed PostgreSQL) with the **`pgvector`** extension for both data storage and facial similarity matching.

## Required Setup

Execute the following SQL in your Supabase **SQL Editor** (Dashboard → SQL Editor → New query):

```sql
-- 1. Enable the pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- 2. Create the students table with the vector column
CREATE TABLE students (
    id        text PRIMARY KEY,
    name      text NOT NULL,
    program   text,
    branch    text,
    mobile    text,
    gmail     text,
    embedding vector(512)  -- InsightFace buffalo_l produces 512-dimensional embeddings
);

-- 3. Create the attendance table
CREATE TABLE attendance (
    id         bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    student_id text REFERENCES students(id),
    name       text,
    program    text,
    branch     text,
    mobile     text,
    status     text,     -- 'Present' or 'Absent'
    timestamp  text,     -- 'YYYY-MM-DD HH:MM:SS'
    lecture    text,
    section    text
);

-- 4. Create the face-matching RPC function
CREATE OR REPLACE FUNCTION match_face(
    query_embedding vector(512),
    match_threshold float
)
RETURNS TABLE (id text, name text, similarity float)
LANGUAGE sql STABLE AS $$
    SELECT
        id,
        name,
        1 - (embedding <=> query_embedding) AS similarity
    FROM students
    WHERE embedding IS NOT NULL
    AND   1 - (embedding <=> query_embedding) >= match_threshold
    ORDER BY embedding <=> query_embedding
    LIMIT 1;
$$;
```

> [!IMPORTANT]
> If `pgvector` is not available in your Supabase plan, enable it from:  
> **Dashboard → Database → Extensions → vector**

---

## User Accounts and Admin Roles

All user credentials are managed by **Supabase Auth** — there is no custom `users` table. Admin roles are stored in Supabase user metadata.

### Bootstrap First Admin

After creating a user in Supabase Auth, run this SQL to grant admin access:

```sql
UPDATE auth.users
SET raw_user_meta_data = jsonb_build_object(
    'is_admin', true,
    'username', 'admin'
)
WHERE email = 'your-admin-email@example.com';
```

---

## Row Level Security (RLS)

The application uses the **service-role key** (which bypasses RLS) for all database operations. If you enable RLS on the `students` or `attendance` tables, ensure that the service-role key is used for all Flask backend operations.

For least-privilege compliance, consider adding RLS policies that allow:
- `SELECT` on `students` for authenticated users
- `INSERT`/`SELECT` on `attendance` for authenticated users
- Full access for the service role

---

## How Vector Matching Works

When a face is detected in an uploaded photo:
1. InsightFace generates a **512-dimensional float array** (embedding)
2. The embedding is **L2-normalised** (divided by its Euclidean norm)
3. The normalised embedding is sent to Supabase via the `match_face` RPC
4. PostgreSQL computes **cosine similarity** (`1 - cosine_distance`) against all stored embeddings using pgvector's `<=>` operator
5. The closest match above `FACE_MATCH_THRESHOLD` (default: 0.3) is returned

> [!NOTE]
> Cosine similarity of **1.0** = identical faces. Threshold of **0.3** means the system requires at least 30% similarity — this is intentionally permissive to handle varying lighting and angles. Increase it (e.g., 0.5) for stricter matching.
