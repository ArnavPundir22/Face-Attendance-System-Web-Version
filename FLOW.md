# System Execution Flow & Path Mapping — BioSecure AI

This document maps control flow and data transitions across BioSecure AI subsystems.

---

## 1. Academic Structure Management Flow

```
Admin Browser
     │
     ├─► GET /admin/academics
     │     │
     │     ├─► Query `academic_structure` table (program, branch)
     │     ├─► Query `students` table (aggregate student counts per program/branch)
     │     └─► Render `admin_academics.html` with selection checkboxes, filter inputs,
     │         student count badges, and bulk-action toolbars.
     │
     ├─► POST /admin/academics (Bulk Removal / Single Delete / Add)
     │     │
     │     ├─► Authentication Guard: `_require_admin()` (Admin session verified)
     │     │
     │     ├─► Action: 'add'
     │     │     └─► Upsert `(type, value)` into `academic_structure`
     │     │
     │     ├─► Action: 'delete' / 'delete_multiple' / 'bulk_delete'
     │     │     ├─► Extract `values` or `(program_values, branch_values)`
     │     │     ├─► Chunk into safe batch sizes (≤50 items per query)
     │     │     ├─► PostgREST: `.delete().eq('type', ...).in_('value', chunk)`
     │     │     └─► Return JSON `{ success: true, deleted_count: N }` OR redirect
     │     │
     │     └─► UI Update: Animate removal from DOM / refresh catalog dropdowns
```

---

## 2. Face Recognition & Attendance Pipeline

```
Camera Stream (Browser)
     │
     ├─► POST /api/recognize_frame
     │     │
     │     ├─► OpenCV Frame Decoding
     │     ├─► InsightFace (SCRFD Detector + ArcFace ResNet50)
     │     ├─► In-Memory BLAS Matrix Dot Product Search (`face_cache.py`)
     │     │     └─ Cosine Similarity Threshold: ≥ 0.40 (Positive match)
     │     │     └─ Visual Alert fallback if unknown
     │     ├─► EWMA Drift Tracking (Biometric Aging update)
     │     └─► Supabase `attendance` record insertion
```


---

## 3. Student ID Card OCR & Academic Normalization Flow

```
ID Card Capture (Camera / File Upload)
     │
     ├─► POST /api/ocr_id_card
     │     │
     │     ├─► Pretrained RapidOCR (ONNX DBNet + SVTR) / PyTesseract
     │     ├─► Camera Watermark & Artifact Sanitization (strips "Vivo", "ZEISS", dates)
     │     ├─► Line-by-Line Tokenization & Label Stop Delimiters (Blood Group, DOB, Registrar)
     │     ├─► Dedicated Field Extraction (Program, Branch, ID, Name, Session)
     │     ├─► Dynamic Academic Structure Catalog Matcher (`academic_structure` table)
     │     ├─► Negative Blacklist Verification (Rejects blood types, titles, metadata)
     │     └─► Response `{ success: true, parsed_data: {...} }`
     │
     ▼
Student Registration Frontend (`add_student.html`)
     │
     ├─► `selectBestMatchingOption()` normalized fuzzy matching against catalog
     ├─► Dropdown matches highlighted in green (Zero unverified auto-additions)
     └─► Prevents spurious OCR text from contaminating `academic_structure` DB table
```
