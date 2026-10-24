# Empirical Test Checklist — BioSecure AI

## Verification Matrix

| Category | Verification Item | Target Command / Method | Expected Output | Status |
| :--- | :--- | :--- | :--- | :--- |
| **Doc Rules** | No Patent Mentions (10-Page PDF) | PyMuPDF full text scan | Exactly 0 occurrences / 0 matches | ✅ **VERIFIED PASSED** |
| **Doc Rules** | No Patent Mentions (10-Page DOCX) | python-docx full text & table scan | Exactly 0 occurrences / 0 matches | ✅ **VERIFIED PASSED** |
| **Doc Rules** | No Patent Mentions (One-Page PDF) | PyMuPDF full text scan | Exactly 0 occurrences / 0 matches | ✅ **VERIFIED PASSED** |
| **Doc Rules** | No Patent Mentions (One-Page DOCX) | python-docx full text & table scan | Exactly 0 occurrences / 0 matches | ✅ **VERIFIED PASSED** |
| **Page Count** | Exact 10 Pages (Master PDF) | `fitz.open(...).page_count == 10` | Exact 10 pages | ✅ **VERIFIED PASSED** |
| **Page Count** | Exact 1 Page (One-Page PDF) | `fitz.open(...).page_count == 1` | Exact 1 page | ✅ **VERIFIED PASSED** |
| **DOCX Structure** | Full 10 Chapters (Master DOCX) | 134 paragraphs, 22 styled tables | Complete parity with PDF | ✅ **VERIFIED PASSED** |
| **DOCX Structure** | One-Page Overview (DOCX) | Executive Briefing, 3 styled tables | Complete parity with PDF | ✅ **VERIFIED PASSED** |
| **Security & Git** | Comprehensive .gitignore Audit | `git check-ignore -v` verification suite | Secrets, PII faces, logs, temp files, and root symlinks blocked | ✅ **VERIFIED PASSED** |
| **Code Tests** | Unit Tests Execution | `.venv/bin/pytest tests/unit -v` | 22 passed | ✅ **VERIFIED PASSED** |
| **OCR Profile Extraction** | Blood Group & Watermark Isolation | `test_parse_student_id_text_blood_group_and_watermark_isolation` | Captures B.Pharma; ignores Blood Group, Registrar, Vivo stamps | ✅ **VERIFIED PASSED** |
| **OCR Profile Extraction** | Inline Stop-Label Boundary Check | `test_parse_student_id_text_inline_blood_group_stop_token` | Stops program capture before inline blood group tokens | ✅ **VERIFIED PASSED** |
| **OCR Profile Extraction** | Dedicated Branch Line Parser | `test_parse_student_id_text_separate_branch_line` | Accurately extracts independent Branch / Dept rows | ✅ **VERIFIED PASSED** |
| **OCR Profile Extraction** | Dynamic Catalog & Blacklist Rejection | `test_parse_student_id_text_dynamic_catalog_and_blacklist_rejection` | Matches DB catalog; rejects non-academic candidate strings | ✅ **VERIFIED PASSED** |
| **Academic Bulk Delete** | Non-Admin Access Guard | `test_admin_academics_unauthorized` | Unauthorized access blocked (status 302/200 login error) | ✅ **VERIFIED PASSED** |
| **Academic Bulk Delete** | Admin View & Enrollment Metrics | `test_admin_academics_get_success` | Renders programs, branches, student count badges, and modal | ✅ **VERIFIED PASSED** |
| **Academic Bulk Delete** | Multi-Category JSON Bulk Deletion | `test_admin_academics_json_bulk_delete` | Deleted count = 3, PostgREST in_ filter chunked execution | ✅ **VERIFIED PASSED** |
| **Academic Bulk Delete** | Form Multi-Select Deletion Fallback | `test_admin_academics_form_bulk_delete` | Standard form POST redirects with success message | ✅ **VERIFIED PASSED** |
| **Excel Tracker** | Modern XLSX Generation | `openpyxl.load_workbook(...)` | 7 sheets, valid styles, freeze panes | ✅ **VERIFIED PASSED** |
| **Excel Tracker** | Native BIFF8 XLS Generation | File size & binary header check | >70 KB valid BIFF8 workbook | ✅ **VERIFIED PASSED** |
| **Excel Tracker** | Defect & Task Parity | Script audit vs git log | 38 tasks, 26 bugs, 12 ADRs, 65 commits | ✅ **VERIFIED PASSED** |
| **Format** | Visual Layout & Formal Spacing | Vertical height budget | Professional, balanced, proper formal spacing | ✅ **VERIFIED PASSED** |
| **300+ Tracker** | Item Count Verification | `assert len(ALL_ITEMS) >= 300` | Exactly 311 items verified | ✅ **VERIFIED PASSED** |
| **300+ Tracker** | Date Format Verification | `cell.number_format == 'dd mmmm yyyy'` | Proper full date (day, month, year) | ✅ **VERIFIED PASSED** |
| **300+ Tracker** | Category Coverage | Counter(Planning, Execution, Bug Fix, Testing) | 51 Plan, 118 Exec, 36 Bug, 106 Test | ✅ **VERIFIED PASSED** |
| **300+ Tracker** | XLSX Structure & Rows | `openpyxl.load_workbook(...)` | 312 rows (1 header + 311 data), 10 cols | ✅ **VERIFIED PASSED** |
| **300+ Tracker** | XLS BIFF8 Compatibility | `file /home/dell/AI_Intern_Work_Tracker_Face_Recognition.xls` | CDFV2 Microsoft Excel valid binary | ✅ **VERIFIED PASSED** |
