# Rollback Strategy & Safety Net — BioSecure AI

## Emergency Rollback Plan

### Git Restore Points
- **Baseline Commit**: `git rev-parse HEAD` prior to academic structure bulk-delete feature implementation.
- **Rollback Command**:
  ```bash
  git checkout HEAD -- src/blueprints/admin.py src/templates/admin_academics.html
  ```

### Database Safety Net
- Table `academic_structure` entries deleted during testing or cleanup can be restored from canonical institutional lists or by re-adding through `/admin/academics` or auto-registration via students sync.
- Student profiles (`students` table) and attendance records (`attendance` table) are completely decoupled from `academic_structure` by foreign key constraints (no cascading deletes occur on student data).

### Verification After Rollback
1. Run pytest suite:
   ```bash
   .venv/bin/pytest tests/unit -v
   ```
2. Verify admin academics route loads:
   ```bash
   .venv/bin/python -c "from app import create_app; app = create_app(); client = app.test_client(); res = client.get('/admin/academics'); print(res.status_code)"
   ```
