# 🗄️ Database Schema & Vector Search Engine

BioSecure AI relies on **Supabase** (managed PostgreSQL) with the **`pgvector`** extension to handle data persistence and high-speed vector calculations.

---

## 1. Schema Definitions

```
          ┌──────────────────────────────────┐
          │             students             │
          ├──────────────────────────────────┤
          │ id        : text (PK)            │
          │ name      : text                 │
          │ program   : text                 │
          │ branch    : text                 │
          │ gmail     : text                 │
          │ embedding : vector(512)          │
          └────────────────┬─────────────────┘
                           │ 1
                           │
                           │ N
          ┌────────────────▼──────────────────┐
          │            attendance             │
          ├───────────────────────────────────┤
          │ id         : bigint (PK, Identity)│
          │ student_id : text (FK)            │
          │ name       : text                 │
          │ program    : text                 │
          │ branch     : text                 │
          │ status     : text                 │
          │ timestamp  : text                 │
          │ lecture    : text                 │
          │ section    : text                 │
          └───────────────────────────────────┘
```

---

## 2. Table Creation SQL Scripts

Run the following queries in the Supabase **SQL Editor** to initialize the database:

```sql
-- 1. Enable the vector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- 2. Create the students table
CREATE TABLE students (
    id        text PRIMARY KEY,
    name      text NOT NULL,
    program   text,
    branch    text,
    gmail     text,
    embedding vector(512) -- Holds InsightFace embeddings
);

-- 3. Create the attendance table
CREATE TABLE attendance (
    id         bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    student_id text REFERENCES students(id) ON DELETE CASCADE,
    name       text,
    program    text,
    branch     text,
    status     text NOT NULL, -- 'Present' | 'Absent'
    timestamp  text NOT NULL, -- Format: 'YYYY-MM-DD HH:MM:SS'
    lecture    text NOT NULL,
    section    text
);
```

---

## 3. Vector Similarity Match Function (RPC)

To compare local face signatures with enrolled student vectors efficiently, we define a custom RPC function in PostgreSQL that runs calculations on the database server.

```sql
CREATE OR REPLACE FUNCTION match_face(
    query_embedding vector(512),
    match_threshold float,
    filter_program text DEFAULT NULL,
    filter_branch text DEFAULT NULL,
    filter_section text DEFAULT NULL
)
RETURNS TABLE (
    id text,
    name text,
    similarity float
)
LANGUAGE sql STABLE AS $$
    SELECT 
        id, 
        name, 
        1 - (embedding <=> query_embedding) AS similarity
    FROM students
    WHERE 
        (filter_program IS NULL OR program = filter_program)
        AND (filter_branch IS NULL OR branch = filter_branch)
        AND embedding IS NOT NULL
        AND 1 - (embedding <=> query_embedding) >= match_threshold
    ORDER BY embedding <=> query_embedding ASC
    LIMIT 1;
$$;
```

> [!NOTE]
> The operator `<=>` represents **Cosine Distance** in PostgreSQL. Since embeddings are already unit-length L2 normalized, the calculation simplifies to:
> \[ \text{Similarity} = 1 - \text{Cosine Distance} \]

---

## 4. Query Performance Tuning (HNSW Indexing)

For installations scaling beyond thousands of students, scan times can be optimized by constructing a hierarchical nav navigable small world (HNSW) index:

```sql
CREATE INDEX ON students USING hnsw (embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);
```
This enables approximate nearest neighbor (ANN) searches, reducing lookups to sub-millisecond execution times.
