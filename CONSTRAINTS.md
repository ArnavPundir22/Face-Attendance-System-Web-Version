# Project Constraints & Guardrails — BioSecure AI

## Critical Directives & Boundaries
1. **No Patent Mentions in User Overview Document**: In response to user requirements, all overviews, reports, and generated summary documentation must omit any reference to patents, patent applications, IDF, or patent filing status. Refer to capabilities purely as technical architecture and mathematical algorithms.
2. **Strict Vector Normalization Invariant**: All ArcFace embeddings stored in memory and Supabase must maintain $\|v\|_2 = 1.0 \pm 10^{-6}$ to allow direct Cosine similarity computation via dot product.
3. **Database Security & RLS**: All Supabase database tables (`students`, `attendance`, `embedding_health`, `academic_structure`) must enforce Row-Level Security (RLS) to safeguard biometric data and student PII.
4. **Pose Gate Boundary**: Only faces with $|\text{Yaw}| \le 25^\circ$ and $|\text{Pitch}| \le 20^\circ$ are accepted for EWMA drift accumulation to prevent off-angle distortion from corrupting aging metrics.
5. **Stateless WSGI Model**: Web worker processes (Gunicorn) must remain stateless, delegating persistence to Supabase and cache updates via thread-safe synchronization.
