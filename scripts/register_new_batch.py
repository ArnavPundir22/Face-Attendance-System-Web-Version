import os
import sys
import csv
import re
import shutil
import numpy as np
import cv2
from PIL import Image
import pillow_heif

# Ensure project root is in sys.path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

from src.utils.db import supabase_admin as supabase
from src.utils.face import normalize_embedding, model

# Register HEIF opener so Pillow can read HEIC files
pillow_heif.register_heif_opener()

CSV_PATH = os.path.join(PROJECT_ROOT, "STUDENT DETAILS FORM 2026-2027 (Responses) - Form Responses 1.csv")
PHOTOS_DIR = os.path.join(PROJECT_ROOT, "UPLOAD YOUR LATEST PASSPORT PHOTOGRAPH IN HD QUALITY. ENSURE TO HAVE CLEAR FACE IN THE PHOTOGRAPH. (File responses)-20260805T052531Z-1-001/UPLOAD YOUR LATEST PASSPORT PHOTOGRAPH IN HD QUALITY. ENSURE TO HAVE CLEAR FACE IN THE PHOTOGRAPH. (File responses)")
ACTIVE_DIR = os.path.join(PROJECT_ROOT, "known_faces")
QUARANTINE_DIR = os.path.join(PROJECT_ROOT, "unsuitable_faces")

os.makedirs(ACTIVE_DIR, exist_ok=True)
os.makedirs(QUARANTINE_DIR, exist_ok=True)

def load_image_to_opencv(filepath):
    """Load an image (including HEIC) using Pillow and convert to BGR OpenCV format."""
    try:
        pil_img = Image.open(filepath)
        if pil_img.mode != 'RGB':
            pil_img = pil_img.convert('RGB')
        open_cv_image = np.array(pil_img)
        # Convert RGB to BGR
        open_cv_image = open_cv_image[:, :, ::-1].copy()
        return open_cv_image
    except Exception as e:
        print(f"Error loading image {filepath} with Pillow: {e}")
        return None

def clean_for_matching(text):
    return re.sub(r'[^a-z0-9]', '', text.lower()) if text else ""

