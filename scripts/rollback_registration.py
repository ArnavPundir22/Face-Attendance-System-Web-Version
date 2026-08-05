import os
import sys
import csv
import shutil

# Ensure project root is in sys.path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

from src.utils.db import supabase_admin as supabase

CSV_PATH = os.path.join(PROJECT_ROOT, "Student Registration Form (Responses) - Form Responses 1.csv")
PHOTOS_DIR = os.path.join(PROJECT_ROOT, "Recent Photograph (Google Drive Link) (File responses)-20260801T065802Z-1-001", "Recent Photograph (Google Drive Link) (File responses)")
ACTIVE_DIR = os.path.join(PROJECT_ROOT, "known_faces")
QUARANTINE_DIR = os.path.join(PROJECT_ROOT, "unsuitable_faces")

def main():
    print(f"Reading CSV: {CSV_PATH}")
    if not os.path.exists(CSV_PATH):
        print("CSV file not found!")
        return

    with open(CSV_PATH, mode='r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    # Collect IDs to delete
    cu_ids = []
    for row in rows:
        cleaned_row = {k.strip(): v for k, v in row.items()}
        cu_id = cleaned_row.get("CU ID", "").strip()
        if cu_id:
            cu_ids.append(cu_id)

    print(f"Found {len(cu_ids)} potential student IDs to clean up.")

    # 1. Supabase deletion
    deleted_db_count = 0
    # Batch deletes in small chunks to avoid limits
    chunk_size = 50
    for i in range(0, len(cu_ids), chunk_size):
        chunk = cu_ids[i:i+chunk_size]
        try:
            # Delete from Supabase matching these IDs
            response = supabase.table("students").delete().in_("id", chunk).execute()
            deleted_db_count += len(response.data) if response.data else 0
        except Exception as e:
            print(f"Error deleting batch from Supabase: {e}")

    print(f"Deleted {deleted_db_count} student records from Supabase database.")

    # 2. Delete copied photos from known_faces/
    deleted_photos_count = 0
    for cu_id in cu_ids:
        photo_path = os.path.join(ACTIVE_DIR, f"{cu_id}.jpg")
        if os.path.exists(photo_path):
            try:
                os.remove(photo_path)
                deleted_photos_count += 1
            except Exception as e:
                print(f"Failed to delete photo {photo_path}: {e}")

    print(f"Deleted {deleted_photos_count} face photos from known_faces/.")

    # 3. Restore quarantined photos from unsuitable_faces/ back to source directory
    restored_count = 0
    if os.path.exists(QUARANTINE_DIR):
        for file in os.listdir(QUARANTINE_DIR):
            src_path = os.path.join(QUARANTINE_DIR, file)
            dest_path = os.path.join(PHOTOS_DIR, file)
            try:
                shutil.move(src_path, dest_path)
                restored_count += 1
            except Exception as e:
                print(f"Failed to restore quarantined file {file}: {e}")

    print(f"Restored {restored_count} quarantined photos back to source directory.")
    print("Rollback completed successfully!")

if __name__ == "__main__":
    main()
