import os
import re
from difflib import get_close_matches
import pandas as pd

photos_folder = "photos"
csv_file = "data.csv"  # CSV now only contains names

# Read names
csv_names_raw = pd.read_csv(csv_file, header=None)[0].astype(str).tolist()

# Normalize function
def normalize_text(text):
    text = str(text).strip().lower()
    text = re.sub(r'[^a-z ]', ' ', text)
    text = re.sub(r'\s+', ' ', text)
    return text

csv_names = [normalize_text(name) for name in csv_names_raw]
name_mapping = dict(zip(csv_names, csv_names_raw))

def clean_photo_name(filename):
    name, _ = os.path.splitext(filename)
    return normalize_text(name)

# Loop through photos
for file in os.listdir(photos_folder):
    if file.lower().endswith(('.jpg', '.jpeg', '.png')):
        cleaned_photo = clean_photo_name(file)

        # Substring match
        match = None
        for cname in csv_names:
            if cname in cleaned_photo or cleaned_photo in cname:
                match = cname
                break

        # Fuzzy match
        if not match:
            fuzzy = get_close_matches(cleaned_photo, csv_names, n=1, cutoff=0.3)
            if fuzzy:
                match = fuzzy[0]

        # Rename
        if match:
            new_name = name_mapping[match] + os.path.splitext(file)[1]
            old_path = os.path.join(photos_folder, file)
            new_path = os.path.join(photos_folder, new_name)
            os.rename(old_path, new_path)
            print(f"✅ Renamed: {file} → {new_name}")
        else:
            print(f"❌ No match found for: {file}")
