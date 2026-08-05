import os
import sys
import csv
import re
import shutil
import datetime
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

CSV_PATH = os.path.join(PROJECT_ROOT, "Student Registration Form (Responses) - Form Responses 1.csv")
PHOTOS_DIR = os.path.join(PROJECT_ROOT, "Recent Photograph (Google Drive Link) (File responses)-20260801T065802Z-1-001", "Recent Photograph (Google Drive Link) (File responses)")
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

def clean_name_for_fuzzy(name):
    """Remove special characters and lowercase for fuzzy matching."""
    return re.sub(r"[^a-z0-9]", "", name.lower())

def clean_program_branch(program_name):
    """Normalize program name and extract branch dynamically."""
    pn = program_name.strip()
    if not pn:
        return "BCA", "General"
    
    # Split by the first whitespace
    parts = pn.split(maxsplit=1)
    program = parts[0]
    
    # Normalize program name prefixes
    prog_clean = program.lower().replace(".", "")
    if prog_clean == "btech":
        program = "B.Tech"
    elif prog_clean == "mtech":
        program = "M.Tech"
    elif prog_clean == "bca":
        program = "BCA"
    elif prog_clean == "mca":
        program = "MCA"
    elif prog_clean == "bba":
        program = "BBA"
    elif prog_clean == "mba":
        program = "MBA"
        
    branch = "General"
    if len(parts) > 1:
        branch = parts[1].strip()
        # Convert short abbreviations (e.g. cse -> CSE, aiml -> AIML) to uppercase
        if len(branch) <= 4:
            branch = branch.upper()
            
    return program, branch


def derive_enrollment_year(cu_id):
    """Extract 4-digit enrollment year from CU ID prefix (with or without 'CU')."""
    cu_id = cu_id.strip()
    # Match optional 'CU' prefix followed by 2 digits (e.g. CU24..., cu25..., or just 24..., 25...)
    match = re.match(r'(?i)(?:cu)?(\d{2})', cu_id)
    if match:
        two_digit_year = match.group(1)
        return int(f"20{two_digit_year}")
    return 2026

def parse_csv_timestamp(ts_str):
    """Parse Google Forms timestamp string into a datetime object."""
    for fmt in ("%m/%d/%Y %H:%M:%S", "%m/%d/%Y %H:%M"):
        try:
            return datetime.datetime.strptime(ts_str.strip(), fmt)
        except ValueError:
            continue
    return None

