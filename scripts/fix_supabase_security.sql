-- ============================================================================
-- BioSecure AI — Supabase Row Level Security (RLS) & Security Fix Script
-- Target Supabase Project: Face Attendance (avznrudspncnjbqersyg)
--
-- Fixes:
-- 1. rls_disabled_in_public (Enables Row-Level Security on all public tables)
-- 2. sensitive_columns_exposed (Restricts access to biometric embeddings & student PII)
-- ============================================================================

-- ----------------------------------------------------------------------------
-- 1. Enable Row Level Security (RLS) on active database tables
-- ----------------------------------------------------------------------------
ALTER TABLE IF EXISTS public.students ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.attendance ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.embedding_health ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS public.academic_structure ENABLE ROW LEVEL SECURITY;

-- ----------------------------------------------------------------------------
-- 2. Revoke default direct table permissions from unauthenticated 'anon' role
-- ----------------------------------------------------------------------------
REVOKE ALL ON ALL TABLES IN SCHEMA public FROM anon;

-- Explicitly revoke permissions on active sensitive tables if present
DO $$
BEGIN
    IF EXISTS (SELECT FROM pg_tables WHERE schemaname = 'public' AND tablename = 'students') THEN
        EXECUTE 'REVOKE ALL ON public.students FROM anon;';
    END IF;
    IF EXISTS (SELECT FROM pg_tables WHERE schemaname = 'public' AND tablename = 'attendance') THEN
        EXECUTE 'REVOKE ALL ON public.attendance FROM anon;';
    END IF;
    IF EXISTS (SELECT FROM pg_tables WHERE schemaname = 'public' AND tablename = 'embedding_health') THEN
        EXECUTE 'REVOKE ALL ON public.embedding_health FROM anon;';
    END IF;
END $$;

-- ----------------------------------------------------------------------------
-- 3. Clean up and create RLS policies on active tables
-- Note: Service Role (SUPABASE_SERVICE_ROLE_KEY) automatically bypasses RLS
-- ----------------------------------------------------------------------------

-- Table: public.students
DO $$
BEGIN
    IF EXISTS (SELECT FROM pg_tables WHERE schemaname = 'public' AND tablename = 'students') THEN
        EXECUTE 'DROP POLICY IF EXISTS "Authenticated users view students" ON public.students;';
        EXECUTE 'CREATE POLICY "Authenticated users view students" ON public.students FOR SELECT TO authenticated USING (true);';
    END IF;
END $$;

-- Table: public.attendance
DO $$
BEGIN
    IF EXISTS (SELECT FROM pg_tables WHERE schemaname = 'public' AND tablename = 'attendance') THEN
        EXECUTE 'DROP POLICY IF EXISTS "Authenticated users view attendance" ON public.attendance;';
        EXECUTE 'CREATE POLICY "Authenticated users view attendance" ON public.attendance FOR SELECT TO authenticated USING (true);';
    END IF;
END $$;

-- Table: public.academic_structure
DO $$
BEGIN
    IF EXISTS (SELECT FROM pg_tables WHERE schemaname = 'public' AND tablename = 'academic_structure') THEN
        EXECUTE 'DROP POLICY IF EXISTS "Authenticated read academic_structure" ON public.academic_structure;';
        EXECUTE 'CREATE POLICY "Authenticated read academic_structure" ON public.academic_structure FOR SELECT TO authenticated USING (true);';
    END IF;
END $$;

-- Table: public.embedding_health
-- Restricted exclusively to service_role (bypasses RLS automatically). No policy for anon/authenticated = Default DENY ALL.

-- ----------------------------------------------------------------------------
-- 4. Enable RLS and Policies for optional/legacy schema tables if they exist
-- ----------------------------------------------------------------------------
DO $$
BEGIN
    -- student_profiles
    IF EXISTS (SELECT FROM pg_tables WHERE schemaname = 'public' AND tablename = 'student_profiles') THEN
        EXECUTE 'ALTER TABLE public.student_profiles ENABLE ROW LEVEL SECURITY;';
        EXECUTE 'REVOKE ALL ON public.student_profiles FROM anon;';
        EXECUTE 'DROP POLICY IF EXISTS "Authenticated users view student_profiles" ON public.student_profiles;';
        EXECUTE 'CREATE POLICY "Authenticated users view student_profiles" ON public.student_profiles FOR SELECT TO authenticated USING (true);';
    END IF;

    -- attendance_logs
    IF EXISTS (SELECT FROM pg_tables WHERE schemaname = 'public' AND tablename = 'attendance_logs') THEN
        EXECUTE 'ALTER TABLE public.attendance_logs ENABLE ROW LEVEL SECURITY;';
        EXECUTE 'REVOKE ALL ON public.attendance_logs FROM anon;';
        EXECUTE 'DROP POLICY IF EXISTS "Authenticated users view attendance_logs" ON public.attendance_logs;';
        EXECUTE 'CREATE POLICY "Authenticated users view attendance_logs" ON public.attendance_logs FOR SELECT TO authenticated USING (true);';
    END IF;

    -- drift_logs
    IF EXISTS (SELECT FROM pg_tables WHERE schemaname = 'public' AND tablename = 'drift_logs') THEN
        EXECUTE 'ALTER TABLE public.drift_logs ENABLE ROW LEVEL SECURITY;';
        EXECUTE 'REVOKE ALL ON public.drift_logs FROM anon;';
    END IF;
END $$;