def find_best_photo_match(student_name, student_cuid, files):
    """
    Search the directory files to find the best match for the student.
    Returns: (filename, match_type) or (None, None)
    """
    name_clean = clean_for_matching(student_name)
    cu_id_clean = clean_for_matching(student_cuid)
    
    # 1. Try matching by CU-ID in filename
    if cu_id_clean:
        for f in files:
            if cu_id_clean in clean_for_matching(f):
                return f, "CU-ID Match"
                
    # 2. Try matching by exact full name in filename
    if name_clean:
        for f in files:
            if name_clean in clean_for_matching(f):
                return f, "Exact Name Match"
                
    # 3. Fuzzy matching using parts of name (where at least 2 parts match, or if it is a single-part name and matches)
    name_parts = [p for p in student_name.lower().split() if len(p) > 2]
    if name_parts:
        best_match = None
        max_part_matches = 0
        for f in files:
            f_clean = clean_for_matching(f)
            # Count how many parts of the name are in this filename
            matches = sum(1 for part in name_parts if part in f_clean)
            if matches > max_part_matches:
                max_part_matches = matches
                best_match = f
                
        # Require that if name has multiple parts, at least half of them match
        min_required = max(1, len(name_parts) // 2)
        if max_part_matches >= min_required:
            return best_match, f"Fuzzy Name Parts ({max_part_matches}/{len(name_parts)})"
            
    return None, None

def main():
    dry_run = "--run" not in sys.argv
    if dry_run:
        print("=== DRY RUN MODE: No database inserts or file writes will be made. ===")
        print("=== To execute, run this script with --run flag. ===\n")
    else:
        print("=== RUN MODE: Processing registrations and database ingestion... ===\n")

    if not os.path.exists(CSV_PATH):
        print(f"CSV file not found: {CSV_PATH}")
        return
    if not os.path.exists(PHOTOS_DIR):
        print(f"Photos directory not found: {PHOTOS_DIR}")
        return

    with open(CSV_PATH, mode='r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    print(f"Found {len(rows)} records in CSV.")

    photo_files = os.listdir(PHOTOS_DIR)
    
    success_count = 0
    skipped_issue_count = 0
    missing_photo_count = 0
    no_face_count = 0
    db_error_count = 0

    for idx, row in enumerate(rows, start=1):
        cleaned_row = {k.strip(): v for k, v in row.items()}
        
        name = cleaned_row.get("STUDENT'S NAME", "").strip()
        cu_id = cleaned_row.get("CU-ID", "").strip()
        program = cleaned_row.get("PROGRAM", "").strip()
        branch = cleaned_row.get("BRANCH", "").strip()
        issue_marker = cleaned_row.get("0/1", "0").strip()
        issue_desc = cleaned_row.get("photo issue", "").strip()

        # Deduce missing B.Tech program
        if not program:
            program = "B.TECH"

        if not cu_id:
            print(f"[{idx}] Skipping row with missing CU ID.")
            continue

        print(f"\n--- [{idx}/{len(rows)}] Processing {name} ({cu_id}) ---")

        # Find photo match
        matched_file, match_type = find_best_photo_match(name, cu_id, photo_files)

        # 1. Handle issue-flagged students
        if issue_marker == "1" or issue_desc:
            print(f"Skipping student due to flagged photo issue: '{issue_desc if issue_desc else 'issue == 1'}'")
            if matched_file:
                src_path = os.path.join(PHOTOS_DIR, matched_file)
                dest_path = os.path.join(QUARANTINE_DIR, matched_file)
                if not dry_run:
                    try:
                        shutil.move(src_path, dest_path)
                        print(f"Moved flagged photo to quarantine: {matched_file}")
                    except Exception as e:
                        print(f"Failed to quarantine photo: {e}")
                else:
                    print(f"[Dry Run] Would move flagged photo to quarantine: {matched_file}")
            skipped_issue_count += 1
            continue

        # 2. Check if photo was found
        if not matched_file:
            print(f"Error: Could not locate photo file for student {name} ({cu_id}).")
            missing_photo_count += 1
            continue

        print(f"Mapped photo: '{matched_file}' via {match_type}")
        src_photo_path = os.path.join(PHOTOS_DIR, matched_file)
        dest_active_path = os.path.join(ACTIVE_DIR, f"{cu_id}.jpg")

        # 3. Check duplicate/existing student in Supabase DB to avoid extra work
        if not dry_run:
            try:
                existing = supabase.table("students").select("id").eq("id", cu_id).execute()
                if existing.data:
                    print(f"Student {cu_id} already exists in database. Skipping.")
                    success_count += 1
                    continue
            except Exception as e:
                print(f"Error checking DB for existing student: {e}")

        # 4. Load and process face photo
        image = load_image_to_opencv(src_photo_path)
        if image is None:
            print("Error: Failed to read/convert photo image file.")
            missing_photo_count += 1
            continue

        # 5. Extract face embedding
        faces = model.get(image)
        if not faces:
            print("No face detected in the photo!")
            if not dry_run:
                dest_q = os.path.join(QUARANTINE_DIR, f"{cu_id}_no_face_{matched_file}")
                shutil.copy(src_photo_path, dest_q)
                print(f"Moved face-less photo to quarantine: {dest_q}")
            else:
                print(f"[Dry Run] Would move face-less photo to quarantine")
            no_face_count += 1
            continue

        face = faces[0]
        new_emb = np.array(face.embedding, dtype=np.float32)
        normalized_emb = normalize_embedding(new_emb)

        if normalized_emb is None:
            print("Generated face embedding is invalid (zero norm).")
            no_face_count += 1
            continue

        # 6. Database ingestion
        if not dry_run:
            try:
                insert_data = {
                    "id": cu_id,
                    "name": name,
                    "program": program,
                    "branch": branch,
                    "gmail": "",  # No email column in this CSV
                    "enrollment_year": 2026,  # Default batch year
                    "embedding": normalized_emb.tolist()
                }
                supabase.table("students").insert(insert_data).execute()
                
                # Auto-upsert academic structure
                try:
                    if program:
                        supabase.table("academic_structure").upsert({"type": "program", "value": program}, on_conflict="type,value").execute()
                    if branch:
                        supabase.table("academic_structure").upsert({"type": "branch", "value": branch}, on_conflict="type,value").execute()
                except Exception as ae:
                    print(f"Warning: Could not auto-upsert academic structure: {ae}")

                # Save standardized active image
                cv2.imwrite(dest_active_path, image)
                print(f"Successfully registered student in Supabase: {name} ({cu_id})")
                success_count += 1
            except Exception as e:
                print(f"Database error during insertion: {e}")
                db_error_count += 1
        else:
            print(f"[Dry Run] Would generate embedding and register: {name} ({cu_id}) in Program: {program}, Branch: {branch}")
            success_count += 1

    print("\n=== Registration Summary ===")
    print(f"Successfully Registered / Dry Run Mapped: {success_count}")
    print(f"Skipped / Quarantined due to Issue Flags: {skipped_issue_count}")
    print(f"No Face Detected: {no_face_count}")
    print(f"Missing Photos: {missing_photo_count}")
    print(f"Database Insertion Errors: {db_error_count}")

if __name__ == "__main__":
    main()