def main():
    print(f"Reading CSV: {CSV_PATH}")
    if not os.path.exists(CSV_PATH):
        print("CSV file not found!")
        return

    with open(CSV_PATH, mode='r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    print(f"Found {len(rows)} student records in CSV.")

    # 1. Read files and their mtimes in the source directory
    files_info = []
    if os.path.exists(PHOTOS_DIR):
        for file in os.listdir(PHOTOS_DIR):
            path = os.path.join(PHOTOS_DIR, file)
            stat = os.stat(path)
            mtime = datetime.datetime.fromtimestamp(stat.st_mtime)
            files_info.append((file, mtime))
    
    success_count = 0
    skip_count = 0
    error_count = 0

    for idx, row in enumerate(rows, start=1):
        # Normalize keys
        cleaned_row = {k.strip(): v for k, v in row.items()}
        
        name = cleaned_row.get("Student's Name", "").strip()
        cu_id = cleaned_row.get("CU ID", "").strip()
        email = cleaned_row.get("Email Address", "").strip()
        program_name = cleaned_row.get("Program Name", "").strip()
        ts_str = cleaned_row.get("Timestamp", "").strip()
        issue_marker = cleaned_row.get("1/0", "0").strip()
        issue_desc = cleaned_row.get("Issue", "").strip()

        if not cu_id:
            print(f"[{idx}] Skipping row with missing CU ID.")
            continue

        print(f"\n--- [{idx}/{len(rows)}] Processing {name} ({cu_id}) ---")

        # Parse submission time
        ts = parse_csv_timestamp(ts_str)
        if not ts:
            print("Error: Could not parse timestamp.")
            error_count += 1
            continue

        # Target file mtime is ts minus 12 hours and 30 minutes
        target_mtime = ts - datetime.timedelta(hours=12, minutes=30)

        # 1. Find candidates containing the student name
        candidates = []
        name_clean = clean_name_for_fuzzy(name)
        for file, mtime in files_info:
            base, ext = os.path.splitext(file)
            name_part = base.split(" - ")[-1].strip()
            
            # Substring/Fuzzy match
            if name_clean in clean_name_for_fuzzy(name_part) or clean_name_for_fuzzy(name_part) in name_clean:
                candidates.append((file, mtime))

        # Find best candidate using mtime comparison (within 10 minutes)
        matched_file = None
        min_diff = datetime.timedelta(seconds=999999)
        for file, mtime in candidates:
            diff = abs(mtime - target_mtime)
            if diff < min_diff:
                min_diff = diff
                matched_file = file

        # Check if the closest match is within a reasonable timeframe (e.g. 5 minutes)
        if matched_file and min_diff.total_seconds() > 300:
            print(f"Candidate file found ({matched_file}) but time difference too large ({min_diff.total_seconds()}s). Ignoring.")
            matched_file = None

        # 2. Process skipped/flagged issues
        if issue_marker == "1":
            print(f"Skipping student due to flagged issue status: '{issue_desc}'")
            if matched_file:
                src_path = os.path.join(PHOTOS_DIR, matched_file)
                dest_path = os.path.join(QUARANTINE_DIR, matched_file)
                try:
                    shutil.move(src_path, dest_path)
                    print(f"Moved photo to quarantine: {matched_file}")
                except Exception as e:
                    print(f"Failed to quarantine photo: {e}")
            skip_count += 1
            continue

        # 3. Check for duplicate/existing student in DB
        try:
            existing = supabase.table("students").select("id").eq("id", cu_id).execute()
            if existing.data:
                print(f"Student {cu_id} already exists in database. Skipping.")
                success_count += 1
                continue
        except Exception as e:
            print(f"Error checking DB for existing student: {e}")

        # 4. Map Photo
        if not matched_file:
            print(f"Error: Could not locate photo file for student {name} at timestamp {ts_str}.")
            error_count += 1
            continue

        print(f"Successfully mapped photo: '{matched_file}' (Time Diff: {min_diff.total_seconds()}s)")

        src_photo_path = os.path.join(PHOTOS_DIR, matched_file)
        temp_photo_path = os.path.join(ACTIVE_DIR, f"{cu_id}.jpg")

        # 5. Load and convert image to BGR format
        image = load_image_to_opencv(src_photo_path)
        if image is None:
            print("Error: Failed to read/convert photo image file.")
            error_count += 1
            continue

        # 6. Generate face embedding
        faces = model.get(image)
        if not faces:
            print("No face detected in the photo!")
            # Move photo to quarantine as it failed face detection
            dest_q = os.path.join(QUARANTINE_DIR, f"{cu_id}_no_face_{matched_file}")
            shutil.copy(src_photo_path, dest_q)
            error_count += 1
            continue

        face = faces[0]
        new_emb = np.array(face.embedding, dtype=np.float32)
        normalized_emb = normalize_embedding(new_emb)

        if normalized_emb is None:
            print("Generated face embedding is invalid (zero norm).")
            error_count += 1
            continue

        # 7. Clean student details and insert to Supabase
        program, branch = clean_program_branch(program_name)
        enrollment_year = derive_enrollment_year(cu_id)

        try:
            insert_data = {
                "id": cu_id,
                "name": name,
                "program": program,
                "branch": branch,
                "gmail": email,
                "enrollment_year": enrollment_year,
                "embedding": normalized_emb.tolist()
            }
            supabase.table("students").insert(insert_data).execute()
            
            # Register program & branch in academic_structure table so they show up on admin pages
            try:
                if program:
                    supabase.table("academic_structure").upsert({"type": "program", "value": program}, on_conflict="type,value").execute()
                if branch:
                    supabase.table("academic_structure").upsert({"type": "branch", "value": branch}, on_conflict="type,value").execute()
            except Exception as ae:
                print(f"Warning: Could not auto-upsert academic structure: {ae}")
            
            # Save standard JPG to active known faces directory
            cv2.imwrite(temp_photo_path, image)
            print(f"Successfully registered student in Supabase: {name} ({cu_id})")
            success_count += 1
        except Exception as e:
            print(f"Database error during insertion: {e}")
            error_count += 1

    print("\n=== Registration Summary ===")
    print(f"Successfully Registered: {success_count}")
    print(f"Skipped / Quarantined: {skip_count}")
    print(f"Errors / Missing photos: {error_count}")

if __name__ == "__main__":
    main()
