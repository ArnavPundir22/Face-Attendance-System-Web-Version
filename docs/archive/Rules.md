# 📏 Engineering Rules & Standards
# BioSecure AI

**Version**: 2.0  
**Last Updated**: 2026-07-14  
**Applies to**: All contributors and AI-assisted development sessions.

---

## 1. Code Quality Standards

### Python

| Rule | Standard |
|---|---|
| Style | PEP 8 — 4-space indent, 99-char line limit |
| Type hints | Required on all function signatures |
| Docstrings | Required on all public functions and classes (Google style) |
| Imports | Standard lib → third-party → local; sorted within groups |
| F-strings | Preferred over `.format()` or `%` formatting |
| Error handling | Never use bare `except:` — catch specific exceptions |
| Logging | Use `logger = logging.getLogger(__name__)` — no `print()` |

### Python Anti-Patterns (Banned)

```python
# ❌ BAD — bare except
try:
    do_thing()
except:
    pass

# ✅ GOOD — specific exception with logging
try:
    do_thing()
except Exception as e:
    logger.error("do_thing failed: %s", e)

# ❌ BAD — print debugging
print("User logged in:", username)

# ✅ GOOD — structured logging
logger.info("User authenticated: %s (admin=%s)", username, is_admin)

# ❌ BAD — raw string SQL or unparameterised queries
query = f"SELECT * FROM students WHERE name = '{name}'"

# ✅ GOOD — Supabase parameterised builder
supabase.table('students').select('*').eq('name', name).execute()
```

### HTML / Jinja2
- Use semantic HTML5 elements (`<main>`, `<nav>`, `<header>`, `<section>`)
- All form inputs must have `id` attributes matching their `name`
- All interactive buttons must have unique, descriptive `id` attributes
- Jinja2 template variables should always use the `{{ var | e }}` escaping pattern for user-supplied content

### JavaScript
- Use `const` / `let` — never `var`
- Prefer `async/await` over `.then()` chains
- Always handle `fetch()` errors with `try/catch`
- Use `lucide.createIcons()` after any dynamic DOM insertion using Lucide

---

## 2. Security Rules

### Mandatory

- **No secrets in code**: All credentials go in `.env` and are loaded via `config.py`
- **Never commit `.env`**: It is in `.gitignore`; check before every commit
- **Service-role key**: Only used in `admin_bp` routes; never in templates or JS
- **All admin routes**: Must call `_require_admin()` at the top of the handler
- **File uploads**: Always use `werkzeug.utils.secure_filename()` before saving
- **Password handling**: Never store passwords — Supabase Auth handles all password storage
- **Session**: Never store sensitive data (passwords, full JWTs) in client-accessible cookies

### Access Control Checklist (before merging any new route)

- [ ] Is the route behind `session['logged_in']`? (handled by `before_request`)
- [ ] If admin-only, does it call `_require_admin()`?
- [ ] If using `supabase_admin`, is there a legitimate reason to bypass RLS?
- [ ] Are all form inputs validated (not null, correct type, safe length)?
- [ ] Are file paths constructed with `os.path.join` + `secure_filename`?

---

## 3. Git Workflow

### Branch Naming
```
feature/short-description    # New features
fix/issue-description        # Bug fixes
docs/what-was-documented     # Documentation only
refactor/what-was-changed    # Refactoring, no new features
chore/task-description       # Dependency updates, config changes
```

### Commit Messages
Follow [Conventional Commits](https://www.conventionalcommits.org/):
```
feat: add Redis-backed rate limiter for multi-worker support
fix: resolve broken SQLite import in auth_helpers.py
docs: create 11 production documentation files
refactor: convert app.py to application factory pattern
chore: update gunicorn to 23.0.0
```

### Pull Request Rules
1. PRs must be rebased on `main` (no merge commits)
2. All CI checks must pass before merge
3. Self-review required — read your own diff before requesting review
4. Include a "Testing" section in the PR description

---

## 4. Environment Variable Rules

- **All new config values** must be added to both `config.py` and `.env.example`
- **Required variables** must raise `ValueError` on import if missing
- **Optional variables** must have documented defaults and use `warnings.warn()` if needed
- **Boolean env vars** must use: `os.environ.get('VAR', 'false').lower() == 'true'`
- **Never** use `os.environ['KEY']` (raises `KeyError`); always use `.get(KEY, default)`

---

## 5. Dependency Management

- **Pin all dependencies** in `requirements.txt` to exact versions (e.g., `Flask==3.1.1`)
- **Update dependencies** only intentionally — test after any update
- **Security audits**: Run `pip audit` periodically
- **No new dependencies** should be added without documenting the rationale

---

## 6. Documentation Rules

- **Every new feature** must update `docs/FTL.md` with date, version, and status
- **Every new route** must be documented in `docs/TAD.md`
- **Architecture changes** must update `docs/SAD.md` and `docs/Architecture.md`
- **Breaking changes** must update `docs/memory.md` with the decision rationale
- **`.env.example`** must be updated whenever a new config variable is added

---

## 7. Blueprint Rules

- **Each blueprint** handles exactly one domain: auth / attendance / students / admin
- **Admin operations** always use `supabase_admin` (service-role client)
- **Non-admin operations** always use `supabase` (anon/RLS-constrained client)
- **Helper functions** shared across blueprints belong in `utils/`, not in blueprints
- **No cross-blueprint imports** — blueprints must not import from each other
- **Auth guard** in admin blueprint: every function must call `_require_admin()` first

---

## 8. Error Handling Standard

```python
# Pattern for database operations in route handlers
try:
    response = supabase.table('students').select('*').execute()
    data = response.data
except Exception as e:
    logger.error("Failed to fetch students: %s", e)
    data = []  # graceful degradation
    # For writes, consider returning an error response instead
```

For routes that write data and failure is unacceptable:
```python
try:
    supabase.table('attendance').insert({...}).execute()
except Exception as e:
    logger.error("Attendance insert failed for %s: %s", student_name, e)
    return render_template('page.html', error="Failed to save attendance. Please try again.")
```

---

## 9. Performance Rules

- **InsightFace model** is loaded once at import — never reload per-request
- **Supabase clients** are module-level singletons — never create per-request
- **Images**: Validate and reject files > 10MB at the Flask level (Nginx handles 20MB upstream)
- **Database queries**: Use `.select('col1, col2')` not `.select('*')` when only specific columns needed
- **Pagination**: Large table queries (attendance) must use `.limit()` or client-side pagination

---

## 10. AI-Assisted Development Rules

When using AI (Gemini, Claude, etc.) to modify this codebase:

- The AI **must read** `docs/memory.md` before making architectural decisions
- The AI **must not** change route signatures without updating `docs/TAD.md`
- The AI **must not** add new dependencies without updating `requirements.txt`
- The AI **must** follow the error handling standard in section 8
- The AI **must** use `logger.X()` not `print()` for any new log output
- The AI **must** update `docs/FTL.md` for any feature changes
